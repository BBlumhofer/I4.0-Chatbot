from __future__ import annotations

import asyncio
from abc import ABC

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.common import namespace_uri
from pyuaadapter.common.enums import LaserStates, LaserSystemStates, MachineryItemStates, MachineryOperationModes
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import write_optional
from pyuaadapter.server.spatial_object import SpatialObject
from pyuaadapter.server.ua_fsm import UaFiniteStateMachine


class BaseLaser(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing a laser. """

    _int_identifier: ua.Int32 = ua.Int32(1005)  # identifier of AxisType of robotic companion specification

    _laser_state_machine: UaFiniteStateMachine  # state machine according to specification
    ua_laser_system_status: Node  # Node under which all state values are
    ua_controller_is_on: Node
    ua_laser_state: Node

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str, config: BaseConfig,
                 spatial_object: SpatialObject = None, **kwargs):
        """
        Creates a new laser
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_LASER_SYSTEMS_URI,
                         ns_uris_dependency_nodesets={namespace_uri.NS_IA_URI: 0, namespace_uri.NS_MACHINE_TOOLS_URI: 0},
                         **kwargs)
        self.logger = structlog.getLogger("sf.server.laser_tool_spec.Laser", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always component type from laser spec.
                                  but to support reflection of child
        """

        await super().init(parent_node, self._int_identifier)

    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        # no decorator laser systems has mandatory identification
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_status(self):
        # note laser system state machine is the 'true' state machine
        # all state machines may follow this state machine

        # dont handle status change cause laser machine should define all states (see laser spec.)
        await super()._init_status(handle_status_change=False)

        from pyuaadapter.server import UaTypes

        # TODO asyncua problem while instantiating with existing references, therefore delete reference and add again
        _ua_identification = await self.ua_machinery_building_blocks.get_child(f"{UaTypes.ns_di}:Identification")
        _ua_machinery_item_state, _ua_machinery_operation_state = \
            await asyncio.gather(self.ua_laser_system_status.get_child(f"{UaTypes.ns_machinery}:MachineryItemState"),
                                 self.ua_laser_system_status.get_child(f"{UaTypes.ns_machinery}:MachineryOperationMode"))

        await asyncio.gather(_ua_identification.delete(), _ua_machinery_item_state.delete(),
                             _ua_machinery_operation_state.delete())

        # TODO AddIn reference raises error so HasComponent used
        await asyncio.gather(
            self.ua_machinery_building_blocks.add_reference(self.ua_identification_folder, ua.ObjectIds.HasComponent),
            self.ua_laser_system_status.add_reference(self.ua_state_machine, ua.ObjectIds.HasComponent),
            self.ua_laser_system_status.add_reference(self.ua_operation_mode, ua.ObjectIds.HasComponent),
        )

    async def _init_notification(self) -> None:
        await super()._init_notification()

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        self.ua_laser_system_status = await self.ua_monitoring.get_child(f"{self.ns_idx_cs}:LaserSystemStatus")

        self.ua_controller_is_on, self.ua_laser_state, ua_name = await asyncio.gather(
            self.ua_laser_system_status.get_child(
                [f"{self.ns_idx_cs}:MachineToolsLaserStatus",
                 f"{self.ns_uris_dependency_nodesets[namespace_uri.NS_MACHINE_TOOLS_URI]}:ControllerIsOn"]),
            self.ua_laser_system_status.get_child(
                [f"{self.ns_idx_cs}:MachineToolsLaserStatus",
                 f"{self.ns_uris_dependency_nodesets[namespace_uri.NS_MACHINE_TOOLS_URI]}:LaserState"]),
            self.ua_laser_system_status.get_child(
                [f"{self.ns_idx_cs}:MachineToolsLaserStatus",
                 f"{self.ns_uris_dependency_nodesets[namespace_uri.NS_MACHINE_TOOLS_URI]}:Name"]
            )
        )

        ua_state_machine = await self.ua_laser_system_status.get_child(f"{self.ns_idx_cs}:LaserSystemState")

        self._laser_state_machine = UaFiniteStateMachine("LaserStateMachine", states=LaserSystemStates,
                                            initial=LaserSystemStates.Off)

        self._add_laser_transitions()

        await asyncio.gather(self._laser_state_machine.init(ua_state_machine,
                                                            self.server.get_node(f"ns={self.ns_idx_cs};i=1009")),
                             self._set_machine_tools_laser_status(is_on=False, laser_state=LaserStates.Undefined),
                             ua_name.write_value("LaserState"))
        await asyncio.gather(self._laser_state_machine.enable_historizing(self.server))

    def _add_laser_transitions(self) -> None:
        # internal --> transitions influences and defines all other states
        self._laser_state_machine.add_transition(trigger="off_internal", source="*", dest="Off", after=[self._on_off])
        self._laser_state_machine.add_transition(trigger="laser_on_internal", source="*", dest="LaserOn", after=[self._on_laser_on])
        self._laser_state_machine.add_transition(trigger="error_internal", source="*", dest="Error", after=[self._on_error])
        self._laser_state_machine.add_transition(trigger="maintenance_internal", source="*", dest="Maintenance", after=[self._on_maintenance])
        self._laser_state_machine.add_transition(trigger="laser_ready_internal", source="*", dest="LaserReady", after=[self._on_ready])
        self._laser_state_machine.add_transition(trigger="set_up_internal", source="*", dest="SetUp", after=[self._on_setup])
        self._laser_state_machine.add_transition(trigger="idle_internal", source="*", dest="Idle", after=[self._on_idle])
        self._laser_state_machine.add_transition(trigger="energy_saving_internal", source="*", dest="EnergySaving", after=[self._on_energy_saving])

    async def _on_off(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.OutOfService),
            self.set_current_operation_mode(MachineryOperationModes.None_),
            self._set_machine_tools_laser_status(is_on=False, laser_state=LaserStates.Undefined))

    async def _on_energy_saving(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.OutOfService),
            self.set_current_operation_mode(MachineryOperationModes.Setup),
            self._set_machine_tools_laser_status(is_on=True, laser_state=LaserStates.Undefined))

    async def _on_idle(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.NotExecuting),
            self.set_current_operation_mode(MachineryOperationModes.None_),
            self._set_machine_tools_laser_status(is_on=True, laser_state=LaserStates.Undefined))

    async def _on_setup(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.NotExecuting),
            self.set_current_operation_mode(MachineryOperationModes.None_),
            self._set_machine_tools_laser_status(is_on=False, laser_state=LaserStates.Undefined))

    async def _on_ready(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.Executing),
            self.set_current_operation_mode(MachineryOperationModes.Processing),
            self._set_machine_tools_laser_status(is_on=True, laser_state=LaserStates.Ready))

    async def _on_maintenance(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.Executing),
            self.set_current_operation_mode(MachineryOperationModes.Maintenance),
            self._set_machine_tools_laser_status(is_on=True, laser_state=LaserStates.Undefined))

    async def _on_laser_on(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.Executing),
            self.set_current_operation_mode(MachineryOperationModes.Processing),
            self._set_machine_tools_laser_status(is_on=True, laser_state=LaserStates.Active))

    async def _on_error(self, user=None) -> None:
        await asyncio.gather(
            self.set_current_state(MachineryItemStates.OutOfService),
            self.set_current_operation_mode(MachineryOperationModes.None_),
            self._set_machine_tools_laser_status(is_on=True, laser_state=LaserStates.Error))

    async def _set_machine_tools_laser_status(self, is_on: bool = None, laser_state=None) -> None:
        await asyncio.gather(
            write_optional(self.ua_controller_is_on, is_on),
            write_optional(self.ua_laser_state, laser_state))
