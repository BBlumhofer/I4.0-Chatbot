"""
RAG service – document retrieval via ChromaDB + sentence-transformers.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from typing import Any
from urllib.parse import urlparse
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.HttpClient | None = None
_collection: Any = None
_collection_name_in_use: str | None = None
_bootstrap_ingest_done = False
_bootstrap_ingest_started = False


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", (text or "").lower())


def _lexical_overlap_ratio(query: str, document: str) -> float:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return 0.0
    d_tokens = set(_tokenize(document))
    if not d_tokens:
        return 0.0
    overlap = len(q_tokens.intersection(d_tokens))
    return overlap / max(len(q_tokens), 1)


def _exact_asset_boost(query: str, document: str, metadata: dict[str, Any] | None) -> float:
    q = (query or "").lower()
    d = (document or "").lower()
    m = str((metadata or {}).get("path") or (metadata or {}).get("source") or "").lower()

    boost = 0.0
    # Explicit asset id mentions such as P24 should be strongly preferred.
    asset_tokens = set(re.findall(r"\bp\d+\b", q))
    if asset_tokens:
        if any(tok in d for tok in asset_tokens):
            boost += 0.7
        if any(tok in m for tok in asset_tokens):
            boost += 0.3
    return boost


def _hybrid_score(query: str, document: str, distance: float | None, metadata: dict[str, Any] | None) -> float:
    # Convert distance (smaller is better) into a bounded semantic score.
    semantic = 0.0 if distance is None else 1.0 / (1.0 + max(distance, 0.0))
    lexical = _lexical_overlap_ratio(query, document)
    exact = _exact_asset_boost(query, document, metadata)
    return (0.55 * semantic) + (0.35 * lexical) + (0.10 * min(exact, 1.0))


def _resolve_embedding_base_url() -> str:
    if settings.embedding_base_url:
        return settings.embedding_base_url.rstrip("/")

    parsed = urlparse(settings.llm_base_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return settings.llm_base_url.rstrip("/").removesuffix("/v1")


def _build_embedding_function() -> Any | None:
    provider = settings.embedding_provider.strip().lower()
    if provider == "chroma":
        logger.info("RAG: using Chroma default embedding model (server-side)")
        return None

    if provider == "ollama":
        base_url = _resolve_embedding_base_url()
        logger.info(
            "RAG: using Ollama embeddings model=%s base_url=%s",
            settings.embedding_model,
            base_url,
        )
        return embedding_functions.OllamaEmbeddingFunction(
            url=base_url,
            model_name=settings.embedding_model,
            timeout=settings.embedding_timeout_seconds,
        )

    logger.warning("RAG: unknown embedding provider '%s', using Chroma default", settings.embedding_provider)
    return None


def _seed_builtin_docs(collection: Any) -> None:
    """Populate a minimal FAQ corpus when the collection is empty."""
    try:
        if collection.count() > 0:
            return

        docs = [
            (
                "system-profile",
                "Der I4.0 Chatbot ist ein Assistent fur Produktionsanlagen. "
                "Er beantwortet Fragen uber Neo4j/AAS, OPC UA, RAG-Dokumente und Kafka-Befehle. "
                "Steuerbefehle werden nur nach expliziter Bestatigung ausgefuhrt.",
                {"source": "builtin", "type": "identity"},
            ),
            (
                "system-tools-overview",
                "Verfugbare Bereiche: neo4j (Assets und Submodelle), opcua (Live-Zustande), "
                "rag (Dokumentation) und kafka (Befehle). "
                "Bei asset-spezifischen Neo4j-Fragen wird eine Anlage oder Asset-ID benotigt.",
                {"source": "builtin", "type": "tools"},
            ),
        ]

        collection.add(
            ids=[doc_id for doc_id, _, _ in docs],
            documents=[text for _, text, _ in docs],
            metadatas=[meta for _, _, meta in docs],
        )
        logger.info("RAG: seeded builtin FAQ documents")
    except Exception as exc:
        logger.warning("RAG: failed to seed builtin FAQ docs: %s", exc)


def _split_markdown(text: str, max_chars: int = 1200) -> list[str]:
    sections = re.split(r"\n(?=#)", text)
    chunks: list[str] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(section)
            continue

        paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(para) <= max_chars:
                    current = para
                else:
                    for i in range(0, len(para), max_chars):
                        chunks.append(para[i:i + max_chars])
                    current = ""
        if current:
            chunks.append(current)
    return chunks


def _stable_doc_id(rel_path: str, chunk_index: int, chunk_text: str) -> str:
    digest = hashlib.sha1(chunk_text.encode("utf-8")).hexdigest()[:12]
    base = rel_path.replace("/", "_").replace(" ", "_")
    return f"{base}__{chunk_index:04d}__{digest}"


def _bootstrap_markdown_ingest(collection: Any) -> None:
    global _bootstrap_ingest_done
    if _bootstrap_ingest_done:
        return

    markdown_root = Path("/app/rag/markdown")
    if not markdown_root.exists():
        logger.info("RAG bootstrap: markdown folder not found at %s", markdown_root)
        _bootstrap_ingest_done = True
        return

    try:
        # Only bootstrap-ingest if collection has no real corpus yet.
        if collection.count() > 2:
            return
    except Exception:
        pass

    files = sorted(markdown_root.rglob("*.md"))
    if not files:
        _bootstrap_ingest_done = True
        return

    ingested = 0
    for file_path in files:
        rel_path = file_path.relative_to(markdown_root).as_posix()
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("RAG bootstrap: failed reading %s: %s", file_path, exc)
            continue

        for idx, chunk in enumerate(_split_markdown(content), start=1):
            doc_id = _stable_doc_id(rel_path, idx, chunk)
            metadata = {"source": "markdown-folder", "path": rel_path, "chunk": idx}
            try:
                collection.upsert(ids=[doc_id], documents=[chunk], metadatas=[metadata])
                ingested += 1
            except Exception as exc:
                logger.warning("RAG bootstrap: failed upsert for %s: %s", doc_id, exc)

    logger.info("RAG bootstrap: ingested %d markdown chunks from %s", ingested, markdown_root)
    _bootstrap_ingest_done = True


def _bootstrap_markdown_ingest_async(collection: Any) -> None:
    global _bootstrap_ingest_started
    if _bootstrap_ingest_done or _bootstrap_ingest_started:
        return

    _bootstrap_ingest_started = True

    def _worker() -> None:
        try:
            _bootstrap_markdown_ingest(collection)
        except Exception as exc:
            logger.warning("RAG bootstrap background ingest failed: %s", exc)

    threading.Thread(target=_worker, daemon=True).start()


def _get_collection() -> Any:
    global _client, _collection, _collection_name_in_use
    if _collection is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        embedding_fn = _build_embedding_function()
        requested_name = settings.chroma_collection

        try:
            _collection = _client.get_or_create_collection(
                name=requested_name,
                embedding_function=embedding_fn,
            )
            _collection_name_in_use = requested_name
        except Exception as exc:
            err = str(exc)
            if embedding_fn is not None and "Embedding function conflict" in err:
                provider_suffix = settings.embedding_provider.strip().lower()
                model_suffix = settings.embedding_model.split(":")[0].replace("/", "-")
                fallback_name = f"{requested_name}_{provider_suffix}_{model_suffix}"
                logger.warning(
                    "RAG: embedding conflict for collection '%s'; switching to '%s'. "
                    "Re-ingest documents for full recall.",
                    requested_name,
                    fallback_name,
                )
                _collection = _client.get_or_create_collection(
                    name=fallback_name,
                    embedding_function=embedding_fn,
                )
                _collection_name_in_use = fallback_name
            else:
                raise

        logger.info("RAG: active collection '%s'", _collection_name_in_use)
        _seed_builtin_docs(_collection)
        _bootstrap_markdown_ingest_async(_collection)
    return _collection


def search_docs(query: str, n_results: int | None = None) -> list[dict[str, Any]]:
    """
    Semantic search over the plant documentation corpus.

    Returns a list of {document, metadata, distance} dicts.
    """
    collection = _get_collection()
    final_n_results = n_results or settings.rag_default_n_results
    candidate_n = max(final_n_results * 5, final_n_results)
    results = collection.query(
        query_texts=[query],
        n_results=candidate_n,
        include=["documents", "metadatas", "distances"],
    )
    docs = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        distance_val: float | None
        try:
            distance_val = float(dist) if dist is not None else None
        except (TypeError, ValueError):
            distance_val = None

        docs.append(
            {
                "document": doc,
                "metadata": meta,
                "distance": distance_val,
                "hybrid_score": _hybrid_score(query, str(doc or ""), distance_val, meta if isinstance(meta, dict) else None),
            }
        )

    # Re-rank with hybrid semantic+lexical score for more robust retrieval.
    docs.sort(key=lambda item: float(item.get("hybrid_score", -1.0)), reverse=True)
    top_docs = docs[:final_n_results]

    logger.debug("RAG search '%s': %d candidates, %d returned", query, len(docs), len(top_docs))
    return top_docs


def add_document(text: str, metadata: dict[str, Any], doc_id: str) -> None:
    """Ingest a single document chunk into the vector store."""
    collection = _get_collection()
    collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
    logger.info("RAG: added document %s", doc_id)
