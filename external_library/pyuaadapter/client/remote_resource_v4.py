from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node, ua
from asyncua.common.subscription import DataChangeNotif
from typing_extensions import override

from pyuaadapter.client.mixins.attributes_mixin import AttributesMixin, AttributeUpdateSubscriber
from pyuaadapter.client.mixins.monitoring_mixin import MonitoringMixin, MonitoringUpdateSubscriber
from pyuaadapter.client.remote_variable import add_variable_nodes
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer


class RemoteResourceSubscriber(AttributeUpdateSubscriber, MonitoringUpdateSubscriber):
    """ Subscriber interface for RemoteResource events. """
    pass


class RemoteResource(AttributesMixin, MonitoringMixin):
    """ Represents a resource object according to the skill node set version 4 specification. """

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__()
        self._name = name
        self._ua_node = base_node
        self._remote_server = remote_server

        self._subscribers: list[RemoteResourceSubscriber] = []  # type: ignore
        self.logger = structlog.getLogger("sf.RemoteResource")

    def dto(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_id": self._ua_node.nodeid.to_string(),
            "monitoring": [m.dto() for m in self.monitoring.values()],
            "attributes": [a.dto() for a in self.attributes.values()],
        }

    def add_subscriber(self, subscriber: RemoteResourceSubscriber) -> None:
        """ Adds given subscriber to the list of subscribers to be notified. """
        self._subscribers.append(subscriber)

    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:
        """ Sets up all subscriptions for all subcomponents and itself. """
        children = await self._ua_node.get_children()
        bname_data_values = await self._remote_server.ua_client.read_attributes(children, ua.AttributeIds.BrowseName)
        for child, data_value in zip(children, bname_data_values):  # to avoid namespace issues
            child_name = data_value.Value.Value.Name  # type: ignore #  Variant -> QualifiedName
            if child_name == "Monitoring":
                await self._setup_monitoring_subscriptions(child, subscription_manager)
            elif child_name == "Identification":
                # TODO @SiJu shouldn't these be identification nodes etc. ?
                await add_variable_nodes(child, self._attributes_nodes, self._attributes,
                                         is_writable=False, remote_server=self._remote_server)
            elif child_name == "Attributes":
                await self._setup_attributes_subscriptions(child, subscription_manager)
            else:
                self.logger.warning("Found unhandled child node!", node_id=child.nodeid.to_string())

    @override
    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> bool:
        if await MonitoringMixin.datachange_notification(self, node, val, data):
            return True
        return await AttributesMixin.datachange_notification(self, node, val, data)

    @property
    def name(self) -> str:
        """ Returns the name of the remote module """
        return self._name