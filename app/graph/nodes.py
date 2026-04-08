"""
LangGraph node functions.

Each function takes the current AgentState and returns a (partial) state
update dict.  Nodes are pure functions – side-effects live in services/tools.
"""
from __future__ import annotations

import logging
from typing import Any

from app.graph.state import AgentState
from app.llm import interpreter as llm
from app.services import neo4j_service as neo4j_svc
from app.services import session_service as session_svc
from app.tools.neo4j import SUBMODEL_REGISTRY, VALID_SUBMODELS
from app.tools import neo4j_tools, opcua_tools, kafka_tools, rag_tools
from app.config import settings

logger = logging.getLogger(__name__)


# ── 1. interpret_input ─────────────────────────────────────────────────────────

def interpret_input(state: AgentState) -> dict[str, Any]:
    """
    Use the LLM to extract intent, capability, submodel and entities
    from the user's raw input.
    """
    session_ctx = {}
    if state.get("session_id"):
        session_ctx = session_svc.get_session(state["session_id"])

    try:
        result = llm.interpret(state["user_input"], context=session_ctx)
    except Exception as exc:
        logger.error("LLM interpretation error in node: %s", exc)
        result = {
            "intent": "unknown",
            "capability": "rag",
            "submodel": None,
            "entities": {},
        }

    return {
        "intent": result.get("intent", "unknown"),
        "capability": result.get("capability", "rag"),
        "submodel": result.get("submodel"),
        "entities": result.get("entities", {}),
        "error": None,
    }


# ── 2. resolve_entities ────────────────────────────────────────────────────────

def resolve_entities(state: AgentState) -> dict[str, Any]:
    """
    Map human-readable entity names to system IDs using Neo4j fuzzy search.

    Populates state["resolved_entities"] with at minimum an "asset_id" key
    when an asset entity can be resolved.
    """
    entities: dict[str, Any] = dict(state.get("entities") or {})
    resolved: dict[str, Any] = {}

    asset_hint = (
        entities.get("asset")
        or entities.get("asset_name")
        or entities.get("anlage")
        or entities.get("modul")
    )

    if asset_hint:
        try:
            candidates = neo4j_svc.find_asset_by_name(str(asset_hint))
            if len(candidates) == 1:
                resolved["asset_id"] = candidates[0]["id"]
                resolved["asset_name"] = candidates[0].get("name") or candidates[0].get("idShort")
                resolved["asset_type"] = candidates[0].get("type")
                # persist in session
                if state.get("session_id"):
                    session_svc.update_session(
                        state["session_id"],
                        {
                            "current_asset": resolved["asset_id"],
                            "current_asset_name": resolved["asset_name"],
                        },
                    )
            elif len(candidates) > 1:
                # Ambiguous – ask for clarification
                names = [c.get("name") or c.get("idShort") for c in candidates]
                resolved["disambiguation"] = names
        except Exception as exc:
            logger.warning("Entity resolution failed: %s", exc)
    else:
        # Fall back to session context
        if state.get("session_id"):
            ctx = session_svc.get_session(state["session_id"])
            if ctx.get("current_asset"):
                resolved["asset_id"] = ctx["current_asset"]
                resolved["asset_name"] = ctx.get("current_asset_name")

    # Forward any non-asset entities (e.g. step name, node_id) unchanged
    for k, v in entities.items():
        if k not in {"asset", "asset_name", "anlage", "modul"}:
            resolved[k] = v

    return {"resolved_entities": resolved}


# ── 3. route_capability ────────────────────────────────────────────────────────

def route_capability(state: AgentState) -> dict[str, Any]:
    """
    Pure routing node – no state mutation needed here because the conditional
    edge lambda reads state["capability"] directly.
    Validates the capability value and falls back to "rag" if unknown.
    """
    valid = {"neo4j", "opcua", "rag", "kafka"}
    capability = state.get("capability", "rag")
    if capability not in valid:
        logger.warning("Unknown capability '%s', falling back to 'rag'", capability)
        capability = "rag"
    return {"capability": capability}


# ── 4. validate_submodel ───────────────────────────────────────────────────────

def validate_submodel(state: AgentState) -> dict[str, Any]:
    """
    Ensure the LLM-chosen submodel is valid.
    Falls back to 'Structure' if missing or unknown.
    """
    submodel = state.get("submodel")
    if submodel not in VALID_SUBMODELS:
        logger.warning("Invalid/missing submodel '%s', falling back to 'Structure'", submodel)
        submodel = "Structure"
    # Update session with current submodel
    if state.get("session_id"):
        session_svc.update_session(state["session_id"], {"current_submodel": submodel})
    return {"submodel": submodel}


# ── 5a. select_tool_neo4j ──────────────────────────────────────────────────────

def select_tool_neo4j(state: AgentState) -> dict[str, Any]:
    """
    Select the appropriate Neo4j tool based on submodel + intent.
    """
    submodel = state.get("submodel", "Structure")
    intent = state.get("intent", "get_properties")
    resolved = state.get("resolved_entities") or {}

    registry = SUBMODEL_REGISTRY.get(submodel, {})
    tools_map: dict[str, Any] = registry.get("tools", {})

    # Direct intent match
    tool_name = intent if intent in tools_map else None

    # Fallback mapping
    if tool_name is None:
        fallback_map = {
            "get_structure": "get_parts",
            "list_parts": "get_parts",
            "get_bom": "get_parts",
            "list_steps": "get_steps",
            "check_done": "is_finished",
            "explain": "get_properties",
            "describe": "get_properties",
        }
        tool_name = fallback_map.get(intent, "get_properties")

    # If still not found in this submodel's registry, use get_properties
    if tool_name not in tools_map:
        tool_name = "get_properties"

    tool_args: dict[str, Any] = {}
    if resolved.get("asset_id"):
        tool_args["asset_id"] = resolved["asset_id"]
    if resolved.get("step"):
        tool_args["step"] = resolved["step"]
    if submodel and "submodel" not in tool_args:
        tool_args["submodel"] = submodel

    return {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "requires_confirmation": False,
    }


# ── 5b. select_tool_generic ────────────────────────────────────────────────────

def select_tool_generic(state: AgentState) -> dict[str, Any]:
    """
    Select the appropriate tool for opcua / rag / kafka capabilities.
    """
    capability = state.get("capability", "rag")
    intent = state.get("intent", "")
    resolved = state.get("resolved_entities") or {}
    entities = state.get("entities") or {}

    tool_name: str
    tool_args: dict[str, Any] = {}
    requires_confirmation = False
    confirmation_message = ""

    if capability == "opcua":
        endpoint = (
            resolved.get("endpoint")
            or entities.get("endpoint")
            or settings.opcua_endpoint
        )
        node_id = (
            resolved.get("node_id")
            or entities.get("node_id")
            or "ns=2;i=1"
        )
        username = entities.get("username")
        password = entities.get("password")

        if intent == "connect_to_server":
            tool_name = "connect_to_server"
            tool_args = {"endpoint": endpoint, "username": username, "password": password}
        elif intent == "disconnect":
            tool_name = "disconnect"
            tool_args = {"endpoint": endpoint}
            requires_confirmation = True
            confirmation_message = (
                f"OPC UA Server '{endpoint}' wirklich trennen?"
            )
        elif intent == "browse":
            tool_name = "browse"
            tool_args = {"endpoint": endpoint, "node_id": node_id if node_id != "ns=2;i=1" else None}
        elif intent == "lock_server":
            tool_name = "lock_server"
            tool_args = {"endpoint": endpoint}
        elif intent == "read_value":
            tool_name = "read_value"
            tool_args = {"endpoint": endpoint, "node_id": node_id}
        else:
            tool_name = "get_live_status"
            tool_args = {"endpoint": endpoint, "node_id": node_id}

    elif capability == "kafka":
        command = {
            "action": intent,
            "asset_id": resolved.get("asset_id"),
            **{k: v for k, v in entities.items() if k not in {"asset", "asset_name"}},
        }
        tool_name = "send_command"
        tool_args = {"command": command}
        requires_confirmation = True
        confirmation_message = (
            f"Soll der Befehl '{intent}' wirklich ausgeführt werden? "
            f"Asset: {resolved.get('asset_id') or '(unbekannt)'}"
        )

    else:  # rag
        tool_name = "search_docs"
        tool_args = {"query": state.get("user_input", "")}

    return {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "requires_confirmation": requires_confirmation,
        "confirmation_message": confirmation_message,
    }


# ── 6. check_confirmation ──────────────────────────────────────────────────────

def check_confirmation(state: AgentState) -> dict[str, Any]:
    """
    If confirmation is required, the graph terminates early (END) so that the
    API can return the confirmation_message to the frontend.
    If no confirmation needed, this node is a pass-through.
    The actual routing is done by the conditional edge, not here.
    """
    return {}


# ── Shared utility ─────────────────────────────────────────────────────────────

def clean_tool_args(tool_args: dict[str, Any]) -> dict[str, Any]:
    """
    Strip internal routing keys (e.g. 'submodel') that are not real
    tool-function parameters.  Centralised here to avoid duplication
    between execute_tool and the /chat/confirm endpoint.
    """
    cleaned = dict(tool_args)
    cleaned.pop("submodel", None)
    return cleaned


# ── 7. execute_tool ────────────────────────────────────────────────────────────

def execute_tool(state: AgentState) -> dict[str, Any]:
    """
    Dispatch to the appropriate tool based on capability + tool_name.
    """
    capability = state.get("capability", "rag")
    tool_name = state.get("tool_name", "")
    tool_args = clean_tool_args(dict(state.get("tool_args") or {}))

    tool_fn = None

    if capability == "neo4j":
        submodel = state.get("submodel", "Structure")
        registry = SUBMODEL_REGISTRY.get(submodel, {})
        tool_fn = registry.get("tools", {}).get(tool_name)

    elif capability == "opcua":
        tool_fn = opcua_tools.OPCUA_TOOL_REGISTRY.get(tool_name)

    elif capability == "kafka":
        tool_fn = kafka_tools.KAFKA_TOOL_REGISTRY.get(tool_name)

    else:  # rag
        tool_fn = rag_tools.RAG_TOOL_REGISTRY.get(tool_name)

    if tool_fn is None:
        logger.error("No tool found for capability=%s tool=%s", capability, tool_name)
        return {"tool_result": None, "error": f"Unknown tool: {tool_name}"}

    try:
        result = tool_fn(**tool_args)
        return {"tool_result": result, "error": None}
    except Exception as exc:
        logger.error("Tool execution failed: %s", exc)
        return {"tool_result": None, "error": str(exc)}


# ── 8. generate_response ───────────────────────────────────────────────────────

def generate_response(state: AgentState) -> dict[str, Any]:
    """
    Produce a natural-language response from the tool result.
    For now, uses a simple template; in production this would call the LLM
    again with a summarisation prompt.
    """
    error = state.get("error")
    if error:
        return {"response": f"Fehler: {error}"}

    tool_result = state.get("tool_result")
    capability = state.get("capability", "")
    intent = state.get("intent", "")
    asset_id = (state.get("resolved_entities") or {}).get("asset_id", "")

    if tool_result is None:
        return {"response": "Es wurden keine Daten gefunden."}

    if capability == "rag":
        if isinstance(tool_result, list) and tool_result:
            snippets = "\n\n".join(d["document"] for d in tool_result[:3])
            return {"response": f"Relevante Dokumentation:\n\n{snippets}"}
        return {"response": "Keine relevanten Dokumente gefunden."}

    if capability == "opcua":
        if isinstance(tool_result, dict):
            status = tool_result.get("status", "")
            endpoint = tool_result.get("endpoint", "")
            if status in ("connected", "disconnected", "not_registered", "locked"):
                return {"response": f"OPC UA Server '{endpoint}': {status}"}
            # DataValue result
            value = tool_result.get("value")
            node_id = tool_result.get("node_id", "")
            ts = tool_result.get("source_timestamp", "")
            return {"response": f"Node {node_id} @ {endpoint}: {value} (Zeitstempel: {ts})"}
        if isinstance(tool_result, list):
            count = len(tool_result)
            names = [e.get("display_name") or e.get("node_id") for e in tool_result[:10]]
            return {"response": f"{count} Knoten gefunden: {', '.join(str(n) for n in names)}"}
        return {"response": f"OPC UA Ergebnis: {tool_result}"}

    if capability == "kafka":
        return {"response": f"Befehl gesendet: {tool_result}"}

    # neo4j
    if isinstance(tool_result, list):
        count = len(tool_result)
        return {
            "response": (
                f"Ergebnis für {intent} auf Asset {asset_id}: "
                f"{count} Einträge gefunden.\n{tool_result}"
            )
        }
    return {"response": f"Ergebnis: {tool_result}"}
