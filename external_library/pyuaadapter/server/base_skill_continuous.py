from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from asyncua import Node
from asyncua.ua import QualifiedName, VariantType
from typing_extensions import override

from pyuaadapter.common.util import write_value
from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.base_skill_logic import BaseSkillLogic, TRIGGER

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem


class BaseSkillContinuous(BaseSkillLogic, ABC):
    """ Abstract base class for all continuous skills. """
    ua_successful_starts_count: Node  # opc ua node counting the successful starts

    def __init__(self, name: str, machinery_item: 'BaseMachineryItem', suspendable: bool = False,
                 minimum_access_level: int = 1,
                 precondition_check: BaseSkill | None = None,
                 feasibility_check: BaseSkill | None = None,
                 handle_running_success_trigger: TRIGGER | None = "halt"):

        from pyuaadapter.server import UaTypes
        super().__init__(name=name, machinery_item=machinery_item, _type=UaTypes.continuous_skill_type,
                         suspendable=suspendable, minimum_access_level=minimum_access_level,
                         precondition_check=precondition_check, feasibility_check=feasibility_check)
        self._handle_running_success_trigger = handle_running_success_trigger
        """ Defines which state machine transition trigger should be called after the _handle_running() returns. """

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location=location, existing_node=existing_node)

        from pyuaadapter.server.ua_types import UaTypes  # here to avoid circular import

        self.ua_successful_starts_count = await self.ua_final_result_data.get_child(
            QualifiedName("SuccessfulExecutionsCount", UaTypes.ns_skill_set))

    @override
    async def _after_running(self, *args, **kwargs):
        """Is called by the finite state machine after the RUNNING state is entered."""
        old_value = await self.ua_successful_starts_count.read_value()
        new_value = old_value + 1 if old_value is not None else 1
        await write_value(self.ua_successful_starts_count, new_value, VariantType.UInt32)

        await self._wrap_handle_method(self._handle_running, self._handle_running_success_trigger)


