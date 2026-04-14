"""
OpenAI-compatible API for the I4.0 Chatbot.

Open WebUI connects to this as its "OpenAI" backend.

Endpoints:
  GET  /v1/models                  – model list (required by Open WebUI)
  POST /v1/chat/completions        – main chat endpoint (streaming & non-streaming)

Session management
------------------
Open WebUI sends a ``chat-id`` HTTP header that uniquely identifies the
current conversation.  We use this value as the session_id so that each
Open WebUI conversation maps to exactly one Redis session (including
pending-confirmation state).  If the header is absent a random UUID is
generated instead.

Confirmation flow
-----------------
When the LangGraph pipeline returns ``requires_confirmation=True`` (e.g. for
Kafka commands), the confirmation message is returned as the assistant's
reply.  On the very next request the latest user message is inspected: if it
is a plain "ja" / "yes" / "nein" / "no" and there is a pending confirmation
in Redis for the session, it is dispatched to ``execute_confirmed_tool`` or
``cancel_pending_tool`` directly, bypassing the LangGraph graph.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.chat_engine import (
    append_chat_turns,
    cancel_pending_tool,
    execute_confirmed_tool,
    persist_pending_confirmation,
    run_graph_with_updates,
)
from app.services import session_service as session_svc

logger = logging.getLogger(__name__)
router = APIRouter()

# The virtual model name presented to Open WebUI.
_MODEL_ID = "i4-chatbot"

# Words that count as "yes" / "no" for the confirmation flow.
_CONFIRM_YES = {"ja", "yes", "j", "y", "bestätigen", "bestaetigen", "ok", "okay"}
_CONFIRM_NO = {"nein", "no", "n", "abbrechen", "cancel", "abbort", "abort"}


# ── Pydantic models ────────────────────────────────────────────────────────────

class _Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = _MODEL_ID
    messages: list[_Message]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _session_id_from_request(request: Request) -> str:
    """Derive a stable session ID from the Open WebUI chat-id header."""
    return (
        request.headers.get("chat-id")
        or request.headers.get("x-chat-id")
        or request.headers.get("x-session-id")
        or str(uuid.uuid4())
    )


def _last_user_message(messages: list[_Message]) -> str:
    """Return the content of the last user-role message."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content.strip()
    return ""


def _is_confirmation_reply(text: str) -> Optional[bool]:
    """
    Return True (confirmed), False (cancelled), or None (not a confirmation).
    """
    normalized = text.lower().strip().rstrip("!.")
    if normalized in _CONFIRM_YES:
        return True
    if normalized in _CONFIRM_NO:
        return False
    return None


def _has_pending_confirmation(session_id: str) -> bool:
    ctx = session_svc.get_session(session_id)
    return bool(ctx.get("pending_state"))


def _openai_completion(
    completion_id: str,
    content: str,
    finish_reason: str = "stop",
    created: int | None = None,
) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created or int(time.time()),
        "model": _MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _openai_chunk(
    completion_id: str,
    delta_content: str,
    finish_reason: str | None = None,
    created: int | None = None,
) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created or int(time.time()),
        "model": _MODEL_ID,
        "choices": [
            {
                "index": 0,
                "delta": {"content": delta_content} if delta_content else {"role": "assistant"},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/v1/models")
def list_models() -> dict[str, Any]:
    """Return a minimal model list so Open WebUI can populate its selector."""
    return {
        "object": "list",
        "data": [
            {
                "id": _MODEL_ID,
                "object": "model",
                "created": 1_700_000_000,
                "owned_by": "i4-chatbot",
            }
        ],
    }


@router.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest, request: Request):
    """
    OpenAI-compatible chat completions endpoint consumed by Open WebUI.

    Handles:
    - Normal conversation turns → run LangGraph pipeline
    - Pending-confirmation replies (ja/nein) → execute or cancel the stored tool
    - Both streaming (SSE) and non-streaming responses
    """
    session_id = _session_id_from_request(request)
    user_text = _last_user_message(req.messages)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    # ── Confirmation short-circuit ─────────────────────────────────────────────
    confirmation_reply = _is_confirmation_reply(user_text)
    if confirmation_reply is not None and _has_pending_confirmation(session_id):
        if confirmation_reply:
            success, response_text = execute_confirmed_tool(session_id)
            if not success:
                response_text = f"Fehler: {response_text}"
        else:
            cancel_pending_tool(session_id)
            response_text = "Aktion abgebrochen."

        append_chat_turns(session_id, user_text, response_text)

        if req.stream:
            def _confirm_stream():
                yield _openai_chunk(completion_id, "", created=created)
                yield _openai_chunk(completion_id, response_text, created=created)
                yield _openai_chunk(completion_id, "", finish_reason="stop", created=created)
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                _confirm_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        return _openai_completion(completion_id, response_text, created=created)

    # ── Normal graph execution ─────────────────────────────────────────────────
    if req.stream:
        return _stream_response(session_id, user_text, completion_id, created)
    return _sync_response(session_id, user_text, completion_id, created)


# ── Internal helpers for sync / streaming response generation ─────────────────

def _sync_response(
    session_id: str,
    user_text: str,
    completion_id: str,
    created: int,
) -> dict[str, Any]:
    """Run the graph synchronously and return an OpenAI completion object."""
    import queue as _queue
    import threading as _threading

    result_queue: _queue.Queue = _queue.Queue(maxsize=1)

    def worker():
        try:
            state = run_graph_with_updates(session_id, user_text)
            result_queue.put(("ok", state))
        except Exception as exc:
            result_queue.put(("error", exc))

    thread = _threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=300)

    outcome, payload = result_queue.get(timeout=5)
    if outcome == "error":
        raise payload

    final_state: dict[str, Any] = payload

    if final_state.get("requires_confirmation"):
        persist_pending_confirmation(session_id, final_state)
        response_text = final_state.get("confirmation_message") or "Bitte bestätigen (ja/nein)."
        append_chat_turns(session_id, user_text, response_text)
        return _openai_completion(completion_id, response_text, finish_reason="stop", created=created)

    response_text = final_state.get("response") or ""
    append_chat_turns(session_id, user_text, response_text)
    return _openai_completion(completion_id, response_text, created=created)


def _stream_response(
    session_id: str,
    user_text: str,
    completion_id: str,
    created: int,
) -> StreamingResponse:
    """Run the graph with status callbacks and emit OpenAI SSE chunks."""
    import queue as _queue
    import threading as _threading

    status_queue: _queue.Queue[str] = _queue.Queue()
    result_queue: _queue.Queue = _queue.Queue(maxsize=1)

    def on_status(message: str) -> None:
        status_queue.put(message)

    def worker() -> None:
        try:
            state = run_graph_with_updates(session_id, user_text, on_status=on_status)
            result_queue.put(("ok", state))
        except Exception as exc:
            result_queue.put(("error", exc))

    def event_generator():
        thread = _threading.Thread(target=worker, daemon=True)
        thread.start()

        # Emit role-opening delta first.
        yield _openai_chunk(completion_id, "", created=created)

        # Stream status messages as comment-style chunks so Open WebUI can
        # display thinking indicators without polluting the assistant text.
        while thread.is_alive() or not status_queue.empty():
            try:
                status = status_queue.get(timeout=0.1)
                # Send status as a special chunk prefixed with a non-printing
                # marker that Open WebUI ignores but clients can parse if needed.
                # We keep the visible assistant stream clean by NOT yielding
                # status text as normal content chunks.
                logger.debug("Graph status [%s]: %s", session_id, status)
            except _queue.Empty:
                continue

        # Drain any remaining status messages.
        while True:
            try:
                status_queue.get_nowait()
            except _queue.Empty:
                break

        try:
            outcome, payload = result_queue.get(timeout=5)
        except _queue.Empty:
            yield _openai_chunk(completion_id, "Zeitüberschreitung.", finish_reason="stop", created=created)
            yield "data: [DONE]\n\n"
            return

        if outcome == "error":
            err_text = f"Fehler: {payload}"
            yield _openai_chunk(completion_id, err_text, finish_reason="stop", created=created)
            yield "data: [DONE]\n\n"
            return

        final_state: dict[str, Any] = payload

        if final_state.get("requires_confirmation"):
            persist_pending_confirmation(session_id, final_state)
            response_text = final_state.get("confirmation_message") or "Bitte bestätigen (ja/nein)."
            append_chat_turns(session_id, user_text, response_text)
            yield _openai_chunk(completion_id, response_text, finish_reason="stop", created=created)
            yield "data: [DONE]\n\n"
            return

        response_text = final_state.get("response") or ""
        append_chat_turns(session_id, user_text, response_text)

        # Stream the response word-by-word for a natural typewriter effect.
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk_text = word if i == len(words) - 1 else word + " "
            yield _openai_chunk(completion_id, chunk_text, created=created)

        yield _openai_chunk(completion_id, "", finish_reason="stop", created=created)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
