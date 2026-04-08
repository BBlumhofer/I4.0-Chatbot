"""
OPC UA service – async read/write access to a live OPC UA server.
Uses the *asyncua* library.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from asyncua import Client as OpcUaClient

from app.config import settings

logger = logging.getLogger(__name__)


async def read_node_value(node_id: str) -> Any:
    """Read a single node value from the OPC UA server."""
    async with OpcUaClient(url=settings.opcua_endpoint) as client:
        node = client.get_node(node_id)
        value = await node.read_value()
        logger.debug("OPC UA read %s = %s", node_id, value)
        return value


async def get_live_status(node_id: str) -> dict[str, Any]:
    """
    Return a status dict for *node_id*:
      {node_id, value, status, source_timestamp}
    """
    async with OpcUaClient(url=settings.opcua_endpoint) as client:
        node = client.get_node(node_id)
        data_value = await node.read_data_value()
        return {
            "node_id": node_id,
            "value": data_value.Value.Value if data_value.Value else None,
            "status": str(data_value.StatusCode),
            "source_timestamp": (
                data_value.SourceTimestamp.isoformat()
                if data_value.SourceTimestamp
                else None
            ),
        }


def read_node_value_sync(node_id: str) -> Any:
    """Synchronous wrapper around :func:`read_node_value`."""
    return asyncio.run(read_node_value(node_id))


def get_live_status_sync(node_id: str) -> dict[str, Any]:
    """Synchronous wrapper around :func:`get_live_status`."""
    return asyncio.run(get_live_status(node_id))
