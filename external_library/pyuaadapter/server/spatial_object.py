from __future__ import annotations

import asyncio
import uuid
from typing import Dict

from asyncua import Node, ua
from asyncua.ua import NodeId, ObjectIds
from asyncua.ua.uaerrors import BadNoMatch

from .common import add_object, write_unit
from .data_classes import Orientation, Position
from .ua_types import UaTypes


class SpatialLocationType:
    """
    Spatial Location Type (SLT) from Relative Spacial Location specification:

    SLT has base (NodeId), Orientation (Angles) and Position (Length) in three coordinates
    """

    _position: Position
    _orientation: Orientation
    _base: NodeId | None # references the node (position frame) that describes the relative coordinate system

    # set nodes when object is created in opc ua server
    _ua_node: Node
    _ua_position: Node | None
    _ua_orientation: Node | None
    _ua_base: Node | None

    # position in cartesian
    _ua_x: Node
    _ua_y: Node
    _ua_z: Node

    # orientation in cartesian
    _ua_a: Node
    _ua_b: Node
    _ua_c: Node

    def __init__(self, name: str, position: Position, orientation: Orientation, base: NodeId = None):
        self._name = name
        self._position = position
        self._orientation = orientation
        self._base = base

        self._ua_position = None
        self._ua_orientation = None
        self._ua_base = None

    async def init(self, ua_node: Node):
        self._ua_node = ua_node
        self._ua_base, self._ua_position, self._ua_orientation = await asyncio.gather(
            self._ua_node.get_child(f"{UaTypes.ns_rsl}:Base"),
            self._ua_node.get_child(f"{UaTypes.ns_rsl}:Position"),
            self._ua_node.get_child(f"{UaTypes.ns_rsl}:Orientation"))

        (self._ua_x, self._ua_y, self._ua_z,
         self._ua_a, self._ua_b, self._ua_c) = await asyncio.gather(
            self._ua_position.get_child("X"),
            self._ua_position.get_child("Y"),
            self._ua_position.get_child("Z"),
            self._ua_orientation.get_child(f"{UaTypes.ns_rsl}:A"),
            self._ua_orientation.get_child(f"{UaTypes.ns_rsl}:B"),
            self._ua_orientation.get_child(f"{UaTypes.ns_rsl}:C"))

        await asyncio.gather(
            write_unit(self._ua_position, self._position.unit, "LengthUnit"),
            write_unit(self._ua_orientation, self._orientation.unit, "AngleUnit"),
            self._set_ua_position(), self._set_ua_orientation(), self._set_ua_base())

    @property
    def name(self) -> str:
        return self._name

    async def _set_ua_base(self):
        if self._base is None:
            return
        await self._ua_base.write_value(self._base)

    async def _set_ua_position(self):
        if self._ua_position is not None:
            await asyncio.gather(self._ua_x.write_value(ua.Double(self._position.x)),
                                 self._ua_y.write_value(ua.Double(self._position.y)),
                                 self._ua_z.write_value(ua.Double(self._position.z)))

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value: Position):
        self._position = value
        asyncio.create_task(self._set_ua_position())

    async def _set_ua_orientation(self):
        if self._ua_orientation is not None:
            await asyncio.gather(self._ua_a.write_value(ua.Double(self._orientation.a)),
                                 self._ua_b.write_value(ua.Double(self._orientation.b)),
                                 self._ua_c.write_value(ua.Double(self._orientation.c)))

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, value: Orientation):
        self._orientation = value
        asyncio.create_task(self._set_ua_orientation())

    @property
    def base(self) -> NodeId:
        return self._base

    @property
    def ua_node(self) -> Node:
        return self._ua_node


class PositionFrame(SpatialLocationType):
    """
    Subtype of Spatial Location Type with fixed name 'PositionFrame'
    """

    def __init__(self, position: Position, orientation: Orientation, base: NodeId):
        super().__init__("PositionFrame", position,orientation, base)


class WorldFrame(SpatialLocationType):
    """
    Subtype of Spatial Location Type with fixed name 'WorldFrame' and default base=None
    """

    def __init__(self, position: Position, orientation: Orientation):
        super().__init__("WorldFrame", position, orientation)


class SpatialObject:
    """
    Spatial Object (SO)from Relative Spatial Location specification"
    SO contains position frame and attach points with Spatial Location Types
    """

    _parent: "BaseAsset"

    _ua_spatial_object: Node
    _ua_attach_points: Node | None
    _position_frame: PositionFrame
    _attach_points: Dict[str, SpatialLocationType]

    def __init__(self, name: str, position_frame: PositionFrame):
        self.name = name
        self._position_frame = position_frame
        self._ua_attach_points = None
        self._attach_points: Dict[str, SpatialLocationType] = {}

    async def init(self, parent: "BaseAsset", spatial_object_list: SpatialObjectList = None) -> None:
        try:
            self._parent = parent
            self._ua_spatial_object = await self._parent.ua_monitoring.get_child(f"{UaTypes.ns_rsl}:SpatialObject")

            ua_position_frame = await self._ua_spatial_object.get_child(f"{UaTypes.ns_rsl}:PositionFrame")

            if self._position_frame._base is None:
                await self._ua_spatial_object.delete()
                return

            if (await ua_position_frame.read_type_definition()).to_string() != UaTypes.cartesian_frame_angle_orientation_type:
                # TODO quick fix
                await ua_position_frame.delete(recursive=True)
                ua_position_frame = await add_object(ns_idx=self._parent.ns_idx,
                                               bname=ua.QualifiedName("PositionFrame", UaTypes.ns_rsl),
                                               location=self._ua_spatial_object,
                                               object_tyoe=UaTypes.cartesian_frame_angle_orientation_type)

            await self._position_frame.init(ua_position_frame)

            if spatial_object_list is not None:
                await spatial_object_list.add_spatial_object(self)

        except BadNoMatch:
            self._parent.logger.warning("No spatial object for element", parent_name=self._parent.name)

    @property
    def position_frame(self) -> PositionFrame:
        return self._position_frame

    async def add_attach_point(self, attach_point: SpatialLocationType) -> None:

        if self._ua_attach_points is None:
            self._ua_attach_points = await (self._ua_spatial_object.add_folder
                                                (nodeid=ua.NodeId(f"{self._ua_spatial_object.nodeid.Identifier}.AttachPoints",
                                                 self._ua_spatial_object.nodeid.NamespaceIndex),
                                                 bname=ua.QualifiedName("AttachPoints", UaTypes.ns_rsl)))

        ua_attach_point = await add_object(ns_idx=self._parent.ns_idx,
                                           bname=ua.QualifiedName(attach_point.name, UaTypes.ns_rsl),
                                           location=self._ua_attach_points,
                                           object_tyoe=UaTypes.cartesian_frame_angle_orientation_type)

        await attach_point.init(ua_attach_point)
        self._attach_points[attach_point.name] = attach_point

    @property
    def attach_points(self) -> Dict[str, SpatialLocationType]:
        return self._attach_points

    @classmethod
    async def delete(cls, parent: "BaseAsset") -> None:
        try:
            _ua_spatial_object = await parent.ua_monitoring.get_child(f"{UaTypes.ns_rsl}:SpatialObject")
            await _ua_spatial_object.delete()
        except BadNoMatch:
            parent.logger.warning("Cannot delete spatial object", parent_name=parent.name)


class SpatialObjectList:
    """
    Spatial Object List (SOL) from Relative Spatial Location specification"
    SO contains world frame and Spatial Objects
    """

    _name = "MachineRoomList"
    _ua_spatial_object_list: Node
    _spatial_objects: Dict[str, SpatialObject]

    _world_frame: WorldFrame
    _parent: "BaseAsset"

    def __init__(self, world_frame: WorldFrame):
        self._world_frame = world_frame
        self._spatial_objects = {}

    async def init(self, parent: "BaseAsset") -> None:
        try:
            self._parent = parent
            self._ua_spatial_object_list = await self._parent.ua_monitoring.get_child(f"{UaTypes.ns_rsl}:{self._name}")
            ua_world_frame = await self._ua_spatial_object_list.get_child(f"{UaTypes.ns_rsl}:WorldFrame")
            await self._world_frame.init(ua_world_frame)

            await (await self._ua_spatial_object_list.get_child(f"{UaTypes.ns_rsl}:Identifier")).write_value(
                str(uuid.uuid4()))

        except BadNoMatch:
            self._parent.logger.warning("Cannot init spatial object list", parent_name=self._parent.name)

    async def add_spatial_object(self, spatial_object: SpatialObject):
        self._spatial_objects[spatial_object.name] = spatial_object
        await self._ua_spatial_object_list.add_reference(spatial_object._ua_spatial_object, ObjectIds.Organizes)

    @property
    def ua_node(self):
        return self._ua_spatial_object_list

    @property
    def world_frame(self) -> WorldFrame:
        return self._world_frame