from __future__ import annotations

import asyncio
import contextlib
from abc import ABC
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import NodeId, uaerrors
from typing_extensions import override

from pyuaadapter.client.mixins.monitoring_mixin import MonitoringMixin, MonitoringUpdateSubscriber
from pyuaadapter.client.mixins.parameter_mixin import ParameterMixin, ParameterUpdateSubscriber
from pyuaadapter.client.remote_variable import RemoteVariable, add_variable_nodes
from pyuaadapter.common.enums import SkillStates
from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer

class FinalResultUpdateSubscriber:
    def on_final_result_update(self, var: RemoteVariable) -> None:
        """ Is called whenever the value of a final result variable changed in the remote method/skill. """
        pass


class RemoteMethodSubscriber(ParameterUpdateSubscriber, MonitoringUpdateSubscriber, FinalResultUpdateSubscriber):
    """ Subscriber interface for RemoteMethod events. """
    pass


class RemoteSkillSubscriber(RemoteMethodSubscriber):
    """ Subscriber interface for RemoteSkill events. """

    def on_skill_state_change(self, new_state: SkillStates) -> None:
        """ Is called whenever the state of the subscribed remote skill is changed. """
        pass


class BaseRemoteCallable(ParameterMixin, MonitoringMixin, ABC):
    """ Base class for all remote methods/skills. """

    _ua_final_result_data: Node | None
    """ (Optional) OPC UA node for the final result data folder of the method/skill. """

    logger: structlog.BoundLogger

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__()
        self.name = name
        self._ua_base_node = base_node
        self._remote_server = remote_server
        self._ns_idx_methods = -1
        """ OPC UA namespace index of skills methods (start, reset, halt, suspend). """
        self._ns_idx_other = -1
        """ OPC UA namespace index of every other modelled node in the skill node set. """

        self._final_result_data: dict[str, RemoteVariable] = {}
        self._final_result_nodes: dict[NodeId, RemoteVariable] = {}

        self._ua_final_result_data = None

        self._min_access_level: int | None = None

        self._subscribers: list[RemoteMethodSubscriber | RemoteSkillSubscriber] = []  # type: ignore

    @property
    def ua_base_node(self) -> Node:
        return self._remote_server.ua_client.get_node(self._ua_base_node.nodeid)

    @property
    def ua_final_result_data(self) -> Node:
        if self._ua_final_result_data is None:
            raise RuntimeError(f"There is no final result data node in '{self.name}'!")
        else:
            return self._remote_server.ua_client.get_node(self._ua_final_result_data.nodeid)

    @property
    def min_access_level(self) -> int | None:
        """ Minimum access level required to interact with the skill/method. Is None when the server does not provide
        this information. """
        return self._min_access_level

    def add_subscriber(self, subscriber: RemoteMethodSubscriber | RemoteSkillSubscriber) -> None:
        """ Adds given subscriber to the list of subscribers to be notified. """
        self._subscribers.append(subscriber)

    def dto(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_id": self._ua_base_node.nodeid.to_string(),
            "parameter_set": [p.dto() for p in self.parameter_set.values()],
            "monitoring": [m.dto() for m in self.monitoring.values()],
            "final_result_data": [f.dto() for f in self.final_result_data.values()],
            "min_access_level": self.min_access_level,
        }

    async def read_results(self) -> dict[str, Any]:
        """ Reads all remote variables contained in the final result data folder of the remote callable. """
        results = {}
        for name, remote_variable in self.final_result_data.items():
            results[name] = await remote_variable.read_value()
        return results

    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:
        # It is important to read the following values immediately after subscribing
        # Otherwise the first change can take too long and not be included in the UI

        with contextlib.suppress(uaerrors.BadNoMatch):  # new addition, server might not have it (yet)
            ua_min_access_level_node = await self.ua_base_node.get_child(f"{self._ns_idx_other}:MinAccessLevel")
            self._min_access_level = await ua_min_access_level_node.read_value()

        with contextlib.suppress(uaerrors.BadNoMatch):
            # Note: needs to be parsed before ParameterSet in case of duplications due to colliding nodesets
            await self._setup_monitoring_subscriptions(
                await self._ua_base_node.get_child(f"{self._ns_idx_other}:Monitoring"), subscription_manager)


        with contextlib.suppress(uaerrors.BadNoMatch):  # these are optional, so no problem
            await self._setup_parameter_subscriptions(
                await self._ua_base_node.get_child(f"{self._ns_idx_other}:ParameterSet"), subscription_manager
            )

        with contextlib.suppress(uaerrors.BadNoMatch):
            self._final_result_nodes.clear()
            self._ua_final_result_data = await self._ua_base_node.get_child(
                f"{self._ns_idx_other}:FinalResultData")
            await add_variable_nodes(self._ua_final_result_data, self._final_result_nodes, self._final_result_data,
                                     is_writable=False, remote_server=self._remote_server)


        if len(self._final_result_nodes) > 0:
            await subscription_manager.subscribe_data_change(handler=self, nodes=self._final_result_nodes.keys())


    @override
    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:  # type: ignore
        """ OPC UA callback when the data of a node subscription changed. """
        if await ParameterMixin.datachange_notification(self, node, val, data):
            return
        if await MonitoringMixin.datachange_notification(self, node, val, data):
            return
        try:
            var = self._final_result_nodes[node.nodeid]
            var.update_from_data_value(data)
            for sub in self._subscribers:  # notify subscribers
                if asyncio.iscoroutinefunction(sub.on_final_result_update):
                    await sub.on_final_result_update(var)
                else:
                    sub.on_final_result_update(var)
        except KeyError as ke:
            self.logger.warning(f"KeyError '{ke}'", node=node, bname=await node.read_browse_name(), value=val)

    @property
    def final_result_data(self) -> dict[str, RemoteVariable]:
        """ Provides convenient access to result variables via browse name (without namespace index). """
        return self._final_result_data


