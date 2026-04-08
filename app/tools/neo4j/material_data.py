"""
Neo4j tools for the **MaterialData** submodel.

Covers: material properties, classifications, supplier info.
Semantic ID: https://admin-shell.io/idta/Submodel/MaterialData/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_material_data(asset_id: str) -> list[dict[str, Any]]:
    """Return material data submodel elements for an asset."""
    return db.get_submodel_elements(asset_id, "MaterialData")


get_properties = get_material_data


register_submodel(SubmodelToolset(
    idShort="MaterialData",
    semantic_id="https://admin-shell.io/idta/Submodel/MaterialData/1/0",
    description="Materialeigenschaften, Klassifizierung, Lieferanteninfo",
    tools={
        "get_material_data": get_material_data,
        "get_properties": get_properties,
    },
))
