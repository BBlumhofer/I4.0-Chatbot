"""
LangGraph AgentState – shared state that flows through every node.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # ── Conversation messages (LangGraph SDK / agent-chat-ui) ─────────────────
    messages: Annotated[list[BaseMessage], add_messages]

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
