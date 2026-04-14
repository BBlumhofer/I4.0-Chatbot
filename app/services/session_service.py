"""
Session service – stores per-session context in Redis.

Each session keeps:
  current_asset, current_submodel, pending_clarification
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

SESSION_TTL = 3600  # seconds
MAX_CHAT_HISTORY_TURNS = 16

_redis: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def get_session(session_id: str) -> dict[str, Any]:
    """Return the stored context for *session_id* (empty dict if not found)."""
    raw = _get_redis().get(f"session:{session_id}")
    if raw is None:
        return {}
    return json.loads(raw)


def save_session(session_id: str, context: dict[str, Any]) -> None:
    """Persist *context* for *session_id* with TTL refresh."""
    _get_redis().setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps(context),
    )


def update_session(session_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Merge *updates* into the existing session and persist."""
    ctx = get_session(session_id)
    ctx.update(updates)
    save_session(session_id, ctx)
    return ctx


def delete_session(session_id: str) -> None:
    _get_redis().delete(f"session:{session_id}")


def append_chat_history(
    session_id: str,
    role: str,
    text: str,
    max_turns: int = MAX_CHAT_HISTORY_TURNS,
) -> dict[str, Any]:
    """Append one chat turn and keep only the most recent turns."""
    if not text.strip():
        return get_session(session_id)

    ctx = get_session(session_id)
    history = ctx.get("chat_history")
    if not isinstance(history, list):
        history = []

    history.append({"role": str(role), "text": str(text)})
    if max_turns > 0 and len(history) > max_turns:
        history = history[-max_turns:]

    ctx["chat_history"] = history
    save_session(session_id, ctx)
    return ctx
