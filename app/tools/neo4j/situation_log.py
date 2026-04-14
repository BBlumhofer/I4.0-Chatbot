"""Neo4j tools for the SituationLog submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "SituationLog"


def list_situations(asset_id: str, limit: int = 150) -> list[dict[str, Any]]:
    """Return entries from the SituationSet container."""
    return list_children_by_parent(asset_id, SUBMODEL, "SituationSet", limit=limit)


def get_situation_by_id_short(asset_id: str, situation_id_short: str) -> list[dict[str, Any]]:
    """Return a specific situation element by idShort."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL, limit=50, id_short=situation_id_short)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all SituationLog elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/SituationLog/1/0",
    description="Situationsprotokoll und Ereigniseintrage",
    tools={
        "list_situations": list_situations,
        "get_situation_by_id_short": get_situation_by_id_short,
        "get_properties": get_properties,
    },
))
