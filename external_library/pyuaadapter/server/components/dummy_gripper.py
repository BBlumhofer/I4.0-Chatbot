from __future__ import annotations

import asyncio

from typing_extensions import override, TYPE_CHECKING

from pyuaadapter.common.enums import GripPointType
from pyuaadapter.server import Server, BaseConfig
from pyuaadapter.server.components.base_gripper import BaseGripper
from pyuaadapter.server.components.component_data_classes import Gripper
from pyuaadapter.server.skills.base_gripper_skills import BaseFiniteGraspSkill, BaseFiniteReleaseSkill
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem


class DummyGraspSkill(BaseFiniteGraspSkill):
    """
    Dummy implementation of a gripper grasp skill.
    Starts grasp skill with defined delay.
    Set gripper state to 'open'.
    """

    _delay: float

    def __init__(self, machinery_item: BaseGripper, *, delay: float = 5):
        super().__init__(machinery_item)
        self._delay = delay

    @override
    async def _handle_running(self):
        await asyncio.sleep(self._delay)
        await self.gripper.set_gripper_monitoring_values(is_open=False)


class DummyReleaseSkill(BaseFiniteReleaseSkill):
    """
    Dummy implementation of a gripper release skill.
    Checks if gripper is already open and starts release skill with defined delay.
    Set gripper state to 'open'.
    """

    _delay: float

    def __init__(self, machinery_item: BaseGripper, *,delay: float = 5):
        super().__init__(machinery_item)
        self._delay = delay

    @override
    async def _handle_running(self):
        if not await self.gripper.is_open:
            await asyncio.sleep(self._delay)
            await self.gripper.set_gripper_monitoring_values(is_open=True)


class DummyGripper(BaseGripper):
    """
    Dummy implementation of a gripper for development purposes.
    """

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, *, gripper_values: Gripper=Gripper(grip_point_type=GripPointType.Parallel),
                 spatial_object: SpatialObject = None, delay: float = 5):
        super().__init__(server=server, parent=parent, ns_idx=ns_idx, _id=_id, name=name, config=config,
                         gripper_values=gripper_values, spatial_object=spatial_object,
                         grasp_skill=DummyGraspSkill, grasp_skill_kwargs={"delay": delay},
                         release_skill=DummyReleaseSkill, release_skill_kwargs={"delay": delay})