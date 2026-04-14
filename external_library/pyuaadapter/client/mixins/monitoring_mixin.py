from __future__ import annotations

import asyncio
from abc import ABC
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node, ua
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import NodeId
from typing_extensions import deprecated

from pyuaadapter.client.remote_variable import RemoteVariable, add_variable_nodes
from pyuaadapter.common.subscription_manager import SubscriptionManager
from pyuaadapter.common.util import read_all_variables

if TYPE_CHECKING:
    from pyuaadapter.client.remote_server import RemoteServer


class MonitoringUpdateSubscriber:
    """ Subscriber interface for monitoring update events. """

    def on_monitoring_update(self, var: RemoteVariable) -> None:
        """ Is called whenever the value of a monitoring variable changed. """
        pass


class MonitoringMixin(ABC):
    """ Mixin providing monitoring related functionality (for components, skills, etc.). """

    _ua_monitoring: Node | None
    """ (Optional) OPC UA node for the monitoring folder. """

    logger: structlog.BoundLogger
    _remote_server: "RemoteServer"
    _subscribers: list[MonitoringUpdateSubscriber]

    def __init__(self):
        super().__init__()

        self._monitoring_nodes: dict[NodeId, RemoteVariable] = {}
        self._monitoring: dict[str, RemoteVariable] = {}

        self._ua_monitoring = None

    @property
    def ua_monitoring(self) -> Node:
        if self._ua_monitoring is not None:
            return self._remote_server.ua_client.get_node(self._ua_monitoring)
        else:
            raise RuntimeError(f"There is no ua_monitoring node on '{self}'!")

    async def _setup_monitoring_subscriptions(self, node: Node, subscription_manager: SubscriptionManager):
        try:
            self._monitoring_nodes.clear()
            self._ua_monitoring = node
            await add_variable_nodes(self._ua_monitoring, self._monitoring_nodes, self._monitoring,
                                     is_writable=False, remote_server=self._remote_server)
        except ua.uaerrors.BadNoMatch:
            pass  # is optional, so no problem

        if len(self._monitoring_nodes) > 0:
            await subscription_manager.subscribe_data_change(handler=self, nodes=self._monitoring_nodes.keys())

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> bool:
        """ OPC UA callback when the data of a node subscription changed. """
        try:
            var = self._monitoring_nodes[node.nodeid]
            var.update_from_data_value(data)

            for sub in self._subscribers:  # notify subscribers
                if asyncio.iscoroutinefunction(sub.on_monitoring_update):
                    await sub.on_monitoring_update(var)
                else:
                    sub.on_monitoring_update(var)

            return True
        except KeyError:
            return False

    @deprecated("Please use the RemoteVariable based access instead of this!")
    async def read_monitoring(self) -> dict[str, Any]:
        """ Reads all variables contained in the monitoring folder directly from OPC UA. """
        return await read_all_variables(self.ua_monitoring)  # TODO is this really used anywhere? if yes, why?

    @property
    def monitoring(self) -> dict[str, RemoteVariable]:
        """ Provides convenient access to monitoring variables via browse name (without namespace index). """
        return self._monitoring