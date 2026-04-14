from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import LocalizedText
from asyncua.ua.uaerrors import BadNoMatch

from pyuaadapter.client.base_remote_skill import BaseRemoteSkill
from pyuaadapter.client.mixins.attributes_mixin import AttributesMixin, AttributeUpdateSubscriber
from pyuaadapter.client.mixins.monitoring_mixin import MonitoringMixin, MonitoringUpdateSubscriber
from pyuaadapter.client.mixins.parameter_mixin import ParameterMixin, ParameterUpdateSubscriber
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer


class RemoteComponentSubscriber(ParameterUpdateSubscriber, MonitoringUpdateSubscriber, AttributeUpdateSubscriber, ABC):
    """ Subscriber interface for RemoteComponent events. """

    def on_state_change(self, new_state: str) -> None:
        """ Is called whenever the state of the subscribed remote component is changed. """
        pass

    def on_new_message(self, component: 'BaseRemoteComponent', text: str, severity: int, code: str) -> None:
        pass


class BaseRemoteComponent(ParameterMixin, MonitoringMixin, AttributesMixin, ABC):
    """ Base class for remote components. """

    _name: str
    _skill_ns_idx: int = -1
    """ OPC UA namespace index containing the skills. """

    _ua_skill_set_node: Node

    _ua_node: Node
    _ua_state_machine_node: Node
    _ua_components: Node

    def __init__(self, name: str | LocalizedText, base_node: Node, remote_server: "RemoteServer"):
        super().__init__()
        self.name = name
        self._asset_id = None  # TODO
        self._ua_node = base_node
        self._remote_server = remote_server

        self.skill_set: dict[str, "BaseRemoteSkill"] = {}
        self.feasibility_check_set: dict[str, "BaseRemoteSkill"] = {}
        self.precondition_check_set: dict[str, "BaseRemoteSkill"] = {}
        self.components: dict[str, BaseRemoteComponent] = {}
        self._current_state: str | None = None

        self._subscribers: list[RemoteComponentSubscriber] = []  # type: ignore

        self._ua_current_state: Node | None = None


    def dto(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_id": self._ua_node.nodeid.to_string(),
            "type": self.type,
            "current_state": self.current_state,
            "skill_set": [s.dto() for s in self.skill_set.values()],
            "feasibility_check_set": [s.dto() for s in self.feasibility_check_set.values()],
            "precondition_check_set": [s.dto() for s in self.precondition_check_set.values()],
            "monitoring": [m.dto() for m in self.monitoring.values()],
            "attributes": [a.dto() for a in self.attributes.values()],
            "parameter_set": [p.dto() for p in self.parameter_set.values()],
            "components": [c.dto() for c in self.components.values()],
        }

    def add_subscriber(self, subscriber: RemoteComponentSubscriber) -> None:
        """ Adds given subscriber to the list of subscribers to be notified. """
        self._subscribers.append(subscriber)

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> bool:
        if await ParameterMixin.datachange_notification(self, node, val, data):
            return True
        if await MonitoringMixin.datachange_notification(self, node, val, data):
            return True
        if await AttributesMixin.datachange_notification(self, node, val, data):
            return True
        if self._ua_current_state is not None and node.nodeid == self._ua_current_state.nodeid:
            try:
                self._current_state = val.Text
            except AttributeError:
                # some servers use normal strings instead
                self._current_state = val if val is not None else ''

            for sub in self._subscribers:  # notify subscribers
                if asyncio.iscoroutinefunction(sub.on_state_change):
                    await sub.on_state_change(self._current_state)
                else:
                    sub.on_state_change(self._current_state)

            return True
        return False  # Let others know notification was not handled

    @property
    def asset_id(self):
        return self._asset_id

    @property
    def current_state(self) -> str:
        """ Current state of the remote component (may not be up-to-date due to subscription delay)"""
        return self._current_state

    @property
    def name(self) -> str:
        """ Returns the name of the remote module """
        return self._name

    @name.setter
    def name(self, value: str | LocalizedText):
        if isinstance(value, LocalizedText):
            self._name = str(value.Text)
        else:
            self._name = value

    @property
    def type(self) -> str:
        """ Human-readable component type (mainly for UI purposes). """
        return "Generic"

    @abstractmethod
    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _instantiate_skill(self, name: str, base_node: Node):
        raise NotImplementedError

    async def _setup_skills(self, ua_skill_set_node: Node, subscription_manager: SubscriptionManager):
        """ Iterates through all skills and instantiates RemoteSkill instances or updates them if they already exist. """
        self._ua_skill_set_node = ua_skill_set_node

        for ua_skill_base_node in await ua_skill_set_node.get_children():
            name = (await ua_skill_base_node.read_browse_name()).Name
            self.logger.info("Processing skill...", skill_bname=name)

            ua_execution_node = await ua_skill_base_node.get_child(f"{self._skill_ns_idx}:SkillExecution")  # mandatory
            if name not in self.skill_set:
                self.skill_set[name] = await self._instantiate_skill(name, ua_execution_node)
            await self.skill_set[name].setup_subscriptions(subscription_manager)

            try:
                ua_feasibility_node = await ua_skill_base_node.get_child(f"{self._skill_ns_idx}:FeasibilityCheck")
                if name not in self.feasibility_check_set:
                    self.logger.info("Adding feasibility check...", skill_name=name)
                    self.feasibility_check_set[name] = await self._instantiate_skill(name, ua_feasibility_node)
                await self.feasibility_check_set[name].setup_subscriptions(subscription_manager)
            except BadNoMatch:
                pass  # optional

            try:
                ua_precondition_node = await ua_skill_base_node.get_child(f"{self._skill_ns_idx}:PreconditionCheck")
                if name not in self.precondition_check_set:
                    self.logger.info("Adding precondition check...", skill_name=name)
                    self.precondition_check_set[name] = await self._instantiate_skill(name, ua_precondition_node)
                await self.precondition_check_set[name].setup_subscriptions(subscription_manager)
            except BadNoMatch:
                pass  # optional