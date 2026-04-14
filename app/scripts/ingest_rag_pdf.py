"""Extract PDF documents, optionally convert to markdown, and ingest into RAG.

Usage:
    python app/scripts/ingest_rag_pdf.py --input-dir rag/pdf
    python app/scripts/ingest_rag_pdf.py --input-dir rag/pdf --export-markdown-dir rag/markdown/pdf_converted
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# Allow running as a plain script from project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services import rag_service
from app.scripts.ingest_rag_markdown import stable_doc_id


def sanitize_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.splitlines()).strip()


def to_markdown(page_text: str, source_name: str, page_number: int) -> str:
    content = sanitize_text(page_text)
    return f"# {source_name}\n\n## Seite {page_number}\n\n{content}\n"


def ingest_pdf_folder(input_dir: Path, export_markdown_dir: Path | None = None) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    pdf_files = sorted(input_dir.rglob("*.pdf"))
    if not pdf_files:
        print("No PDF files found. Nothing to ingest.")
        return

    if export_markdown_dir is not None:
        export_markdown_dir.mkdir(parents=True, exist_ok=True)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )

    total_chunks = 0

    for pdf_path in pdf_files:
        rel_pdf_path = pdf_path.relative_to(input_dir).as_posix()
        reader = PdfReader(str(pdf_path))
        source_name = pdf_path.stem

        page_markdowns: list[str] = []
        pdf_chunk_count = 0

        for page_index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            markdown_page = to_markdown(page_text, source_name, page_index)
            page_markdowns.append(markdown_page)

            page_chunks = splitter.split_text(markdown_page)
            for chunk_index, chunk_text in enumerate(page_chunks, start=1):
                chunk_text = sanitize_text(chunk_text)
                if not chunk_text:
                    continue
                doc_id = stable_doc_id(rel_pdf_path, page_index * 10000 + chunk_index, chunk_text)
                metadata = {
                    "source": "pdf-folder",
                    "path": rel_pdf_path,
                    "page": page_index,
                    "chunk": chunk_index,
                }
                rag_service.add_document(chunk_text, metadata=metadata, doc_id=doc_id)
                pdf_chunk_count += 1

        total_chunks += pdf_chunk_count
        print(f"Ingested {pdf_chunk_count:>3} chunks from {rel_pdf_path}")

        if export_markdown_dir is not None:
            md_rel = Path(rel_pdf_path).with_suffix(".md")
            md_target = export_markdown_dir / md_rel
            md_target.parent.mkdir(parents=True, exist_ok=True)
            md_text = "\n\n".join(page_markdowns)
            md_target.write_text(md_text, encoding="utf-8")
            print(f"Exported markdown: {md_target}")

    print(f"Done. Total ingested PDF chunks: {total_chunks}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest PDF files into RAG (Chroma)")
    parser.add_argument(
        "--input-dir",
        default="rag/pdf",
        help="Directory containing PDF files (default: rag/pdf)",
    )
    parser.add_argument(
        "--export-markdown-dir",
        default=None,
        help="Optional directory to store converted markdown files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_dir = Path(args.export_markdown_dir) if args.export_markdown_dir else None
    ingest_pdf_folder(Path(args.input_dir), export_markdown_dir=export_dir)


if __name__ == "__main__":
    main()
