from __future__ import annotations

import traceback
from abc import ABC, abstractmethod

import structlog
from asyncua import Node, Server, ua
from asyncua.common.subscription import Subscription
from asyncua.ua import NodeId

from pyuaadapter.common.enums import SkillStates
from pyuaadapter.server.base_skill import BaseSkill


class SkillPublisher(ABC):
    """
    Subscribes to skill state changes for given skill and
    publishes the state + parameters (when RUNNING) & results (when COMPLETED) on opc ua data change notifications.
    """

    logger = structlog.getLogger("sf.server.plugins.skill_publisher")
    ua_node_skill_state: Node
    ua_subscription: Subscription

    def __init__(self, ua_server: Server, skill: BaseSkill):
        self._ua_server = ua_server
        self._skill = skill
        self.ua_parameter_nodes: dict[str, Node] = {}
        self.ua_result_nodes: dict[str, Node] = {}

    async def init(self):
        self.ua_node_skill_state = await self._skill.ua_state_machine.get_child("0:CurrentState")

        self.ua_subscription = await self._ua_server.create_subscription(100, self)
        await self.ua_subscription.subscribe_data_change(nodes=[self.ua_node_skill_state])

        for node in await self._skill.ua_parameter_set.get_children():
            name = (await node.read_browse_name()).Name
            self.ua_parameter_nodes[name] = node

        for node in await self._skill.ua_final_result_data.get_children():
            name = (await node.read_browse_name()).Name
            self.ua_result_nodes[name] = node

        return self

    async def datachange_notification(self, node, val, data):
        """ OPC-UA subscription callback """
        data_value = data.monitored_item.Value
        skill_state: str = data_value.Value.Value.Text.upper()
        parameters = {}
        results = {}

        if skill_state == SkillStates.Running.name.upper():
            # gather parameters
            for name, node in self.ua_parameter_nodes.items():
                value = await self._get_value(node)
                parameters[name] = value

        if skill_state == SkillStates.Completed.name.upper():
            # gather results
            for name, node in self.ua_result_nodes.items():
                value = await self._get_value(node)
                results[name] = value

        self.logger.debug(f"Skill '{self._skill.name}' changed state to '{skill_state}'")
        await self.publish({
            "state": skill_state,
            "parameters": parameters if len(parameters) > 0 else None,
            "results": results if len(results) > 0 else None,
            "source_timestamp": int(data_value.SourceTimestamp.timestamp()) * 1000
        })

    @abstractmethod
    async def publish(self, value_dict) -> None:
        raise NotImplementedError

    async def _get_value(self, node: Node):
        try:
            value = await node.read_value()
            if isinstance(value, NodeId):
                if value.is_null():  # we cannot read the browse name of this node
                    return None
                else:  # get more useful representation
                    return (await self._ua_server.get_node(value).read_browse_name()).Name
            else:
                return value
        except ua.UaError as err:  # make sure we don't fail because of asyncua problems
            traceback.print_exception(err)  # here to get notified of handled problems
            self.logger.warning(f"Could not get the value for node '{node.nodeid}'!")
            return None
