# LangGraph – Zustandsautomat

Dieser Abschnitt beschreibt den LangGraph-Graphen, der das Herzstück des Chatbots bildet.  
Implementierung: `app/graph/graph.py`, Knoten: `app/graph/nodes.py`, Zustand: `app/graph/state.py`.

---

## 1. Vollständiger Graph

```
                    ┌─────────────────┐
                    │  interpret_input │  ◀── Einstiegspunkt
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ resolve_entities│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ route_capability│
                    └────────┬────────┘
            ┌────────────────┼──────────────────────┐
            │ neo4j          │ opcua / rag / kafka   │
   ┌────────▼───────┐        │                      │
   │validate_submodel│       │                      │
   └────────┬────────┘       │                      │
            │        ┌───────▼────────┐             │
   ┌────────▼────────│select_tool_    │◀────────────┘
   │select_tool_neo4j│  generic       │
   └────────┬────────┴───────┬────────┘
            └───────┬────────┘
                    │
          ┌─────────▼──────────┐
          │ check_confirmation  │
          └─────────┬──────────┘
           ┌────────┴──────────┐
     confirm│                  │execute
           ▼                   ▼
          END          ┌──────────────┐
                       │ execute_tool │
                       └──────┬───────┘
                              │
                    ┌─────────▼────────┐
                    │generate_response │
                    └─────────┬────────┘
                              │
                             END
```

---

## 2. Knoten im Detail

### `interpret_input`
- **Eingabe:** `user_input` (direkt) oder letztes `HumanMessage` in `messages`
- **Aktion:** Ruft `app/llm/interpreter.interpret()` auf (lokaler OpenAI-kompatibler Endpunkt)
- **Ausgabe:** `intent`, `capability`, `submodel`, `entities`
- **Fallback:** Bei LLM-Fehler → `capability=rag`, `intent=unknown`

### `resolve_entities`
- **Eingabe:** `entities` (z. B. `{asset: "Anlage A"}`)
- **Aktion:** Neo4j-Fuzzy-Suche auf dem `Asset`-Knoten (CONTAINS, case-insensitiv)
- **Ausgabe:** `resolved_entities` mit `asset_id`, `asset_name`, `asset_type`
- **Session-Persistenz:** Löst `asset_id` wird in Redis für Folge-Turns gespeichert
- **Disambiguierung:** Bei mehreren Treffern → `disambiguation`-Liste in `resolved_entities`

### `route_capability`
- **Eingabe:** `capability`
- **Aktion:** Validiert gegen `{"neo4j", "opcua", "rag", "kafka"}`; Fallback → `rag`
- **Ausgabe:** validiertes `capability`
- **Routing:** Conditional Edge → `validate_submodel` (neo4j) oder `select_tool_generic` (alle anderen)

### `validate_submodel`  *(nur neo4j-Pfad)*
- **Eingabe:** `submodel`
- **Aktion:** Prüft gegen `VALID_SUBMODELS`; Fallback → `"Structure"`
- **Session-Persistenz:** Aktuelles Submodell wird in Redis gespeichert

### `select_tool_neo4j`  *(nur neo4j-Pfad)*
- **Eingabe:** `submodel`, `intent`, `resolved_entities`
- **Aktion:**
  1. Direktes Intent-Matching gegen `SUBMODEL_REGISTRY[submodel]["tools"]`
  2. Fallback-Mapping (z. B. `list_steps` → `get_steps`)
  3. Letzter Fallback: `get_properties`
- **Ausgabe:** `tool_name`, `tool_args`, `requires_confirmation=False`

### `select_tool_generic`  *(opcua / rag / kafka)*
- **Eingabe:** `capability`, `intent`, `resolved_entities`, `entities`
- **Aktion:** Intent-basierte Tool-Auswahl je Capability
  - `opcua`: connect / disconnect / browse / lock / read_value / get_live_status
  - `kafka`: immer `send_command`, setzt `requires_confirmation=True`
  - `rag`: immer `search_docs`
- **Ausgabe:** `tool_name`, `tool_args`, `requires_confirmation`, `confirmation_message`

### `check_confirmation`
- **Aktion:** Reines Routing (keine State-Mutation)
- **Conditional Edge:**
  - `requires_confirmation == True` → `END` (API gibt `confirmation_message` zurück)
  - sonst → `execute_tool`

### `execute_tool`
- **Eingabe:** `capability`, `tool_name`, `tool_args`
- **Aktion:** Dispatcht an das passende Tool-Registry-Dict; führt `tool_fn(**tool_args)` aus
- **Ausgabe:** `tool_result`, `error`

### `generate_response`
- **Eingabe:** `tool_result`, `error`, `capability`, `intent`
- **Aktion:** Erzeugt deutschen Antworttext; hängt `AIMessage` an `messages`
- **Ausgabe:** `response`, `messages`

---

## 3. Conditional Edges

| Quellknoten | Bedingung | Zielknoten |
|---|---|---|
| `route_capability` | `capability == "neo4j"` | `validate_submodel` |
| `route_capability` | `capability ∈ {opcua, rag, kafka}` | `select_tool_generic` |
| `check_confirmation` | `requires_confirmation == True` | `END` |
| `check_confirmation` | `requires_confirmation == False` | `execute_tool` |

---

## 4. LangGraph Server

Die Datei `langgraph.json` registriert den kompilierten Graphen:

```json
{
  "graphs": {
    "agent": "./app/graph/graph.py:graph"
  },
  "python_version": "3.12",
  "dependencies": ["."]
}
```

Gestartet mit `langgraph dev` auf Port 2024.  
Die Chat-UI verbindet sich via `NEXT_PUBLIC_API_URL=http://localhost:2024`.

---

## 5. Session-Management

```
Redis Key: session:{session_id}
TTL: 3600 Sekunden

Inhalt:
{
  "current_asset": "asset-001",
  "current_asset_name": "Anlage A",
  "current_submodel": "ProductionPlan",
  "pending_state": {            ← nur während Bestätigung gesetzt
    "tool_name": "send_command",
    "tool_args": {...},
    "capability": "kafka",
    "submodel": null
  }
}
```

Jeder Turn liest den Session-Kontext in `interpret_input` und schreibt ihn in `resolve_entities` und `validate_submodel` zurück.
