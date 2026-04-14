"""
Neo4j tools for the **ProductionPlan** submodel.

Covers: production steps, step durations, completion status.
Semantic ID: https://admin-shell.io/idta/Submodel/ProductionPlan/1/0
"""
from __future__ import annotations

from typing import Any, Optional

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import asset_match_clause


def get_steps(asset_id: str) -> list[dict[str, Any]]:
    """Return all production steps for an asset, ordered by execution sequence."""
    cypher = """
        MATCH (a:Asset)
        """ + asset_match_clause() + """
        WITH a LIMIT 1
        MATCH (a)<-[:DESCRIBES_ASSET]-(s:Shell)
            -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
            -[:HAS_ELEMENT]->(step)
    OPTIONAL MATCH (step)-[:HAS_ELEMENT*0..2]->(status_prop:Property)
    WHERE toLower(status_prop.idShort) = 'status'
    OPTIONAL MATCH (step)-[:HAS_ELEMENT*0..2]->(duration_prop:Property)
    WHERE toLower(duration_prop.idShort) = 'duration'
    OPTIONAL MATCH (step)-[:HAS_ELEMENT*0..2]->(order_prop:Property)
    WHERE toLower(order_prop.idShort) IN ['order', 'sequence']
    WITH step,
      head(collect(status_prop.value)) AS status,
      head(collect(duration_prop.value)) AS duration,
      head(collect(order_prop.value)) AS step_order
    RETURN step.idShort AS step, step.value AS value,
        status AS status, duration AS duration
    ORDER BY coalesce(toIntegerOrNull(step_order), 999999), step.idShort
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_step_duration(asset_id: str, step: str) -> Optional[dict[str, Any]]:
    """Return duration and status of a specific production step."""
    cypher = """
        MATCH (a:Asset)
        """ + asset_match_clause() + """
        WITH a LIMIT 1
        MATCH (a)<-[:DESCRIBES_ASSET]-(s:Shell)
            -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
            -[:HAS_ELEMENT]->(step_node {idShort: $step})
    OPTIONAL MATCH (step_node)-[:HAS_ELEMENT*0..2]->(status_prop:Property)
    WHERE toLower(status_prop.idShort) = 'status'
    OPTIONAL MATCH (step_node)-[:HAS_ELEMENT*0..2]->(duration_prop:Property)
    WHERE toLower(duration_prop.idShort) = 'duration'
    WITH step_node,
       head(collect(duration_prop.value)) AS duration,
       head(collect(status_prop.value)) AS status
    RETURN step_node.idShort AS step, duration AS duration, status AS status
    """
    rows = db.run_query(cypher, {"asset_id": asset_id, "step": step})
    return rows[0] if rows else None


def is_finished(asset_id: str) -> bool:
    """Return True if all production steps are completed."""
    cypher = """
        MATCH (a:Asset)
        """ + asset_match_clause() + """
        WITH a LIMIT 1
        MATCH (a)<-[:DESCRIBES_ASSET]-(s:Shell)
            -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
            -[:HAS_ELEMENT]->(step)
    OPTIONAL MATCH (step)-[:HAS_ELEMENT*0..2]->(status_prop:Property)
    WHERE toLower(status_prop.idShort) = 'status'
    WITH step, head(collect(status_prop.value)) AS status
    WHERE toLower(coalesce(status, '')) <> 'done'
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
