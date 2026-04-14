from __future__ import annotations

from abc import ABC

from asyncua import ua
from typing_extensions import override

from pyuaadapter.server.common import add_property
from pyuaadapter.server.resources.base_resource import BaseResource


class TruckResource(BaseResource):
    color: str | None = None
    form: str | None = None

    @override
    async def _fill_resource_obj(self, ns_idx: int, **kwargs) -> None:
        await super()._fill_resource_obj(ns_idx, **kwargs)

        ua_attributes = await self.ua_node.get_child(f"{ns_idx}:Attributes")
        if self.form is not None:
            await add_property(ns_idx, ua_attributes, "Form", self.form, ua.VariantType.String)
        if self.color is not None:
            await add_property(ns_idx, ua_attributes, "Color", self.color, ua.VariantType.String)

        if self.form is None and self.color is None:
            await ua_attributes.delete()

    @classmethod
    async def init(cls, ns_idx: int) -> None:
        from pyuaadapter.server import UaTypes
        # TODO via XML Node set?
        cls._ua_resource_type = await UaTypes.base_resource_type.add_object_type(
            ns_idx, bname="TruckResourceType")
        truck_attributes = await cls._ua_resource_type.add_object(
            ns_idx, bname="Attributes", objecttype=UaTypes.functional_group_type.nodeid)
        await truck_attributes.set_modelling_rule(True)
        await (await truck_attributes.add_property(ns_idx, "Color", "")).set_modelling_rule(False)
        await (await truck_attributes.add_property(ns_idx, "Form", "")).set_modelling_rule(False)
        truck_monitoring = await cls._ua_resource_type.add_object(  # TODO this is bad code duplication, see NubstoneResource
            ns_idx, bname="Monitoring", objecttype=UaTypes.functional_group_type.nodeid)
        await truck_monitoring.set_modelling_rule(True)
        await (await truck_monitoring.add_property(ns_idx, "Amount", 0,
                                                      varianttype=ua.VariantType.Int32)).set_modelling_rule(False)




class CabResource(TruckResource, ABC):
    resource_class = "Cab"


class Cab_A_Blue(CabResource):  # noqa: N801
    asset_id = "snr-T10000-000ff"
    component_name = "Cab_A_Blue"
    form = "A"
    color = "Blue"


class Cab_B_Red(CabResource):  # noqa: N801
    asset_id = "snr-T10001-ff000"
    component_name = "Cab_B_Red"
    form = "A"
    color= "Red"


class ChassisResource(TruckResource, ABC):
    resource_class = "Chassis"


class Cab_Chassis(ChassisResource):  # noqa: N801
    asset_id = "snr-T10100-808080"
    component_name = "Cab_Chassis"


class Semitrailer_Chassis(ChassisResource):  # noqa: N801
    asset_id = "snr-T10101-000ff"
    component_name = "Semitrailer_Chassis"


class TrailerResource(TruckResource, ABC):
    resource_class = "Trailer"


class Trailer_Body_Blue(TrailerResource):  # noqa: N801
    asset_id = "snr-T10200-000ff"
    component_name = "Trailer_Body_Blue"
    form = "A"
    color = "Blue"


class Trailer_Body_White(TrailerResource):  # noqa: N801
    asset_id = "snr-T10200-fffff"
    component_name = "Trailer_Body_White"
    form = "A"
    color = "White"


class Trailer_Body_White_Penholder(TrailerResource):  # noqa: N801
    asset_id = "snr-T10201-fffff"
    component_name = "Trailer_Body_White_Penholder"
    resource_class = "Trailer"
    form = "B"
    color = "White"


class LidResource(TruckResource, ABC):
    resource_class = "Lid"


class Lid_A_Black(LidResource):  # noqa: N801
    asset_id = "snr-T10300-0000"
    component_name = "Lid_A_Black"
    form = "A"
    color = "Black"

class Lid_A_Blue(LidResource):  # noqa: N801
    asset_id = "snr-T10301-000ff"
    component_name = "Lid_A_Blue"
    form = "A"
    color = "Blue"


class Lid_A_White(LidResource):  # noqa: N801
    asset_id = "snr-T10302-fffff"
    component_name = "Lid_A_White"
    form = "A"
    color = "White"


class Lid_A_Gray(LidResource):  # noqa: N801
    asset_id = "snr-T10303-808080"
    component_name = "Lid_A_Gray"
    form = "A"
    color = "Gray"


class Semitrailer(TruckResource):  # noqa: N801
    asset_id = "snr-T20000"
    component_name = "Semitrailer"
    resource_class = "Semitrailer"


class Semitrailer_Truck(TruckResource):  # noqa: N801
    asset_id = "snr-T30000"
    component_name = "Semitrailer_Truck"
    resource_class = "Semitrailer_Truck"


class Truck(TruckResource):
    asset_id = "snr-T40000"
    component_name = "Truck"
    resource_class = "Truck"


class WindshieldResource(TruckResource, ABC):
    resource_class = "Windshield"


class Windshield_A_Red(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10001"
    component_name = "Windshield_A_Red"
    form = "A"
    color = "Red"

class Windshield_B_Red(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10002"
    component_name = "Windshield_B_Red"
    form = "B"
    color = "Red"

class Windshield_C_Red(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10003"
    component_name = "Windshield_C_Red"
    form = "C"
    color = "Red"

class Windshield_D_Red(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10004"
    component_name = "Windshield_D_Red"
    form = "D"
    color = "Red"


class Windshield_A_Blue(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10011"
    component_name = "Windshield_A_Blue"
    form = "A"
    color = "Blue"

class Windshield_B_Blue(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10012"
    component_name = "Windshield_B_Blue"
    form = "B"
    color = "Blue"

class Windshield_C_Blue(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10013"
    component_name = "Windshield_C_Blue"
    form = "C"
    color = "Blue"

class Windshield_D_Blue(WindshieldResource):  # noqa: N801
    asset_id = "snr-W10014"
    component_name = "Windshield_D_Blue"
    form = "D"
    color = "Blue"