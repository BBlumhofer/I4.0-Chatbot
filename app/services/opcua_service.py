"""
OPC UA service – multi-server, credential-aware access.

Architecture
------------
``OpcUaConnectionManager`` acts as a lightweight registry.  Each connected
server is represented by an ``OpcUaServerConfig`` entry that stores the
endpoint URL, optional credentials, and a *lock* flag that prevents
accidental disconnects while an operation is in flight.

All async helpers accept an explicit *endpoint* parameter so the graph can
fan out across many different OPC UA servers in the same session.  Sync
wrappers (``*_sync``) are provided for use from LangGraph nodes which run
in a synchronous context.

Adding a new server
-------------------
Call ``connection_manager.register(endpoint, username, password)`` (or use
the ``connect_to_server_sync`` tool-level helper) before issuing read/write
commands.  Unregistered endpoints fall back to an anonymous connection so
that the legacy single-server workflow keeps working.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from asyncua import Client as OpcUaClient

from app.config import settings

logger = logging.getLogger(__name__)


# ── Server config dataclass ────────────────────────────────────────────────────

@dataclass
class OpcUaServerConfig:
    """Runtime config for a single OPC UA server connection."""

    endpoint: str
    username: Optional[str] = None
    password: Optional[str] = None
    locked: bool = False


# ── Connection manager ─────────────────────────────────────────────────────────

class OpcUaConnectionManager:
    """
    Registry of OPC UA server configurations for the current process.

    Thread-safety note: this registry is process-global and mutated from
    synchronous code.  It is intentionally simple – no concurrent locking –
    because the LangGraph runtime is single-threaded per graph invocation.
    """

    def __init__(self) -> None:
        self._servers: dict[str, OpcUaServerConfig] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        endpoint: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> OpcUaServerConfig:
        """Register (or update) a server entry.  Returns the config."""
        cfg = OpcUaServerConfig(
            endpoint=endpoint,
            username=username,
            password=password,
        )
        self._servers[endpoint] = cfg
        logger.info("OPC UA server registered: %s (user=%s)", endpoint, username or "<anonymous>")
        return cfg

    def unregister(self, endpoint: str) -> bool:
        """Remove a server entry.  Returns True if it existed."""
        if endpoint in self._servers:
            del self._servers[endpoint]
            logger.info("OPC UA server unregistered: %s", endpoint)
            return True
        return False

    def get(self, endpoint: str) -> Optional[OpcUaServerConfig]:
        """Return the config for *endpoint*, or None if not registered."""
        return self._servers.get(endpoint)

    def get_or_default(self, endpoint: str) -> OpcUaServerConfig:
        """Return a config, falling back to anonymous if not registered."""
        return self._servers.get(endpoint) or OpcUaServerConfig(endpoint=endpoint)

    def list_servers(self) -> list[dict[str, Any]]:
        """Return a serialisable summary of all registered servers."""
        return [
            {
                "endpoint": cfg.endpoint,
                "username": cfg.username,
                "locked": cfg.locked,
            }
            for cfg in self._servers.values()
        ]

    # ── Lock management ───────────────────────────────────────────────────────

    def lock(self, endpoint: str) -> bool:
        """Set the lock flag for *endpoint*.  Returns True on success."""
        cfg = self._servers.get(endpoint)
        if cfg is None:
            logger.warning("lock: endpoint not registered – %s", endpoint)
            return False
        cfg.locked = True
        logger.info("OPC UA server locked: %s", endpoint)
        return True

    def unlock(self, endpoint: str) -> bool:
        """Clear the lock flag for *endpoint*.  Returns True on success."""
        cfg = self._servers.get(endpoint)
        if cfg is None:
            return False
        cfg.locked = False
        logger.info("OPC UA server unlocked: %s", endpoint)
        return True

    def is_locked(self, endpoint: str) -> bool:
        cfg = self._servers.get(endpoint)
        return cfg.locked if cfg else False

    # ── Context manager helper ────────────────────────────────────────────────

    def _make_client(self, endpoint: str) -> OpcUaClient:
        """Create an *asyncua* Client pre-configured with stored credentials."""
        cfg = self.get_or_default(endpoint)
        client = OpcUaClient(url=cfg.endpoint)
        if cfg.username:
            client.set_user(cfg.username)
        if cfg.password:
            client.set_password(cfg.password)
        return client


# Process-global manager instance
connection_manager = OpcUaConnectionManager()


# ── Async helpers ──────────────────────────────────────────────────────────────

async def validate_connection(endpoint: str, username: Optional[str], password: Optional[str]) -> dict[str, Any]:
    """
    Open a short-lived connection to *endpoint* to verify credentials.
    Raises on failure (connection refused, bad credentials, …).
    Returns a dict with server info on success.
    """
    client = OpcUaClient(url=endpoint)
    if username:
        client.set_user(username)
    if password:
        client.set_password(password)
    async with client:
        server_node = client.get_node("i=2253")  # Server node
        namespace_array = await client.get_namespace_array()
        logger.info("OPC UA connection validated: %s", endpoint)
        return {
            "endpoint": endpoint,
            "username": username or "<anonymous>",
            "namespaces": namespace_array,
            "status": "connected",
        }


async def browse_nodes(endpoint: str, node_id: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Browse child nodes of *node_id* (defaults to the Objects folder) on
    *endpoint*.  Returns a list of {node_id, display_name, node_class} dicts.
    """
    client = connection_manager._make_client(endpoint)
    async with client:
        if node_id:
            node = client.get_node(node_id)
        else:
            node = client.nodes.objects
        children = await node.get_children()
        result = []
        for child in children:
            try:
                display_name = (await child.read_display_name()).Text
                node_class = str(await child.read_node_class())
            except Exception:
                display_name = str(child)
                node_class = "unknown"
            result.append({
                "node_id": child.nodeid.to_string(),
                "display_name": display_name,
                "node_class": node_class,
            })
        return result


async def read_node_value(endpoint: str, node_id: str) -> Any:
    """Read a single node value from *endpoint*."""
    client = connection_manager._make_client(endpoint)
    async with client:
        node = client.get_node(node_id)
        value = await node.read_value()
        logger.debug("OPC UA read %s @ %s = %s", node_id, endpoint, value)
        return value


async def get_live_status(endpoint: str, node_id: str) -> dict[str, Any]:
    """
    Return a status dict for *node_id* on *endpoint*:
      {endpoint, node_id, value, status, source_timestamp}
    """
    client = connection_manager._make_client(endpoint)
    async with client:
        node = client.get_node(node_id)
        data_value = await node.read_data_value()
        return {
            "endpoint": endpoint,
            "node_id": node_id,
            "value": data_value.Value.Value if data_value.Value else None,
            "status": str(data_value.StatusCode),
            "source_timestamp": (
                data_value.SourceTimestamp.isoformat()
                if data_value.SourceTimestamp
                else None
            ),
        }


# ── Sync wrappers ──────────────────────────────────────────────────────────────

def validate_connection_sync(
    endpoint: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, Any]:
    return asyncio.run(validate_connection(endpoint, username, password))


def browse_nodes_sync(
    endpoint: str,
    node_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    return asyncio.run(browse_nodes(endpoint, node_id))


def read_node_value_sync(endpoint: str, node_id: str) -> Any:
    return asyncio.run(read_node_value(endpoint, node_id))


def get_live_status_sync(endpoint: str, node_id: str) -> dict[str, Any]:
    return asyncio.run(get_live_status(endpoint, node_id))
