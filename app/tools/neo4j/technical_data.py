"""Neo4j tools for the TechnicalData submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "TechnicalData"


def get_general_information(asset_id: str) -> list[dict[str, Any]]:
    """Return GeneralInformation fields for technical data."""
    return list_children_by_parent(asset_id, SUBMODEL, "GeneralInformation", limit=120)


def get_further_information(asset_id: str) -> list[dict[str, Any]]:
    """Return FurtherInformation fields for technical data."""
    return list_children_by_parent(asset_id, SUBMODEL, "FurtherInformation", limit=120)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all TechnicalData elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/TechnicalData/1/0",
    description="Technische Daten und allgemeine Zusatzinfos",
    tools={
        "get_general_information": get_general_information,
        "get_further_information": get_further_information,
        "get_properties": get_properties,
    },
))
