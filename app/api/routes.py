"""
FastAPI routes for the I4.0 Chatbot.

Endpoints:
  POST /chat           – main chat endpoint
  POST /chat/confirm   – confirm a pending Kafka action
  DELETE /sessions/{session_id} – clear session context
  GET  /health         – liveness probe
"""
from __future__ import annotations

import json
import uuid
import logging
import queue
import threading
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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
router = APIRouter()

# Compile graph once at module load
_graph = build_graph()


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's natural-language message")
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn context. Generated if omitted.",
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    intent: Optional[str] = None
    capability: Optional[str] = None
    submodel: Optional[str] = None


class ConfirmRequest(BaseModel):
    session_id: str
    confirmed: bool = Field(..., description="True = proceed, False = cancel")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run_graph(session_id: str, user_input: str) -> dict[str, Any]:
    initial_state: dict[str, Any] = {
        "session_id": session_id,
        "user_input": user_input,
    }
    return _graph.invoke(initial_state)


def _short_asset_label(asset_id: str | None) -> str:
    if not asset_id:
        return ""
    parts = [p for p in str(asset_id).split("/") if p]
    return parts[-1] if parts else str(asset_id)


def _persist_pending_confirmation(session_id: str, final_state: dict[str, Any]) -> None:
    ctx = session_svc.get_session(session_id)
    ctx["pending_state"] = {
        "tool_name": final_state.get("tool_name"),
        "tool_args": final_state.get("tool_args"),
        "capability": final_state.get("capability"),
        "submodel": final_state.get("submodel"),
    }
    session_svc.save_session(session_id, ctx)


def _append_chat_turns(session_id: str, user_text: str | None, assistant_text: str | None) -> None:
    """Best-effort persistence of short chat history for follow-up context."""
    try:
        if user_text:
            session_svc.append_chat_history(session_id, "user", user_text)
        if assistant_text:
            session_svc.append_chat_history(session_id, "assistant", assistant_text)
    except Exception as exc:
        logger.debug("Unable to persist chat history for session %s: %s", session_id, exc)


def _run_graph_with_updates(
    session_id: str,
    user_input: str,
    on_status: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
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
        # For broad inventory queries prefer conservative UX: don't imply
        # automatic listing in the status stream.
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


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_text(text: str, chunk_size: int = 80) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    current = ""
    for token in text.split(" "):
        candidate = token if not current else f"{current} {token}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = token
    if current:
        chunks.append(current)
    return chunks


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.  Runs the full LangGraph pipeline and returns
    either a final answer or a confirmation request (for Kafka actions).
    """
    session_id = req.session_id or str(uuid.uuid4())

    try:
        final_state = _run_graph(session_id, req.message)
    except Exception as exc:
        logger.exception("Graph execution error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    requires_confirmation = bool(final_state.get("requires_confirmation"))

    if requires_confirmation:
        _persist_pending_confirmation(session_id, final_state)

    response_text = final_state.get("response") or final_state.get("confirmation_message") or ""
    _append_chat_turns(session_id, req.message, response_text)

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        requires_confirmation=requires_confirmation,
        confirmation_message=final_state.get("confirmation_message"),
        intent=final_state.get("intent"),
        capability=final_state.get("capability"),
        submodel=final_state.get("submodel"),
    )


@router.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """
    Streaming chat endpoint (SSE).

    Events:
      - status:   processing step updates for UX typing indicators
      - chunk:    partial assistant text deltas
      - final:    final payload compatible with ChatResponse
      - error:    failure information
    """
    session_id = req.session_id or str(uuid.uuid4())

    def event_generator():
        status_queue: queue.Queue[str] = queue.Queue()
        result_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

        def on_status(message: str) -> None:
            status_queue.put(message)

        def worker() -> None:
            try:
                final_state = _run_graph_with_updates(session_id, req.message, on_status=on_status)
                result_queue.put(("ok", final_state))
            except Exception as exc:
                result_queue.put(("error", exc))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        try:
            yield _sse("status", {"message": "Empfange Nachricht"})
            while thread.is_alive() or not status_queue.empty():
                try:
                    status = status_queue.get(timeout=0.1)
                    yield _sse("status", {"message": status})
                except queue.Empty:
                    continue

            status: str
            while True:
                try:
                    status = status_queue.get_nowait()
                except queue.Empty:
                    break
                yield _sse("status", {"message": status})

            outcome, payload = result_queue.get(timeout=1)
            if outcome == "error":
                raise payload

            final_state: dict[str, Any] = payload

            requires_confirmation = bool(final_state.get("requires_confirmation"))
            if requires_confirmation:
                _persist_pending_confirmation(session_id, final_state)
                confirmation_text = final_state.get("confirmation_message") or "Bestaetigung erforderlich."
                _append_chat_turns(session_id, req.message, confirmation_text)
                yield _sse("confirmation", {"message": confirmation_text})
                yield _sse(
                    "final",
                    {
                        "session_id": session_id,
                        "response": confirmation_text,
                        "requires_confirmation": True,
                        "confirmation_message": final_state.get("confirmation_message"),
                        "intent": final_state.get("intent"),
                        "capability": final_state.get("capability"),
                        "submodel": final_state.get("submodel"),
                    },
                )
                return

            response_text = final_state.get("response") or ""
            _append_chat_turns(session_id, req.message, response_text)
            for part in _chunk_text(response_text):
                yield _sse("chunk", {"delta": part + " "})

            yield _sse(
                "final",
                {
                    "session_id": session_id,
                    "response": response_text,
                    "requires_confirmation": False,
                    "confirmation_message": final_state.get("confirmation_message"),
                    "intent": final_state.get("intent"),
                    "capability": final_state.get("capability"),
                    "submodel": final_state.get("submodel"),
                },
            )
        except Exception as exc:
            logger.exception("Streaming graph execution error: %s", exc)
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/confirm", response_model=ChatResponse)
def confirm(req: ConfirmRequest) -> ChatResponse:
    """
    Confirm or cancel a pending Kafka action.
    If confirmed=True the stored tool is executed; otherwise it is cancelled.
    """
    from app.tools import agent_management_tools, kafka_tools, opcua_tools, rag_tools
    from app.tools.neo4j import SUBMODEL_REGISTRY

    ctx = session_svc.get_session(req.session_id)
    pending = ctx.get("pending_state")

    if not pending:
        raise HTTPException(status_code=400, detail="No pending confirmation found.")

    if not req.confirmed:
        ctx.pop("pending_state", None)
        session_svc.save_session(req.session_id, ctx)
        _append_chat_turns(req.session_id, "Bestaetigung: Aktion abbrechen", "Aktion abgebrochen.")
        return ChatResponse(
            session_id=req.session_id,
            response="Aktion abgebrochen.",
            requires_confirmation=False,
        )

    # Execute the pending tool
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
    session_svc.save_session(req.session_id, ctx)

    if tool_fn is None:
        raise HTTPException(status_code=500, detail=f"Tool '{tool_name}' not found.")

    try:
        result = tool_fn(**tool_args)
        response_text = f"Befehl ausgeführt: {result}"
        _append_chat_turns(req.session_id, "Bestaetigung: Aktion ausfuehren", response_text)
        return ChatResponse(
            session_id=req.session_id,
            response=response_text,
            requires_confirmation=False,
        )
    except Exception as exc:
        logger.exception("Confirmed tool execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}")
def clear_session(session_id: str) -> dict[str, str]:
    """Delete the stored context for *session_id*."""
    session_svc.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
