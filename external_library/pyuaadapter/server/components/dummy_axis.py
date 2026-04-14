from __future__ import annotations

import asyncio
import operator
from typing import Tuple

from asyncua import Node, ua
from typing_extensions import override

from pyuaadapter.common.enums import MotionProfile, SkillStates
from pyuaadapter.server import BaseConfig, Server
from pyuaadapter.server.components.component_data_classes import Axis
from pyuaadapter.server.components.robotic_spec.base_axis import BaseAxis
from pyuaadapter.server.skills.base_axis_skills import BaseFiniteAxisHomingSkill, BaseFiniteAxisMoveToSkill
from pyuaadapter.server.skills.base_skill_templates import BaseMoveToSkill
from pyuaadapter.server.spatial_object import SpatialObject
from pyuaadapter.server.user import User


class DummyAxisMoveToSkill(BaseFiniteAxisMoveToSkill):
    """
    Dummy implementation of an axis move to skill. Does nothing internally, but simulates the moving process.
    """

    _ua_target_position: Node  # Node of axis position parameter
    _target_position_unit: str  # Unit of axis position parameter
    _target_position_range: Tuple[float, float]  # allowed range of axis speed parameter

    _ua_target_speed: Node  # Node of axis speed parameter
    _target_speed_unit: str  # Unit of axis speed parameter
    _target_speed_range: Tuple[float, float]  # allowed range of axis speed parameter

    _target_position: float   # target position of axis
    _target_position_default: float  # default position parameter
    _target_speed: float   # target speed
    _target_speed_default: float  # default speed parameter

    def __init__(self, machinery_item: BaseAxis, *,
                 target_position_parameter_range: Tuple[float, float] = (0, 100),
                 target_speed_default: float = 1.0, target_speed_range: Tuple[int, int] = (0, 5)):
        super().__init__(machinery_item)

        self._target_position_default = float(target_position_parameter_range[0])
        self._target_position_unit = machinery_item._axis_values.position_unit
        self._target_position_range = target_position_parameter_range

        self._target_speed_default = target_speed_default
        self._target_speed_unit = machinery_item._axis_values.speed_unit
        self._target_speed_range = target_speed_range

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location)
        self._ua_target_position = await self.add_parameter_variable(
            name=BaseMoveToSkill.PARAM_NAME_POSITION, val=self._target_position_default,
            varianttype=ua.VariantType.Double,
            historize=True, unit=self._target_position_unit, _range=self._target_position_range)
        self._ua_target_speed = await self.add_parameter_variable(
            name=BaseMoveToSkill.PARAM_NAME_SPEED, val=self._target_speed_default, varianttype=ua.VariantType.Double,
            historize=True, unit=self._target_speed_unit, _range=self._target_speed_range)

    @override
    async def _handle_resetting(self):
        await self._ua_target_position.write_value(self._target_position_default)
        await self._ua_target_speed.write_value(self._target_speed_default)

    @override
    async def _handle_starting(self):
        self._target_position = await self._ua_target_position.read_value()
        self._target_speed = await self._ua_target_speed.read_value()

    @override
    async def _handle_running(self):

        sleep_time = 0.1

        if self._target_position >= await self.axis.actual_position:
            _operator = operator.add
        else:
            _operator = operator.sub


        while await self.axis.actual_position != self._target_position:
            await asyncio.sleep(sleep_time)

            position_current = _operator(await self.axis.actual_position, sleep_time * self._target_speed)

            if position_current >= self._target_position and _operator == operator.add:
                position_current = self._target_position
            elif position_current <= self._target_position and _operator == operator.sub:
                position_current = self._target_position

            await self.axis.set_axis_monitoring_values(position=position_current, speed=self._target_speed)

        await self.axis.set_axis_monitoring_values(position=self._target_position, speed=0.0)
        await self.axis.set_axis_stopped()



class DummyAxisHomingSkill(BaseFiniteAxisHomingSkill):
    """
    Dummy implementation of an axis homing skill. Does nothing internally, but simulates the moving process.
    """
    axis_move_to_skill: DummyAxisMoveToSkill

    def __init__(self, machinery_item: BaseAxis, axis_move_to_skill: DummyAxisMoveToSkill, *,
                 homing_position: int = 0, homing_speed: float = 5):
        super().__init__(machinery_item, axis_move_to_skill)
        self._homing_position = homing_position
        self._homing_speed = homing_speed

    @override
    async def _handle_resetting(self, *args, **kwargs):
        if self.axis_move_to_skill.current_state in [SkillStates.Halted, SkillStates.Completed]:
            await self.axis_move_to_skill.reset()
            await self.axis_move_to_skill.wait_for_state(SkillStates.Ready)

    @override
    async def _condition_start_allowed(self, _user: User) -> bool:
        return self.axis_move_to_skill.current_state == SkillStates.Ready

    @override
    async def _handle_running(self):
        await self.call_other_finite_skill(
            skill=self.axis_move_to_skill,
            parameters={BaseMoveToSkill.PARAM_NAME_POSITION: self._homing_position,
                      BaseMoveToSkill.PARAM_NAME_SPEED: self._homing_speed},
            timeout=None)


class DummyAxis(BaseAxis):
    """
    Dummy implementation of a axis for development purposes.
    """

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, *, axis_values: Axis = Axis(motion_profile=MotionProfile.Linear),
                 spatial_object: SpatialObject = None,
                 target_position_parameter_range: Tuple[int, int] = (0, 100),
                 target_speed_default: float = 1.0, target_speed_range: Tuple[int, int] = (0, 5),
                 homing_position: float = 0.0, homing_speed: float = 1.0):

        super().__init__(server=server, parent=parent, ns_idx=ns_idx, _id=_id, name=name, config=config,
                         axis_values=axis_values, spatial_object=spatial_object,
                         move_to_skill=DummyAxisMoveToSkill,
                         move_to_skill_kwargs={
                             "target_position_parameter_range": target_position_parameter_range,
                             "target_speed_default": target_speed_default, "target_speed_range": target_speed_range},
                         homing_skill=DummyAxisHomingSkill,
                         homing_skill_kwargs={
                             "homing_position": homing_position,
                             "homing_speed": homing_speed})

