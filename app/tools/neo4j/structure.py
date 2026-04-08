"""
Neo4j tools for the **Structure** submodel.

Covers: asset sub-structure, component hierarchy.
Semantic ID: https://admin-shell.io/idta/Submodel/HierarchicalStructuresEnablingBoM/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_parts(asset_id: str) -> list[dict[str, Any]]:
    """Return direct structural parts of an asset."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'Structure'})
          -[:HAS_ELEMENT]->(el:SubmodelElement)
    RETURN el.idShort AS part, el.value AS value, el.quantity AS quantity
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_hierarchy(asset_id: str) -> list[dict[str, Any]]:
    """Return the full asset hierarchy reachable from *asset_id*."""
    cypher = """
    MATCH path = (a:Asset {id: $asset_id})-[:HAS_PART*1..5]->(child:Asset)
    RETURN [n IN nodes(path) | n.id] AS hierarchy,
           child.id AS child_id, child.name AS child_name
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all Structure submodel elements (generic fallback)."""
    return db.get_submodel_elements(asset_id, "Structure")


register_submodel(SubmodelToolset(
    idShort="Structure",
    semantic_id="https://admin-shell.io/idta/Submodel/HierarchicalStructuresEnablingBoM/1/0",
    description="Aufbau, Struktur, Komponentenhierarchie",
    tools={
        "get_parts": get_parts,
        "get_hierarchy": get_hierarchy,
        "get_structure": get_parts,
        "list_parts": get_parts,
        "get_properties": get_properties,
    },
))
