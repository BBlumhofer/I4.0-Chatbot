"""
FastAPI routes for the I4.0 Chatbot.

Endpoints:
  POST /chat           – main chat endpoint
  POST /chat/confirm   – confirm a pending Kafka action
  DELETE /sessions/{session_id} – clear session context
  GET  /health         – liveness probe
"""
from __future__ import annotations

import uuid
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.graph import build_graph
from app.graph.nodes import clean_tool_args
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
        # Persist the pending state so /confirm can resume it
        ctx = session_svc.get_session(session_id)
        ctx["pending_state"] = {
            "tool_name": final_state.get("tool_name"),
            "tool_args": final_state.get("tool_args"),
            "capability": final_state.get("capability"),
            "submodel": final_state.get("submodel"),
        }
        session_svc.save_session(session_id, ctx)

    return ChatResponse(
        session_id=session_id,
        response=final_state.get("response") or final_state.get("confirmation_message") or "",
        requires_confirmation=requires_confirmation,
        confirmation_message=final_state.get("confirmation_message"),
        intent=final_state.get("intent"),
        capability=final_state.get("capability"),
        submodel=final_state.get("submodel"),
    )


@router.post("/chat/confirm", response_model=ChatResponse)
def confirm(req: ConfirmRequest) -> ChatResponse:
    """
    Confirm or cancel a pending Kafka action.
    If confirmed=True the stored tool is executed; otherwise it is cancelled.
    """
    from app.tools import kafka_tools, neo4j_tools, opcua_tools, rag_tools
    from app.tools.neo4j_tools import SUBMODEL_REGISTRY

    ctx = session_svc.get_session(req.session_id)
    pending = ctx.get("pending_state")

    if not pending:
        raise HTTPException(status_code=400, detail="No pending confirmation found.")

    if not req.confirmed:
        ctx.pop("pending_state", None)
        session_svc.save_session(req.session_id, ctx)
        return ChatResponse(
            session_id=req.session_id,
            response="Aktion abgebrochen.",
            requires_confirmation=False,
        )

    # Execute the pending tool
    capability: str = pending.get("capability", "kafka")
    tool_name: str = pending.get("tool_name", "")
    tool_args: dict[str, Any] = _clean_tool_args(dict(pending.get("tool_args") or {}))

    tool_fn = None
    if capability == "kafka":
        tool_fn = kafka_tools.KAFKA_TOOL_REGISTRY.get(tool_name)
    elif capability == "opcua":
        tool_fn = opcua_tools.OPCUA_TOOL_REGISTRY.get(tool_name)
    elif capability == "neo4j":
        submodel = pending.get("submodel", "Structure")
        tool_fn = SUBMODEL_REGISTRY.get(submodel, {}).get("tools", {}).get(tool_name)
    else:
        tool_fn = rag_tools.RAG_TOOL_REGISTRY.get(tool_name)

    ctx.pop("pending_state", None)
    session_svc.save_session(req.session_id, ctx)

    if tool_fn is None:
        raise HTTPException(status_code=500, detail=f"Tool '{tool_name}' not found.")

    try:
        result = tool_fn(**tool_args)
        return ChatResponse(
            session_id=req.session_id,
            response=f"Befehl ausgeführt: {result}",
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
