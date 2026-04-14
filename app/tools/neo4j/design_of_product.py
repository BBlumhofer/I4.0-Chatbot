"""Neo4j tools for the DesignOfProduct submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "DesignOfProduct"


def get_design_overview(asset_id: str) -> list[dict[str, Any]]:
    """Return compact design model information from Design_V01."""
    return list_children_by_parent(asset_id, SUBMODEL, "Design_V01", limit=120)


def get_author_info(asset_id: str) -> list[dict[str, Any]]:
    """Return author/contact details for design data."""
    return list_children_by_parent(asset_id, SUBMODEL, "Author", limit=50)


def get_model_descriptor(asset_id: str) -> list[dict[str, Any]]:
    """Return common model descriptor fields from design data."""
    rows = list_children_by_parent(asset_id, SUBMODEL, "Design_V01", limit=200)
    wanted = {
        "ModelName",
        "ModelType",
        "ModelDescription",
        "ModelFileVersion",
        "ApplicationName",
        "ApplicationSource",
    }
    return [row for row in rows if row.get("idShort") in wanted]


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all DesignOfProduct elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/DesignOfProduct/1/0",
    description="Konstruktionsdaten: Modellinfos, Versionen, Autor",
    tools={
        "get_design_overview": get_design_overview,
        "get_author_info": get_author_info,
        "get_model_descriptor": get_model_descriptor,
        "get_properties": get_properties,
    },
))
