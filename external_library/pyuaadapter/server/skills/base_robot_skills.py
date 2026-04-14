from abc import ABC

from typing_extensions import deprecated

from pyuaadapter.server.components.robotic_spec.base_motion_device import BaseMotionDevice
from pyuaadapter.server.skills.base_skill_templates import BaseMoveToSkill, BaseHomingSkill, BaseFiniteMoveToSkill, \
    BaseFiniteHomingSkill


@deprecated("Use BaseMotionDeviceSkill")
class BaseRobotSkill(ABC):
    robot: BaseMotionDevice


@deprecated("Use BaseMotionDeviceMoveToSkill")
class BaseRobotMoveToSkill(BaseMoveToSkill, BaseRobotSkill, ABC):
    def __init__(self, machinery_item: "BaseMotionDevice", **kwargs):
        super().__init__(name=BaseMoveToSkill.NAME, machinery_item=machinery_item, suspendable=False, **kwargs)
        self.robot = machinery_item


@deprecated("Use BaseFiniteMotionDeviceMoveToSkill")
class BaseFiniteAxisMoveToSkill(BaseRobotMoveToSkill, BaseFiniteMoveToSkill, ABC):
    pass


@deprecated("Use BaseMotionDeviceHomingSkill")
class BaseRobotHomingSkill(BaseHomingSkill, BaseRobotSkill, ABC):
    def __init__(self, machinery_item: "BaseMotionDevice", **kwargs):
        super().__init__(name=BaseHomingSkill.NAME, machinery_item=machinery_item, suspendable=False, **kwargs)
        self.robot = machinery_item


@deprecated("Use BaseFiniteMotionDeviceHomingSkill")
class BaseFiniteAxisHomingSkill(BaseRobotHomingSkill, BaseFiniteHomingSkill, ABC):
    pass


class BaseMotionDeviceSkill(ABC):
    motion_device: BaseMotionDevice


class BaseMotionDeviceMoveToSkill(BaseMoveToSkill, BaseMotionDeviceSkill, ABC):
    def __init__(self, machinery_item: "BaseMotionDevice", **kwargs):
        super().__init__(name=BaseMoveToSkill.NAME, machinery_item=machinery_item, suspendable=False, **kwargs)
        self.motion_device = machinery_item


class BaseFiniteMotionDeviceMoveToSkill(BaseMotionDeviceMoveToSkill, BaseFiniteMoveToSkill, ABC):
    pass


class BaseMotionDeviceHomingSkill(BaseHomingSkill, BaseMotionDeviceSkill, ABC):
    def __init__(self, machinery_item: "BaseMotionDevice", **kwargs):
        super().__init__(name=BaseHomingSkill.NAME, machinery_item=machinery_item, suspendable=False, **kwargs)
        self.motion_device = machinery_item


class BaseFiniteMotionDeviceHomingSkill(BaseMotionDeviceHomingSkill, BaseFiniteHomingSkill, ABC):
    pass