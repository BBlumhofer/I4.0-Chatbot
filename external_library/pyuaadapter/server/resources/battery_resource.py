from __future__ import annotations

from pyuaadapter.server.resources.base_resource import BaseResource


class BatteryResource(BaseResource):
    asset_id = "snr-BP10000-24-fffff"
    component_name = "Battery_Pack"
    resource_class = "Battery_Pack"

    @classmethod
    async def init(cls, ns_idx: int) -> None:
        from pyuaadapter.server import UaTypes
        # TODO via XML Node set?
        cls._ua_resource_type = await UaTypes.base_resource_type.add_object_type(
            ns_idx, bname="BatteryResourceType")
