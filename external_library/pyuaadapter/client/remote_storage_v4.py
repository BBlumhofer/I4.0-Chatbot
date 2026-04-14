from __future__ import annotations

from pyuaadapter.client.remote_component_v4 import RemoteComponent
from pyuaadapter.client.remote_storage_slot_v4 import RemoteStorageSlot


class RemoteStorage(RemoteComponent):
    """ Represents a remote storage (specialized remote component) using the skill v4 node set. """

    @property
    def type(self) -> str:
        """ Human-readable component type (mainly for UI purposes). """
        return "Storage"

    @property
    def slots(self) -> dict[str, RemoteStorageSlot]:
        """ Returns a dictionary of all storages of this remote module. """
        return {key: value for key, value in self.components.items() if isinstance(value, RemoteStorageSlot)}