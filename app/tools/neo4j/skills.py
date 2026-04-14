"""
Neo4j tools for the **Skills** submodel.

Covers: capabilities / skills of a resource asset (IDTA Skills concept).
Semantic ID: https://admin-shell.io/idta/Submodel/Skills/1/0
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel
from app.tools.neo4j._query import asset_match_clause, get_submodel_elements_recursive


SUBMODEL = "Skills"


def list_skills(asset_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return all skills from SkillSet including optional display names."""
    cypher = f"""
    MATCH (a:Asset)
    {asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: '{SUBMODEL}'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(skillSet {{idShort: 'SkillSet'}})
    MATCH (skillSet)-[:HAS_ELEMENT]->(skill)
    OPTIONAL MATCH (skill)-[:HAS_ELEMENT]->(nameEl {{idShort: 'Name'}})
    RETURN skill.idShort AS skillIdShort,
           nameEl.value AS skillName,
           labels(skill) AS elementTypes,
           skillSet.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(cypher, {"asset_id": asset_id, "limit": limit})


def get_skills(asset_id: str) -> list[dict[str, Any]]:
    """Backward-compatible compact alias for list_skills."""
    rows = list_skills(asset_id)
    return [
        {
            "skill": row.get("skillIdShort"),
            "name": row.get("skillName"),
        }
        for row in rows
    ]


def get_skill_endpoints(
    asset_id: str,
    skill_id_short: str | None = None,
    skill_name: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return SkillEndpoint values for one skill or all skills."""
    cypher = f"""
    MATCH (a:Asset)
    {asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: '{SUBMODEL}'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(skillSet {{idShort: 'SkillSet'}})
    MATCH (skillSet)-[:HAS_ELEMENT]->(skill)
    OPTIONAL MATCH (skill)-[:HAS_ELEMENT]->(nameEl {{idShort: 'Name'}})
    MATCH (skill)-[:HAS_ELEMENT]->(sid {{idShort: 'SkillInterfaceDescription'}})
    MATCH (sid)-[:HAS_ELEMENT*0..]->(endpoint {{idShort: 'SkillEndpoint'}})
    WHERE ($skill_id_short IS NULL OR skill.idShort = $skill_id_short)
      AND ($skill_name IS NULL OR toLower(coalesce(nameEl.value, '')) = toLower($skill_name))
    RETURN skill.idShort AS skillIdShort,
           nameEl.value AS skillName,
           endpoint.value AS endpoint,
           endpoint.valueType AS valueType,
           sid.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(
        cypher,
        {
            "asset_id": asset_id,
            "skill_id_short": skill_id_short,
            "skill_name": skill_name,
            "limit": limit,
        },
    )


def list_skill_input_parameters(
    asset_id: str,
    skill_id_short: str | None = None,
    skill_name: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return RequiredInputParameters entries for one skill or all skills."""
    cypher = f"""
    MATCH (a:Asset)
    {asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(:Submodel {{idShort: '{SUBMODEL}'}})
          -[:HAS_ELEMENT]->(root)
    MATCH (root)-[:HAS_ELEMENT*0..]->(skillSet {{idShort: 'SkillSet'}})
    MATCH (skillSet)-[:HAS_ELEMENT]->(skill)
    OPTIONAL MATCH (skill)-[:HAS_ELEMENT]->(nameEl {{idShort: 'Name'}})
    MATCH (skill)-[:HAS_ELEMENT]->(sid {{idShort: 'SkillInterfaceDescription'}})
    MATCH (sid)-[:HAS_ELEMENT]->(required {{idShort: 'RequiredInputParameters'}})
    MATCH (required)-[:HAS_ELEMENT]->(param)
    WHERE ($skill_id_short IS NULL OR skill.idShort = $skill_id_short)
      AND ($skill_name IS NULL OR toLower(coalesce(nameEl.value, '')) = toLower($skill_name))
    RETURN skill.idShort AS skillIdShort,
           nameEl.value AS skillName,
           required.idShort AS containerIdShort,
           param.idShort AS idShort,
           param.value AS value,
           param.valueType AS valueType,
           labels(param) AS elementTypes,
           required.idShort AS parentIdShort
    LIMIT $limit
    """
    return db.run_query(
        cypher,
        {
            "asset_id": asset_id,
            "skill_id_short": skill_id_short,
            "skill_name": skill_name,
            "limit": limit,
        },
    )


def get_properties(asset_id: str) -> list[dict[str, Any]]:
    """Return all Skills submodel elements (generic fallback)."""
    return get_submodel_elements_recursive(asset_id, SUBMODEL)


register_submodel(SubmodelToolset(
    idShort=SUBMODEL,
    semantic_id="https://admin-shell.io/idta/Submodel/Skills/1/0",
    description="Fähigkeiten einer Ressource (IDTA Skills)",
    tools={
        "list_skills": list_skills,
        "get_skills": get_skills,
        "get_skill_endpoints": get_skill_endpoints,
        "list_skill_input_parameters": list_skill_input_parameters,
        "get_properties": get_properties,
    },
))
