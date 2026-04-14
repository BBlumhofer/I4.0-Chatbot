from __future__ import annotations

import json
from unittest.mock import patch

from app.services import neo4j_service


class TestExpandAssetSearchTerms:
    def test_maps_known_alias_to_canonical_p_id(self):
        contains_terms, exact_terms, canonical_ids = neo4j_service._expand_asset_search_terms("ca-modul")

        assert "ca-modul" in contains_terms
        assert "p17" in contains_terms
        assert "https://smartfactory.de/asset/p17" in contains_terms
        assert "p17" in exact_terms
        assert canonical_ids == ["P17"]

    def test_extracts_p_id_from_text(self):
        contains_terms, exact_terms, canonical_ids = neo4j_service._expand_asset_search_terms(
            "Bitte zeige Status von P17 CA-Modul"
        )

        assert "p17" in contains_terms
        assert "https://smartfactory.de/asset/p17" in contains_terms
        assert canonical_ids == ["P17"]


class TestFindAssetByName:
    @patch("app.services.neo4j_service.run_query", return_value=[])
    def test_uses_expanded_terms_in_query_params(self, mock_run_query):
        neo4j_service.find_asset_by_name("collaborative-assembly module")

        assert mock_run_query.called
        _, params = mock_run_query.call_args[0]
        assert "contains_terms" in params
        assert "canonical_ids" in params
        assert "P17" in params["canonical_ids"]
        assert "p17" in params["contains_terms"]

    @patch("app.services.neo4j_service.run_query", return_value=[])
    def test_empty_name_returns_empty_without_query(self, mock_run_query):
        result = neo4j_service.find_asset_by_name("   ")

        assert result == []
        mock_run_query.assert_not_called()


class TestLoadResourceAliases:
    def test_loads_new_resources_schema(self, tmp_path):
        aliases_file = tmp_path / "resource_aliases.json"
        aliases_file.write_text(
            json.dumps(
                {
                    "resources": [
                        {
                            "canonical_id": "P24",
                            "site": "Werk-A",
                            "line": "Linie-1",
                            "aliases": ["P24", "Lager-Modul", "storage module"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        with patch("app.services.neo4j_service._RESOURCE_ALIASES_FILE", aliases_file):
            loaded = neo4j_service._load_resource_aliases()

        assert loaded["p24"] == "P24"
        assert loaded["lagermodul"] == "P24"
        assert loaded["storagemodule"] == "P24"

    def test_loads_legacy_aliases_schema(self, tmp_path):
        aliases_file = tmp_path / "resource_aliases.json"
        aliases_file.write_text(
            json.dumps({"aliases": {"Handarbeitsmodul": "P17"}}),
            encoding="utf-8",
        )

        with patch("app.services.neo4j_service._RESOURCE_ALIASES_FILE", aliases_file):
            loaded = neo4j_service._load_resource_aliases()

        assert loaded["handarbeitsmodul"] == "P17"


class TestGetAgentConnectedNodeProperties:
    @patch(
        "app.services.neo4j_service.run_query",
        return_value=[{"nodeProps": {"id": "P17", "embedding_error": "missing_text"}}],
    )
    def test_uses_apoc_query_by_default(self, mock_run_query):
        result = neo4j_service.get_agent_connected_node_properties(shell_id="P17", limit=42)

        assert result == [{"nodeProps": {"id": "P17", "embedding_error": "missing_text"}}]
        cypher, params = mock_run_query.call_args[0]
        assert "apoc.map.removeKeys" in cypher
        assert params["shell_id"] == "P17"
        assert params["limit"] == 42

    def test_falls_back_without_apoc_and_removes_embedding(self):
        with patch(
            "app.services.neo4j_service.run_query",
            side_effect=[
                Exception("Unknown function 'apoc.map.removeKeys'"),
                [{"nodeProps": {"id": "P17", "embedding": [0.1, 0.2], "x": 1}}],
            ],
        ) as mock_run_query:
            result = neo4j_service.get_agent_connected_node_properties(shell_id=None, limit=5)

        assert result == [{"nodeProps": {"id": "P17", "x": 1}}]
        assert mock_run_query.call_count == 2
        first_cypher, _ = mock_run_query.call_args_list[0][0]
        second_cypher, _ = mock_run_query.call_args_list[1][0]
        assert "apoc.map.removeKeys" in first_cypher
        assert "properties(n) AS nodeProps" in second_cypher


class TestExhibitionInsightHelpers:
    def test_returns_needs_query_placeholder_when_no_cypher(self):
        rows = neo4j_service.get_today_truck_production()

        assert rows
        assert rows[0]["status"] == "needs_query"
        assert rows[0]["query_name"] == "today_truck_production"

    @patch("app.services.neo4j_service.run_query", return_value=[{"count": 12}])
    def test_runs_custom_cypher_with_passed_params(self, mock_run_query):
        result = neo4j_service.list_active_agents_insight(
            cypher="MATCH (a:Agent) RETURN count(a) AS count",
            params={"x": 1},
        )

        assert result == [{"count": 12}]
        cypher, params = mock_run_query.call_args[0]
        assert "MATCH (a:Agent)" in cypher
        assert params["x"] == 1
