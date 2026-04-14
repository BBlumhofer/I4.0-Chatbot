
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Dict

from asyncua import Node
from asyncua.ua import NodeId
from typing_extensions import override

from pyuaadapter.common import namespace_uri
from pyuaadapter.server.common import add_interface
from pyuaadapter.server.components.ecm_spec.base_energy_measurement import BaseEnergyMeasurement

if TYPE_CHECKING:
    pass


class EnergyMeasurement_SFKL(BaseEnergyMeasurement, ABC):
    """ Abstract base class representing an energy measurement device for E0_SFKL profile. """

    @override
    async def _add_interface(self) -> Dict[str, Node]:
        ns_idx_cs = await self._init_namespace(namespace_uri.NS_ECM_SFKL_URI,
                                               {namespace_uri.NS_IA_URI: 0, namespace_uri.NS_ECM_URI: 0})

        return await add_interface(ns_idx=self.ns_idx,
                                   interface_type=NodeId(self._energy_profile_identifier, ns_idx_cs),
                                   location=self.ua_node, server=self.server)


