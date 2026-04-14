from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, Optional

import structlog
from asyncua import Node, Server, ua
from asyncua.ua import NodeId, QualifiedName, VariantType
from asyncua.ua.uaerrors import BadNoMatch

from .base_config import BaseConfig
from .base_requirements import BaseRequirements
from .common import add_variable, create_missing_objects, get_child_without_ns
from .ua_types import UaTypes

if TYPE_CHECKING:
    from .base_module import BaseModule


class BaseAsset(BaseRequirements, ABC):
    """ Base class for every asset (module, port, component, ...) """

    logger: structlog.BoundLogger

    _ua_node: Node
    ua_attributes: Node
    ua_monitoring: Node
    ua_identification_folder: Node

    def __init__(self, server: Server, parent: Optional["BaseAsset"], ns_idx: int, _id: str,
                 name: str, config: BaseConfig, **kwargs):
        super().__init__()
        self.server = server
        self._parent = parent  # only modules should have no parent!
        self.ns_idx = ns_idx
        self._id = _id
        self._name = name
        self.config = config
        self._initialized = False
        """ Flag indicating whether this instance is fully initialized (i.e. async init() call succeeded). """

        self.ua_identification_nodes: Dict[str, Node] = {}
        self.ua_monitoring_nodes: Dict[str, Node] = {}
        self.ua_attribute_nodes: Dict[str, Node] = {}

    @abstractmethod
    async def init(self, folder_node: Node, component_type: Node | None = None) -> None:
        """
        Initialize the module asynchronously.

        :param folder_node: parent OPC-UA node, ideally a folder type
        :param component_type: OPC UA node to used to instantiate object
        """
        pass

    @property
    def initialized(self) -> bool:
        """ Return True if this instance is fully initialized. """
        return self._initialized

    async def _add_nodes_to_map(self, parent: Node, _dict: Dict[str, Node]):
        for child in await parent.get_children():
            _dict[(await child.read_browse_name()).Name] = child

    @create_missing_objects("Attributes", "functional_group_type", "ns_machine_set")
    async def _init_attributes(self) -> None:
        self.ua_attributes = await self.ua_node.get_child(f"{UaTypes.ns_machine_set}:Attributes")
        await self._add_nodes_to_map(self.ua_attributes, self.ua_attribute_nodes)

    async def _add_variable(self, name: str | QualifiedName,
                            val,
                            attr: str, init_attr: Callable[[], Awaitable[None]],
                            node_dict: Dict[str, Node],
                            *,
                            varianttype: VariantType | None = None,
                            datatype: NodeId | int | None = None,
                            historize=False,
                            unit: str | int | None = None,
                            _range: tuple[float, float] | None = None,
                            instantiate: bool = True):
        """ Creates a new OPC UA node in the defined parent folder with the given parameters. """
        if not instantiate:
            return None

        if not hasattr(self, attr):
            await init_attr()

        node = await add_variable(self.ns_idx, getattr(self, attr), name, val, varianttype, datatype, unit, _range)

        if isinstance(name, str):
            node_dict[name] = node
        else:
            node_dict[name.Name] = node

        if historize:
            await self.server.historize_node_data_change(node, count=1000)

        return node

    async def add_attribute_variable(self, name: str | QualifiedName,
                                     val, *,
                                     varianttype: VariantType | None = None,
                                     datatype: NodeId | int | None = None,
                                     historize=False,
                                     unit: str | int | None = None,
                                     _range: tuple[float, float] | None = None,
                                     instantiate: bool = True) -> Node:
        """ Creates a new OPC UA node in the attribute folder with the given parameters. """

        return await self._add_variable(name, val, "ua_attributes", self._init_attributes, self.ua_attribute_nodes,
                                  varianttype=varianttype, datatype=datatype, historize=historize,
                                  unit=unit, _range=_range, instantiate=instantiate)

    @create_missing_objects("Monitoring", "monitoring_type", "ns_machine_set")
    async def _init_monitoring(self) -> None:
        try:
            self.ua_monitoring = await self.ua_node.get_child(f"{UaTypes.ns_machine_set}:Monitoring")

        except BadNoMatch:
            # it may be possible what node id is already chosen, therefore search for alternative bname
            self.ua_monitoring = await get_child_without_ns(self.ua_node, "Monitoring")

        await self._add_nodes_to_map(self.ua_monitoring, self.ua_monitoring_nodes)

    async def add_monitoring_variable(self, name: str | QualifiedName,
                                      val,
                                      *,
                                      varianttype: VariantType | None = None,
                                      datatype: NodeId | int | None = None,
                                      historize=False,
                                      unit: str | int | None = None,
                                      _range: tuple[float, float] | None = None,
                                      instantiate: bool = True) -> Node:
        """ Creates a new OPC UA node in the monitoring folder with the given parameters. """

        return await self._add_variable(name, val, "ua_monitoring", self._init_monitoring, self.ua_monitoring_nodes,
                                        varianttype=varianttype, datatype=datatype, historize=historize,
                                        unit=unit, _range=_range, instantiate=instantiate)

    @create_missing_objects("Requirements", "functional_group_type", "ns_di")
    async def _init_requirements(self) -> None:
        self.ua_requirements_folder = await self.ua_node.get_child(f"{UaTypes.ns_di}:Requirements")
        await self._delete_children(self.ua_requirements_folder)

    async def _init_identification(self) -> None:
        self.ua_identification_folder = await self.ua_node.get_child(f"{UaTypes.ns_di}:Identification")

        try:
            ua_asset_id = await self.ua_identification_folder.get_child(f"{UaTypes.ns_di}:AssetId")
            await ua_asset_id.write_value(self._id)
        except BadNoMatch:
            # AssetId is optional
            ua_asset_id = await add_variable(ns_idx=self.ns_idx, bname=ua.QualifiedName("AssetId", UaTypes.ns_di),
                location=self.ua_identification_folder, val=self._id)

        self.ua_identification_nodes["AssetId"] = ua_asset_id

        try:
            ua_component_name = await self.ua_identification_folder.get_child(f"{UaTypes.ns_di}:ComponentName")
            await ua_component_name.write_value(ua.LocalizedText(self._name, "en-US"))
        except BadNoMatch:
            # ComponentName is optional
            ua_component_name = await add_variable(ns_idx=self.ns_idx, bname=ua.QualifiedName("ComponentName", UaTypes.ns_di),
                location=self.ua_identification_folder, val=ua.LocalizedText(self._name, "en-US"))

        self.ua_identification_nodes["ComponentName"] = ua_component_name

    async def _delete_children(self, parent: Node) -> None:
        for child in await parent.get_children():
            await child.delete()  # not recursive to improve start up

    async def _delete_empty_folders(self, parent: Optional[Node] = None) -> None:
        # TODO: verify if start up is too slow and if stupid things happen
        if parent is None:
            parent = self._ua_node

        self.logger.debug("Deleting empty folders...", node=parent.nodeid.to_string())
        for child in await parent.get_children():
            # only delete if child has no children and node class is object
            if len(await child.get_children()) == 0 and await child.read_node_class() == 1:
                self.logger.debug("deleting empty node", node=child.nodeid.to_string())
                await child.delete()


    @property
    def id(self) -> str:
        """ ID of the asset. """
        return self._id

    @property
    def name(self) -> str:
        """ Name of the asset. """
        return self._name

    @property
    def full_name(self) -> str:
        """ Return the full name including the full names of all parents, separated by '/'. """
        if self._parent is not None:
            return f"{self._parent.full_name}/{self.name}"
        else:
            return f"/{self.name}"

    @property
    def ua_node(self) -> Node:
        """ Main OPC UA node of the asset. """
        return self._ua_node

    @property
    def root_parent(self) -> "BaseModule":
        """
        parent is machinery item that might be a (nested) component or a module, method return the root parent
        """
        return self._parent.root_parent  # type: ignore
