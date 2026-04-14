"""Neo4j tools for the MachineScheduleLog submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "MachineScheduleLog"


def get_schedule_log(asset_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return historical schedule entries from MachineScheduleLog."""
    return list_children_by_parent(asset_id, SUBMODEL, "Schedule", limit=limit)


def get_last_update_log(asset_id: str) -> list[dict[str, Any]]:
    """Return LastTimeUpdated from MachineScheduleLog."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL, limit=10, id_short="LastTimeUpdated")


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all MachineScheduleLog elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/MachineScheduleLog/1/0",
    description="Historische Maschinenplanung und Zeitstempel",
    tools={
        "get_schedule_log": get_schedule_log,
        "list_log_entries": get_schedule_log,
        "get_last_update_log": get_last_update_log,
        "get_properties": get_properties,
    },
))
