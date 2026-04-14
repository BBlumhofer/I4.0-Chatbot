from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from asyncua import Node
from asyncua.ua import UaStatusCodeError
from typing_extensions import override

from pyuaadapter.client.base_remote_component import BaseRemoteComponent
from pyuaadapter.common import get_type_definition
from pyuaadapter.common.namespace_uri import NS_SFM_V3_URI
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer


class RemoteComponent(BaseRemoteComponent):
    """ Represents a remote component using the skill v3 node set. """

    _ua_last_error_text: Node
    _ua_last_message_text: Node

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server=remote_server)

        self._ua_last_error_text = None
        self._ua_last_message_text = None

        self.last_error_text = ""
        self.last_message_text = ""

        self._skill_ns_idx = self._remote_server.namespace_map[NS_SFM_V3_URI]

    async def _setup_lock(self, ua_lock_node: Node, subscription_manager: SubscriptionManager):
        from pyuaadapter.client.remote_lock import RemoteLock

        self.lock = RemoteLock(node=ua_lock_node, remote_server=self._remote_server,
                               ns_idx_sfm=self._remote_server.namespace_map[NS_SFM_V3_URI])
        await self.lock.setup_subscriptions(subscription_manager)

    @override
    async def _instantiate_skill(self, name: str, base_node: Node):
        from pyuaadapter.client.remote_skill_v3 import RemoteSkill
        return RemoteSkill(name, base_node, self._remote_server)

    async def _setup_components(self, ua_components: Node, subscription_manager: SubscriptionManager):
        from pyuaadapter.client.remote_port_v3 import RemotePort

        for ua_component_node in await ua_components.get_children():
            name = (await ua_component_node.read_browse_name()).Name
            if await get_type_definition(ua_component_node) == "PortType":
                self.components[name] = RemotePort(name, ua_component_node, self._remote_server)
            else:
                self.components[name] = RemoteComponent(name, ua_component_node, self._remote_server)

            await self.components[name].setup_subscriptions(subscription_manager)

    async def _setup_state_machine(self, ua_state_machine: Node):
        self._ua_state_machine_node = ua_state_machine
        self._ua_current_state = await ua_state_machine.get_child("CurrentState")  # no namespace index

    async def _setup_subscriptions(self, subscription_manager: SubscriptionManager):

        nodes = [n for n in [self._ua_current_state,
                             self._ua_last_error_text,  # Note: these should come from monitoring setup
                             self._ua_last_message_text] if n is not None]
        if len(nodes) > 0:
            await subscription_manager.subscribe_data_change(handler=self, nodes=nodes)

    @override
    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:  # noqa: C901
        """ Sets up all subscriptions for all subcomponents and itself. """
        for child in await self._ua_node.get_children():  # to avoid namespace issues
            child_name = (await child.read_browse_name()).Name
            if child_name == "Lock":
                await self._setup_lock(child, subscription_manager)
            elif child_name == "SkillSet":
                if self._remote_server.browse_skills:
                    await self._setup_skills(child, subscription_manager)
            elif child_name == "Monitoring":
                await self._setup_monitoring_subscriptions(child, subscription_manager)
            elif child_name == "ParameterSet":
                await self._setup_parameter_subscriptions(child, subscription_manager)
            elif child_name == "Components":
                await self._setup_components(child, subscription_manager)
            elif child_name == "StateMachine":
                await self._setup_state_machine(child)
            elif child_name == "ComponentName":
                try:
                    name = await child.read_value()
                    if name is not None:
                        self.name = name
                except UaStatusCodeError as err:
                    self.logger.warning(f"Could not read ComponentName: {err}")
            elif child_name == "AssetId":
                try:
                    asset_id = await child.read_value()
                    if asset_id is not None:
                        self._asset_id = asset_id
                except UaStatusCodeError as err:
                    self.logger.warning(f"Could not read ComponentName: {err}")
            else:
                self.logger.warning("Found unhandled child node!", node_id=child.nodeid.to_string())

        await self._setup_subscriptions(subscription_manager)  # this MUST be the last step

    async def reset(self) -> None:
        """ Resets the remote component. """
        await self._ua_state_machine_node.call_method(f"{self._remote_server.namespace_map[NS_SFM_V3_URI]}:Reset")

    async def halt(self) -> None:
        """ Halts the remote component. """
        await self._ua_state_machine_node.call_method(f"{self._remote_server.namespace_map[NS_SFM_V3_URI]}:Halt")

    async def datachange_notification(self, node: Node, val, data) -> None:
        if await super().datachange_notification(node, val, data):
            return  # already handled
        elif node.nodeid == self._ua_last_error_text.nodeid and val.Text is not None:
            self.last_error_text = val.Text
            for sub in self._subscribers:
                if asyncio.iscoroutinefunction(sub.on_new_message):
                    await sub.on_new_message(self, text=self.last_error_text, severity=999, code="")  # TODO code
                else:
                    sub.on_new_message(self, text=self.last_error_text, severity=999, code="")  # TODO code
        elif node.nodeid == self._ua_last_message_text.nodeid and val.Text is not None:
            self.last_message_text = val.Text
            for sub in self._subscribers:
                if asyncio.iscoroutinefunction(sub.on_new_message):
                    await sub.on_new_message(self, text=self.last_message_text, severity=0, code="")  # TODO code
                else:
                    sub.on_new_message(self, text=self.last_message_text, severity=0, code="")  # TODO code
