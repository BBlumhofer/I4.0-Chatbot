"""
Neo4j tools for the **ConditionMonitoring** submodel.

Covers: live and historical condition metrics, sensor readings.
Semantic ID: https://admin-shell.io/idta/Submodel/ConditionMonitoring/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import asset_match_clause


def get_condition_history(asset_id: str) -> list[dict[str, Any]]:
    """Return the most recent condition monitoring entries for an asset."""
    cypher = """
        MATCH (a:Asset)
        """ + asset_match_clause() + """
        WITH a LIMIT 1
        MATCH (a)<-[:DESCRIBES_ASSET]-(s:Shell)
            -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ConditionMonitoring'})
            -[:HAS_ELEMENT]->(entry)
    RETURN entry.idShort AS metric, entry.value AS value,
           entry.timestamp AS timestamp, entry.unit AS unit
    ORDER BY entry.timestamp DESC
    LIMIT 100
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all ConditionMonitoring submodel elements (generic fallback)."""
    return db.get_submodel_elements(asset_id, "ConditionMonitoring")


register_submodel(SubmodelToolset(
    idShort="ConditionMonitoring",
    semantic_id="https://admin-shell.io/idta/Submodel/ConditionMonitoring/1/0",
    description="Zustandsüberwachung: Messwerte, historische Verläufe",
    tools={
        "get_condition_history": get_condition_history,
        "get_properties": get_properties,
    },
))
