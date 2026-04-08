"""
OPC UA tools – read live values from the connected OPC UA server.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services import opcua_service as svc

logger = logging.getLogger(__name__)


def get_live_status(node_id: str) -> dict[str, Any]:
    """Return current status / data-value for *node_id*."""
    return svc.get_live_status_sync(node_id)


def read_value(node_id: str) -> Any:
    """Read a raw scalar value from *node_id*."""
    return svc.read_node_value_sync(node_id)


# Registry for tool selection
OPCUA_TOOL_REGISTRY: dict[str, Any] = {
    "get_live_status": get_live_status,
    "read_value": read_value,
}
