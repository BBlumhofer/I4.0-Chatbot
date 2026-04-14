# RAG Markdown Ablage

Lege hier deine Markdown-Dateien (`*.md`) ab, die im RAG durchsuchbar werden sollen.

Beispiele:
- `anlagen/foerderband.md`
- `fehlercodes/e4711.md`
- `betrieb/warteplan.md`

Danach die Ingestion starten (Projektroot):

```bash
python app/scripts/ingest_rag_markdown.py --input-dir rag/markdown
```

PDF-Dateien aus `rag/pdf` ingestieren (optional mit Markdown-Export):

```bash
python app/scripts/ingest_rag_pdf.py --input-dir rag/pdf --export-markdown-dir rag/markdown/pdf_converted
```

Alles in einem Lauf vorbereiten (Markdown + PDF):

```bash
./scripts/prepare_rag_docs.sh
```

Optional vorher leeren:

```bash
python app/scripts/ingest_rag_markdown.py --input-dir rag/markdown --reset-collection
```

Kompletter Neuaufbau:

```bash
./scripts/prepare_rag_docs.sh --reset
```
