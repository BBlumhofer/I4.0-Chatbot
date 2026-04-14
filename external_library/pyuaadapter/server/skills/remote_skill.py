from __future__ import annotations

from asyncua import Node, ua, uamethod
from asyncua.server.internal_session import InternalSession
from asyncua.ua import NodeId
from typing_extensions import override

from pyuaadapter.client.base_remote_callable import RemoteSkillSubscriber
from pyuaadapter.client.base_remote_skill import BaseRemoteSkill, SkillTypes
from pyuaadapter.common.enums import SkillStates
from pyuaadapter.server import UaTypes
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.mixins.remote_mirror import (
    RemoteFinalResultUpdateMixin,
    RemoteMonitoringUpdateMixin,
    RemoteParameterMirrorMixin,
)
from pyuaadapter.server.user import User


class RemoteSkill(
    BaseSkill,
    RemoteSkillSubscriber,
    RemoteParameterMirrorMixin,
    RemoteMonitoringUpdateMixin,
    RemoteFinalResultUpdateMixin
):
    _client_remote_object: BaseRemoteSkill

    def __init__(
        self,
        name: str,
        machinery_item: BaseMachineryItem,
        *,
        client_remote_skill: BaseRemoteSkill,
        minimum_access_level: int = 1,
    ):
        if client_remote_skill is None:
            raise ValueError("No RemoteSkill from Client given!")
        self._client_remote_object = client_remote_skill

        super().__init__(
            name=name,
            machinery_item=machinery_item,
            _type=UaTypes.continuous_skill_type if self.is_continuous else UaTypes.finite_skill_type,
            suspendable=client_remote_skill.suspendable,
            minimum_access_level=minimum_access_level,
        )


    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location=location, existing_node=existing_node)

        await self._init_monitoring_mirror()
        await self._init_parameter_set_mirror()
        await self._init_final_result_data_mirror()

        await self._set_current_state(self._client_remote_object.current_state)

        self._client_remote_object.add_subscriber(self)

    @override
    @property
    def is_finite(self) -> bool:
        return self._client_remote_object.type == SkillTypes.Finite

    @override
    @property
    def is_continuous(self) -> bool:
        return self._client_remote_object.type == SkillTypes.Continuous

    @override
    @uamethod
    async def _ua_start(self, _parent: NodeId, session: InternalSession):
        try:
            await self._condition_access_allowed(session.user)
            await self.start(session.user)
        except ua.UaStatusCodeError as e:
            return ua.StatusCode(e.code)

    @override
    @uamethod
    async def _ua_suspend(self, _parent: NodeId, session: InternalSession):
        try:
            await self._condition_access_allowed(session.user)
            await self.suspend(session.user)
        except ua.UaStatusCodeError as e:
            return ua.StatusCode(e.code)

    @override
    @uamethod
    async def _ua_reset(self, _parent: NodeId, session: InternalSession):
        try:
            await self._condition_access_allowed(session.user)
            await self.reset(session.user)
        except ua.UaStatusCodeError as e:
            return ua.StatusCode(e.code)

    @override
    @uamethod
    async def _ua_halt(self, _parent: NodeId, session: InternalSession):
        try:
            await self._condition_access_allowed(session.user)
            await self.halt(session.user)
        except ua.UaStatusCodeError as e:
            return ua.StatusCode(e.code)

    @override
    async def start(self, user: User | None = None) -> None:
        # subscription based copying is too slow
        # copy local parameters to remote parameters to ensure they are immediately available @ remote server
        self.logger.info("Copying local parameters before starting skill...")
        await self._copy_parameter_set_to_remote()
        await self._client_remote_object.start()

    @override
    async def suspend(self, user: User | None = None) -> None:
        await self._client_remote_object.suspend()

    @override
    async def reset(self, user: User | None = None) -> None:
        await self._client_remote_object.reset()

    @override
    async def halt(self, user: User | None = None) -> None:
        await self._client_remote_object.halt()

    ############################################################################################################
    # (Client) RemoteComponent callback methods
    ###########################################################################################################

    @override
    async def on_skill_state_change(self, new_state: SkillStates) -> None:
        await self._set_current_state(new_state)
