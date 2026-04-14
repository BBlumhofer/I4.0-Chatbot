"""
Kafka service – thin producer wrapper.

Every command is sent as a JSON message on the configured topic.
All writes REQUIRE a prior confirmation step (enforced in the graph).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaProducer

from app.config import settings

logger = logging.getLogger(__name__)

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def send_command(command: dict[str, Any]) -> dict[str, Any]:
    """
    Publish *command* to the plant command topic.

    Returns a receipt dict.
    """
    producer = get_producer()
    future = producer.send(settings.kafka_command_topic, value=command)
    metadata = future.get(timeout=10)
    logger.info("Kafka command sent: topic=%s partition=%s offset=%s",
                metadata.topic, metadata.partition, metadata.offset)
    return {
        "status": "sent",
        "topic": metadata.topic,
        "partition": metadata.partition,
        "offset": metadata.offset,
        "command": command,
    }
