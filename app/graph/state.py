"""
LangGraph AgentState – shared state that flows through every node.
"""
from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    session_id: str
    user_input: str

    # ── LLM interpretation ────────────────────────────────────────────────────
    intent: str
    capability: str          # neo4j | opcua | rag | kafka
    submodel: Optional[str]  # only relevant for neo4j
    entities: dict[str, Any]

    # ── Entity resolution ─────────────────────────────────────────────────────
    resolved_entities: dict[str, Any]

    # ── Tool selection ────────────────────────────────────────────────────────
    tool_name: str
    tool_args: dict[str, Any]

    # ── Confirmation ──────────────────────────────────────────────────────────
    requires_confirmation: bool
    confirmation_message: str

    # ── Tool result ───────────────────────────────────────────────────────────
    tool_result: Any

    # ── Final response ────────────────────────────────────────────────────────
    response: str

    # ── Error handling ────────────────────────────────────────────────────────
    error: Optional[str]
