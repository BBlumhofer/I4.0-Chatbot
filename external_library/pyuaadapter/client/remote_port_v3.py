from __future__ import annotations

from pyuaadapter.client.mixins.couple_mixin import CoupleMixin
from pyuaadapter.client.remote_component_v3 import RemoteComponent


class RemotePort(CoupleMixin, RemoteComponent):
    """ Represents a remote port (specialized remote component) using the skill v3 node set. """

    @property
    def active_port(self) -> bool:
        """ Returns whether the remote port is active. """
        return self.monitoring['ActivePort'].value

    @property
    def own_rfid_tag(self) -> str:
        """ Returns the own RFID tag of the remote port. """
        return self.monitoring['OwnRfidTag'].value

    @property
    def partner_rfid_tag(self) -> str:
        """ Returns the RFID tag of the partner port this port is coupled/near enough to. """
        return self.monitoring['PartnerRfidTag'].value

    @property
    def position(self) -> list[float]:
        """ Returns the position (X, Y, Z) of this remote port. """
        return self.monitoring['Position'].value

    @property
    def type(self) -> str:
        return "Port"