from abc import ABC

from asyncua.ua import QualifiedName
from typing_extensions import override

from .base_skill_finite import BaseSkillFinite
from .ua_types import UaTypes


class BaseFeasibilityCheck(BaseSkillFinite, ABC):
    """ Base class for feasibility checks for skills. """

    @override
    async def _get_sub_node(self):
        return await self._ua_node.get_child(QualifiedName("FeasibilityCheck", UaTypes.ns_skill_set))
