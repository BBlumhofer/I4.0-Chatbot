"""Agent Management tools exposed to the chatbot."""
from __future__ import annotations

from typing import Any

from app.services import agent_management_service as svc


# Registry queries

def get_all_registered_agents() -> Any:
    return svc.get_all_registered_agents()


def register_agent(
    agent_id: str,
    name: str,
    agent_type: str,
    url: str | None = None,
    ref: str | None = None,
    agents: list[str] | None = None,
    capabilities: list[str] | None = None,
    subs: list[str] | None = None,
    neighbors: list[str] | None = None,
) -> Any:
    payload = {
        "id": agent_id,
        "name": name,
        "type": agent_type,
        "url": url,
        "ref": ref,
        "agents": agents,
        "capabilities": capabilities,
        "subs": subs,
        "neighbors": neighbors,
    }
    return svc.register_agent(payload)


def unregister_agent(agent_id: str) -> Any:
    return svc.unregister_agent(agent_id)


def get_agent_details(agent_id: str) -> Any:
    return svc.get_agent_details(agent_id)


def get_agents_of_agent(agent_id: str) -> Any:
    return svc.get_agents_of_agent(agent_id)


def register_agent_at_agent(
    parent_agent_id: str,
    agent_id: str,
    name: str,
    agent_type: str,
    url: str | None = None,
    ref: str | None = None,
) -> Any:
    payload = {
        "id": agent_id,
        "name": name,
        "type": agent_type,
        "url": url,
        "ref": ref,
        "agents": [],
        "capabilities": [],
        "subs": [],
        "neighbors": [],
    }
    return svc.register_agent_at_agent(parent_agent_id, payload)


# Lifecycle

def spawn_agent(receiver: str, agent_id: str) -> Any:
    return svc.spawn_agent(receiver, agent_id)


def restart_agent(receiver: str) -> Any:
    return svc.restart_agent(receiver)


def kill_agent(receiver: str) -> Any:
    return svc.kill_agent(receiver)


# Surgery

def repeat_action(agent_id: str, conversation_id: str) -> Any:
    return svc.repeat_action(agent_id, conversation_id)


def terminate_action(agent_id: str, conversation_id: str) -> Any:
    return svc.terminate_action(agent_id, conversation_id)


def previously_action(agent_id: str, conversation_id: str) -> Any:
    return svc.previously_action(agent_id, conversation_id)


def idle_mode(agent_id: str, enable: bool) -> Any:
    return svc.idle_mode(agent_id, enable)


def change_step_state(agent_id: str, state: str, conversation_id: str) -> Any:
    return svc.change_step_state(agent_id, state, conversation_id)


def kill_step(agent_id: str, conversation_id: str) -> Any:
    return svc.kill_step(agent_id, conversation_id)


def delete_step(agent_id: str, step_id: str, conversation_id: str) -> Any:
    return svc.delete_step(agent_id, step_id, conversation_id)


# Kafka view through agent-management side

def list_kafka_topics(category: str | None = None) -> Any:
    return svc.list_kafka_topics(category)


def get_kafka_topic_info(topic_name: str) -> Any:
    return svc.get_kafka_topic_info(topic_name)


def read_kafka_messages(topic_name: str, max_messages: int = 10, timeout_seconds: int = 10) -> Any:
    return svc.read_kafka_messages(topic_name, max_messages=max_messages, timeout_seconds=timeout_seconds)


# Order / step helper

def order_storage_module_step_retrieve_amr_step(
    productid: str | None = None,
    product_type: str | None = None,
    carrier_id: str | None = None,
) -> Any:
    return svc.order_storage_module_step_retrieve_amr_step(productid, product_type, carrier_id)


AGENT_MANAGEMENT_TOOL_REGISTRY: dict[str, Any] = {
    "get_all_registered_agents": get_all_registered_agents,
    "register_agent": register_agent,
    "unregister_agent": unregister_agent,
    "get_agent_details": get_agent_details,
    "spawn_agent": spawn_agent,
    "restart_agent": restart_agent,
    "kill_agent": kill_agent,
    "get_agents_of_agent": get_agents_of_agent,
    "register_agent_at_agent": register_agent_at_agent,
    "repeat_action": repeat_action,
    "terminate_action": terminate_action,
    "previously_action": previously_action,
    "idle_mode": idle_mode,
    "change_step_state": change_step_state,
    "kill_step": kill_step,
    "delete_step": delete_step,
    "list_kafka_topics": list_kafka_topics,
    "get_kafka_topic_info": get_kafka_topic_info,
    "read_kafka_messages": read_kafka_messages,
    "order_storage_module_step_retrieve_amr_step": order_storage_module_step_retrieve_amr_step,
}
