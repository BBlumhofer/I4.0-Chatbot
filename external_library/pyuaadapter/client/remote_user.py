from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from asyncua import Node
from asyncua.common.subscription import DataChangeNotif

from pyuaadapter.common.subscription_manager import SubscriptionManager


class RemoteUserSubscriber:
    """ Subscriber interface for RemoteUser events. """

    def on_user_change(self, user: RemoteUser) -> None:
        """ Is called whenever the state of the subscribed remote component is changed. """
        pass


@dataclass
class RemoteUser:
    """ Represents a remote User. """

    ua_node: Node
    """ Root OPC UA node of the user. """

    name: str = ""
    """ Static property containing the name of the user. """
    allow_multiple: bool = False
    """ Static property indicating whether multiple logins for this user are allowed. """
    user_level: str = ""
    """ Static property indicating the priority of the user (for breaking locks). """
    max_access_level: int = 0
    """ Static property indicating the maximum access level the user has.
     (Refer to minimum access level required to execute certain skills.) """
    is_present: bool = False
    """ Dynamic property indicating whether the user is currently present on the remote server. """
    # TODO ID, CardUid, Language?

    _subscribers: list[RemoteUserSubscriber] = field(default_factory=list)

    @classmethod
    async def create(cls, node: Node, subscription_manager: SubscriptionManager) -> RemoteUser:
        """ Create a new instance of a remote user based on the given root node. """
        user = RemoteUser(ua_node=node)

        for child in await node.get_children():
            bname = await child.read_browse_name()
            if bname.Name in ["Name", "UserRole"]:
                user.name = await child.read_value()
            elif bname.Name == "AllowMultiple":
                user.allow_multiple = await child.read_value()
            elif bname.Name == "UserLevel":
                user.user_level = await child.read_value()
            elif bname.Name == "MaxAccessLevel":
                user.max_access_level = await child.read_value()
            elif bname.Name == "IsPresent":
                user.is_present = await child.read_value()
                await subscription_manager.subscribe_data_change(user, child)

        return user

    def dto(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "allow_multiple": self.allow_multiple,
            "user_level": self.user_level,
            "max_access_level": self.max_access_level,
            "is_present": self.is_present,
            "ua_node": self.ua_node.nodeid.to_string(),
        }

    def __str__(self):
        return f"User '{self.name}' (access-level: {self.max_access_level}, present: {self.is_present})"

    def add_subscriber(self, sub: RemoteUserSubscriber) -> None:
        self._subscribers.append(sub)

    def remove_subscriber(self, sub: RemoteUserSubscriber) -> None:
        self._subscribers.remove(sub)

    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:
        self.is_present = val  # there is currently only one subscription, so we don't need to check which node it is

        for sub in self._subscribers:  # notify subscribers
            if asyncio.iscoroutinefunction(sub.on_user_change):
                await sub.on_user_change(self)
            else:
                sub.on_user_change(self)
