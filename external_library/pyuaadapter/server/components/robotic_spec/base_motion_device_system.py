from __future__ import annotations

import asyncio
import logging
from abc import ABC

import structlog
from asyncua import Node, Server, ua
from asyncua.ua.uaerrors import BadNoMatch

from pyuaadapter.common import namespace_uri
from pyuaadapter.server import UaTypes
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.common import add_object


class BaseMotionDeviceSystem(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing a motion device system. """

    ua_motion_device_system: Node
    ua_motion_devices: Node
    ua_controllers: Node
    ua_safety_states: Node

    _motion_device_system = "MotionDeviceSystem"
    _int_identifier: ua.Int32 = ua.Int32(1002)  # identifier of MotionDeviceSystemType of robotic companion specification

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BaseMotionDeviceSystem, cls).__new__(cls)
            cls._instance.ua_motion_device_system = None

        return cls._instance

    def __init__(self, server: Server, ns_idx: int):
        """
        Creates a new motion device system
        """

        super().__init__(server, ns_idx=ns_idx,
                         _id=None, name=None, config=None, parent=None, # not needed
                         ns_uri_cs=namespace_uri.NS_ROBOTICS_URI)
        self.logger = structlog.getLogger("sf.server.robotic_spec.MotionDeviceSystem", name=self.full_name)


    async def init(self) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always component type from robotic spec.
                                  but to support reflection of child
        """

        # for motion device system check creation of motion device system

        if self.ua_motion_device_system is not None:
            return

        self.ns_idx_cs = await super()._init_namespace(self.ns_uri_cs, self.ns_uris_dependency_nodesets)
        device_set = await self.server.get_objects_node().get_child(f"{UaTypes.ns_di}:DeviceSet")

        try:
            # check if motion device systems exist
            self.ua_motion_device_system = await device_set.get_child(f"{self.ns_idx_cs}:{self._motion_device_system}")
        except BadNoMatch:
            ua_motion_device_system_type = self.server.get_node(f"ns={self.ns_idx_cs};i=1002")
            self.ua_motion_device_system = await add_object(ns_idx=self.ns_idx, location=device_set,
                                                       bname=ua.QualifiedName(self._motion_device_system, self.ns_idx_cs),
                                                       object_tyoe=ua_motion_device_system_type
                                                       )
        self.ua_motion_devices, self.ua_controllers, self.ua_safety_states = \
            await asyncio.gather(self.ua_motion_device_system.get_child(f"{self.ns_idx_cs}:MotionDevices"),
                                 self.ua_motion_device_system.get_child(f"{self.ns_idx_cs}:Controllers"),
                                 self.ua_motion_device_system.get_child(f"{self.ns_idx_cs}:SafetyStates"))

        # delete clutter ...
        await asyncio.gather(self._delete_children(self.ua_motion_devices),
                             self._delete_children(self.ua_controllers),
                             self._delete_children(self.ua_safety_states))  # remove clutter ...

    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        pass

    async def add_motion_device_reference(self, ua_node: Node):
        await self.ua_motion_devices.add_reference(ua_node, ua.ObjectIds.HasComponent)

    async def add_controller_reference(self, ua_node: Node):
        await self.ua_controllers.add_reference(ua_node, ua.ObjectIds.HasComponent)

    async def add_safety_state_reference(self, ua_node: Node):
        await self.ua_safety_states.add_reference(ua_node, ua.ObjectIds.HasComponent)
