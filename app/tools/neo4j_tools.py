"""
Neo4j tools – grouped by AAS submodel.

Each tool function takes keyword arguments that match the tool_args dict
populated by select_tool_neo4j and returns a plain Python value that
will be stored in AgentState["tool_result"].
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services import neo4j_service as db

logger = logging.getLogger(__name__)


# ── ProductionPlan ─────────────────────────────────────────────────────────────

def get_steps(asset_id: str) -> list[dict[str, Any]]:
    """Return all production steps for an asset."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
          -[:HAS_ELEMENT]->(step:SubmodelElement)
    RETURN step.idShort AS step, step.value AS value,
           step.status AS status, step.duration AS duration
    ORDER BY step.order
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_step_duration(asset_id: str, step: str) -> Optional[dict[str, Any]]:
    """Return duration and status of a specific production step."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
          -[:HAS_ELEMENT]->(step:SubmodelElement {idShort: $step})
    RETURN step.idShort AS step, step.duration AS duration, step.status AS status
    """
    rows = db.run_query(cypher, {"asset_id": asset_id, "step": step})
    return rows[0] if rows else None


def is_finished(asset_id: str) -> bool:
    """Return True if the production plan is fully completed."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ProductionPlan'})
          -[:HAS_ELEMENT]->(step:SubmodelElement)
    WHERE step.status <> 'done'
    RETURN count(step) AS remaining
    """
    rows = db.run_query(cypher, {"asset_id": asset_id})
    return rows[0]["remaining"] == 0 if rows else False


# ── BillOfMaterial / Structure ─────────────────────────────────────────────────

def get_parts(asset_id: str) -> list[dict[str, Any]]:
    """Return direct parts / BOM entries for an asset."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel)
    WHERE sm.idShort IN ['BillOfMaterial', 'Structure']
    WITH sm
    MATCH (sm)-[:HAS_ELEMENT]->(el:SubmodelElement)
    RETURN el.idShort AS part, el.value AS value, el.quantity AS quantity
    """
    return db.run_query(cypher, {"asset_id": asset_id})


def get_hierarchy(asset_id: str) -> list[dict[str, Any]]:
    """Return the full asset hierarchy reachable from *asset_id*."""
    cypher = """
    MATCH path = (a:Asset {id: $asset_id})-[:HAS_PART*1..5]->(child:Asset)
    RETURN [n IN nodes(path) | n.id] AS hierarchy,
           child.id AS child_id, child.name AS child_name
    """
    return db.run_query(cypher, {"asset_id": asset_id})


# ── Nameplate ──────────────────────────────────────────────────────────────────

def get_nameplate(asset_id: str) -> list[dict[str, Any]]:
    """Return nameplate properties for an asset."""
    return db.get_submodel_elements(asset_id, "Nameplate")


# ── MaterialData ───────────────────────────────────────────────────────────────

def get_material_data(asset_id: str) -> list[dict[str, Any]]:
    """Return material data submodel elements for an asset."""
    return db.get_submodel_elements(asset_id, "MaterialData")


# ── Skills ─────────────────────────────────────────────────────────────────────

def get_skills(asset_id: str) -> list[dict[str, Any]]:
    """Return skill definitions for a resource asset."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'Skills'})
          -[:HAS_ELEMENT]->(skill:SubmodelElement)
    RETURN skill.idShort AS skill, skill.value AS value,
           skill.skillIri AS skillIri
    """
    return db.run_query(cypher, {"asset_id": asset_id})


# ── AssetInterfaceDescription ──────────────────────────────────────────────────

def get_interface_description(asset_id: str) -> list[dict[str, Any]]:
    """Return interface description elements."""
    return db.get_submodel_elements(asset_id, "AssetInterfaceDescription")


# ── FaultDescription ───────────────────────────────────────────────────────────

def get_fault_descriptions(asset_id: str) -> list[dict[str, Any]]:
    """Return fault code descriptions for an asset."""
    return db.get_submodel_elements(asset_id, "FaultDescription")


# ── ConditionMonitoring ────────────────────────────────────────────────────────

def get_condition_history(asset_id: str) -> list[dict[str, Any]]:
    """Return condition monitoring history entries."""
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {idShort: 'ConditionMonitoring'})
          -[:HAS_ELEMENT]->(entry:SubmodelElement)
    RETURN entry.idShort AS metric, entry.value AS value,
           entry.timestamp AS timestamp, entry.unit AS unit
    ORDER BY entry.timestamp DESC
    LIMIT 100
    """
    return db.run_query(cypher, {"asset_id": asset_id})


# ── Generic properties ─────────────────────────────────────────────────────────

def get_properties(asset_id: str, submodel: Optional[str] = None) -> list[dict[str, Any]]:
    """Return all properties of an asset (optionally filtered by submodel)."""
    if submodel:
        return db.get_submodel_elements(asset_id, submodel)
    cypher = """
    MATCH (a:Asset {id: $asset_id})
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel)
          -[:HAS_ELEMENT]->(el:SubmodelElement)
    RETURN sm.idShort AS submodel, el.idShort AS property,
           el.value AS value, el.valueType AS valueType
    """
    return db.run_query(cypher, {"asset_id": asset_id})


# ── Registry ───────────────────────────────────────────────────────────────────

# Maps submodel name → {tools: {intent: callable}}
SUBMODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "ProductionPlan": {
        "tools": {
            "get_steps": get_steps,
            "get_step_duration": get_step_duration,
            "is_finished": is_finished,
            "get_properties": get_properties,
        }
    },
    "BillOfMaterial": {
        "tools": {
            "get_parts": get_parts,
            "get_hierarchy": get_hierarchy,
            "get_structure": get_parts,
            "get_properties": get_properties,
        }
    },
    "Structure": {
        "tools": {
            "get_parts": get_parts,
            "get_hierarchy": get_hierarchy,
            "get_structure": get_parts,
            "get_properties": get_properties,
        }
    },
    "Nameplate": {
        "tools": {
            "get_nameplate": get_nameplate,
            "get_properties": get_nameplate,
        }
    },
    "MaterialData": {
        "tools": {
            "get_material_data": get_material_data,
            "get_properties": get_material_data,
        }
    },
    "Skills": {
        "tools": {
            "get_skills": get_skills,
            "get_properties": get_skills,
        }
    },
    "AssetInterfaceDescription": {
        "tools": {
            "get_interface_description": get_interface_description,
            "get_properties": get_interface_description,
        }
    },
    "FaultDescription": {
        "tools": {
            "get_fault_descriptions": get_fault_descriptions,
            "get_properties": get_fault_descriptions,
        }
    },
    "ConditionMonitoring": {
        "tools": {
            "get_condition_history": get_condition_history,
            "get_properties": get_condition_history,
        }
    },
}

VALID_SUBMODELS = set(SUBMODEL_REGISTRY.keys())
