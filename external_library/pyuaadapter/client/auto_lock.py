import asyncio

import structlog
from typing_extensions import override

from .base_remote_lock import BaseRemoteLock, RemoteLockSubscriber


class AutoLock(RemoteLockSubscriber):

    def __init__(self, lock: BaseRemoteLock, break_lock: bool = False):
        """
        Mechanism that automatically locks given Lock instance. Will try to lock again after the lock is lost of any
        reason (i.e. connection lost, kicked by user with higher priority

        :param lock: The lock instance to automatically lock.
        :param break_lock: Whether to use break_lock() instead of init_lock().

        """
        self._lock = lock
        self._break_lock = break_lock
        self.logger = structlog.getLogger("sf.client.AutoLock")

        self._lock.add_subscriber(self)

    async def lock(self) -> None:
        """Block until we successfully locked the remote module. """
        while not self._lock.locked_by_us:
            try:
                self.logger.info(
                    f"Trying to {'break' if self._break_lock else 'init'} the lock... ",
                    locking_user=self._lock.locking_user, locking_client=self._lock.locking_client
                )
                if self._break_lock:
                    await self._lock.break_lock()
                    break
                else:
                    await self._lock.init_lock()
                    break
            except Exception as ex:
                self.logger.warning("Cannot init lock!", reason=ex)
            await asyncio.sleep(1)

        self.logger.info("Successfully locked!")

    @override
    async def on_locking_user_changed(self, new_locking_user: str) -> None:
        await self.lock()