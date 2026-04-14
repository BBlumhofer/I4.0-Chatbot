from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Type

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.common import add_object
from pyuaadapter.server.spatial_object import SpatialObject


class BaseComponent(BaseMachineryItem, ABC):
    """ Base class for all components. """
    _spatial_object: SpatialObject | None
    _skills: Dict[str, Type[BaseSkill]] | None

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object: SpatialObject | None = None, skills: List[Type[BaseSkill]] | None = None,
                 **kwargs):
        super().__init__(server=server, parent=parent, ns_idx=ns_idx, _id=_id, name=name, config=config)
        self._spatial_object = spatial_object
        self._skills = skills
        self.logger = structlog.getLogger("sf.server.Component", name=self.full_name)

    async def init(self, folder_node: Node, component_type: Node | None = None) -> None:
        """
        Asynchronous initialization.

        :param folder_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
        """

        from pyuaadapter.server import UaTypes
        if component_type is None:
            component_type = UaTypes.component_type  # generic component type
        self._ua_node = await add_object(ns_idx=self.ns_idx, location=folder_node,
                                         bname=ua.QualifiedName(self._name, UaTypes.ns_machine_set),
                                         object_tyoe=component_type,
                                         instantiate_optional=False)

        await self._init_notification()  # may need logs during initialization

        await asyncio.gather(self._init_component_identification(),
                             self._init_monitoring(),
                             self._init_attributes(),
                             self._init_parameter_set(),
                             self._init_requirements(),
                             )

        await self._init_components()  # assets may need spatial object during init monitoring
        await self._init_methods()
        await self._init_skills()
        await self._init_status()  # TODO should they have? what about start up and running condition?

        self._initialized = True

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        if self._spatial_object is None:
            return

        from pyuaadapter.server import UaTypes

        await add_object(ns_idx=self.ns_idx, location=self.ua_monitoring,
                         bname=ua.QualifiedName("SpatialObject", UaTypes.ns_rsl),
                         object_tyoe=UaTypes.spatial_object)  # optional

        await self._spatial_object.init(self, self.root_parent.spatial_object_list)

    @abstractmethod
    async def _init_component_identification(self) -> None:
        """
        Forces user to call child method _init_identification()
        """
        pass

    @property
    def spatial_object(self) -> SpatialObject | None:
        return self._spatial_object
