"""
Neo4j tools for flexible exhibition insights.

These tools intentionally avoid hardcoded business Cypher templates.
You can provide the exact Cypher per question once available.
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def get_today_truck_production(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.get_today_truck_production(asset_id=asset_id, cypher=cypher, params=params)


def count_total_products(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.count_total_products(asset_id=asset_id, cypher=cypher, params=params)


def count_successfully_finished_products(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.count_successfully_finished_products(asset_id=asset_id, cypher=cypher, params=params)


def get_production_kpi_overview(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.get_production_kpi_overview(asset_id=asset_id, cypher=cypher, params=params)


def count_products_in_production(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.count_products_in_production(asset_id=asset_id, cypher=cypher, params=params)


def get_average_assembly_duration(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.get_average_assembly_duration(asset_id=asset_id, cypher=cypher, params=params)


def count_products_with_quality_check_step(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.count_products_with_quality_check_step(asset_id=asset_id, cypher=cypher, params=params)


def count_finished_products_last_24h(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.count_finished_products_last_24h(asset_id=asset_id, cypher=cypher, params=params)


def count_finished_products_last_7d(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.count_finished_products_last_7d(asset_id=asset_id, cypher=cypher, params=params)


def breakdown_products_by_type(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.breakdown_products_by_type(asset_id=asset_id, cypher=cypher, params=params)


def get_module_step_status_overview(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.get_module_step_status_overview(asset_id=asset_id, cypher=cypher, params=params)


def list_modules(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.list_modules_insight(asset_id=asset_id, cypher=cypher, params=params)


def list_active_agents(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.list_active_agents_insight(asset_id=asset_id, cypher=cypher, params=params)


def list_inventory_products(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return db.list_inventory_products_insight(asset_id=asset_id, cypher=cypher, params=params)


def get_properties(
    asset_id: str | None = None,
    cypher: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generic fallback for exhibition insight questions."""
    return get_today_truck_production(asset_id=asset_id, cypher=cypher, params=params)


register_submodel(SubmodelToolset(
    idShort="ExhibitionInsights",
    semantic_id="https://smartfactory.de/idta/Submodel/ExhibitionInsights/1/0",
    description="Flexible Messe-KPIs und Besucherfragen (query-getrieben)",
    tools={
        "get_today_truck_production": get_today_truck_production,
        "count_total_products": count_total_products,
        "count_successfully_finished_products": count_successfully_finished_products,
        "get_production_kpi_overview": get_production_kpi_overview,
        "count_products_in_production": count_products_in_production,
        "get_average_assembly_duration": get_average_assembly_duration,
        "count_products_with_quality_check_step": count_products_with_quality_check_step,
        "count_finished_products_last_24h": count_finished_products_last_24h,
        "count_finished_products_last_7d": count_finished_products_last_7d,
        "breakdown_products_by_type": breakdown_products_by_type,
        "get_module_step_status_overview": get_module_step_status_overview,
        "list_modules": list_modules,
        "list_active_agents": list_active_agents,
        "list_inventory_products": list_inventory_products,
        "get_properties": get_properties,
    },
))
