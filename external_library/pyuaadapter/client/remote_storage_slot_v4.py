from __future__ import annotations

from asyncua.ua import NodeId

from pyuaadapter.client.remote_component_v4 import RemoteComponent
from pyuaadapter.common import NULL_NODE_ID
from pyuaadapter.common.enums import SlotStates


class RemoteStorageSlot(RemoteComponent):
    """ Represents a remote storage slot (specialized remote component) using the skill v4 node set. """

    @property
    def type(self) -> str:
        """ Human-readable component type (mainly for UI purposes). """
        return "StorageSlot"

    @property
    def carrier_id(self) -> str | None:
        """ Returns the carrier ID if the slot is occupied, None otherwise. """
        return self.monitoring['CarrierID'].value

    @property
    def carrier_type(self) -> NodeId | str:
        """
        Returns the carrier type (see resources of the machine) either as a node ID or as a string if node IDs
        are unsupported by the OPC UA server (e.g. PLCs).
        """
        if self.monitoring['CarrierType'].value is None:
            return NULL_NODE_ID
        return self.monitoring['CarrierType'].value

    @property
    def product_id(self) -> str | None:
        """ Returns the product ID if both the storage slot and carrier are occupied, None otherwise. """
        return self.monitoring['ProductID'].value

    @property
    def is_slot_empty(self) -> bool:
        """ Flag indicating whether the slot itself is empty. """
        return self.monitoring['IsSlotEmpty'].value

    @property
    def is_carrier_empty(self) -> bool:
        """ Flag indicating whether the carrier in the storage slot is empty. """
        return self.monitoring['IsCarrierEmpty'].value

    @property
    def product_type(self) -> NodeId | str:
        """
        Returns the product type (see resources of the machine) either as a node ID or as a string if node IDs
        are unsupported by the OPC UA server (e.g. PLCs).
        """
        if self.monitoring['ProductType'].value is None:
            return NULL_NODE_ID
        return self.monitoring['ProductType'].value

    @property
    def state(self) -> SlotStates:
        return SlotStates[self.monitoring['CurrentState'].value]