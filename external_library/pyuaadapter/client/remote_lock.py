from __future__ import annotations

import asyncio
from typing import Any

from asyncua import Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua.uaerrors import BadNoMatch
from typing_extensions import override

from pyuaadapter.client.base_remote_lock import BaseRemoteLock
from pyuaadapter.common.subscription_manager import SubscriptionManager


class RemoteLock(BaseRemoteLock):
    """ Represents the lock folder of the remote module. """
    _ua_locking_user: Node
    _ua_locked: Node
    _ua_locking_client: Node

    @override
    async def init_lock(self) -> None:
        """ Occupies the remote module, will fail when already locked. """
        await self.ua_node.call_method(f"{self.ns_idx_sfm}:InitLock")

    @override
    async def break_lock(self) -> None:
        """ Occupies the remote module, will fail when already locked by higher priority user. """
        await self.ua_node.call_method(f"{self.ns_idx_sfm}:BreakLock")

    @override
    async def exit_lock(self) -> None:
        """ Frees the remote module, will fail when we are not the locking user. """
        await self.ua_node.call_method(f"{self.ns_idx_sfm}:ExitLock")

    @override
    async def renew_lock(self) -> None:
        """ Renews the remote module, will fail when we are not the locking user. """
        await self.ua_node.call_method(f"{self.ns_idx_sfm}:RenewLock")

    @override
    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:
        self._ua_locked = await self._ua_node.get_child(f"{self.ns_idx_sfm}:Locked")
        self._ua_locking_user = await self._ua_node.get_child(f"{self.ns_idx_sfm}:LockingUser")

        nodes_to_subscribe = [self._ua_locked, self._ua_locking_user]

        try:
            self._ua_locking_client = await self._ua_node.get_child(f"{self.ns_idx_sfm}:LockingClient")
            nodes_to_subscribe.append(self._ua_locking_client)
        except BadNoMatch:
            pass  # New in nodeset v4

        await subscription_manager.subscribe_data_change(handler=self, nodes=nodes_to_subscribe)

    @override
    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:
        if node.nodeid == self._ua_locking_user.nodeid:
            self._locking_user = val
            for sub in self._subscribers:
                if asyncio.iscoroutinefunction(sub.on_locking_user_changed):
                    await sub.on_locking_user_changed(val)
                else:
                    sub.on_locking_user_changed(val)
        elif node.nodeid == self._ua_locked.nodeid:
            self._locked = val
            self._locked_since = data.monitored_item.Value.ServerTimestamp if val else None
            for sub in self._subscribers:
                if asyncio.iscoroutinefunction(sub.on_locked_state_changed):
                    await sub.on_locked_state_changed(val)
                else:
                    sub.on_locked_state_changed(val)
        elif node.nodeid == self._ua_locking_client.nodeid:
            self._locking_client = val
