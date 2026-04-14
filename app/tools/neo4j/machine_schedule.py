"""
Neo4j tools for the **MachineSchedule** submodel.

Covers: open task state, schedule entries, and update timestamps.
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def _asset_match_clause() -> str:
    return """
    WHERE a.id = $asset_id
       OR a.globalAssetId = $asset_id
       OR a.globalAssetId = replace($asset_id, '/asset/', '/assets/')
       OR a.globalAssetId = replace($asset_id, '/assets/', '/asset/')
    """


def _schedule_elements(asset_id: str) -> list[dict[str, Any]]:
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'MachineSchedule'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el)
    OPTIONAL MATCH (parent)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_schedule(asset_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return schedule entries from Schedule list and nested elements."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'MachineSchedule'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(schedule {{idShort: 'Schedule'}})
    MATCH (schedule)-[:HAS_ELEMENT*0..]->(el)
    OPTIONAL MATCH (parent)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(cypher, {"asset_id": asset_id, "limit": limit})


def has_open_tasks(asset_id: str) -> bool:
    """Return True if MachineSchedule reports open tasks."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'MachineSchedule'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el:Property {{idShort: 'HasOpenTasks'}})
    RETURN toLower(coalesce(el.value, 'false')) IN ['true', '1', 'yes'] AS hasOpenTasks
    LIMIT 1
    """
    rows = db.run_query(cypher, {"asset_id": asset_id})
    return bool(rows[0]["hasOpenTasks"]) if rows else False


def get_last_update(asset_id: str) -> list[dict[str, Any]]:
    """Return LastTimeUpdated from MachineSchedule."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'MachineSchedule'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el {{idShort: 'LastTimeUpdated'}})
    OPTIONAL MATCH (parent)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    LIMIT 1
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all MachineSchedule elements."""
    return _schedule_elements(asset_id)


register_submodel(SubmodelToolset(
    idShort="MachineSchedule",
    semantic_id="https://admin-shell.io/idta/Submodel/MachineSchedule/1/0",
    description="Maschinenplanung: Schedule, offene Aufgaben, letzter Update-Zeitpunkt",
    tools={
        "get_schedule": get_schedule,
        "list_schedule_entries": get_schedule,
        "has_open_tasks": has_open_tasks,
        "get_last_update": get_last_update,
        "get_properties": get_properties,
    },
))
