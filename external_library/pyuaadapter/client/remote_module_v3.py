from __future__ import annotations

from pyuaadapter.client.remote_component_v3 import RemoteComponent
from pyuaadapter.client.remote_lock import RemoteLock
from pyuaadapter.client.remote_port_v3 import RemotePort


class RemoteModule(RemoteComponent):
    """ Represents a remote module using the skill v3 node set. """

    lock: RemoteLock = None

    @property
    def ports(self) -> dict[str, RemotePort]:
        """ Returns a dictionary of all ports of this remote module. """
        return {key: value for key, value in self.components.items() if isinstance(value, RemotePort)}

    @property
    def type(self) -> str:
        return "Module"