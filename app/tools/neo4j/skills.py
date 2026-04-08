"""
Neo4j tools for the **Skills** submodel.

Covers: capabilities / skills of a resource asset (IDTA Skills concept).
Semantic ID: https://admin-shell.io/idta/Submodel/Skills/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_skills(asset_id: str) -> list[dict[str, Any]]:
    """Return skill definitions for a resource asset."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'Skills'})
          -[:HAS_ELEMENT]->(skill:SubmodelElement)
    RETURN skill.idShort AS skill, skill.value AS value,
           skill.skillIri AS skillIri
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all Skills submodel elements (generic fallback)."""
    return db.get_submodel_elements(asset_id, "Skills")


register_submodel(SubmodelToolset(
    idShort="Skills",
    semantic_id="https://admin-shell.io/idta/Submodel/Skills/1/0",
    description="Fähigkeiten einer Ressource (IDTA Skills)",
    tools={
        "get_skills": get_skills,
        "get_properties": get_properties,
    },
))
