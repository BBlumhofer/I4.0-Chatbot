from abc import ABC

from pyuaadapter.server.components.robotic_spec.base_axis import BaseAxis
from pyuaadapter.server.skills.base_skill_templates import BaseMoveToSkill, BaseHomingSkill, BaseFiniteMoveToSkill, \
    BaseFiniteHomingSkill


class BaseAxisSkill(ABC):
    axis: BaseAxis


class BaseAxisMoveToSkill(BaseMoveToSkill, ABC):

    def __init__(self, machinery_item: "BaseAxis", suspendable=False, **kwargs):
        super().__init__(name=BaseMoveToSkill.NAME, machinery_item=machinery_item, suspendable=suspendable, **kwargs)
        self.axis = machinery_item


class BaseFiniteAxisMoveToSkill(BaseAxisMoveToSkill, BaseFiniteMoveToSkill, ABC):
    pass


class BaseAxisHomingSkill(BaseHomingSkill, ABC):
    def __init__(self, machinery_item: "BaseAxis", axis_move_to_skill: BaseAxisMoveToSkill, suspendable=False, **kwargs):
        super().__init__(name=BaseHomingSkill.NAME, machinery_item=machinery_item, suspendable=suspendable, **kwargs)
        self.axis = machinery_item
        self.axis_move_to_skill = axis_move_to_skill


class BaseFiniteAxisHomingSkill(BaseAxisHomingSkill, BaseFiniteHomingSkill, ABC):
    pass