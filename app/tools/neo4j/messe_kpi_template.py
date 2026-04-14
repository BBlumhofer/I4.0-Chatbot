"""
Template tools for exhibition KPI questions.

Important:
- This module is intentionally NOT auto-registered in app.tools.neo4j.__init__.
- Replace the QUERY_* constants with real Cypher queries from your graph model.
- After finalizing queries, wire this module into a dedicated SubmodelToolset.
"""
from __future__ import annotations

from typing import Any

from app.services import neo4j_service as db


QUERY_TRUCKS_PRODUCED_TODAY = """
// TODO: Replace with your production query.
// Example idea:
// MATCH (p:Product)
// WHERE toLower(coalesce(p.type, '')) CONTAINS 'lkw'
//   AND date(datetime(coalesce(p.produced_at, p.created_at))) = date()
// RETURN count(p) AS produced_today
RETURN 0 AS produced_today
"""


QUERY_LIST_MODULES = """
// TODO: Replace with your modules query.
// Example idea:
// MATCH (m:Module)
// RETURN coalesce(m.idShort, m.id, m.name) AS module
// ORDER BY module
RETURN [] AS modules
"""


QUERY_ACTIVE_AGENTS = """
// TODO: Replace with your active agents query.
// Example idea:
// MATCH (a:Agent)
// WHERE coalesce(a.status, '') IN ['running', 'active']
// RETURN a.id AS agent_id, a.status AS status
RETURN [] AS active_agents
"""


QUERY_PRODUCTS_IN_STOCK = """
// TODO: Replace with your stock query.
// Example idea:
// MATCH (p:Product)
// WHERE coalesce(p.in_stock, false) = true
// RETURN coalesce(p.id, p.productId, p.name) AS product
RETURN [] AS products_in_stock
"""


def _run(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return db.run_query(query, params or {})


def count_trucks_produced_today(query: str | None = None) -> list[dict[str, Any]]:
    """Template for: Wie viel Lkws wurden heute produziert?"""
    return _run(query or QUERY_TRUCKS_PRODUCED_TODAY)


def list_modules(query: str | None = None) -> list[dict[str, Any]]:
    """Template for: Welche Module gibt es?"""
    return _run(query or QUERY_LIST_MODULES)


def list_active_agents(query: str | None = None) -> list[dict[str, Any]]:
    """Template for: Welche Agenten laufen gerade?"""
    return _run(query or QUERY_ACTIVE_AGENTS)


def list_products_in_stock(query: str | None = None) -> list[dict[str, Any]]:
    """Template for: Welche Produkte sind im Lager vorrätig?"""
    return _run(query or QUERY_PRODUCTS_IN_STOCK)
