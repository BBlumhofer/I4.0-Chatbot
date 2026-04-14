import asyncio

from asyncua import Server
from typing_extensions import override

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.components.base_port import BasePort
from pyuaadapter.server.skills.base_couple_skill import BaseContinuousCoupleSkill
from pyuaadapter.server.user import User


class DummyPortCoupleSkill(BaseContinuousCoupleSkill):
    """
    Dummy implementation of a port couple skill. Does nothing internally, but simulates the physical
    mating process by waiting 2 seconds (by default) between (old) mate() and finally being mated.
    """

    def __init__(self, machinery_item: BasePort, rfid_tag_neighbor: int, delay: float = 2):
        super().__init__(machinery_item)
        self.rfid_tag_neighbor = rfid_tag_neighbor
        self.delay = delay

    @override
    async def _handle_resetting(self):
        await self.port.set_monitoring_values("", False)  # reset neighbor tag value

    @override
    async def _handle_halting(self):
        """ Corresponds to old unmate()"""
        await self.port.set_monitoring_values("", False)  # reset neighbor tag value

    @override
    async def _handle_starting(self):
        """Corresponds to old mate()"""
        await asyncio.sleep(self.delay)
        await self.port.set_monitoring_values(self.rfid_tag_neighbor, True)  # reset neighbor tag value

    @override
    async def _handle_running(self):
        while True:
            await asyncio.sleep(99999)



class DummyPort(BasePort):
    """
    Dummy implementation of a port for development purposes.
    """

    def __init__(self, *,
                 ns_idx: int,
                 parent: "BaseMachineryItem",
                 server: Server,
                 _id: str,
                 name: str,
                 rfid_tag_own: int,
                 config: BaseConfig,
                 rfid_tag_neighbor: int, delay: float = 2, spatial_object=None):
        super().__init__(server, parent, ns_idx, _id, name, rfid_tag_own, config, spatial_object=spatial_object,
                         couple_skill=DummyPortCoupleSkill,
                         couple_skill_kwargs={'rfid_tag_neighbor': rfid_tag_neighbor, 'delay': delay})

    async def _condition_neighbor_detected(self, _user: User) -> bool:
        return True
