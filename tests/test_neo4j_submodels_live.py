"""
Live integration tests against a real Neo4j instance.

These tests intentionally call the real database and should be run only when
network access and credentials are available.
"""
from __future__ import annotations

import os
from typing import Any

import pytest
from neo4j import GraphDatabase

from app.services import neo4j_service as neo4j_svc
from app.tools.neo4j import SUBMODEL_REGISTRY


NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://database.neo4j.phuket.plant.smartfactory.de:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "testtest")


@pytest.fixture(scope="module", autouse=True)
def _inject_live_driver_for_tool_calls():
    """Ensure app.service queries use the same live credentials as this test."""
    neo4j_svc.close_driver()
    neo4j_svc._driver = GraphDatabase.driver(  # type: ignore[attr-defined]
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )
    try:
        yield
    finally:
        neo4j_svc.close_driver()


def _asset_candidates_from_db(limit: int = 20) -> list[str]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            rows = session.run(
                """
                MATCH (a:Asset)
                WITH coalesce(a.id, a.shell_id, a.globalAssetId, a.idShort) AS asset_id
                WHERE asset_id IS NOT NULL
                RETURN asset_id
                LIMIT $limit
                """,
                {"limit": limit},
            )
            return [r["asset_id"] for r in rows if r.get("asset_id")]
    finally:
        driver.close()


def _available_submodels_for_asset(asset_id: str) -> set[str]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            rows = session.run(
                """
                MATCH (a:Asset)
                WHERE toLower(coalesce(a.id, '')) = toLower($asset_id)
                   OR toLower(coalesce(a.shell_id, '')) = toLower($asset_id)
                   OR toLower(coalesce(a.idShort, '')) = toLower($asset_id)
                   OR toLower(coalesce(a.globalAssetId, '')) = toLower($asset_id)
                MATCH (a)<-[:DESCRIBES_ASSET]-(:Shell)-[:HAS_SUBMODEL]->(sm:Submodel)
                RETURN sm.idShort AS idShort
                """,
                {"asset_id": asset_id},
            )
            return {r["idShort"] for r in rows if r.get("idShort")}
    finally:
        driver.close()


def _safe_call_get_properties(submodel: str, asset_id: str) -> list[dict[str, Any]]:
    tool = SUBMODEL_REGISTRY[submodel]["tools"]["get_properties"]
    result = tool(asset_id)
    assert isinstance(result, list), f"{submodel}.get_properties must return list"
    return result


@pytest.fixture(scope="module")
def live_asset_id() -> str:
    assets = _asset_candidates_from_db(limit=50)
    assert assets, "No assets returned from live Neo4j"
    return assets[0]


def test_live_neo4j_connectivity():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
    finally:
        driver.close()


def test_live_get_properties_for_available_submodels(live_asset_id: str):
    present = _available_submodels_for_asset(live_asset_id)
    assert present, f"Asset {live_asset_id} has no submodels in Neo4j"

    tested = 0
    failures: list[str] = []

    for submodel in sorted(present):
        if submodel not in SUBMODEL_REGISTRY:
            continue
        try:
            _safe_call_get_properties(submodel, live_asset_id)
            tested += 1
        except Exception as exc:  # noqa: BLE001 - we want full surface coverage
            failures.append(f"{submodel}: {type(exc).__name__}: {exc}")

    assert tested > 0, (
        f"No matching registered submodels found for asset {live_asset_id}. "
        f"Present in DB: {sorted(present)}"
    )
    assert not failures, "Live submodel get_properties failures:\n" + "\n".join(failures)


def test_live_targeted_queries_no_submodelelement_label(live_asset_id: str):
    # Regression guard for earlier schema mismatch in Structure/BOM paths.
    from app.tools.neo4j.structure import get_parts as structure_get_parts
    from app.tools.neo4j.bill_of_material import get_parts as bom_get_parts

    # These calls should not fail just because :SubmodelElement label is absent.
    # Empty list is acceptable when no data exists for that submodel.
    structure_result = structure_get_parts(live_asset_id)
    bom_result = bom_get_parts(live_asset_id)

    assert isinstance(structure_result, list)
    assert isinstance(bom_result, list)
