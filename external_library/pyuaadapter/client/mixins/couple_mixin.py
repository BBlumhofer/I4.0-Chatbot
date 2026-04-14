from __future__ import annotations

from abc import ABC

from asyncua.ua.uaerrors import BadInvalidState

from pyuaadapter.client.base_remote_skill import BaseRemoteSkill
from pyuaadapter.common.enums import SkillStates

COUPLE_SKILL_NAME = "CoupleSkill"


class CoupleMixin(ABC):
    """ Mixin providing couple functionality, mainly useful for port(-like) components. """
    skill_set: dict[str, BaseRemoteSkill]
    partner_rfid_tag: str

    async def couple(self, timeout: float | None = 30.0) -> None:
        """
        Tries to couple the remote port to another port.
        Might fail if there is not another port close enough.
        """
        if self.skill_set[COUPLE_SKILL_NAME].current_state == SkillStates.Halted:
            try:
                await self.skill_set[COUPLE_SKILL_NAME].reset()
                await self.skill_set[COUPLE_SKILL_NAME].wait_for_state(SkillStates.Ready, timeout=timeout)
            except BadInvalidState:
                # was already in READY, happens if server-side state changes before client realizes (subscription delay)
                pass
        if not self.coupled:
            await self.skill_set[COUPLE_SKILL_NAME].start()
            await self.skill_set[COUPLE_SKILL_NAME].wait_for_state(SkillStates.Running, timeout=timeout)

    async def uncouple(self, timeout: float | None = 30.0) -> None:
        """ Uncouples the remote port. """
        await self.skill_set[COUPLE_SKILL_NAME].halt()
        await self.skill_set[COUPLE_SKILL_NAME].wait_for_state(SkillStates.Halted, timeout=timeout)
        await self.skill_set[COUPLE_SKILL_NAME].reset()
        await self.skill_set[COUPLE_SKILL_NAME].wait_for_state(SkillStates.Ready, timeout=timeout)

    @property
    def coupled(self) -> bool:
        """ Returns whether this remote port is coupled to another port (of another module). """
        try:
            return self.skill_set[COUPLE_SKILL_NAME].current_state == SkillStates.Running
        except KeyError:  # no couple skill -> passive port
            return self.partner_rfid_tag != ""  # TODO is there a better way hardware-wise?
