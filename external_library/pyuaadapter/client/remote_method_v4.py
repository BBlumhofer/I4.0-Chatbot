from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node

from pyuaadapter.client.base_remote_callable import BaseRemoteCallable
from pyuaadapter.common.namespace_uri import NS_SKILL_SET_URI

if TYPE_CHECKING:
    from .remote_server import RemoteServer


class RemoteMethod(BaseRemoteCallable):
    """ Represents a remote method """

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server)

        self._ns_idx_other = self._remote_server.namespace_map[NS_SKILL_SET_URI]

        self.logger = structlog.getLogger("sf.client.RemoteMethod")

    def dto(self) -> dict[str, Any]:
        ret = super().dto()
        ret.update({
            "type": "method"
        })
        return ret


    async def call(self) -> dict[str, Any]:
        """ Calls the remote method. User is responsible for handling any errors. """
        await self._ua_base_node.call_method(f"{self._ns_idx_other}:Call")
        return await self.read_results()

