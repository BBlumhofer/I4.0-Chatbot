"""
Neo4j service – thin wrapper around the official neo4j driver.

All graph queries are centralised here so that tools only need to call
high-level methods.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from neo4j import GraphDatabase, Driver

from app.config import settings

logger = logging.getLogger(__name__)

_driver: Optional[Driver] = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


# ── Generic helpers ────────────────────────────────────────────────────────────

def run_query(cypher: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Execute a read query and return rows as plain dicts."""
    with get_driver().session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def run_write(cypher: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Execute a write query inside an explicit write transaction."""
    with get_driver().session() as session:
        result = session.execute_write(
            lambda tx: list(tx.run(cypher, params or {}))
        )
        return [record.data() for record in result]


# ── Entity / Asset resolution ──────────────────────────────────────────────────

def find_asset_by_name(name: str) -> list[dict[str, Any]]:
    """
    Fuzzy-search for assets whose name contains *name* (case-insensitive).
    Returns a list of {id, name, type} dicts.
    """
    cypher = """
    MATCH (a:Asset)
    WHERE toLower(a.name) CONTAINS toLower($name)
       OR toLower(a.idShort) CONTAINS toLower($name)
    RETURN a.id AS id, a.name AS name, a.idShort AS idShort, a.type AS type
    LIMIT 10
    """
    return run_query(cypher, {"name": name})


def get_asset_shell(asset_id: str) -> Optional[dict[str, Any]]:
    """Return the AAS Shell that describes the given asset."""
    cypher = """
    MATCH (s:Shell)-[:DESCRIBES_ASSET]->(a:Asset {id: $asset_id})
    RETURN s.id AS id, s.idShort AS idShort
    """
    rows = run_query(cypher, {"asset_id": asset_id})
    return rows[0] if rows else None


def get_submodel_elements(asset_id: str, submodel_name: str) -> list[dict[str, Any]]:
    """
    Return all SubmodelElements of a given submodel for an asset.
    """
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: $submodel_name})
          -[:HAS_ELEMENT]->(el:SubmodelElement)
    RETURN el.idShort AS idShort, el.value AS value,
           el.valueType AS valueType, labels(el) AS elementTypes
    """
    return run_query(cypher, {"asset_id": asset_id, "submodel_name": submodel_name})
