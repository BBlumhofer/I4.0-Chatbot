from __future__ import annotations

import asyncio
import logging

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.common import namespace_uri
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.common import add_reference
from pyuaadapter.server.components.robotic_spec.base_motion_device_system import BaseMotionDeviceSystem


class BaseSafetyState(BaseCompanionSpecificationComponent):
    """ Abstract base class representing a safety state. """

    _int_identifier: ua.Int32 = ua.Int32(1013)  # identifier of SafetyStateType of robotic companion specification

    ua_emergency_stop: Node
    ua_protective_stop: Node
    ua_operational_mode: Node | None

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object=None):  # spatial object for reflection

        """
        Creates a new safety state
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)
        self.logger = structlog.getLogger("sf.server.robotic_spec.SafetyState", name=self.full_name)

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
        await _motion_device_system.add_safety_state_reference(self.ua_node)


    async def _init_component_identification(self) -> None:
        return  # no identification required

    async def _init_parameter_set(self) -> None:
        await super()._init_parameter_set()
        await super()._init_monitoring()


        self.ua_emergency_stop, self.ua_operational_mode, self.ua_protective_stop = await asyncio.gather(
            self.ua_parameter_set.get_child([f"{self.ns_idx_cs}:EmergencyStop"]),
            self.ua_parameter_set.get_child([f"{self.ns_idx_cs}:OperationalMode"]),
            self.ua_parameter_set.get_child([f"{self.ns_idx_cs}:ProtectiveStop"]))

        await asyncio.gather(
            add_reference(self.ua_monitoring, self.ua_emergency_stop, _dict=self.ua_monitoring_nodes),
            add_reference(self.ua_monitoring, self.ua_operational_mode, _dict=self.ua_monitoring_nodes),
            add_reference(self.ua_monitoring, self.ua_protective_stop, _dict=self.ua_monitoring_nodes))

