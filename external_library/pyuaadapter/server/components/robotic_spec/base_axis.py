from __future__ import annotations

import asyncio
from abc import ABC
from typing import TYPE_CHECKING, Any, Coroutine, Dict, List, Type

import structlog
from asyncua import Node, Server, ua
from asyncua.ua import Double

from pyuaadapter.common import namespace_uri
from pyuaadapter.common.enums import MotionProfile
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import (
    add_object,
    add_reference,
    create_missing_objects,
    read_optional,
    write_optional,
    write_unit,
)
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:
    from pyuaadapter.server.components.component_data_classes import Axis
    from pyuaadapter.server.skills.base_axis_skills import BaseAxisHomingSkill, BaseAxisMoveToSkill, BaseAxisSkill


class BaseAxis(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing an axis. """

    ua_additional_load: Node | None  # Optional
    ua_actual_position: Node
    ua_motion_profile: Node
    ua_is_referenced: Node
    ua_actual_speed: Node | None  # Optional
    ua_actual_acceleration: Node | None  # Optional

    move_to_skill: BaseAxisMoveToSkill | None
    homing_skill: BaseAxisHomingSkill | None

    _motion_profile: MotionProfile
    _axis_values: Axis
    _int_identifier: ua.Int32 = ua.Int32(16601)  # identifier of AxisType of robotic companion specification

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 axis_values: Axis, spatial_object: SpatialObject = None,
                 homing_skill: Type[BaseAxisHomingSkill] = None, homing_skill_kwargs: Dict[str, Any] = None,
                 move_to_skill: Type[BaseAxisMoveToSkill] = None, move_to_skill_kwargs: Dict[str, Any] = None):
        # TODO kwargs necessary?
        """
        Creates a new axis
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)
        self._motion_profile = axis_values.motion_profile
        self.ua_additional_load = None
        self._axis_values = axis_values
        self.homing_skill = None
        self.move_to_skill = None
        self._axis_skills: List[Type[BaseAxisSkill]] =\
            [_skill for _skill in [move_to_skill, homing_skill] if _skill is not None]
        self._skill_kwargs: List[Dict[str, Any]] =\
            [_skill if _skill is not None else {} for _skill in [move_to_skill_kwargs, homing_skill_kwargs]]
        self.logger = structlog.getLogger("sf.server.robotic_spec.Axis", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always component type from robotic spec.
                               but to support reflection of child
        """
        await super().init(parent_node, self._int_identifier)

    @create_missing_objects("Identification", "component_identification_type", "ns_di")
    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:

        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_skills(self) -> None:

        await super()._init_skills()

        if len(self._axis_skills) > 0:

            from pyuaadapter.server.skills.base_axis_skills import BaseAxisHomingSkill, BaseAxisMoveToSkill

            for n, _skill in enumerate(self._axis_skills):
                if issubclass(_skill, BaseAxisMoveToSkill):
                    self.move_to_skill = await self.add_skill(_skill, **self._skill_kwargs[n])

                elif issubclass(_skill, BaseAxisHomingSkill):
                    self._skill_kwargs[n]["axis_move_to_skill"] = self.move_to_skill
                    self.homing_skill = await self.add_skill(_skill, **self._skill_kwargs[n])

    async def _init_attributes(self) -> None:
        await super()._init_attributes()

        self.ua_motion_profile = await self.ua_node.get_child(f"{self.ns_idx_cs}:MotionProfile")
        callables = [self.ua_motion_profile.write_value(ua.Int32(self._motion_profile),
                                                        varianttype=ua.VariantType.Int32),

                     add_reference(self.ua_attributes, self.ua_motion_profile, _dict=self.ua_attribute_nodes),
                     self._add_load_object()]

        await asyncio.gather(*callables)

    async def _add_load_object(self):

        if not self._axis_values.instantiate_load:
            self.ua_additional_load = None
            return

        self.ua_additional_load = await add_object(ns_idx=self.ns_idx, location=self.ua_node,
                                                   object_tyoe=self.server.get_node(f"ns={self.ns_idx_cs};i=1018"),
                                                   bname=ua.QualifiedName("AdditionalLoad", self.ns_idx_cs))

        ua_mass, _ = await asyncio.gather(
            self.ua_additional_load.get_child(f"{self.ns_idx_cs}:Mass"),
            add_reference(self.ua_attributes, self.ua_additional_load, _dict=self.ua_attribute_nodes))

        await asyncio.gather(ua_mass.write_value(ua.Double(self._axis_values.load),
                                                 varianttype=ua.VariantType.Double),
                             write_unit(ua_mass, self._axis_values.load_unit))

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        # be careful this parameter set is from robotic specification and not from SF-KL machine set
        await super()._init_parameter_set()
        self.ua_actual_position = await self.ua_parameter_set.get_child(f"{self.ns_idx_cs}:ActualPosition")

        _, self.ua_is_referenced, _, _, _ = await asyncio.gather(
                    self.ua_actual_position.write_value(0.0),
                    self.add_monitoring_variable("IsReferenced", False,
                                                  varianttype=ua.VariantType.Boolean),
                     write_unit(self.ua_actual_position, self._axis_values.position_unit),
                     add_reference(self.ua_monitoring, self.ua_actual_position, _dict=self.ua_monitoring_nodes), 
                     self._handle_optionals())

    async def _handle_optionals(self):
        (self.ua_actual_acceleration, self.ua_is_axis_empty, self.ua_is_carrier_empty,
         self.ua_carrier_id, self.ua_product_id) = \
            await asyncio.gather(
                self.add_monitoring_variable(name="ActualAcceleration", val=0.0, varianttype=ua.VariantType.Double,
                                             unit=self._axis_values.acceleration_unit,
                                             instantiate=self._axis_values.instantiate_acceleration),
                self.add_monitoring_variable(name="IsAxisEmpty", val=False, varianttype=ua.VariantType.Boolean,
                                             instantiate=self._axis_values.instantiate_is_axis_empty),
                self.add_monitoring_variable(name="IsCarrierEmpty", val=False, varianttype=ua.VariantType.Boolean,
                                             instantiate=self._axis_values.instantiate_is_carrier_empty),
                self.add_monitoring_variable(name="CarrierID", val="", varianttype=ua.VariantType.String,
                                             instantiate=self._axis_values.instantiate_carrier_id),
                self.add_monitoring_variable(name="ProductID", val="", varianttype=ua.VariantType.String,
                                             instantiate=self._axis_values.instantiate_product_id)
            )

        if self.ua_actual_acceleration is not None:
            await add_reference(self.ua_parameter_set, self.ua_actual_acceleration, _dict=self.ua_parameter_set_nodes)
        
        self.ua_actual_speed = \
            await self.add_monitoring_variable(name="ActualSpeed", val=0.0, varianttype=ua.VariantType.Double,
                                               unit=self._axis_values.speed_unit,
                                               instantiate=self._axis_values.instantiate_speed)
        if self.ua_actual_speed is not None:
            await add_reference(self.ua_parameter_set, self.ua_actual_speed, _dict=self.ua_parameter_set_nodes)

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change([self.ua_actual_acceleration, self.ua_actual_position,
                                                 self.ua_actual_speed], count=count)

    async def set_axis_referenced(self, value: bool) -> None:
        await self.ua_is_referenced.write_value(value, ua.VariantType.Boolean)

    async def set_axis_monitoring_values(self, position: float = None, speed: float = None, acceleration: float = None,
                                         carrier_id: str = None, product_id: str = None, carrier_empty: bool = False,
                                         axis_empty: bool = False) -> None:

        await asyncio.gather(write_optional(self.ua_actual_position, position, ua.VariantType.Double),
                             write_optional(self.ua_actual_speed, speed, ua.VariantType.Double),
                             write_optional(self.ua_actual_acceleration, acceleration, ua.VariantType.Double),
                             write_optional(self.ua_carrier_id, carrier_id, ua.VariantType.String),
                             write_optional(self.ua_product_id, product_id, ua.VariantType.String),
                             write_optional(self.ua_is_axis_empty, axis_empty, ua.VariantType.Boolean),
                             write_optional(self.ua_is_carrier_empty, carrier_empty, ua.VariantType.Boolean))

    async def set_axis_stopped(self) -> None:
        await asyncio.gather(write_optional(self.ua_actual_speed, 0.0, ua.VariantType.Double),
                             write_optional(self.ua_actual_acceleration, 0.0, ua.VariantType.Double))

    @property
    async def actual_position(self) -> Double:
        return await self.ua_actual_position.read_value()

    @property
    async def actual_speed(self) -> Double | None:
        return await read_optional(self.ua_actual_speed)

    @property
    async def actual_acceleration(self) -> Double | None:
        return await read_optional(self.ua_actual_acceleration)

    async def _delete_empty_folders(self, parent: Node | None = None) -> None:
        """
        delete additional clutter nodes at the end of instantiation
            -> delete every variable in first level expect of motion profile
        """
        await super()._delete_empty_folders(parent)

        if parent is None or parent == self.ua_node:
            for child in await self.ua_node.get_children():
                if child == self.ua_motion_profile:
                    continue
                elif await child.read_node_class() != 1:  # delete everything that is not an object
                    self.logger.debug("Removing node...", child_node_id=child.nodeid.to_string())
                    await child.delete()
