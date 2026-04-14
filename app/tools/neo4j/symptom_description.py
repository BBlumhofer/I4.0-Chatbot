"""Neo4j tools for the SymptomDescription submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "SymptomDescription"


def list_symptoms(asset_id: str, limit: int = 120) -> list[dict[str, Any]]:
    """Return symptoms grouped under SymptomSet."""
    return list_children_by_parent(asset_id, SUBMODEL, "SymptomSet", limit=limit)


def get_symptom_by_id_short(asset_id: str, symptom_id_short: str) -> list[dict[str, Any]]:
    """Return one symptom element by idShort."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL, limit=80, id_short=symptom_id_short)


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all SymptomDescription elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/SymptomDescription/1/0",
    description="Symptombeschreibung und Symptomgruppen",
    tools={
        "list_symptoms": list_symptoms,
        "get_symptom_by_id_short": get_symptom_by_id_short,
        "get_properties": get_properties,
    },
))
