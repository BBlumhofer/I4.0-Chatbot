"""
RAG tools – semantic document retrieval.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services import rag_service as svc

logger = logging.getLogger(__name__)


def search_docs(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Search plant documentation for *query*."""
    return svc.search_docs(query, n_results=n_results)


# Registry for tool selection
RAG_TOOL_REGISTRY: dict[str, Any] = {
    "search_docs": search_docs,
}
