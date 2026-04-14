"""Neo4j tools for the RequiredCapabilityDescription submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "RequiredCapabilityDescription"


def list_required_capabilities(asset_id: str, limit: int = 120) -> list[dict[str, Any]]:
    """Return capabilities required by the asset/process."""
    return list_children_by_parent(asset_id, SUBMODEL, "CapabilitySet", limit=limit)


def list_required_property_sets(asset_id: str, limit: int = 120) -> list[dict[str, Any]]:
    """Return requirement properties from PropertySet."""
    return list_children_by_parent(asset_id, SUBMODEL, "PropertySet", limit=limit)


def get_required_capability_by_id_short(asset_id: str, capability_id_short: str) -> list[dict[str, Any]]:
    """Return one required capability by idShort."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL, limit=80, id_short=capability_id_short)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all RequiredCapabilityDescription elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/RequiredCapabilityDescription/1/0",
    description="Benotigte Fahigkeiten und Eigenschaftsanforderungen",
    tools={
        "list_required_capabilities": list_required_capabilities,
        "list_required_property_sets": list_required_property_sets,
        "get_required_capability_by_id_short": get_required_capability_by_id_short,
        "get_properties": get_properties,
    },
))
