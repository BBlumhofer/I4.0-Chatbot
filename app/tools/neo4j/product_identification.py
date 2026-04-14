"""Neo4j tools for the ProductIdentification submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "ProductIdentification"


def get_product_identification(asset_id: str) -> list[dict[str, Any]]:
    """Return product identification related fields."""
    return list_children_by_parent(asset_id, SUBMODEL, "ProductIdentification", limit=150)


def get_additional_information(asset_id: str) -> list[dict[str, Any]]:
    """Return additional product information fields."""
    return list_children_by_parent(asset_id, SUBMODEL, "AdditionalInformation", limit=100)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all ProductIdentification elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/ProductIdentification/1/0",
    description="Produktidentifikation und Zusatzinformationen",
    tools={
        "get_product_identification": get_product_identification,
        "get_additional_information": get_additional_information,
        "get_properties": get_properties,
    },
))
