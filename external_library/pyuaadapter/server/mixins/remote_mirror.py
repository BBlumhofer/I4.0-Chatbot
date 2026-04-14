from __future__ import annotations

from typing import Any

from asyncua import Node, Server, ua
from asyncua.common.structures104 import new_enum
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import NodeId, UaStatusCodeError
from structlog import BoundLogger
from typing_extensions import override

from pyuaadapter.client.base_remote_callable import BaseRemoteCallable, FinalResultUpdateSubscriber
from pyuaadapter.client.base_remote_component import BaseRemoteComponent
from pyuaadapter.client.mixins.attributes_mixin import AttributeUpdateSubscriber
from pyuaadapter.client.mixins.monitoring_mixin import MonitoringUpdateSubscriber
from pyuaadapter.client.mixins.parameter_mixin import ParameterUpdateSubscriber
from pyuaadapter.client.remote_variable import RemoteVariable


async def _get_datatype(server: Server, var: RemoteVariable) -> NodeId:
    if var.ua_data_type == "Enumeration":
        # create new enum based on valid values
        # TODO actually mirror the enum? with correct namespace etc
        node = await new_enum(server=server, idx=1, name=f"{var.name}Type",  # type: ignore
                              fields=[var.valid_values[key] for key in sorted(var.valid_values)])
        return node.nodeid
    else:
        return getattr(ua.ObjectIds, var.ua_data_type, None)

class RemoteAttributeUpdateMixin(AttributeUpdateSubscriber):
    """Mixin implementing (one-way) attribute updates from the remote server."""
    ua_attribute_nodes: dict[str, Node]
    _client_remote_object: BaseRemoteComponent
    logger: BoundLogger

    async def _init_attributes_mirror(self, historize: bool = True) -> None:
        if len(self._client_remote_object.attributes) <= 0:
            return

        for attribute in self._client_remote_object.attributes.values():
            await self.add_attribute_variable(
                attribute.name,
                attribute.raw_value,
                datatype=getattr(ua.ObjectIds, attribute.ua_data_type, None),
                historize=historize,
                unit=attribute.unit.UnitId if attribute.unit else None,
                _range=(attribute.range.Low, attribute.range.High) if attribute.range else None,
            )

    @override
    async def on_attribute_update(self, var: RemoteVariable) -> None:
        try:
            await self.ua_attribute_nodes[var.name].write_value(var.raw_value)
        except KeyError:
            self.logger.warning("Received unknown attribute update from remote component!", variable=var)


class RemoteParameterMirrorMixin(ParameterUpdateSubscriber):
    """Mixin implementing bidirectional parameter synchronization for RemoteComponents & RemoteCallables."""
    ua_parameter_set_nodes: dict[str, Node]
    _client_remote_object: BaseRemoteComponent | BaseRemoteCallable
    server: Server
    logger: BoundLogger

    async def _init_parameter_set_mirror(self, historize: bool = True) -> None:
        if len(self._client_remote_object.parameter_set) <= 0:
            return

        nodes = []
        for parameter in self._client_remote_object.parameter_set.values():
            node = await self.add_parameter_variable(
                parameter.name,
                parameter.raw_value,
                datatype=await _get_datatype(self.server, parameter),
                historize=historize,
                unit=parameter.unit.UnitId if parameter.unit else None,
                _range=(parameter.range.Low, parameter.range.High) if parameter.range else None,
            )
            nodes.append(node)

        # create (local) subscriptions for the parameters so we can transfer changes back to the remote instance.
        # NOTE: This mechanism is usually too slow for remote callables. Copy parameters over immediately before
        # executing remote execution call
        subscription = await self.server.create_subscription(period=100, handler=self)
        await subscription.subscribe_data_change(nodes)

    async def _copy_parameter_set_to_remote(self) -> None:
        """ Manually copy the (local) parameter set over to the mirrored remote object. """
        for name, parameter_node in self.ua_parameter_set_nodes.items():
            local_value = await parameter_node.read_value()
            await self._client_remote_object.parameter_set[name].write_value(local_value)

    @override
    async def on_parameter_update(self, var: RemoteVariable) -> None:
        try:
            await self.ua_parameter_set_nodes[var.name].write_value(var.raw_value)
        except KeyError:
            self.logger.warning("Received unknown parameter update!", variable=var)

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:
        # these are (local) server side notifications, and the only thing that clients can change are
        # parameters
        for param_name, param_node in self.ua_parameter_set_nodes.items():
            if node.nodeid == param_node.nodeid:
                try:
                    remote_value = self._client_remote_object.parameter_set[param_name]
                    await remote_value.write_value(val)
                except KeyError:
                    self.logger.warning("Could not find parameter in client parameter set!", param_name=param_name)
                except UaStatusCodeError as err:
                    self.logger.error("Could not write to remote variable!", param_name=param_name, err=err)
                return

        self.logger.warning("Unmatched data change notification!", node=node.nodeid.to_string())


class RemoteMonitoringUpdateMixin(MonitoringUpdateSubscriber):
    """Mixin implementing (one-way) monitoring updates from the remote server."""
    ua_monitoring_nodes: dict[str, Node]
    _client_remote_object: BaseRemoteComponent | BaseRemoteCallable
    server: Server
    logger: BoundLogger

    async def _init_monitoring_mirror(self, historize: bool = True) -> None:
        if len(self._client_remote_object.monitoring) <= 0:
            return

        for monitoring in self._client_remote_object.monitoring.values():
            await self.add_monitoring_variable(
                monitoring.name,
                monitoring.raw_value,
                datatype=await _get_datatype(self.server, monitoring),
                historize=historize,
                unit=monitoring.unit.UnitId if monitoring.unit else None,
                _range=(monitoring.range.Low, monitoring.range.High) if monitoring.range else None,
            )

    @override
    async def on_monitoring_update(self, var: RemoteVariable) -> None:
        try:
            await self.ua_monitoring_nodes[var.name].write_value(var.raw_value)
        except KeyError:
            self.logger.warning("Received unknown monitoring update!", variable=var)


class RemoteFinalResultUpdateMixin(FinalResultUpdateSubscriber):
    """Mixin implementing (one-way) final result updates from the remote server."""
    ua_final_result_data_nodes: dict[str, Node]
    _client_remote_object: BaseRemoteCallable
    server: Server
    logger: BoundLogger

    async def _init_final_result_data_mirror(self, historize: bool = True) -> None:
        if len(self._client_remote_object.final_result_data) <= 0:
            return

        for final_result in self._client_remote_object.final_result_data.values():
            await self.add_result_variable(
                final_result.name,
                final_result.raw_value,
                datatype=await _get_datatype(self.server, final_result),
                historize=historize,
                unit=final_result.unit.UnitId if final_result.unit else None,
                _range=(final_result.range.Low, final_result.range.High) if final_result.range else None,
            )

    @override
    async def on_final_result_update(self, var: RemoteVariable) -> None:
        try:
            await self.ua_final_result_data_nodes[var.name].write_value(var.raw_value)
        except KeyError:
            self.logger.warning("Received unknown final result data update!", variable=var)

    async def _copy_final_result_data_from_remote(self) -> None:
        """ Manually copy the (local) parameter set over to the mirrored remote object. """
        for name, remote_final_result in self._client_remote_object.final_result_data.items():
            remote_value = await remote_final_result.read_value(update_cache=True)
            await self.ua_final_result_data_nodes[name].write_value(remote_value)
