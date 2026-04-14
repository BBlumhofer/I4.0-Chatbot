from __future__ import annotations

import logging
from abc import ABC

from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.components.ecm_spec.base_energy_measurement import BaseEnergyMeasurement
from pyuaadapter.server.spatial_object import SpatialObject


class EnergyMeasurementE1(BaseEnergyMeasurement, ABC):
    """ Abstract base class representing an energy measurement device for e1 profile. """

    ua_ac_active_power_total: Node

    _energy_profile_identifier: ua.Int32 = ua.Int32(1008)  # identifier of e1 energy profile interface of ecm specification

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object: SpatialObject = None ):

        """
        Creates an energy measurement device for e1 profile
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         spatial_object=spatial_object)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()
        self.ua_ac_active_power_total = self.ua_monitoring_nodes["AcActivePowerTotal"]

        await self.write_ac_active_power_total(0.0)

    async def write_ac_active_power_total(self, value: float) -> None:
        await self.ua_ac_active_power_total.write_value(ua.Variant(value, VariantType=ua.VariantType.Float))

    async def read_ac_active_power_total(self) -> float:
        return await self.ua_ac_active_power_total.read_value()
