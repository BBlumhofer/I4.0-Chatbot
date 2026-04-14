
from __future__ import annotations

import asyncio
import logging
from abc import ABC

from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.components.component_data_classes import AcPe, AcPp
from pyuaadapter.server.components.ecm_spec.energy_measurement_e0 import EnergyMeasurementE0
from pyuaadapter.server.components.ecm_spec.energy_measurement_sfkl import EnergyMeasurement_SFKL
from pyuaadapter.server.spatial_object import SpatialObject


class EnergyMeasurementE0_SFKL(EnergyMeasurementE0, EnergyMeasurement_SFKL, ABC):
    """ Abstract base class representing an energy measurement device for E0_SFKL profile. """

    # Define all the UA node variables based on the provided template
    ua_ac_active_energy_total_import_hp: Node
    ua_ac_active_power: Node
    ua_ac_active_power_total: Node
    ua_ac_apparent_energy_total_hp: Node
    ua_ac_apparent_power: Node
    ua_ac_apparent_power_total: Node
    ua_ac_current_n: Node
    ua_ac_frequency: Node
    ua_ac_power_factor: Node
    ua_ac_power_factor_total: Node
    ua_ac_reactive_energy_total_import_hp: Node
    ua_ac_reactive_power: Node
    ua_ac_reactive_power_total: Node
    ua_ac_voltage_pe: Node
    ua_ac_voltage_pp: Node
    ua_phase: Node
    ua_temperature: Node

    _energy_profile_identifier: ua.Int32 = ua.Int32(1004)  # identifier for eo sfkl energy profile interface

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 config: BaseConfig, spatial_object: SpatialObject = None):
        """
        Creates an energy measurement device for eo sfkl profile
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id),
                         name=name, config=config,
                         spatial_object=spatial_object)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        self.ua_ac_active_energy_total_import_hp = self.ua_monitoring_nodes["AcActiveEnergyTotalImportHp"]
        self.ua_ac_active_power = self.ua_monitoring_nodes["AcActivePower"]
        self.ua_ac_active_power_total = self.ua_monitoring_nodes["AcActivePowerTotal"]
        self.ua_ac_apparent_energy_total_hp = self.ua_monitoring_nodes["AcApparentEnergyTotalHp"]
        self.ua_ac_apparent_power = self.ua_monitoring_nodes["AcApparentPower"]
        self.ua_ac_apparent_power_total = self.ua_monitoring_nodes["AcApparentPowerTotal"]
        self.ua_ac_current_n = self.ua_monitoring_nodes["AcCurrentN"]
        self.ua_ac_frequency = self.ua_monitoring_nodes["AcFrequency"]
        self.ua_ac_power_factor = self.ua_monitoring_nodes["AcPowerFactor"]
        self.ua_ac_power_factor_total = self.ua_monitoring_nodes["AcPowerFactorTotal"]
        self.ua_ac_reactive_energy_total_import_hp = self.ua_monitoring_nodes["AcReactiveEnergyTotalImportHp"]
        self.ua_ac_reactive_power = self.ua_monitoring_nodes["AcReactivePower"]
        self.ua_ac_reactive_power_total = self.ua_monitoring_nodes["AcReactivePowerTotal"]
        self.ua_ac_voltage_pe = self.ua_monitoring_nodes["AcVoltagePe"]
        self.ua_ac_voltage_pp = self.ua_monitoring_nodes["AcVoltagePp"]
        # self.ua_phase = self.ua_monitoring_nodes["Phase"]
        # self.ua_temperature = self.ua_monitoring_nodes["Temperature"]

        # Initialize default values
        await asyncio.gather(
            self.write_ac_active_energy_total_import_hp(0.0),
            self.write_ac_active_power(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_active_power_total(0.0),
            self.write_ac_apparent_energy_total_hp(0.0),
            self.write_ac_apparent_power(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_apparent_power_total(0.0),
            self.write_ac_current_n(0.0),
            self.write_ac_frequency(0.0),
            self.write_ac_power_factor(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_power_factor_total(0.0),
            self.write_ac_reactive_energy_total_import_hp(0.0),
            self.write_ac_reactive_power(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_reactive_power_total(0.0),
            self.write_ac_voltage_pe(AcPe(L1=0, L2=0, L3=0)),
            self.write_ac_voltage_pp(AcPp(L1L2=0, L2L3=0, L3L1=0)),
            # self.write_ac_phase(AcPe(L1=0, L2=0, L3=0)),
            # self.write_ac_temperature(0.0),
        )

    async def write_ac_active_energy_total_import_hp(self, value: float) -> None:
        await self.ua_ac_active_energy_total_import_hp.write_value(value, varianttype=ua.VariantType.Double)

    async def write_ac_active_power(self, value: AcPe) -> None:
        await self.ua_ac_active_power.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_active_power_total(self, value: float) -> None:
        await self.ua_ac_active_power_total.write_value(value, varianttype=ua.VariantType.Float)

    async def write_ac_apparent_energy_total_hp(self, value: float) -> None:
        await self.ua_ac_apparent_energy_total_hp.write_value(value, varianttype=ua.VariantType.Double)

    async def write_ac_apparent_power(self, value: AcPe) -> None:
        await self.ua_ac_apparent_power.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_apparent_power_total(self, value: float) -> None:
        await self.ua_ac_apparent_power_total.write_value(value, varianttype=ua.VariantType.Float)

    async def write_ac_current_n(self, value: float) -> None:
        await self.ua_ac_current_n.write_value(value, varianttype=ua.VariantType.Float)

    async def write_ac_frequency(self, value: float) -> None:
        await self.ua_ac_frequency.write_value(value, varianttype=ua.VariantType.Float)

    async def write_ac_power_factor(self, value: AcPe) -> None:
        await self.ua_ac_power_factor.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_power_factor_total(self, value: float) -> None:
        await self.ua_ac_power_factor_total.write_value(value, varianttype=ua.VariantType.Float)

    async def write_ac_reactive_energy_total_import_hp(self, value: float) -> None:
        await self.ua_ac_reactive_energy_total_import_hp.write_value(value, varianttype=ua.VariantType.Double)

    async def write_ac_reactive_power(self, value: AcPe) -> None:
        await self.ua_ac_reactive_power.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_reactive_power_total(self, value: float) -> None:
        await self.ua_ac_reactive_power_total.write_value(value, varianttype=ua.VariantType.Float)

    async def write_ac_voltage_pe(self, value: AcPe) -> None:
        await self.ua_ac_voltage_pe.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))

    async def write_ac_voltage_pp(self, value: AcPp) -> None:
        await self.ua_ac_voltage_pp.write_value(ua.AcPpDataType(value.L1L2, value.L2L3, value.L3L1))

    # async def write_ac_phase(self, value: AcPe) -> None:
    #     await self.ua_phase.write_value(ua.AcPeDataType(value.L1, value.L2, value.L3))
    #
    # async def write_ac_temperature(self, value: float) -> None:
    #     await self.ua_temperature.write_value(value, varianttype=ua.VariantType.Float)

    async def read_ac_active_energy_total_import_hp(self) -> float:
        return await self.ua_ac_active_energy_total_import_hp.read_value()

    async def read_ac_active_power(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_active_power.read_value())

    async def read_ac_active_power_total(self) -> float:
        return await self.ua_ac_active_power_total.read_value()

    async def read_ac_apparent_energy_total_hp(self) -> float:
        return await self.ua_ac_apparent_energy_total_hp.read_value()

    async def read_ac_apparent_power(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_apparent_power.read_value())

    async def read_ac_apparent_power_total(self) -> float:
        return await self.ua_ac_apparent_power_total.read_value()

    async def read_ac_current_n(self) -> float:
        return await self.ua_ac_current_n.read_value()

    async def read_ac_frequency(self) -> float:
        return await self.ua_ac_frequency.read_value()

    async def read_ac_power_factor(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_power_factor.read_value())

    async def read_ac_power_factor_total(self) -> float:
        return await self.ua_ac_power_factor_total.read_value()

    async def read_ac_reactive_energy_total_import_hp(self) -> float:
        return await self.ua_ac_reactive_energy_total_import_hp.read_value()

    async def read_ac_reactive_power(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_reactive_power.read_value())

    async def read_ac_reactive_power_total(self) -> float:
        return await self.ua_ac_reactive_power_total.read_value()

    async def read_ac_voltage_pe(self) -> AcPe:
        return self._read_acpe(await self.ua_ac_voltage_pe.read_value())

    async def read_ac_voltage_pp(self) -> AcPp:
        return self._read_acpp(await self.ua_ac_voltage_pp.read_value())

    # async def read_ac_phase(self) -> AcPe:
    #     return self._read_acpe(await self.ua_phase.read_value())
    #
    # async def read_ac_temperature(self) -> float:
    #     return await self.ua_temperature.read_value()

    async def write_monitoring_values(
            self, *,
            ac_current: AcPe = None,
            ac_active_energy_total_import_hp: float = None,
            ac_active_power: AcPe = None,
            ac_active_power_total: float = None,
            ac_apparent_energy_total_hp: float = None,
            ac_apparent_power: AcPe = None,
            ac_apparent_power_total: float = None,
            ac_current_n: float = None,
            ac_frequency: float = None,
            ac_power_factor: AcPe = None,
            ac_power_factor_total: float = None,
            ac_reactive_energy_total_import_hp: float = None,
            ac_reactive_power: AcPe = None,
            ac_reactive_power_total: float = None,
            ac_voltage_pe: AcPe = None,
            ac_voltage_pp: AcPp = None,
            # ac_phase: AcPe = None,
            # ac_temperature: float = None
    ):

        if ac_current is not None:
            await self.write_ac_current(ac_current)

        if ac_active_energy_total_import_hp is not None:
            await self.write_ac_active_energy_total_import_hp(ac_active_energy_total_import_hp)

        if ac_active_power is not None:
            await self.write_ac_active_power(ac_active_power)

        if ac_active_power_total is not None:
            await self.write_ac_active_power_total(ac_active_power_total)

        if ac_apparent_energy_total_hp is not None:
            await self.write_ac_apparent_energy_total_hp(ac_apparent_energy_total_hp)

        if ac_apparent_power is not None:
            await self.write_ac_apparent_power(ac_apparent_power)

        if ac_apparent_power_total is not None:
            await self.write_ac_apparent_power_total(ac_apparent_power_total)

        if ac_current_n is not None:
            await self.write_ac_current_n(ac_current_n)

        if ac_frequency is not None:
            await self.write_ac_frequency(ac_frequency)

        if ac_power_factor is not None:
            await self.write_ac_power_factor(ac_power_factor)

        if ac_power_factor_total is not None:
            await self.write_ac_power_factor_total(ac_power_factor_total)

        if ac_reactive_energy_total_import_hp is not None:
            await self.write_ac_reactive_energy_total_import_hp(ac_reactive_energy_total_import_hp)

        if ac_reactive_power is not None:
            await self.write_ac_reactive_power(ac_reactive_power)

        if ac_reactive_power_total is not None:
            await self.write_ac_reactive_power_total(ac_reactive_power_total)

        if ac_voltage_pe is not None:
            await self.write_ac_voltage_pe(ac_voltage_pe)

        if ac_voltage_pp is not None:
            await self.write_ac_voltage_pp(ac_voltage_pp)

        # if ac_phase is not None:
        #     await self.write_ac_phase(ac_phase)
        #
        # if ac_temperature is not None:
        #     await self.write_ac_temperature(ac_temperature)

