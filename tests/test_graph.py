"""
Unit tests for the LangGraph state machine and graph nodes.

All external services (Neo4j, OPC UA, Kafka, Redis, LLM) are mocked so these
tests run without any infrastructure.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.graph.state import AgentState
from app.graph.nodes import (
    interpret_input,
    resolve_entities,
    route_capability,
    validate_submodel,
    select_tool_neo4j,
    select_tool_generic,
    execute_tool,
    generate_response,
    check_confirmation,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _state(**kwargs: Any) -> AgentState:
    """Build a minimal AgentState for testing."""
    base: AgentState = {
        "session_id": "test-session",
        "user_input": "Test",
        "entities": {},
        "resolved_entities": {},
        "requires_confirmation": False,
    }
    base.update(kwargs)
    return base


# ── interpret_input ────────────────────────────────────────────────────────────

class TestInterpretInput:
    @patch("app.graph.nodes.session_svc.get_session", return_value={})
    @patch(
        "app.graph.nodes.llm.interpret",
        return_value={
            "intent": "get_steps",
            "capability": "neo4j",
            "submodel": "ProductionPlan",
            "entities": {"asset": "Lagermodul"},
        },
    )
    def test_populates_state(self, mock_llm, mock_session):
        state = _state(user_input="Welche Schritte wurden heute ausgeführt?")
        result = interpret_input(state)

        assert result["intent"] == "get_steps"
        assert result["capability"] == "neo4j"
        assert result["submodel"] == "ProductionPlan"
        assert result["entities"] == {"asset": "Lagermodul"}
        assert result["error"] is None

    @patch("app.graph.nodes.session_svc.get_session", return_value={})
    @patch(
        "app.graph.nodes.llm.interpret",
        return_value={
            "intent": "explain_led",
            "capability": "rag",
            "submodel": None,
            "entities": {},
        },
    )
    def test_rag_capability(self, mock_llm, mock_session):
        state = _state(user_input="Was bedeuten die blauen LEDs?")
        result = interpret_input(state)
        assert result["capability"] == "rag"
        assert result["submodel"] is None

    @patch("app.graph.nodes.session_svc.get_session", return_value={})
    @patch("app.graph.nodes.llm.interpret", side_effect=Exception("LLM offline"))
    def test_fallback_on_llm_error(self, mock_llm, mock_session):
        """interpret_input should not raise; it returns a safe fallback."""
        state = _state(user_input="anything")
        result = interpret_input(state)
        assert result["capability"] == "rag"
        assert result["intent"] == "unknown"


# ── resolve_entities ───────────────────────────────────────────────────────────

class TestResolveEntities:
    @patch("app.graph.nodes.session_svc.update_session")
    @patch(
        "app.graph.nodes.neo4j_svc.find_asset_by_name",
        return_value=[{"id": "p24", "name": "Lagermodul", "idShort": "Storage", "type": "resource"}],
    )
    def test_resolves_asset(self, mock_find, mock_update):
        state = _state(entities={"asset": "Lagermodul"})
        result = resolve_entities(state)
        assert result["resolved_entities"]["asset_id"] == "p24"
        assert result["resolved_entities"]["asset_name"] == "Lagermodul"

    @patch("app.graph.nodes.neo4j_svc.find_asset_by_name", return_value=[])
    def test_no_match(self, mock_find):
        state = _state(entities={"asset": "unknown"})
        result = resolve_entities(state)
        assert "asset_id" not in result["resolved_entities"]

    @patch(
        "app.graph.nodes.neo4j_svc.find_asset_by_name",
        return_value=[
            {"id": "p1", "name": "Modul A", "idShort": "A", "type": "resource"},
            {"id": "p2", "name": "Modul B", "idShort": "B", "type": "resource"},
        ],
    )
    def test_ambiguous_returns_disambiguation(self, mock_find):
        state = _state(entities={"asset": "Modul"})
        result = resolve_entities(state)
        assert "disambiguation" in result["resolved_entities"]
        assert len(result["resolved_entities"]["disambiguation"]) == 2

    @patch("app.graph.nodes.session_svc.get_session", return_value={"current_asset": "p99"})
    def test_falls_back_to_session(self, mock_session):
        state = _state(entities={})
        result = resolve_entities(state)
        assert result["resolved_entities"].get("asset_id") == "p99"

    @patch("app.graph.nodes.neo4j_svc.find_asset_by_name", side_effect=Exception("DB down"))
    def test_handles_db_error_gracefully(self, mock_find):
        state = _state(entities={"asset": "something"})
        result = resolve_entities(state)
        assert result["resolved_entities"] == {}

    @patch(
        "app.graph.nodes.neo4j_svc.find_asset_by_name",
        return_value=[{"id": "https://smartfactory.de/asset/P17", "name": "P17", "idShort": "P17", "type": "resource"}],
    )
    def test_extracts_explicit_p_id_from_user_input(self, mock_find):
        state = _state(entities={}, user_input="Zeig Skills fuer P17")
        result = resolve_entities(state)
        assert result["resolved_entities"]["asset_id"] == "https://smartfactory.de/asset/P17"

    @patch("app.graph.nodes.neo4j_svc.find_asset_by_name", return_value=[])
    def test_extracts_explicit_p_id_as_deterministic_fallback(self, mock_find):
        state = _state(entities={}, user_input="Status von P17")
        result = resolve_entities(state)
        assert result["resolved_entities"]["asset_id"] == "https://smartfactory.de/asset/P17"

    @patch("app.graph.nodes.session_svc.get_session", return_value={})
    @patch("app.graph.nodes.neo4j_svc.find_asset_by_name")
    def test_extracts_hyphenated_module_hint_from_user_input(self, mock_find, mock_session):
        def _side_effect(name: str):
            if str(name).lower() == "ca-module":
                return [
                    {
                        "id": "https://smartfactory.de/asset/P17",
                        "name": "CA-Module",
                        "idShort": "P17",
                        "type": "resource",
                    }
                ]
            return []

        mock_find.side_effect = _side_effect

        state = _state(entities={}, user_input="Welche Skills hat das CA-Module")
        result = resolve_entities(state)
        assert result["resolved_entities"]["asset_id"] == "https://smartfactory.de/asset/P17"


# ── route_capability ───────────────────────────────────────────────────────────

class TestRouteCapability:
    @pytest.mark.parametrize("cap", ["neo4j", "opcua", "rag", "kafka"])
    def test_valid_capabilities(self, cap):
        state = _state(capability=cap)
        result = route_capability(state)
        assert result["capability"] == cap

    def test_invalid_falls_back_to_rag(self):
        state = _state(capability="unknown_cap")
        result = route_capability(state)
        assert result["capability"] == "rag"

    def test_missing_falls_back_to_rag(self):
        state = _state()
        result = route_capability(state)
        assert result["capability"] == "rag"

    def test_skill_endpoint_query_forces_neo4j(self):
        state = _state(capability="opcua", user_input="Zeige Skill Endpoint von P17")
        result = route_capability(state)
        assert result["capability"] == "neo4j"

    def test_skill_listing_query_with_asset_forces_neo4j(self):
        state = _state(
            capability="rag",
            query_mode="exploratory",
            user_input="Welche Skills hat das CA-Module",
            resolved_entities={"asset_id": "https://smartfactory.de/asset/P17"},
        )
        result = route_capability(state)
        assert result["capability"] == "neo4j"


# ── validate_submodel ──────────────────────────────────────────────────────────

class TestValidateSubmodel:
    @patch("app.graph.nodes.session_svc.update_session")
    def test_valid_submodel_passes_through(self, mock_update):
        state = _state(submodel="ProductionPlan")
        result = validate_submodel(state)
        assert result["submodel"] == "ProductionPlan"

    @patch("app.graph.nodes.session_svc.update_session")
    def test_invalid_submodel_falls_back(self, mock_update):
        state = _state(submodel="DoesNotExist")
        result = validate_submodel(state)
        assert result["submodel"] == "Structure"

    @patch("app.graph.nodes.session_svc.update_session")
    def test_none_submodel_falls_back(self, mock_update):
        state = _state(submodel=None)
        result = validate_submodel(state)
        assert result["submodel"] == "Structure"

    @patch("app.graph.nodes.session_svc.update_session")
    def test_skill_query_infers_skills_submodel(self, mock_update):
        state = _state(capability="neo4j", submodel=None, user_input="Zeige Skills von P17")
        result = validate_submodel(state)
        assert result["submodel"] == "Skills"


# ── select_tool_neo4j ──────────────────────────────────────────────────────────

class TestSelectToolNeo4j:
    def test_production_plan_get_steps(self):
        state = _state(
            submodel="ProductionPlan",
            intent="get_steps",
            resolved_entities={"asset_id": "p24"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_steps"
        assert result["tool_args"]["asset_id"] == "p24"

    def test_fallback_to_get_properties(self):
        state = _state(
            submodel="Nameplate",
            intent="some_unknown_intent",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_properties"

    def test_no_confirmation_for_neo4j(self):
        state = _state(
            submodel="Structure",
            intent="get_parts",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["requires_confirmation"] is False

    def test_soft_mapping_nameplate_date(self):
        state = _state(
            submodel="Nameplate",
            intent="wann ist das hergestellt",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_date_of_manufacture"

    def test_soft_mapping_nameplate_overview(self):
        state = _state(
            submodel="Nameplate",
            intent="zeige typschild daten",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_nameplate"

    def test_direct_tool_name_has_priority(self):
        state = _state(
            submodel="Nameplate",
            intent="get_software_version",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_software_version"

    def test_soft_mapping_skills_endpoint(self):
        state = _state(
            submodel="Skills",
            intent="zeige mir den skill endpoint",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_skill_endpoints"

    def test_soft_mapping_skills_input_parameters(self):
        state = _state(
            submodel="Skills",
            intent="welche inputparameter braucht der skill",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "list_skill_input_parameters"

    def test_soft_mapping_agents_connected_nodes(self):
        state = _state(
            submodel="Agents",
            intent="zeige agent topologie und knoten",
            resolved_entities={"asset_id": "RH2"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "list_connected_node_properties"
        assert result["tool_args"]["shell_id"] == "RH2"

    def test_soft_mapping_exhibition_insights_today_trucks(self):
        state = _state(
            submodel="ExhibitionInsights",
            intent="wie viele lkws wurden heute produziert",
            resolved_entities={"asset_id": "P17"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_today_truck_production"

    def test_forwards_skill_name_to_tool_args(self):
        state = _state(
            submodel="Skills",
            intent="get_skill_endpoints",
            resolved_entities={"asset_id": "p1", "skill_name": "Store"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_args"]["skill_name"] == "Store"

    def test_skills_endpoint_query_overrides_wrong_intent(self):
        state = _state(
            submodel="Skills",
            intent="read_skill_parameters",
            user_input="Zeige Skill Endpoint fuer P17",
            resolved_entities={"asset_id": "p1"},
        )
        result = select_tool_neo4j(state)
        assert result["tool_name"] == "get_skill_endpoints"


# ── select_tool_generic ────────────────────────────────────────────────────────

class TestSelectToolGeneric:
    def test_rag_uses_search_docs(self):
        state = _state(capability="rag", intent="explain_led", user_input="Was bedeuten LEDs?")
        result = select_tool_generic(state)
        assert result["tool_name"] == "search_docs"
        assert not result["requires_confirmation"]

    def test_opcua_uses_list_skills(self):
        state = _state(
            capability="opcua",
            intent="list_skills",
            entities={"machine_name": "MachineA"},
            resolved_entities={},
        )
        result = select_tool_generic(state)
        assert result["tool_name"] == "list_skills"
        assert result["tool_args"]["machine_name"] == "MachineA"
        assert "endpoint" in result["tool_args"]

    def test_kafka_requires_confirmation(self):
        state = _state(
            capability="kafka",
            intent="start_production",
            entities={},
            resolved_entities={"asset_id": "p24"},
        )
        result = select_tool_generic(state)
        assert result["tool_name"] == "send_command"
        assert result["requires_confirmation"] is True
        assert "confirmation_message" in result
        assert result["confirmation_message"]


# ── check_confirmation ─────────────────────────────────────────────────────────

class TestCheckConfirmation:
    def test_passthrough_returns_empty_dict(self):
        state = _state(requires_confirmation=False)
        result = check_confirmation(state)
        assert result == {}


# ── execute_tool ───────────────────────────────────────────────────────────────

class TestExecuteTool:
    def test_neo4j_tool_called(self):
        mock_fn = MagicMock(return_value=[{"step": "A", "status": "done"}])
        state = _state(
            capability="neo4j",
            submodel="ProductionPlan",
            tool_name="get_steps",
            tool_args={"asset_id": "p24"},
        )
        with patch(
            "app.graph.nodes.SUBMODEL_REGISTRY",
            {"ProductionPlan": {"tools": {"get_steps": mock_fn}}},
        ):
            result = execute_tool(state)
        mock_fn.assert_called_once_with(asset_id="p24")
        assert result["tool_result"] == [{"step": "A", "status": "done"}]
        assert result["error"] is None

    def test_rag_tool_called(self):
        mock_fn = MagicMock(return_value=[{"document": "LED info", "metadata": {}, "distance": 0.1}])
        state = _state(
            capability="rag",
            tool_name="search_docs",
            tool_args={"query": "Was bedeuten LEDs?"},
        )
        with patch.dict("app.tools.rag_tools.RAG_TOOL_REGISTRY", {"search_docs": mock_fn}):
            result = execute_tool(state)
        assert result["tool_result"][0]["document"] == "LED info"

    def test_unknown_tool_returns_error(self):
        state = _state(
            capability="rag",
            tool_name="nonexistent_tool",
            tool_args={},
        )
        result = execute_tool(state)
        assert result["tool_result"] is None
        assert "Unknown tool" in (result["error"] or "")

    def test_tool_exception_returns_error(self):
        mock_fn = MagicMock(side_effect=Exception("DB offline"))
        state = _state(
            capability="neo4j",
            submodel="ProductionPlan",
            tool_name="get_steps",
            tool_args={"asset_id": "p24"},
        )
        with patch(
            "app.graph.nodes.SUBMODEL_REGISTRY",
            {"ProductionPlan": {"tools": {"get_steps": mock_fn}}},
        ):
            result = execute_tool(state)
        assert result["error"] == "DB offline"
        assert result["tool_result"] is None

    def test_opcua_skills_connection_error_falls_back_to_neo4j(self):
        opcua_fn = MagicMock(side_effect=Exception("Reached maximum number of retries, giving up!"))
        neo4j_fn = MagicMock(return_value=[{"skillIdShort": "Skill_0001"}])

        state = _state(
            capability="opcua",
            tool_name="list_skills",
            user_input="Zeige Skills von P17",
            tool_args={"endpoint": "opc.tcp://localhost:4840"},
            resolved_entities={"asset_id": "https://smartfactory.de/asset/P17"},
        )

        with patch.dict("app.tools.opcua_tools.OPCUA_TOOL_REGISTRY", {"list_skills": opcua_fn}), patch(
            "app.graph.nodes.SUBMODEL_REGISTRY",
            {"Skills": {"tools": {"list_skills": neo4j_fn}}},
        ):
            result = execute_tool(state)

        neo4j_fn.assert_called_once_with(asset_id="https://smartfactory.de/asset/P17")
        assert result["error"] is None
        assert result["tool_result"] == [{"skillIdShort": "Skill_0001"}]
        assert result["capability"] == "neo4j"
        assert result["submodel"] == "Skills"
        assert result["tool_name"] == "list_skills"

    def test_opcua_skills_missing_args_falls_back_to_neo4j(self):
        def _requires_args(endpoint: str, machine_name: str) -> dict[str, Any]:
            return {"endpoint": endpoint, "machine_name": machine_name}

        neo4j_fn = MagicMock(return_value=[{"idShort": "Port", "value": "0"}])
        state = _state(
            capability="opcua",
            tool_name="read_skill_parameters",
            user_input="Inputparameter fuer P17",
            tool_args={"endpoint": "opc.tcp://localhost:4840"},
            resolved_entities={"asset_id": "https://smartfactory.de/asset/P17", "skill_name": "Store"},
        )

        with patch.dict("app.tools.opcua_tools.OPCUA_TOOL_REGISTRY", {"read_skill_parameters": _requires_args}), patch(
            "app.graph.nodes.SUBMODEL_REGISTRY",
            {"Skills": {"tools": {"list_skill_input_parameters": neo4j_fn}}},
        ):
            result = execute_tool(state)

        neo4j_fn.assert_called_once_with(asset_id="https://smartfactory.de/asset/P17", skill_name="Store")
        assert result["error"] is None
        assert result["tool_result"] == [{"idShort": "Port", "value": "0"}]


# ── generate_response ──────────────────────────────────────────────────────────

class TestGenerateResponse:
    def test_error_produces_error_message(self):
        state = _state(error="Something went wrong", tool_result=None)
        result = generate_response(state)
        assert "Fehler" in result["response"]

    def test_none_result_produces_no_data_message(self):
        state = _state(error=None, tool_result=None, capability="neo4j")
        result = generate_response(state)
        assert "keine daten" in result["response"].lower()

    def test_rag_result_shows_documents(self):
        state = _state(
            capability="rag",
            error=None,
            tool_result=[{"document": "LED bedeutet X", "metadata": {}, "distance": 0.1}],
        )
        result = generate_response(state)
        assert result["response"]

    def test_kafka_result(self):
        state = _state(
            capability="kafka",
            error=None,
            tool_result={"status": "sent", "topic": "commands"},
        )
        result = generate_response(state)
        assert "Befehl gesendet" in result["response"]

    def test_neo4j_list_result(self):
        state = _state(
            capability="neo4j",
            intent="get_steps",
            error=None,
            resolved_entities={"asset_id": "p24"},
            tool_result=[{"step": "A"}, {"step": "B"}],
        )
        result = generate_response(state)
        assert "2" in result["response"]

    def test_opcua_list_skills_response(self):
        state = _state(
            capability="opcua",
            intent="list_skills",
            error=None,
            tool_result={
                "endpoint": "opc.tcp://172.17.54.3:4842",
                "machines": {
                    "CA-Module": {
                        "skills": [
                            {"name": "Store"},
                            {"name": "Retrieve"},
                        ]
                    }
                },
            },
        )
        result = generate_response(state)
        assert "Skills" in result["response"]
        assert "CA-Module" in result["response"]
        assert "Store" in result["response"]

    def test_opcua_read_skill_parameters_response(self):
        state = _state(
            capability="opcua",
            intent="read_skill_parameters",
            error=None,
            tool_result={
                "endpoint": "opc.tcp://172.17.54.3:4842",
                "parameters": [
                    {"name": "TargetSlot", "value": 0},
                    {"name": "SpecifySlot", "value": False},
                ],
            },
        )
        result = generate_response(state)
        assert "Parameter" in result["response"]
        assert "TargetSlot=0" in result["response"]


# ── Full graph (integration-style, all IO mocked) ──────────────────────────────

class TestGraphIntegration:
    @patch("app.graph.nodes.session_svc.get_session", return_value={})
    @patch("app.graph.nodes.session_svc.update_session")
    @patch(
        "app.graph.nodes.llm.interpret",
        return_value={
            "intent": "get_steps",
            "capability": "neo4j",
            "submodel": "ProductionPlan",
            "entities": {"asset": "Lagermodul"},
        },
    )
    @patch(
        "app.graph.nodes.neo4j_svc.find_asset_by_name",
        return_value=[{"id": "p24", "name": "Lagermodul", "idShort": "Storage", "type": "resource"}],
    )
    def test_neo4j_flow_end_to_end(
        self, mock_find, mock_llm, mock_update, mock_session
    ):
        from app.graph.graph import build_graph

        mock_get_steps = MagicMock(return_value=[{"step": "Bohren", "status": "done"}])

        with patch.dict(
            "app.tools.neo4j.SUBMODEL_REGISTRY",
            {"ProductionPlan": {"tools": {"get_steps": mock_get_steps, "get_properties": mock_get_steps}}},
        ):
            graph = build_graph()
            final = graph.invoke({"session_id": "s1", "user_input": "Welche Schritte?"})

        assert final.get("capability") == "neo4j"
        assert final.get("submodel") == "ProductionPlan"
        assert final.get("tool_name") == "get_steps"
        assert "response" in final

    @patch("app.graph.nodes.session_svc.get_session", return_value={})
    @patch("app.graph.nodes.session_svc.update_session")
    @patch(
        "app.graph.nodes.llm.interpret",
        return_value={
            "intent": "start_motor",
            "capability": "kafka",
            "submodel": None,
            "entities": {"asset": "Motor1"},
        },
    )
    @patch(
        "app.graph.nodes.neo4j_svc.find_asset_by_name",
        return_value=[{"id": "m1", "name": "Motor1", "idShort": "M1", "type": "resource"}],
    )
    def test_kafka_flow_stops_for_confirmation(
        self, mock_find, mock_llm, mock_update, mock_session
    ):
        from app.graph.graph import build_graph

        graph = build_graph()
        final = graph.invoke({"session_id": "s2", "user_input": "Starte den Motor"})

        assert final.get("requires_confirmation") is True
        assert final.get("tool_name") == "send_command"
        # Should NOT have executed the tool
        assert "tool_result" not in final or final.get("tool_result") is None
