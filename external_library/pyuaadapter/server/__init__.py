import contextlib

from pyuaadapter.server.base_config import BaseConfig
from pyuaadapter.server.base_module import BaseModule
from pyuaadapter.server.server import Server
from pyuaadapter.server.ua_types import UaTypes

__all__ = ["BaseConfig", "BaseModule", "Server", "UaTypes"]

def run(config: BaseConfig) -> None:
    """ Runs the OPC-UA server using the given configuration. """
    import asyncio

    with contextlib.suppress(KeyboardInterrupt):  # catch for smoother shutdown
        asyncio.run(run_async(config))


async def run_async(config: BaseConfig) -> None:
    """ Runs the OPC-UA server using the given configuration. """

    _server = Server(config)
    try:
        await _server.init()
        await _server.start()
    except KeyboardInterrupt:
        _server.logger.info("Received KeyboardInterrupt; PyUaAdapter is shutting down")
    finally:
        await _server.shutdown()
