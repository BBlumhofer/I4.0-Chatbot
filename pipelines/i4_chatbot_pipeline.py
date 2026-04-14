"""
title: I4.0 Produktionsanlagen-Assistent
author: I4.0 Project
description: |
  Connects Open WebUI to the I4.0 LangGraph production-plant chatbot.

  Handles Neo4j / AAS submodel queries, OPC-UA status reads, RAG document
  search, and Kafka plant commands (with confirmation workflow).

  Architecture:
    Open WebUI → Pipelines (this file, port 9099) → FastAPI/LangGraph (port 8000)

  The pipeline calls the existing /chat/stream SSE endpoint so that
  every processing step ("Analysiere Anfrage", "Loese Entitaeten auf", …)
  is forwarded to Open WebUI as a live status indicator.
  Confirmation requests (ja / nein) are routed to /chat/confirm automatically.

version: 1.0
license: MIT
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Words that count as an affirmative / negative confirmation reply.
_CONFIRM_YES = {"ja", "yes", "j", "y", "bestätigen", "bestaetigen", "ok", "okay"}
_CONFIRM_NO = {"nein", "no", "n", "abbrechen", "cancel", "abort"}


class Pipeline:
    """
    Open WebUI Pipeline – I4.0 Produktionsanlagen-Assistent.

    This class is auto-discovered by the Pipelines service.  Every public
    attribute of ``Valves`` becomes a configurable knob in the Open WebUI
    Admin ▸ Pipelines settings panel, so operators can adjust the backend URL
    or timeout without rebuilding the container.
    """

    class Valves(BaseModel):
        """Runtime-configurable settings for this pipeline."""

        API_BASE_URL: str = os.getenv("API_BASE_URL", "http://api:8000")
        """Base URL of the I4.0 FastAPI backend (no trailing slash)."""

        API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "300"))
        """Maximum seconds to wait for the LangGraph pipeline to finish."""

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def __init__(self) -> None:
        # Model ID and display name shown in Open WebUI's model selector.
        self.id = "i4-chatbot"
        self.name = "I4.0 Produktionsanlagen-Assistent"
        self.valves = self.Valves()

        # Track sessions that are waiting for a confirmation reply.
        # Stored in memory so it survives across multiple requests within the
        # same container instance; Redis holds the actual pending tool state.
        self._pending_sessions: set[str] = set()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _last_user_message(self, messages: list[dict]) -> str:
        """Return the content of the most recent user-role message."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return str(msg.get("content", "")).strip()
        return ""

    def _is_confirmation_reply(self, text: str) -> Optional[bool]:
        """
        Return True (confirmed), False (cancelled), or None (not a reply).
        """
        normalized = text.lower().strip().rstrip("!.")
        if normalized in _CONFIRM_YES:
            return True
        if normalized in _CONFIRM_NO:
            return False
        return None

    async def _emit_status(
        self,
        emitter: Optional[Callable[[Any], Awaitable[None]]],
        description: str,
        done: bool = False,
    ) -> None:
        """Forward a status event to Open WebUI (shown as a spinner line)."""
        if emitter:
            await emitter(
                {
                    "type": "status",
                    "data": {"description": description, "done": done},
                }
            )

    # ── Confirmation path ──────────────────────────────────────────────────────

    async def _handle_confirmation(
        self,
        session_id: str,
        confirmed: bool,
        event_emitter: Optional[Callable[[Any], Awaitable[None]]],
    ) -> AsyncGenerator[str, None]:
        """Call /chat/confirm and yield the API response text."""
        await self._emit_status(event_emitter, "Bearbeite Bestätigung…")

        payload = {"session_id": session_id, "confirmed": confirmed}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{self.valves.API_BASE_URL}/chat/confirm",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "")
            except httpx.HTTPStatusError as exc:
                text = f"Fehler bei der Bestätigung: {exc.response.status_code}"
            except Exception as exc:
                logger.exception("Confirmation request failed: %s", exc)
                text = "Ein Fehler ist aufgetreten."

        self._pending_sessions.discard(session_id)
        await self._emit_status(event_emitter, "Abgeschlossen", done=True)
        yield text

    # ── Streaming chat path ────────────────────────────────────────────────────

    async def _stream_chat(
        self,
        session_id: str,
        user_message: str,
        event_emitter: Optional[Callable[[Any], Awaitable[None]]],
    ) -> AsyncGenerator[str, None]:
        """
        Call the /chat/stream SSE endpoint and translate events into Open WebUI
        status indicators + streamed text chunks.
        """
        payload = {"message": user_message, "session_id": session_id}

        await self._emit_status(event_emitter, "Verbinde mit I4.0 Backend…")

        try:
            async with httpx.AsyncClient(timeout=self.valves.API_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{self.valves.API_BASE_URL}/chat/stream",
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    current_event: str = ""

                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip()
                        if not line:
                            current_event = ""
                            continue

                        if line.startswith("event: "):
                            current_event = line[7:].strip()
                            continue

                        if not line.startswith("data: "):
                            continue

                        try:
                            data: dict = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        if current_event == "status":
                            # Forward backend status messages as Open WebUI
                            # status spinners so the user sees live progress.
                            await self._emit_status(
                                event_emitter, data.get("message", "")
                            )

                        elif current_event == "chunk":
                            # Partial answer text – stream to the user.
                            yield data.get("delta", "")

                        elif current_event == "confirmation":
                            # The backend needs user confirmation (e.g. Kafka).
                            self._pending_sessions.add(session_id)
                            await self._emit_status(
                                event_emitter,
                                "Bestätigung erforderlich – bitte mit 'ja' oder 'nein' antworten",
                            )
                            yield data.get("message", "")

                        elif current_event == "final":
                            if data.get("requires_confirmation"):
                                self._pending_sessions.add(session_id)
                            await self._emit_status(
                                event_emitter, "Abgeschlossen", done=True
                            )

                        elif current_event == "error":
                            await self._emit_status(
                                event_emitter, "Fehler aufgetreten", done=True
                            )
                            yield f"\n\n⚠️ {data.get('message', 'Unbekannter Fehler')}"

        except httpx.TimeoutException:
            await self._emit_status(event_emitter, "Zeitüberschreitung", done=True)
            yield "\n\n⚠️ Die Anfrage hat zu lange gedauert. Bitte versuche es erneut."
        except httpx.HTTPStatusError as exc:
            logger.error("Backend HTTP error %s for session %s", exc.response.status_code, session_id)
            await self._emit_status(event_emitter, "Backend-Fehler", done=True)
            yield f"\n\n⚠️ Backend-Fehler ({exc.response.status_code})."
        except Exception as exc:
            logger.exception("Unexpected pipeline error for session %s: %s", session_id, exc)
            await self._emit_status(event_emitter, "Interner Fehler", done=True)
            yield "\n\n⚠️ Ein interner Fehler ist aufgetreten."

    # ── Main entry point ───────────────────────────────────────────────────────

    async def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: list[dict],
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Main pipeline handler called by the Open WebUI Pipelines service.

        The Pipelines framework calls this method with the following keyword
        arguments (Open WebUI ≥ 0.3 API):
          - ``user_message``: the last user-role message text
          - ``model_id``:     the selected model identifier
          - ``messages``:     the full conversation history
          - ``body``:         the raw request body

        The method is an async generator: it ``yield``s plain-text chunks that
        Open WebUI assembles into the assistant's response.  Status events are
        sent via ``__event_emitter__`` and shown as live spinner lines above the
        message.
        """
        # Open WebUI sends a stable chat-id for the whole conversation.
        session_id: str = body.get("chat_id") or str(uuid.uuid4())

        if not user_message:
            yield "Bitte gib eine Nachricht ein."
            return

        # ── Confirmation short-circuit ─────────────────────────────────────────
        if session_id in self._pending_sessions:
            reply = self._is_confirmation_reply(user_message)
            if reply is not None:
                async for chunk in self._handle_confirmation(
                    session_id, reply, __event_emitter__
                ):
                    yield chunk
                return

        # ── Normal conversation ────────────────────────────────────────────────
        async for chunk in self._stream_chat(session_id, user_message, __event_emitter__):
            yield chunk
