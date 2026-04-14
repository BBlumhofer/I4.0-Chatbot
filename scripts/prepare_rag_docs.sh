#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR"

if ! python - <<'PY' >/dev/null 2>&1
import chromadb  # noqa: F401
import pypdf  # noqa: F401
import langchain_text_splitters  # noqa: F401
PY
then
  echo "Fehlende Python-Abhangigkeiten fur RAG-Ingestion." >&2
  echo "Bitte zuerst ausfuhren: pip install -r requirements.txt" >&2
  exit 1
fi

PDF_EXPORT_DIR="rag/markdown/pdf_converted"

RESET_FLAG=""
if [[ "${1:-}" == "--reset" ]]; then
  RESET_FLAG="--reset-collection"
fi

echo "[1/3] Ingest markdown files from rag/markdown"
python -m app.scripts.ingest_rag_markdown --input-dir rag/markdown $RESET_FLAG

echo "[2/3] Ingest PDF files from rag/pdf and convert to markdown"
python -m app.scripts.ingest_rag_pdf --input-dir rag/pdf --export-markdown-dir "$PDF_EXPORT_DIR"

echo "[3/3] Done"
echo "RAG content is prepared."
