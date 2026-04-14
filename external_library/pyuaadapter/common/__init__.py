from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any

import orjson
import structlog
from asyncua import Node, ua
from asyncua.ua import NodeId

NULL_NODE_ID = NodeId.from_string("ns=0;i=0")
""" This node id indicates an invalid Node ID and should be treated as 'None'. """


async def get_type_definition(node: Node) -> str:
    """ Returns the browse name of the OPC UA type definition of the given node. """

    try:
        type_definition_list = await node.get_references(ua.ObjectIds.HasTypeDefinition, ua.BrowseDirection.Forward)
        return type_definition_list[0].BrowseName.Name
    except Exception as ex:
        raise RuntimeError(f"Could not find type definition for node {node.nodeid.to_string()}!") from ex

###############################

def _format_elapsed(seconds: float) -> str:
    """ Formats given seconds float into short human-readable string. """
    if seconds >= 1:
        return f"{seconds:.3f}s"
    return f"{seconds * 1000:.1f}ms"

def _elapsed_to_ms(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    """ structlog processor to convert "elapsed" entry in event dict to shorter format. """
    if "elapsed" in event_dict:
        event_dict["elapsed"] = _format_elapsed(event_dict["elapsed"])
    return event_dict

""" Global flag indicated whether logging is initialized. """
_logging_initialized = False

class LogFormat(IntEnum):
    KeyValue = 0
    Json = 1

def setup_logging(*,
                  log_levels: dict[str, int | str] | None = None,
                  log_format: LogFormat = LogFormat.KeyValue) -> None:
    """ Sets up logging """
    global _logging_initialized
    if _logging_initialized:
        return

    logging.basicConfig(force=True, format=None)
    if log_levels is not None:
        logger = logging.getLogger("sf.common.logging")
        for name, level in log_levels.items():
            try:
                logging.getLogger(name).setLevel(level)
            except (TypeError, ValueError) as err:
                logger.error(f"Could not set logger level. {name=}, {level=}, reason='{err}'")

    # see https://www.structlog.org/en/stable/logging-best-practices.html#pretty-printing-vs-structured-output
    if log_format == LogFormat.KeyValue:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            _elapsed_to_ms,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(sort_keys=False),
        ]
        logger_factory = structlog.stdlib.LoggerFactory()
    else:  # JSON
        processors = [
            structlog.contextvars.merge_contextvars,
            # structlog.stdlib.filter_by_level,
            # structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            _elapsed_to_ms,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ]
        logger_factory = structlog.BytesLoggerFactory()

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        logger_factory=logger_factory,
        cache_logger_on_first_use=True,
    )

    _logging_initialized = True
