from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC
from asyncio import Task
from typing import Any, Dict, Generic, Type, TypeVar

import structlog
from asyncua import Node, Server, ua
from asyncua.ua import NodeId

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.common import write_range
from pyuaadapter.server.components.base_storage_slot import BaseStorageSlot
from pyuaadapter.server.methods.storage_methods import ExportStorageDataMethod, ImportStorageDataMethod
from pyuaadapter.server.resources.base_resource import BaseResource
from pyuaadapter.server.resources.carrier_resource import CarrierResource
from pyuaadapter.server.spatial_object import SpatialObject

S = TypeVar("S", bound="BaseStorageSlot")


async def filter_slots(slots: dict[str, S], *,
                       slot_empty: bool | None = None,
                       carrier_empty: bool | None = None,
                       carrier_type: NodeId | CarrierResource | None = None,
                       carrier_id: str | None = None,
                       product_type: NodeId | BaseResource | None = None,
                       product_id: str | None = None
                       ) -> dict[str, S]:
    """ Returns all storage slots that fulfill the given requirements. """
    if isinstance(carrier_type, CarrierResource):
        carrier_type = carrier_type.ua_node.nodeid
    if isinstance(product_type, BaseResource):
        product_type = product_type.ua_node.nodeid

    found_slots = {}
    for name, slot in slots.items():
        if slot_empty is not None and (await slot.ua_slot_empty.read_value()) != slot_empty:
            continue
        if carrier_empty is not None and (await slot.ua_carrier_empty.read_value()) != carrier_empty:
            continue
        if carrier_id is not None and (await slot.ua_carrier_id.read_value()) != carrier_id:
            continue
        if carrier_type is not None and (await slot.ua_carrier_type.read_value()) != carrier_type:
            continue
        if product_type is not None and (await slot.ua_product_type.read_value()) != product_type:
            continue
        if product_id is not None and (await slot.ua_product_id.read_value()) != product_id:
            continue

        # all requirements fulfilled
        found_slots[name] = slot

    return found_slots


class BaseStorage(BaseComponent, Generic[S], ABC):
    """ Abstract base class representing a storage.

    Handles the free slot monitoring automatically with subscriptions using slot.ua_slot_empty changes.
    """

    ua_slot_count: Node
    ua_free_slot_count: Node

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: int, name: str, config: BaseConfig,
                 slot_count: int | tuple[int, int],
                 spatial_object: SpatialObject | None = None,
                 slot_type: Type[S] = BaseStorageSlot,  # type: ignore
                 storage_slot_kwargs: Dict[str, Any] | None = None):
        """ Creates a new storage instance.

        :param slot_count: number of slots to instantiate. Can be a single number or a range with [start, stop] with s
            start >= 1, stop > start (both values included!)
        :param slot_type: Storage slot class to use for instantiation
        :param storage_slot_kwargs: key-word arguments passed to storage slot __init__ during instantiation
        """
        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=str(_id), name=name,
                         config=config, spatial_object=spatial_object)
        if isinstance(slot_count, (tuple, list)):
            if len(slot_count) != 2:
                raise ValueError("Please provide exactly 1 or 2 int values for slot_count!")
            if slot_count[0] < 1:
                raise ValueError(f"The provided start value {slot_count[0]} for slot_count needs to be "
                                 f"greater equal than 1!")
            if slot_count[1] < slot_count[0]:
                raise ValueError(f"The end value {slot_count[1]} for slot_count needs to be greater "
                                 f"than the start value {slot_count[0]}")
            self._slot_start = int(slot_count[0])
            self._slot_count = int(slot_count[1]) - int(slot_count[0]) + 1  # include stop value as well
        else:
            self._slot_start = 1
            self._slot_count = int(slot_count)

        self._free_slot_count = self._slot_count
        self._storage_slot_type = slot_type
        self._storage_slot_kwargs = {} if storage_slot_kwargs is None else storage_slot_kwargs
        self._update_task: Task | None = None
        """ Asynchronous task handling the free slot update mechanism. """
        self._update_required = True
        """ Flag indicated whether our free slot count needs updating. """
        self.logger = structlog.getLogger("sf.server.Storage", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node | None = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always storage_type but to support reflection of child
        """
        
        from pyuaadapter.server import UaTypes
        await super().init(folder_node=parent_node, component_type=UaTypes.storage_type)

        await self.add_method(ExportStorageDataMethod)
        await self.add_method(ImportStorageDataMethod)

    async def _init_component_identification(self, manufacturer: str | None = None,
                                             serial_number: str | None = None,
                                             product_instance_uri: str | None = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_attributes(self) -> None:
        await super()._init_attributes()

        from pyuaadapter.server import UaTypes

        self.ua_slot_count = await self.ua_attributes.get_child([f"{UaTypes.ns_machine_set}:StorageSlotCount"])
        await self.ua_slot_count.write_value(ua.UInt16(self._slot_count))

    async def _init_monitoring(self):
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        self.ua_free_slot_count = await self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:FreeStorageSlotCount"])

        await asyncio.gather(
            write_range(self.ua_free_slot_count, (0, self._slot_count)),
            self.ua_free_slot_count.write_value(ua.Variant(self._free_slot_count, VariantType=ua.VariantType.UInt16)))

        self._update_task = asyncio.create_task(self._update_free_slot_count())

    async def datachange_notification(self, node: Node, val, data):
        """ OPC UA callback when the data of a node subscription changed. """
        # we are only subscribed to "slot empty" nodes of storage slots,
        # so we need to update the free storage slot count
        self._update_required = True

    async def _init_components(self) -> None:
        await super()._init_components()

        for n in range(self._slot_start, self._slot_start + self._slot_count):
            # not gathered cause gather(*slots) requires more time
            await self.add_component(_id=str(uuid.uuid4()), name=f"Slot_{n}", component_type=self._storage_slot_type,
                                     storage=self, **self._storage_slot_kwargs)

        if self._slot_count > 0:
            await self._init_notification()

        subscription_nodes = []
        for slot in self.slots.values():
            subscription_nodes.append(slot.ua_slot_empty)

        if len(subscription_nodes) > 0:
            self._ua_subscription = await self.server.create_subscription(100, self)
            await self._ua_subscription.subscribe_data_change(subscription_nodes)

    async def _update_free_slot_count(self):
        while True:
            if self._update_required:
                self._update_required = False  # we might get further updates while processing all slots
                free_slot_count = self._slot_count

                for slot in self.slots.values():
                    if not await slot.read_slot_empty():
                        free_slot_count -= 1

                self._free_slot_count = free_slot_count

                self.logger.info(f"Setting free slot count to {free_slot_count}!")
                await self.ua_free_slot_count.write_value(ua.Variant(self._free_slot_count, VariantType=ua.VariantType.UInt16))
            await asyncio.sleep(0.1)

    @property
    def slot_count(self) -> int:
        return self._slot_count

    @property
    def free_slot_count(self) -> int:
        return self._free_slot_count

    @property
    def slots(self) -> Dict[str, S]:
        """ Returns all storage slot components of this storage. """
        return {name: comp for name, comp in self.components.items() if isinstance(comp, BaseStorageSlot)}  # type: ignore

    async def filter_slots(self, *,
                           slot_empty: bool | None = None,
                           carrier_empty: bool | None = None,
                           carrier_type: NodeId | CarrierResource | None = None,
                           carrier_id: str | None = None,
                           product_type: NodeId | BaseResource | None = None,
                           product_id: str | None = None
                           ) -> dict[str, S]:
        """ Returns all storage slots that fulfill the given requirements. """
        return await filter_slots(self.slots, slot_empty=slot_empty, carrier_empty=carrier_empty,
                                  carrier_type=carrier_type, carrier_id=carrier_id, product_type=product_type,
                                  product_id=product_id)