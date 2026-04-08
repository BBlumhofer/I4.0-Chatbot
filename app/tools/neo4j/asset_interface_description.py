"""
Neo4j tools for the **AssetInterfaceDescription** submodel.

Covers: interface endpoints, protocols, parameter descriptions.
Semantic ID: https://admin-shell.io/idta/Submodel/AssetInterfaceDescription/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_interface_description(asset_id: str) -> list[dict[str, Any]]:
    """Return interface description elements for an asset."""
    return db.get_submodel_elements(asset_id, "AssetInterfaceDescription")


get_properties = get_interface_description


register_submodel(SubmodelToolset(
    idShort="AssetInterfaceDescription",
    semantic_id="https://admin-shell.io/idta/Submodel/AssetInterfaceDescription/1/0",
    description="Schnittstellenbeschreibung: Protokolle, Endpunkte, Parameter",
    tools={
        "get_interface_description": get_interface_description,
        "get_properties": get_properties,
    },
))
