"""
Tests for the OpenAI-compatible API (/v1/models and /v1/chat/completions).

All external services (Redis, LangGraph nodes, LLM) are mocked so these tests
run without any infrastructure.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.api import openai_routes

client = TestClient(app)


# ── /v1/models ────────────────────────────────────────────────────────────────

def test_list_models_returns_model_list():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) >= 1
    model_ids = [m["id"] for m in data["data"]]
    assert "i4-chatbot" in model_ids


# ── /v1/chat/completions – non-streaming ─────────────────────────────────────

def _fake_run_graph_with_updates(
    session_id: str,
    user_input: str,
    on_status=None,
) -> dict[str, Any]:
    return {
        "response": "Testantwort vom Assistenten.",
        "requires_confirmation": False,
        "intent": "query",
        "capability": "rag",
        "submodel": None,
    }


def test_chat_completions_non_streaming(monkeypatch):
    monkeypatch.setattr(openai_routes, "run_graph_with_updates", _fake_run_graph_with_updates)
    # Disable Redis calls
    monkeypatch.setattr(openai_routes, "append_chat_turns", lambda *a, **kw: None)
    monkeypatch.setattr(openai_routes, "_has_pending_confirmation", lambda sid: False)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "i4-chatbot",
            "messages": [{"role": "user", "content": "Hallo"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "i4-chatbot"
    assert len(data["choices"]) == 1
    choice = data["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert "Testantwort" in choice["message"]["content"]
    assert choice["finish_reason"] == "stop"


# ── /v1/chat/completions – streaming ─────────────────────────────────────────

def test_chat_completions_streaming(monkeypatch):
    monkeypatch.setattr(openai_routes, "run_graph_with_updates", _fake_run_graph_with_updates)
    monkeypatch.setattr(openai_routes, "append_chat_turns", lambda *a, **kw: None)
    monkeypatch.setattr(openai_routes, "_has_pending_confirmation", lambda sid: False)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "i4-chatbot",
            "messages": [{"role": "user", "content": "Hallo"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "data: [DONE]" in body
    assert "chat.completion.chunk" in body


# ── Confirmation flow ─────────────────────────────────────────────────────────

def test_confirmation_yes_reply(monkeypatch):
    """When there is a pending confirmation and user says 'ja', the tool is executed."""
    monkeypatch.setattr(openai_routes, "_has_pending_confirmation", lambda sid: True)
    monkeypatch.setattr(
        openai_routes,
        "execute_confirmed_tool",
        lambda sid: (True, "Befehl ausgeführt: ok"),
    )
    monkeypatch.setattr(openai_routes, "append_chat_turns", lambda *a, **kw: None)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "i4-chatbot",
            "messages": [{"role": "user", "content": "ja"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "Befehl ausgeführt" in data["choices"][0]["message"]["content"]


def test_confirmation_no_reply(monkeypatch):
    """When there is a pending confirmation and user says 'nein', the action is cancelled."""
    monkeypatch.setattr(openai_routes, "_has_pending_confirmation", lambda sid: True)
    monkeypatch.setattr(openai_routes, "cancel_pending_tool", lambda sid: None)
    monkeypatch.setattr(openai_routes, "append_chat_turns", lambda *a, **kw: None)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "i4-chatbot",
            "messages": [{"role": "user", "content": "nein"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "abgebrochen" in data["choices"][0]["message"]["content"]


def test_non_confirmation_word_with_pending_goes_to_graph(monkeypatch):
    """A message that is not yes/no bypasses the confirmation logic."""
    monkeypatch.setattr(openai_routes, "_has_pending_confirmation", lambda sid: True)
    monkeypatch.setattr(openai_routes, "run_graph_with_updates", _fake_run_graph_with_updates)
    monkeypatch.setattr(openai_routes, "append_chat_turns", lambda *a, **kw: None)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "i4-chatbot",
            "messages": [{"role": "user", "content": "Was ist der Status der Anlage?"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    # Should come from graph, not confirmation handler
    assert "Testantwort" in data["choices"][0]["message"]["content"]
