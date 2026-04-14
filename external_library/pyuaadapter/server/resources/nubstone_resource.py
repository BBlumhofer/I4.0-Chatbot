from __future__ import annotations

from abc import ABC

from asyncua import ua
from typing_extensions import override

from pyuaadapter.server.resources.base_resource import BaseResource


class NubstoneResource(BaseResource):
    resource_class = "NubStone"
    color: str
    size: str

    @override
    async def _fill_resource_obj(self, ns_idx: int, **kwargs) -> None:
        await super()._fill_resource_obj(ns_idx, **kwargs)

        await (await self.ua_node.get_child([f"{ns_idx}:Attributes", f"{ns_idx}:Color"])).set_value(self.color)
        await (await self.ua_node.get_child([f"{ns_idx}:Attributes", f"{ns_idx}:Size"])).set_value(self.size)

    @classmethod
    async def init(cls, ns_idx: int) -> None:
        from pyuaadapter.server import UaTypes
        # TODO via XML Node set?
        cls._ua_resource_type = await UaTypes.base_resource_type.add_object_type(
            ns_idx, bname="NubstoneResourceType")
        nubstone_attributes = await cls._ua_resource_type.add_object(
            ns_idx, bname="Attributes", objecttype=UaTypes.functional_group_type.nodeid)
        await nubstone_attributes.set_modelling_rule(True)
        await (await nubstone_attributes.add_property(ns_idx, "Color", "")).set_modelling_rule(True)
        await (await nubstone_attributes.add_property(ns_idx, "Size", "")).set_modelling_rule(True)
        nubstone_monitoring = await cls._ua_resource_type.add_object(
            ns_idx, bname="Monitoring", objecttype=UaTypes.functional_group_type.nodeid)
        await nubstone_monitoring.set_modelling_rule(True)
        await (await nubstone_monitoring.add_property(ns_idx, "Amount", 0,
                                                      varianttype=ua.VariantType.Int32)).set_modelling_rule(False)


class UsbPenDriveResource(NubstoneResource, ABC):
    resource_class = "UsbPenDrive"


class UsbPenDrive_2x4_Blue(UsbPenDriveResource):  # noqa: N801
    asset_id = "snr-NS10000-24-000ff"
    component_name = "UsbPenDrive_2x4_Blue"
    size = "2x4"
    color = "Blue"


class UsbPenDrive_2x4_Red(UsbPenDriveResource):  # noqa: N801
    asset_id = "snr-NS10000-24-ff000"
    component_name = "UsbPenDrive_2x4_Red"
    size = "2x4"
    color = "Red"

    
class NubStone_2x2_Orange(NubstoneResource):  # noqa: N801
    asset_id = "snr-NS10100-22-ffa500"
    component_name = "NubStone_2x2_Orange"
    size = "2x2"
    color = "Orange"


class NubStone_2x2_Blue(NubstoneResource):  # noqa: N801
    asset_id = "snr-NS10100-22-000ff"
    component_name = "NubStone_2x2_Blue"
    size = "2x2"
    color = "Blue"


class FlatStoneResource(NubstoneResource, ABC):
    resource_class = "FlatStone"


class FlatStone_2x4_Black(FlatStoneResource):  # noqa: N801
    asset_id = "snr-NS10200-24-000000"
    component_name = "FlatStone_2x4_Black"
    size = "2x4"
    color = "Black"


class FlatStone_2x4_Brown(FlatStoneResource):  # noqa: N801
    asset_id = "snr-NS10200-24-8B4513"
    component_name = "FlatStone_2x4_Brown"
    size = "2x4"
    color = "Brown"
