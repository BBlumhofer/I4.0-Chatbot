from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pyuaadapter.server import BaseConfig

if TYPE_CHECKING:  # prevent circular imports during run-time
    from pyuaadapter.server.base_module import BaseModule


class BasePlugin(ABC):
    """ Interface for plugins providing optional features like kafka reporting. """

    def __init__(self, config: BaseConfig):
        self.config = config

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check whether the plugin is enabled in the given configuration."""
        raise NotImplementedError

    @abstractmethod
    async def init(self, module: 'BaseModule') -> None:
        """ Initialization method for plugins, is called before module has finished its initialization. """
        raise NotImplementedError

    @abstractmethod
    async def after_module_init(self) -> None:
        """ This callback is called after the module has finished its initialization. """
        raise NotImplementedError
