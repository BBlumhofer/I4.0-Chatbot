from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC
from typing import Coroutine, Dict, List

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.common import namespace_uri
from pyuaadapter.common.enums import MotionDeviceCategory
from pyuaadapter.server import BaseConfig, UaTypes
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import add_object, add_reference, create_missing_objects, write_unit
from pyuaadapter.server.components.base_gripper import BaseGripper
from pyuaadapter.server.components.component_data_classes import Roboter
from pyuaadapter.server.components.robotic_spec.base_axis import BaseAxis
from pyuaadapter.server.components.robotic_spec.base_motion_device_system import BaseMotionDeviceSystem
from pyuaadapter.server.components.robotic_spec.base_power_train import BasePowerTrain
from pyuaadapter.server.spatial_object import SpatialObject


class BaseMotionDevice(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing a roboter. """

    ua_axes: Node
    ua_power_trains: Node
    ua_device_category: Node
    ua_flange_load: Node | None  # optional
    ua_motion_device_category: Node
    ua_speed_override: Node
    ua_on_path: Node | None  # optional
    ua_in_control: Node | None  # optional

    _int_identifier: ua.Int32 = ua.Int32(
        1004)  # identifier of MotionDeviceType of robotic companion specification
    _motion_device_category: MotionDeviceCategory
    _roboter_values: Roboter

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 roboter_values: Roboter, spatial_object: SpatialObject = None):
        """
        Creates a new motion device system
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)

        self._motion_device_category = roboter_values.motion_device_category
        self._roboter_values = roboter_values
        self.logger = structlog.getLogger("sf.server.robotic_spec.MotionDevice", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always component type from robotic spec.
                                  but to support reflection of child
        """

        await super().init(parent_node, self._int_identifier)

        _motion_device_system = BaseMotionDeviceSystem(self.server, self.ns_idx)
        await _motion_device_system.init()
        await _motion_device_system.add_motion_device_reference(self.ua_node)

    @create_missing_objects("Identification", "component_identification_type", "ns_di")
    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        await super()._init_component_identification()

        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_attributes(self) -> None:
        await super()._init_attributes()

        (self.ua_axes, self.ua_power_trains, self.ua_motion_device_category) = await asyncio.gather(
            self.ua_node.get_child(f"{self.ns_idx_cs}:Axes"),
            self.ua_node.get_child(f"{self.ns_idx_cs}:PowerTrains"),
            self.ua_node.get_child(f"{self.ns_idx_cs}:MotionDeviceCategory"))

        # delete placeholder
        await asyncio.gather(self._delete_children(self.ua_axes), self._delete_children(self.ua_power_trains))

        await asyncio.gather(self.ua_motion_device_category.write_value(ua.Int32(self._motion_device_category),
                                                                varianttype=ua.VariantType.UInt32),
                             self._add_load_object())

    async def _add_load_object(self):

        if not self._roboter_values.instantiate_load:
            self.ua_flange_load = None
            return

        self.ua_flange_load = await add_object(ns_idx=self.ns_idx, location=self.ua_node,
                                                   object_tyoe=self.server.get_node(f"ns={self.ns_idx_cs};i=1018"),
                                                   bname=ua.QualifiedName("FlangeLoad", self.ns_idx_cs))

        ua_mass, _ = await asyncio.gather(
            self.ua_flange_load.get_child(f"{self.ns_idx_cs}:Mass"),
            add_reference(self.ua_attributes, self.ua_flange_load, _dict=self.ua_attribute_nodes))

        await asyncio.gather(ua_mass.write_value(ua.Double(self._roboter_values.load),
                                                 varianttype=ua.VariantType.Double),
                             write_unit(ua_mass, self._roboter_values.load_unit))

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        # Note: ParameterSet from Robotic Specification --> Same ns (di) as our parameter set, be carefully!
        await super()._init_parameter_set()

        (self.ua_speed_override, _) =\
            await asyncio.gather(self.ua_parameter_set.get_child(f"{self.ns_idx_cs}:SpeedOverride"),
                                 self._handle_optionals())

        await add_reference(self.ua_monitoring, self.ua_speed_override, _dict=self.ua_monitoring_nodes)
        self.ua_monitoring_nodes["SpeedOverride"] = self.ua_speed_override

    async def _handle_optionals(self):
        self.ua_on_path = \
            await self.add_monitoring_variable(name="OnPath", val=False,
                                               instantiate=self._roboter_values.instantiate_on_path)

        if self.ua_on_path is not None:
            await add_reference(self.ua_parameter_set, self.ua_on_path, _dict=self.ua_parameter_set_nodes)

        self.ua_in_control = \
            await self.add_monitoring_variable(name="InControl", val=False,
                                               instantiate=self._roboter_values.instantiate_in_control)
        if self.ua_in_control is not None:
            await add_reference(self.ua_parameter_set, self.ua_in_control, _dict=self.ua_parameter_set_nodes)

    async def _init_components(self) -> None:
        await super()._init_components()

        if self._roboter_values.axes is not None:
            for n, axis_values in enumerate(self._roboter_values.axes):

                kwargs = {} if axis_values.component_kwargs is None else axis_values.component_kwargs
                axis = await self.add_component(_id=str(uuid.uuid4()), name=f"Axis_{n + 1}",
                                                component_type=axis_values.component_type,
                                                axis_values=axis_values,
                                                **kwargs)
                await self.ua_axes.add_reference(axis.ua_node, ua.ObjectIds.HasComponent)

        if self._roboter_values.grippers is not None:
            for n, gripper_values in enumerate(self._roboter_values.grippers):
                gripper = await self.add_component(_id=str(uuid.uuid4()), name=f"Gripper_{n + 1}",
                                                   component_type=gripper_values.component_type,
                                                   gripper_values=gripper_values)

        if self._roboter_values.power_trains is not None:
            for n, power_train_values in enumerate(self._roboter_values.power_trains):
                kwargs = {} if power_train_values.component_kwargs is None else power_train_values.component_kwargs
                power_train = await self.add_component(_id=str(uuid.uuid4()), name=f"PowerTrain_{n + 1}",
                                                       component_type=power_train_values.component_type,
                                                       power_train_values=power_train_values,
                                                       **kwargs)
                await self.ua_power_trains.add_reference(power_train.ua_node, ua.ObjectIds.HasComponent)

    @property
    def axes(self) -> Dict[str, BaseAxis]:
        return {key: value for key, value in self.components.items() if isinstance(value, BaseAxis)}

    @property
    def power_trains(self) -> Dict[str, BasePowerTrain]:
        return {key: value for key, value in self.components.items() if isinstance(value, BasePowerTrain)}

    @property
    def grippers(self) -> Dict[str, BaseGripper]:
        return {key: value for key, value in self.components.items() if isinstance(value, BaseGripper)}

    async def _delete_empty_folders(self, parent: Node | None = None) -> None:
        """
        delete additional clutter nodes at the end of instantiation
            -> delete every variable in first level expect of motion device category
            -> delete AdditionalComponents element
        """

        await super()._delete_empty_folders(parent)

        if parent is None or parent == self.ua_node:
            for child in await self.ua_node.get_children():
                if child == self.ua_motion_device_category:
                    continue
                elif await child.read_node_class() != 1 or child.nodeid.Identifier.endswith(".AdditionalComponents"):
                    self.logger.debug("Removing node...", child_node_id=child.nodeid.to_string())
                    await child.delete()

