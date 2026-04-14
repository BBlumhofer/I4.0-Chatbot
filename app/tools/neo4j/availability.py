"""
Neo4j tools for the **Availability** submodel.

Covers: machine state and unavailability blocks/events.
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


def _availability_elements(asset_id: str) -> list[dict[str, Any]]:
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'Availability'}})
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


def get_machine_state(asset_id: str) -> list[dict[str, Any]]:
    """Return current machine state from Availability."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'Availability'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el:Property {{idShort: 'MachineState'}})
    OPTIONAL MATCH (parent)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    LIMIT 1
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def list_unavailability_blocks(asset_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return grouped unavailability blocks with their key attributes."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'Availability'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(blocks {{idShort: 'UnavailabilityBlocks'}})
    MATCH (blocks)-[:HAS_ELEMENT]->(block)
    OPTIONAL MATCH (block)-[:HAS_ELEMENT*0..2]->(el:Property)
    WHERE el.idShort IN ['Start', 'End', 'Reason', 'Type']
    WITH id(block) AS blockId,
         collect({
           idShort: el.idShort,
           value: el.value,
           valueType: el.valueType,
           elementTypes: labels(el)
         }) AS attributes
    RETURN blockId, attributes
    LIMIT $limit
    """
    return db.run_query(cypher, {"asset_id": asset_id, "limit": limit})


def list_unavailability_reasons(asset_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return reason entries from unavailability blocks."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'Availability'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(blocks {{idShort: 'UnavailabilityBlocks'}})
    MATCH (blocks)-[:HAS_ELEMENT]->(block)
    MATCH (block)-[:HAS_ELEMENT*0..2]->(el:Property {{idShort: 'Reason'}})
    RETURN id(block) AS blockId,
           el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes
    LIMIT $limit
    """
    return db.run_query(cypher, {"asset_id": asset_id, "limit": limit})


def get_availability_overview(asset_id: str, limit: int = 10) -> dict[str, Any]:
    """Return compact availability overview for chatbot answers."""
    return {
        "machine_state": get_machine_state(asset_id),
        "unavailability_blocks": list_unavailability_blocks(asset_id, limit=limit),
    }


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all Availability elements in flattened form."""
    return _availability_elements(asset_id)


register_submodel(SubmodelToolset(
    idShort="Availability",
    semantic_id="https://admin-shell.io/idta/Submodel/Availability/1/0",
    description="Verfugbarkeit: Maschinenzustand und Unverfugbarkeitsblocke",
    tools={
        "get_machine_state": get_machine_state,
        "list_unavailability_blocks": list_unavailability_blocks,
        "list_unavailability_reasons": list_unavailability_reasons,
        "get_availability_overview": get_availability_overview,
        "get_properties": get_properties,
    },
))
