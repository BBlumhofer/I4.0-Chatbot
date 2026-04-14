# Chatbot Fragen-Test (2026-04-08)

## Testkontext
- Ausfuehrung: direkter LangGraph-Lauf mit `graph.invoke({"user_input": ...})`
- Ort: Projekt `I4.0-Chatbot`
- Beobachtung: LLM-Modell `llama3` nicht verfuegbar und Chroma-Server nicht erreichbar.
- Folge: Fachfragen wurden als RAG geroutet und scheiterten an Chroma; Meta-/Toollisten-Fragen lieferten dennoch verwertbare Antworten aus eingebauter Fallback-Logik.

## Ergebnisuebersicht
- Gesamtfragen: 10
- Erfolgreich: 4
- Fehlgeschlagen: 6

## Dokumentation je Frage

### 1) Frage
**Hallo**

**Erfolg:** Ja

**Antwort:**
> Hallo! Ich helfe dir gerne weiter. Fur diese allgemeine Frage habe ich kein Tool verwendet.
>
> Wenn du willst, kann ich als Nachstes direkt mit Tools arbeiten. Verfugbare Tool-Gruppen sind:
> Neo4j (Submodelle): AssetInterfaceDescription, Availability, BillOfApplications, BillOfMaterial, CarbonFootprint, ConditionMonitoring, DesignOfProduct, FaultDescription, MachineSchedule, MachineScheduleLog, MaterialData, Nameplate, OfferedCapabilityDescription, ProductIdentification, ProductionPlan, QualityInformation, RequiredCapabilityDescription, SituationLog, Skills, StorageConfiguration, Structure, SymptomDescription, TechnicalData
> OPC UA: browse, connect_to_server, disconnect, get_live_status, lock_server, read_value
> RAG: search_docs
> Kafka: send_command
>
> Nenne mir einfach eine konkrete Frage, z. B. zu einem Asset, Modul oder einer Live-Abfrage.

### 2) Frage
**Was kannst du?**

**Erfolg:** Ja

**Antwort:**
> Hi! Ich bin dein I4.0-Chatbot fur Anlagenwissen und Live-Daten. Fur diese Meta-Frage habe ich kein RAG und kein anderes Tool verwendet.
>
> Ich kann dir helfen bei:
> - Doku- und Architekturfragen via RAG
> - Asset-/Submodellabfragen aus Neo4j
> - Live-Werten aus OPC UA
> - Befehlen via Kafka (mit Bestatigung)
>
> Frag mich am besten konkret, z. B.: 'Was ist P17 und welche Skills hat es?'

### 3) Frage
**Welche Tools kennst du?**

**Erfolg:** Ja

**Antwort:**
> Ich kenne folgende Tool-Gruppen:
>
> Neo4j-Tools (globale Ubersicht):
> - AssetInterfaceDescription: get_interface_description, get_properties
> - Availability: get_availability_overview, get_machine_state, get_properties, list_unavailability_blocks, list_unavailability_reasons
> - BillOfApplications: get_application_stack, get_properties, list_applications
> - BillOfMaterial: get_bom, get_hierarchy, get_parts, get_properties, get_structure, list_parts
> - CarbonFootprint: get_footprint_overview, get_goods_address_handover, get_properties
> - ConditionMonitoring: get_condition_history, get_properties
> - DesignOfProduct: get_author_info, get_design_overview, get_model_descriptor, get_properties
> - FaultDescription: get_fault_descriptions, get_properties
> - MachineSchedule: get_last_update, get_properties, get_schedule, has_open_tasks, list_schedule_entries
> - MachineScheduleLog: get_last_update_log, get_properties, get_schedule_log, list_log_entries
> - MaterialData: get_material_data, get_properties
> - Nameplate: get_country_of_origin, get_date_of_manufacture, get_hardware_version, get_manufacture_date, get_manufacturer_name, get_manufacturer_product_designation, get_manufacturer_product_family, get_manufacturer_product_root, get_manufacturer_product_type, get_nameplate, get_nameplate_element, get_product_uri, get_properties, get_software_version, get_uri_of_the_product, get_year_of_construction, list_address_information, list_contact_channels
> - OfferedCapabilityDescription: get_capability_by_id_short, get_properties, list_capabilities, list_capability_sets, list_properties_by_container
> - ProductIdentification: get_additional_information, get_product_identification, get_properties
> - ProductionPlan: check_done, get_properties, get_step_duration, get_steps, is_finished, list_steps
> - QualityInformation: get_properties, get_quality_by_id_short, get_quality_information
> - RequiredCapabilityDescription: get_properties, get_required_capability_by_id_short, list_required_capabilities, list_required_property_sets
> - SituationLog: get_properties, get_situation_by_id_short, list_situations
> - Skills: get_properties, get_skills
> - StorageConfiguration: get_demand_config, get_projection_config, get_properties, list_slots, list_storages
> - Structure: get_hierarchy, get_parts, get_properties, get_structure, list_parts
> - SymptomDescription: get_properties, get_symptom_by_id_short, list_symptoms
> - TechnicalData: get_further_information, get_general_information, get_properties
>
> OPC UA: browse, connect_to_server, disconnect, get_live_status, lock_server, read_value
> RAG: search_docs
> Kafka: send_command
>
> Wenn du asset-spezifische Details willst, nenne bitte das Asset (z. B. 'Anlage A').

### 4) Frage
**Wie heisst der Hersteller von Anlage A?**

**Erfolg:** Nein

**Antwort:**
> Das hat leider nicht geklappt. Fehler: Could not connect to a Chroma server. Are you sure it is running?

### 5) Frage
**Wann wurde Anlage A hergestellt?**

**Erfolg:** Nein

**Antwort:**
> Das hat leider nicht geklappt. Fehler: Could not connect to a Chroma server. Are you sure it is running?

### 6) Frage
**Welche Adresse und Kontaktdaten hat Anlage A?**

**Erfolg:** Nein

**Antwort:**
> Das hat leider nicht geklappt. Fehler: Could not connect to a Chroma server. Are you sure it is running?

### 7) Frage
**Welche technischen Daten hat Anlage C?**

**Erfolg:** Nein

**Antwort:**
> Das hat leider nicht geklappt. Fehler: Could not connect to a Chroma server. Are you sure it is running?

### 8) Frage
**Welche Quality-Informationen hat Anlage C?**

**Erfolg:** Nein

**Antwort:**
> Das hat leider nicht geklappt. Fehler: Could not connect to a Chroma server. Are you sure it is running?

### 9) Frage
**Welche Capabilities werden fuer Anlage C benoetigt?**

**Erfolg:** Nein

**Antwort:**
> Das hat leider nicht geklappt. Fehler: Could not connect to a Chroma server. Are you sure it is running?

### 10) Frage
**Fasse die Doku zur Gesamtanlage kurz zusammen.**

**Erfolg:** Ja (nur Fallback-Text)

**Antwort:**
> Ich habe in dieser Session noch keine belastbare Doku-Zusammenfassung gespeichert. Stelle bitte zuerst eine konkrete Fachfrage (z. B. zu P17), dann fasse ich sie dir zusammen.

## Kurzfazit
- Die Antwortdokumentation ist vollstaendig vorhanden (alle Fragen + Antworten + Erfolgsstatus).
- Produktive Fachantworten sind aktuell durch zwei Infrastrukturthemen blockiert:
  - lokales LLM-Modell `llama3` nicht vorhanden
  - ChromaDB unter konfigurierter Adresse nicht erreichbar
