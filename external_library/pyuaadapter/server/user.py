from __future__ import annotations

from dataclasses import dataclass

from asyncua import Node
try:  # asyncua <=1.1.6
    from asyncua.server.users import User as UaUser, UserRole
except ModuleNotFoundError:  # asyncua >= 1.1.7
    from asyncua.crypto.permission_rules import User as UaUser, UserRole
from asyncua.ua import Int32


@dataclass
class User:
    """ Data class containing all necessary variables for a user (role). """
    name: str
    """ Name of the user """
    password: bytes | str
    """ The password of the user, is assumed to be salted when bytes are used - otherwise cleartext """
    priority: int
    """ Priority of the user, used when breaking the lock. Higher priority users can break the lock of lower 
    priority users. """
    access: int
    """ Access level of the user. All actions (interacting with skills, writing variables, etc.) require a certain
    access level. Higher is better. """
    allow_multiple: bool
    """ Are multiple logins from different clients allowed? """

    role = UserRole.User
    """ is required to for asyncua internals, do NOT touch it! """

    ua_node: None | Node = None
    """ OPC UA root node of the user instance. """

    ua_is_present: None | Node = None
    """ OPC UA (dynamic) node indicating whether this user instance is present. """

    def __str__(self):
        return f"User '{self.name}' (access-level: {self.access})"

    async def ua_init(self, node: Node) -> None:
        self.ua_node = node

        for child in await self.ua_node.get_children():
            bname = await child.read_browse_name()
            if bname.Name in ["Name", "UserRole"]:
                await child.write_value(self.name)
            elif bname.Name == "AllowMultiple":
                await child.write_value(self.allow_multiple)
            elif bname.Name == "UserLevel":
                await child.write_value(str(self.priority))
            elif bname.Name == "MaxAccessLevel":
                await child.write_value(Int32(self.access))
            elif bname.Name == "IsPresent":
                self.ua_is_present = child
                await self.ua_is_present.write_value(False)
            # TODO ID, CardUid, Language?


INTERNAL_USER = UaUser(name="INTERNAL", role=UserRole.Admin)
