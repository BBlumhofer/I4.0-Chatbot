from abc import ABC

from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.base_skill_finite import BaseSkillFinite
from pyuaadapter.server.components.base_gripper import BaseGripper


class BaseGripperSkill:
    gripper: BaseGripper


class BaseGraspSkill(BaseSkill, BaseGripperSkill, ABC):
    """ Base class for all grasp skills (e.g. used & required for grippers) without state machine"""

    NAME: str = "Grasp"

    def __init__(self, machinery_item: "BaseGripper", suspendable=False, **kwargs):
        super().__init__(name=BaseGraspSkill.NAME, machinery_item=machinery_item, suspendable=suspendable, **kwargs)
        self.gripper = machinery_item


class BaseFiniteGraspSkill(BaseGraspSkill, BaseSkillFinite, ABC):
    """ Base class for all grasp skills (e.g. used & required for grippers) with state machine """
    pass


class BaseReleaseSkill(BaseSkill, BaseGripperSkill, ABC):
    """ Base class for all release skills (used & required) without state machine"""

    NAME: str = "Release"

    def __init__(self, machinery_item: "BaseGripper", suspendable=False, **kwargs):
        super().__init__(name=BaseReleaseSkill.NAME, machinery_item=machinery_item, suspendable=suspendable, **kwargs)
        self.gripper = machinery_item


class BaseFiniteReleaseSkill(BaseReleaseSkill, BaseSkillFinite, ABC):
    """ Base class for all release skills (e.g. used & required for grippers) with state machine """
    pass