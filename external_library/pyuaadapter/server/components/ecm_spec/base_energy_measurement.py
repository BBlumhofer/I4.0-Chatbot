from __future__ import annotations

import asyncio
from abc import ABC
from typing import Coroutine, Dict, List

import structlog
from asyncua import Node, Server, ua
from asyncua.ua import NodeId

from pyuaadapter.common import namespace_uri
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_companion_specification_component import BaseCompanionSpecificationComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import add_interface, create_missing_objects
from pyuaadapter.server.components.component_data_classes import AcPe, AcPp
from pyuaadapter.server.spatial_object import SpatialObject


class BaseEnergyMeasurement(BaseCompanionSpecificationComponent, ABC):
    """ Abstract base class representing an energy measurement device. """

    _int_energy_profile_identifier: int

    _int_identifier: ua.Int32 = ua.Int32(1006)  # identifier of EnergyMeasurementType of ecm companion specification
    _energy_profile_identifier: ua.Int32

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,
                 spatial_object: SpatialObject = None):
        """
        Creates a new energy measurement device
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config, spatial_object=spatial_object,
                         ns_uri_cs=namespace_uri.NS_ECM_URI,
                         ns_uris_dependency_nodesets={namespace_uri.NS_IA_URI: 0})
        self._energy_profile_identifier = self.__class__._energy_profile_identifier
        self.logger = structlog.getLogger("sf.server.ecm_spec.EnergyMeasurement", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always component type from robotic spec.
                               but to support reflection of child
        """
        await super().init(parent_node, self._int_identifier)

    @create_missing_objects("Identification", "component_identification_type", "ns_di")
    async def _init_component_identification(self, manufacturer: str = None, serial_number: str = None,
                                             product_instance_uri: str = None) -> None:

        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _add_interface(self) -> Dict[str, Node]:
        return await add_interface(ns_idx=self.ns_idx,
                                   interface_type=NodeId(self._energy_profile_identifier, self.ns_idx_cs),
                                   location=self.ua_node, server=self.server)

    def _read_acpe(self, value: ua.AcPeDataType) -> AcPe:
        return AcPe(L1=value.L1, L2=value.L2, L3=value.L3)

    def _read_acpp(self, value: ua.AcPpDataType) -> AcPp:
        return AcPp(L1L2=value.L1L2, L3L1=value.L3L1, L2L3=value.L2L3)

    async def _init_monitoring(self) -> None:

        await super()._init_monitoring()

        interface_nodes = await self._add_interface()

        for name, node in interface_nodes.items():
            await self.ua_monitoring.add_reference(node, ua.ObjectIds.HasComponent)
            self.ua_monitoring_nodes[name] = node

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change(list(self.ua_monitoring_nodes.values()), count=count)

    async def _delete_empty_folders(self, parent: Node | None = None) -> None:
        """
        delete additional clutter nodes at the end of instantiation
            -> delete every variable in first level expect of motion profile
        """

        await super()._delete_empty_folders(parent)

        if parent is None or parent == self.ua_node:
            nodes_to_delete: List[Coroutine] = []

            for child in await self.ua_node.get_children():
                if (await child.read_browse_name()).Name == "<MeasurementValue>":
                    nodes_to_delete.append(child.delete())

            await asyncio.gather(*nodes_to_delete)