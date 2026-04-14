from __future__ import annotations

import asyncio
import logging
from abc import ABC

from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.components.ecm_spec.base_energy_measurement import BaseEnergyMeasurement
from pyuaadapter.server.spatial_object import SpatialObject


class EnergyMeasurementE2(BaseEnergyMeasurement, ABC):
    """ Abstract base class representing an energy measurement device for e2 profile. """

    ua_ac_active_energy_total_export_lp: Node
    ua_ac_active_energy_total_import_lp: Node
    ua_ac_active_power_total: Node

    _energy_profile_identifier: ua.Int32 = ua.Int32(1009)  # identifier of e2 energy profile interface of ecm specification

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object: SpatialObject = None):

        """
        Creates an energy measurement device for e2 profile
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         spatial_object=spatial_object)


    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()
        self.ua_ac_active_energy_total_export_lp = self.ua_monitoring_nodes["AcActiveEnergyTotalExportLp"]
        self.ua_ac_active_energy_total_import_lp = self.ua_monitoring_nodes["AcActiveEnergyTotalImportLp"]
        self.ua_ac_active_power_total = self.ua_monitoring_nodes["AcActivePowerTotal"]

        await asyncio.gather(
            self.write_ac_active_energy_total_export_lp(0.0),
            self.write_ac_active_energy_total_import_hp(0.0),
            self.write_ac_active_power_total(0.0),
        )

    async def write_ac_active_energy_total_export_lp(self, value: float) -> None:
        await self.ua_ac_active_energy_total_export_lp.write_value(ua.Variant(value, VariantType=ua.VariantType.Float))

    async def write_ac_active_energy_total_import_hp(self, value: float) -> None:
        await self.ua_ac_active_energy_total_import_lp.write_value(ua.Variant(value, VariantType=ua.VariantType.Float))

    async def write_ac_active_power_total(self, value: float) -> None:
        await self.ua_ac_active_power_total.write_value(ua.Variant(value, VariantType=ua.VariantType.Float))

    async def read_ac_active_energy_total_export_lp(self) -> float:
        return await self.ua_ac_active_energy_total_export_lp.read_value()

    async def read_ac_active_energy_total_import_lp(self) -> float:
        return await self.ua_ac_active_energy_total_import_lp.read_value()

    async def read_ac_active_power_total(self) -> float:
        return await self.ua_ac_active_power_total.read_value()


    async def write_monitoring_values(
            self, *,
            ac_active_energy_total_export_lp: float = None,
            ac_active_energy_total_import_lp: float = None,
            ac_active_power_total: float = None) -> None:

        if ac_active_energy_total_export_lp is not None:
            await self.write_ac_active_energy_total_export_lp(ac_active_energy_total_export_lp)

        if ac_active_energy_total_import_lp is not None:
            await self.write_ac_active_energy_total_import_hp(ac_active_energy_total_import_lp)

        if ac_active_power_total is not None:
            await self.write_ac_active_power_total(ac_active_power_total)