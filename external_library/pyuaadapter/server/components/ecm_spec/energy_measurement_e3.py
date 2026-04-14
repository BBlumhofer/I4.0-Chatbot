from __future__ import annotations

import asyncio
import logging
from abc import ABC

from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.components.component_data_classes import AcPe, AcPp
from pyuaadapter.server.components.ecm_spec.base_energy_measurement import BaseEnergyMeasurement
from pyuaadapter.server.spatial_object import SpatialObject


class EnergyMeasurementE3(BaseEnergyMeasurement, ABC):
    """ Abstract base class representing an energy measurement device for e3 profile. """

    ua_ac_active_energy_total_export_hp: Node
    ua_ac_active_energy_total_import_hp: Node
    ua_ac_active_power_pe: Node
    ua_ac_current_pe: Node
    ua_ac_power_factor_pe: Node
    ua_ac_reactive_energy_total_export_hp: Node
    ua_ac_reactive_energy_total_import_hp: Node
    ua_ac_reactive_power_pe: Node
    ua_ac_voltage_pe: Node
    ua_ac_voltage_pp: Node
    _energy_profile_identifier: ua.Int32 = ua.Int32(1010)  # identifier of e3 energy profile interface of ecm specification

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object: SpatialObject = None):

        """
        Creates an energy measurement device for e3 profile
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         spatial_object=spatial_object)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()
        self.ua_ac_active_energy_total_export_hp = self.ua_monitoring_nodes["AcActiveEnergyTotalExportHp"]
        self.ua_ac_active_energy_total_import_hp = self.ua_monitoring_nodes["AcActiveEnergyTotalImportHp"]
        self.ua_ac_active_power_pe = self.ua_monitoring_nodes["AcActivePower"]
        self.ua_ac_current_pe = self.ua_monitoring_nodes["AcCurrent"]
        self.ua_ac_power_factor_pe = self.ua_monitoring_nodes["AcPowerFactor"]
        self.ua_ac_reactive_energy_total_export_hp = self.ua_monitoring_nodes["AcReactiveEnergyTotalExportHp"]
        self.ua_ac_reactive_energy_total_import_hp = self.ua_monitoring_nodes["AcReactiveEnergyTotalImportHp"]
        self.ua_ac_reactive_power_pe = self.ua_monitoring_nodes["AcReactivePower"]
        self.ua_ac_voltage_pe = self.ua_monitoring_nodes["AcVoltagePe"]
        self.ua_ac_voltage_pp = self.ua_monitoring_nodes["AcVoltagePp"]

        await asyncio.gather(
            self.write_ac_active_energy_total_export_hp(0.0),
            self.write_ac_active_energy_total_import_hp(0.0),
            self.write_ac_active_power_pe(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_current_pe(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_power_factor_pe(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_reactive_energy_total_export_hp(0.0),
            self.write_ac_reactive_energy_total_import_hp(0.0),
            self.write_ac_reactive_power_pe(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_voltage_pe(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_voltage_pp(AcPp(L1L2=0, L2L3=0, L3L1=0)),
        )

    async def write_ac_active_energy_total_export_hp(self, value: float) -> None:
        await self.ua_ac_active_energy_total_export_hp.write_value(value)

    async def write_ac_active_energy_total_import_hp(self, value: float) -> None:
        await self.ua_ac_active_energy_total_import_hp.write_value(value)

    async def write_ac_active_power_pe(self, value: AcPe) -> None:
        await self.ua_ac_active_power_pe.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_current_pe(self, value: AcPe) -> None:
        await self.ua_ac_current_pe.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_power_factor_pe(self, value: AcPe) -> None:
        await self.ua_ac_power_factor_pe.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_reactive_energy_total_export_hp(self, value: float) -> None:
        await self.ua_ac_reactive_energy_total_export_hp.write_value(value)

    async def write_ac_reactive_energy_total_import_hp(self, value: float) -> None:
        await self.ua_ac_reactive_energy_total_import_hp.write_value(value)

    async def write_ac_reactive_power_pe(self, value: AcPe) -> None:
        await self.ua_ac_reactive_power_pe.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_voltage_pe(self, value: AcPe) -> None:
        await self.ua_ac_voltage_pe.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_voltage_pp(self, value: AcPp) -> None:
        await self.ua_ac_voltage_pp.write_value(ua.AcPpDataType(value.L1L2, value.L2L3, value.L3L1))

    async def write_monitoring_values(
            self, *,
            ac_active_energy_total_export_hp: float=None,
            ac_active_energy_total_import_hp: float=None,
            ac_active_power: AcPe=None,
            ac_current: AcPe=None,
            ac_power_factor: AcPe=None,
            ac_reactive_energy_total_export_hp: float=None,
            ac_reactive_energy_total_import_hp: float=None,
            ac_reactive_power: AcPe=None,
            ac_voltage_pe: AcPe=None,
            ac_voltage_pp: AcPp=None) -> None:

        if ac_active_energy_total_export_hp is not None:
            await self.write_ac_active_energy_total_export_hp(ac_active_energy_total_export_hp)

        if ac_active_energy_total_import_hp is not None:
            await self.write_ac_active_energy_total_import_hp(ac_active_energy_total_import_hp)

        if ac_active_power is not None:
            await self.write_ac_active_power_pe(ac_active_power)

        if ac_current is not None:
            await self.write_ac_current_pe(ac_current)

        if ac_power_factor is not None:
            await self.write_ac_power_factor_pe(ac_power_factor)

        if ac_reactive_energy_total_export_hp is not None:
            await self.write_ac_reactive_energy_total_export_hp(ac_reactive_energy_total_export_hp)

        if ac_reactive_energy_total_import_hp is not None:
            await self.write_ac_reactive_energy_total_import_hp(ac_reactive_energy_total_import_hp)

        if ac_reactive_power is not None:
            await self.write_ac_reactive_power_pe(ac_reactive_power)

        if ac_voltage_pe is not None:
            await self.write_ac_voltage_pe(ac_voltage_pe)

        if ac_voltage_pp is not None:
            await self.write_ac_voltage_pp(ac_voltage_pp)

    async def read_ac_active_energy_total_export_hp(self) -> float:
        return await self.ua_ac_active_energy_total_export_hp.read_value()

    async def read_ac_active_energy_total_import_hp(self) -> float:
        return await self.ua_ac_active_energy_total_import_hp.read_value()

    async def read_ac_active_power_pe(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_active_power_pe.read_value())

    async def read_ac_current_pe(self)-> AcPe:
        return self._read_acpe(await self.ua_ac_current_pe.read_value())

    async def read_ac_power_factor_pe(self)-> AcPe:
        return self._read_acpe(await self.ua_ac_power_factor_pe.read_value())

    async def read_ac_reactive_energy_total_export_hp(self) -> float:
        return await self.ua_ac_reactive_energy_total_export_hp.read_value()

    async def read_ac_reactive_energy_total_import_hp(self) -> float:
        return await self.ua_ac_reactive_energy_total_import_hp.read_value()

    async def read_ac_reactive_power_pe(self)-> AcPe:
        return self._read_acpe(await self.ua_ac_reactive_power_pe.read_value())

    async def read_ac_voltage_pe(self)-> AcPe:
        return self._read_acpe(await self.ua_ac_voltage_pe.read_value())

    async def read_ac_voltage_pp(self)-> AcPp:
        return self._read_acpp(await self.ua_ac_voltage_pp.read_value())
