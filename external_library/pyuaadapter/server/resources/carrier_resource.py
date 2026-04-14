from __future__ import annotations

from abc import ABC

from asyncua import ua
from typing_extensions import override

from pyuaadapter.server.common import add_property
from pyuaadapter.server.resources.base_resource import BaseResource


class CarrierResource(BaseResource, ABC):
    form: str | None = None
    color: str | None = None
    resource_class = "Carrier"

    @override
    async def _fill_resource_obj(self, ns_idx: int, **kwargs) -> None:
        await super()._fill_resource_obj(ns_idx, **kwargs)

        ua_attributes = await self.ua_node.get_child(f"{ns_idx}:Attributes")
        if self.form is not None:
            await add_property(ns_idx, ua_attributes,"Form", self.form, ua.VariantType.String)
        if self.color is not None:
            await add_property(ns_idx, ua_attributes, "Color", self.color, ua.VariantType.String)

        if self.form is None and self.color is None:
            await ua_attributes.delete()


    @classmethod
    async def init(cls, ns_idx: int) -> None:
        from pyuaadapter.server import UaTypes
        # TODO via XML Node set?
        cls._ua_resource_type = await UaTypes.base_resource_type.add_object_type(
            ns_idx, bname="CarrierResourceType")
        truck_attributes = await cls._ua_resource_type.add_object(
            ns_idx, bname="Attributes", objecttype=UaTypes.functional_group_type.nodeid)
        await truck_attributes.set_modelling_rule(True)
        await (await truck_attributes.add_property(ns_idx, "Form", "")).set_modelling_rule(False)
        truck_monitoring = await cls._ua_resource_type.add_object(  # TODO this is bad code duplication, see NubstoneResource
            ns_idx, bname="Monitoring", objecttype=UaTypes.functional_group_type.nodeid)
        await truck_monitoring.set_modelling_rule(True)
        await (await truck_monitoring.add_property(ns_idx, "Amount", 0,
                                                      varianttype=ua.VariantType.Int32)).set_modelling_rule(False)


class WST_A(CarrierResource):  # noqa: N801
    asset_id = "snr-C10000"
    component_name = "WST_A"
    form = "A"
    color = "Black"


class WST_B(CarrierResource):  # noqa: N801
    asset_id = "snr-C10001"
    component_name = "WST_B"
    form = "B"
    color = "Black"


class WST_C(CarrierResource):  # noqa: N801
    asset_id = "snr-C10002"
    component_name = "WST_C"
    form = "C"
    color = "Black"


class WST_D(CarrierResource):  # noqa: N801
    asset_id = "snr-C10003"
    component_name = "WST_D"
    form = "D"
    color = "Black"


class WST_E(CarrierResource):  # noqa: N801
    asset_id = "snr-C10004"
    component_name = "WST_E"
    form = "E"
    color = "Black"


class WST_F(CarrierResource):  # noqa: N801
    asset_id = "snr-C10004"
    component_name = "WST_F"
    form = "F"
    color = "Black"


class WST_G(CarrierResource):  # noqa: N801
    asset_id = "snr-C10005"
    component_name = "WST_G"
    form = "G"
    color = "Black"