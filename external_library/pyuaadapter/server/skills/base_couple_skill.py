from abc import ABC

from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.base_skill_continuous import BaseSkillContinuous
from pyuaadapter.server.components.base_port import BasePort


class BaseCoupleSkill(BaseSkill, ABC):
    """ Base class for all couple skills (used & required for active ports) without state machine. """

    NAME: str = "CoupleSkill"
    port: 'BasePort'

    def __init__(self, machinery_item: "BasePort", suspendable=False, **kwargs):
        super().__init__(name=BaseCoupleSkill.NAME, machinery_item=machinery_item, suspendable=suspendable, **kwargs)
        self.port = machinery_item


class BaseContinuousCoupleSkill(BaseCoupleSkill, BaseSkillContinuous, ABC):
    """ Base class for all couple skills (used & required for active ports) with state machine. """
    pass