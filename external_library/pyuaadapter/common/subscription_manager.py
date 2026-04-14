from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Iterable

import structlog
from asyncua import Client, Node, ua
from asyncua.common.subscription import DataChangeNotif, Subscription, SubscriptionHandler
from asyncua.ua import NodeId, UaStatusCodeError
from asyncua.ua.uaerrors import BadAttributeIdInvalid


class SubscriptionManager:
    """
    Centrally manages all OPC UA subscription needs using only one subscription to an OPC UA server
    to not stay within max. subscription limits of certain OPC UA servers.

    Note:
    OPC UA subscriptions and nodes are bound to the OPC UA client and are no longer useful when reconnecting to
    a server. Only NodeIDs stay relevant (assuming the address space of the server we are reconnecting to did
    not change). Hence, only NodeIDs are used for subscriptions in our codebase.
    """

    _ua_client: Client
    _ua_subscription: Subscription

    def __init__(self):
        self._data_subscription_map: dict[NodeId, list[SubscriptionHandler]] = {}
        """ Maps a OPC UA node to a list of handlers for data change notifications. """
        self._event_subscription_map: dict[NodeId, list[SubscriptionHandler]] = {}
        """ Maps a OPC UA node to a list of handlers for event notifications. """

        self.period: float = 100
        """Publishing interval in milliseconds for OPC UA subscription."""

        self.logger = structlog.getLogger("sf.common.SubscriptionManager")

    async def _create_subscription(self, ua_client: Client):
        self._ua_subscription = await ua_client.create_subscription(period=self.period, handler=self)
        self.logger.info("Created subscription!", parameters=self._ua_subscription.parameters)

    async def init(self, ua_client: Client, period: float = 100) -> None:
        self.period = period
        self._ua_client = ua_client
        await self._create_subscription(ua_client)

        # subscribe to a node that always changes reliably, for example the current time of the server
        # this is done to prevent the subscription from timing out
        current_time_node = ua_client.get_node(ua.ObjectIds.Server_ServerStatus_CurrentTime)
        await self.subscribe_data_change(self, current_time_node)

    async def renew_subscriptions(self, ua_client: Client) -> None:
        self.logger.info(f"Renewing {self.no_of_monitored_items} subscriptions...")
        old_data_subscription_map = self._data_subscription_map.copy()
        old_event_subscription_map = self._event_subscription_map.copy()

        await self.clear_subscriptions()
        await self._create_subscription(ua_client)

        # add all old data change subscriptions back
        for node_id, handlers in old_data_subscription_map.items():
            for handler in handlers:
                await self.subscribe_data_change(handler=handler, nodes=[ua_client.get_node(node_id)])

        # add all old event subscriptions back
        for node_id, handlers in old_event_subscription_map.items():
            for handler in handlers:
                await self.subscribe_event(handler=handler, source_node=node_id)


    async def clear_subscriptions(self) -> None:
        self.logger.info(f"Clearing {self.no_of_monitored_items} subscriptions...")
        try:
            await self._ua_subscription.delete()
            self.logger.info("Deleted main OPC UA subscription!")
        except ConnectionError:
            pass  # we can safely ignore it since is no longer relevant
        except AttributeError:
            pass  # we can safely ignore it since there is no subscription to delete
        except Exception as err:
            self.logger.exception(err)

        with contextlib.suppress(NameError, AttributeError):
            del self._ua_subscription

        self._data_subscription_map.clear()
        self._event_subscription_map.clear()

    @property
    def no_of_monitored_items(self) -> int:
        return len(self._data_subscription_map) + len(self._event_subscription_map)

    async def subscribe_data_change(self, handler: SubscriptionHandler,
                                    nodes: Node | NodeId | Iterable[Node | NodeId]) -> None:
        if not isinstance(nodes, Iterable):
            nodes = [nodes]  # create a list out of the given single node or node id

        for node in nodes:
            if isinstance(node, NodeId):
                node = self._ua_client.get_node(node)

            if node.nodeid not in self._data_subscription_map:
                self._data_subscription_map[node.nodeid] = []
                try:
                    await self._ua_subscription.subscribe_data_change(node)
                    self._data_subscription_map[node.nodeid].append(handler)
                    self.logger.debug("Added data change handler", handler=handler, node=node.nodeid.to_string())
                except BadAttributeIdInvalid:
                    self.logger.warning("Node does not support subscription!", node=node.nodeid.to_string())
                except UaStatusCodeError as status_error:
                    self.logger.exception(status_error)
            else:
                # We only need 1 subscription for n handlers.
                self.logger.debug("Added data change handler, reusing existing subscription.", handler=handler,
                                  node=node.nodeid.to_string())
                self._data_subscription_map[node.nodeid].append(handler)

    async def subscribe_event(self, handler: SubscriptionHandler, source_node: Node | NodeId) -> None:
        # we only get the node ID in the notification
        if isinstance(source_node, Node):
            node_id: NodeId = source_node.nodeid
        elif isinstance(source_node, NodeId):
            node_id = source_node
        else:
            raise TypeError(f"Given source_node {source_node} is not supported!")

        if source_node not in self._event_subscription_map:
            self._event_subscription_map[node_id] = []

        try:
            await self._ua_subscription.subscribe_events(sourcenode=source_node)
            self._event_subscription_map[node_id].append(handler)
        except Exception as ex:
            self.logger.exception(ex)

    ###########################################
    # asyncua callbacks

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:
        try:
            for handler in self._data_subscription_map[node.nodeid]:  # list of handlers
                if handler == self:
                    continue  # current time, not required for anything specific
                try:
                    if asyncio.iscoroutinefunction(handler.datachange_notification):  # type: ignore
                        await handler.datachange_notification(node, val, data)  # type: ignore
                    else:
                        handler.datachange_notification(node, val, data)  # type: ignore
                except Exception as ex:
                    self.logger.exception(ex, node=node.nodeid.to_string(), value=val)

        except KeyError as ke:
            self.logger.warning(f"Data Notification KeyError '{ke}': ", node=node.nodeid.to_string(), value=val)

    async def status_change_notification(self, status: ua.StatusChangeNotification) -> None:
        # TODO, status_change_notification is somehow required?!
        self.logger.info("Received status change notification", status=status)

    async def event_notification(self, event) -> None:
        source_node = event.SourceNode
        try:
            for handler in self._event_subscription_map[source_node]:
                if asyncio.iscoroutinefunction(handler.event_notification):  # type: ignore
                    await handler.event_notification(event)  # type: ignore
                else:
                    handler.event_notification(event)  # type: ignore
        except KeyError as ke:
            self.logger.warning(f"Event Notification KeyError '{ke}'", event=event)
