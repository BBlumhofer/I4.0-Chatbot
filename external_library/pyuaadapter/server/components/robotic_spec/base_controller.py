from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Coroutine, List

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.common import namespace_uri
from pyuaadapter.server import BaseConfig, UaTypes
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.common import add_object, add_reference, create_missing_objects
from pyuaadapter.server.components.robotic_spec.base_motion_device_system import BaseMotionDeviceSystem
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:
    from pyuaadapter.server.components.component_data_classes import Controller, TaskControl


class BaseSoftware(BaseCompanionSpecificationComponent):
    """ Abstract base class representing a software. """

    _int_identifier: ua.Int32 = ua.Int32(15106)  # identifier of ControllerType of robotic companion specification

    ua_manufacturer: Node
    ua_model: Node
    ua_software_revision: Node

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object=None):  # spatial object for reflection

        """
        Creates a new software
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         ns_uri_cs=namespace_uri.NS_DI_URI)
        self.logger = structlog.getLogger("sf.server.robotic_spec.Software", name=self.full_name)

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
                                             product_instance_uri: str = None, software_revision: str = None,
                                             model: str = None) -> None:

        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

        self.ua_manufacturer, self.ua_model, self.ua_software_revision = await asyncio.gather(
            self.ua_node.get_child([f"{self.ns_idx_cs}:Manufacturer"]),
            self.ua_node.get_child([f"{self.ns_idx_cs}:Model"]),
            self.ua_node.get_child([f"{self.ns_idx_cs}:SoftwareRevision"]))

        await asyncio.gather(self.ua_identification_folder.add_reference(self.ua_model, ua.ObjectIds.HasProperty),
                             self.ua_identification_folder.add_reference(self.ua_software_revision, ua.ObjectIds.HasProperty),
                             self.ua_model.write_value(ua.LocalizedText("" if model is None else model, "en-US")),
                             self.ua_software_revision.write_value("" if software_revision is None else software_revision),
                             self.ua_manufacturer.delete())

        await self.ua_node.add_reference(self.ua_identification_nodes["Manufacturer"], ua.ObjectIds.HasProperty)


class BaseTaskControl(BaseCompanionSpecificationComponent):
    """ Abstract base class representing a task control. """

    _task_control_values: 'TaskControl'
    _int_identifier: ua.Int32 = ua.Int32(1011)  # identifier of TaskControllerType of robotic companion specification

    ua_task_program_loaded: Node
    ua_task_program_name: Node
    ua_execution_mode: Node | None # optional

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, task_control_values: 'TaskControl', spatial_object=None):
                # spatial object for reflection

        """
        Creates a new task control
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)
        self._task_control_values = task_control_values
        self.logger = structlog.getLogger("sf.server.robotic_spec.TaskControl", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always component type from robotic spec.
                                  but to support reflection of child
        """

        await super().init(parent_node, self._int_identifier)

    async def _init_component_identification(self) -> None:
        await (await self.ua_node.get_child(f"{UaTypes.ns_di}:ComponentName")).write_value(ua.LocalizedText(self.name, "en-US"))

    async def _init_monitoring(self) -> None:
        await super()._init_parameter_set()
        await super()._init_attributes()

        self.ua_task_program_loaded, self.ua_task_program_name, self.ua_execution_mode = await asyncio.gather(
            self.ua_parameter_set.get_child([f"{self.ns_idx_cs}:TaskProgramLoaded"]),
            self.ua_parameter_set.get_child([f"{self.ns_idx_cs}:TaskProgramName"]),
            self.add_attribute_variable("ExecutionMode", 0,
                                        datatype=ua.NodeId(18191, self.ns_idx_cs),
                                        instantiate=self._task_control_values.instantiate_execution_mode))


        await asyncio.gather(
            add_reference(self.ua_attributes, self.ua_task_program_loaded, _dict=self.ua_attribute_nodes),
            add_reference(self.ua_attributes, self.ua_task_program_name, _dict=self.ua_attribute_nodes))

        if self.ua_execution_mode is not None:
            await add_reference(self.ua_parameter_set, self.ua_execution_mode, _dict=self.ua_parameter_set_nodes)

        await self._add_nodes_to_map(self.ua_attributes, self.ua_attribute_nodes)


class BaseController(BaseCompanionSpecificationComponent):
    """ Abstract base class representing a controller. """

    _controller_values: 'Controller'
    _int_identifier: ua.Int32 = ua.Int32(1003)  # identifier of ControllerType of robotic companion specification

    ua_level: Node
    ua_software: Node
    ua_task_control: Node

    ua_cabinet_fan_speed: Node | None  #optional
    ua_cpu_fan_speed: Node | None  #optional
    ua_startup_time: Node | None  #optional
    ua_temperature: Node | None  #optional
    ua_input_voltage: Node | None  #optional
    ua_total_energy_consumption: Node | None  #optional
    ua_total_power_on_time: Node | None  #optional
    ua_ups_state: Node | None  #optional


    _software: List[BaseSoftware]
    _task_controls: List[BaseTaskControl]

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 controller_values: 'Controller', spatial_object: SpatialObject = None):

        """
        Creates a new controller
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)
        self._controller_values = controller_values
        self._software = []
        self._task_controls = []
        self.logger = structlog.getLogger("sf.server.robotic_spec.Controller", name=self.full_name)

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

        self.ua_software, self.ua_task_control, self.ua_level = await asyncio.gather(
            self.ua_node.get_child([f"{self.ns_idx_cs}:Software"]),
            self.ua_node.get_child([f"{self.ns_idx_cs}:TaskControls"]),
            self.ua_node.get_child([f"{self.ns_idx_cs}:CurrentUser", f"{self.ns_idx_cs}:Level"]))

        await asyncio.gather(self._delete_children(self.ua_software), self._delete_children(self.ua_task_control))

        await _motion_device_system.add_controller_reference(self.ua_node)
        [await self.ua_software.add_reference(software.ua_node, ua.ObjectIds.HasComponent) for software in self._software]
        [await self.ua_task_control.add_reference(task_control.ua_node, ua.ObjectIds.HasComponent) for task_control in self._task_controls]


    @create_missing_objects("Identification", "component_identification_type", "ns_di")
    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_monitoring(self) -> None:
        if self._controller_values.instantiate_parameter_set:
            self.ua_parameter_set = await add_object(ns_idx=self.ns_idx, location=self.ua_node,
                                                     bname=ua.QualifiedName("ParameterSet", self.ns_idx_cs),
                                                     object_tyoe=ua.ObjectIds.BaseObjectType)
        else:
            return

        await super()._init_monitoring()

        self.ua_cabinet_fan_speed = \
            await self.add_monitoring_variable(name="CabinetFanSpeed", val=0.0, varianttype=ua.VariantType.Double,
                                               unit=self._controller_values.cabinet_fan_speed_unit,
                                               instantiate=self._controller_values.instantiate_cabinet_fan_speed)
        self.ua_cpu_fan_speed = \
            await self.add_monitoring_variable(name="CPUFanSpeed", val=0.0, varianttype=ua.VariantType.Double,
                                               unit=self._controller_values.cpu_fan_speed_unit,
                                               instantiate=self._controller_values.instantiate_cpu_fan_speed)
        self.ua_startup_time = \
            await self.add_monitoring_variable(name="StartUpTime", val="",
                                               instantiate=self._controller_values.instantiate_startup_time,
                                               varianttype=ua.VariantType.DateTime)

        self.ua_input_voltage = \
            await self.add_monitoring_variable(name="InputVoltage", val=0.0, varianttype=ua.VariantType.Double,
                                               unit=self._controller_values.input_voltage_unit,
                                               instantiate=self._controller_values.instantiate_input_voltage)
        self.ua_temperature = \
            await self.add_monitoring_variable(name="Temperature", val=0.0, varianttype=ua.VariantType.Double,
                                               unit=self._controller_values.temperature_unit,
                                               instantiate=self._controller_values.instantiate_temperature)

        self.ua_total_energy_consumption = \
            await self.add_monitoring_variable(name="TotalEnergyConsumption", val=0.0, varianttype=ua.VariantType.Double,
                                               unit=self._controller_values.total_energy_consumption_unit,
                                               instantiate=self._controller_values.instantiate_total_energy_consumption)

        self.ua_total_power_on_time = \
            await self.add_monitoring_variable(name="TotalPowerOnTime", val="",
                                               instantiate=self._controller_values.instantiate_total_power_on_time)

        self.ua_ups_state = \
            await self.add_monitoring_variable(name="UpsState", val="",
                                               instantiate=self._controller_values.instantiate_ups_state)

        for name, node in self.ua_monitoring_nodes.items():
            await add_reference(self.ua_parameter_set, node, _dict=self.ua_parameter_set_nodes)

        for n in range(self._controller_values.softwares):
            software = BaseSoftware(_id=str(uuid.uuid4()), name=f"Software{n+1}", server=self.server, parent=self,
                                    ns_idx=self.ns_idx, config=self.config)
            await software.init(self.ua_monitoring)
            self._software.append(software)

        for n, task_control_values in enumerate(self._controller_values.task_controls):
            kwargs = {} if task_control_values.component_kwargs is None else task_control_values.component_kwargs
            task_control = task_control_values.component_type(_id=str(uuid.uuid4()), name=f"TaskControl{n+1}", server=self.server,
                                                  parent=self, task_control_values=task_control_values,
                                                  ns_idx=self.ns_idx, config=self.config, **kwargs)
            await task_control.init(self.ua_monitoring)
            self._task_controls.append(task_control)


    # async def _init_components(self) -> None:
    #     await super()._init_components()
    #
    #     for n in range(self._controller_values.software_numbers):
    #         software = await self.add_component(_id=str(uuid.uuid4()), name=f"Software{n+1}", component_type=BaseSoftware)
    #         self._software.append(software)
    #
    #     for n, task_control in enumerate(self._controller_values.task_controls):
    #         task_control = await self.add_component(_id=str(uuid.uuid4()), name=f"TaskControl{n+1}", component_type=BaseTaskControl,
    #                                                task_control_values=task_control)
    #         self._task_controls.append(task_control)

    async def _delete_empty_folders(self, parent: Node | None = None) -> None:
        """
        delete additional clutter nodes at the end of instantiation
            -> delete every variable in first level expect of motion device category
        """

        await super()._delete_empty_folders(parent)

        if parent is None or parent == self.ua_node:
            for child in await self.ua_node.get_children():
                if await child.read_node_class() != 1:
                    self.logger.debug("Removing node...", child_node_id=child.nodeid.to_string())
                    await child.delete()

        [await self.ua_node.add_reference(node, ua.ObjectIds.HasProperty) for _,node in self.ua_identification_nodes.items()]