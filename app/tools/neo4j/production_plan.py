"""
Neo4j tools for the **ProductionPlan** submodel.

Covers: production steps, step durations, completion status.
Semantic ID: https://admin-shell.io/idta/Submodel/ProductionPlan/1/0
"""
from __future__ import annotations

from typing import Any, Optional

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_steps(asset_id: str) -> list[dict[str, Any]]:
    """Return all production steps for an asset, ordered by execution sequence."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
          -[:HAS_ELEMENT]->(step:SubmodelElement)
    RETURN step.idShort AS step, step.value AS value,
           step.status AS status, step.duration AS duration
    ORDER BY step.order
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_step_duration(asset_id: str, step: str) -> Optional[dict[str, Any]]:
    """Return duration and status of a specific production step."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
          -[:HAS_ELEMENT]->(step:SubmodelElement {idShort: $step})
    RETURN step.idShort AS step, step.duration AS duration, step.status AS status
    """
    rows = db.run_query(cypher, {"asset_id": asset_id, "step": step})
    return rows[0] if rows else None


def is_finished(asset_id: str) -> bool:
    """Return True if all production steps are completed."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
          -[:HAS_ELEMENT]->(step:SubmodelElement)
    WHERE step.status <> 'done'
    RETURN count(step) AS remaining
    """
    rows = db.run_query(cypher, {"asset_id": asset_id})
    return rows[0]["remaining"] == 0 if rows else False


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all ProductionPlan submodel elements (generic fallback)."""
    return db.get_submodel_elements(asset_id, "ProductionPlan")


register_submodel(SubmodelToolset(
    idShort="ProductionPlan",
    semantic_id="https://admin-shell.io/idta/Submodel/ProductionPlan/1/0",
    description="Produktionsschritte, Dauer, Status",
    tools={
        "get_steps": get_steps,
        "get_step_duration": get_step_duration,
        "is_finished": is_finished,
        "list_steps": get_steps,
        "check_done": is_finished,
        "get_properties": get_properties,
    },
))
