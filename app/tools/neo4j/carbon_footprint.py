"""Neo4j tools for the CarbonFootprint submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "CarbonFootprint"


def get_footprint_overview(asset_id: str) -> list[dict[str, Any]]:
    """Return footprint entries grouped by common lifecycle phases."""
    rows: list[dict[str, Any]] = []
    for parent in ("ProductCarbonFootprint_A1A3", "ProductCarbonFootprint_A4", "ProductCarbonFootprint_B5"):
        rows.extend(list_children_by_parent(asset_id, SUBMODEL, parent, limit=80))
    return rows


def get_goods_address_handover(asset_id: str) -> list[dict[str, Any]]:
    """Return handover location data used in carbon footprint context."""
    return list_children_by_parent(asset_id, SUBMODEL, "PCFGoodsAddressHandover", limit=120)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all CarbonFootprint elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/CarbonFootprint/1/0",
    description="CO2-Fusabdruck nach Lebenszyklusphasen",
    tools={
        "get_footprint_overview": get_footprint_overview,
        "get_goods_address_handover": get_goods_address_handover,
        "get_properties": get_properties,
    },
))
