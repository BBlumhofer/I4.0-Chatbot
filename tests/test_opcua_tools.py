"""Tests for OPC UA v4 tool bindings and routing."""
from __future__ import annotations

from unittest.mock import patch

from app.tools.opcua_tools import OPCUA_TOOL_REGISTRY


ENDPOINT = "opc.tcp://testserver:4842"


def test_registry_contains_v4_tools():
    expected = {
        "connect_to_server",
        "disconnect",
        "list_skills",
        "read_component_parameters",
        "read_component_monitoring",
        "read_component_attributes",
        "read_skill_parameters",
        "read_skill_monitoring",
        "write_skill_parameter",
        "execute_skill",
    }
    assert expected.issubset(set(OPCUA_TOOL_REGISTRY.keys()))


def test_connect_delegates_to_service():
    with patch("app.tools.opcua_tools.svc.connect_server_sync", return_value={"status": "connected"}) as mock_fn:
        result = OPCUA_TOOL_REGISTRY["connect_to_server"](ENDPOINT, "operator", "operator")
    mock_fn.assert_called_once_with(ENDPOINT, "operator", "operator")
    assert result["status"] == "connected"


def test_read_skill_parameters_delegates_to_service():
    payload = {"parameters": [{"name": "Speed", "value": 10}]}
    with patch("app.tools.opcua_tools.svc.read_skill_parameters_sync", return_value=payload) as mock_fn:
        result = OPCUA_TOOL_REGISTRY["read_skill_parameters"](
            endpoint=ENDPOINT,
            machine_name="MachineA",
            component_name="Robot1",
            skill_name="Move",
            scope="execution",
        )
    mock_fn.assert_called_once_with(
        endpoint=ENDPOINT,
        machine_name="MachineA",
        skill_name="Move",
        component_name="Robot1",
        scope="execution",
    )
    assert result == payload


def test_execute_skill_delegates_to_service():
    payload = {"status": "ok", "action": "start"}
    with patch("app.tools.opcua_tools.svc.execute_skill_sync", return_value=payload) as mock_fn:
        result = OPCUA_TOOL_REGISTRY["execute_skill"](
            endpoint=ENDPOINT,
            machine_name="MachineA",
            skill_name="Move",
            action="start",
        )
    mock_fn.assert_called_once()
    assert result["status"] == "ok"


def test_select_tool_generic_routes_list_skills():
    from app.graph.nodes import select_tool_generic

    state = {
        "session_id": "s1",
        "user_input": "zeige skills",
        "capability": "opcua",
        "intent": "list_skills",
        "entities": {"endpoint": ENDPOINT, "machine_name": "MachineA"},
        "resolved_entities": {},
        "requires_confirmation": False,
    }

    result = select_tool_generic(state)
    assert result["tool_name"] == "list_skills"
    assert result["tool_args"]["machine_name"] == "MachineA"


def test_select_tool_generic_requires_confirmation_for_write():
    from app.graph.nodes import select_tool_generic

    state = {
        "session_id": "s1",
        "user_input": "setze parameter",
        "capability": "opcua",
        "intent": "write_skill_parameter",
        "entities": {
            "endpoint": ENDPOINT,
            "machine_name": "MachineA",
            "skill_name": "Move",
            "parameter_name": "Speed",
            "value": 42,
        },
        "resolved_entities": {},
        "requires_confirmation": False,
    }

    result = select_tool_generic(state)
    assert result["tool_name"] == "write_skill_parameter"
    assert result["requires_confirmation"] is True


def test_select_tool_generic_requires_confirmation_for_execute():
    from app.graph.nodes import select_tool_generic

    state = {
        "session_id": "s1",
        "user_input": "fuehre skill aus",
        "capability": "opcua",
        "intent": "execute_skill",
        "entities": {
            "endpoint": ENDPOINT,
            "machine_name": "MachineA",
            "skill_name": "Move",
            "action": "start",
        },
        "resolved_entities": {},
        "requires_confirmation": False,
    }

    result = select_tool_generic(state)
    assert result["tool_name"] == "execute_skill"
    assert result["requires_confirmation"] is True
