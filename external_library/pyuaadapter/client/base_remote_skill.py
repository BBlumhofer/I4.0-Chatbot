from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import LocalizedText, NodeId
from asyncua.ua.uaerrors import BadNoMatch
from typing_extensions import override

from pyuaadapter.client.base_remote_callable import BaseRemoteCallable
from pyuaadapter.common.enums import SkillStates
from pyuaadapter.common.exceptions import SkillHaltedError, SkillNotSuspendableError
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer

class SkillTypes(IntEnum):
    """ Enum of possible Skill types. """
    Finite = 1
    Continuous = 2
    Unknown = -1


class BaseRemoteSkill(BaseRemoteCallable, ABC):
    _ua_state_machine_node: Node
    """ OPC UA node representing the state machine of the skill. """
    _ua_current_state: Node
    """ OPC UA node representing the current state of the skill. """

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server)

        self._current_state = SkillStates.Halted
        self._type = SkillTypes.Unknown
        self._depends_on: dict[NodeId, str] = {}
        self._dependency_of: dict[NodeId, str] = {}
        self._suspendable = False

        self.logger = structlog.get_logger("sf.client.RemoteSkill", skill_name=self.name)

    @override
    def dto(self) -> dict[str, Any]:
        ret = super().dto()
        ret.update(
            {
                "type": self.type.name,
                "current_state": self.current_state.name,
                "suspendable": self.suspendable,
                "depends_on": [n.to_string() for n in self.depends_on],  # node_ids
                "dependency_of": [n.to_string() for n in self.dependency_of],  # node_ids
            }
        )
        return ret

    def __str__(self):
        return f"RemoteSkill <{self.name} ({str(self._ua_base_node.nodeid)})>"

    @override
    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:
        self._ua_state_machine_node = await self._ua_base_node.get_child(f"{self._ns_idx_other}:StateMachine")
        self._ua_current_state = await self._ua_state_machine_node.get_child("CurrentState")  # no namespace index

        await super().setup_subscriptions(subscription_manager)
        await self._setup_type_and_dependencies()

        with contextlib.suppress(BadNoMatch):
            await self.ua_state_machine_node.get_child(f"{self._ns_idx_methods}:Suspend")
            self._suspendable = True

        await subscription_manager.subscribe_data_change(handler=self, nodes=[self._ua_current_state])
        self.logger.debug("Subscription setup completed!")

    @property
    def ua_state_machine_node(self) -> Node:
        return self._remote_server.ua_client.get_node(self._ua_state_machine_node.nodeid)

    @property
    def ua_current_state(self) -> Node:
        return self._remote_server.ua_client.get_node(self._ua_current_state.nodeid)

    @property
    def suspendable(self) -> bool:
        """ Indicates whether the skill is suspendable. """
        return self._suspendable

    @abstractmethod
    async def _get_dependency_reference_node_id(self) -> NodeId:
        pass

    async def get_parameter_resources(self, parameter_name: str) -> dict[NodeId, str]:
        # TODO no direct OPC UA # TODO: Problem modelling depenencies on skill level...
        """ Returns all referenced resources of a given parameter name. """
        ret = {}

        ua_reference_node: NodeId = await self._get_dependency_reference_node_id()

        for node in await self.ua_parameter_set.get_children():
            if (await node.read_browse_name()).Name == parameter_name:
                for ref in await node.get_references(refs=ua_reference_node):  # type: ignore
                    ret[ref.NodeId] = str(ref.DisplayName.Text)

        return ret  # type: ignore

    async def start(self, write_parameters: bool = False) -> None:
        """ Calls the start method on the remote skill. User is responsible for handling any errors. """
        if write_parameters:
            with contextlib.suppress(RuntimeError):
                await self.write_parameters(self.parameter_set)
        await self.ua_state_machine_node.call_method(f"{self._ns_idx_methods}:Start")

    async def reset(self) -> None:
        """ Calls the reset method on the remote skill. User is responsible for handling any errors. """
        await self.ua_state_machine_node.call_method(f"{self._ns_idx_methods}:Reset")

    async def halt(self) -> None:
        """ Calls the halt method on the remote skill. User is responsible for handling any errors. """
        await self.ua_state_machine_node.call_method(f"{self._ns_idx_methods}:Halt")

    async def suspend(self) -> None:
        """ Calls the suspend method on the remote skill. User is responsible for handling any errors. """
        try:
            await self.ua_state_machine_node.call_method(f"{self._ns_idx_methods}:Suspend")
        except BadNoMatch:
            raise SkillNotSuspendableError(f"Skill '{self.name}' is not suspendable!") from None

    async def wait_for_state(self, target_state: SkillStates, timeout: float | None = 60.0) -> None:
        """ Blocks until the skill either reached the given state or was halted. Given timeout is in seconds. """
        start_state = self.current_state

        async def _wait():
            while True:
                if self.current_state == target_state:
                    break
                elif self.current_state == SkillStates.Halted and start_state != SkillStates.Halted:
                    raise SkillHaltedError(f"Skill '{self.name}' halted while waiting for state '{target_state.name}'!")
                await asyncio.sleep(0.1)

        await asyncio.wait_for(_wait(), timeout)

    @abstractmethod
    async def _setup_type_and_dependencies(self):
        pass

    async def _handle_state_change(self, val: str | LocalizedText):
        try:
            state_str = val.Text  # type: ignore
        except AttributeError:
            # some servers ignore the node-set datatype specification and use normal strings instead...
            state_str = val

        try:
            # assume the worst/safest state
            self._current_state = SkillStates.Halted if state_str is None else SkillStates[state_str]

            for sub in self._subscribers:  # notify subscribers
                if asyncio.iscoroutinefunction(sub.on_skill_state_change):  # type: ignore
                    await sub.on_skill_state_change(self._current_state)  # type: ignore
                else:
                    sub.on_skill_state_change(self._current_state)  # type: ignore

        except KeyError:  #
            self.logger.warning("Received unknown state, ignoring!", state_str=state_str)

    @override
    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:  # type: ignore
        """ OPC UA callback when the data of a node subscription changed. """
        self.logger.debug("Processing data change notification", node=node.nodeid.to_string(), new_value=val)
        try:
            if node.nodeid == self._ua_current_state.nodeid:
                await self._handle_state_change(val)
            else:
                await super().datachange_notification(node, val, data)
        except AttributeError as err:
            self.logger.warning(err, node=node.nodeid.to_string(), new_value=val)

    @property
    def current_state(self) -> SkillStates:
        """ Current state of the remote module."""
        return self._current_state

    @property
    def type(self) -> SkillTypes:
        return self._type

    @property
    def depends_on(self) -> dict[NodeId, str] :
        return self._depends_on

    @property
    def dependency_of(self) -> dict[NodeId, str] :
        return self._dependency_of
