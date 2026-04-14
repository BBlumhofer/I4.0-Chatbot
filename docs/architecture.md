# Softwarearchitektur – I4.0 Produktionsanlagen-Assistent

## 1. Überblick

Der I4.0-Chatbot ist ein **LLM-gestützter, zustandsbasierter Assistent** für industrielle Produktionsanlagen.  
Er verbindet natürlichsprachliche Nutzereingaben mit vier industriellen Datenbereichen:

| Capability | Zweck | Technologie |
|---|---|---|
| **neo4j** | Asset-Daten, AAS-Submodelle, MES-Informationen | Neo4j Graph-DB |
| **opcua** | Live-Zustände, Sensorwerte, Steuerung | OPC UA (asyncua) |
| **rag** | Dokumentation, Handbücher, Erklärungen | ChromaDB + Embeddings |
| **kafka** | Steuerbefehle an die Anlage | Apache Kafka |

---

## 2. Systemübersicht (C4 – Context)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Operator / Instandhalter                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Browser
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  agent-chat-ui  (Next.js)                                            │
│  Port 3000  –  LangGraph Chat-UI                                     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ LangGraph Server Protocol (HTTP/SSE)
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LangGraph Server  (langgraph dev / uvicorn)                         │
│  Port 2024  –  graph entry: app/graph/graph.py:graph                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  LangGraph Agent  (app/graph/)                                 │  │
│  │                                                                │  │
│  │  interpret → resolve → route → select → confirm → execute      │  │
│  │                              → generate_response               │  │
│  └───────┬────────────┬───────────────┬──────────────┬───────────┘  │
│          │            │               │              │               │
└──────────┼────────────┼───────────────┼──────────────┼───────────────┘
           │            │               │              │
           ▼            ▼               ▼              ▼
        Neo4j        OPC UA          ChromaDB        Kafka
     (Graph-DB)    (Live-PLC)     (Vector-Store)  (Command Bus)
```

Zusätzlich läuft die **FastAPI**-Anwendung (`app/main.py`) auf Port 8000 als klassische REST-API (alternativ zum LangGraph-Server-Protokoll).

---

## 3. Container-Architektur (C4 – Container)

```
┌─────────────────── Docker Compose ──────────────────────────────────┐
│                                                                      │
│  ┌──────────────┐    HTTP    ┌──────────────────────────────────┐   │
│  │ agent-chat-ui│──────────▶│  api  (FastAPI / uvicorn)         │   │
│  │ Next.js :3001│           │  Port 8000                        │   │
│  └──────────────┘           │  app/main.py                      │   │
│                             └────────────┬─────────────────────┘   │
│                                          │                          │
│                      ┌───────────────────┼───────────────────────┐  │
│                      │                   │                       │  │
│                      ▼                   ▼                       ▼  │
│              ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│              │  redis :6379 │   │ chroma :8001 │   │  Neo4j*      │ │
│              │  Session-TTL │   │ Vector Store │   │  :7687       │ │
│              └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                      │
│  * Neo4j, Kafka, OPC UA laufen extern (außerhalb Compose)           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Schichtenmodell (C4 – Component)

```
app/
├── main.py                  # FastAPI-App, CORS, Router-Registrierung
├── config.py                # Zentrale Konfiguration (pydantic-settings)
│
├── api/
│   └── routes.py            # REST-Endpunkte: POST /chat, POST /chat/confirm,
│                            #   DELETE /sessions/{id}, GET /health
│
├── graph/
│   ├── state.py             # AgentState (TypedDict) – gemeinsamer Zustand
│   ├── nodes.py             # 8 Node-Funktionen (rein, keine Seiteneffekte)
│   └── graph.py             # Graphaufbau + Kompilierung; Einstieg für langgraph.json
│
├── llm/
│   └── interpreter.py       # LLM-Aufruf → intent / capability / submodel / entities
│
├── services/                # Thin Wrapper um externe Systeme
│   ├── neo4j_service.py     # Neo4j Driver, Cypher-Helpers, Entity-Resolution
│   ├── opcua_service.py     # asyncua Client, ConnectionManager, sync Wrapper
│   ├── kafka_service.py     # KafkaProducer, send_command
│   ├── rag_service.py       # ChromaDB HttpClient, search_docs, add_document
│   └── session_service.py   # Redis-Session (get/save/update/delete)
│
└── tools/
    ├── neo4j_tools.py       # (Legacy-Kompatibilitäts-Import)
    ├── opcua_tools.py       # OPCUA_TOOL_REGISTRY
    ├── kafka_tools.py       # KAFKA_TOOL_REGISTRY
    ├── rag_tools.py         # RAG_TOOL_REGISTRY
    └── neo4j/               # Per-Submodell-Toolsets (AAS)
        ├── _base.py         # SubmodelToolset + register_submodel()
        ├── __init__.py      # SUBMODEL_REGISTRY, get_available_submodels()
        ├── production_plan.py
        ├── bill_of_material.py
        ├── structure.py
        ├── nameplate.py
        ├── material_data.py
        ├── skills.py
        ├── asset_interface_description.py
        ├── fault_description.py
        └── condition_monitoring.py
```

---

## 5. Datenfluss – Sequenz

```
Nutzer
  │
  │  "Wie viele Schritte hat der Produktionsplan von Anlage A?"
  ▼
interpret_input
  │  LLM → { intent: "get_steps", capability: "neo4j",
  │           submodel: "ProductionPlan", entities: {asset: "Anlage A"} }
  ▼
resolve_entities
  │  Neo4j fuzzy-search → asset_id = "asset-001"
  ▼
route_capability
  │  capability == "neo4j"
  ▼
validate_submodel
  │  "ProductionPlan" ∈ VALID_SUBMODELS ✓
  ▼
select_tool_neo4j
  │  intent "get_steps" → tool_fn = production_plan.get_steps
  │  requires_confirmation = False
  ▼
check_confirmation
  │  False → weiter
  ▼
execute_tool
  │  get_steps(asset_id="asset-001") → [{step, status, duration}, ...]
  ▼
generate_response
  │  AIMessage("Ergebnis für get_steps auf Asset asset-001: 5 Einträge...")
  ▼
Nutzer sieht Antwort
```

---

## 6. Confirmation-Flow (Kafka / OPC UA)

Steuerbefehle erfordern explizite Bestätigung durch den Operator:

```
select_tool_generic
  │  requires_confirmation = True
  │  confirmation_message = "Soll Befehl X wirklich ausgeführt werden?"
  ▼
check_confirmation
  │  True → END  (Graph endet, API gibt confirmation_message zurück)

  Operator bestätigt via POST /chat/confirm { confirmed: true }
  │
  ▼
execute_tool  (direkt aus routes.py aufgerufen, nicht erneut über Graph)
  ▼
Kafka → plant.commands Topic
```

---

## 7. AgentState

Alle Knoten lesen und schreiben einen gemeinsamen `AgentState` (TypedDict):

| Feld | Typ | Beschreibung |
|---|---|---|
| `messages` | `list[BaseMessage]` | Gesprächshistorie (LangGraph SDK) |
| `session_id` | `str` | Redis-Session-Schlüssel |
| `user_input` | `str` | Rohtext der Nutzereingabe |
| `intent` | `str` | LLM-extrahierte Absicht |
| `capability` | `str` | `neo4j` / `opcua` / `rag` / `kafka` |
| `submodel` | `str?` | AAS-Submodell (nur neo4j) |
| `entities` | `dict` | Extrahierte Entitäten (z. B. Asset-Name) |
| `resolved_entities` | `dict` | Aufgelöste System-IDs |
| `tool_name` | `str` | Ausgewählte Tool-Funktion |
| `tool_args` | `dict` | Argumente für das Tool |
| `requires_confirmation` | `bool` | Bestätigung erforderlich? |
| `confirmation_message` | `str` | Anzuzeigende Bestätigungsnachricht |
| `tool_result` | `Any` | Rückgabewert des Tools |
| `response` | `str` | Finaler Antworttext |
| `error` | `str?` | Fehlermeldung bei Ausnahmen |

---

## 8. AAS-Submodell-Erweiterbarkeit

Neues Submodell in drei Schritten hinzufügen:

1. `app/tools/neo4j/my_submodel.py` erstellen und `register_submodel(SubmodelToolset(...))` aufrufen
2. Import in `app/tools/neo4j/__init__.py` ergänzen
3. LLM-Prompt in `app/llm/interpreter.py` um das neue Submodell erweitern

Das `SUBMODEL_REGISTRY`-Dict und `VALID_SUBMODELS` werden automatisch aktualisiert.

---

## 9. Technologie-Stack

| Bereich | Technologie | Version |
|---|---|---|
| Agent-Framework | LangGraph | latest |
| LLM-Integration | OpenAI-kompatibler Endpunkt (Ollama) | qwen3:32b / llama3 |
| API | FastAPI + uvicorn | – |
| Graph-DB | Neo4j | 5 |
| OPC UA | asyncua | – |
| Message Bus | Apache Kafka | – |
| Vector Store | ChromaDB | latest |
| Session Store | Redis | 7 |
| Chat-UI | Next.js (agent-chat-ui) | – |
| Konfiguration | pydantic-settings (.env) | – |
| Tests | pytest | – |
