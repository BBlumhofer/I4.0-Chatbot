from __future__ import annotations

import asyncio
import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, List, Type

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.common.enums import GripPointType
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import read_optional, write_optional
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:  # prevent circular imports during run-time
    from pyuaadapter.server.components.component_data_classes import Gripper
    from pyuaadapter.server.skills.base_gripper_skills import BaseGraspSkill, BaseGripperSkill, BaseReleaseSkill


class BaseGripper(BaseComponent, ABC):
    """ Abstract base class representing a gripper. """
    # TODO check EoAT specification (End-of-arm-Tools): https://opcfoundation.org/markets-collaboration/eoat/

    ua_is_open: Node
    ua_grip_point_type: Node
    ua_part_gripped: Node | None  # optionals

    grasp_skill: BaseGraspSkill | None
    release_skill: BaseReleaseSkill | None

    _grip_point_type: GripPointType
    _gripper_values: Gripper

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 gripper_values: Gripper, spatial_object: SpatialObject = None,
                 grasp_skill: Type[BaseGraspSkill] = None, grasp_skill_kwargs: Dict[str, Any] = None,
                 release_skill: Type[BaseReleaseSkill] = None, release_skill_kwargs: Dict[str, Any] = None):
        """
        Creates a new gripper
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object)

        self._grip_point_type = gripper_values.grip_point_type
        self._gripper_values = gripper_values
        self.release_skill = None
        self.grasp_skill = None
        self._gripper_skills: List[Type[BaseGripperSkill]] =\
            [_skill for _skill in [grasp_skill, release_skill] if _skill is not None]
        self._skill_kwargs: List[Dict[str, Any]] =\
            [_skill for _skill in [grasp_skill_kwargs, release_skill_kwargs] if _skill is not None]
        self.logger = structlog.getLogger("sf.server.Gripper", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always gripper_type but to support reflection of child
        """
        from pyuaadapter.server import UaTypes
        await super().init(folder_node=parent_node, component_type=UaTypes.gripper_type)

    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_attributes(self) -> None:
        await super()._init_attributes()

        from pyuaadapter.server import UaTypes

        self.ua_grip_point_type = await self.ua_attributes.get_child([f"{UaTypes.ns_machine_set}:GripPointType"])
        await self.ua_grip_point_type.write_value(ua.UInt32(self._grip_point_type), varianttype=ua.VariantType.UInt32)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        self.ua_is_open, self.ua_part_gripped = await asyncio.gather(
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:IsOpen"]),
            self.add_monitoring_variable("PartGripped", False, instantiate=self._gripper_values.instantiate_part_gripped))
        await self.ua_is_open.write_value(False)


    async def _init_skills(self) -> None:
        await super()._init_skills()

        if len(self._gripper_skills) > 0:
            await self.add_skills(skills=self._gripper_skills, skill_kwargs=self._skill_kwargs)

            from pyuaadapter.server.skills.base_gripper_skills import BaseGraspSkill, BaseReleaseSkill

            if BaseGraspSkill.NAME in self.skills:
                self.grasp_skill = self.skills[BaseGraspSkill.NAME]
            if BaseReleaseSkill.NAME in self.skills:
                self.release_skill = self.skills[BaseReleaseSkill.NAME]

    @property
    async def is_open(self) -> bool:
        return await self.ua_is_open.read_value()

    @property
    async def part_gripped(self) -> bool | None:
        return await read_optional(self.ua_part_gripped)

    async def set_gripper_values(self, is_open: bool = None, part_gripped: bool = None):
        if is_open is not None:
            await self.ua_is_open.write_value(is_open)
        if part_gripped is not None:
            await self.ua_part_gripped.write_value(is_open)

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change([self.ua_is_open, self.ua_part_gripped], count=count)

    async def set_gripper_monitoring_values(self, is_open: bool, part_gripped: bool = None) -> None:

        await asyncio.gather(self.ua_is_open.write_value(is_open, ua.VariantType.Boolean),
                             write_optional(self.ua_part_gripped, part_gripped))
