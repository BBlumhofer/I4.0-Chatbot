"""Neo4j tools for the BillOfApplications submodel."""
from __future__ import annotations

from typing import Any

from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import get_submodel_elements_recursive, list_children_by_parent


SUBMODEL = "BillOfApplications"


def list_applications(asset_id: str, limit: int = 150) -> list[dict[str, Any]]:
    """Return application entries from BillOfApplications."""
    return list_children_by_parent(asset_id, SUBMODEL, "BillOfApplications", limit=limit)


def get_application_stack(asset_id: str) -> list[dict[str, Any]]:
    """Return common digital stack/application nodes."""
    rows: list[dict[str, Any]] = []
    for parent in ("DigitalProductionSystem", "SmartFactoryShellScape", "XitasoMnestix"):
        rows.extend(list_children_by_parent(asset_id, SUBMODEL, parent, limit=120))
    return rows


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all BillOfApplications elements."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/BillOfApplications/1/0",
    description="Anwendungslandschaft und digitaler Stack",
    tools={
        "list_applications": list_applications,
        "get_application_stack": get_application_stack,
        "get_properties": get_properties,
    },
))
