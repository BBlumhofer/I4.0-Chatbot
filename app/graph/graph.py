"""
LangGraph graph construction.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.state import AgentState
from app.graph.nodes import (
    check_confirmation,
    execute_tool,
    generate_response,
    interpret_input,
    resolve_entities,
    route_capability,
    select_tool_generic,
    select_tool_neo4j,
    validate_submodel,
)


def build_graph() -> StateGraph:
    """
    Construct and compile the LangGraph state machine.

    Flow:
        interpret_input
            → resolve_entities
            → route_capability
               ├─ neo4j  → validate_submodel → select_tool_neo4j ─┐
               ├─ opcua  → select_tool_generic                     │
               ├─ rag    → select_tool_generic                     │
               └─ kafka  → select_tool_generic ────────────────────┤
                                                                    ↓
                                                         check_confirmation
                                                           ├─ confirm → END  (await operator)
                                                           └─ execute → execute_tool
                                                                            → generate_response
                                                                                → END
    """
    graph = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    graph.add_node("interpret_input", interpret_input)
    graph.add_node("resolve_entities", resolve_entities)
    graph.add_node("route_capability", route_capability)
    graph.add_node("validate_submodel", validate_submodel)
    graph.add_node("select_tool_neo4j", select_tool_neo4j)
    graph.add_node("select_tool_generic", select_tool_generic)
    graph.add_node("check_confirmation", check_confirmation)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("generate_response", generate_response)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("interpret_input")

    # ── Linear edges ──────────────────────────────────────────────────────────
    graph.add_edge("interpret_input", "resolve_entities")
    graph.add_edge("resolve_entities", "route_capability")

    # ── Capability routing ─────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "route_capability",
        lambda s: s.get("capability", "rag"),
        {
            "neo4j": "validate_submodel",
            "opcua": "select_tool_generic",
            "rag": "select_tool_generic",
            "kafka": "select_tool_generic",
            "agent_management": "select_tool_generic",
        },
    )

    # ── Neo4j branch ───────────────────────────────────────────────────────────
    graph.add_edge("validate_submodel", "select_tool_neo4j")

    # ── Merge both branches → confirmation gate ────────────────────────────────
    graph.add_edge("select_tool_neo4j", "check_confirmation")
    graph.add_edge("select_tool_generic", "check_confirmation")

    # ── Confirmation gate ──────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "check_confirmation",
        lambda s: "confirm" if s.get("requires_confirmation") else "execute",
        {
            "confirm": END,
            "execute": "execute_tool",
        },
    )

    # ── Execution path ─────────────────────────────────────────────────────────
    graph.add_edge("execute_tool", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()


# Module-level compiled graph — used by langgraph.json / langgraph dev
graph = build_graph()
