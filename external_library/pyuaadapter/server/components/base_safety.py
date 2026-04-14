from __future__ import annotations

import asyncio
import logging
from abc import ABC

import structlog
from asyncua import Node, Server, ua
from typing_extensions import deprecated

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import read_optional, write_optional
from pyuaadapter.server.components.component_data_classes import Safety
from pyuaadapter.server.spatial_object import SpatialObject


class BaseSafety(BaseComponent, ABC):
    """ Abstract base class representing a safety component. """

    ua_emergency_stop_not_triggered: Node
    """ indicates whether emergency top of module is not triggered"""
    ua_emergency_stop_ack_req: Node
    """ indicates whether acknowledge of safety device is necessary """
    ua_sdd_not_triggered: Node
    """ indicates whether safety device diagnostics is not triggered, i.e., all psen safety switches are ok"""

    ua_housing_not_triggered: Node | None  # Optional
    """ indicates whether the safety of the housing (doors, cameras, scanners ...) is not triggered 
    -> focus is inside envelope body of the module """
    ua_environment_not_triggered: Node | None  # Optional
    """ indicates whether the safety of the environment (doors, cameras, scanners ...) is not triggered
         -> focus is outside envelope body of the module """
    ua_sto_not_triggered: Node | None  # Optional
    """ indicates whether the safe-torque-of off all axis are not not triggered """

    ua_safety_not_triggered: Node
    """ indicates the whole safety state and whether all safety devices are ok """

    _safety_values: Safety


    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: int, name: str,
                 config: BaseConfig, safety_values: Safety, spatial_object: SpatialObject | None = None):
        """
        Creates a new safety component
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object)
        self._safety_values = safety_values
        self._safety_subscription_values = ["SafetyNotTriggered",
                                            "EmergencyStopNotTriggered",
                                            "HousingNotTriggered",
                                            "EnvironmentNotTriggered",
                                            "SafetyDeviceDiagnosticsNotTriggered"]
        """ List of safety nodes that should be internally subscribed 
        to emit error notifications based on device triggers """
        self.logger = structlog.getLogger("sf.server.Safety", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node | None = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always safety_type but to support reflection of child
        """
        from pyuaadapter.server import UaTypes
        await super().init(folder_node=parent_node, component_type=UaTypes.safety_type)

    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def datachange_notification(self, node: Node, val, data) -> None:
        """ OPC UA callback when the data of a node subscription changed. """

        # TODO add error codes for safety component

        if val:
            # device has not triggered just ignore the datachange notification
            return

        if not self.initialized:  # ignore notifications during initialization
            return

        if node == self.ua_safety_not_triggered:
            await self._log_error(f"Safety has triggered! {self.root_parent.name} cannot be used!")
        elif node == self.ua_emergency_stop_not_triggered:
            await self._log_error(f"Emergency Stop has triggered! {self.root_parent.name} cannot be used!")
        elif node == self.ua_housing_not_triggered:
            await self._log_error(f"Housing of Safety has triggered! {self.root_parent.name} cannot be used!")
        elif node == self.ua_environment_not_triggered:
            await self._log_error(f"Safety environment has triggered! {self.root_parent.name} cannot be used!")
        elif node == self.ua_sdd_not_triggered:
            await self._log_error(f"SDD has triggered - a Port is open! {self.root_parent.name} cannot be used!")
        else:
            self.logger.warning(f"Can not handle safety event of node {node} with value {val}")

    async def _init_subscriptions(self) -> None:
        if len(self._safety_subscription_values) == 0:
            return

        await self._init_notification()

        subscription_nodes = []
        for safety_value in self._safety_subscription_values:
            if safety_value in self.ua_monitoring_nodes:
                subscription_nodes.append(self.ua_monitoring_nodes[safety_value])

        if len(subscription_nodes) == 0:
            return

        _ua_subscription = await self.server.create_subscription(100, self)
        await _ua_subscription.subscribe_data_change(subscription_nodes)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        (self.ua_emergency_stop_not_triggered, self.ua_emergency_stop_ack_req,
         self.ua_sdd_not_triggered, self.ua_safety_not_triggered, self.ua_housing_not_triggered,
         self.ua_environment_not_triggered, self.ua_sto_not_triggered) = await asyncio.gather(
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:EmergencyStopNotTriggered"]),
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:EmergencyStopAcknowledgeRequired"]),
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:SafetyDeviceDiagnosticsNotTriggered"]),
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:SafetyNotTriggered"]),
            self.add_monitoring_variable(ua.QualifiedName("HousingNotTriggered", UaTypes.ns_machine_set),
                                         False, varianttype=ua.VariantType.Boolean,
                                         instantiate=self._safety_values.instantiate_housing),
            self.add_monitoring_variable(ua.QualifiedName("EnvironmentNotTriggered", UaTypes.ns_machine_set),
                                         False, varianttype=ua.VariantType.Boolean,
                                         instantiate=self._safety_values.instantiate_environment),
            self.add_monitoring_variable(ua.QualifiedName("SafeTorqueOffNotTriggerd", UaTypes.ns_machine_set),
                                         False, varianttype=ua.VariantType.Boolean,
                                         instantiate=self._safety_values.instantiate_sto))

        await self._init_subscriptions()

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change([self.ua_emergency_stop_not_triggered, self.ua_emergency_stop_ack_req,
                                                 self.ua_sdd_not_triggered, self.ua_safety_not_triggered], count=count)

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def safety_not_triggered(self) -> bool:
        return await self.ua_safety_not_triggered.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def emergency_stop_not_triggered(self) -> bool:
        return await self.ua_emergency_stop_not_triggered.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def emergency_stop_ack_req(self) -> bool:
        return await self.ua_emergency_stop_ack_req.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def sdd_not_triggered(self) -> bool:
        return await self.ua_sdd_not_triggered.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def housing_not_triggered(self) -> bool:
        return await self.ua_housing_not_triggered.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def environment_not_triggered(self) -> bool:
        return await self.ua_environment_not_triggered.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def sto_not_triggered(self) -> bool:
        return await self.ua_sto_not_triggered.read_value()

    async def read_safety_not_triggered(self) -> bool:
        return await self.ua_safety_not_triggered.read_value()

    async def read_emergency_stop_not_triggered(self) -> bool:
        return await self.ua_emergency_stop_not_triggered.read_value()

    async def read_emergency_stop_ack_req(self) -> bool:
        return await self.ua_emergency_stop_ack_req.read_value()

    async def read_sdd_not_triggered(self) -> bool | None:
        return await read_optional(self.ua_sdd_not_triggered)

    async def read_housing_not_triggered(self) -> bool:
        return await self.ua_housing_not_triggered.read_value()

    async def read_environment_not_triggered(self) -> bool | None:
        return await read_optional(self.ua_environment_not_triggered)

    async def read_sto_not_triggered(self) -> bool | None:
        return await read_optional(self.ua_sto_not_triggered)

    async def write_safety_not_triggered(self, value: bool) -> None:
        await self.ua_safety_not_triggered.write_value(value)

    async def write_emergency_stop_not_triggered(self, value: bool) -> None:
        await self.ua_emergency_stop_not_triggered.write_value(value)

    async def write_emergency_stop_ack_req(self, value: bool) -> None:
        await self.ua_emergency_stop_ack_req.write_value(value)

    async def write_sdd_not_triggered(self, value: bool) -> None:
        await self.ua_sdd_not_triggered.write_value(value)

    async def write_housing_not_triggered(self, value: bool) -> None:
        await write_optional(self.ua_housing_not_triggered, value)

    async def write_environment_not_triggered(self, value: bool) -> None:
        await write_optional(self.ua_environment_not_triggered, value)

    async def write_sto_not_triggered(self, value: bool) -> None:
        await write_optional(self.ua_sto_not_triggered, value)

    async def write_monitoring_values(
            self,
            safety_not_triggered: bool = None,
            emergency_stop_not_triggered: bool = None,
            emergency_stop_ack_req: bool = None,
            sdd_not_triggered: bool = None,
            housing_not_triggered: bool = None,
            environment_not_triggered: bool = None,
            sto_not_triggered: bool = None) -> None:

        if safety_not_triggered is not None:
            await self.write_safety_not_triggered(safety_not_triggered)

        if emergency_stop_not_triggered is not None:
            await self.write_emergency_stop_not_triggered(emergency_stop_not_triggered)

        if emergency_stop_ack_req is not None:
            await self.write_emergency_stop_ack_req(emergency_stop_ack_req)

        if sdd_not_triggered is not None:
            await self.write_sdd_not_triggered(sdd_not_triggered)

        if housing_not_triggered is not None:
            await self.write_housing_not_triggered(housing_not_triggered)

        if environment_not_triggered is not None:
            await self.write_environment_not_triggered(environment_not_triggered)

        if sto_not_triggered is not None:
            await self.write_sto_not_triggered(sto_not_triggered)
