"""
Neo4j tools for the **OfferedCapabilityDescription** submodel.

Covers: capability sets and grouped capability properties.
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


def _all_elements(asset_id: str) -> list[dict[str, Any]]:
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'OfferedCapabilityDescription'}})
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


def list_capability_sets(asset_id: str) -> list[dict[str, Any]]:
    """Return capability set containers."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'OfferedCapabilityDescription'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el)
    WHERE el.idShort = 'CapabilitySet'
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def list_capabilities(asset_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return capabilities under CapabilitySet (consolidated view)."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'OfferedCapabilityDescription'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(capset {{idShort: 'CapabilitySet'}})
    MATCH (capset)-[:HAS_ELEMENT]->(cap)
    RETURN cap.idShort AS idShort,
           cap.value AS value,
           cap.valueType AS valueType,
           labels(cap) AS elementTypes,
           capset.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(cypher, {"asset_id": asset_id, "limit": limit})


def get_capability_by_id_short(asset_id: str, capability_id_short: str) -> list[dict[str, Any]]:
    """Return one capability by idShort."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'OfferedCapabilityDescription'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el {{idShort: $capability_id_short}})
    OPTIONAL MATCH (parent)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    """
    return db.run_query(cypher, {"asset_id": asset_id, "capability_id_short": capability_id_short})


def list_properties_by_container(asset_id: str, container_id_short: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return direct properties of a container node."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'OfferedCapabilityDescription'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(container {{idShort: $container_id_short}})
    MATCH (container)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           container.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(
        cypher,
        {
            "asset_id": asset_id,
            "container_id_short": container_id_short,
            "limit": limit,
        },
    )


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all OfferedCapabilityDescription elements."""
    return _all_elements(asset_id)


register_submodel(SubmodelToolset(
    idShort="OfferedCapabilityDescription",
    semantic_id="https://admin-shell.io/idta/Submodel/OfferedCapabilityDescription/1/0",
    description="Angebotene Fahigkeiten inklusive CapabilitySet und PropertySet",
    tools={
        "list_capability_sets": list_capability_sets,
        "list_capabilities": list_capabilities,
        "get_capability_by_id_short": get_capability_by_id_short,
        "list_properties_by_container": list_properties_by_container,
        "get_properties": get_properties,
    },
))
