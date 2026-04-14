from __future__ import annotations

from abc import ABC

from asyncua import Node
from typing_extensions import override, TYPE_CHECKING

from pyuaadapter.server.base_skill_continuous import BaseSkillContinuous
from pyuaadapter.server.base_skill_logic import TRIGGER

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem


class BaseStartupSkill(BaseSkillContinuous, ABC):
    """ The base for a basic startup skill. """

    NAME = "StartupSkill"

    def __init__(self, machinery_item: 'BaseMachineryItem',
                 minimum_access_level = 1,  # Orchestrator as default value
                 handle_running_success_trigger: TRIGGER | None = "halt"):
        super().__init__(name=BaseStartupSkill.NAME, machinery_item=machinery_item,
                         minimum_access_level = minimum_access_level,
                         handle_running_success_trigger=handle_running_success_trigger)

    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location)


    @override
    async def _handle_starting(self):
        # define logic that is executed after entering the STARTING state

        # your module-specific setup/startup code goes here
        await self.machinery_item.reset_components()
        await self.machinery_item.reset_skills()


    @override
    async def _handle_halting(self):
        # define logic that is executed after entering the HALTING state

        # this skill is important for the machine/component to function correctly,
        # so halt the machine/component if this skill is halted
        await self.machinery_item.halt_components()
        await self.machinery_item.halt_skills()



