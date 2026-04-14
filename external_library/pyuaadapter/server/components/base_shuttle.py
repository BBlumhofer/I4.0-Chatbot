from __future__ import annotations

import asyncio
from abc import ABC
from typing import Any

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import write_optional
from pyuaadapter.server.components.component_data_classes import Shuttle
from pyuaadapter.server.spatial_object import SpatialObject


class BaseShuttle(BaseComponent, ABC):
    """ Abstract base class representing a shuttle. """

    ua_shuttle_locked: Node | None
    ua_is_carrier_empty: Node
    ua_carrier_id: Node

    ua_is_shuttle_empty: Node
    ua_product_id: Node
    ua_product_type: Node | None

    ua_load_capacity: Node

    ua_actual_acc: Node | None
    ua_actual_vel: Node | None
    ua_actual_pos: Node
    ua_target_position: Node | None
    ua_current_port: Node | None
    ua_target_port: Node | None

    _shuttle_values: Shuttle

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 shuttle_values: Shuttle, spatial_object: SpatialObject = None, move_to_skill=None, release_skill=None):
        # TODO support move_to and release skills
        """
        Creates a new shuttle
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object)
        self._shuttle_values = shuttle_values
        self.logger = structlog.getLogger("sf.server.Shuttle", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always shuttle_type but to support reflection of child
        """
        from pyuaadapter.server import UaTypes
        await super().init(folder_node=parent_node, component_type=UaTypes.shuttle_type)

    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        (self.ua_actual_pos, self.ua_is_shuttle_empty, self.ua_is_carrier_empty, self.ua_carrier_id,
         self.ua_product_id, self.ua_shuttle_locked, self.ua_product_type, self.ua_actual_vel,
         self.ua_actual_acc, self.ua_target_position, self.ua_load_capacity, self.ua_current_port,
         self.ua_target_port) \
            = await asyncio.gather(self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:ActualPosition"]),
                                   self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:IsShuttleEmpty"]),
                                   self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:IsCarrierEmpty"]),
                                   self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:CarrierID"]),
                                   self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:ProductID"]),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("ShuttleLocked", UaTypes.ns_machine_set),
                                       False, varianttype=ua.VariantType.Boolean,
                                       instantiate=self._shuttle_values.instantiate_shuttle_locked),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("ProductType", UaTypes.ns_machine_set),
                                       "", varianttype=ua.VariantType.String,
                                       instantiate=self._shuttle_values.instantiate_product_type),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("ActualVelocity", UaTypes.ns_machine_set),
                                       0.0, varianttype=ua.VariantType.Double,
                                       unit=self._shuttle_values.velocity_unit,
                                       instantiate=self._shuttle_values.instantiate_velocity),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("ActualAcceleration", UaTypes.ns_machine_set),
                                       0.0, varianttype=ua.VariantType.Double,
                                       unit=self._shuttle_values.acceleration_unit,
                                       instantiate=self._shuttle_values.instantiate_acceleration),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("TargetPosition", UaTypes.ns_machine_set),
                                       0.0, varianttype=ua.VariantType.Double,
                                       unit=self._shuttle_values.target_pos_unit,
                                       instantiate=self._shuttle_values.instantiate_target_pos),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("LoadCapacity", UaTypes.ns_machine_set),
                                       self._shuttle_values.load_capacity, varianttype=ua.VariantType.Double,
                                       unit=self._shuttle_values.load_cap_unit,
                                       instantiate=self._shuttle_values.instantiate_load_capacity),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("CurrentPort", UaTypes.ns_machine_set),
                                       "", varianttype=ua.VariantType.String,
                                       instantiate=self._shuttle_values.instantiate_current_port),
                                   self.add_monitoring_variable(
                                       ua.QualifiedName("TargetPort", UaTypes.ns_machine_set),
                                       "", varianttype=ua.VariantType.String,
                                       instantiate=self._shuttle_values.instantiate_target_port))

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change([self.ua_actual_pos, self.ua_carrier_id, self.ua_is_shuttle_empty,
                                                 self.ua_product_id, self.ua_is_carrier_empty], count=count)

    async def set_shuttle_load(self, is_shuttle_empty: bool, carrier_id: str, is_carrier_empty: bool,
                               product_id: str, product_type: Any = None):
        self.logger.info(f"Change load of shuttle {self.name}: "
                         f"isShuttleEmpty from {await self.ua_is_shuttle_empty.read_value()} to {is_shuttle_empty}, "
                         f"carrierId from {await self.ua_carrier_id.read_value()} to {carrier_id}, "
                         f"isCarrierEmpty from {await self.ua_is_carrier_empty.read_value()} to {is_carrier_empty},"
                         f"productId=from {await self.ua_product_id.read_value()} to {product_id}")

        await asyncio.gather(self.ua_is_shuttle_empty.write_value(is_shuttle_empty),
                             self.ua_carrier_id.write_value(carrier_id),
                             self.ua_is_carrier_empty.write_value(is_carrier_empty),
                             self.ua_product_id.write_value(product_id),
                             write_optional(self.ua_product_type, product_type))

    async def set_shuttle_process_data(self, actual_pos: float, actual_vel: float = None, actual_acc: float = None,
                                       target_pos: float = None, current_port: str = None, target_port: str = None,
                                       shuttle_locked: bool = None):
        await asyncio.gather(self.ua_actual_pos.write_value(actual_pos, varianttype=ua.VariantType.Double),
                             write_optional(self.ua_actual_vel, actual_vel, variant_type=ua.VariantType.Double),
                             write_optional(self.ua_actual_acc, actual_acc, variant_type=ua.VariantType.Double),
                             write_optional(self.ua_target_position, target_pos, variant_type=ua.VariantType.Double),
                             write_optional(self.ua_current_port, current_port),
                             write_optional(self.ua_target_port, target_port),
                             write_optional(self.ua_shuttle_locked, shuttle_locked))
