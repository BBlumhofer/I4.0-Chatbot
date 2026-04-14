"""
Script-like regression tests for Neo4j submodel tools.

Goal:
- Provide lightweight, executable checks per submodel.
- Catch schema-coupling issues early (e.g. hardcoded :SubmodelElement labels).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.tools.neo4j import SUBMODEL_REGISTRY


@pytest.mark.parametrize("submodel", sorted(SUBMODEL_REGISTRY.keys()))
def test_each_submodel_get_properties_smoke(submodel: str):
    """Every registered submodel must expose a runnable get_properties tool."""
    get_properties = SUBMODEL_REGISTRY[submodel]["tools"]["get_properties"]

    with patch("app.services.neo4j_service.get_submodel_elements", return_value=[]), patch(
        "app.services.neo4j_service.run_query", return_value=[]
    ), patch(
        "app.services.neo4j_service.get_agent_connected_node_properties", return_value=[]
    ):
        result = get_properties("P24")

    assert isinstance(result, list), f"{submodel}.get_properties should return list"


def test_structure_get_parts_query_is_label_agnostic():
    from app.tools.neo4j.structure import get_parts

    with patch("app.tools.neo4j.structure.db.run_query", return_value=[]) as mock_db:
        get_parts("P24")

    query = mock_db.call_args[0][0]
    assert ":SubmodelElement" not in query
    assert "el.quantity" not in query
    assert "HAS_ELEMENT" in query


def test_bom_get_parts_query_is_label_agnostic():
    from app.tools.neo4j.bill_of_material import get_parts

    with patch("app.tools.neo4j.bill_of_material.db.run_query", return_value=[]) as mock_db:
        get_parts("P24")

    query = mock_db.call_args[0][0]
    assert ":SubmodelElement" not in query
    assert "el.quantity" not in query
    assert "HAS_ELEMENT" in query


def test_condition_monitoring_query_is_label_agnostic():
    from app.tools.neo4j.condition_monitoring import get_condition_history

    with patch("app.tools.neo4j.condition_monitoring.db.run_query", return_value=[]) as mock_db:
        get_condition_history("P24")

    query = mock_db.call_args[0][0]
    assert ":SubmodelElement" not in query
    assert "HAS_ELEMENT" in query


def test_production_plan_queries_are_label_agnostic():
    from app.tools.neo4j.production_plan import get_steps, get_step_duration, is_finished

    with patch("app.tools.neo4j.production_plan.db.run_query", return_value=[]) as mock_db:
        get_steps("P24")
        get_step_duration("P24", "Step0001")
        is_finished("P24")

    queries = [call.args[0] for call in mock_db.call_args_list]
    assert queries, "Expected production plan queries to be executed"
    assert all(":SubmodelElement" not in q for q in queries)
    assert all("HAS_ELEMENT" in q for q in queries)
