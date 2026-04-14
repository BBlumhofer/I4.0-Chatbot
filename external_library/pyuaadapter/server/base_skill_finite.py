from __future__ import annotations

from abc import ABC
from typing import Optional, TYPE_CHECKING

from asyncua import Node
from asyncua.ua import QualifiedName, VariantType
from asyncua.ua.uaerrors import BadNoMatch
from typing_extensions import override

from pyuaadapter.common.util import write_value
from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.base_skill_logic import BaseSkillLogic

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem


class BaseSkillFinite(BaseSkillLogic, ABC):
    """ Abstract base class for all finite skills. """
    ua_successful_executions_count: Optional[Node]  # OPC UA node counting the successful executions

    def __init__(self, name: str, machinery_item: 'BaseMachineryItem', suspendable: bool = False,
                 minimum_access_level: int = 1,
                 precondition_check: BaseSkill | None = None, feasibility_check: BaseSkill | None = None):

        from pyuaadapter.server import UaTypes # here to avoid circular import
        super().__init__(name=name, machinery_item=machinery_item, _type=UaTypes.finite_skill_type,
                         suspendable=suspendable, minimum_access_level=minimum_access_level,
                         precondition_check=precondition_check, feasibility_check=feasibility_check)

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location=location, existing_node=existing_node)

        from pyuaadapter.server.ua_types import UaTypes  # here to avoid circular import

        try:
            self.ua_successful_executions_count = await self.ua_final_result_data.get_child(
                QualifiedName("SuccessfulExecutionsCount", UaTypes.ns_skill_set))
        except BadNoMatch:  # Optional, FeasibilityChecks do not have it
            self.ua_successful_executions_count = None

    @override
    async def _add_transitions(self) -> None:
        await super()._add_transitions()

        # the only difference between finite and continuous skills is that finite skills have the completed state.
        # hence, we only need to add missing transitions
        self._machine.add_transition(
            trigger="done_internal", source="Running", dest="Completing", after=self._after_completing
        )
        self._machine.add_transition(trigger="done_internal", source="Completing", dest="Completed")

    @override
    async def _after_running(self, *args, **kwargs):
        """Is called by the finite state machine after the RUNNING state is entered."""
        await self._wrap_handle_method(self._handle_running, "done_internal")

    async def _after_completing(self, *args, **kwargs):
        """Is called by the finite state machine after the COMPLETED state is entered."""
        # Update successful executions count if it exists
        if self.ua_successful_executions_count is not None:
            old_value = await self.ua_successful_executions_count.read_value()
            new_value = old_value + 1 if old_value is not None else 1
            await write_value(self.ua_successful_executions_count, new_value, VariantType.UInt32)

        await self._wrap_handle_method(self._handle_completing, "done_internal")


    async def _handle_completing(self):
        """Is called to handle user-specific logic during the COMPLETING state. After this function is done,
        the skill will automatically advance to the COMPLETED state."""
        pass
