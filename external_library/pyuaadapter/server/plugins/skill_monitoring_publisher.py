from __future__ import annotations

from abc import ABC, abstractmethod

import structlog
from asyncua import Node, Server
from asyncua.common.subscription import Subscription

from pyuaadapter.server.base_skill import BaseSkill


class SkillMonitoringPublisher(ABC):
    """
    Subscribes to skill state changes for given skill and
    publishes the state + parameters & results on opc ua data change notifications.
    """

    logger = structlog.getLogger("sf.server.plugins.skill_publisher")
    ua_subscription: Subscription

    def __init__(self, ua_server: Server, skill: BaseSkill):
        self._ua_server = ua_server
        self._skill = skill
        self.ua_variables: dict[Node, str] = {}

    async def init(self, period=100):
        async def _add_node(node: Node) -> None:
            name = (await node.read_browse_name()).Name  # namespace is ignored
            # handle nested variables, e.g. Cartesian Position Status
            nested_variables = await node.get_variables()  # ignores properties like EUInformation, Range, etc.
            if len(nested_variables) > 0:
                for node_child in nested_variables:
                    await _add_node(node_child)
            else:
                self.ua_variables[node] = name


        for node in await self._skill.ua_monitoring.get_children():
            await _add_node(node)

        if len(self.ua_variables) == 0:
            return self

        self.ua_subscription = await self._ua_server.create_subscription(period, self)
        await self.ua_subscription.subscribe_data_change(nodes=self.ua_variables.keys())

        return self

    async def datachange_notification(self, node, val, data):
        """ OPC-UA subscription callback """
        data_value = data.monitored_item.Value
        value = data_value.Value.Value
        try:
            await self.publish({
                "variable": self.ua_variables[node],
                "value": value,
                "source_timestamp": int(data_value.SourceTimestamp.timestamp() * 1000)
            })
        except TypeError:  # Object of type XXX is not JSON serializable
            self.logger.warning(f"Cannot serialize value '{value}' of node '{node.nodeid}'!")

    @abstractmethod
    async def publish(self, value_dict) -> None:
        raise NotImplementedError
