from __future__ import annotations

from typing import Any

import structlog
from asyncua import Node
from typing_extensions import override

from pyuaadapter.client.remote_component_v4 import RemoteComponent
from pyuaadapter.client.remote_lock import RemoteLock
from pyuaadapter.client.remote_port_v4 import RemotePort
from pyuaadapter.client.remote_storage_v4 import RemoteStorage
from pyuaadapter.client.remote_user import RemoteUser
from pyuaadapter.common.subscription_manager import SubscriptionManager


class RemoteModule(RemoteComponent):
    """ Represents a remote module using the skill v4 node set. """

    lock: RemoteLock = None

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server)

        self.logger = structlog.getLogger("sf.client.RemoteModule", name=name)

        self._users: list[RemoteUser] = []

    @override
    def dto(self) -> dict[str, Any]:
        ret = super().dto()
        ret["users"] = [u.dto() for u in self._users]
        return ret

    @property
    def ports(self) -> dict[str, RemotePort]:
        """ Returns a dictionary of all ports of this remote module. """
        return {key: value for key, value in self.components.items() if isinstance(value, RemotePort)}

    @property
    def storages(self) -> dict[str, RemoteStorage]:
        """ Returns a dictionary of all storages of this remote module. """
        return {key: value for key, value in self.components.items() if isinstance(value, RemoteStorage)}

    @property
    def type(self) -> str:
        return "Module"

    @property
    def users(self) -> list[RemoteUser]:
        return self._users

    async def _setup_users(self, node: Node, subscription_manager: SubscriptionManager) -> None:
        """ Create and setup all users found on remote server.

        :param node: OPC UA root node organizing the users. Browse name is usually "Users".
        """
        for user_node in await node.get_children():
            self._users.append(await RemoteUser.create(user_node, subscription_manager))

    @override
    async def _process_machinery_building_blocks(self, node: Node, subscription_manager: SubscriptionManager) -> None:
        await super()._process_machinery_building_blocks(node=node, subscription_manager=subscription_manager)

        for child in await node.get_children():
            bname = await child.read_browse_name()
            if bname.Name == "Users":  # ignore namespace
                await self._setup_users(child, subscription_manager)