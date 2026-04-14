"""Ingest markdown files from a folder into the configured Chroma collection.

Usage:
    python app/scripts/ingest_rag_markdown.py --input-dir rag/markdown
    python app/scripts/ingest_rag_markdown.py --input-dir rag/markdown --reset-collection
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# Allow running as a plain script from project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services import rag_service


def split_markdown(text: str, max_chars: int = 1200) -> list[str]:
    """Split markdown text into semantic chunks using headings and size limits."""
    sections = re.split(r"\n(?=#)", text)
    chunks: list[str] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chars:
            chunks.append(section)
            continue

        # Fallback split for long sections by paragraphs.
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
                    # Hard split paragraph if still too long.
                    for i in range(0, len(para), max_chars):
                        chunks.append(para[i:i + max_chars])
                    current = ""
        if current:
            chunks.append(current)

    return chunks


def stable_doc_id(rel_path: str, chunk_index: int, chunk_text: str) -> str:
    digest = hashlib.sha1(chunk_text.encode("utf-8")).hexdigest()[:12]
    base = rel_path.replace("/", "_").replace(" ", "_")
    return f"{base}__{chunk_index:04d}__{digest}"


def ingest_markdown(input_dir: Path, reset_collection: bool) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    collection = rag_service._get_collection()  # Reuse configured client/collection.

    if reset_collection:
        existing = collection.get(include=[])
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            print(f"Deleted {len(ids)} existing vectors from collection.")

    files = sorted(input_dir.rglob("*.md"))
    if not files:
        print("No markdown files found. Nothing to ingest.")
        return

    ingested_chunks = 0
    for file_path in files:
        rel_path = file_path.relative_to(input_dir).as_posix()
        content = file_path.read_text(encoding="utf-8")
        chunks = split_markdown(content)
        for idx, chunk in enumerate(chunks, start=1):
            doc_id = stable_doc_id(rel_path, idx, chunk)
            metadata = {
                "source": "markdown-folder",
                "path": rel_path,
                "chunk": idx,
            }
            rag_service.add_document(chunk, metadata=metadata, doc_id=doc_id)
            ingested_chunks += 1

        print(f"Ingested {len(chunks):>3} chunks from {rel_path}")

    print(f"Done. Total ingested chunks: {ingested_chunks}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest markdown files into RAG (Chroma)")
    parser.add_argument(
        "--input-dir",
        default="rag/markdown",
        help="Directory containing markdown files (default: rag/markdown)",
    )
    parser.add_argument(
        "--reset-collection",
        action="store_true",
        help="Delete existing vectors in the target collection before ingesting",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ingest_markdown(Path(args.input_dir), reset_collection=args.reset_collection)


if __name__ == "__main__":
    main()
