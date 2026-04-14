from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node, ua, uamethod
from asyncua.server.internal_session import InternalSession
from asyncua.ua import NodeId, QualifiedName
from asyncua.ua.uaerrors import BadNoMatch
from typing_extensions import deprecated, final, override

from ..common.enums import SkillStates
from ..common.exceptions import SkillHaltedError
from .base_callable import BaseCallable
from .common import get_node_id
from .ua_types import UaTypes
from .user import User

if TYPE_CHECKING:  # prevent circular imports during run-time
    from .base_machinery_item import BaseMachineryItem


class BaseSkill(BaseCallable, ABC):
    """
    Abstract base skill, only simplifies the OPC-UA representation, contains no state machine logic etc.

    Derived classes must implement at least the reset(), start() and halt() methods for a non-suspendable skill.
    The _condition_skill_ready() method can be overridden in order to add skill specific conditions before the
    start() method is allowed to be executed by the state machine.
    """

    ua_state_machine: Node
    """OPC UA base node of state machine."""
    ua_state_variable: Node
    """OPC UA node if the state variable of the state machine."""


    def __init__(self, name: str, machinery_item: 'BaseMachineryItem', _type: Node, suspendable: bool =False,
                 minimum_access_level: int = 1,
                 precondition_check: BaseSkill | None = None, feasibility_check: BaseSkill | None = None):
        """Create a new skill instance.

        :param name: name of the skill
        :param machinery_item: machinery_item instance
        :param _type: OPC UA node determining the OPC UA object type used for instantiation.
        :param suspendable: whether the skill can be suspended/resumed
        :param minimum_access_level: Minimum required access level to start the skill (see User for more info)
        :param precondition_check: Optional reference to corresponding separate precondition check for this skill
        :param feasibility_check: Optional reference to corresponding separate feasibility check for this skill
        """
        super().__init__(name=name, machinery_item=machinery_item, _type=_type,
                         minimum_access_level=minimum_access_level)

        self._current_state = SkillStates.Halted
        self.suspendable = suspendable
        self._precondition_check = precondition_check
        self._feasibility_check = feasibility_check
        self._called_skills: list[BaseSkill] = []
        self.logger = structlog.stdlib.get_logger("sf.server.Skill", name=self.full_name)

    @override
    async def _get_sub_node(self) -> Node:
        return await self._ua_node.get_child(QualifiedName("SkillExecution", UaTypes.ns_skill_set))

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        """Initialize the skill instance asynchronously.

        :param existing_node: pre-existing OPC UA node prior to init().
                Will be used instead of creating a new node in the given location.
        :param location: parent OPC-UA node, ideally a folder type
        """
        await super().init(location=location, existing_node=existing_node)

        ua_sub_node = await self._get_sub_node()  # either SkillExecution, PreconditionCheck or FeasibilityCheck
        self.ua_state_machine = await ua_sub_node.get_child(QualifiedName("StateMachine", UaTypes.ns_skill_set))
        self.ua_state_variable = await self.ua_state_machine.get_child("CurrentState")

        node_start, node_halt, node_reset = await asyncio.gather(
            self.ua_state_machine.get_child(f"{UaTypes.ns_machine_set}:Start"),
            self.ua_state_machine.get_child(f"{UaTypes.ns_machine_set}:Halt"),
            self.ua_state_machine.get_child(f"{UaTypes.ns_machine_set}:Reset")
        )

        _session = self._machinery_item.server.iserver.isession
        _session.add_method_callback(node_start.nodeid, self._ua_start)
        _session.add_method_callback(node_halt.nodeid, self._ua_halt)
        _session.add_method_callback(node_reset.nodeid, self._ua_reset)

        try:
            node_suspend = await self.ua_state_machine.get_child(f"{UaTypes.ns_machine_set}:Suspend")
        except BadNoMatch:
            node_suspend = None

        if self.suspendable:  # checks are not suspendable at all (?!)
            if node_suspend is not None:
                _session.add_method_callback(node_suspend.nodeid, self._ua_suspend)
            else:
                suspend_node_id = get_node_id(self.ua_state_machine, "Suspend", UaTypes.ns_machine_set)
                await self.ua_state_machine.add_method(
                    suspend_node_id, f"{UaTypes.ns_machine_set}:Suspend", self._ua_suspend)
        elif node_suspend is not None:
            await node_suspend.delete()  # suspend method must not exist for skills that cannot be suspended


        if self._precondition_check is None and existing_node is None:
            try:
                # no recursive delete to improve startup speed
                await (await self._ua_node.get_child(f"{UaTypes.ns_skill_set}:PreconditionCheck")).delete()
                self.logger.debug("Removed unused PreconditionCheck")
            except BadNoMatch:
                pass
        elif self._precondition_check is not None:
            await self._precondition_check.init(existing_node=self._ua_node)

        if self._feasibility_check is None and existing_node is None:
            try:
                # no recursive delete to improve startup speed
                await (await self._ua_node.get_child(f"{UaTypes.ns_skill_set}:FeasibilityCheck")).delete()
                self.logger.debug("Removed unused FeasibilityCheck")
            except BadNoMatch:
                pass
        elif self._feasibility_check is not None:
            await self._feasibility_check.init(existing_node=self._ua_node)

    async def _set_current_state(self, state: SkillStates):
        """ Sets the current state of this skill to the given state without any logic checks. """
        if not isinstance(state, SkillStates):
            raise TypeError(f"Given state '{state}' is not of type SkillStates")
        self._current_state = state
        await self.ua_state_variable.write_value(ua.LocalizedText(state.name, "en-US"))

    # The user should not figure out the type manually based on OPC UA nodes - CaHa

    ######################################
    # FSM Conditions

    # Raise UaStatusCodeError for correct OPC-UA status code answers instead of a misc one

    async def _condition_access_allowed(self, user: User) -> bool:
        """ Checks if the provided user has access to this skill, i.e. currently occupies the machinery_item. """
        if not self.access_control.access_allowed(user, self._minimum_access_level):
            await self._log_error(
                f"Denied, user '{user}' has no access to this skill "
                f"(access level {self._minimum_access_level} required)!"
            )
            raise ua.UaStatusCodeError(ua.StatusCodes.BadUserAccessDenied)
        return True

    async def _condition_startup_completed(self, user: User) -> bool:
        """Check whether the parent startup is completed."""
        # the startup skill is the skill that is responsible for "startup" being completed,
        # so it is always passes this condition check
        if self.name.lower().startswith("startup"):
            self.logger.debug(f"{self.full_name} passed the condition_startup_completed check automatically!")
            return True

        return await self._machinery_item._condition_startup_completed(user)


    async def _condition_is_suspendable(self, _user: User) -> bool:
        """ Checks whether this skill is suspendable. """
        if not self.suspendable:
            await self._log_error(f"Denied, skill '{self.full_name}' is not suspendable!")
            raise ua.UaStatusCodeError(ua.StatusCodes.BadNotImplemented)
        return True

    async def _condition_dependencies_ready(self, _user: User) -> bool:
        """ Checks whether ALL dependencies are ready (different meaning for different types). """
        from pyuaadapter.server.components.base_port import BasePort

        for dependency in self._dependencies:
            if isinstance(dependency, BasePort) and not dependency.is_mated():
                await self._log_error(
                    f"Denied, required port '{dependency.full_name}' for skill '{self.full_name}' is not coupled!")
                raise ua.UaStatusCodeError(ua.StatusCodes.BadStateNotActive)
            elif isinstance(dependency, BaseSkill):
                self.logger.debug(
                    "Skill dependency state", dependency=dependency.full_name, state=dependency.current_state.name
                )
                if dependency.is_continuous:
                    if dependency.current_state not in [SkillStates.Ready, SkillStates.Running]:
                        await self._log_error(
                            f"Denied, required continuous skill '{dependency.full_name}' for skill '{self.full_name}' is not running!")
                        raise ua.UaStatusCodeError(ua.StatusCodes.BadStateNotActive)
                elif dependency.is_finite:
                    if dependency.current_state not in [SkillStates.Ready, SkillStates.Completed]:
                        await self._log_error(
                            f"Denied, required finite skill '{dependency.full_name}' for skill '{self.full_name}' is not ready!")
                        raise ua.UaStatusCodeError(ua.StatusCodes.BadStateNotActive)
                else:
                    await self._log_warning(
                        f"Given skill dependency '{dependency.full_name}' for skill '{self.full_name}' "
                        f"is neither finite nor continuous, ignoring!")
            else:
                await self._log_warning(f"Given dependency '{dependency}' for skill '{self.full_name}'"
                                        f" is not supported, ignoring!")
        return True

    # TODO remove for the next major version
    @deprecated("Please use _condition_start_allowed() instead!")
    @final  # marked final to notify users hopefully...
    async def _condition_skill_ready(self, _user: User) -> bool:
        """To be implemented (optional) by derived classes to implement custom skill related conditions."""
        return True

    async def _condition_start_allowed(self, _user: User) -> bool:
        """Implement custom conditions checked before starting the skill."""
        return True

    async def _condition_reset_allowed(self, _user: User) -> bool:
        """Implement custom conditions checked before resetting the skill."""
        return True

    async def _condition_suspend_allowed(self, _user: User) -> bool:
        """Implement custom conditions checked before suspending the skill."""
        return True

    ######################################
    # OPC-UA Callbacks

    @uamethod
    @abstractmethod
    async def _ua_start(self, _parent: NodeId, session: InternalSession):
        raise ua.UaStatusCodeError(ua.StatusCodes.BadNotImplemented)

    @uamethod
    @abstractmethod
    async def _ua_suspend(self, _parent: NodeId, session: InternalSession):
        raise ua.UaStatusCodeError(ua.StatusCodes.BadNotImplemented)

    @uamethod
    @abstractmethod
    async def _ua_reset(self, _parent: NodeId, session: InternalSession):
        raise ua.UaStatusCodeError(ua.StatusCodes.BadNotImplemented)

    @uamethod
    @abstractmethod
    async def _ua_halt(self, _parent: NodeId, session: InternalSession):
        raise ua.UaStatusCodeError(ua.StatusCodes.BadNotImplemented)

    ######################################
    # Internal skill interface (for composite skills)

    # TODO remove user from these methods for next major version, no longer required (is a breaking change!)

    @abstractmethod
    async def start(self, user: User | None = None) -> None:
        """ Start the skill. Machine internal interface.

        Similar to calling the OPC UA method start() as the given user, except that exceptions are not handled.
        """
        raise NotImplementedError

    @abstractmethod
    async def suspend(self, user: User | None = None) -> None:
        """ Suspend the skill (if the skill is suspendable). Machine internal interface.

        Similar to calling the OPC UA method suspend() as the given user, except that exceptions are not handled.
        """
        raise NotImplementedError

    @abstractmethod
    async def reset(self, user: User | None = None) -> None:
        """ Reset the skill. Machine internal interface.

        Similar to calling the OPC UA method reset() as the given user, except that exceptions are not handled.
        """
        raise NotImplementedError

    @abstractmethod
    async def halt(self, user: User | None = None) -> None:
        """ Halt (Stop) the skill. Machine internal interface.

        Similar to calling the OPC UA method halt() as the given user, except that exceptions are not handled.
        """
        raise NotImplementedError


    @property
    @deprecated("Use current_state instead!")
    def state(self) -> SkillStates:  # TODO legacy, remove with v4
        """ State of the skill. """
        return self.current_state

    @property
    def current_state(self) -> SkillStates:
        """ Current state of the skill. """
        return self._current_state

    async def wait_for_state(self, state: SkillStates, timeout: float | None = 60) -> None:
        """ Blocks until the skill either reached the given state or was halted or the timeout was reached.

        :param state: the state of this skill to wait for
        :param timeout:  timeout in seconds, maximum wait time.
        """
        source_state = self.current_state
        self.logger.debug("Waiting for state...", source_state=source_state.name, target_state=state.name,
                          timeout=timeout)

        async def _wait():
            while True:
                if self.current_state == state:
                    break
                elif source_state != SkillStates.Halted and self.current_state == SkillStates.Halted:
                    raise SkillHaltedError(f"Skill '{self.full_name}' halted while waiting for state '{state.name}'!")
                await asyncio.sleep(0.1)

        if timeout is not None:
            await asyncio.wait_for(_wait(), timeout)
        else:
            await _wait()

    async def _halt_running_called_skills(self):
        for skill in self._called_skills:
            if skill.current_state == SkillStates.Running:
                try:
                    await skill.halt()
                except Exception as ex:
                    self.logger.exception(ex)
                    self.logger.error(f"Could not halt running skill '{skill.full_name}'! Skipping!")


    async def call_other_finite_skill(self, skill: 'BaseSkill',
                                      *,
                                      parameters: dict[str, Any] | None = None,
                                      wait_for_completion: bool = True,
                                      timeout: float | None = 60.0,
                                      reset_after_completion: bool = True
                                      ) -> dict[str, Any]:
        """ Calls another finite skill with the given parameters.

        :param skill: the finite skill to call.
        :param parameters: optional parameters given to the skill before starting it.
        :param wait_for_completion: should this method block until the timeout is reached or the skill is completed?
        :param timeout: timeout in seconds, can be disabled by setting it to None.
        :param reset_after_completion: should the called skill be reset after completion?

        Returns the final result data as a dictionary if the called skill completed successfully when
        wait_for_completion == True. Otherwise, the dictionary will be empty.
        """
        if skill is None:
            raise ValueError("No Skill given!")
        elif not skill.is_finite:
            raise TypeError("Wrong type of skill given, a finite skill is required!")

        logger = self.logger.bind(other_skill=skill.full_name)

        if skill not in self._dependencies:
            logger.warning("Calling other skill that is not in dependencies!")

        if skill not in self._called_skills:  # only add it the first time it is called
            self._called_skills.append(skill)

        match skill.current_state:
            case SkillStates.Ready:
                pass  # Already in Ready, nothing to do
            case SkillStates.Completed:  # Safe to reset
                self.logger.info("Resetting completed skill dependency...", skill=skill.full_name)
                await skill.reset()
                await skill.wait_for_state(SkillStates.Ready, timeout=timeout)
            case _:  # Potentially unsafe to reset
                raise RuntimeError(f"Other skill in unsupported state '{skill.current_state.name}'!")

        if parameters is not None:
            await skill.write_parameters(parameters)

        logger.debug("Trying to start skill...")
        await skill.start()

        if not wait_for_completion:
            return {}  # we are done
        # else:
        logger.debug("Waiting for other skill to be completed.", timeout=timeout)
        await skill.wait_for_state(SkillStates.Completed, timeout)

        # grab a results from completed skill
        ret = await skill.read_results()
        if reset_after_completion and skill.is_finite:
            # reset seems not to be suitable for conti skills
            logger.debug("Trying to reset other skill after completion...")
            await skill.reset()  # needs to be reset to be ready again (Skill V3+)
            logger.debug("Waiting for other skill to be ready again.", timeout=timeout)
            await skill.wait_for_state(SkillStates.Ready, timeout)

        return ret


    async def call_other_continuous_skill(self, skill: 'BaseSkill',
                                          *,
                                          parameters: dict[str, Any] | None = None,
                                          wait_for_running: bool = True,
                                          timeout: float | None = 10.0,
                                          ) -> None:
        """ Calls another continuous skill with the given parameters.

        :param skill: the continuous skill to call.
        :param parameters: optional parameters given to the skill before starting it.
        :param wait_for_running: should this method block until the timeout is reached or the skill is running?
        :param timeout: timeout in seconds, can be disabled by setting it to None.
        """
        if skill is None:
            raise ValueError("No Skill given!")
        elif not skill.is_continuous:
            raise TypeError("Wrong type of skill given, a continuous skill is required!")

        logger = self.logger.bind(other_skill=skill.full_name)

        if skill not in self._dependencies:
            logger.warning("Calling other skill that is not in dependencies!")

        if skill not in self._called_skills:  # only add it the first time it is called
            self._called_skills.append(skill)

        if parameters is not None:
            await skill.write_parameters(parameters)

        logger.debug("Trying to start other skill...")
        await skill.start()

        if wait_for_running:
            logger.debug("Waiting for other skill to be running", timeout=timeout)
            await skill.wait_for_state(SkillStates.Running, timeout)

    # TODO discuss this API further after HM2025, it is too much magic
    #  continuous skills operate differently than finite skills and the user should be aware of
    #  what kind of skill they call. If a composite skill requires a continuous skill to be running
    #  while it is running, it is NOT enough to wait until that conti skill is running once, but to make sure
    #  it stays running as long as it is required!
    @deprecated("Please use either call_other_finite_skill() or call_other_continuous_skill()")
    async def call_other_skill2(self, skill: 'BaseSkill',
                               *,
                               parameters: dict[str, Any] | None = None,
                               timeout: float = 10.0,
                               wait_for_completion: bool = True,
                               reset_after_completion: bool = True) -> dict[str, Any] | None:
        """ Calls another skill with the given parameters.

        By default, a timeout of 10 seconds is used, but it can be disabled by setting it to None.

        If skill is a finite skill and 'wait_for_completion=True' target state is 'Completed'.
        If skill is a continuous skill and 'wait_for_completion=True' target state is 'Running'.

        reset_after_completion is only executed if skill is a finite skill.

        Returns all values of variables of FinalResultData from called finite skill as dictionary when the
        skill call completed successfully within the timeout limit.
        """
        if skill is None:
            raise ValueError("No Skill given!")
        elif skill.is_finite:
            return await self.call_other_finite_skill(skill,
                                               parameters=parameters,
                                               timeout=timeout,
                                               wait_for_completion=wait_for_completion,
                                               reset_after_completion=reset_after_completion)
        elif skill.is_continuous:
            await self.call_other_continuous_skill(skill,
                                                   parameters=parameters,
                                                   timeout=timeout,
                                                   wait_for_running=wait_for_completion
                                                   )
            return None
        else:
            raise ValueError("Given skill is neither finite nor continuous?!")


    @deprecated("Please Use either call_other_finite_skill() or call_other_continuous_skill()")
    async def call_other_skill(self, user: User, # TODO remove method sometime after HM 2025
                               skill: 'BaseSkill',
                               parameters: dict[str, Any] | None = None,
                               timeout: float = 10.0,
                               wait_for_completion: bool = True,
                               reset_after_completion: bool = True) -> dict[str, Any] | None:
        """
        Calls another skill with the given parameters.
        By default, a timeout of 10 seconds is used, but it can be disabled by setting it to None
        (required for continuous skills).

        If skill is a finite skill and 'wait_for_completion=True' target state is 'Completed'.
        If skill is a continuous skill and 'wait_for_completion=True' target state is 'Running'.

        reset_after_completion is only executed if skill is a finite skill.

        Returns all values of variables of FinalResultData from called Skill as dictionary when the skill call
        completed successfully within the timeout limit. Note: If timeout is None, no result will be returned!
        """
        if parameters is not None:
            await skill.write_parameters(parameters)

        self.logger.debug(f"Trying to start skill '{skill.full_name}' ...")
        await skill.start()
        if wait_for_completion:
            if skill.is_finite:
                self.logger.debug(f"Waiting for finite skill '{skill.full_name}' to be completed. {timeout=}")
                await skill.wait_for_state(SkillStates.Completed, timeout)
            else:
                self.logger.debug(f"Waiting for continuous skill '{skill.full_name}' to be running. {timeout=}")
                await skill.wait_for_state(SkillStates.Running, timeout)
            # grab a results from completed skill
            ret = await skill.read_results()
            if reset_after_completion and skill.is_finite:
                # reset seems not to be suitable for conti skills
                self.logger.debug(f"Trying to reset skill '{skill.full_name} after completion...")
                await skill.reset()  # needs to be reset to be ready again (Skill V3+)
                self.logger.debug(f"Waiting for skill '{skill.full_name}' to be ready again. {timeout=}")
                await skill.wait_for_state(SkillStates.Ready, timeout)

            return ret


    @property
    def is_finite(self) -> bool:
        """ Returns True if this skill is finite, regardless where the logic is implemented (PLC vs Adapter). """
        return self._type.nodeid == UaTypes.finite_skill_type.nodeid

    @property
    def is_continuous(self) -> bool:
        """ Returns True if this skill is continuous, regardless where the logic is implemented (PLC vs Adapter). """
        return self._type.nodeid == UaTypes.continuous_skill_type.nodeid
