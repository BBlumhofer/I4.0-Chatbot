from __future__ import annotations

import asyncio
from abc import ABC
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import NodeId, uaerrors
from asyncua.ua.uaerrors import BadTypeMismatch
from typing_extensions import deprecated

from pyuaadapter.client.remote_variable import RemoteVariable, add_variable_nodes
from pyuaadapter.common.subscription_manager import SubscriptionManager
from pyuaadapter.common.util import read_all_variables, write_value

if TYPE_CHECKING:
    from pyuaadapter.client.remote_server import RemoteServer

class ParameterUpdateSubscriber:
    """ Subscriber interface for monitoring parameter update events. """

    def on_parameter_update(self, var: RemoteVariable) -> None:
        """ Is called whenever the value of a parameter variable changed. """
        pass


class ParameterMixin(ABC):
    """ Mixin providing parameter-set related functionality (for components, skills, etc.). """

    _ua_parameter_set: Node | None
    """ (Optional) OPC UA node for the parameter set. """

    logger: structlog.BoundLogger
    _remote_server: "RemoteServer"
    _subscribers: list[ParameterUpdateSubscriber]

    def __init__(self):
        super().__init__()

        self._parameter_set: dict[str, RemoteVariable] = {}
        self._parameter_nodes: dict[NodeId, RemoteVariable] = {}

        self._ua_parameter_set = None

    @property
    def ua_parameter_set(self) -> Node:
        if self._ua_parameter_set is not None:
            return self._remote_server.ua_client.get_node(self._ua_parameter_set)
        else:
            raise RuntimeError(f"There is no ua_parameter_set node on '{self}'!")

    @deprecated("Please use the RemoteVariable based access instead of this!")
    async def read_parameters(self) -> dict[str, Any]:
        """Reads all variables contained in the parameter set of the remote method/skill."""
        # TODO is this really used anywhere? if yes, why?
        return await read_all_variables(self.ua_parameter_set)

    @deprecated("Please use the RemoteVariable based access instead of this!")
    async def write_parameter(self, browse_name: str, value: Any) -> None:
        """
        Writes the given value to a single parameter specified via browse name without namespace index

        :param browse_name: OPC UA browse name without namespace index
        :param value: Value
        """
        # loop instead of get_child() to prevent eventual namespace problems
        for node in await self.ua_parameter_set.get_children():
            if browse_name == (await node.read_browse_name()).Name:
                await write_value(node, value)
                return

        raise RuntimeError(f"Could not find parameter with name '{browse_name}'")

    @deprecated("Please use the RemoteVariable based access instead of this!")
    async def write_parameters(self, new_parameters: dict[str, RemoteVariable | Any] | None = None) -> None:
        """
        Writes all variables contained in the parameter set of the remote skill with the given parameter dictionary.

        :param new_parameters: Keys are mapped to OPC UA browse names (without namespace index), values are written
            to the mapped OPC UA node. Unmapped keys are ignored. When None, this skill's internal parameter set is used.
        """
        if new_parameters is None:
            new_parameters = self.parameter_set

        for node in await self.ua_parameter_set.get_children():
            name = (await node.read_browse_name()).Name
            try:
                # because asyncua is very strict, e.g. float is not automatically cast to double
                variant_type = (await node.read_data_value()).Value.VariantType
                val = new_parameters[name]
                if isinstance(val, RemoteVariable):
                    await node.write_value(val.value, variant_type)
                else:
                    await node.write_value(val, variant_type)
            except KeyError:
                self.logger.warning("No value given for parameter!", parameter=name)
            except BadTypeMismatch:
                self.logger.warning("Could not write parameter!", parameter=name, reason="Type mismatch")

    async def _setup_parameter_subscriptions(self, node: Node, subscription_manager: SubscriptionManager):
        try:
            self._parameter_nodes.clear()
            self._ua_parameter_set = node
            await add_variable_nodes(self._ua_parameter_set, self._parameter_nodes, self._parameter_set,
                                     is_writable=True, remote_server=self._remote_server)
        except uaerrors.BadNoMatch:
            pass  # is optional, so no problem

        if len(self._parameter_nodes) > 0:
            await subscription_manager.subscribe_data_change(handler=self, nodes=self._parameter_nodes.keys())

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> bool:
        """ OPC UA callback when the data of a node subscription changed. """
        try:
            var = self._parameter_nodes[node.nodeid]
            var.update_from_data_value(data)
            for sub in self._subscribers:  # notify subscribers
                if asyncio.iscoroutinefunction(sub.on_parameter_update):
                    await sub.on_parameter_update(var)
                else:
                    sub.on_parameter_update(var)
            return True
        except KeyError:
            return False

    @property
    def parameter_set(self) -> dict[str, RemoteVariable]:
        """ Provides convenient access to parameter variables via browse name (without namespace index). """
        return self._parameter_set