"""
Kafka tools – send control commands to the plant.

IMPORTANT: Every Kafka action *requires* user confirmation.
The graph enforces this via the check_confirmation node.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services import kafka_service as svc

logger = logging.getLogger(__name__)


def send_command(command: dict[str, Any]) -> dict[str, Any]:
    """
    Publish *command* to the Kafka plant command topic.

    Should only be called after the operator has confirmed the action.
    """
    return svc.send_command(command)


# Registry for tool selection
KAFKA_TOOL_REGISTRY: dict[str, Any] = {
    "send_command": send_command,
}
