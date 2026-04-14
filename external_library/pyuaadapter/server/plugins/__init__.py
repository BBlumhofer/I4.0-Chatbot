
from pyuaadapter.server.plugins.base_plugin import BasePlugin

AVAILABLE_PLUGINS = {
    "Kafka": ".plugin_kafka",
    "CSV": ".plugin_csv"
}

__all__ = ["BasePlugin", "AVAILABLE_PLUGINS"]
