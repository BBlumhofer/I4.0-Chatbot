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
    "Agents",
    "ExhibitionInsights",
    "Availability",
    "BillOfApplications",
    "CarbonFootprint",
    "DesignOfProduct",
    "MachineScheduleLog",
    "MachineSchedule",
    "OfferedCapabilityDescription",
    "ProductIdentification",
    "ProductionPlan",
    "QualityInformation",
    "RequiredCapabilityDescription",
    "SituationLog",
    "StorageConfiguration",
    "SymptomDescription",
    "TechnicalData",
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

    def test_skills_has_detailed_tools(self):
        tools = SUBMODEL_REGISTRY["Skills"]["tools"]
        assert "list_skills" in tools
        assert "get_skill_endpoints" in tools
        assert "list_skill_input_parameters" in tools

    def test_agents_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["Agents"]["tools"]
        assert "list_connected_node_properties" in tools
        assert "get_agent_nodes" in tools
        assert "get_properties" in tools

    def test_exhibition_insights_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["ExhibitionInsights"]["tools"]
        assert "get_today_truck_production" in tools
        assert "list_modules" in tools
        assert "list_active_agents" in tools
        assert "list_inventory_products" in tools
        assert "get_properties" in tools

    def test_condition_monitoring_has_get_condition_history(self):
        assert "get_condition_history" in SUBMODEL_REGISTRY["ConditionMonitoring"]["tools"]

    def test_bill_of_material_has_get_parts(self):
        assert "get_parts" in SUBMODEL_REGISTRY["BillOfMaterial"]["tools"]

    def test_structure_has_get_parts(self):
        assert "get_parts" in SUBMODEL_REGISTRY["Structure"]["tools"]

    def test_nameplate_has_specific_tools(self):
        tools = SUBMODEL_REGISTRY["Nameplate"]["tools"]
        assert "get_nameplate" in tools
        assert "get_nameplate_element" in tools
        assert "get_date_of_manufacture" in tools
        assert "get_manufacturer_name" in tools
        assert "get_hardware_version" in tools
        assert "get_software_version" in tools
        assert "get_uri_of_the_product" in tools
        assert "get_country_of_origin" in tools
        assert "get_year_of_construction" in tools
        assert "get_manufacturer_product_type" in tools
        assert "list_address_information" in tools
        assert "list_contact_channels" in tools

    def test_availability_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["Availability"]["tools"]
        assert "get_machine_state" in tools
        assert "list_unavailability_blocks" in tools
        assert "list_unavailability_reasons" in tools
        assert "get_availability_overview" in tools

    def test_machine_schedule_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["MachineSchedule"]["tools"]
        assert "get_schedule" in tools
        assert "list_schedule_entries" in tools
        assert "has_open_tasks" in tools
        assert "get_last_update" in tools

    def test_offered_capability_description_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["OfferedCapabilityDescription"]["tools"]
        assert "list_capability_sets" in tools
        assert "list_capabilities" in tools
        assert "get_capability_by_id_short" in tools
        assert "list_properties_by_container" in tools

    def test_design_of_product_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["DesignOfProduct"]["tools"]
        assert "get_design_overview" in tools
        assert "get_author_info" in tools
        assert "get_model_descriptor" in tools

    def test_machine_schedule_log_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["MachineScheduleLog"]["tools"]
        assert "get_schedule_log" in tools
        assert "get_last_update_log" in tools

    def test_storage_configuration_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["StorageConfiguration"]["tools"]
        assert "list_storages" in tools
        assert "list_slots" in tools
        assert "get_demand_config" in tools
        assert "get_projection_config" in tools

    def test_quality_information_has_expected_tools(self):
        tools = SUBMODEL_REGISTRY["QualityInformation"]["tools"]
        assert "get_quality_information" in tools
        assert "get_quality_by_id_short" in tools


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

    @patch(
        "app.tools.neo4j.skills.db.run_query",
        return_value=[{"skillIdShort": "Skill_0009", "skillName": "Drilling"}],
    )
    def test_skills_get_skills_returns_list(self, mock_db):
        from app.tools.neo4j.skills import get_skills
        result = get_skills("r1")
        assert result == [{"skill": "Skill_0009", "name": "Drilling"}]

    @patch(
        "app.tools.neo4j.skills.db.run_query",
        return_value=[{"skillIdShort": "Skill_0001", "skillName": "Store"}],
    )
    def test_skills_list_skills(self, mock_db):
        from app.tools.neo4j.skills import list_skills

        result = list_skills("r1")

        assert result[0]["skillIdShort"] == "Skill_0001"
        assert result[0]["skillName"] == "Store"

    @patch(
        "app.tools.neo4j.agents.db.get_agent_connected_node_properties",
        return_value=[{"nodeProps": {"id": "P17"}}],
    )
    def test_agents_list_connected_node_properties(self, mock_db):
        from app.tools.neo4j.agents import list_connected_node_properties

        result = list_connected_node_properties(shell_id="P17")

        assert result == [{"nodeProps": {"id": "P17"}}]
        mock_db.assert_called_once_with(shell_id="P17", limit=1000)

    @patch(
        "app.tools.neo4j.skills.db.run_query",
        return_value=[{"skillIdShort": "Skill_0001", "endpoint": "opc.tcp://x"}],
    )
    def test_skills_get_skill_endpoints(self, mock_db):
        from app.tools.neo4j.skills import get_skill_endpoints

        result = get_skill_endpoints("r1", skill_id_short="Skill_0001")

        assert result[0]["endpoint"] == "opc.tcp://x"
        assert mock_db.call_args[0][1]["skill_id_short"] == "Skill_0001"

    @patch(
        "app.tools.neo4j.skills.db.run_query",
        return_value=[{"skillIdShort": "Skill_0001", "idShort": "Port", "value": "0"}],
    )
    def test_skills_list_input_parameters(self, mock_db):
        from app.tools.neo4j.skills import list_skill_input_parameters

        result = list_skill_input_parameters("r1", skill_name="Store")

        assert result[0]["idShort"] == "Port"
        assert mock_db.call_args[0][1]["skill_name"] == "Store"

    @patch("app.tools.neo4j.condition_monitoring.db.run_query", return_value=[{"metric": "temp"}])
    def test_condition_monitoring_get_history(self, mock_db):
        from app.tools.neo4j.condition_monitoring import get_condition_history
        result = get_condition_history("r1")
        assert result[0]["metric"] == "temp"

    @patch("app.tools.neo4j.nameplate.db.run_query", return_value=[{"idShort": "manufacturer"}])
    def test_nameplate_get_nameplate(self, mock_db):
        from app.tools.neo4j.nameplate import get_nameplate
        result = get_nameplate("p1")
        assert result[0]["idShort"] == "manufacturer"
        mock_db.assert_called_once()

    @patch("app.tools.neo4j.nameplate.db.run_query", return_value=[{"idShort": "DateOfManufacture"}])
    def test_nameplate_get_date_of_manufacture(self, mock_db):
        from app.tools.neo4j.nameplate import get_date_of_manufacture

        result = get_date_of_manufacture("https://smartfactory.de/assets/P18")

        assert result == [{"idShort": "DateOfManufacture"}]
        assert mock_db.call_args[0][1]["id_short"] == "DateOfManufacture"

    @patch("app.tools.neo4j.nameplate.db.run_query", return_value=[{"idShort": "ManufacturerName"}])
    def test_nameplate_get_manufacturer_name(self, mock_db):
        from app.tools.neo4j.nameplate import get_manufacturer_name

        result = get_manufacturer_name("p1")

        assert result == [{"idShort": "ManufacturerName"}]
        assert mock_db.call_args[0][1]["id_short"] == "ManufacturerName"

    @patch("app.tools.neo4j.nameplate.db.run_query", return_value=[{"idShort": "URIOfTheProduct"}])
    def test_nameplate_get_uri_of_the_product(self, mock_db):
        from app.tools.neo4j.nameplate import get_uri_of_the_product

        result = get_uri_of_the_product("https://smartfactory.de/asset/P18")

        assert result == [{"idShort": "URIOfTheProduct"}]
        assert mock_db.call_args[0][1]["id_short"] == "URIOfTheProduct"

    @patch("app.tools.neo4j.availability.db.run_query", return_value=[{"idShort": "MachineState", "value": "available"}])
    def test_availability_get_machine_state(self, mock_db):
        from app.tools.neo4j.availability import get_machine_state

        result = get_machine_state("https://smartfactory.de/asset/P18")

        assert result[0]["idShort"] == "MachineState"
        mock_db.assert_called_once()

    @patch("app.tools.neo4j.machine_schedule.db.run_query", return_value=[{"idShort": "Schedule"}])
    def test_machine_schedule_get_schedule(self, mock_db):
        from app.tools.neo4j.machine_schedule import get_schedule

        result = get_schedule("p1")

        assert result == [{"idShort": "Schedule"}]
        mock_db.assert_called_once()

    @patch("app.tools.neo4j.machine_schedule.db.run_query", return_value=[{"hasOpenTasks": True}])
    def test_machine_schedule_has_open_tasks(self, mock_db):
        from app.tools.neo4j.machine_schedule import has_open_tasks

        assert has_open_tasks("p1") is True

    @patch("app.tools.neo4j.offered_capability_description.db.run_query", return_value=[{"idShort": "CapabilitySet"}])
    def test_offered_capability_list_sets(self, mock_db):
        from app.tools.neo4j.offered_capability_description import list_capability_sets

        result = list_capability_sets("p1")

        assert result == [{"idShort": "CapabilitySet"}]
        mock_db.assert_called_once()

    @patch("app.tools.neo4j.design_of_product.list_children_by_parent", return_value=[{"idShort": "Design_V01"}])
    def test_design_of_product_overview(self, mock_list):
        from app.tools.neo4j.design_of_product import get_design_overview

        result = get_design_overview("p1")
        assert result == [{"idShort": "Design_V01"}]

    @patch("app.tools.neo4j.storage_configuration.list_children_by_parent", return_value=[{"idShort": "Slot_1"}])
    def test_storage_configuration_list_slots(self, mock_list):
        from app.tools.neo4j.storage_configuration import list_slots

        result = list_slots("p1")
        assert result == [{"idShort": "Slot_1"}]

    @patch("app.tools.neo4j.situation_log.list_children_by_parent", return_value=[{"idShort": "Situation_1"}])
    def test_situation_log_list_situations(self, mock_list):
        from app.tools.neo4j.situation_log import list_situations

        result = list_situations("p1")
        assert result == [{"idShort": "Situation_1"}]
