"""Neo4j tools for the StorageConfiguration submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "StorageConfiguration"


def list_storages(asset_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return configured storages from Storages container."""
    return list_children_by_parent(asset_id, SUBMODEL, "Storages", limit=limit)


def list_slots(asset_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return slot definitions from Slots container."""
    return list_children_by_parent(asset_id, SUBMODEL, "Slots", limit=limit)


def get_demand_config(asset_id: str) -> list[dict[str, Any]]:
    """Return demand-related storage configuration."""
    return list_children_by_parent(asset_id, SUBMODEL, "DemandConfig", limit=80)


def get_projection_config(asset_id: str) -> list[dict[str, Any]]:
    """Return projection-related storage configuration."""
    return list_children_by_parent(asset_id, SUBMODEL, "ProjectionConfig", limit=80)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all StorageConfiguration elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/StorageConfiguration/1/0",
    description="Lagerkonfiguration: Storages, Slots, Demand/Projection",
    tools={
        "list_storages": list_storages,
        "list_slots": list_slots,
        "get_demand_config": get_demand_config,
        "get_projection_config": get_projection_config,
        "get_properties": get_properties,
    },
))
