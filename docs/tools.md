# Tool-Katalog

Alle verfügbaren Tools, gruppiert nach Capability.  
Tools werden ausschließlich über das `execute_tool`-Node des Graphen oder  
den `/chat/confirm`-Endpunkt aufgerufen.

---

## 1. Neo4j – AAS-Submodelle

Jedes Submodell ist eine `SubmodelToolset`-Instanz mit eigenem Python-Modul unter `app/tools/neo4j/`.  
Das globale `SUBMODEL_REGISTRY`-Dict wird beim Import automatisch befüllt.

### Registrierte Submodelle

| idShort | Beschreibung | Semantic ID |
|---|---|---|
| `ProductionPlan` | Produktionsschritte, Dauer, Status | `https://admin-shell.io/idta/Submodel/ProductionPlan/1/0` |
| `BillOfMaterial` | Stückliste, Teile | `https://admin-shell.io/idta/Submodel/BillOfMaterial/1/0` |
| `Structure` | Aufbau, Komponentenhierarchie | `https://admin-shell.io/idta/Submodel/HierarchicalStructuresEnablingBoM/1/0` |
| `Nameplate` | Typschild-Informationen | `https://admin-shell.io/idta/Submodel/Nameplate/2/0` |
| `MaterialData` | Materialeigenschaften | `https://admin-shell.io/idta/Submodel/MaterialData/1/0` |
| `Skills` | Fähigkeiten einer Ressource | `https://admin-shell.io/idta/Submodel/Skills/1/0` |
| `AssetInterfaceDescription` | Schnittstellenbeschreibung | `https://admin-shell.io/idta/Submodel/AssetInterfaceDescription/1/0` |
| `FaultDescription` | Fehlerbeschreibungen | `https://admin-shell.io/idta/Submodel/FaultDescription/1/0` |
| `ConditionMonitoring` | Zustände, historische Werte | `https://admin-shell.io/idta/Submodel/ConditionMonitoring/1/0` |

### Tools je Submodell

#### ProductionPlan (`app/tools/neo4j/production_plan.py`)
| Tool | Signatur | Beschreibung |
|---|---|---|
| `get_steps` | `(asset_id)` | Alle Schritte, geordnet nach Ausführungsreihenfolge |
| `get_step_duration` | `(asset_id, step)` | Dauer + Status eines bestimmten Schritts |
| `is_finished` | `(asset_id)` | True wenn alle Schritte abgeschlossen |
| `get_properties` | `(asset_id)` | Alle SubmodelElements (generischer Fallback) |

#### BillOfMaterial (`app/tools/neo4j/bill_of_material.py`)
| Tool | Signatur | Beschreibung |
|---|---|---|
| `get_parts` | `(asset_id)` | Direkte Teile der Stückliste |
| `get_properties` | `(asset_id)` | Alle SubmodelElements |

#### Structure (`app/tools/neo4j/structure.py`)
| Tool | Signatur | Beschreibung |
|---|---|---|
| `get_parts` | `(asset_id)` | Direkte strukturelle Teile |
| `get_hierarchy` | `(asset_id)` | Vollständige Hierarchie (bis 5 Ebenen tief) |
| `get_properties` | `(asset_id)` | Alle SubmodelElements |

#### Nameplate, MaterialData, Skills, AssetInterfaceDescription, FaultDescription, ConditionMonitoring
Alle bieten mindestens:
| Tool | Signatur | Beschreibung |
|---|---|---|
| `get_properties` | `(asset_id)` | Alle SubmodelElements (Pflichtfallback) |

---

## 2. OPC UA (`app/tools/opcua_tools.py`)

Registry: `OPCUA_TOOL_REGISTRY`

| Tool | Signatur | Beschreibung |
|---|---|---|
| `connect_to_server` | `(endpoint, username?, password?)` | Verbindung validieren + Credentials registrieren |
| `disconnect` | `(endpoint)` | Credentials entfernen (erfordert Bestätigung) |
| `browse` | `(endpoint, node_id?)` | Kindknoten des Objects-Ordners oder eines bestimmten Knotens auflisten |
| `lock_server` | `(endpoint)` | Server gegen versehentliche Aktionen sperren |
| `get_live_status` | `(endpoint, node_id)` | Vollständiger DataValue (Wert, Status, Zeitstempel) |
| `read_value` | `(endpoint, node_id)` | Rohen Skalarwert lesen |

**Hinweis:** OPC UA-Aufrufe sind intern async (`asyncua`), werden aber über `asyncio.run()` synchron gemacht, da LangGraph-Knoten synchron laufen.

---

## 3. RAG (`app/tools/rag_tools.py`)

Registry: `RAG_TOOL_REGISTRY`

| Tool | Signatur | Beschreibung |
|---|---|---|
| `search_docs` | `(query, n_results=5)` | Semantische Suche über Anlagen-Dokumentation in ChromaDB |

Intern:
- `rag_service.add_document(text, metadata, doc_id)` – Dokument in ChromaDB einfügen (Ingestion-Pipeline)

---

## 4. Kafka (`app/tools/kafka_tools.py`)

Registry: `KAFKA_TOOL_REGISTRY`

| Tool | Signatur | Beschreibung |
|---|---|---|
| `send_command` | `(command: dict)` | JSON-Nachricht auf `plant.commands`-Topic senden |

**Sicherheitsregel:** Jeder Kafka-Aufruf setzt `requires_confirmation=True`.  
Die Ausführung erfolgt erst nach expliziter Bestätigung über `POST /chat/confirm`.

---

## 5. Tool hinzufügen

### Neo4j-Submodell-Tool erweitern
Neue Funktion in der entsprechenden Submodell-Datei hinzufügen und in das `tools`-Dict des `register_submodel()`-Aufrufs eintragen.

### Neues Submodell
1. `app/tools/neo4j/mein_submodell.py` erstellen
2. `register_submodel(SubmodelToolset(idShort=..., semantic_id=..., tools={..., "get_properties": ...}))` aufrufen
3. Import in `app/tools/neo4j/__init__.py` ergänzen
4. Submodell-Name in `SYSTEM_PROMPT` in `app/llm/interpreter.py` ergänzen

### OPC UA / RAG / Kafka
Funktion definieren und in das jeweilige `*_TOOL_REGISTRY`-Dict eintragen.
