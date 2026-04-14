from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Node
from asyncua.common.subscription import DataChangeNotif

from pyuaadapter.common.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from .remote_server import RemoteServer


class RemoteLockSubscriber:
    """ Subscriber interface for RemoteLock events. """

    def on_locked_state_changed(self, new_state: bool) -> None:
        """ Is called whenever the locked state is changed. """
        pass

    def on_locking_user_changed(self, new_locking_user: str) -> None:
        pass


class BaseRemoteLock(ABC):
    def __init__(self, node: Node, remote_server: "RemoteServer", ns_idx_sfm: int):
        self._ua_node = node
        self._remote_server = remote_server
        self.ns_idx_sfm = ns_idx_sfm

        self._locking_user = ""
        self._locking_client = ""
        self._locked = False
        self._locked_since: datetime | None = None

        self._subscribers: list[RemoteLockSubscriber] = []

        self.logger = structlog.getLogger("sf.client.RemoteLock")

    @property
    def ua_node(self) -> Node:
        return self._remote_server.ua_client.get_node(self._ua_node.nodeid)

    def dto(self) -> dict[str, Any]:
        return {
            "locked": self.locked,
            "locking_user": self.locking_user,
            "locking_client": self.locking_client,
            "locked_since": self.locked_since.isoformat() if self.locked_since is not None else None,
        }

    def add_subscriber(self, subscriber: RemoteLockSubscriber) -> None:
        """ Adds given subscriber to the list of subscribers to be notified. """
        self._subscribers.append(subscriber)

    @abstractmethod
    async def init_lock(self) -> None:
        """ Occupies the remote module, will fail when already locked. """
        pass

    @abstractmethod
    async def break_lock(self) -> None:
        """ Occupies the remote module, will fail when already locked by higher priority user. """
        pass

    @abstractmethod
    async def exit_lock(self) -> None:
        """ Frees the remote module, will fail when we are not the locking user. """
        pass

    @abstractmethod
    async def renew_lock(self) -> None:
        """ Renews the remote module, will fail when we are not the locking user. """
        pass

    @abstractmethod
    async def setup_subscriptions(self, subscription_manager: SubscriptionManager) -> None:
        pass

    @abstractmethod
    async def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:
        pass

    @property
    def locked(self) -> bool:
        """ True if module is locked, false otherwise. """
        return self._locked

    @property
    def locking_user(self) -> str:
        """ Empty when module is unlocked, otherwise name of the locking user. """
        return self._locking_user

    @property
    def locked_since(self) -> datetime | None:
        """ Returns the time when the current user locked the asset. Is None when Lock is unlocked. """
        return self._locked_since

    @property
    def locking_client(self) -> str:
        """ Empty when module is unlocked, otherwise hostname of the locking user. """
        return self._locking_client

    @property
    def locked_by_us(self) -> bool:
        return self.locked and self.locking_user == self._remote_server.username
