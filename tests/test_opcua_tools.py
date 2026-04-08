"""
Tests for the OPC UA service layer and tools.

All asyncua network calls are mocked so these tests run without any
OPC UA server infrastructure.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.opcua_service import (
    OpcUaConnectionManager,
    OpcUaServerConfig,
    connection_manager,
)
from app.tools.opcua_tools import (
    browse,
    connect_to_server,
    disconnect,
    get_live_status,
    lock_server,
    read_value,
    OPCUA_TOOL_REGISTRY,
)


ENDPOINT = "opc.tcp://testserver:4840"
ENDPOINT_B = "opc.tcp://otherserver:4840"


# ── OpcUaConnectionManager ─────────────────────────────────────────────────────

class TestConnectionManager:
    def setup_method(self):
        self.mgr = OpcUaConnectionManager()

    def test_register_creates_entry(self):
        cfg = self.mgr.register(ENDPOINT, "alice", "secret")
        assert cfg.endpoint == ENDPOINT
        assert cfg.username == "alice"
        assert cfg.password == "secret"
        assert cfg.locked is False

    def test_get_returns_config(self):
        self.mgr.register(ENDPOINT, "alice", "secret")
        cfg = self.mgr.get(ENDPOINT)
        assert cfg is not None
        assert cfg.username == "alice"

    def test_get_returns_none_for_unknown(self):
        assert self.mgr.get("opc.tcp://unknown:4840") is None

    def test_get_or_default_returns_anonymous_for_unknown(self):
        cfg = self.mgr.get_or_default("opc.tcp://unknown:4840")
        assert cfg.endpoint == "opc.tcp://unknown:4840"
        assert cfg.username is None

    def test_unregister_removes_entry(self):
        self.mgr.register(ENDPOINT)
        result = self.mgr.unregister(ENDPOINT)
        assert result is True
        assert self.mgr.get(ENDPOINT) is None

    def test_unregister_unknown_returns_false(self):
        assert self.mgr.unregister("opc.tcp://unknown:4840") is False

    def test_register_multiple_servers(self):
        self.mgr.register(ENDPOINT, "alice", "secret")
        self.mgr.register(ENDPOINT_B, "bob", "pw2")
        servers = self.mgr.list_servers()
        endpoints = [s["endpoint"] for s in servers]
        assert ENDPOINT in endpoints
        assert ENDPOINT_B in endpoints

    def test_lock_and_unlock(self):
        self.mgr.register(ENDPOINT)
        assert self.mgr.is_locked(ENDPOINT) is False
        assert self.mgr.lock(ENDPOINT) is True
        assert self.mgr.is_locked(ENDPOINT) is True
        assert self.mgr.unlock(ENDPOINT) is True
        assert self.mgr.is_locked(ENDPOINT) is False

    def test_lock_unregistered_returns_false(self):
        assert self.mgr.lock("opc.tcp://unknown:4840") is False

    def test_list_servers_shows_lock_state(self):
        self.mgr.register(ENDPOINT, "alice", "pw")
        self.mgr.lock(ENDPOINT)
        servers = self.mgr.list_servers()
        entry = next(s for s in servers if s["endpoint"] == ENDPOINT)
        assert entry["locked"] is True

    def test_register_updates_existing_entry(self):
        self.mgr.register(ENDPOINT, "alice", "old")
        self.mgr.register(ENDPOINT, "alice", "new")
        assert self.mgr.get(ENDPOINT).password == "new"

    def test_make_client_applies_credentials(self):
        self.mgr.register(ENDPOINT, "user1", "pass1")
        with patch("app.services.opcua_service.OpcUaClient") as MockClient:
            client_inst = MockClient.return_value
            self.mgr._make_client(ENDPOINT)
            client_inst.set_user.assert_called_once_with("user1")
            client_inst.set_password.assert_called_once_with("pass1")

    def test_make_client_anonymous_skips_credentials(self):
        self.mgr.register(ENDPOINT)  # no credentials
        with patch("app.services.opcua_service.OpcUaClient") as MockClient:
            client_inst = MockClient.return_value
            self.mgr._make_client(ENDPOINT)
            client_inst.set_user.assert_not_called()
            client_inst.set_password.assert_not_called()


# ── connect_to_server tool ─────────────────────────────────────────────────────

class TestConnectToServer:
    @patch(
        "app.tools.opcua_tools.svc.validate_connection_sync",
        return_value={
            "endpoint": ENDPOINT,
            "username": "alice",
            "namespaces": ["urn:test"],
            "status": "connected",
        },
    )
    @patch("app.tools.opcua_tools.svc.connection_manager")
    def test_registers_and_returns_info(self, mock_mgr, mock_validate):
        result = connect_to_server(ENDPOINT, "alice", "secret")
        mock_validate.assert_called_once_with(ENDPOINT, "alice", "secret")
        mock_mgr.register.assert_called_once_with(ENDPOINT, "alice", "secret")
        assert result["status"] == "connected"
        assert result["endpoint"] == ENDPOINT

    @patch(
        "app.tools.opcua_tools.svc.validate_connection_sync",
        side_effect=Exception("Connection refused"),
    )
    @patch("app.tools.opcua_tools.svc.connection_manager")
    def test_raises_on_connection_failure(self, mock_mgr, mock_validate):
        with pytest.raises(Exception, match="Connection refused"):
            connect_to_server(ENDPOINT, "alice", "badpass")
        mock_mgr.register.assert_not_called()

    @patch(
        "app.tools.opcua_tools.svc.validate_connection_sync",
        return_value={"endpoint": ENDPOINT, "status": "connected", "namespaces": [], "username": "<anonymous>"},
    )
    @patch("app.tools.opcua_tools.svc.connection_manager")
    def test_anonymous_connect(self, mock_mgr, mock_validate):
        connect_to_server(ENDPOINT)
        mock_validate.assert_called_once_with(ENDPOINT, None, None)
        mock_mgr.register.assert_called_once_with(ENDPOINT, None, None)


# ── disconnect tool ────────────────────────────────────────────────────────────

class TestDisconnect:
    @patch(
        "app.tools.opcua_tools.svc.connection_manager"
    )
    def test_disconnects_registered_server(self, mock_mgr):
        mock_mgr.unregister.return_value = True
        result = disconnect(ENDPOINT)
        mock_mgr.unregister.assert_called_once_with(ENDPOINT)
        assert result["status"] == "disconnected"
        assert result["endpoint"] == ENDPOINT

    @patch("app.tools.opcua_tools.svc.connection_manager")
    def test_disconnect_not_registered(self, mock_mgr):
        mock_mgr.unregister.return_value = False
        result = disconnect(ENDPOINT)
        assert result["status"] == "not_registered"


# ── browse tool ────────────────────────────────────────────────────────────────

class TestBrowse:
    @patch(
        "app.tools.opcua_tools.svc.browse_nodes_sync",
        return_value=[
            {"node_id": "ns=2;i=1", "display_name": "Motor", "node_class": "Object"},
            {"node_id": "ns=2;i=2", "display_name": "Speed", "node_class": "Variable"},
        ],
    )
    def test_returns_children(self, mock_browse):
        result = browse(ENDPOINT)
        mock_browse.assert_called_once_with(ENDPOINT, None)
        assert len(result) == 2
        assert result[0]["display_name"] == "Motor"

    @patch(
        "app.tools.opcua_tools.svc.browse_nodes_sync",
        return_value=[],
    )
    def test_browse_specific_node(self, mock_browse):
        browse(ENDPOINT, node_id="ns=2;i=5")
        mock_browse.assert_called_once_with(ENDPOINT, "ns=2;i=5")

    @patch(
        "app.tools.opcua_tools.svc.browse_nodes_sync",
        return_value=[],
    )
    def test_browse_empty_result(self, mock_browse):
        result = browse(ENDPOINT)
        assert result == []


# ── lock_server tool ───────────────────────────────────────────────────────────

class TestLockServer:
    @patch("app.tools.opcua_tools.svc.connection_manager")
    def test_lock_registered_server(self, mock_mgr):
        mock_mgr.lock.return_value = True
        result = lock_server(ENDPOINT)
        mock_mgr.lock.assert_called_once_with(ENDPOINT)
        assert result["locked"] is True
        assert result["status"] == "locked"

    @patch("app.tools.opcua_tools.svc.connection_manager")
    def test_lock_unregistered_server(self, mock_mgr):
        mock_mgr.lock.return_value = False
        result = lock_server(ENDPOINT)
        assert result["locked"] is False
        assert result["status"] == "not_registered"


# ── get_live_status tool ───────────────────────────────────────────────────────

class TestGetLiveStatus:
    @patch(
        "app.tools.opcua_tools.svc.get_live_status_sync",
        return_value={
            "endpoint": ENDPOINT,
            "node_id": "ns=2;i=42",
            "value": 100,
            "status": "Good",
            "source_timestamp": "2026-01-01T00:00:00",
        },
    )
    def test_returns_data_value(self, mock_svc):
        result = get_live_status(ENDPOINT, "ns=2;i=42")
        mock_svc.assert_called_once_with(ENDPOINT, "ns=2;i=42")
        assert result["value"] == 100
        assert result["endpoint"] == ENDPOINT


# ── read_value tool ────────────────────────────────────────────────────────────

class TestReadValue:
    @patch("app.tools.opcua_tools.svc.read_node_value_sync", return_value=42.5)
    def test_returns_scalar(self, mock_svc):
        result = read_value(ENDPOINT, "ns=2;i=10")
        mock_svc.assert_called_once_with(ENDPOINT, "ns=2;i=10")
        assert result == 42.5


# ── OPCUA_TOOL_REGISTRY ────────────────────────────────────────────────────────

class TestOpcuaToolRegistry:
    def test_all_expected_tools_present(self):
        expected = {"connect_to_server", "disconnect", "browse", "lock_server", "get_live_status", "read_value"}
        assert expected.issubset(set(OPCUA_TOOL_REGISTRY.keys()))

    def test_all_values_are_callable(self):
        for name, fn in OPCUA_TOOL_REGISTRY.items():
            assert callable(fn), f"{name} should be callable"


# ── select_tool_generic integration ───────────────────────────────────────────

class TestSelectToolGenericOpcua:
    """
    Verify that graph/nodes.py routes OPC UA intents to the correct tools
    and passes the correct tool_args.
    """

    def _run_select(self, intent: str, entities: dict, resolved: dict | None = None):
        from app.graph.nodes import select_tool_generic
        from app.graph.state import AgentState

        state: AgentState = {
            "session_id": "s1",
            "user_input": "test",
            "capability": "opcua",
            "intent": intent,
            "entities": entities,
            "resolved_entities": resolved or {},
            "requires_confirmation": False,
        }
        return select_tool_generic(state)

    def test_connect_to_server_routes(self):
        result = self._run_select(
            "connect_to_server",
            {"endpoint": ENDPOINT, "username": "alice", "password": "pw"},
        )
        assert result["tool_name"] == "connect_to_server"
        assert result["tool_args"]["endpoint"] == ENDPOINT
        assert result["tool_args"]["username"] == "alice"
        assert result["tool_args"]["password"] == "pw"
        assert result["requires_confirmation"] is False

    def test_disconnect_requires_confirmation(self):
        result = self._run_select("disconnect", {"endpoint": ENDPOINT})
        assert result["tool_name"] == "disconnect"
        assert result["requires_confirmation"] is True
        assert "confirmation_message" in result
        assert ENDPOINT in result["confirmation_message"]

    def test_browse_routes_without_node_id(self):
        result = self._run_select("browse", {"endpoint": ENDPOINT})
        assert result["tool_name"] == "browse"
        assert result["tool_args"]["endpoint"] == ENDPOINT
        assert result["tool_args"].get("node_id") is None

    def test_browse_routes_with_node_id(self):
        result = self._run_select("browse", {"endpoint": ENDPOINT, "node_id": "ns=2;i=5"})
        assert result["tool_args"]["node_id"] == "ns=2;i=5"

    def test_lock_server_routes(self):
        result = self._run_select("lock_server", {"endpoint": ENDPOINT})
        assert result["tool_name"] == "lock_server"
        assert result["tool_args"]["endpoint"] == ENDPOINT

    def test_read_value_routes(self):
        result = self._run_select("read_value", {"endpoint": ENDPOINT, "node_id": "ns=2;i=7"})
        assert result["tool_name"] == "read_value"
        assert result["tool_args"]["node_id"] == "ns=2;i=7"

    def test_default_intent_maps_to_get_live_status(self):
        result = self._run_select("some_unknown_intent", {"endpoint": ENDPOINT, "node_id": "ns=2;i=1"})
        assert result["tool_name"] == "get_live_status"

    def test_endpoint_falls_back_to_settings(self):
        result = self._run_select("get_live_status", {"node_id": "ns=2;i=1"})
        from app.config import settings
        assert result["tool_args"]["endpoint"] == settings.opcua_endpoint
