"""
Neo4j tools for the **Agents** graph view.

Covers: nodes reachable from Agent entities and their normalized properties.
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


SUBMODEL = "Agents"


def list_connected_node_properties(
    shell_id: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Return distinct node property maps reachable from Agent nodes."""
    return db.get_agent_connected_node_properties(shell_id=shell_id, limit=limit)


def get_properties(
    shell_id: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Generic fallback for the Agents view."""
    return list_connected_node_properties(shell_id=shell_id, limit=limit)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://smartfactory.de/idta/Submodel/Agents/1/0",
    description="Agent-Topologie und verbundene Knoten-Eigenschaften",
    tools={
        "list_connected_node_properties": list_connected_node_properties,
        "get_agent_nodes": list_connected_node_properties,
        "get_properties": get_properties,
    },
))
