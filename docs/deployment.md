# Deployment & Konfiguration

## 1. Voraussetzungen

| Dienst | Mindestversion | Bemerkung |
|---|---|---|
| Python | 3.11 | Im Dockerfile; 3.12 für `langgraph dev` |
| Docker + Docker Compose | 24+ | Für Container-Deployment |
| Neo4j | 5 | Extern oder via Compose (auskommentiert) |
| Redis | 7 | In Compose enthalten |
| ChromaDB | latest | In Compose enthalten |
| Apache Kafka | 3.x | Extern (Compose-Konfiguration auskommentiert) |
| OPC UA Server | – | Extern (Produktionsanlage) |
| LLM (Ollama) | – | Extern; OpenAI-API-kompatibler Endpunkt |

---

## 2. Umgebungsvariablen

Alle Variablen können über `.env` oder Docker-Umgebungsvariablen gesetzt werden.  
Standard-Werte eignen sich für lokale Entwicklung.

| Variable | Standard | Beschreibung |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt-Endpunkt |
| `NEO4J_USER` | `neo4j` | Neo4j Benutzername |
| `NEO4J_PASSWORD` | `password` | Neo4j Passwort |
| `REDIS_URL` | `redis://localhost:6379` | Redis-Verbindungs-URL |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka Broker (kommagetrennt bei mehreren) |
| `KAFKA_COMMAND_TOPIC` | `plant.commands` | Kafka-Topic für Steuerbefehle |
| `OPCUA_ENDPOINT` | `opc.tcp://localhost:4840` | Standard OPC UA Endpunkt |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-kompatibler LLM-Endpunkt |
| `LLM_MODEL` | `llama3` | Modellname (Produktion: `qwen3:32b`) |
| `LLM_API_KEY` | `ollama` | API-Key (bei Ollama beliebig) |
| `CHROMA_HOST` | `localhost` | ChromaDB Hostname |
| `CHROMA_PORT` | `8001` | ChromaDB Port |
| `CHROMA_COLLECTION` | `plant_docs` | ChromaDB Collection-Name |
| `ENTITY_FUZZY_THRESHOLD` | `0.6` | Fuzzy-Matching-Schwellwert für Entitäten |

---

## 3. Lokale Entwicklung

### 3.1 Abhängigkeiten installieren

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 FastAPI-Server starten

```bash
uvicorn app.main:app --reload --port 8000
```

### 3.3 LangGraph-Server starten (für Chat-UI)

```bash
langgraph dev
# Läuft auf http://localhost:2024
```

### 3.4 Chat-UI starten

```bash
cd agent-chat-ui
npm install
npm run dev
# Läuft auf http://localhost:3000
# Verbindet sich mit NEXT_PUBLIC_API_URL=http://localhost:2024
```

### 3.5 Tests ausführen

```bash
python -m pytest tests/
```

Alle externen Services (Neo4j, Redis, OPC UA, Kafka, ChromaDB, LLM) sind in den Tests gemockt.

---

## 4. Docker-Compose Deployment

```bash
docker compose up --build
```

Verfügbare Endpunkte nach Start:

| Dienst | URL |
|---|---|
| FastAPI (REST API) | http://localhost:8000 |
| Chat-UI | http://localhost:3001 |
| ChromaDB | http://localhost:8001 |
| Redis | localhost:6379 |

### Produktionskonfiguration (docker-compose.yml)

Im gelieferten `docker-compose.yml` sind Neo4j, Kafka und Zookeeper **auskommentiert**, da sie extern betrieben werden.  
Die IP-Adressen für externen Zugriff sind über Umgebungsvariablen im `api`-Service konfiguriert:

```yaml
environment:
  - NEO4J_URI=bolt://172.17.12.104:7687
  - KAFKA_BOOTSTRAP_SERVERS=172.17.200.155:9092
  - OPCUA_ENDPOINT=opc.tcp://172.17.54.3:4842
  - LLM_BASE_URL=http://172.17.12.104:11434/v1
  - LLM_MODEL=qwen3:32b
```

---

## 5. API-Endpunkte (FastAPI)

### `POST /chat`

Hauptendpunkt für Nutzereingaben.

**Request:**
```json
{
  "message": "Wie viele Schritte hat der Produktionsplan von Anlage A?",
  "session_id": "optional-uuid"
}
```

**Response (normale Antwort):**
```json
{
  "session_id": "uuid",
  "response": "Ergebnis für get_steps auf Asset asset-001: 5 Einträge...",
  "requires_confirmation": false,
  "intent": "get_steps",
  "capability": "neo4j",
  "submodel": "ProductionPlan"
}
```

**Response (Bestätigung erforderlich):**
```json
{
  "session_id": "uuid",
  "response": "Soll der Befehl 'start' wirklich ausgeführt werden? Asset: asset-001",
  "requires_confirmation": true,
  "confirmation_message": "Soll der Befehl 'start' wirklich ausgeführt werden? Asset: asset-001",
  "capability": "kafka"
}
```

---

### `POST /chat/confirm`

Bestätigt oder bricht eine ausstehende Kafka-Aktion ab.

**Request:**
```json
{
  "session_id": "uuid",
  "confirmed": true
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "response": "Befehl ausgeführt: {...}",
  "requires_confirmation": false
}
```

---

### `DELETE /sessions/{session_id}`

Löscht den gespeicherten Session-Kontext aus Redis.

---

### `GET /health`

Liveness-Probe.

```json
{"status": "ok"}
```

---

## 6. LangGraph Server – Endpunkte

Beim Betrieb mit `langgraph dev` stellt der LangGraph-Server zusätzlich bereit:

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/runs` | Neuen Graph-Run starten |
| `POST` | `/runs/stream` | Streaming-Run (SSE) |
| `GET` | `/runs/{run_id}` | Run-Status abfragen |
| `GET` | `/threads` | Alle Threads auflisten |

Die Chat-UI nutzt das offizielle `@langchain/langgraph-sdk`.
