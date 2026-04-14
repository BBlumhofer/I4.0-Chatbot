from __future__ import annotations

import asyncio
import time
import traceback
from abc import ABC
from collections.abc import Iterable
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional, Type, TypeVar, cast

from asyncua import Node, Server, ua
from asyncua.server import EventGenerator
from asyncua.ua import NodeId, QualifiedName, VariantType
from asyncua.ua.uaerrors import BadNoMatch
from typing_extensions import deprecated

from ..common.enums import MachineryItemStates, MachineryOperationModes, SkillStates
from .base_asset import BaseAsset
from .base_config import BaseConfig
from .base_method import BaseMethod
from .base_skill import BaseSkill
from .common import (
    add_object,
    create_missing_objects,
    get_child_without_ns,
    halt_skills_parallel_and_wait,
    reset_skills_parallel_and_wait,
    write_optional,
)
from .resources.base_resource import BaseResource
from .skills.base_startup_skill import BaseStartupSkill
from .spatial_object import SpatialObject
from .ua_fsm import _get_proper_state_name
from .ua_types import UaTypes
from .user import User

T = TypeVar('T', bound="BaseMachineryItem")
S = TypeVar('S', bound="BaseSkill")
M = TypeVar('M', bound="BaseMethod")
P = TypeVar("P", bound="BasePort")  # noqa: F821
R = TypeVar('R', bound="BaseResource")

INITIAL_STATE = MachineryItemStates.OutOfService
INITIAL_OPERATION_MODE = MachineryOperationModes.None_

class BaseMachineryItem(BaseAsset, ABC):
    """ Base class for every asset (module, port, component) """

    ua_parameter_set: Node
    ua_parameter_set_nodes: Dict[str, Node]

    ua_components: Node

    ua_notification: Node
    ua_error_code: Node
    ua_severity: Node
    ua_info_text: Node
    ua_info_event_gen: EventGenerator
    ua_alarm_event_gen: EventGenerator

    ua_skills_folder: Node
    ua_resources_folder: Node
    ua_machinery_building_blocks: Node
    ua_state_machine: Node | None
    """Optional 'MachineryItemState' (finite state machine) OPC UA node."""
    ua_operation_mode: Node | None
    """Optional 'MachineryOperationMode' (finite state machine) OPC UA node."""

    _ua_state_machine_current_state: Node | None
    """Optional current_state OPC UA node of 'MachineryItemState'."""
    _ua_operation_mode_current_state: Node | None
    """Optional current_state OPC UA node of 'MachineryOperationMode'."""

    _handle_status_change_task: asyncio.Task | None

    def __init__(self, server: Server, parent: Optional["BaseMachineryItem"], ns_idx: int, _id: str, name: str,
                 config: BaseConfig, **kwargs):
        super().__init__(server=server, parent=parent, ns_idx=ns_idx, _id=_id, name=name, config=config)
        self.skills: dict[str, "BaseSkill"] = {}
        self.components: dict[str, BaseMachineryItem] = {}
        self.methods: dict[str,"BaseMethod"] = {}
        self.resources: dict[str, "BaseResource"] = {}
        self.ua_parameter_set_nodes = {}

        self._current_state: MachineryItemStates = INITIAL_STATE
        self._current_operation_mode: MachineryOperationModes = INITIAL_OPERATION_MODE
        self._ua_state_machine_current_state = None
        self._ua_operation_mode_current_state = None

        self._handle_status_change_task = None

    async def _init_identification(self, *,
                                   manufacturer: str | None = None,
                                   serial_number: str | None = None,
                                   product_instance_uri: str | None = None) -> None:
        await super()._init_identification()

        if manufacturer is None:
            manufacturer = "Technologie-Initiative SmartFactory KL e. V."

        ua_manufacturer = await self.ua_identification_folder.get_child(f"{UaTypes.ns_di}:Manufacturer")
        await ua_manufacturer.write_value(ua.LocalizedText(manufacturer, "en-US"))
        self.ua_identification_nodes["Manufacturer"] = ua_manufacturer

        ua_serial_number = await self.ua_identification_folder.get_child(f"{UaTypes.ns_di}:SerialNumber")
        await ua_serial_number.write_value(self._id if serial_number is None else serial_number)
        self.ua_identification_nodes["SerialNumber"] = ua_serial_number

        if (await self._ua_node.read_type_definition()).to_string() == UaTypes.module_type.nodeid.to_string():
            ua_product_instance_id = await self.ua_identification_folder.get_child(f"{UaTypes.ns_di}:ProductInstanceUri")
            await ua_product_instance_id.write_value(f"urn:smartfactory.de-model:snr-{await ua_serial_number.read_value()}"
                                if product_instance_uri is None else product_instance_uri)
            self.ua_identification_nodes["ProductInstanceUri"] = ua_product_instance_id

        # TODO verify influence on start up
        # depending on instantiation much clutter nodes ...
        for child in await self.ua_identification_folder.get_children():
            if ((child.nodeid.Identifier.endswith("ProductInstanceUri") and
                    (await self._ua_node.read_type_definition()).to_string() != UaTypes.module_type.nodeid.to_string())
                    or not child.nodeid.Identifier.endswith(
                    ("AssetId", "ComponentName", "SerialNumber", "Manufacturer", "ProductInstanceUri"))):
                await child.delete()

    @create_missing_objects("ParameterSet", "functional_group_type", "ns_di")
    async def _init_parameter_set(self) -> None:
        self.ua_parameter_set = await self.ua_node.get_child(f"{UaTypes.ns_di}:ParameterSet")
        await self._add_nodes_to_map(self.ua_parameter_set, self.ua_parameter_set_nodes)

    async def add_parameter_variable(self, name: str | QualifiedName,
                                     val: Any,
                                     *,
                                     varianttype: VariantType | None = None,
                                     datatype: NodeId | int | None = None,
                                     historize: bool = False,
                                     unit: str | int | None = None,
                                     _range: tuple[float, float] | None = None,
                                     instantiate: bool = True) -> Node:
        """ Creates a new OPC UA node in the parameter set folder with the given parameters. """

        _ua_parameter_node: Node = await self._add_variable(name, val, "ua_parameter_set", self._init_parameter_set, self.ua_parameter_set_nodes,
                                  varianttype=varianttype, datatype=datatype, historize=historize, unit=unit,
                                  _range=_range, instantiate=instantiate)

        await _ua_parameter_node.set_writable(True)
        return _ua_parameter_node

    @create_missing_objects("Components", "components_type", "ns_machinery")
    async def _init_components(self) -> None:
        self.ua_components = await self.ua_node.get_child(f"{UaTypes.ns_machinery}:Components")
        # remove wrongly instantiated placeholders
        for child in await self.ua_components.get_children():
            identifier = cast(str, child.nodeid.Identifier).lower()
            if identifier.endswith("<no>") or identifier.endswith("<component>"):
                await child.delete()  # not recursive to improve start up

    async def add_component(self, _id: str,
                            name: str,
                            component_type: Type[T],
                            spatial_object: SpatialObject | None = None,
                            object_type: Node | None = None,
                            **kwargs) -> T:
        """
        Creates a new instance of given component type, initializes  it and keeps track of it.
        Results the initialized component.
        """

        if not hasattr(self, "ua_components"):
            await self._init_components()

        start_time = time.monotonic()

        component: T = component_type(server=self.server, parent=self, ns_idx=self.ns_idx, _id=_id, name=name,
                                   config=self.config, spatial_object=spatial_object, **kwargs)
        await component.init(self.ua_components, object_type)
        await component._delete_empty_folders()  # TODO component should do this own its own...

        self.components[component.name] = component
        self.logger.info("Added sub-component", sub_component=component.name, elapsed=time.monotonic() - start_time)
        return component

    async def add_port(self, _id: str, port_number: int, component_type: Type[P],
                       spatial_object: SpatialObject | None = None, object_type: Node | None = None, **kwargs) -> P:
        return await self.add_component(_id=_id, name=f"Port_{port_number}", component_type=component_type,
                                        spatial_object=spatial_object, object_type=object_type, **kwargs)

    @create_missing_objects("Notification", "notification_type", "ns_machine_set")
    async def _init_notification(self) -> None:
        try:
            self.ua_notification = await self.ua_node.get_child(f"{UaTypes.ns_machine_set}:Notification")
            ua_messages = await self.ua_notification.get_child(f"{UaTypes.ns_machine_set}:Messages")
        except BadNoMatch:
            # it may be possible what node id is already chosen, therefore search for alternative bname
            # TODO little bit tricky since some specs have also messages type
            self.ua_notification = await get_child_without_ns(self.ua_node, "Notification")
            ua_messages = await add_object(ns_idx=self.ns_idx, location=self.ua_notification,
                                           bname=ua.QualifiedName("Messages", UaTypes.ns_machine_set),
                                           object_tyoe=UaTypes.messages_type)

        # TODO is seems 'generates_event' non-hierachical gets los during xml-import, therefore access event types
        self.ua_error_code, self.ua_info_text, self.ua_severity, self.ua_info_event_gen, self.ua_alarm_event_gen\
            = await asyncio.gather(
                ua_messages.get_child(f"{UaTypes.ns_machine_set}:LastErrorCode"),
                ua_messages.get_child(f"{UaTypes.ns_machine_set}:LastText"),
                ua_messages.get_child(f"{UaTypes.ns_machine_set}:LastSeverity"),
                self.server.get_event_generator(UaTypes.base_event, ua_messages),
                self.server.get_event_generator(UaTypes.alert_event, ua_messages)
            )

        await self.set_message_info(0, "", "")  # init data and types

        await self.server.historize_node_data_change(
            [self.ua_error_code, self.ua_info_text, self.ua_severity],
            count=1000)
        # await self.server.historize_node_event(ua_messages, count=1000)
        # TODO event history does not work, throws exceptions in asyncua

    async def set_message_info(self, severity: int, text: str, code: str = "") -> None:
        """
        Sets the diagnostic message info OPC-UA nodes to the given code and text.

        :param severity: OPC UA-specific message code
            -> based on OPC UA device integration spec. (levels between 0 and 1000)
        :param text: Human-readable text of the message
        :param code: Module-specific error code
        """

        try:
            await asyncio.gather(
                self.ua_severity.write_value(severity, ua.VariantType.UInt16),
                self.ua_info_text.write_value(ua.LocalizedText(text, "en-US")),
                self.ua_error_code.write_value(code, ua.VariantType.String)
            )
        except AttributeError:
            # may be optional for components
            pass  # TODO @SiJu evaluate design decision

    async def generate_info_event(self, text: str, severity: int = 0) -> None:
        self.logger.debug("Generating info event", text=text, severity=severity)

        self.ua_info_event_gen.event.Severity = severity
        self.ua_info_event_gen.event.Message = ua.LocalizedText(text)
        await self.ua_info_event_gen.trigger()

    async def generate_alert_event(self, text: str, severity: int = 0, code: str = "") -> None:
        self.logger.debug("Generating alert event", text=text, severity=severity, code=code)

        self.ua_alarm_event_gen.event.Severity = severity
        # TODO remove work-around when no longer required
        self.ua_alarm_event_gen.event.Message = ua.LocalizedText(f"{text}|||{code}")
        self.ua_alarm_event_gen.event.ErrorCode = code
        await self.ua_alarm_event_gen.trigger()

    async def _log_external(self, event_method: Callable[[str, int, Optional[str]], Awaitable[None]], **kwargs) -> None:
        # Check for the 'ua_notification' attribute
        if not hasattr(self, "ua_notification"):
            return

        await self.set_message_info(**kwargs)
        await event_method(**kwargs)

    async def _log_info(self, text: str, severity: int = 0) -> None:
        self.logger.info("OPC UA message", text=text, severity=severity)
        await self._log_external(self.generate_info_event, text=text, severity=severity)

    async def _log_warning(self, text: str, severity: int = 555) -> None:
        self.logger.warning("OPC UA message", text=text, severity=severity)
        await self._log_external(self.generate_info_event, text=text, severity=severity)

    async def _log_error(self, text: str, severity: int = 999, code: str = "") -> None:
        self.logger.error("OPC UA message", text=text, severity=severity, code=code)
        await self._log_external(self.generate_alert_event, text=text, severity=severity, code=code)

    @create_missing_objects("Resources", "resources_type", "ns_machine_set")
    async def _init_resources(self) -> None:
        self.ua_resources_folder = await self.ua_node.get_child(f"{UaTypes.ns_machine_set}:Resources")

    async def add_resource(self, resource: R | Type[R], **kwargs) -> R:
        """ Adds the given resource class or instance to the resources of this machinery item. """
        if isinstance(resource, type(BaseResource)):  # given a class, instantiate etc. ourselves
            resource = resource(**kwargs)
        elif not isinstance(resource, BaseResource):
            raise TypeError(f"Given resource '{resource}' is not a valid resource!")

        await resource.add_resource_object(self.ua_resources_folder, self.ns_idx)
        self.resources[resource.component_name] = resource
        return resource  # type: ignore

    async def _init_status(self, handle_status_change: bool = True) -> None:
        """
        :param handle_status_change: maps skill states to machinery item state,
            for some specifications there is a defined mapping, and we don't want to activate the loop.
        """
        try:
            self.ua_machinery_building_blocks = await self.ua_node.get_child(
                f"{UaTypes.ns_machinery}:MachineryBuildingBlocks"
            )

            self.ua_state_machine = await self.ua_machinery_building_blocks.get_child(
                f"{UaTypes.ns_machinery}:MachineryItemState")
            self.ua_operation_mode = await self.ua_machinery_building_blocks.get_child(
                f"{UaTypes.ns_machinery}:MachineryOperationMode")

            self._ua_state_machine_current_state = await self.ua_state_machine.get_child("CurrentState")
            self._ua_operation_mode_current_state = await self.ua_operation_mode.get_child("CurrentState")

            # Set the current state and operation mode (also in OPC UA)
            await self.set_current_state(INITIAL_STATE)
            await self.set_current_operation_mode(INITIAL_OPERATION_MODE)

            if handle_status_change:
                self._handle_status_change_task = asyncio.create_task(
                    self._handle_status_changes(), name=f"{self.name}_handle_status_changes")
        except BadNoMatch:
            self.logger.debug("No machinery state machine found.")

    @property
    def current_state(self) -> MachineryItemStates:
        return self._current_state

    @property
    def current_operation_mode(self) -> MachineryOperationModes:
        return self._current_operation_mode

    async def set_current_state(self, state: MachineryItemStates) -> None:
        """Set the current state of this machinery item without any logic checks. """
        if not isinstance(state, MachineryItemStates):
            try:
                name = state.name
            except AttributeError:
                name = ""
            raise TypeError(f"Given state '{name}' is not of type MachineryItemStates!")

        self._current_state = state
        state_name = _get_proper_state_name(state)
        await write_optional(self._ua_state_machine_current_state, ua.LocalizedText(state_name, "en-US"))

    async def set_current_operation_mode(self, mode: MachineryOperationModes) -> None:
        """Set the current operation mode of this machinery item without any logic checks."""
        if not isinstance(mode, MachineryOperationModes):
            raise TypeError(f"Given mode '{mode}' is not of type MachineryOperationModes!")

        self._current_operation_mode = mode
        mode_name = _get_proper_state_name(mode)
        await write_optional(self._ua_operation_mode_current_state, ua.LocalizedText(mode_name, "en-US"))


    @create_missing_objects("MethodSet", "method_set_type", "ns_skill_set")
    async def _init_methods(self) -> None:
        """ Initializes the method set folder of the asset """

        self.ua_methods_folder = await self.ua_node.get_child(f"{UaTypes.ns_skill_set}:MethodSet")
        # the node set contains some placeholders that need to be removed
        for placeholder_method in await self.ua_methods_folder.get_children():
            self.logger.info("Deleting placeholder node", node=placeholder_method.nodeid.Identifier)
            await placeholder_method.delete(recursive=True)
    
    #################
    
    
    @create_missing_objects("SkillSet", "skill_set_type", "ns_skill_set")
    async def _init_skills(self) -> None:
        """ Initializes the skill set folder of the asset. """

        self.ua_skills_folder = await self.ua_node.get_child(f"{UaTypes.ns_skill_set}:SkillSet")
        # the node set contains some placeholders that need to be removed
        for placeholder_skill in await self.ua_skills_folder.get_children():
            self.logger.info("Deleting placeholder node", node=placeholder_skill.nodeid.Identifier)
            await placeholder_skill.delete(recursive=True)

    # TODO @SiJu why? this is API is too error prone compared to add skills one by one -CaHa
    @deprecated("Please add your skills one-by-one instead with add_skill()!")
    async def add_skills(self, skills: List[BaseSkill | Type[BaseSkill]] | None  = None,
                         skill_kwargs: List[Dict[str, Any]] | None = None) -> None:
        if skills is not None:
            for n, skill in enumerate(skills):
                if skill_kwargs is not None and len(skill_kwargs) > n:
                    await self.add_skill(**skill_kwargs[n], skill=skill)
                else:
                    await self.add_skill(skill=skill)

    async def add_skill(self, skill: S | Type[S],
                        enable_historizing: bool = True,
                        folder: Node | None = None,
                        **kwargs) -> S:
        """ Adds the given skill to the asset.

        :param skill: can either be an instance, which is expected to be initialized. Or a class, which will be used to
            instantiate a new object using the given class and additional keyword parameters.
        :param enable_historizing: enables historizing on the given skill
        :param folder: OPC UA folder node where the skill should be placed. Usually the module skill set folder or
            component skill set folders. Only used when instantiating a skill.
        :param kwargs: keyword arguments given to __init()__ of new instance
        """
        start_time = time.monotonic()

        if not hasattr(self, "ua_skills_folder"):
            await self._init_skills()

        if not hasattr(self, "ua_notification"):
            await self._init_notification()  # skills use from default notifications

        if isinstance(skill, type(BaseSkill)):  # given a class, instantiate etc. ourselves
            self.logger.debug("Instantiating new skill", skill=skill, kwargs=kwargs)
            skill = skill(**kwargs, machinery_item=self)

        try:  # TODO @SiJu: Why do we need to check this?
            # check if skill has machine otherwise initialize skill
            _ = skill.machine
        except AttributeError:
            await skill.init(folder or self.ua_skills_folder)

        self.skills[skill.name] = skill
        if enable_historizing:
            await skill.enable_historizing(self.server)

        self.logger.info("Added skill", skill=skill.name, elapsed=time.monotonic() - start_time)
        return skill

    
    async def add_method(self, method: M | Type[M],
                         folder: Node | None = None,
                         **kwargs) -> M:
        """ Adds the given method to the asset.

        :param method: can either be an instance, which is expected to be initialized. Or a class, which will be used to
            instantiate a new object using the given class and additional keyword parameters.
        :param folder: OPC UA folder node where the skill should be placed. Usually the module skill set folder or
            component skill set folders. Only used when instantiating a skill.
        :param kwargs: keyword arguments given to __init()__ of new instance
        """
        start_time = time.monotonic()

        if not hasattr(self, "ua_methods_folder"):
            await self._init_methods()

        if not hasattr(self, "ua_notification"):
            await self._init_notification()  

        if isinstance(method, type(BaseMethod)):  # given a class, instantiate etc. ourselves
            self.logger.debug("Instantiating new method", method=method, kwargs=kwargs)
            method = method(**kwargs, machinery_item=self)

            await method.init(folder or self.ua_methods_folder)
        
        self.methods[method.name] = method  # type: ignore

        self.logger.info("Added method", method=method.name, elapsed=time.monotonic() - start_time)
        return method  # type: ignore

    # TODO @SiJu why? this is API is too error prone compared to add methods one by one -CaHa
    @deprecated("Please add your methods one-by-one instead with add_method()!")
    async def add_methods(self, methods: List[M | Type[M]] | None = None,
                         method_kwargs: List[Dict[str, Any]] | None = None) -> None:
        if methods is not None:
            for n, method in enumerate(methods):
                if method_kwargs is not None and len(method_kwargs) > n:
                    await self.add_method(**method_kwargs[n], method=method)
                else:
                    await self.add_method(method=method)

    #####################################
    # FSM Conditions

    # Raise UaStatusCodeError for correct OPC-UA status code answers instead of a misc one

    async def _condition_access_allowed(self, user: User) -> bool:
        # go up in the chain until we reach our module
        return await self._parent._condition_access_allowed(user)

    async def _condition_startup_completed(self, _user: User) -> bool:
        try:
            if self.startup_skill.current_state != SkillStates.Running:
                await self._log_error(f"Denied, skill '{self.startup_skill.full_name}' must be running!")
                raise ua.UaStatusCodeError(ua.StatusCodes.BadInvalidState)
            return True  # has the StartupSkill and it is running
        except KeyError:
            return True  # has no StartupSkill -> always ready

    async def _condition_component_ready(self, user: User) -> bool:
        return True  # To implement custom checks that depend on the component

    async def reset(self) -> None:
        """ Attempts to reset the base machinery item (if the state indicates resetting is required. Is safe to call
        when the machinery item is most states. If it is in state `NotAvailable`, an error will be raised.

        If a "Startup" skill for this machinery item exists, reset is expected to be performed by the startup skill.
        If there is no "Startup" skill, then reset all skills and subcomponents.
        """
        match self._current_state:
            case MachineryItemStates.Executing | MachineryItemStates.NotExecuting:
                self.logger.debug("Skipping reset() of machinery item", state=self._current_state.name)
                return
            case MachineryItemStates.OutOfService:
                try:
                    startup_skill = self.startup_skill
                    self.logger.debug("Resetting with startup skill")
                    await self.reset_skills([startup_skill])  # make sure the startup skill is ready
                    if startup_skill.current_state == SkillStates.Ready:
                        await startup_skill.start()
                        await startup_skill.wait_for_state(SkillStates.Running)
                    else:
                        self.logger.debug("Startup skill is already in target state", state=startup_skill.current_state.name)
                except KeyError:  # no startup skill found
                    self.logger.debug("Resetting without startup skill")
                    await self.reset_components()
                    await self.reset_skills()
            case _:
                raise RuntimeError(
                    f"Cannot reset machinery item '{self.full_name}' from state='{self._current_state.name}'!"
                )


    async def reset_components(self, components: dict[str, BaseMachineryItem] | None = None) -> None:
        """Reset given components. If None given, resets all own components."""
        if components is None:
            components = self.components

        for component in components.values():
            await component.reset()


    async def reset_skills(self, skills: dict[str, BaseSkill] | Iterable[BaseSkill] | None = None) -> None:
        """Reset all given skills. If None given, resets all own skills."""
        if skills is None:
            skills = self.skills.values()
        elif isinstance(skills, dict):
            skills = skills.values()

        try:
            await reset_skills_parallel_and_wait(skills)
        except Exception as ex:
            await self._log_error("Error resetting skills!", 666)
            await self.set_current_state(MachineryItemStates.OutOfService)
            raise ua.UaStatusCodeError(ua.StatusCodes.BadInvalidState) from ex

    async def halt_components(
        self, components_to_halt: Iterable[str] | Iterable[BaseMachineryItem] | None = None
    ) -> None:
        """Halt all components (None, default) of this machinery item or only specific ones.

        :param components_to_halt: All components or only specific ones. Note: components by name will only be searched
            for in this machinery item!
        """
        for component_name, component in self.components.items():  # halt all requested components
            if (components_to_halt is not None
                    and (component_name not in components_to_halt or component not in components_to_halt)):
                self.logger.debug("Skipping halting component, because it should not be halted.",
                                  component_name=component.full_name)
                continue
            elif component_name.lower().startswith("port_"):
                self.logger.debug("Skipping halting component, because it is a port.",
                                  component_name=component.full_name)
                continue

            try:
                await component.halt(components_to_halt=components_to_halt)
            except Exception:
                await self._log_error(f"Could not halt component '{component.full_name}'!")
                traceback.print_exc()

    async def halt_skills(self, skills_to_halt: Iterable[str] | Iterable[BaseSkill] | None = None) -> None:
        """ Halt all skills (None, default) of this machinery item or only specific ones.

        :param skills_to_halt: All skills (None, default) or only specific skills. Note: skills by name will only be
            searched for in this machinery item!
        """
        if skills_to_halt is None:  # halt all own skills
            await halt_skills_parallel_and_wait(self.skills.values())
        else:  # halt only specific skills
            new_skills_to_halt: list[BaseSkill] = []
            for skill in skills_to_halt:  # convert str into BaseSkill instances
                if isinstance(skill, str):
                    try:
                        new_skills_to_halt.append(self.skills[skill])
                    except KeyError:
                        self.logger.warning("Could not find skill in own skill set!", skill_name=skill)
                elif isinstance(skill, BaseSkill):
                    new_skills_to_halt.append(skill)

            await halt_skills_parallel_and_wait(new_skills_to_halt)


    async def halt(self, *,
                   components_to_halt: Iterable[str] | Iterable[BaseMachineryItem] | None = None,
                   skills_to_halt: Iterable[str] | Iterable[BaseSkill] | None = None) -> None:
        """
        Halt the machinery item.

        If a "Startup" skill for this machinery item exists, halt is expected to be performed by the startup skill.
        Otherwise, halt all/no skills and all/no subcomponents.

        Note: The startup skill should not simply call this method, it will not halt anything!

        :param components_to_halt: Whether to halt all subcomponents (except Ports) (None, default) or specified ones.
        :param skills_to_halt: Whether to halt all skills (None, default) or specified ones.
        """
        await self.set_current_state(MachineryItemStates.OutOfService)
        await self.set_current_operation_mode(MachineryOperationModes.Maintenance)

        try:
            startup_skill = self.startup_skill
            self.logger.debug("Halting with startup skill")
            await halt_skills_parallel_and_wait([startup_skill])
        except KeyError:  # no startup skill
            self.logger.debug("Halting without startup skill",
                              components_to_halt=components_to_halt, skills_to_halt=skills_to_halt)
            if components_to_halt:
                await self.halt_components(components_to_halt)
            if skills_to_halt:
                await self.halt_skills(skills_to_halt)


    async def _handle_status_changes(self) -> None:
        """ Handles automatic status changes according to the skill states (see specification for V4). """

        # grab our StartupSkill (possible wait for it to be added)
        while True:
            try:
                await asyncio.sleep(.5)
                startup_skill = self.startup_skill
                break
            except KeyError:  # skill set may not be initialized
                self.logger.debug("Waiting for StartupSkill to be initialized!")

        while True:
            await asyncio.sleep(.5)

            # our state machines are dependent of the startup skill state
            if startup_skill.current_state != SkillStates.Running:
                await self.set_current_state(MachineryItemStates.OutOfService)
                continue
            # else:
            # we only consider finite skills
            skill_stats = [skill.current_state for skill in self.skills.values() if skill.is_finite]

            # there is at least 1 skill running/suspended
            if (skill_stats.count(SkillStates.Running) > 0
                    or skill_stats.count(SkillStates.Suspended) > 0):
                await self.set_current_state(MachineryItemStates.Executing)
                await self.set_current_operation_mode(MachineryOperationModes.Processing)
            else:
                await self.set_current_state(MachineryItemStates.NotExecuting)
                await self.set_current_operation_mode(MachineryOperationModes.Setup)


    async def _delete_empty_folders(self, parent: Node | None = None):
        await super()._delete_empty_folders(parent)

        skills_to_delete: List[Coroutine] = []
        if parent is None or parent == self.ua_node:
            for _name, skill in self.skills.items():
                skills_to_delete.append(skill._delete_empty_folders())
        await asyncio.gather(*skills_to_delete)


    async def shutdown(self) -> None:
        self.logger.debug("Shutdown started...")
        for component in self.components.values():
            try:
                await component.shutdown()
            except Exception as ex:  # We don't know what might go wrong, catch all just in case
                traceback.print_exc()
                self.logger.exception(ex)
                self.logger.error("Exception was raised while calling shutdown()", sub_component=component.name)
        self.logger.info("Shutdown completed.")


    @property
    def startup_skill(self) -> BaseSkill:
        """ Returns the startup skill if it exists or raise a KeyError if it does not exist."""
        return self.skills[BaseStartupSkill.NAME]
