"""
app.tools.neo4j – per-submodel Neo4j toolsets.

This package exposes:
  SUBMODEL_REGISTRY  – dict[str, dict] compatible with the graph nodes
  VALID_SUBMODELS    – set of valid submodel idShort strings
  get_available_submodels(asset_id)  – list of submodel idShorts actually
                                       present on an asset's shell in Neo4j

To add a new submodel:
  1. Create app/tools/neo4j/my_submodel.py following the pattern in _base.py
  2. Import it here (one line)
  That's it – registration and SUBMODEL_REGISTRY are updated automatically.
"""
from __future__ import annotations

import logging
from typing import Any

# ── Import each submodel module to trigger registration ───────────────────────
# Add one import here when creating a new submodel file.
from app.tools.neo4j import (  # noqa: F401
    agents,
    exhibition_insights,
    production_plan,
    bill_of_material,
    bill_of_applications,
    structure,
    availability,
    machine_schedule,
    machine_schedule_log,
    design_of_product,
    situation_log,
    nameplate,
    material_data,
    skills,
    offered_capability_description,
    required_capability_description,
    storage_configuration,
    carbon_footprint,
    product_identification,
    quality_information,
    technical_data,
    symptom_description,
    asset_interface_description,
    fault_description,
    condition_monitoring,
)

from app.tools.neo4j._base import _REGISTRY, SubmodelToolset

logger = logging.getLogger(__name__)

# ── Public API ─────────────────────────────────────────────────────────────────

def get_submodel_toolset(idShort: str) -> SubmodelToolset | None:
    """Return the :class:`SubmodelToolset` for *idShort*, or None."""
    return _REGISTRY.get(idShort)


def get_available_submodels(asset_id: str) -> list[str]:
    """
    Query Neo4j for the submodels actually linked to the shell of *asset_id*
    via a HAS_SUBMODEL relationship, and return only those whose idShort is
    registered in this package.

    This allows the graph to offer only the tools that are relevant for a
    specific asset instead of loading all submodel tools into the LLM context.
    """
    from app.services import neo4j_service as db

    try:
        rows = db.get_available_submodels_for_asset(asset_id)
    except Exception as exc:
        logger.warning("Could not query available submodels for %s: %s", asset_id, exc)
        return list(_REGISTRY.keys())

    available: list[str] = []
    for row in rows:
        id_short = row.get("idShort")
        semantic_id = row.get("semanticId", "")
        if id_short and id_short in _REGISTRY:
            available.append(id_short)
        elif semantic_id:
            # Also match by semantic ID in case idShort differs
            for ts in _REGISTRY.values():
                if ts.semantic_id == semantic_id and ts.idShort not in available:
                    available.append(ts.idShort)
    return available


# ── Backward-compatible dict shape used by graph/nodes.py ─────────────────────
# Shape: { idShort: {"tools": {intent: callable}, "description": str} }

SUBMODEL_REGISTRY: dict[str, dict[str, Any]] = {
    idShort: {
        "tools": ts.tools,
        "description": ts.description,
        "semantic_id": ts.semantic_id,
    }
    for idShort, ts in _REGISTRY.items()
}

VALID_SUBMODELS: set[str] = set(_REGISTRY.keys())
