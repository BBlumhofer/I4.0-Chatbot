from __future__ import annotations

from typing import TYPE_CHECKING

from asyncua import Node, Server

from pyuaadapter.common import NULL_NODE_ID
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.components.base_storage import BaseStorage
from pyuaadapter.server.components.base_storage_slot import BaseStorageSlot
from pyuaadapter.server.resources.base_resource import BaseResource
from pyuaadapter.server.resources.carrier_resource import CarrierResource
from pyuaadapter.server.skills.storage_skills import StoreSkill
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem


class BinarySwitchStorageSlot(BaseStorageSlot):
    """
    This storage slot represents a physical storage slot with only a binary switch to detect the presence
    of a carrier. There is no hardware to read the ID of the carrier, it must be set from somewhere else.

    Parameters:
        add_store_skill : If `True`, a Store-Skill will be added to this slot using the provided resources
        store_product_resources : List of product resources the Store-Skill should be able to store in this slot.
            Only used if add_store_skill is `True`.
        store_carrier_resources : List of carrier resources the Store-Skill should be able to store in this slot.
            Only used if add_store_skill is `True`.

    Note:
        This binary switch should correspond to the slot_empty variable. This class uses a  subscription on
        that variable that clears the other variables when the slot is set to empty.
    """

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, config: BaseConfig,
                 storage: BaseStorage | None = None,
                 name: str = "", # TODO Not really optional, but is unfortunately placed behind an optional parameter...
                 spatial_object: SpatialObject | None = None,
                 *,
                 add_store_skill = False,
                 store_product_resources: list[BaseResource] | None = None,
                 store_carrier_resources: list[CarrierResource] | None = None
                 ):
        super().__init__(server=server, parent=parent, ns_idx=ns_idx, _id=_id, config=config,
                         storage=storage, name=name, spatial_object=spatial_object)
        self._add_store_skill = add_store_skill
        self._store_product_resources = store_product_resources if store_product_resources is not None else []
        self._store_carrier_resources = store_carrier_resources if store_carrier_resources is not None else []
        if self._add_store_skill and len(self._store_product_resources) == 0:
            raise ValueError("If you want to use the store skill, please provide a list of valid product resources!")
        if self._add_store_skill and len(self._store_carrier_resources) == 0:
            raise ValueError("If you want to use the store skill, please provide a list of valid carrier resources!")

    async def _init_skills(self) -> None:
        await super()._init_skills()

        if self._add_store_skill:
            await self.add_skill(StoreSkill, carrier_resources=self._store_carrier_resources,
                                 product_resources=self._store_product_resources)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        # setup subscription to monitor the slot empty variable, so that we can clear everything if the slot is empty
        self._ua_subscription = await self.server.create_subscription(100, self)
        await self._ua_subscription.subscribe_data_change(self.ua_slot_empty)

    async def datachange_notification(self, node: Node, val, data) -> None:
        """ OPC UA callback when the data of a node subscription changed. """
        if node == self.ua_slot_empty:
            if val:  # slot is empty
                # clear the rest of the variables
                await self.ua_carrier_id.write_value("")
                await self.ua_carrier_type.write_value(NULL_NODE_ID)
                await self.set_carrier_empty()
            else:  # slot is not empty
                await self.update_current_state()