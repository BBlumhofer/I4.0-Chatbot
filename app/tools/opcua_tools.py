"""
OPC UA tools – multi-server, credential-aware.

Each tool accepts an *endpoint* URL so the graph can work with many
different OPC UA servers within the same chat session.  User credentials
are stored in the process-global ``connection_manager`` after a successful
``connect_to_server`` call and are reused automatically for subsequent
tool calls to the same endpoint.

Available tools
---------------
connect_to_server   – register credentials and validate the connection
disconnect          – unregister a server (clears stored credentials)
browse              – list child nodes of a node (or the Objects folder)
lock_server         – mark a server as locked to prevent accidental commands
get_live_status     – read a node's full DataValue (value + status + timestamp)
read_value          – read a raw scalar value

Adding more tools
-----------------
Define the function (using ``svc`` helpers) and add it to
``OPCUA_TOOL_REGISTRY``.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings
from app.services import opcua_service as svc

logger = logging.getLogger(__name__)


# ── Tool functions ─────────────────────────────────────────────────────────────

def connect_to_server(
    endpoint: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, Any]:
    """
    Register an OPC UA server and validate the connection.

    Stores the credentials in the connection manager so that subsequent
    read/browse/lock calls to the same *endpoint* use them automatically.
    Raises on connection failure (bad URL, wrong credentials, server offline).
    """
    info = svc.validate_connection_sync(endpoint, username, password)
    svc.connection_manager.register(endpoint, username, password)
    return info


def disconnect(endpoint: str) -> dict[str, Any]:
    """
    Unregister *endpoint* from the connection manager and clear its credentials.

    The OPC UA protocol itself is stateless between requests (every tool call
    opens and closes its own session), so this only removes the local config.
    Returns a status dict.
    """
    removed = svc.connection_manager.unregister(endpoint)
    return {
        "endpoint": endpoint,
        "status": "disconnected" if removed else "not_registered",
    }


def browse(
    endpoint: str,
    node_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Browse the child nodes of *node_id* on *endpoint*.

    If *node_id* is omitted, the OPC UA Objects folder is browsed.
    Returns a list of {node_id, display_name, node_class} dicts.
    Credentials from a previous ``connect_to_server`` call are used
    automatically.
    """
    return svc.browse_nodes_sync(endpoint, node_id)


def lock_server(endpoint: str) -> dict[str, Any]:
    """
    Mark *endpoint* as locked in the connection manager.

    A locked server will not be unregistered by ``disconnect`` until
    explicitly unlocked.  This is a soft application-level lock; it does
    not interact with the OPC UA GDS or SessionActivate mechanism.
    Returns a status dict.
    """
    success = svc.connection_manager.lock(endpoint)
    return {
        "endpoint": endpoint,
        "locked": success,
        "status": "locked" if success else "not_registered",
    }


def get_live_status(
    endpoint: str,
    node_id: str,
) -> dict[str, Any]:
    """
    Return the current DataValue for *node_id* on *endpoint*:
    {endpoint, node_id, value, status, source_timestamp}.
    """
    return svc.get_live_status_sync(endpoint, node_id)


def read_value(
    endpoint: str,
    node_id: str,
) -> Any:
    """Read a raw scalar value from *node_id* on *endpoint*."""
    return svc.read_node_value_sync(endpoint, node_id)


# ── Registry ───────────────────────────────────────────────────────────────────

OPCUA_TOOL_REGISTRY: dict[str, Any] = {
    "connect_to_server": connect_to_server,
    "disconnect": disconnect,
    "browse": browse,
    "lock_server": lock_server,
    "get_live_status": get_live_status,
    "read_value": read_value,
}
