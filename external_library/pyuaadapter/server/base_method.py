from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import structlog
from asyncua import Node, ua, uamethod
from asyncua.server.internal_session import InternalSession
from asyncua.ua import NodeId
from typing_extensions import override

from pyuaadapter.server.base_callable import BaseCallable
from pyuaadapter.server.ua_types import UaTypes

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem
    

class BaseMethod(BaseCallable, ABC):
    """
    Base method class to allow adding a method set, containing Monitoring, FinalResultData, Parameter and the Call-Method
    """

    def __init__(self, name: str, machinery_item: 'BaseMachineryItem', minimum_access_level: int = 1):
        """
        Creates a new method instance.

        :param name: name of the method
        :param machinery_item: machinery_item instance
        :param minimum_access_level: Minimum required access level to start the callable (see User for more info)
        """
        super().__init__(name=name,
                         machinery_item=machinery_item,
                         _type=UaTypes.method_type,
                         minimum_access_level=minimum_access_level)
        self.logger = structlog.getLogger("sf.server.Method", name=self.full_name)

    @override
    async def _get_sub_node(self) -> Node:
        return self._ua_node  # methods are not organized in sub nodes like skills are

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        """
        Initialize the method instance asynchronously.

        :param existing_node: pre-existing OPC UA node prior to init().
                Will be used instead of creating a new node in the given location.
        :param location: parent OPC-UA node, ideally a folder type
        """
        await super().init(location=location, existing_node=existing_node)

        node_call = await self._ua_node.get_child(f"{UaTypes.ns_skill_set}:Call")
        _session = self.server.iserver.isession
        _session.add_method_callback(node_call.nodeid, self._call)
        

    @uamethod
    async def _call(self, _parent: NodeId, session: InternalSession) -> ua.StatusCode:
        user = session.user
        if not self.access_control.access_allowed(user, access_required=self._minimum_access_level):
            await self._log_error(f"Denied, user '{user}' has no access to this method!")
            return ua.StatusCode(ua.UInt32(ua.StatusCodes.BadUserAccessDenied))
        try:
            await self.execute_method()
            return ua.StatusCode(ua.UInt32(ua.StatusCodes.Good))
        except ua.UaStatusCodeError as e:
            return ua.StatusCode(e.code)
        except Exception as e:
            self.logger.exception(e)
            return ua.StatusCode(ua.UInt32(ua.StatusCodes.BadInternalError))
        

    @abstractmethod    
    async def execute_method(self) -> None:
        # To be implemented by subclasses
        raise NotImplementedError
