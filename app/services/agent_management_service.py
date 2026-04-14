"""
Agent Management / Agent Registry service.

Provides thin HTTP wrappers for registry and lifecycle style endpoints.
The API surface is intentionally tolerant: unexpected payload shapes are
returned as-is to keep the chatbot resilient to backend changes.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, parse, request

from app.config import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return settings.agent_registry_url.rstrip("/")


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if settings.agent_registry_key:
        # Send both common header variants for maximum compatibility.
        headers["X-API-Key"] = settings.agent_registry_key
        headers["Authorization"] = f"Bearer {settings.agent_registry_key}"
    return headers


def _request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> Any:
    url = f"{_base_url()}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"

    body_bytes = None
    if payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=body_bytes, method=method.upper())
    for key, value in _headers().items():
        req.add_header(key, value)

    timeout = float(settings.agent_registry_timeout_seconds)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8") if resp.readable() else ""
            if not raw:
                return {"status": "ok", "http_status": getattr(resp, "status", 200)}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"status": "ok", "raw": raw}
    except error.HTTPError as exc:
        # Try graceful fallbacks for common registry path differences on 404
        raw_error = exc.read().decode("utf-8") if exc.fp else ""
        detail: Any
        try:
            detail = json.loads(raw_error) if raw_error else {"message": exc.reason}
        except json.JSONDecodeError:
            detail = {"message": raw_error or str(exc.reason)}

        logger.warning("Agent registry HTTP error %s on %s: %s", exc.code, path, detail)

        # If the path is the canonical /agents collection and we received 404,
        # attempt a few common alternative prefixes before giving up.
        if exc.code == 404 and method.upper() == "GET" and path.rstrip("/") in ("agents", "/agents"):
            alternatives = ["/api/agents", "/v1/agents", "/api/v1/agents"]
            for alt in alternatives:
                try:
                    return _request_json(method, alt, payload=payload, query=query)
                except RuntimeError:
                    # continue to next alternative
                    continue

            # If still not found, return a non-exception result indicating not found.
            return {"status": "not_found", "http_status": 404, "detail": detail}

        # For other HTTP errors, raise to let callers detect failures.
        raise RuntimeError(f"Agent registry request failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        logger.warning("Agent registry URL error on %s: %s", path, exc.reason)
        raise RuntimeError(f"Agent registry not reachable: {exc.reason}") from exc


def get_all_registered_agents() -> Any:
    return _request_json("GET", "/agent")


def register_agent(agent_payload: dict[str, Any]) -> Any:
    return _request_json("POST", "/agent", payload=agent_payload)


def unregister_agent(agent_id: str) -> Any:
    # API expects a DELETE to /agent with a minimal identification payload
    return _request_json("DELETE", "/agent", payload={"id": agent_id})


def get_agent_details(agent_id: str) -> Any:
    return _request_json("GET", f"/agent/{agent_id}")


def get_agents_of_agent(agent_id: str) -> Any:
    return _request_json("GET", f"/agent/{agent_id}/agents")


def register_agent_at_agent(parent_agent_id: str, agent_payload: dict[str, Any]) -> Any:
    return _request_json("POST", f"/agent/{parent_agent_id}/agent", payload=agent_payload)


def spawn_agent(receiver: str, agent_id: str) -> Any:
    # OpenAPI defines spawn at /agent/{agent_id}/spawn and requires a key query param
    query = {"key": settings.agent_registry_key} if settings.agent_registry_key else None
    return _request_json(
        "POST",
        f"/agent/{agent_id}/spawn",
        payload={"receiver": receiver, "agent_to_spawn": agent_id},
        query=query,
    )


def restart_agent(agent_id: str, payload: dict[str, Any] | None = None) -> Any:
    query = {"key": settings.agent_registry_key} if settings.agent_registry_key else None
    return _request_json("POST", f"/agent/{agent_id}/restart", payload=payload or {}, query=query)


def kill_agent(agent_id: str, payload: dict[str, Any] | None = None) -> Any:
    query = {"key": settings.agent_registry_key} if settings.agent_registry_key else None
    return _request_json("DELETE", f"/agent/{agent_id}/kill", payload=payload or {}, query=query)


def repeat_action(agent_id: str, conversation_id: str) -> Any:
    return _request_json(
        "POST",
        "/surgery/repeat-action",
        payload={"agent_id": agent_id, "conversation_id": conversation_id},
    )


def terminate_action(agent_id: str, conversation_id: str) -> Any:
    return _request_json(
        "POST",
        "/surgery/terminate-action",
        payload={"agent_id": agent_id, "conversation_id": conversation_id},
    )


def previously_action(agent_id: str, conversation_id: str) -> Any:
    return _request_json(
        "POST",
        "/surgery/previously-action",
        payload={"agent_id": agent_id, "conversation_id": conversation_id},
    )


def idle_mode(agent_id: str, enable: bool) -> Any:
    return _request_json(
        "POST",
        "/surgery/idle-mode",
        payload={"agent_id": agent_id, "enable": enable},
    )


def change_step_state(agent_id: str, state: str, conversation_id: str) -> Any:
    return _request_json(
        "POST",
        "/surgery/change-step-state",
        payload={"agent_id": agent_id, "state": state, "conversation_id": conversation_id},
    )


def kill_step(agent_id: str, conversation_id: str) -> Any:
    return _request_json(
        "POST",
        "/surgery/kill-step",
        payload={"agent_id": agent_id, "conversation_id": conversation_id},
    )


def delete_step(agent_id: str, step_id: str, conversation_id: str) -> Any:
    return _request_json(
        "POST",
        "/surgery/delete-step",
        payload={"agent_id": agent_id, "step_id": step_id, "conversation_id": conversation_id},
    )


def list_kafka_topics(category: str | None = None) -> Any:
    return _request_json("GET", "/kafka/topics", query={"category": category} if category else None)


def get_kafka_topic_info(topic_name: str) -> Any:
    return _request_json("GET", f"/kafka/topics/{topic_name}")


def read_kafka_messages(topic_name: str, max_messages: int = 10, timeout_seconds: int = 10) -> Any:
    return _request_json(
        "POST",
        "/kafka/messages/read",
        payload={
            "topic_name": topic_name,
            "max_messages": max_messages,
            "timeout_seconds": timeout_seconds,
        },
    )


def order_storage_module_step_retrieve_amr_step(
    productid: str | None,
    product_type: str | None,
    carrier_id: str | None,
) -> Any:
    input_parameter: dict[str, Any] = {}
    if productid:
        input_parameter["ProductID"] = productid
    if product_type:
        input_parameter["ProductType"] = product_type
    if carrier_id:
        input_parameter["CarrierID"] = carrier_id

    return _request_json(
        "POST",
        "/order/storage/retrieve-amr-step",
        payload={"receiver": "RH2", "input_parameter": input_parameter},
    )
