"""
Neo4j tools for the **FaultDescription** submodel.

Covers: fault codes, descriptions, recommended actions.
Semantic ID: https://admin-shell.io/idta/Submodel/FaultDescription/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_fault_descriptions(asset_id: str) -> list[dict[str, Any]]:
    """Return fault code descriptions for an asset."""
    return db.get_submodel_elements(asset_id, "FaultDescription")


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all FaultDescription submodel elements (generic fallback)."""
    return db.get_submodel_elements(asset_id, "FaultDescription")


register_submodel(SubmodelToolset(
    idShort="FaultDescription",
    semantic_id="https://admin-shell.io/idta/Submodel/FaultDescription/1/0",
    description="Fehlerbeschreibungen, Fehlercodes, Handlungsempfehlungen",
    tools={
        "get_fault_descriptions": get_fault_descriptions,
        "get_properties": get_properties,
    },
))
