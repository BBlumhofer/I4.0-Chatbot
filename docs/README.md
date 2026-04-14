# I4.0-Chatbot – Dokumentation

Willkommen im Dokumentationsordner des **I4.0-Produktionsanlagen-Assistenten**.

## Inhalt

| Datei | Beschreibung |
|---|---|
| [architecture.md](architecture.md) | Gesamtarchitektur: Komponenten, Schichten, Datenfluss |
| [graph.md](graph.md) | LangGraph-Zustandsautomat – Knoten, Kanten, Routing |
| [tools.md](tools.md) | Tool-Katalog je Capability (Neo4j, OPC UA, RAG, Kafka) |
| [deployment.md](deployment.md) | Deployment, Konfiguration, Umgebungsvariablen |
| [target-vision.md](target-vision.md) | Zielbild & Roadmap |
| [adr/001-langgraph-backend.md](adr/001-langgraph-backend.md) | ADR: Wahl von LangGraph als Orchestrierungsframework |

## Schnellübersicht

```
Browser / Chat-UI  (Next.js, Port 3000)
        │  HTTP (LangGraph Server Protocol)
        ▼
LangGraph Server  (langgraph dev, Port 2024)
        │  Python
        ▼
  LangGraph Agent  (app/graph/)
        │
   ┌────┴────┬──────────┬──────────┐
   ▼         ▼          ▼          ▼
 Neo4j    OPC UA       RAG       Kafka
(AAS-KG) (Live-PLC) (ChromaDB) (Befehle)
```

Vollständige Details: → [architecture.md](architecture.md)
