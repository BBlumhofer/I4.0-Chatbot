"""
Neo4j service – thin wrapper around the official neo4j driver.

All graph queries are centralised here so that tools only need to call
high-level methods.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from neo4j import GraphDatabase, Driver

from app.config import settings

logger = logging.getLogger(__name__)

_driver: Optional[Driver] = None


_RESOURCE_ALIASES_FILE = Path(__file__).resolve().parents[1] / "resources" / "resource_aliases.json"


_DEFAULT_RESOURCE_ALIAS_TO_CANONICAL: dict[str, str] = {
    "p17": "P17",
    "p17camodul": "P17",
    "camodul": "P17",
    "collaborativeassemblymodule": "P17",
    "handarbeitsmodul": "P17",
}


# Synonyme fuer Ressourcen-/Modulnamen (normalisierte Schreibweise -> kanonische ID).
# Beispiele: "ca-modul", "collaborative-assembly module" => "P17".
def _load_resource_aliases() -> dict[str, str]:
    try:
        with _RESOURCE_ALIASES_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object.")

        normalized_aliases: dict[str, str] = {}

        # Neues Schema:
        # {
        #   "resources": [
        #     {"canonical_id": "P17", "aliases": ["ca-modul", ...], "site": "X", "line": "Y"}
        #   ]
        # }
        resources = payload.get("resources")
        if isinstance(resources, list):
            for resource in resources:
                if not isinstance(resource, dict):
                    continue
                canonical_id = str(resource.get("canonical_id", "")).strip().upper()
                aliases = resource.get("aliases")
                if not canonical_id or not isinstance(aliases, list):
                    continue

                for alias in aliases:
                    alias_token = _normalize_alias_token(str(alias))
                    if alias_token:
                        normalized_aliases[alias_token] = canonical_id

        # Legacy-Schema (weiterhin unterstuetzt):
        # {"aliases": {"ca-modul": "P17"}}
        alias_map_raw = payload.get("aliases")
        if isinstance(alias_map_raw, dict):
            for alias, canonical in alias_map_raw.items():
                alias_token = _normalize_alias_token(str(alias))
                canonical_id = str(canonical).strip().upper()
                if alias_token and canonical_id:
                    normalized_aliases[alias_token] = canonical_id

        if normalized_aliases:
            return normalized_aliases

        raise ValueError("No valid aliases found in resource alias file.")
    except Exception as exc:
        logger.warning("Failed to load resource aliases from %s: %s", _RESOURCE_ALIASES_FILE, exc)

    return dict(_DEFAULT_RESOURCE_ALIAS_TO_CANONICAL)


def _normalize_alias_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())


_RESOURCE_ALIAS_TO_CANONICAL: dict[str, str] = _load_resource_aliases()


def _expand_asset_search_terms(name: str) -> tuple[list[str], list[str], list[str]]:
    """
    Erzeuge robuste Suchterme fuer Asset-Aufloesung.

    Liefert (contains_terms_lower, exact_terms_lower, canonical_ids_upper).
    """
    raw = (name or "").strip()
    if not raw:
        return [], [], []

    raw_terms: set[str] = {raw}
    canonical_ids: set[str] = set()

    normalized = _normalize_alias_token(raw)
    if normalized:
        raw_terms.add(normalized)

    alias_canonical = _RESOURCE_ALIAS_TO_CANONICAL.get(normalized)
    if alias_canonical:
        canonical_ids.add(alias_canonical)

    p_id_match = re.search(r"\bP\d+\b", raw, flags=re.IGNORECASE)
    if p_id_match:
        canonical_ids.add(p_id_match.group(0).upper())

    for canonical in canonical_ids:
        raw_terms.add(canonical)
        raw_terms.add(f"https://smartfactory.de/asset/{canonical}")

    # Nur aussagekraeftige Terme behalten.
    contains_terms = sorted({t.strip().lower() for t in raw_terms if t and t.strip()})
    exact_terms = sorted({t for t in contains_terms if len(t) >= 3})

    return contains_terms, exact_terms, sorted(canonical_ids)


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
    contains_terms, exact_terms, canonical_ids = _expand_asset_search_terms(name)
    if not contains_terms:
        return []

    cypher = """
    MATCH (a:Asset)
     WHERE any(term IN $contains_terms WHERE
            toLower(coalesce(a.name, '')) CONTAINS term
         OR toLower(coalesce(a.idShort, '')) CONTAINS term
         OR toLower(coalesce(a.shell_id, '')) CONTAINS term
         OR toLower(coalesce(a.globalAssetId, '')) CONTAINS term
         OR toLower(coalesce(a.id, '')) CONTAINS term
     )
     RETURN coalesce(a.id, a.globalAssetId, a.shell_id, a.idShort) AS id,
              a.name AS name,
              a.idShort AS idShort,
              coalesce(a.type, a.assetType) AS type,
              a.globalAssetId AS globalAssetId,
              a.shell_id AS shell_id,
              a.assetKind AS assetKind
     ORDER BY
        CASE
            WHEN any(term IN $exact_terms WHERE
                toLower(coalesce(a.id, '')) = term
                OR toLower(coalesce(a.globalAssetId, '')) = term
                OR toLower(coalesce(a.shell_id, '')) = term
                OR toLower(coalesce(a.idShort, '')) = term
            ) THEN 0
            WHEN any(canonical IN $canonical_ids WHERE
                toUpper(coalesce(a.idShort, '')) = canonical
                OR toUpper(coalesce(a.id, '')) ENDS WITH canonical
                OR toUpper(coalesce(a.globalAssetId, '')) ENDS WITH canonical
            ) THEN 1
            ELSE 2
        END
    LIMIT 10
    """
    return run_query(
        cypher,
        {
            "contains_terms": contains_terms,
            "exact_terms": exact_terms,
            "canonical_ids": canonical_ids,
        },
    )


def get_asset_overview(asset_id_or_hint: str) -> Optional[dict[str, Any]]:
     """
     Return a compact overview for an asset matched by ID/hint.

     Matching is robust across ``id``, ``idShort``, ``shell_id`` and
     ``globalAssetId`` so user hints like "P17" can be resolved to the
     canonical identifier.
     """
     cypher = """
     MATCH (a:Asset)
     WHERE toLower(coalesce(a.id, '')) = toLower($hint)
         OR toLower(coalesce(a.idShort, '')) = toLower($hint)
         OR toLower(coalesce(a.shell_id, '')) = toLower($hint)
         OR toLower(coalesce(a.globalAssetId, '')) = toLower($hint)
         OR toLower(coalesce(a.globalAssetId, '')) CONTAINS toLower($hint)
         OR toLower(coalesce(a.name, '')) CONTAINS toLower($hint)
     WITH a
     ORDER BY
        CASE
          WHEN toLower(coalesce(a.id, '')) = toLower($hint) THEN 0
          WHEN toLower(coalesce(a.shell_id, '')) = toLower($hint) THEN 1
          WHEN toLower(coalesce(a.idShort, '')) = toLower($hint) THEN 2
          WHEN toLower(coalesce(a.globalAssetId, '')) = toLower($hint) THEN 3
          WHEN toLower(coalesce(a.globalAssetId, '')) CONTAINS toLower($hint) THEN 4
          ELSE 5
        END
     LIMIT 1
     OPTIONAL MATCH (s:Shell)-[:DESCRIBES_ASSET]->(a)
     OPTIONAL MATCH (s)-[:HAS_SUBMODEL]->(sm:Submodel)
     RETURN coalesce(a.id, a.globalAssetId, a.shell_id, a.idShort) AS id,
              a.name AS name,
              a.idShort AS idShort,
              a.globalAssetId AS globalAssetId,
              a.shell_id AS shell_id,
              coalesce(a.type, a.assetType) AS type,
              a.assetKind AS assetKind,
              s.id AS shellId,
              collect(DISTINCT sm.idShort) AS submodels
     """
     rows = run_query(cypher, {"hint": asset_id_or_hint})
     return rows[0] if rows else None


def get_asset_shell(asset_id: str) -> Optional[dict[str, Any]]:
    """Return the AAS Shell that describes the given asset."""
    cypher = """
    MATCH (s:Shell)-[:DESCRIBES_ASSET]->(a:Asset)
    WHERE toLower(coalesce(a.id, '')) = toLower($asset_id)
       OR toLower(coalesce(a.globalAssetId, '')) = toLower($asset_id)
       OR toLower(coalesce(a.shell_id, '')) = toLower($asset_id)
       OR toLower(coalesce(a.idShort, '')) = toLower($asset_id)
    RETURN s.id AS id, s.idShort AS idShort
    """
    rows = run_query(cypher, {"asset_id": asset_id})
    return rows[0] if rows else None


def get_available_submodels_for_asset(asset_id: str) -> list[dict[str, Any]]:
    """
    Return all submodels linked via HAS_SUBMODEL to the shell of *asset_id*.

    Each row contains ``idShort`` and ``semanticId`` so the caller can match
    against the registered toolset by either field.
    """
    cypher = """
        MATCH (a:Asset)
        WHERE toLower(coalesce(a.id, '')) = toLower($asset_id)
         OR toLower(coalesce(a.globalAssetId, '')) = toLower($asset_id)
         OR toLower(coalesce(a.shell_id, '')) = toLower($asset_id)
         OR toLower(coalesce(a.idShort, '')) = toLower($asset_id)
        MATCH (a)<-[:DESCRIBES_ASSET]-(s:Shell)-[:HAS_SUBMODEL]->(sm:Submodel)
    RETURN sm.idShort AS idShort, sm.semanticId AS semanticId
    """
    return run_query(cypher, {"asset_id": asset_id})


def get_submodel_elements(asset_id: str, submodel_name: str) -> list[dict[str, Any]]:
    """
    Return all elements of a given submodel for an asset.

    Uses recursive HAS_ELEMENT traversal and does not enforce a concrete
    element label, because real datasets often use heterogeneous labels
    (Property, Entity, SubmodelElementCollection, ...).
    """
    cypher = """
        MATCH (a:Asset)
        WHERE toLower(coalesce(a.id, '')) = toLower($asset_id)
         OR toLower(coalesce(a.globalAssetId, '')) = toLower($asset_id)
         OR toLower(coalesce(a.shell_id, '')) = toLower($asset_id)
         OR toLower(coalesce(a.idShort, '')) = toLower($asset_id)
        MATCH (a)<-[:DESCRIBES_ASSET]-(s:Shell)
            -[:HAS_SUBMODEL]->(sm:Submodel {idShort: $submodel_name})
            -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(el)
    RETURN el.idShort AS idShort, el.value AS value,
           el.valueType AS valueType, labels(el) AS elementTypes
    """
    return run_query(cypher, {"asset_id": asset_id, "submodel_name": submodel_name})


def get_agent_connected_node_properties(
    shell_id: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """
    Return distinct properties of nodes reachable from Agent nodes.

    The primary query mirrors the APOC-based production query and removes the
    ``embedding`` field in Cypher. If APOC is not available, the function falls
    back to plain ``properties(n)`` and strips ``embedding`` in Python.
    """
    cypher_apoc = """
    MATCH (h:Agent)-[*]->(n)
    WHERE $shell_id IS NULL
       OR coalesce(n.shell_id, '') = $shell_id
       OR coalesce(n.id, '') = $shell_id
    WITH DISTINCT n
    RETURN apoc.map.removeKeys(properties(n), ['embedding']) AS nodeProps
    LIMIT $limit
    """

    params = {
        "shell_id": shell_id,
        "limit": limit,
    }

    try:
        return run_query(cypher_apoc, params)
    except Exception:
        cypher_fallback = """
        MATCH (h:Agent)-[*]->(n)
        WHERE $shell_id IS NULL
           OR coalesce(n.shell_id, '') = $shell_id
           OR coalesce(n.id, '') = $shell_id
        WITH DISTINCT n
        RETURN properties(n) AS nodeProps
        LIMIT $limit
        """
        rows = run_query(cypher_fallback, params)
        sanitized: list[dict[str, Any]] = []
        for row in rows:
            props = dict(row.get("nodeProps") or {})
            props.pop("embedding", None)
            sanitized.append({"nodeProps": props})
        return sanitized


def _needs_query_placeholder(question: str, query_name: str) -> list[dict[str, Any]]:
    """Return a structured placeholder until a production Cypher is provided."""
    return [{
        "status": "needs_query",
        "query_name": query_name,
        "question": question,
        "hint": "Bitte hinterlege eine Neo4j-Cypher fuer diese Kennzahl oder uebergib sie direkt als 'cypher'.",
    }]


def get_today_truck_production(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Flexible insight: number of trucks produced today."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType: 'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId: 'ProductionPlan'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(isfinished:Property {idShort: 'IsFinished'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(step:SubmodelElementCollection)
        WHERE step.idShort STARTS WITH 'Step'
        WITH n, isfinished, step, toInteger(replace(step.idShort, 'Step', '')) AS step_num
        ORDER BY n.globalAssetId, step_num DESC
        WITH n, isfinished, collect(step)[0] AS last_step
        OPTIONAL MATCH (last_step)-[:HAS_ELEMENT]->(:SubmodelElementCollection {idShort: 'Scheduling'})-[:HAS_ELEMENT]->(endtime:Property {idShort: 'EndDateTime'})
        WITH n,
             toLower(trim(coalesce(toString(isfinished.value), ''))) AS finished_value,
             toString(coalesce(endtime.value, '')) AS end_value,
             toString(date()) AS today
        WHERE finished_value IN ['true', '1', 'yes']
          AND end_value STARTS WITH today
        RETURN count(DISTINCT n) AS produced_today,
               collect(DISTINCT n.globalAssetId)[0..20] AS sample_product_ids
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def count_total_products(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: total/finished/unfinished product counts."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType: 'product'})
        OPTIONAL MATCH (n)<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(:Submodel {semanticId: 'ProductionPlan'})-[:HAS_ELEMENT]->(f:Property {idShort: 'IsFinished'})
        WITH n, toLower(trim(coalesce(toString(f.value), ''))) AS finished_value
        RETURN count(DISTINCT n) AS products_total,
               sum(CASE WHEN finished_value IN ['true','1','yes'] THEN 1 ELSE 0 END) AS products_finished_successfully,
               (count(DISTINCT n) - sum(CASE WHEN finished_value IN ['true','1','yes'] THEN 1 ELSE 0 END)) AS products_unfinished
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def count_successfully_finished_products(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: products with ProductionPlan.IsFinished = true."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType: 'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId: 'ProductionPlan'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(isfinished:Property {idShort: 'IsFinished'})
        WITH n, toLower(trim(coalesce(toString(isfinished.value), ''))) AS finished_value
        WHERE finished_value IN ['true', '1', 'yes']
        RETURN count(DISTINCT n) AS products_finished_successfully,
               collect(DISTINCT n.globalAssetId)[0..20] AS sample_product_ids
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def get_production_kpi_overview(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: total/finished/unfinished/in-production product KPIs."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType: 'product'})
        WITH collect(DISTINCT n) AS products

        CALL {
          WITH products
          UNWIND products AS p
          OPTIONAL MATCH (p)<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId: 'ProductionPlan'})-[:HAS_ELEMENT]->(f:Property {idShort: 'IsFinished'})
          WITH p, toLower(trim(coalesce(toString(f.value), ''))) AS fv
          RETURN count(DISTINCT p) AS total,
                 sum(CASE WHEN fv IN ['true','1','yes'] THEN 1 ELSE 0 END) AS finished
        }

        CALL {
          WITH products
          UNWIND products AS p
          OPTIONAL MATCH (p)<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId: 'ProductionPlan'})-[:HAS_ELEMENT]->(step:SubmodelElementCollection)-[:HAS_ELEMENT]->(st:Property {idShort:'Status'})
          WHERE step.idShort STARTS WITH 'Step'
          WITH p, collect(toLower(trim(coalesce(toString(st.value), '')))) AS statuses
          OPTIONAL MATCH (p)<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(:Submodel {semanticId: 'ProductionPlan'})-[:HAS_ELEMENT]->(f2:Property {idShort: 'IsFinished'})
          WITH p, statuses, toLower(trim(coalesce(toString(f2.value), ''))) AS fv
          RETURN sum(CASE
            WHEN fv IN ['true','1','yes'] THEN 0
            WHEN any(s IN statuses WHERE s IN ['open','planned','running','executing']) THEN 1
            ELSE 0
          END) AS in_production
        }

        RETURN total AS products_total,
               finished AS products_finished_successfully,
               (total - finished) AS products_unfinished,
               in_production AS products_in_production
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def count_products_in_production(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: products currently in production (open/planned/running/executing step, not finished)."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType: 'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId: 'ProductionPlan'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(f:Property {idShort: 'IsFinished'})
        WITH n, sm, toLower(trim(coalesce(toString(f.value), ''))) AS finished_value
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(step:SubmodelElementCollection)-[:HAS_ELEMENT]->(st:Property {idShort:'Status'})
        WHERE step.idShort STARTS WITH 'Step'
        WITH n, finished_value, collect(toLower(trim(coalesce(toString(st.value), '')))) AS statuses
                WHERE NOT finished_value IN ['true','1','yes']
          AND any(s IN statuses WHERE s IN ['open','planned','running','executing'])
        RETURN count(DISTINCT n) AS products_in_production,
               collect(DISTINCT n.globalAssetId)[0..20] AS sample_product_ids
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def get_average_assembly_duration(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: average duration (minutes) for assembly-like steps."""
    if not cypher:
        cypher = """
        MATCH (:Asset {assetType:'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(:Submodel {semanticId:'ProductionPlan'})-[:HAS_ELEMENT]->(step:SubmodelElementCollection)
        WHERE step.idShort STARTS WITH 'Step'
        MATCH (step)-[:HAS_ELEMENT]->(title:Property {idShort:'StepTitle'})
        MATCH (step)-[:HAS_ELEMENT]->(sched:SubmodelElementCollection {idShort:'Scheduling'})-[:HAS_ELEMENT]->(startp:Property {idShort:'StartDateTime'})
        MATCH (sched)-[:HAS_ELEMENT]->(endp:Property {idShort:'EndDateTime'})
        OPTIONAL MATCH (step)-[:HAS_ELEMENT]->(statusp:Property {idShort:'Status'})
        WITH toLower(coalesce(toString(title.value), '')) AS title,
             toLower(coalesce(toString(statusp.value), '')) AS status,
             datetime(replace(toString(startp.value), ' ', 'T')) AS start_dt,
             datetime(replace(toString(endp.value), ' ', 'T')) AS end_dt
        WHERE (title CONTAINS 'assemble' OR title CONTAINS 'montage')
          AND status = 'done'
          AND end_dt >= start_dt
        WITH duration.inSeconds(start_dt, end_dt).seconds AS dur_seconds
        RETURN round(avg(toFloat(dur_seconds) / 60.0), 2) AS avg_assembly_duration_minutes,
               count(*) AS sample_steps
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def count_products_with_quality_check_step(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: how many products contain a quality-check step."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType:'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(:Submodel {semanticId:'ProductionPlan'})-[:HAS_ELEMENT]->(step:SubmodelElementCollection)-[:HAS_ELEMENT]->(title:Property {idShort:'StepTitle'})
        WHERE step.idShort STARTS WITH 'Step'
          AND toLower(coalesce(toString(title.value), '')) IN ['qualitycontrol', 'qc', 'quality check']
         WITH size(collect(DISTINCT n)) AS qc_count
        MATCH (allp:Asset {assetType:'product'})
        RETURN count(DISTINCT allp) AS products_total,
             qc_count AS products_with_quality_check_step,
             (count(DISTINCT allp) - qc_count) AS products_without_quality_check_step
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def count_finished_products_last_24h(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: number of products finished in the last 24 hours."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType:'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId:'ProductionPlan'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(isfinished:Property {idShort:'IsFinished'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(step:SubmodelElementCollection)-[:HAS_ELEMENT]->(:SubmodelElementCollection {idShort:'Scheduling'})-[:HAS_ELEMENT]->(endtime:Property {idShort:'EndDateTime'})
        WHERE step.idShort STARTS WITH 'Step'
        WITH n,
             toLower(trim(coalesce(toString(isfinished.value), ''))) AS finished_value,
             datetime(replace(toString(coalesce(endtime.value, '1970-01-01 00:00:00')), ' ', 'T')) AS end_dt
        WHERE finished_value IN ['true','1','yes']
          AND end_dt >= datetime() - duration('P1D')
        RETURN count(DISTINCT n) AS products_finished_last_24h,
               collect(DISTINCT n.globalAssetId)[0..20] AS sample_product_ids
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def count_finished_products_last_7d(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: number of products finished in the last 7 days."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType:'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel {semanticId:'ProductionPlan'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(isfinished:Property {idShort:'IsFinished'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(step:SubmodelElementCollection)-[:HAS_ELEMENT]->(:SubmodelElementCollection {idShort:'Scheduling'})-[:HAS_ELEMENT]->(endtime:Property {idShort:'EndDateTime'})
        WHERE step.idShort STARTS WITH 'Step'
        WITH n,
             toLower(trim(coalesce(toString(isfinished.value), ''))) AS finished_value,
             datetime(replace(toString(coalesce(endtime.value, '1970-01-01 00:00:00')), ' ', 'T')) AS end_dt
        WHERE finished_value IN ['true','1','yes']
          AND end_dt >= datetime() - duration('P7D')
        RETURN count(DISTINCT n) AS products_finished_last_7d,
               collect(DISTINCT n.globalAssetId)[0..20] AS sample_product_ids
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def breakdown_products_by_type(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: product count grouped by ProductIdentification type fields."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType:'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel)
        WHERE sm.semanticId = 'ProductIdentification' OR sm.idShort = 'ProductIdentification'
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(name_p:Property {idShort:'ProductName'})
        OPTIONAL MATCH (sm)-[:HAS_ELEMENT]->(fam_p:Property {idShort:'ProductFamilyName'})
        WITH coalesce(toString(name_p.value), toString(fam_p.value), 'unknown') AS product_type, n
        RETURN product_type, count(DISTINCT n) AS products_count
        ORDER BY products_count DESC, product_type
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def get_module_step_status_overview(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Insight: status distribution of production steps per station/module."""
    if not cypher:
        cypher = """
        MATCH (:Asset {assetType:'product'})<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(:Submodel {semanticId:'ProductionPlan'})-[:HAS_ELEMENT]->(step:SubmodelElementCollection)
        WHERE step.idShort STARTS WITH 'Step'
        OPTIONAL MATCH (step)-[:HAS_ELEMENT]->(station:Property {idShort:'Station'})
        OPTIONAL MATCH (step)-[:HAS_ELEMENT]->(status:Property {idShort:'Status'})
        WITH coalesce(toString(station.value), 'unknown') AS module_station,
             toLower(coalesce(toString(status.value), 'unknown')) AS step_status,
             count(*) AS c
        RETURN module_station, step_status, c AS step_count
        ORDER BY module_station, step_status
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def list_modules_insight(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Flexible insight: list available modules."""
    if not cypher:
        cypher = """
        MATCH (n:Asset)
        WHERE coalesce(n.assetType, '') = 'Resource'
           OR coalesce(n.assetKind, '') = 'Instance'
        RETURN DISTINCT coalesce(n.idShort, n.globalAssetId, n.identificationId) AS module
        ORDER BY module
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def list_active_agents_insight(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Flexible insight: list currently active/running agents."""
    if not cypher:
        cypher = """
        MATCH (a:Agent)
        WHERE toLower(trim(coalesce(toString(a.state), ''))) IN ['running', 'active']
        RETURN coalesce(a.id, a.shell_id, a.name) AS agent_id,
               coalesce(a.state, 'unknown') AS state
        ORDER BY agent_id
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)


def list_inventory_products_insight(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Flexible insight: products currently available in stock."""
    if not cypher:
        cypher = """
        MATCH (n:Asset {assetType: 'product'})
        RETURN coalesce(n.globalAssetId, n.idShort, n.identificationId) AS product_id,
               coalesce(n.idShort, '') AS id_short,
               coalesce(n.productType, '') AS product_type
        ORDER BY product_id
        LIMIT 200
        """
    payload = dict(params or {})
    if asset_id and "asset_id" not in payload:
        payload["asset_id"] = asset_id
    return run_query(cypher, payload)
