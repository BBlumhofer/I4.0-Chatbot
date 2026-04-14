from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.api import routes


client = TestClient(app)


def test_chat_stream_emits_status_and_final(monkeypatch):
    def fake_run_graph_with_updates(session_id: str, user_input: str, on_status=None):
        if on_status:
            on_status("Analysiere Anfrage")
            on_status("Formuliere Antwort")
        return {
            "response": "Das ist eine Demo-Antwort.",
            "requires_confirmation": False,
            "intent": "demo",
            "capability": "rag",
            "submodel": None,
        }

    monkeypatch.setattr(routes, "_run_graph_with_updates", fake_run_graph_with_updates)

    response = client.post("/chat/stream", json={"message": "Hallo"})

    assert response.status_code == 200
    body = response.text
    assert "event: status" in body
    assert "Empfange Nachricht" in body
    assert "Analysiere Anfrage" in body
    assert "Formuliere Antwort" in body
    assert "event: final" in body
    assert "Das ist eine Demo-Antwort." in body
