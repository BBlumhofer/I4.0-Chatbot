# RAG PDF Ablage

Lege unter /rag die  PDF-Dokumente ab, die in das RAG geladen werden sollen.

Beispiele:
- `anlagen/p24_handbuch.pdf`
- `wartung/wartungsplan_2026.pdf`

PDF-Ingestion direkt starten:

```bash
python app/scripts/ingest_rag_pdf.py --input-dir rag/pdf
```

Optional zusätzlich Markdown-Version erzeugen:

```bash
python app/scripts/ingest_rag_pdf.py --input-dir rag/pdf --export-markdown-dir rag/markdown/pdf_converted
```
