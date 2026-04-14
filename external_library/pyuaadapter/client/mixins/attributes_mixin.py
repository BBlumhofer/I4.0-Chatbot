from __future__ import annotations

import asyncio
from abc import ABC
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node, ua
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import NodeId

from pyuaadapter.client.remote_variable import RemoteVariable, add_variable_nodes
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from pyuaadapter.client.remote_server import RemoteServer


class AttributeUpdateSubscriber:
    """ Subscriber interface for monitoring attribute update events. """

    def on_attribute_update(self, var: RemoteVariable) -> None:
        """ Is called whenever the value of an attribute variable changed. """
        pass


class AttributesMixin(ABC):
    """
    Mixin providing attributes related functionality (for components, skills, etc.).
    Note: This is unused in skill node set version 3.
    """

    _ua_attributes: Node | None
    """ (Optional) OPC UA node for the attribute set. """

    logger: structlog.BoundLogger
    _remote_server: "RemoteServer"
    _subscribers: list[AttributeUpdateSubscriber]

    def __init__(self):
        super().__init__()

        self._attributes_nodes: dict[NodeId, RemoteVariable] = {}  # will be empty/unused for v3
        self._attributes: dict[str, RemoteVariable] = {}

        _ua_attributes = None

    @property
    def ua_attributes(self) -> Node:
        if self._ua_attributes is not None:
            return self._remote_server.ua_client.get_node(self._ua_attributes)
        else:
            raise RuntimeError(f"There is no ua_attributes node on '{self}'!")

    async def _setup_attributes_subscriptions(self, node: Node, subscription_manager: SubscriptionManager):
        try:
            self._attributes_nodes.clear()
            self._ua_attributes = node
            await add_variable_nodes(self._ua_attributes, self._attributes_nodes, self._attributes,
                                     is_writable=True, remote_server=self._remote_server)
        except ua.uaerrors.BadNoMatch:
            pass  # is optional, so no problem

        if len(self._attributes_nodes) > 0:
            await subscription_manager.subscribe_data_change(handler=self, nodes=self._attributes_nodes.keys())

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> bool:
        try:
            var = self._attributes_nodes[node.nodeid]
            var.update_from_data_value(data)
            for sub in self._subscribers:  # notify subscribers
                if asyncio.iscoroutinefunction(sub.on_attribute_update):
                    await sub.on_attribute_update(var)
                else:
                    sub.on_attribute_update(var)
            return True
        except KeyError:
            return False

    @property
    def attributes(self) -> dict[str, RemoteVariable]:
        return self._attributes