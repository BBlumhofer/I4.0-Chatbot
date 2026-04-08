"""
RAG service – document retrieval via ChromaDB + sentence-transformers.
"""
from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.HttpClient | None = None
_collection: Any = None


def _get_collection() -> Any:
    global _client, _collection
    if _collection is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection,
        )
    return _collection


def search_docs(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """
    Semantic search over the plant documentation corpus.

    Returns a list of {document, metadata, distance} dicts.
    """
    collection = _get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    docs = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        docs.append({"document": doc, "metadata": meta, "distance": dist})
    logger.debug("RAG search '%s': %d results", query, len(docs))
    return docs


def add_document(text: str, metadata: dict[str, Any], doc_id: str) -> None:
    """Ingest a single document chunk into the vector store."""
    collection = _get_collection()
    collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
    logger.info("RAG: added document %s", doc_id)
