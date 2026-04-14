from abc import ABC

from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.base_skill_finite import BaseSkillFinite


class BaseMoveToSkill(BaseSkill, ABC):
    """ Base class for all move to skills (used & required) without state machine. """
    NAME: str = "MoveTo"

    PARAM_NAME_POSITION = "TargetPosition"
    PARAM_NAME_SPEED = "TargetSpeed"


class BaseFiniteMoveToSkill(BaseMoveToSkill, BaseSkillFinite, ABC):
    """ Base class for all move to skills (used & required) with state machine. """
    pass


class BaseHomingSkill(BaseSkill, ABC):
    """ Base class for all homing skills (used & required) without state machine. """
    NAME: str = "Homing"


class BaseFiniteHomingSkill(BaseSkillFinite, BaseHomingSkill, ABC):
    """ Base class for all homing skills (used & required) with state machin. """
    pass


class BaseCallJobSkill(BaseSkill, ABC):
    """ Base class for all call job skills (used & required) without state machine. """
    NAME: str = "CallJob"

    PARAM_NAME_JOB_ID = "JobId"