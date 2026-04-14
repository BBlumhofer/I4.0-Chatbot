from __future__ import annotations

import logging
import typing
from abc import ABC

from asyncua import Node, Server, ua
from asyncua.ua import NodeId
from typing_extensions import deprecated

from pyuaadapter.common import NULL_NODE_ID
from pyuaadapter.common.enums import SlotStates
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.resources.base_resource import BaseResource
from pyuaadapter.server.resources.carrier_resource import CarrierResource
from pyuaadapter.server.spatial_object import SpatialObject

if typing.TYPE_CHECKING:
    from pyuaadapter.server.components.base_storage import BaseStorage


class BaseStorageSlot(BaseComponent, ABC):
    """ Abstract base class representing a storage slot. """

    logger = logging.getLogger("sf.server.StorageSlot")

    ua_carrier_id: Node
    """ OPC UA monitoring string variable containing the ID of the carrier. Is empty if no carrier is contained 
    in this slot OR the slot has a carrier, but no information about the carrier ID is available 
    (e.g. ID sensor-less slot). """
    ua_carrier_type: Node
    """ OPC UA monitoring NodeID variable containing the respective resource OPC UA node ID of the carrier
    (only if the carrier is not empty and this information is available). """
    ua_product_id: Node
    """ OPC UA monitoring string variable containing the ID of the product on the carrier. Is empty if no carrier is 
    in this slot OR the carrier is empty OR no information about the product ID is available. """
    ua_slot_empty: Node
    """ OPC UA monitoring boolean variable containing whether this slot is empty or not. 
    This is set EITHER directly from the PLC etc. or via provided method(s). """
    ua_carrier_empty: Node
    """ OPC UA monitoring boolean variable containing whether the carrier in this slot is empty or not. 
    This is usually set via provided method(s). """
    ua_product_type: Node
    """ OPC UA monitoring NodeID variable containing the respective resource OPC UA node ID of the product 
    (only if the carrier is not empty and this information is available). """
    ua_current_state: Node
    """ OPC UA monitoring enum variable containing the current state of this slot. Valid values are from `SlotStates`. 
    Note: For states that rely on information not available to this slot, this state must be written to externally! """

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, config: BaseConfig,
                 storage: BaseStorage | None = None,
                 name: str = "", # TODO Not really optional, but is unfortunately placed behind an optional parameter...
                 spatial_object: SpatialObject | None = None):

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=_id, name=name,
                         config=config, spatial_object=spatial_object)
        self.storage = storage

    async def init(self, parent_node: Node, component_type: Node | None = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always storage_slot_type but to support reflection of child
        """
        from pyuaadapter.server import UaTypes
        await super().init(folder_node=parent_node, component_type=UaTypes.storage_slot_type)

    async def _init_component_identification(self, manufacturer: str | None  = None,
                                             serial_number: str | None  = None,
                                             product_instance_uri: str | None  = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        self.ua_carrier_id = await self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:CarrierID"])
        self.ua_carrier_type = await self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:CarrierType"])
        self.ua_slot_empty = await self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:IsSlotEmpty"])
        self.ua_carrier_empty = await self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:IsCarrierEmpty"])
        self.ua_product_id = await self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:ProductID"])
        # ProductType is optional in node set because it is modelled as 'BaseDataType' we need to add it
        self.ua_product_type = await self.add_monitoring_variable(
            ua.QualifiedName("ProductType", UaTypes.ns_machine_set), NULL_NODE_ID)
        self.ua_current_state = await self.add_monitoring_variable(
            ua.QualifiedName("CurrentState", UaTypes.ns_machine_set),
            ua.Variant(SlotStates.Uninitialized, VariantType=ua.VariantType.UInt32),
            datatype=UaTypes.slot_state_enum.nodeid)

    async def set_current_state(self, state: SlotStates):
        """ Unconditionally sets the current state of this slot to the given state. """
        await self.ua_current_state.set_value(ua.Variant(state, VariantType=ua.VariantType.UInt32))

    async def update_current_state(self):
        """ Updates the current state of this slot automatically based on what the slot can observe. """
        if await self.read_slot_empty():
            await self.set_current_state(SlotStates.Empty)
            return

        carrier_id = await self.read_carrier_id()
        carrier_type = await self.read_carrier_type()
        # TODO @SiJu carrier_type and probably product_type can be None, I suspect a XML modelling mistake
        #  I think our own read_value function that handles everything properly is in order...
        if carrier_id != "":
            await self.set_current_state(SlotStates.LoadedKnown)
        elif isinstance(carrier_type, NodeId) and not carrier_type.is_null():
            await self.set_current_state(SlotStates.LoadedKnown)
        else:
            # Note: The other states are written by skills etc. directly, since we cannot determine these ourselves
            await self.set_current_state(SlotStates.LoadedUnknown)


    async def free_slot(self) -> None:
        """ Frees the slot completely and clears all other variables accordingly. """

        await self._log_info(f"Free slot {self.name}'!")

        await self.ua_carrier_id.write_value("")
        await self.ua_carrier_type.write_value(NULL_NODE_ID)
        await self.ua_slot_empty.write_value(True)

        await self.set_carrier_empty()

    async def set_carrier_empty(self) -> None:
        """ Sets the carrier to empty and clears all variables dependent on product.

        Note: Carrier variables like carrier ID and carrier type will not be reset!
        """
        await self._log_info(f"Set carrier empty of slot '{self.name}'!")

        await self.ua_carrier_empty.write_value(True)
        await self.ua_product_id.write_value("")
        await self.ua_product_type.write_value(NULL_NODE_ID)

        await self.update_current_state()

    async def update_slot_content(self, *, carrier_id: str | None  = None,
                                  carrier_type: str | NodeId | CarrierResource | None  = None,
                                  product_id: str | None  = None,
                                  product_type: str | NodeId | BaseResource | None  = None) -> None:
        """
        Unconditionally updates the slot variables. If carrier information is provided, the slot is automatically
        set to be not empty. Similarly, if product information is provided, the carrier is automatically set to be
        not empty.

        :param carrier_id: id of the carrier (if None carrier_id is not changed)
        :param carrier_type: type of the carrier (if None, carrier_type is not changed)
        :param product_id: id of the product (if None product_id is not changed)
        :param product_type: type of the product (if None product_type is not changed)
        """
        # if we are given resources, we need to grab the node id from them
        if isinstance(carrier_type, CarrierResource):
            carrier_type = carrier_type.ua_node.nodeid
        # and if we are given strings, try to parse them
        elif isinstance(carrier_type, str):
            carrier_type = NodeId.from_string(carrier_type)

        if isinstance(product_type, BaseResource):
            product_type = product_type.ua_node.nodeid
        elif isinstance(product_type, str):
            product_type = NodeId.from_string(product_type)

        if carrier_type is not None:
            await self.ua_carrier_type.write_value(carrier_type)

        if carrier_id is not None:
            initial_carrier_id = await self.read_carrier_id()
            await self.ua_carrier_id.write_value(carrier_id)
            await self._log_info(f"Place carrier '{carrier_id}' into slot '{self.name}' with initial carrier id "
                                 f"{initial_carrier_id}!")

        if carrier_type is not None or carrier_id is not None:
            # we know something about the carrier -> we cannot be empty
            await self.ua_slot_empty.write_value(False)

        if product_id is not None:
            await self.ua_product_id.write_value(product_id)

        if product_type is not None:
            await self.ua_product_type.write_value(product_type)

        if product_id is not None or product_type is not None:
            # we know something about the product -> our carrier cannot be empty
            await self.ua_carrier_empty.write_value(False)
            await self._log_info(f"Place product '{product_id if product_id is not None else ''}' "
                                         f"({product_type if product_type is not None else ''}) "
                                         f"into slot '{self.name}'!")

        await self.update_current_state()


    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change(
            [self.ua_current_state, self.ua_carrier_type, self.ua_carrier_id, self.ua_product_type,
             self.ua_slot_empty, self.ua_carrier_empty, self.ua_product_id], count=count)

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def carrier_id(self) -> str:
        return await self.ua_carrier_id.read_value()

    async def read_carrier_id(self) -> str:
        return await self.ua_carrier_id.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def product_id(self) -> str:
        return await self.ua_product_id.read_value()

    async def read_product_id(self) -> str:
        return await self.ua_product_id.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def slot_empty(self) -> bool:
        return await self.ua_slot_empty.read_value()

    async def read_slot_empty(self) -> bool:
        return await self.ua_slot_empty.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def carrier_empty(self) -> bool:
        return await self.ua_carrier_empty.read_value()

    async def read_carrier_empty(self) -> bool:
        return await self.ua_carrier_empty.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def product_type(self) -> NodeId:
        return await self.ua_product_type.read_value()

    async def read_product_type(self) -> NodeId:
        return await self.ua_product_type.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def carrier_type(self) -> NodeId:
        return await self.ua_carrier_type.read_value()

    async def read_carrier_type(self) -> NodeId:
        return await self.ua_carrier_type.read_value()

    @property
    @deprecated("Please use the corresponding read_* methods instead!")
    async def state(self) -> SlotStates:
        return SlotStates(await self.ua_current_state.read_value())

    async def read_current_state(self) -> SlotStates:
        return SlotStates(await self.ua_current_state.read_value())


    async def _log_info(self, text: str, severity: int = 0) -> None:
        if self.storage is not None:
            await self.storage._log_info(text, severity)
        else:
            await super()._log_info(text, severity)
