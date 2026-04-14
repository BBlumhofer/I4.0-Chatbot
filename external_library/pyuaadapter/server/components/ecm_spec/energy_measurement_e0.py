from __future__ import annotations

import logging
from abc import ABC

from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.components.component_data_classes import AcPe
from pyuaadapter.server.components.ecm_spec.base_energy_measurement import BaseEnergyMeasurement
from pyuaadapter.server.spatial_object import SpatialObject


class EnergyMeasurementE0(BaseEnergyMeasurement, ABC):
    """ Abstract base class representing an energy measurement device for e0 profile. """

    ua_ac_current: Node

    _energy_profile_identifier: ua.Int32 = ua.Int32(1007)   # identifier of e0 energy profile interface of ecm specification

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig,  spatial_object: SpatialObject = None):
        """
        Creates an energy measurement device for e0 profile
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         spatial_object=spatial_object)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()
        self.ua_ac_current = self.ua_monitoring_nodes["AcCurrent"]

        await self.write_ac_current(AcPe(L1=0, L2=0, L3=0))  # Writing default value

    async def write_ac_current(self, value: AcPe) -> None:
        await self.ua_ac_current.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def read_ac_current(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_current.read_value())

