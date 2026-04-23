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
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services import session_service as session_svc
from app.api.chat_engine import (
    append_chat_turns as _append_chat_turns,
    cancel_pending_tool,
    execute_confirmed_tool,
    persist_pending_confirmation as _persist_pending_confirmation,
    run_graph as _run_graph,
    run_graph_with_updates as _run_graph_with_updates,
)

logger = logging.getLogger(__name__)
router = APIRouter()


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
    ctx = session_svc.get_session(req.session_id)
    pending = ctx.get("pending_state")

    if not pending:
        raise HTTPException(status_code=400, detail="No pending confirmation found.")

    if not req.confirmed:
        cancel_pending_tool(req.session_id)
        _append_chat_turns(req.session_id, "Bestaetigung: Aktion abbrechen", "Aktion abgebrochen.")
        return ChatResponse(
            session_id=req.session_id,
            response="Aktion abgebrochen.",
            requires_confirmation=False,
        )

    success, response_text = execute_confirmed_tool(req.session_id)
    if not success:
        raise HTTPException(status_code=500, detail=response_text)

    _append_chat_turns(req.session_id, "Bestaetigung: Aktion ausfuehren", response_text)
    return ChatResponse(
        session_id=req.session_id,
        response=response_text,
        requires_confirmation=False,
    )


@router.delete("/sessions/{session_id}")
def clear_session(session_id: str) -> dict[str, str]:
    """Delete the stored context for *session_id*."""
    session_svc.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
