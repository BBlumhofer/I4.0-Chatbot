# ADR 001 – LangGraph als Orchestrierungsframework

**Status:** Accepted  
**Datum:** 2025  
**Kontext:** I4.0-Chatbot v0.1

---

## Kontext

Für den I4.0-Chatbot wird ein Framework benötigt, das:

1. Mehrere externe Datenquellen (Neo4j, OPC UA, Kafka, ChromaDB) orchestriert
2. Zustandsbehaftete Mehrturngespräche ermöglicht
3. Einen expliziten Confirmation-Flow für schreibende Aktionen unterstützt
4. Mit einer Chat-UI integrierbar ist
5. Lokal ohne Cloud-Abhängigkeit betrieben werden kann

---

## Entscheidung

**LangGraph** (LangChain) wird als Orchestrierungsframework verwendet.

Der Agent ist als expliziter **gerichteter azyklischer Graph** (DAG) mit bedingten Kanten modelliert.  
Die Knoten sind reine Python-Funktionen; der Zustand fließt als `TypedDict` (`AgentState`) durch alle Knoten.

---

## Begründung

### Pro LangGraph

| Kriterium | Begründung |
|---|---|
| **Expliziter Kontrollfuss** | Der Graph ist vollständig in Code definiert und in `graph.py` dokumentiert. Kein implizites Chain-of-Thought-Routing. |
| **Zustandsverwaltung** | `AgentState` als TypedDict gibt vollständige Kontrolle über alle Zustandsfelder – kein versteckter Memory-Layer. |
| **Bedingte Kanten** | Der Confirmation-Flow (Kafka-Bestätigung) ist natürlich als `conditional_edge` abbildbar. |
| **LangGraph Server** | Out-of-the-box HTTP-/SSE-Server mit `langgraph dev`; kompatibel mit `agent-chat-ui`. |
| **Erweiterbarkeit** | Neue Knoten und Kanten können ohne Umbau des bestehenden Graphen ergänzt werden. |
| **Python-nativ** | Volle Kontrolle über Implementierungsdetails; keine Abstraktionsebene zwischen Knoten und Services. |

### Alternativen (verworfen)

| Alternative | Grund für Ablehnung |
|---|---|
| LangChain LCEL | Keine explizite Zustandsverwaltung; schwierige Umsetzung des Confirmation-Flows |
| LlamaIndex Agents | Weniger Kontrolle über den Ausführungsfluss; schlechtere Unterstützung für multi-step Workflows |
| AutoGen | Primär für Multi-Agent-Kommunikation ausgelegt; Overhead für Single-Agent-Use-Case |
| Custom FastAPI ohne Framework | Mehr Boilerplate; kein eingebautes Session/State-Management für Graphen |

---

## Konsequenzen

### Positiv
- Der Ausführungsfluss ist vollständig transparent und nachvollziehbar
- Jeder Knoten ist isoliert testbar (alle externen Services werden gemockt)
- Die Chat-UI kann direkt mit dem LangGraph-Server kommunizieren

### Negativ / Risiken
- LangGraph befindet sich noch in aktiver Entwicklung; Breaking Changes sind möglich
- `langgraph dev` ist für Entwicklung gedacht; Produktions-Deployment benötigt separaten uvicorn-Server
- Die Synchron/Async-Grenze (OPC UA ist async, LangGraph-Knoten sind sync) erfordert `asyncio.run()`-Wrapper

---

## Referenzen

- [LangGraph Dokumentation](https://langchain-ai.github.io/langgraph/)
- `app/graph/graph.py` – Graphdefinition
- `app/graph/nodes.py` – Knotenimplementierungen
- `langgraph.json` – Server-Konfiguration
