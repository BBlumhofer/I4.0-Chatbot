"""Shared query helpers for Neo4j submodel tools."""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db


def asset_match_clause() -> str:
    """Return a robust WHERE clause for common asset identifier variants."""
    return """
     WHERE toLower(coalesce(a.id, '')) = toLower($asset_id)
         OR toLower(coalesce(a.shell_id, '')) = toLower($asset_id)
         OR toLower(coalesce(a.idShort, '')) = toLower($asset_id)
         OR toLower(coalesce(a.globalAssetId, '')) = toLower($asset_id)
         OR toLower(coalesce(a.globalAssetId, '')) = toLower(replace($asset_id, '/asset/', '/assets/'))
         OR toLower(coalesce(a.globalAssetId, '')) = toLower(replace($asset_id, '/assets/', '/asset/'))
    """


def get_submodel_elements_recursive(
    asset_id: str,
    submodel_id_short: str,
    limit: int = 300,
    parent_id_short: str | None = None,
    id_short: str | None = None,
) -> list[dict[str, Any]]:
    """Return recursively traversed submodel elements with optional filters."""
    cypher = f"""
    MATCH (a:Asset)
    {asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: $submodel_id_short}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el)
    OPTIONAL MATCH (parent)-[:HAS_ELEMENT]->(el)
    WHERE ($parent_id_short IS NULL OR parent.idShort = $parent_id_short)
      AND ($id_short IS NULL OR el.idShort = $id_short)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(
        cypher,
        {
            "asset_id": asset_id,
            "submodel_id_short": submodel_id_short,
            "limit": limit,
            "parent_id_short": parent_id_short,
            "id_short": id_short,
        },
    )


def list_children_by_parent(
    asset_id: str,
    submodel_id_short: str,
    parent_id_short: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return direct children of a given parent idShort in a submodel."""
    cypher = f"""
    MATCH (a:Asset)
    {asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: $submodel_id_short}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(parent {{idShort: $parent_id_short}})
    MATCH (parent)-[:HAS_ELEMENT]->(el)
    RETURN el.idShort AS idShort,
           el.value AS value,
           el.valueType AS valueType,
           labels(el) AS elementTypes,
           parent.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(
        cypher,
        {
            "asset_id": asset_id,
            "submodel_id_short": submodel_id_short,
            "parent_id_short": parent_id_short,
            "limit": limit,
        },
    )
