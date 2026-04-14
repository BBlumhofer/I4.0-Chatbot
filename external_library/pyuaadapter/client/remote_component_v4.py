from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node, ua
from asyncua.ua.uaerrors import BadNoMatch
from typing_extensions import override

from pyuaadapter.client.base_remote_component import BaseRemoteComponent
from pyuaadapter.client.remote_method_v4 import RemoteMethod
from pyuaadapter.client.remote_resource_v4 import RemoteResource
from pyuaadapter.client.remote_variable import add_variable_nodes
from pyuaadapter.common import get_type_definition
from pyuaadapter.common.namespace_uri import NS_DI_URI, NS_MACHINE_SET_URI, NS_MACHINERY_URI, NS_SKILL_SET_URI
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer

class RemoteComponent(BaseRemoteComponent):
    """ Represents a remote component using the skill v4 node set. """

    _ua_messages: Node

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server)

        self.logger = structlog.getLogger("sf.client.RemoteComponent", name=name, type=self.type)

        self._skill_ns_idx = self._remote_server.namespace_map[NS_SKILL_SET_URI]

        self.method_set: dict[str, "RemoteMethod"] = {}
        self.resources: dict[str, "RemoteResource"] = {}

    @override
    def dto(self) -> dict[str, Any]:
        ret = super().dto()
        ret["method_set"] = [m.dto() for m in self.method_set.values()]
        ret["resources"] = [r.dto() for r in self.resources.values()]
        return ret


    async def _setup_lock(self, ua_lock_node: Node, subscription_manager: SubscriptionManager):
        from pyuaadapter.client.remote_lock import RemoteLock

        self.lock = RemoteLock(node=ua_lock_node, remote_server=self._remote_server,
            ns_idx_sfm=self._remote_server.namespace_map[NS_DI_URI])
        await self.lock.setup_subscriptions(subscription_manager)

    @override
    async def _instantiate_skill(self, name: str, base_node: Node):
        from pyuaadapter.client.remote_skill_v4 import RemoteSkill
        return RemoteSkill(name, base_node, self._remote_server)

    async def _setup_notification(self, ua_notification: Node, subscription_manager: SubscriptionManager):
        self._ua_messages = await ua_notification.get_child(
            f"{self._remote_server.namespace_map[NS_MACHINE_SET_URI]}:Messages")

        await subscription_manager.subscribe_event(self, self._ua_messages)

    async def _setup_components(self, ua_components: Node, subscription_manager: SubscriptionManager):
        from pyuaadapter.client.remote_port_v4 import RemotePort
        from pyuaadapter.client.remote_storage_slot_v4 import RemoteStorageSlot
        from pyuaadapter.client.remote_storage_v4 import RemoteStorage

        for ua_component_node in await ua_components.get_children():
            name = (await ua_component_node.read_browse_name()).Name
            self.logger.info("Processing sub-component...", component_bname=name)
            try:
                class_map = {
                    "PortType": RemotePort,
                    "StorageType": RemoteStorage,
                    "StorageSlotType": RemoteStorageSlot
                }
                type_definition = await get_type_definition(ua_component_node)

                component_class = class_map.get(type_definition, RemoteComponent)
                self.components[name] = component_class(name=name,
                                                        base_node=ua_component_node,
                                                        remote_server=self._remote_server)

                await self.components[name].setup_subscriptions(subscription_manager)
            except RuntimeError as err:  # TODO proper custom exception
                self.logger.warning(err)

    async def _setup_resources(self, ua_resources: Node, subscription_manager: SubscriptionManager):
        resource_nodes = await ua_resources.get_children()
        bname_data_values = await self._remote_server.ua_client.read_attributes(resource_nodes, ua.AttributeIds.BrowseName)
        for resource_node, bname_data_value in zip(resource_nodes, bname_data_values):
            # Variant -> QualifiedName
            resource_name = bname_data_value.Value.Value.Name   # type: ignore
            self.logger.info("Processing resource...", resource_name=resource_name)
            try:
                self.resources[resource_name] = RemoteResource(
                    name=resource_name, base_node=resource_node, remote_server=self._remote_server)
                await self.resources[resource_name].setup_subscriptions(subscription_manager)
            except RuntimeError as err:  # TODO proper custom exception
                self.logger.warning(err)

    async def _process_machinery_building_blocks(self, node: Node, subscription_manager: SubscriptionManager) -> None:
        await self._setup_state_machine(node, subscription_manager)

    async def _setup_state_machine(self, node: Node, subscription_manager: SubscriptionManager):
        try:
            # expects a MachineryBuildingBlocks node
            self._ua_state_machine_node = await node.get_child(
                f"{self._remote_server.namespace_map[NS_MACHINERY_URI]}:MachineryItemState")
            self._ua_current_state = await self._ua_state_machine_node.get_child("CurrentState")  # no namespace index
            await subscription_manager.subscribe_data_change(handler=self, nodes=self._ua_current_state)
        except BadNoMatch as err:
            self.logger.exception(err)

    async def _setup_methods(self, ua_method_set_node: Node, subscription_manager: SubscriptionManager):
        self._ua_method_set_node = ua_method_set_node

        for ua_method_base_node in await ua_method_set_node.get_children():
            name = (await ua_method_base_node.read_browse_name()).Name
            self.logger.info("Processing method...", method_bname=name)

            if name not in self.method_set:
                self.method_set[name] = RemoteMethod(name, ua_method_base_node, self._remote_server)
            await self.method_set[name].setup_subscriptions(subscription_manager)

    @override
    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:  # noqa: C901
        """ Sets up all subscriptions for all subcomponents and itself. """
        ua_attributes: Node | None = None
        ua_monitoring: Node | None = None
        ua_parameter_set: Node | None = None

        children = await self._ua_node.get_children()
        bname_data_values = await self._remote_server.ua_client.read_attributes(children, ua.AttributeIds.BrowseName)
        for child, data_value in zip(children, bname_data_values):  # to avoid namespace issues
            #  Variant -> QualifiedName
            child_name = data_value.Value.Value.Name  # type: ignore
            if child_name == "Lock":
                await self._setup_lock(child, subscription_manager)
            elif child_name == "SkillSet":
                if self._remote_server.browse_skills:
                    await self._setup_skills(child, subscription_manager)
            elif child_name == "Monitoring":
                ua_monitoring = child
            elif child_name == "Notification":
                await self._setup_notification(child, subscription_manager)
            elif child_name == "Identification":
                if self._remote_server.browse_identification:
                    # TODO @SiJu shouldn't these be identification nodes etc. ?
                    await add_variable_nodes(child, self._attributes_nodes, self._attributes,
                                             is_writable=False, remote_server=self._remote_server)
            elif child_name == "Attributes":
                ua_attributes = child
            elif child_name == "ParameterSet":
                ua_parameter_set = child
            elif child_name == "Components":
                await self._setup_components(child, subscription_manager)
            elif child_name == "Resources":
                if self._remote_server.browse_resources:
                    await self._setup_resources(child, subscription_manager)
            elif child_name == "MachineryBuildingBlocks":
                await self._process_machinery_building_blocks(child, subscription_manager)
            elif child_name == "MethodSet":
                if self._remote_server.browse_methods:
                    await self._setup_methods(child, subscription_manager)
            else:
                self.logger.warning("Found unhandled child node!", node_id=child.nodeid.to_string())

        # Note: Monitoring needs to be parsed before ParameterSet in case of duplications due to colliding nodesets
        if ua_monitoring:
            await self._setup_monitoring_subscriptions(ua_monitoring, subscription_manager)
        if ua_parameter_set:
            await self._setup_parameter_subscriptions(ua_parameter_set, subscription_manager)
        if ua_attributes:
            await self._setup_attributes_subscriptions(ua_attributes, subscription_manager)


    async def event_notification(self, event) -> None:
        """Callback to handle "message" event notifications."""
        # TODO remove split when work-around no longer required
        text_splits: list[str] = event.Message.Text.split("|||", maxsplit=1)
        text = text_splits[0]
        try:
            error_code = event.ErrorCode  # TODO does not work for some reason @SiJu
        except AttributeError:
            try:
                error_code = text_splits[1]
            except IndexError:
                error_code = ''

        for sub in self._subscribers:
            if asyncio.iscoroutinefunction(sub.on_new_message):
                await sub.on_new_message(self, text=text, severity=event.Severity, code=error_code)
            else:
                sub.on_new_message(self, text=text, severity=event.Severity, code=error_code)