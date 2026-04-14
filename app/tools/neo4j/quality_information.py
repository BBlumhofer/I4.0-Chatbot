"""Neo4j tools for the QualityInformation submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "QualityInformation"


def get_quality_information(asset_id: str, limit: int = 150) -> list[dict[str, Any]]:
    """Return core quality information entries."""
    return list_children_by_parent(asset_id, SUBMODEL, "QualityInformation", limit=limit)


def get_quality_by_id_short(asset_id: str, quality_id_short: str) -> list[dict[str, Any]]:
    """Return one quality element by idShort."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL, limit=80, id_short=quality_id_short)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all QualityInformation elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/QualityInformation/1/0",
    description="Qualitatsinformationen und Kennzahlen",
    tools={
        "get_quality_information": get_quality_information,
        "get_quality_by_id_short": get_quality_by_id_short,
        "get_properties": get_properties,
    },
))
