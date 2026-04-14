from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Union, Dict
from asyncua import Node, Server, ua
from asyncua.ua import Int32, String, Guid, ByteString

from pyuaadapter.server import BaseConfig, UaTypes
from pyuaadapter.server.nodesets import ua_files
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:  # prevent circular imports during run-time
    pass


class BaseCompanionSpecificationComponent(BaseComponent, ABC):
    """
    Abstract base class representing a component from an arbitrary companion specification.

    :param ns_idx_cs: idx of namespace of companion specification of the server
    """

    ns_idx_cs: int
    ns_uris_dependency_nodesets: Dict[str, int]  # Dict if dependencies to be imported before nodeset is imported

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str, config: BaseConfig,
                 ns_uri_cs: str, spatial_object: SpatialObject = None, ns_uris_dependency_nodesets: Dict[str, int] = None):
        """
        Creates a new component based on a relevant companion specification

        :param ns_uri_cs: namespace uri of the companion specification, should like 'http://opcfoundation.org/UA' for UA
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object)
        self.ns_uri_cs = ns_uri_cs
        self.ns_uris_dependency_nodesets = ns_uris_dependency_nodesets

    async def _init_namespace(self, ns_uri: str, ns_uri_dependencies: Dict[str, int] = None) -> int:
        """
        validates of server has namespace of internal needed namespace -> otherwise raise error
        """

        if ns_uri not in UaTypes.ns_uri_idx_dict:
            if ns_uri_dependencies is not None:
                for _ns_uri in ns_uri_dependencies.keys():
                    ns_uri_dependencies[_ns_uri] = await self._init_namespace(_ns_uri)

            return await UaTypes.import_xml(self.server, ua_files.URI_FILE_DICT[ns_uri])
        else:
            return UaTypes.ns_uri_idx_dict[ns_uri]

    async def init(self, parent_node: Node, component_type: Node | Union[Int32, String, Guid, ByteString] ) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> should be from an existing companion specification

        """
        self.ns_idx_cs = await self._init_namespace(self.ns_uri_cs, self.ns_uris_dependency_nodesets)
        if isinstance(component_type, Node):
            await super().init(folder_node=parent_node, component_type=component_type)
        else:
            _object_type = self.server.get_node(ua.NodeId(component_type, self.ns_idx_cs))
            await super().init(folder_node=parent_node, component_type=_object_type)



