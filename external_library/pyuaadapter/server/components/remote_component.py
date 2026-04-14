from __future__ import annotations

from asyncua import Node
from asyncua import Server as UaServer
from asyncua.common.subscription import Subscription
from typing_extensions import override

from pyuaadapter.client.base_remote_component import BaseRemoteComponent, RemoteComponentSubscriber
from pyuaadapter.client.remote_component_v4 import RemoteComponent as ClientRemoteComponent
from pyuaadapter.common.enums import MachineryItemStates
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.methods.remote_method import RemoteMethod
from pyuaadapter.server.mixins.remote_mirror import (
    RemoteAttributeUpdateMixin,
    RemoteMonitoringUpdateMixin,
    RemoteParameterMirrorMixin,
)
from pyuaadapter.server.skills.remote_skill import RemoteSkill
from pyuaadapter.server.spatial_object import SpatialObject

# TODO add support requirements, resources, etc.


class RemoteComponent(
    BaseComponent,
    RemoteComponentSubscriber,
    RemoteAttributeUpdateMixin,
    RemoteParameterMirrorMixin,
    RemoteMonitoringUpdateMixin,
):
    _subscription: Subscription

    def __init__(
        self,
        server: UaServer,
        parent: BaseMachineryItem,
        ns_idx: int,
        _id: str,
        name: str,
        config: BaseConfig,
        *,
        spatial_object: SpatialObject | None = None,
        client_remote_component: ClientRemoteComponent,
        recursive: bool = False,
        minimum_access_level: int = 1
    ) -> None:
        """
        Create new instance.

        :param client_remote_component: Reference of the client remote component that should be mirrored.
        :param recursive: If True, recursively add all subcomponents as well.
        :param minimum_access_level: (Local) Minimum access level for all remote methods and skills.
        """
        super().__init__(server, parent, ns_idx, _id, name, config, spatial_object=spatial_object)
        self._client_remote_object = client_remote_component  # named like this because of mixin use
        self._recursive = recursive
        self._minimum_access_level = minimum_access_level

    @override
    async def init(self, folder_node: Node, component_type: Node | None = None) -> None:
        await super().init(folder_node=folder_node, component_type=component_type)

        await self._init_remote_components()
        await self._init_remote_skills()
        await self._init_remote_methods()

        await self._init_attributes_mirror()
        await self._init_monitoring_mirror()
        await self._init_parameter_set_mirror()

        self._client_remote_object.add_subscriber(self)

    @override
    async def _init_component_identification(self) -> None:
        pass  # TODO

    @override
    async def _init_status(self, _handle_status_change: bool = False) -> None:
        await super()._init_status(handle_status_change=False)  # we only mirror the remote component


    async def _init_remote_components(self) -> None:
        if len(self._client_remote_object.components) <= 0 or not self._recursive:
            return

        for component in self._client_remote_object.components.values():
            await self.add_component(
                _id=component.asset_id,
                name=component.name,
                component_type=RemoteComponent,
                client_remote_component=component,
                recursive=True,
                minimum_access_level=self._minimum_access_level
            )

    async def _init_remote_skills(self) -> None:
        if len(self._client_remote_object.skill_set) <= 0:
            return

        await super()._init_skills()

        for skill in self._client_remote_object.skill_set.values():
            await self.add_skill(
                RemoteSkill,
                name=skill.name,
                client_remote_skill=skill,
                minimum_access_level=self._minimum_access_level
            )

    async def _init_remote_methods(self) -> None:
        if (not isinstance(self._client_remote_object, ClientRemoteComponent)
                or len(self._client_remote_object.method_set) <= 0):
            return

        await super()._init_methods()

        for method in self._client_remote_object.method_set.values():
            await self.add_method(
                RemoteMethod,
                name=method.name,
                client_remote_method=method,
                minimum_access_level=self._minimum_access_level
            )

    ###########################################################
    # Subscription callbacks

    @override
    async def on_state_change(self, new_state: str) -> None:
        try:
            await self.set_current_state(MachineryItemStates[new_state])
        except KeyError:
            self.logger.warning("Received unknown machinery item state!", state=new_state)

    @override
    async def on_new_message(self, component: "BaseRemoteComponent", text: str, severity: int, code: str) -> None:
        if severity < 555:
            await self._log_info(text=text, severity=severity)
        elif severity < 999:
            await self._log_warning(text=text, severity=severity)
        else:
            await self._log_error(text=text, severity=severity, code=code)