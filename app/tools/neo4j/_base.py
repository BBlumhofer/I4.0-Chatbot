"""
Base types and registration mechanism for per-submodel Neo4j toolsets.

Usage – to add a new submodel, create a new file in this package:

    # app/tools/neo4j/my_submodel.py
    from app.tools.neo4j._base import SubmodelToolset, register_submodel
    from app.services import neo4j_service as db

    def my_tool(asset_id: str): ...

    register_submodel(SubmodelToolset(
        idShort="MySubmodel",
        semantic_id="https://admin-shell.io/idta/Submodel/MySubmodel/1/0",
        description="Short description for the LLM prompt",
        tools={
            "my_tool": my_tool,
            "get_properties": my_tool,   # always provide a get_properties fallback
        },
    ))

Then import the new module in app/tools/neo4j/__init__.py – that's all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SubmodelToolset:
    """Describes one AAS submodel and the tools that operate on it."""

    idShort: str
    """AAS idShort used as key in the graph (e.g. 'ProductionPlan')."""

    semantic_id: str
    """Fully qualified AAS semantic ID IRI for this submodel.
    Used to check whether a shell actually carries this submodel via
    the HAS_SUBMODEL relationship."""

    tools: dict[str, Callable[..., Any]]
    """Mapping of intent name → callable.
    Every toolset MUST contain a 'get_properties' entry as a safe fallback."""

    description: str = ""
    """Human-readable one-liner shown to the LLM for context selection."""


# Central registry – populated by each submodel module calling register_submodel().
_REGISTRY: dict[str, SubmodelToolset] = {}


def register_submodel(toolset: SubmodelToolset) -> SubmodelToolset:
    """
    Register *toolset* in the central registry.

    Returns the toolset unchanged so it can be used as a module-level
    statement or decorator-style.
    """
    if "get_properties" not in toolset.tools:
        raise ValueError(
            f"SubmodelToolset '{toolset.idShort}' must define a 'get_properties' tool "
            "as a safe fallback for unknown intents."
        )
    _REGISTRY[toolset.idShort] = toolset
    return toolset
