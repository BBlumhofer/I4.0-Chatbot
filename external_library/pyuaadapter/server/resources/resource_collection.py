from typing import List, TYPE_CHECKING, Type

from pyuaadapter.server.resources.carrier_resource import WST_A, WST_B, WST_C, WST_D, WST_E, WST_F, WST_G
from pyuaadapter.server.resources.nubstone_resource import NubStone_2x2_Blue, NubStone_2x2_Orange, UsbPenDrive_2x4_Blue, \
    UsbPenDrive_2x4_Red, FlatStone_2x4_Black, FlatStone_2x4_Brown
from pyuaadapter.server.resources.truck_resource import Cab_A_Blue, Cab_B_Red, Lid_A_Black, Trailer_Body_Blue, \
    Trailer_Body_White, Trailer_Body_White_Penholder, Semitrailer_Truck, Semitrailer, Truck, Cab_Chassis, \
    Semitrailer_Chassis, Lid_A_White, Lid_A_Blue, Lid_A_Gray

if TYPE_CHECKING:
    from pyuaadapter.server.resources.base_resource import BaseResource


# TODO make methods below generic

def get_all_nubstone_resource_classes() -> List[Type['BaseResource']]:
    return [NubStone_2x2_Blue, NubStone_2x2_Orange,
            UsbPenDrive_2x4_Blue, UsbPenDrive_2x4_Red,
            FlatStone_2x4_Black, FlatStone_2x4_Brown]


def get_all_truck_resource_classes() -> List[Type['BaseResource']]:
    return [Cab_A_Blue, Cab_B_Red, Cab_Chassis,
            Lid_A_Black, Lid_A_White, Lid_A_Blue, Lid_A_Gray,
            Trailer_Body_Blue, Trailer_Body_White, Trailer_Body_White_Penholder, Semitrailer_Chassis,
            Semitrailer_Truck, Semitrailer,
            Truck]


def get_all_carrier_resource_classes() -> List[Type['BaseResource']]:
    return [WST_A, WST_B, WST_C, WST_D, WST_E, WST_F, WST_G]
