# Zielbild – I4.0 Produktionsanlagen-Assistent

## Vision

Ein **natürlichsprachlicher, zustandsbasierter Assistent** für Industrie-4.0-Produktionsanlagen,  
der Operatoren und Instandhaltern ermöglicht, **komplexe Anlagendaten ohne technisches Vorwissen**  
abzufragen, zu interpretieren und – nach expliziter Bestätigung – Steuerbefehle auszulösen.

---

## 1. Zielbild auf einen Blick

```
┌────────────────────────────────────────────────────────────────────┐
│                         Operator                                    │
│                                                                     │
│  "Welche Fehler hat Roboter R3 in den letzten 24h gemeldet?"       │
│  "Starte Produktionsplan Schritt 3 – aber nur wenn Schritt 2 done" │
│  "Erkläre mir was der Fehlercode E-4711 bedeutet"                  │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   I4.0-Chatbot-Agent   │
                    │   (LangGraph)          │
                    │                        │
                    │  • versteht Kontext    │
                    │  • multi-turn fähig    │
                    │  • erklärt Quellen     │
                    │  • schützt vor Fehlern │
                    └────────────┬───────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
        AAS-Graph            Live-Daten         Dokumentation
        (Neo4j)              (OPC UA)           (ChromaDB)
             │                                       │
             └──────────────────┬────────────────────┘
                                ▼
                    Kafka → Steuerbefehl an Anlage
                           (nach Bestätigung)
```

---

## 2. Kernziele

### 2.1 Einheitliche Datenzugriffsschicht
- Alle industriellen Datenquellen (AAS/Neo4j, OPC UA, RAG, Kafka) über **eine** natürlichsprachliche Schnittstelle zugänglich
- Kein Wechsel zwischen verschiedenen Tools oder Systemen für den Operator

### 2.2 Asset Administration Shell (AAS) als Wissensquelle
- Das Asset-Wissen der Anlage ist vollständig in Neo4j als **Property Graph** abgebildet
- Alle AAS-Submodelle (Nameplate, BillOfMaterial, ProductionPlan, Skills, etc.) sind über spezialisierte Tools abfragbar
- Neue Submodelle können **ohne Code-Änderungen am Graphen** hinzugefügt werden

### 2.3 Sicherheit durch Confirmation-Flow
- Schreibende Aktionen (Kafka-Steuerbefehle) erfordern immer eine **explizite Bestätigung** des Operators
- Kein unbeabsichtigtes Auslösen von Maschinenbefehlen

### 2.4 Kontextuelles Mehrturngespräch
- Der Assistent erinnert sich über mehrere Nachrichten hinweg an den Kontext (aktuelles Asset, Submodell)
- Folgefragen wie „und welche Schritte hat er noch?" funktionieren ohne erneute Asset-Angabe

### 2.5 Lokale LLM-Infrastruktur
- Kein Cloud-Anbieter erforderlich – LLM läuft lokal via Ollama
- Datenschutz: Anlagen- und Produktionsdaten verlassen das Netzwerk nicht

---

## 3. Aktueller Stand (v0.1)

| Feature | Status |
|---|---|
| LangGraph-Zustandsautomat (8 Knoten) | ✅ Implementiert |
| 4 Capabilities: neo4j, opcua, rag, kafka | ✅ Implementiert |
| 9 AAS-Submodelle | ✅ Implementiert |
| FastAPI REST-API | ✅ Implementiert |
| LangGraph Server-Integration (Chat-UI) | ✅ Implementiert |
| Session-Management (Redis) | ✅ Implementiert |
| Confirmation-Flow für Kafka | ✅ Implementiert |
| Multi-Server OPC UA | ✅ Implementiert |
| Docker Compose Deployment | ✅ Implementiert |
| Unit-Tests (pytest, gemockte Services) | ✅ Implementiert |

---

## 4. Roadmap – Nächste Schritte

### Kurzfristig (v0.2)

- [ ] **LLM-gestützte Antwortgenerierung:** Statt Template-Texten das LLM für die endgültige Antwortformulierung nutzen (`generate_response` erweitern)
- [ ] **Entity-Disambiguierung:** Bei mehreren Asset-Treffern den Nutzer per Rückfrage zur Auswahl auffordern (statt silent fallback)
- [ ] **RAG-Ingestion-Pipeline:** CLI/Script zum Einlesen von Betriebsanleitungen und Fehlerkatalogen in ChromaDB
- [ ] **Streaming-Responses:** SSE-basiertes Streaming über LangGraph Server für bessere UX

### Mittelfristig (v0.3)

- [ ] **AAS-Submodell-Erkennung aus Neo4j:** Bei jeder Anfrage prüfen, welche Submodelle für das erkannte Asset tatsächlich in Neo4j vorhanden sind (`get_available_submodels`) und nur diese ins LLM-Prompt laden
- [ ] **Mehrsprachigkeit:** Englische Eingaben neben Deutsch unterstützen
- [ ] **Audit-Log:** Alle Kafka-Befehle mit Operator-ID und Zeitstempel persistieren
- [ ] **Erweiterte OPC UA-Tools:** Schreibzugriff (mit Confirmation-Flow), Subscription/Monitoring

### Langfristig (v1.0)

- [ ] **Proaktive Alerts:** Agent überwacht OPC UA-Nodes und alarmiert bei Grenzwertüberschreitungen
- [ ] **AAS-Graphen-Update:** Agent kann AAS-Daten in Neo4j aktualisieren (z. B. Produktionsstatus)
- [ ] **Rollenbasierter Zugriff:** Unterschiedliche Berechtigungen für Operator vs. Instandhalter vs. Admin
- [ ] **Multimodale Eingaben:** Bilder von Fehlerbildern oder QR-Codes von Anlagenteilen als Eingabe
- [ ] **Anbindung weiterer Datenquellen:** SCADA-Systeme, ERP, Historian-Datenbanken
- [ ] **Horizontal Skalierung:** LangGraph in produktionsreifem Kubernetes-Setup mit persistenten Checkpoints

---

## 5. Architekturprinzipien

### Erweiterbarkeit vor Vollständigkeit
Neue Submodelle, Capabilities und Tools sollen mit minimalem Aufwand hinzufügbar sein.  
Das `SubmodelToolset`-Registrierungsmuster ist bewusst einfach gehalten.

### Separation of Concerns
- **Graph-Knoten** sind reine Funktionen ohne Seiteneffekte
- **Services** kapseln alle externen Abhängigkeiten
- **Tools** sind dünne Wrapper über Services

### Safety by Design
- Steuerbefehle erfordern immer eine Bestätigung
- Fallbacks auf sichere Defaults bei LLM-Fehlern

### Lokale Datensouveränität
- LLM läuft lokal (Ollama)
- Alle Produktionsdaten bleiben im lokalen Netzwerk
