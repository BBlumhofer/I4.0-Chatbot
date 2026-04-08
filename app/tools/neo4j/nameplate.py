"""
Neo4j tools for the **Nameplate** submodel.

Covers: manufacturer info, serial number, hardware/software versions.
Semantic ID: https://admin-shell.io/idta/Submodel/Nameplate/2/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_nameplate(asset_id: str) -> list[dict[str, Any]]:
    """Return all nameplate properties for an asset."""
    return db.get_submodel_elements(asset_id, "Nameplate")


# Alias – same data, explicit intent name for the fallback
get_properties = get_nameplate


register_submodel(SubmodelToolset(
    idShort="Nameplate",
    semantic_id="https://admin-shell.io/idta/Submodel/Nameplate/2/0",
    description="Typschild: Hersteller, Seriennummer, Hardware-/Softwareversion",
    tools={
        "get_nameplate": get_nameplate,
        "get_properties": get_properties,
    },
))
