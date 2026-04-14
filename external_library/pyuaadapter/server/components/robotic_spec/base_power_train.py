from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC
from typing import TYPE_CHECKING, List

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.common import namespace_uri
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import add_reference, create_missing_objects, write_unit
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:
    from pyuaadapter.server.components.component_data_classes import Motor, PowerTrain


class BaseMotor(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing a motor. """

    ua_motor_temperature: Node

    _int_identifier: ua.Int32 = ua.Int32(1019)  # identifier of MotorType of robotic companion specification
    _motor_values: Motor

    ua_motor_temperature: Node

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 motor_values: Motor, spatial_object: SpatialObject = None):

        """
        Creates a new motor
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)
        self._motor_values = motor_values
        self.logger = structlog.getLogger("sf.server.robotic_spec.Motor", name=self.full_name)

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

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        await super()._init_parameter_set()

        self.ua_motor_temperature = await self.ua_parameter_set.get_child(f"{self.ns_idx_cs}:MotorTemperature")
        await asyncio.gather(
            add_reference(self.ua_monitoring, self.ua_motor_temperature, _dict=self.ua_monitoring_nodes),
            write_unit(self.ua_motor_temperature, self._motor_values.motor_temperature_unit))

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change([self.ua_motor_temperature], count=count)

    async def set_motor_temperature(self, value: float) -> None:
        await self.ua_motor_temperature.write_value(ua.Double(value), ua.VariantType.Double)

    async def _delete_empty_folders(self, parent: Node | None = None) -> None:
        """
        delete additional clutter nodes at the end of instantiation
            -> delete every variable in first level expect of motion profile
        """
        await super()._delete_empty_folders(parent)

        if parent is None or parent == self.ua_node:
            for child in await self.ua_node.get_children():
                if await child.read_node_class() != 1:  # delete everything that is not an object
                    self.logger.debug("Removing node...", child_node_id=child.nodeid.to_string())
                    await child.delete()


class BasePowerTrain(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing a power train. """

    _base_motors: List[BaseMotor]
    _power_train_values: PowerTrain

    _int_identifier: ua.Int32 = ua.Int32(16794)  # identifier of PowerTrainType of robotic companion specification

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, power_train_values: PowerTrain, spatial_object: SpatialObject = None):
        """
        Creates a new power train
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)

        self._power_train_values = power_train_values
        self._base_motors = []
        self.logger = structlog.getLogger("sf.server.robotic_spec.PowerTrain", name=self.full_name)

        if self._power_train_values.motors is None or len(self._power_train_values.motors) < 1:
            raise RuntimeError(f"PowerTrain with number of motors {self._power_train_values.motors} not possible!")

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

    async def _init_attributes(self) -> None:
        await super()._init_attributes()

        for child in await self.ua_node.get_children():  # power train object has lots of clutter nodes ..
            await child.delete()

    async def _init_components(self) -> None:
        await super()._init_components()

        for n, motor_values in enumerate(self._power_train_values.motors):
            kwargs = {} if motor_values.component_kwargs is None else motor_values.component_kwargs

            _ua_motor = await self.add_component(_id=str(uuid.uuid4()), name=f"Motor_{n + 1}",
                                                 component_type=motor_values.component_type, motor_values=motor_values,
                                                 **kwargs)
            await self.ua_node.add_reference(_ua_motor.ua_node, ua.ObjectIds.HasComponent)
            self._base_motors.append(_ua_motor)

    @property
    async def motors(self) -> List[BaseMotor]:
        return self._base_motors
