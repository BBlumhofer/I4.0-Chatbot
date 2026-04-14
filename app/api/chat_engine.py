"""
Shared graph-execution utilities used by both the custom REST API and the
OpenAI-compatible API.

Responsibilities:
  - Build / hold the compiled LangGraph instance.
  - Provide run_graph() and run_graph_with_updates() helpers.
  - Provide helpers for session / confirmation bookkeeping.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable, Optional

from app.graph.graph import build_graph
from app.graph.nodes import (
    check_confirmation,
    clean_tool_args,
    execute_tool,
    generate_response,
    interpret_input,
    resolve_entities,
    route_capability,
    select_tool_generic,
    select_tool_neo4j,
    validate_submodel,
)
from app.graph.nodes import _is_agent_inventory_query
from app.services import session_service as session_svc

logger = logging.getLogger(__name__)

# Compile graph once at module load (shared across all routers).
_graph = build_graph()


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _short_asset_label(asset_id: str | None) -> str:
    if not asset_id:
        return ""
    parts = [p for p in str(asset_id).split("/") if p]
    return parts[-1] if parts else str(asset_id)


# ── Session / confirmation helpers ─────────────────────────────────────────────

def persist_pending_confirmation(session_id: str, final_state: dict[str, Any]) -> None:
    ctx = session_svc.get_session(session_id)
    ctx["pending_state"] = {
        "tool_name": final_state.get("tool_name"),
        "tool_args": final_state.get("tool_args"),
        "capability": final_state.get("capability"),
        "submodel": final_state.get("submodel"),
    }
    session_svc.save_session(session_id, ctx)


def append_chat_turns(
    session_id: str,
    user_text: str | None,
    assistant_text: str | None,
) -> None:
    """Best-effort persistence of short chat history for follow-up context."""
    try:
        if user_text:
            session_svc.append_chat_history(session_id, "user", user_text)
        if assistant_text:
            session_svc.append_chat_history(session_id, "assistant", assistant_text)
    except Exception as exc:
        logger.debug("Unable to persist chat history for session %s: %s", session_id, exc)


# ── Graph execution ────────────────────────────────────────────────────────────

def run_graph(session_id: str, user_input: str) -> dict[str, Any]:
    """Invoke the full graph synchronously and return the final state."""
    initial_state: dict[str, Any] = {
        "session_id": session_id,
        "user_input": user_input,
    }
    return _graph.invoke(initial_state)


def run_graph_with_updates(
    session_id: str,
    user_input: str,
    on_status: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    """
    Execute the graph node-by-node while emitting status messages via
    *on_status* so callers can stream UX progress indicators.
    """
    state: dict[str, Any] = {
        "session_id": session_id,
        "user_input": user_input,
    }

    def push(status: str) -> None:
        if on_status:
            on_status(status)

    push("Analysiere Anfrage")
    state.update(interpret_input(state))

    intent = str(state.get("intent") or "unknown")
    capability = str(state.get("capability") or "rag")
    submodel = state.get("submodel")
    if submodel:
        push(f"Denke: intent={intent}, capability={capability}, submodel={submodel}")
    else:
        push(f"Denke: intent={intent}, capability={capability}")

    capability = state.get("capability", "rag")
    if capability == "neo4j":
        push("Plane Neo4j-Abfrage")
    elif capability == "opcua":
        push("Pruefe OPC-UA Zugriff")
    elif capability == "kafka":
        push("Bereite Kafka-Befehl vor")
    elif capability == "agent_management":
        if _is_agent_inventory_query(user_input):
            push("Konservativer Modus: keine automatische Agentenauflistung")
        else:
            push("Plane Agent-Registry Abfrage")
    else:
        push("Nutze RAG-Dokumentensuche")

    push("Loese Entitaeten auf")
    state.update(resolve_entities(state))

    resolved = state.get("resolved_entities") or {}
    asset_id = resolved.get("asset_id")
    if asset_id:
        label = _short_asset_label(str(asset_id))
        push(f"Asset aufgeloest: {label}")
    elif resolved.get("disambiguation"):
        options = resolved.get("disambiguation") or []
        push(f"Mehrdeutig: {', '.join(str(o) for o in options[:3])}")

    push("Route Anfrage zur Datenquelle")
    state.update(route_capability(state))

    capability = state.get("capability", "rag")
    if capability == "neo4j":
        push("Pruefe Neo4j-Submodell")
        state.update(validate_submodel(state))
        push(f"Waehle Neo4j-Tool fuer {state.get('submodel')}")
        state.update(select_tool_neo4j(state))
    else:
        push(f"Waehle Tool fuer {capability}")
        state.update(select_tool_generic(state))

    tool_name = state.get("tool_name") or "tool"
    tool_args = state.get("tool_args") or {}
    arg_keys = ", ".join(sorted(str(k) for k in tool_args.keys())[:4])
    if arg_keys:
        push(f"Tool geplant: {tool_name} ({arg_keys})")
    else:
        push(f"Tool geplant: {tool_name}")

    state.update(check_confirmation(state))
    if state.get("requires_confirmation"):
        push("Warte auf Bestaetigung")
        return state

    push(f"Fuehre {tool_name} aus")
    state.update(execute_tool(state))

    if state.get("error"):
        push("Tool meldet Fehler")
    else:
        tool_result = state.get("tool_result")
        if isinstance(tool_result, list):
            push(f"Tool-Ergebnis: {len(tool_result)} Eintraege")
        elif isinstance(tool_result, dict):
            push("Tool-Ergebnis: strukturierte Daten")
        else:
            push("Tool-Ergebnis: Wert erhalten")

    push("Formuliere Antwort")
    state.update(generate_response(state))
    return state


# ── Confirmation execution ─────────────────────────────────────────────────────

def execute_confirmed_tool(session_id: str) -> tuple[bool, str]:
    """
    Execute the pending confirmed tool for *session_id*.

    Returns (success, response_text).
    """
    from app.tools import agent_management_tools, kafka_tools, opcua_tools, rag_tools
    from app.tools.neo4j import SUBMODEL_REGISTRY

    ctx = session_svc.get_session(session_id)
    pending = ctx.get("pending_state")

    if not pending:
        return False, "Kein ausstehender Befehl gefunden."

    capability: str = pending.get("capability", "kafka")
    tool_name: str = pending.get("tool_name", "")
    tool_args: dict[str, Any] = clean_tool_args(dict(pending.get("tool_args") or {}))

    tool_fn = None
    if capability == "kafka":
        tool_fn = kafka_tools.KAFKA_TOOL_REGISTRY.get(tool_name)
    elif capability == "opcua":
        tool_fn = opcua_tools.OPCUA_TOOL_REGISTRY.get(tool_name)
    elif capability == "neo4j":
        submodel = pending.get("submodel", "Structure")
        tool_fn = SUBMODEL_REGISTRY.get(submodel, {}).get("tools", {}).get(tool_name)
    elif capability == "agent_management":
        tool_fn = agent_management_tools.AGENT_MANAGEMENT_TOOL_REGISTRY.get(tool_name)
    else:
        tool_fn = rag_tools.RAG_TOOL_REGISTRY.get(tool_name)

    ctx.pop("pending_state", None)
    session_svc.save_session(session_id, ctx)

    if tool_fn is None:
        return False, f"Tool '{tool_name}' nicht gefunden."

    try:
        result = tool_fn(**tool_args)
        return True, f"Befehl ausgeführt: {result}"
    except Exception as exc:
        logger.exception("Confirmed tool execution failed: %s", exc)
        return False, f"Fehler bei der Ausführung: {exc}"


def cancel_pending_tool(session_id: str) -> None:
    """Discard the pending confirmation state for *session_id*."""
    ctx = session_svc.get_session(session_id)
    ctx.pop("pending_state", None)
    session_svc.save_session(session_id, ctx)
