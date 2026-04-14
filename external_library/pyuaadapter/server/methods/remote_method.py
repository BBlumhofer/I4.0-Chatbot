from __future__ import annotations

from asyncua import Node
from typing_extensions import override

from pyuaadapter.client.base_remote_callable import RemoteSkillSubscriber
from pyuaadapter.client.remote_method_v4 import RemoteMethod as ClientRemoteMethod
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.base_method import BaseMethod
from pyuaadapter.server.mixins.remote_mirror import (
    RemoteFinalResultUpdateMixin,
    RemoteMonitoringUpdateMixin,
    RemoteParameterMirrorMixin,
)


class RemoteMethod(
    BaseMethod,
    RemoteSkillSubscriber,
    RemoteParameterMirrorMixin,
    RemoteMonitoringUpdateMixin,
    RemoteFinalResultUpdateMixin
):

    _client_remote_object: ClientRemoteMethod

    def __init__(
        self,
        name: str,
        machinery_item: BaseMachineryItem,
        *,
        client_remote_method: ClientRemoteMethod,
        minimum_access_level: int = 1,
    ):
        if client_remote_method is None:
            raise ValueError("No RemoteMethod from Client given!")
        self._client_remote_object = client_remote_method

        super().__init__(
            name=name,
            machinery_item=machinery_item,
            minimum_access_level=minimum_access_level,
        )


    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location=location, existing_node=existing_node)

        await self._init_monitoring_mirror()
        await self._init_parameter_set_mirror()
        await self._init_final_result_data_mirror()

        self._client_remote_object.add_subscriber(self)

    @override
    async def execute_method(self) -> None:
        # subscription based mirroring is too slow, explicit copying is required!
        await self._copy_parameter_set_to_remote()
        await self._client_remote_object.call()
        await self._copy_final_result_data_from_remote()