"""
Tests for the per-submodel Neo4j tool package (app.tools.neo4j).

Verifies:
- Each submodel module registers itself correctly
- SUBMODEL_REGISTRY is complete and consistent
- get_available_submodels filters by HAS_SUBMODEL results
- SubmodelToolset validation (get_properties required)
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from app.tools.neo4j._base import _REGISTRY, SubmodelToolset, register_submodel
from app.tools.neo4j import SUBMODEL_REGISTRY, VALID_SUBMODELS, get_available_submodels


EXPECTED_SUBMODELS = {
    "ProductionPlan",
    "BillOfMaterial",
    "Structure",
    "Nameplate",
    "MaterialData",
    "Skills",
    "AssetInterfaceDescription",
    "FaultDescription",
    "ConditionMonitoring",
}


class TestRegistry:
    def test_all_expected_submodels_registered(self):
        assert EXPECTED_SUBMODELS.issubset(VALID_SUBMODELS)

    def test_valid_submodels_matches_registry_keys(self):
        assert VALID_SUBMODELS == set(SUBMODEL_REGISTRY.keys())

    def test_every_entry_has_tools_dict(self):
        for name, entry in SUBMODEL_REGISTRY.items():
            assert "tools" in entry, f"{name} missing 'tools'"
            assert isinstance(entry["tools"], dict), f"{name}.tools must be dict"

    def test_every_entry_has_get_properties(self):
        for name, entry in SUBMODEL_REGISTRY.items():
            assert "get_properties" in entry["tools"], (
                f"{name} must define a 'get_properties' fallback tool"
            )

    def test_every_entry_has_semantic_id(self):
        for name, entry in SUBMODEL_REGISTRY.items():
            assert entry.get("semantic_id"), f"{name} missing 'semantic_id'"

    def test_every_entry_has_description(self):
        for name, entry in SUBMODEL_REGISTRY.items():
            assert entry.get("description"), f"{name} missing 'description'"

    def test_production_plan_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["ProductionPlan"]["tools"]
        assert "get_steps" in tools
        assert "get_step_duration" in tools
        assert "is_finished" in tools

    def test_skills_has_get_skills(self):
        assert "get_skills" in SUBMODEL_REGISTRY["Skills"]["tools"]

    def test_condition_monitoring_has_get_condition_history(self):
        assert "get_condition_history" in SUBMODEL_REGISTRY["ConditionMonitoring"]["tools"]

    def test_bill_of_material_has_get_parts(self):
        assert "get_parts" in SUBMODEL_REGISTRY["BillOfMaterial"]["tools"]

    def test_structure_has_get_parts(self):
        assert "get_parts" in SUBMODEL_REGISTRY["Structure"]["tools"]


class TestSubmodelToolset:
    def test_register_submodel_adds_to_registry(self):
        """register_submodel should add a new entry to _REGISTRY."""
        dummy_fn = lambda asset_id: []
        ts = SubmodelToolset(
            idShort="_TestSubmodel_",
            semantic_id="https://example.com/TestSubmodel/1/0",
            description="Test only",
            tools={"get_properties": dummy_fn},
        )
        register_submodel(ts)
        assert "_TestSubmodel_" in _REGISTRY
        # cleanup
        del _REGISTRY["_TestSubmodel_"]

    def test_missing_get_properties_raises(self):
        """register_submodel must raise if get_properties is absent."""
        dummy_fn = lambda asset_id: []
        ts = SubmodelToolset(
            idShort="_BadSubmodel_",
            semantic_id="https://example.com/Bad/1/0",
            description="Bad",
            tools={"some_tool": dummy_fn},  # no get_properties!
        )
        with pytest.raises(ValueError, match="get_properties"):
            register_submodel(ts)
        assert "_BadSubmodel_" not in _REGISTRY


class TestGetAvailableSubmodels:
    @patch(
        "app.services.neo4j_service.get_available_submodels_for_asset",
        return_value=[
            {"idShort": "ProductionPlan", "semanticId": "https://admin-shell.io/idta/Submodel/ProductionPlan/1/0"},
            {"idShort": "Nameplate", "semanticId": "https://admin-shell.io/idta/Submodel/Nameplate/2/0"},
            {"idShort": "UnknownSubmodel", "semanticId": "https://unknown.example.com"},
        ],
    )
    def test_filters_to_registered_submodels(self, mock_db):
        result = get_available_submodels("p24")
        assert "ProductionPlan" in result
        assert "Nameplate" in result
        assert "UnknownSubmodel" not in result

    @patch(
        "app.services.neo4j_service.get_available_submodels_for_asset",
        return_value=[],
    )
    def test_empty_response_returns_empty_list(self, mock_db):
        result = get_available_submodels("p_unknown")
        assert result == []

    @patch(
        "app.services.neo4j_service.get_available_submodels_for_asset",
        side_effect=Exception("DB down"),
    )
    def test_db_error_returns_all_registered(self, mock_db):
        """If Neo4j is unavailable, fall back to all registered submodels."""
        result = get_available_submodels("p24")
        assert set(result) == VALID_SUBMODELS

    @patch(
        "app.services.neo4j_service.get_available_submodels_for_asset",
        return_value=[
            # idShort is missing but semantic_id matches
            {"idShort": None, "semanticId": "https://admin-shell.io/idta/Submodel/Skills/1/0"},
        ],
    )
    def test_matches_by_semantic_id_when_id_short_missing(self, mock_db):
        result = get_available_submodels("p24")
        assert "Skills" in result


class TestPerSubmodelTools:
    """Smoke-tests that each submodel's tools call the DB layer correctly."""

    @patch("app.tools.neo4j.production_plan.db.run_query", return_value=[])
    def test_production_plan_get_steps_calls_db(self, mock_db):
        from app.tools.neo4j.production_plan import get_steps
        get_steps("p1")
        mock_db.assert_called_once()
        assert "p1" in str(mock_db.call_args)

    @patch("app.tools.neo4j.production_plan.db.run_query", return_value=[{"remaining": 0}])
    def test_production_plan_is_finished_true(self, mock_db):
        from app.tools.neo4j.production_plan import is_finished
        assert is_finished("p1") is True

    @patch("app.tools.neo4j.production_plan.db.run_query", return_value=[{"remaining": 2}])
    def test_production_plan_is_finished_false(self, mock_db):
        from app.tools.neo4j.production_plan import is_finished
        assert is_finished("p1") is False

    @patch("app.tools.neo4j.skills.db.run_query", return_value=[{"skill": "drilling"}])
    def test_skills_get_skills_returns_list(self, mock_db):
        from app.tools.neo4j.skills import get_skills
        result = get_skills("r1")
        assert result == [{"skill": "drilling"}]

    @patch("app.tools.neo4j.condition_monitoring.db.run_query", return_value=[{"metric": "temp"}])
    def test_condition_monitoring_get_history(self, mock_db):
        from app.tools.neo4j.condition_monitoring import get_condition_history
        result = get_condition_history("r1")
        assert result[0]["metric"] == "temp"

    @patch("app.tools.neo4j.nameplate.db.get_submodel_elements", return_value=[{"idShort": "manufacturer"}])
    def test_nameplate_get_nameplate(self, mock_db):
        from app.tools.neo4j.nameplate import get_nameplate
        result = get_nameplate("p1")
        assert result[0]["idShort"] == "manufacturer"
        mock_db.assert_called_once_with("p1", "Nameplate")
