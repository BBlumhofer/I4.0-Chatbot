"""
LangGraph node functions.

Each function takes the current AgentState and returns a (partial) state
update dict.  Nodes are pure functions – side-effects live in services/tools.
"""
from __future__ import annotations

import inspect
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState
from app.llm import interpreter as llm
from app.services import neo4j_service as neo4j_svc
from app.services import session_service as session_svc
from app.tools.neo4j import SUBMODEL_REGISTRY, VALID_SUBMODELS
from app.tools import agent_management_tools, neo4j_tools, opcua_tools, kafka_tools, rag_tools
from app.config import settings

logger = logging.getLogger(__name__)


def _safe_result_hint(tool_result: Any) -> str:
    """Return a compact, non-raw fallback description for tool outputs."""
    if isinstance(tool_result, dict):
        keys = [str(k) for k in list(tool_result.keys())[:6]]
        return f"strukturierte Daten ({', '.join(keys)})" if keys else "strukturierte Daten"
    if isinstance(tool_result, list):
        return f"{len(tool_result)} Eintraege"
    if isinstance(tool_result, (str, int, float, bool)):
        return f"Wert: {tool_result}"
    return "Ergebnisdaten"


def _contains_domain_hint(normalized: str) -> bool:
    domain_hints = (
        "asset",
        "anlage",
        "gesamtanlage",
        "architektur",
        "referenzarchitektur",
        "smartfactory",
        "whitepaper",
        "doku",
        "dokumentation",
        "modul",
        "submodell",
        "nameplate",
        "billofmaterial",
        "productionplan",
        "opc",
        "neo4j",
        "kafka",
        "agent",
        "agenten",
        "registry",
        "p17",
        "skill",
        "parameter",
        "monitoring",
    )
    if any(token in normalized for token in domain_hints):
        return True

    # Detect common asset-like identifiers such as P24, RH2, PH2, HMS2.
    return bool(re.search(r"\b(?:p|rh|ph|hms)\d+\b", normalized, flags=re.IGNORECASE))


def _is_tool_discovery_query(user_input: str) -> bool:
    normalized = user_input.lower()
    return (
        any(token in normalized for token in ("tool", "tools", "fahigkeit", "faehigkeit", "capability", "funktion"))
        and any(token in normalized for token in ("kennst", "verfugbar", "verfügbar", "welche", "liste", "gibt es", "hast du"))
    )


def _is_exploratory_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False

    exploratory_phrases = (
        "erzahl mir",
        "erzähl mir",
        "was kannst du mir uber",
        "was kannst du mir über",
        "was weisst du uber",
        "was weißt du über",
        "was kannst du uber",
        "was kannst du über",
        "was kannst du zu",
        "sag mir was uber",
        "sag mir was über",
        "gib mir einen uberblick",
        "gib mir einen überblick",
    )

    if any(p in normalized for p in exploratory_phrases):
        return True

    # Open domain question with known context token, e.g. "... ueber P17"
    return any(token in normalized for token in (" uber ", " über ")) and _contains_domain_hint(normalized)


def _classify_query_mode(user_input: str, capability: str, intent: str) -> str:
    normalized = re.sub(r"\s+", " ", (user_input or "").strip().lower())

    if _is_assistant_meta_query(user_input) or _is_general_question(user_input):
        return "meta"
    if _is_tool_discovery_query(user_input):
        return "exploratory"
    if capability == "kafka" or intent in {"write_skill_parameter", "execute_skill"}:
        return "control"
    if _is_exploratory_query(user_input):
        return "exploratory"
    if "?" in normalized and any(t in normalized for t in ("was", "welche", "wie", "wo", "warum")):
        return "exploratory"
    return "transactional"


def _is_skill_endpoint_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    return (
        ("skill" in normalized or "skills" in normalized)
        and ("endpoint" in normalized or "schnittstelle" in normalized)
    )


def _is_skill_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    return "skill" in normalized or "skills" in normalized


def _is_skill_listing_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized or not _is_skill_query(user_input):
        return False

    # Queries for endpoint/parameter/monitoring are handled separately.
    if any(token in normalized for token in ("endpoint", "schnittstelle", "parameter", "monitoring", "execute", "ausfuhr", "ausführ", "write", "schreib")):
        return False

    return any(token in normalized for token in ("welche", "welcher", "welches", "liste", "list", "zeige", "gib", "hat", "haben"))


def _is_capability_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False

    capability_tokens = ("capability", "capabilities", "fahigkeit", "faehigkeit", "fahigkeiten", "faehigkeiten")
    context_tokens = ("modul", "module", "asset", "anlage", "ressource", "maschine", "lager")
    question_tokens = ("welche", "was", "hat", "haben", "liste", "zeige", "gib")

    return (
        any(token in normalized for token in capability_tokens)
        and any(token in normalized for token in context_tokens)
        and any(token in normalized for token in question_tokens)
    )


def _is_production_kpi_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False

    product_tokens = ("produkt", "produkte", "lkw", "lkws", "truck", "semitrailer")
    metric_tokens = (
        "wie viel",
        "wieviel",
        "anzahl",
        "count",
        "gesamt",
        "insgesamt",
        "heute",
        "fertig",
        "fertiggestellt",
        "erfolgreich",
        "produziert",
        "gefertigt",
    )
    direct_kpi_phrases = (
        "produktionsstatus",
        "in produktion",
        "montageprozess",
        "qualitycheck",
        "quality control",
        "qualitycontrol",
        "produktverteilung",
        "typverteilung",
        "step-status",
        "status pro modul",
        "status pro station",
    )
    if any(p in normalized for p in direct_kpi_phrases):
        return True
    return any(t in normalized for t in product_tokens) and any(t in normalized for t in metric_tokens)


def _infer_production_kpi_intent(user_input: str) -> str:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if any(t in normalized for t in ("24h", "24 h", "letzten 24", "letzte 24")):
        return "count_finished_products_last_24h"
    if any(t in normalized for t in ("7 tage", "7 tagen", "letzten 7", "letzte 7", "woche")):
        return "count_finished_products_last_7d"
    if any(t in normalized for t in ("produktverteilung", "typverteilung", "produkttyp", "product type", "typen", "typ", "cabin", "trailer", "semitrailer")):
        return "breakdown_products_by_type"
    if any(t in normalized for t in ("modulstatus", "station", "step status", "step-status", "status pro modul", "status pro station")):
        return "get_module_step_status_overview"
    if any(t in normalized for t in ("status", "uebersicht", "überblick", "overview", "fertig und unfertig", "unfinished", "total", "insgesamt", "gesamt")):
        return "get_production_kpi_overview"
    if any(t in normalized for t in ("gerade", "aktuell", "in produktion", "produziert werden")):
        return "count_products_in_production"
    if any(t in normalized for t in ("durchschnitt", "im durchschnitt", "dauer", "wie lange", "montageprozess", "assemble")):
        return "get_average_assembly_duration"
    if any(t in normalized for t in ("qualitycheck", "quality check", "qualitycontrol", "qc")):
        return "count_products_with_quality_check_step"
    if any(t in normalized for t in ("heute", "today")):
        return "get_today_truck_production"
    if any(t in normalized for t in ("erfolgreich", "fertiggestellt", "isfinished", "abgeschlossen")):
        return "count_successfully_finished_products"
    if any(t in normalized for t in ("insgesamt", "gesamt", "total")):
        return "count_total_products"
    return "count_total_products"


def _is_agent_inventory_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    if not any(token in normalized for token in ("agent", "agenten", "agents")):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "welche agenten gibt es",
            "welche agents gibt es",
            "welche agenten",
            "agenten gibt es",
            "liste der agenten",
            "liste agenten",
            "list agents",
        )
    )


def _has_explicit_asset_id(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", (user_input or "").strip().lower())
    if not normalized:
        return False
    return bool(re.search(r"\bp\d+\b", normalized))


def _is_asset_information_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", (user_input or "").strip().lower())
    if not normalized:
        return False
    if not _has_explicit_asset_id(user_input) and not any(t in normalized for t in ("lagermodul", "ca-modul", "modul")):
        return False
    return any(t in normalized for t in ("was", "welche", "wie", "infos", "informationen", "sag", "uber", "über", "status", "skills", "capabilities"))


def _extract_asset_hints_from_text(user_input: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", (user_input or "").strip().lower())
    if not normalized:
        return []

    hints: list[str] = []

    # Hyphenated identifiers like "ca-module".
    hints.extend(re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)+\b", normalized))

    # Split variants like "ca module" -> also try "ca-module".
    tokens = re.findall(r"[a-z0-9-]+", normalized)
    for idx, token in enumerate(tokens):
        if token in {"modul", "module"} and idx > 0:
            prev = tokens[idx - 1]
            hints.append(f"{prev}-{token}")
            hints.append(f"{prev}{token}")
            hints.append(prev)

    # Keep order, remove duplicates/very short noise.
    seen: set[str] = set()
    ordered: list[str] = []

    # Domain heuristic: "Lagermodul" maps to storage module naming used in assets (e.g. P24).
    if "lager" in normalized and ("modul" in normalized or "module" in normalized):
        hints = ["p24", "storage", "storage-p24", *hints]

    for hint in hints:
        clean = hint.strip()
        if len(clean) < 3 or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)

    return ordered


def _build_tool_discovery_text(asset_id: str | None) -> str:
    neo4j_lines = []
    for submodel, spec in sorted(SUBMODEL_REGISTRY.items()):
        tools = sorted((spec.get("tools") or {}).keys())
        if not tools:
            continue
        neo4j_lines.append(f"- {submodel}: {', '.join(tools)}")

    opcua_tools_list = sorted(opcua_tools.OPCUA_TOOL_REGISTRY.keys())
    rag_tools_list = sorted(rag_tools.RAG_TOOL_REGISTRY.keys())
    kafka_tools_list = sorted(kafka_tools.KAFKA_TOOL_REGISTRY.keys())
    agent_mgmt_tools_list = sorted(agent_management_tools.AGENT_MANAGEMENT_TOOL_REGISTRY.keys())

    lines = [
        "Ich kenne folgende Tool-Gruppen:",
        "",
        "Neo4j-Tools (globale Ubersicht):",
        *neo4j_lines,
        "",
        f"OPC UA: {', '.join(opcua_tools_list)}",
        f"RAG: {', '.join(rag_tools_list)}",
        f"Kafka: {', '.join(kafka_tools_list)}",
        f"Agent Management: {', '.join(agent_mgmt_tools_list)}",
    ]

    if asset_id:
        lines.extend(
            [
                "",
                f"Fur Asset '{asset_id}' kann ich direkt asset-spezifische Neo4j-Details auslesen.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Wenn du asset-spezifische Details willst, nenne bitte das Asset (z. B. 'Anlage A').",
            ]
        )

    return "\n".join(lines)


def _tool_groups_compact_text() -> str:
    neo4j_groups = ", ".join(sorted(SUBMODEL_REGISTRY.keys()))
    opcua_groups = ", ".join(sorted(opcua_tools.OPCUA_TOOL_REGISTRY.keys()))
    rag_groups = ", ".join(sorted(rag_tools.RAG_TOOL_REGISTRY.keys()))
    kafka_groups = ", ".join(sorted(kafka_tools.KAFKA_TOOL_REGISTRY.keys()))
    agent_mgmt_groups = ", ".join(sorted(agent_management_tools.AGENT_MANAGEMENT_TOOL_REGISTRY.keys()))
    return (
        f"Neo4j (Submodelle): {neo4j_groups}\n"
        f"OPC UA: {opcua_groups}\n"
        f"RAG: {rag_groups}\n"
        f"Kafka: {kafka_groups}\n"
        f"Agent Management: {agent_mgmt_groups}"
    )


def _is_general_question(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False

    if _contains_domain_hint(normalized):
        return False

    phrases = (
        "wer bist du",
        "was kannst du",
        "hilfe",
        "help",
        "danke",
        "wie geht",
    )
    greetings = {"hi", "hallo", "hey", "moin", "servus", "guten morgen", "guten tag"}
    words = normalized.split(" ")
    return normalized in greetings or (len(words) <= 12 and any(p in normalized for p in phrases))


def _is_assistant_meta_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    if _contains_domain_hint(normalized):
        return False
    meta_phrases = (
        "wer bist du",
        "was kannst du",
        "was geht",
        "wie geht",
        "hilfe",
        "help",
    )
    return any(p in normalized for p in meta_phrases)


def _is_summary_request(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    return (
        ("fasse" in normalized and "zusammen" in normalized)
        or "zusammenfassung" in normalized
        or "erkenntnisse" in normalized
    )


def _is_session_recap_request(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    recap_phrases = (
        "deine erkenntnisse",
        "was hast du gefunden",
        "fasse mir das zusammen",
        "fasse das zusammen",
        "was war das ergebnis",
    )
    return any(p in normalized for p in recap_phrases)


def _is_pure_greeting(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    return normalized in {"hi", "hallo", "hey", "moin", "servus", "guten morgen", "guten tag"}


def _build_assistant_intro_response() -> str:
    return (
        "Hi! Ich bin dein I4.0-Chatbot fur Anlagenwissen und Live-Daten. "
        "Fur diese Meta-Frage habe ich kein RAG und kein anderes Tool verwendet.\n\n"
        "Ich kann dir helfen bei:\n"
        "- Doku- und Architekturfragen via RAG\n"
        "- Asset-/Submodellabfragen aus Neo4j\n"
        "- Live-Werten aus OPC UA\n"
        "- Befehlen via Kafka (mit Bestatigung)\n"
        "- Agent-Registry und Agent-Lifecycle\n\n"
        "Frag mich am besten konkret, z. B.: 'Was ist P17 und welche Skills hat es?'"
    )


def _build_last_summary_response(session_ctx: dict[str, Any]) -> str:
    findings = session_ctx.get("last_rag_findings") or []
    summary = session_ctx.get("last_rag_summary") or ""
    if not findings and not summary:
        return (
            "Ich habe in dieser Session noch keine belastbare Doku-Zusammenfassung gespeichert. "
            "Stelle bitte zuerst eine konkrete Fachfrage (z. B. zu P17), dann fasse ich sie dir zusammen."
        )

    findings_text = "\n".join(f"- {f}" for f in findings) if findings else "- Keine Einzelpunkte gespeichert"
    summary_text = summary or "Keine ubergeordnete Zusammenfassung gespeichert."
    return f"Habe das gefunden:\n{findings_text}\n\nZusammenfassend:\n{summary_text}"


def _extract_query_terms(user_input: str) -> set[str]:
    stopwords = {
        "was", "wer", "wie", "und", "oder", "uber", "ueber", "mir", "dir", "das",
        "der", "die", "den", "dem", "ein", "eine", "einen", "fasse", "zusammen",
        "kannst", "sagen", "mal", "deine", "dein", "erkenntnisse", "bitte", "du",
        "eure", "kann", "steht", "drin", "paper",
    }
    return {
        t
        for t in re.findall(r"[a-z0-9]{2,}", user_input.lower())
        if t not in stopwords and len(t) >= 3
    }


def _is_broad_docs_query(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return False
    return (
        "doku" in normalized
        or "dokumentation" in normalized
        or "gesamt" in normalized
        or ("was steht" in normalized and "drin" in normalized)
        or "uberblick" in normalized
        or "zusammenfassung" in normalized
    )


def _build_rag_query(user_input: str) -> str:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    if not normalized:
        return user_input

    if "doku" in normalized or "dokumentation" in normalized:
        return f"{user_input} Gesamtanlage Architektur SmartFactory Referenzarchitektur Module Skills"

    if _is_summary_request(user_input) and not _contains_domain_hint(normalized):
        return (
            f"{user_input} Gesamtanlage Architektur SmartFactory "
            "Module Submodelle Skills Schnittstellen"
        )

    return user_input


def _select_relevant_rag_hits(user_input: str, rag_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_terms = _extract_query_terms(_build_rag_query(user_input))
    is_broad = _is_broad_docs_query(user_input)

    max_distance = settings.rag_max_distance + (1.0 if is_broad else 0.2)
    min_overlap = 0 if is_broad else settings.rag_min_lexical_overlap

    selected: list[dict[str, Any]] = []

    for hit in rag_hits:
        if not isinstance(hit, dict):
            continue

        doc_text = str(hit.get("document") or "")
        if not doc_text.strip():
            continue

        distance_raw = hit.get("distance")
        distance: float | None
        try:
            distance = float(distance_raw) if distance_raw is not None else None
        except (TypeError, ValueError):
            distance = None

        if distance is not None and distance > max_distance:
            continue

        overlap = sum(1 for term in query_terms if term in doc_text.lower())
        if query_terms and overlap < min_overlap:
            continue

        selected.append(hit)

    selected.sort(key=lambda h: float(h.get("distance", 999.0)))

    if selected:
        return selected[:4]

    # Controlled fallback for broad documentation questions:
    # prefer the closest hits instead of returning an empty result.
    if is_broad and rag_hits:
        sorted_hits = sorted(
            [h for h in rag_hits if isinstance(h, dict) and str(h.get("document") or "").strip()],
            key=lambda h: float(h.get("distance", 999.0)),
        )
        return sorted_hits[:4]

    return []


def _format_hit_source(hit: dict[str, Any]) -> str:
    metadata = (hit or {}).get("metadata") or {}
    path = str(metadata.get("path") or metadata.get("source") or "unbekannt")
    chunk = metadata.get("chunk")
    if chunk is not None:
        return f"{path}, Chunk {chunk}"
    return path


def _extract_summary_from_llm_output(llm_text: str | None) -> str | None:
    if not llm_text:
        return None
    split = re.split(r"Zusammenfassend\s*:\s*", llm_text, maxsplit=1, flags=re.IGNORECASE)
    if len(split) != 2:
        return None
    summary = split[1].strip()
    return summary or None


def _store_summary_in_session(session_id: str | None, summary_text: str) -> None:
    if not session_id or not summary_text:
        return

    findings = [
        line[2:].strip()
        for line in summary_text.splitlines()
        if line.strip().startswith("- ")
    ]

    summary_part = ""
    summary_split = re.split(r"Zusammenfassend\s*:\s*", summary_text, maxsplit=1, flags=re.IGNORECASE)
    if len(summary_split) == 2:
        summary_part = summary_split[1].strip()

    if findings or summary_part:
        session_svc.update_session(
            session_id,
            {
                "last_rag_findings": findings,
                "last_rag_summary": summary_part,
            },
        )


def _build_rag_fallback_response(user_input: str) -> str | None:
    rag_query = _build_rag_query(user_input)
    try:
        rag_hits = rag_tools.search_docs(query=rag_query, n_results=settings.rag_default_n_results)
    except Exception as exc:
        logger.warning("RAG fallback failed: %s", exc)
        return None

    if not isinstance(rag_hits, list) or not rag_hits:
        return None

    relevant_hits = _select_relevant_rag_hits(user_input, rag_hits)
    if not relevant_hits:
        return None

    return _format_rag_summary_text(
        rag_query,
        relevant_hits,
        prefix="Ich habe dafur als Fallback die RAG-Dokumentation genutzt.",
    )


def _extract_doc_highlight(doc_text: str, query_terms: set[str]) -> str:
    lines = [ln.strip() for ln in doc_text.splitlines() if ln.strip()]
    if not lines:
        return "Kein verwertbarer Inhalt in diesem Treffer."

    heading = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), None)

    # Prefer content lines over pure headings to avoid quote-like output.
    content_lines = [ln for ln in lines if not ln.startswith("#")]

    # Pick the sentence/line that best matches query terms, otherwise first meaningful text line.
    scored: list[tuple[int, str]] = []
    for ln in (content_lines or lines):
        plain = ln.lstrip("# ").strip()
        if not plain:
            continue
        lowered = plain.lower()
        score = sum(1 for t in query_terms if t and t in lowered)
        scored.append((score, plain))

    best_line = ""
    if scored:
        best_line = sorted(scored, key=lambda x: x[0], reverse=True)[0][1]
    if not best_line:
        best_line = lines[0].lstrip("# ").strip()

    if heading and best_line.lower() != heading.lower():
        return f"{heading}: {best_line[:220]}"
    return best_line[:220]


def _build_overall_summary(highlights: list[str], query_terms: set[str]) -> str:
    if not highlights:
        return "Es gibt keine ausreichend relevanten Dokumenttreffer."

    p17_related = any("p17" in h.lower() for h in highlights) or ("p17" in query_terms)
    if p17_related:
        return (
            "P17 wird in der Dokumentation als Modul-/Architekturkontext beschrieben. "
            "Die Treffer enthalten vor allem System- und Prozessbeschreibungen; "
            "fur belastbare Detailaussagen sollten wir gezielt nach technischen Kennwerten "
            "oder einer konkreten Asset-ID filtern."
        )

    return (
        "Die Dokumenttreffer deuten auf kontextuelle Beschreibungen hin. "
        "Fur eine prazise Antwort kann ich als Nachstes gezielt auf einen technischen Aspekt "
        "(z. B. Funktion, Schnittstelle, Zustand) eingrenzen."
    )


def _format_rag_summary_text(
    user_input: str,
    rag_hits: list[dict[str, Any]],
    prefix: str | None = None,
) -> str | None:
    if not isinstance(rag_hits, list) or not rag_hits:
        return None

    query_terms = _extract_query_terms(user_input)
    if not query_terms:
        return None

    filtered_hits = _select_relevant_rag_hits(user_input, rag_hits)
    if not filtered_hits:
        return None

    highlights: list[str] = []
    source_lines: list[str] = []
    llm_snippets: list[str] = []
    for hit in filtered_hits[:3]:
        doc = (hit or {}).get("document")
        if not doc:
            continue

        doc_text = str(doc)

        llm_snippets.append(doc_text)

        highlight = _extract_doc_highlight(doc_text, query_terms)
        if highlight:
            highlights.append(highlight)
            source_lines.append(_format_hit_source(hit))

    if not highlights:
        return None

    # De-duplicate near-identical highlights while keeping order.
    deduped_pairs: list[tuple[str, str]] = []
    seen_highlights: set[str] = set()
    for hl, src in zip(highlights, source_lines):
        if hl in seen_highlights:
            continue
        seen_highlights.add(hl)
        deduped_pairs.append((hl, src))
    deduped_pairs = deduped_pairs[:3]

    llm_summary = llm.summarize_rag(user_input, llm_snippets)
    llm_summary_text = _extract_summary_from_llm_output(llm_summary)

    findings = "\n".join(
        f"- {h} (Quelle: {src})" for h, src in deduped_pairs
    )
    summary = llm_summary_text or _build_overall_summary([h for h, _ in deduped_pairs], query_terms)

    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    parts.append("Habe das gefunden:")
    parts.append(findings)
    parts.append("")
    parts.append("Zusammenfassend:")
    parts.append(summary)
    return "\n".join(parts)


def _is_non_empty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _first_property_value(rows: list[dict[str, Any]], candidates: tuple[str, ...]) -> str | None:
    for row in rows:
        key = str(row.get("idShort") or "")
        if key not in candidates:
            continue
        value = row.get("value")
        if _is_non_empty_value(value):
            return str(value)
    return None


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in values:
        val = item.strip()
        if not val or val in seen:
            continue
        seen.add(val)
        ordered.append(val)
    return ordered


def _extract_skill_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        if _is_non_empty_value(row.get("skillName")):
            names.append(str(row.get("skillName")))
        elif (row.get("idShort") == "Name") and str(row.get("parentIdShort") or "").startswith("Skill_"):
            value = row.get("value")
            if _is_non_empty_value(value):
                names.append(str(value))
    return _unique_ordered(names)


def _extract_skill_input_parameter_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    blacklist = {"ID", "Port", "RequiredAccessLevel", "SkillExecutionResult"}
    for row in rows:
        parent = str(row.get("parentIdShort") or "")
        key = str(row.get("idShort") or "")
        if not key or key in blacklist:
            continue
        if parent in {"RequiredInputParameters", "InputParameters"}:
            names.append(key)
        elif row.get("containerIdShort") in {"RequiredInputParameters", "InputParameters"}:
            names.append(key)
    return _unique_ordered(names)


def _extract_skill_endpoints(rows: list[dict[str, Any]]) -> list[str]:
    endpoints: list[str] = []
    for row in rows:
        if _is_non_empty_value(row.get("endpoint")):
            endpoints.append(str(row.get("endpoint")))
            continue
        if str(row.get("idShort") or "") == "SkillEndpoint" and _is_non_empty_value(row.get("value")):
            endpoints.append(str(row.get("value")))
    return _unique_ordered(endpoints)


def _build_skills_summary(asset_id: str) -> list[str]:
    lines: list[str] = []
    skills_tools = (SUBMODEL_REGISTRY.get("Skills") or {}).get("tools", {})

    list_skills_fn = skills_tools.get("list_skills") or skills_tools.get("get_skills")
    endpoints_fn = skills_tools.get("get_skill_endpoints")
    input_params_fn = skills_tools.get("list_skill_input_parameters")

    skills_rows: list[dict[str, Any]] = []
    if callable(list_skills_fn):
        try:
            raw = list_skills_fn(asset_id=asset_id)
            if isinstance(raw, list):
                skills_rows = [r for r in raw if isinstance(r, dict)]
        except Exception as exc:
            logger.debug("Skills list summary skipped: %s", exc)

    skill_names = _extract_skill_names(skills_rows)
    if skill_names:
        lines.append(f"- Skills: {len(skill_names)} gefunden ({', '.join(skill_names[:8])}).")

    endpoint_rows: list[dict[str, Any]] = []
    if callable(endpoints_fn):
        try:
            raw = endpoints_fn(asset_id=asset_id, limit=120)
            if isinstance(raw, list):
                endpoint_rows = [r for r in raw if isinstance(r, dict)]
        except Exception as exc:
            logger.debug("Skills endpoint summary skipped: %s", exc)

    endpoints = _extract_skill_endpoints(endpoint_rows)
    if endpoints:
        lines.append(f"- Skill-Endpunkte: {len(endpoints)} gefunden (z. B. {', '.join(endpoints[:2])}).")

    params_rows: list[dict[str, Any]] = []
    if callable(input_params_fn):
        try:
            raw = input_params_fn(asset_id=asset_id, limit=300)
            if isinstance(raw, list):
                params_rows = [r for r in raw if isinstance(r, dict)]
        except Exception as exc:
            logger.debug("Skills input parameter summary skipped: %s", exc)

    param_names = _extract_skill_input_parameter_names(params_rows)
    if param_names:
        lines.append(f"- Typische Input-Parameter: {', '.join(param_names[:10])}.")

    return lines


def _build_additional_submodel_highlights(asset_id: str) -> list[str]:
    lines: list[str] = []

    try:
        nameplate_rows = neo4j_svc.get_submodel_elements(asset_id, "Nameplate")
    except Exception:
        nameplate_rows = []

    if isinstance(nameplate_rows, list) and nameplate_rows:
        manufacturer = _first_property_value(nameplate_rows, ("ManufacturerName", "manufacturerName"))
        date_of_manufacture = _first_property_value(nameplate_rows, ("DateOfManufacture", "YearOfConstruction"))
        np_parts: list[str] = []
        if manufacturer:
            np_parts.append(f"Hersteller: {manufacturer}")
        if date_of_manufacture:
            np_parts.append(f"Baujahr/Herstellungsdatum: {date_of_manufacture}")
        if np_parts:
            lines.append(f"- Nameplate: {'; '.join(np_parts)}.")

    try:
        availability_rows = neo4j_svc.get_submodel_elements(asset_id, "Availability")
    except Exception:
        availability_rows = []

    if isinstance(availability_rows, list) and availability_rows:
        machine_state = _first_property_value(availability_rows, ("MachineState",))
        if machine_state:
            lines.append(f"- Verfugbarkeit: aktueller Maschinenzustand ist '{machine_state}'.")

    try:
        technical_rows = neo4j_svc.get_submodel_elements(asset_id, "TechnicalData")
    except Exception:
        technical_rows = []

    if isinstance(technical_rows, list) and technical_rows:
        technical_keys = _unique_ordered([
            str(r.get("idShort"))
            for r in technical_rows
            if isinstance(r, dict) and r.get("idShort")
        ])
        if technical_keys:
            lines.append(f"- TechnicalData: Felder vorhanden, z. B. {', '.join(technical_keys[:6])}.")

    return lines


def _build_neo4j_structured_summary(
    asset_id: str,
    tool_name: str,
    tool_result: Any,
    user_input: str,
) -> str:
    overview = None
    try:
        overview = neo4j_svc.get_asset_overview(asset_id)
    except Exception as exc:
        logger.debug("Asset overview query failed: %s", exc)

    title = f"Ich habe das Tool '{tool_name}' auf Asset '{asset_id}' angewendet und Folgendes herausgefunden:"
    lines: list[str] = [title]

    if isinstance(overview, dict):
        name = overview.get("name") or overview.get("idShort")
        asset_type = overview.get("type") or overview.get("assetKind")
        if name or asset_type:
            lines.append(
                "- Asset-Kontext: "
                + ", ".join(
                    p
                    for p in [
                        f"Name {name}" if name else "",
                        f"Typ {asset_type}" if asset_type else "",
                    ]
                    if p
                )
                + "."
            )
        submodels = [s for s in (overview.get("submodels") or []) if s]
        if submodels:
            lines.append(f"- Verfugbare Submodelle: {len(submodels)} ({', '.join(sorted(submodels)[:10])}).")

    # Skills summary is useful for both focused and broad questions.
    skill_lines = _build_skills_summary(asset_id)
    lines.extend(skill_lines)

    # For broad exploratory questions, enrich with additional submodels.
    if _is_exploratory_query(user_input):
        lines.extend(_build_additional_submodel_highlights(asset_id))

    # Fallback if no structured enrichment is available.
    if len(lines) == 1:
        if isinstance(tool_result, list):
            lines.append(f"- Ergebnisumfang: {len(tool_result)} Eintrage.")
        elif isinstance(tool_result, dict):
            keys = ", ".join(list(tool_result.keys())[:8])
            lines.append(f"- Strukturierte Daten erhalten (Schlussel: {keys}).")
        else:
            lines.append(f"- Ergebnis: {tool_result}")

    lines.append("")
    lines.append("Zusammenfassung:")
    if skill_lines:
        lines.append("Das Modul bietet mehrere Skills mit dokumentierten Endpunkten und klaren Eingabeparametern; damit sind sowohl Skill-Auswahl als auch Ausfuhrungsvorbereitung direkt ableitbar.")
    else:
        lines.append("Es liegen strukturierte Neo4j-Daten vor; fur eine tiefere Analyse kann ich als Nachstes ein konkretes Submodell (z. B. Nameplate, TechnicalData oder QualityInformation) detailliert aufschlussen.")

    return "\n".join(lines)


def _build_no_tool_general_response() -> str:
    return (
        "Hallo! Ich helfe dir gerne weiter. Fur diese allgemeine Frage habe ich "
        "kein Tool verwendet.\n\n"
        "Wenn du willst, kann ich als Nachstes direkt mit Tools arbeiten. "
        "Verfugbare Tool-Gruppen sind:\n"
        f"{_tool_groups_compact_text()}\n\n"
        "Nenne mir einfach eine konkrete Frage, z. B. zu einem Asset, Modul "
        "oder einer Live-Abfrage."
    )


# ── 1. interpret_input ─────────────────────────────────────────────────────────

def interpret_input(state: AgentState) -> dict[str, Any]:
    """
    Use the LLM to extract intent, capability, submodel and entities
    from the user's raw input.

    ``user_input`` can be provided directly (FastAPI path) or extracted from
    the last :class:`~langchain_core.messages.HumanMessage` in ``messages``
    (LangGraph Server / agent-chat-ui path).
    """
    # Resolve user text from explicit field or last HumanMessage
    user_input: str = state.get("user_input") or ""
    if not user_input:
        for msg in reversed(state.get("messages") or []):
            if isinstance(msg, HumanMessage):
                content = msg.content
                user_input = content if isinstance(content, str) else str(content)
                break

    # Fast-path: for common, clearly classifiable intents use deterministic
    # routing directly and skip an LLM interpretation call.
    result: dict[str, Any]
    if _is_agent_inventory_query(user_input):
        result = {
            "intent": "get_all_registered_agents",
            "capability": "agent_management",
            "submodel": None,
            "entities": {},
        }
    elif _is_production_kpi_query(user_input):
        result = {
            "intent": _infer_production_kpi_intent(user_input),
            "capability": "neo4j",
            "submodel": "ExhibitionInsights",
            "entities": {},
        }
    elif _is_capability_query(user_input):
        lowered = user_input.lower()
        inferred_submodel = (
            "RequiredCapabilityDescription"
            if "required" in lowered or "benotig" in lowered
            else "OfferedCapabilityDescription"
        )
        inferred_intent = "list_required_capabilities" if inferred_submodel == "RequiredCapabilityDescription" else "list_capabilities"
        result = {
            "intent": inferred_intent,
            "capability": "neo4j",
            "submodel": inferred_submodel,
            "entities": {},
        }
    elif _is_asset_information_query(user_input):
        result = {
            "intent": "get_properties",
            "capability": "neo4j",
            "submodel": "Structure",
            "entities": {},
        }
    else:
        session_ctx = {}
        if state.get("session_id"):
            session_ctx = session_svc.get_session(state["session_id"])

        try:
            result = llm.interpret(user_input, context=session_ctx)
        except Exception as exc:
            logger.error("LLM interpretation error in node: %s", exc)
            result = {
                "intent": "unknown",
                "capability": "rag",
                "submodel": None,
                "entities": {},
            }

    if _is_agent_inventory_query(user_input):
        result["capability"] = "agent_management"
        if _normalize_intent(result.get("intent")) in {"", "unknown", "get_properties", "explain", "describe"}:
            result["intent"] = "get_all_registered_agents"
        result["submodel"] = None

    # Deterministic guardrails for common industrial phrasing where LLM routing can be too generic.
    if _is_capability_query(user_input):
        result["capability"] = "neo4j"
        normalized_intent = _normalize_intent(result.get("intent"))
        if "required" in normalized_intent or "benotig" in normalized_intent:
            result["submodel"] = "RequiredCapabilityDescription"
            if normalized_intent in {"", "unknown", "get_properties", "explain", "describe"}:
                result["intent"] = "list_required_capabilities"
        else:
            result["submodel"] = "OfferedCapabilityDescription"
            if normalized_intent in {"", "unknown", "get_properties", "explain", "describe"}:
                result["intent"] = "list_capabilities"

    if _is_production_kpi_query(user_input):
        result["capability"] = "neo4j"
        result["submodel"] = "ExhibitionInsights"
        normalized_intent = _normalize_intent(result.get("intent"))
        if normalized_intent in {"", "unknown", "get_properties", "explain", "describe", "get_info"}:
            result["intent"] = _infer_production_kpi_intent(user_input)

    # If LLM falls back to rag/unknown but the query explicitly targets an
    # asset/module (e.g. "Was kannst du mir uber P24 sagen?"), force Neo4j.
    if _is_asset_information_query(user_input):
        normalized_intent = _normalize_intent(result.get("intent"))
        if result.get("capability") in {None, "", "rag", "unknown"}:
            result["capability"] = "neo4j"
        if normalized_intent in {"", "unknown", "explain", "describe"}:
            result["intent"] = "get_properties"
        if not result.get("submodel"):
            result["submodel"] = "Structure"

    return {
        "user_input": user_input,
        "intent": result.get("intent", "unknown"),
        "query_mode": _classify_query_mode(
            user_input,
            result.get("capability", "rag"),
            result.get("intent", "unknown"),
        ),
        "capability": result.get("capability", "rag"),
        "submodel": result.get("submodel"),
        "entities": result.get("entities", {}),
        "error": None,
    }


# ── 2. resolve_entities ────────────────────────────────────────────────────────

def resolve_entities(state: AgentState) -> dict[str, Any]:
    """
    Map human-readable entity names to system IDs using Neo4j fuzzy search.

    Populates state["resolved_entities"] with at minimum an "asset_id" key
    when an asset entity can be resolved.
    """
    entities: dict[str, Any] = dict(state.get("entities") or {})
    resolved: dict[str, Any] = {}

    asset_hint = (
        entities.get("asset")
        or entities.get("asset_name")
        or entities.get("anlage")
        or entities.get("modul")
    )

    if asset_hint:
        try:
            candidates = neo4j_svc.find_asset_by_name(str(asset_hint))
            if len(candidates) == 1:
                resolved["asset_id"] = candidates[0]["id"]
                resolved["asset_name"] = candidates[0].get("name") or candidates[0].get("idShort")
                resolved["asset_type"] = candidates[0].get("type")
                # persist in session
                if state.get("session_id"):
                    session_svc.update_session(
                        state["session_id"],
                        {
                            "current_asset": resolved["asset_id"],
                            "current_asset_name": resolved["asset_name"],
                        },
                    )
            elif len(candidates) > 1:
                # Ambiguous – ask for clarification
                names = [c.get("name") or c.get("idShort") for c in candidates]
                resolved["disambiguation"] = names
        except Exception as exc:
            logger.warning("Entity resolution failed: %s", exc)
    else:
        # Convenience fallback: recognize direct IDs like "P17" from plain text.
        user_input = state.get("user_input") or ""
        id_match = re.search(r"\bP\d+\b", user_input, flags=re.IGNORECASE)
        if id_match:
            try:
                parsed_id = id_match.group(0).upper()
                candidates = neo4j_svc.find_asset_by_name(parsed_id)
                if len(candidates) == 1:
                    resolved["asset_id"] = candidates[0]["id"]
                    resolved["asset_name"] = candidates[0].get("name") or candidates[0].get("idShort")
                    resolved["asset_type"] = candidates[0].get("type")
                    if state.get("session_id"):
                        session_svc.update_session(
                            state["session_id"],
                            {
                                "current_asset": resolved["asset_id"],
                                "current_asset_name": resolved["asset_name"],
                            },
                        )
                else:
                    # Deterministic fallback for explicit IDs like P17.
                    resolved["asset_id"] = f"https://smartfactory.de/asset/{parsed_id}"
                    resolved["asset_name"] = parsed_id
            except Exception as exc:
                logger.warning("Entity resolution by explicit ID failed: %s", exc)

        # Additional fallback for free-text hints like "CA-Module".
        if not resolved.get("asset_id"):
            for hint in _extract_asset_hints_from_text(user_input):
                try:
                    candidates = neo4j_svc.find_asset_by_name(hint)
                    if len(candidates) == 1:
                        resolved["asset_id"] = candidates[0]["id"]
                        resolved["asset_name"] = candidates[0].get("name") or candidates[0].get("idShort")
                        resolved["asset_type"] = candidates[0].get("type")
                        if state.get("session_id"):
                            session_svc.update_session(
                                state["session_id"],
                                {
                                    "current_asset": resolved["asset_id"],
                                    "current_asset_name": resolved["asset_name"],
                                },
                            )
                        break
                except Exception as exc:
                    logger.warning("Entity resolution by free-text hint '%s' failed: %s", hint, exc)

        # Fall back to session context, but keep this optional for environments
        # where Redis/session storage is not available (e.g. local tests).
        if state.get("session_id"):
            try:
                ctx = session_svc.get_session(state["session_id"])
                if ctx.get("current_asset"):
                    resolved["asset_id"] = ctx["current_asset"]
                    resolved["asset_name"] = ctx.get("current_asset_name")
            except Exception as exc:
                logger.debug("Session fallback unavailable during entity resolution: %s", exc)

    # Forward any non-asset entities (e.g. step name, node_id) unchanged
    for k, v in entities.items():
        if k not in {"asset", "asset_name", "anlage", "modul"}:
            resolved[k] = v

    return {"resolved_entities": resolved}


# ── 3. route_capability ────────────────────────────────────────────────────────

def route_capability(state: AgentState) -> dict[str, Any]:
    """
    Pure routing node – no state mutation needed here because the conditional
    edge lambda reads state["capability"] directly.
    Validates the capability value and falls back to "rag" if unknown.
    """
    valid = {"neo4j", "opcua", "rag", "kafka", "agent_management"}
    capability = state.get("capability", "rag")
    user_input = state.get("user_input", "")
    query_mode = state.get("query_mode", "transactional")
    resolved = state.get("resolved_entities") or {}

    # Skills endpoints are modeled in Neo4j and should query there directly.
    if _is_skill_endpoint_query(user_input):
        capability = "neo4j"

    # Discovery/listing skill questions should prefer Neo4j Skills when an
    # asset could be identified from context or the query is exploratory.
    if _is_skill_listing_query(user_input) and (resolved.get("asset_id") or query_mode == "exploratory"):
        capability = "neo4j"

    if _is_capability_query(user_input):
        capability = "neo4j"

    if _is_production_kpi_query(user_input):
        capability = "neo4j"

    # Guardrail: explicit asset questions should not remain on RAG.
    if _is_asset_information_query(user_input) or resolved.get("asset_id"):
        if capability == "rag":
            capability = "neo4j"

    if _is_agent_inventory_query(user_input):
        capability = "agent_management"

    if capability not in valid:
        logger.warning("Unknown capability '%s', falling back to 'rag'", capability)
        capability = "rag"
    return {"capability": capability}


# ── 4. validate_submodel ───────────────────────────────────────────────────────

def validate_submodel(state: AgentState) -> dict[str, Any]:
    """
    Ensure the LLM-chosen submodel is valid.
    Falls back to 'Structure' if missing or unknown.
    """
    submodel = state.get("submodel")
    if state.get("capability") == "neo4j" and _is_skill_query(state.get("user_input", "")):
        submodel = "Skills"
    if submodel not in VALID_SUBMODELS:
        logger.warning("Invalid/missing submodel '%s', falling back to 'Structure'", submodel)
        submodel = "Structure"
    # Update session with current submodel
    if state.get("session_id"):
        session_svc.update_session(state["session_id"], {"current_submodel": submodel})
    return {"submodel": submodel}


# ── 5a. select_tool_neo4j ──────────────────────────────────────────────────────

def _normalize_intent(intent: str | None) -> str:
    return (intent or "").strip().lower()


def _select_soft_neo4j_tool(
    submodel: str,
    normalized_intent: str,
    tools_map: dict[str, Any],
) -> str | None:
    """
    Soft intent mapping as fallback only.

    Keeps routing flexible: direct tool names stay highest priority,
    this mapping only helps when the intent is natural language.
    """
    if not normalized_intent:
        return None

    # Generic fallbacks that are safe across most submodels.
    generic_pairs: list[tuple[tuple[str, ...], str]] = [
        (("explain", "describe", "erklar", "erlaer", "beschreib"), "get_properties"),
    ]

    # Submodel-specific soft hints.
    by_submodel: dict[str, list[tuple[tuple[str, ...], str]]] = {
        "Nameplate": [
            (("nameplate", "typschild", "overview", "alle", "all", "gesamt"), "get_nameplate"),
            (("dateofmanufacture", "manufacture", "hergestellt", "hergestell", "herstell", "fertigung", "built"), "get_date_of_manufacture"),
            (("manufacturername", "herstellername", "manufacturer", "hersteller"), "get_manufacturer_name"),
            (("hardware",), "get_hardware_version"),
            (("software",), "get_software_version"),
            (("urioftheproduct", "product uri", "produkt uri", "url", "link"), "get_uri_of_the_product"),
            (("country", "origin", "ursprung", "land"), "get_country_of_origin"),
            (("yearofconstruction", "baujahr", "construction year"), "get_year_of_construction"),
            (("product type", "produkttyp", "typ"), "get_manufacturer_product_type"),
            (("product family", "produktfamilie", "familie"), "get_manufacturer_product_family"),
            (("product root", "produktroot", "root"), "get_manufacturer_product_root"),
            (("designation", "bezeichnung"), "get_manufacturer_product_designation"),
        ],
        "ProductionPlan": [
            (("steps", "schritte", "ablauf"), "get_steps"),
            (("duration", "dauer"), "get_step_duration"),
            (("finished", "done", "abgeschlossen", "fertig"), "is_finished"),
        ],
        "BillOfMaterial": [
            (("parts", "teile", "stuckliste", "stueckliste", "bom"), "get_parts"),
        ],
        "Structure": [
            (("parts", "teile", "struktur", "hierarchie", "aufbau"), "get_parts"),
        ],
        "Skills": [
            (("skills", "fahigkeiten", "faehigkeiten", "capabilities"), "get_skills"),
            (("liste", "list"), "list_skills"),
            (("endpoint", "skillendpoint", "skill endpoint", "schnittstelle"), "get_skill_endpoints"),
            (("inputparameter", "input parameter", "requiredinputparameters", "required input"), "list_skill_input_parameters"),
        ],
        "Agents": [
            (("agent", "agenten", "topologie", "topology", "knoten", "nodes"), "list_connected_node_properties"),
        ],
        "ExhibitionInsights": [
            (("lkw", "lkws", "truck", "produktion", "heute"), "get_today_truck_production"),
            (("24h", "24 h", "letzten 24", "letzte 24"), "count_finished_products_last_24h"),
            (("7 tage", "7 tagen", "letzten 7", "letzte 7", "woche"), "count_finished_products_last_7d"),
            (("produkttyp", "product type", "typen", "semitrailer", "cabin", "trailer"), "breakdown_products_by_type"),
            (("modulstatus", "station", "status pro modul", "status pro station", "step status"), "get_module_step_status_overview"),
            (("status", "uebersicht", "überblick", "unfinished", "unfertig"), "get_production_kpi_overview"),
            (("gerade", "aktuell", "in produktion", "produziert werden"), "count_products_in_production"),
            (("durchschnitt", "dauer", "wie lange", "montageprozess", "assemble"), "get_average_assembly_duration"),
            (("qualitycheck", "quality check", "qualitycontrol", "qc"), "count_products_with_quality_check_step"),
            (("insgesamt", "gesamt", "total", "produkte"), "count_total_products"),
            (("erfolgreich", "fertig", "fertiggestellt", "isfinished", "abgeschlossen"), "count_successfully_finished_products"),
            (("module", "modul", "module gibt es"), "list_modules"),
            (("agent", "agenten", "laufen", "aktiv"), "list_active_agents"),
            (("lager", "vorrat", "vorratig", "produkte"), "list_inventory_products"),
        ],
        "ConditionMonitoring": [
            (("history", "historie", "trend", "zustand", "sensor"), "get_condition_history"),
        ],
        "Availability": [
            (("state", "zustand", "maschinenzustand", "availability"), "get_machine_state"),
            (("reason", "grund", "unavailability", "ausfall"), "list_unavailability_reasons"),
            (("block", "blocks"), "list_unavailability_blocks"),
            (("overview", "uberblick", "ueberblick"), "get_availability_overview"),
        ],
        "MachineSchedule": [
            (("schedule", "plan", "planung"), "get_schedule"),
            (("open", "offen", "tasks"), "has_open_tasks"),
            (("update", "aktualisiert", "timestamp"), "get_last_update"),
        ],
        "OfferedCapabilityDescription": [
            (("capability set", "capabilityset"), "list_capability_sets"),
            (("capabilities", "fahigkeiten", "faehigkeiten"), "list_capabilities"),
            (("container", "property set", "propertyset"), "list_properties_by_container"),
        ],
        "DesignOfProduct": [
            (("design", "cad", "modell", "model"), "get_design_overview"),
            (("author", "autor"), "get_author_info"),
            (("descriptor", "version"), "get_model_descriptor"),
        ],
        "MachineScheduleLog": [
            (("history", "log", "historie"), "get_schedule_log"),
            (("update", "timestamp"), "get_last_update_log"),
        ],
        "SituationLog": [
            (("situation", "ereignis", "event"), "list_situations"),
        ],
        "RequiredCapabilityDescription": [
            (("required", "benotigt", "required capability"), "list_required_capabilities"),
            (("property set", "anforderung"), "list_required_property_sets"),
        ],
        "StorageConfiguration": [
            (("storage", "lager"), "list_storages"),
            (("slot", "slots"), "list_slots"),
            (("demand",), "get_demand_config"),
            (("projection",), "get_projection_config"),
        ],
        "CarbonFootprint": [
            (("co2", "carbon", "footprint"), "get_footprint_overview"),
            (("handover", "goods address"), "get_goods_address_handover"),
        ],
        "ProductIdentification": [
            (("identification", "identifikation", "product id"), "get_product_identification"),
            (("additional", "zusatz"), "get_additional_information"),
        ],
        "QualityInformation": [
            (("quality", "qualitat", "qualitaet"), "get_quality_information"),
        ],
        "TechnicalData": [
            (("general", "allgemein"), "get_general_information"),
            (("further", "weitere"), "get_further_information"),
        ],
        "SymptomDescription": [
            (("symptom", "sympt"), "list_symptoms"),
        ],
        "BillOfApplications": [
            (("applications", "application", "stack"), "list_applications"),
            (("digital production", "mnestix", "shellscape"), "get_application_stack"),
        ],
    }

    for keywords, candidate in generic_pairs:
        if candidate in tools_map and any(k in normalized_intent for k in keywords):
            return candidate

    for keywords, candidate in by_submodel.get(submodel, []):
        if candidate in tools_map and any(k in normalized_intent for k in keywords):
            return candidate

    return None

def select_tool_neo4j(state: AgentState) -> dict[str, Any]:
    """
    Select the appropriate Neo4j tool based on submodel + intent.
    """
    submodel = state.get("submodel", "Structure")
    intent = state.get("intent", "get_properties")
    resolved = state.get("resolved_entities") or {}
    entities = state.get("entities") or {}

    registry = SUBMODEL_REGISTRY.get(submodel, {})
    tools_map: dict[str, Any] = registry.get("tools", {})
    normalized_intent = _normalize_intent(intent)
    user_input = state.get("user_input", "")

    if submodel == "Skills" and _is_skill_endpoint_query(user_input) and "get_skill_endpoints" in tools_map:
        tool_name = "get_skill_endpoints"
    else:
        tool_name = None

    # Direct intent match
    if tool_name is None:
        tool_name = intent if intent in tools_map else None

    # Exact fallback mapping (stable aliases)
    if tool_name is None:
        fallback_map = {
            "get_structure": "get_parts",
            "list_parts": "get_parts",
            "get_bom": "get_parts",
            "list_steps": "get_steps",
            "check_done": "is_finished",
            "list_schedule": "get_schedule",
            "check_open_tasks": "has_open_tasks",
            "list_history": "get_schedule_log",
            "explain": "get_properties",
            "describe": "get_properties",
        }
        tool_name = fallback_map.get(intent)

    # Soft fallback mapping from natural language intents.
    if tool_name is None:
        tool_name = _select_soft_neo4j_tool(submodel, normalized_intent, tools_map)

    if tool_name is None:
        tool_name = "get_properties"

    # If still not found in this submodel's registry, use get_properties
    if tool_name not in tools_map:
        tool_name = "get_properties"

    tool_args: dict[str, Any] = {}
    if resolved.get("asset_id"):
        tool_args["asset_id"] = resolved["asset_id"]
    if resolved.get("step"):
        tool_args["step"] = resolved["step"]
    if resolved.get("element_id_short"):
        tool_args["element_id_short"] = resolved["element_id_short"]
    elif entities.get("element_id_short"):
        tool_args["element_id_short"] = entities["element_id_short"]
    if resolved.get("skill_id_short"):
        tool_args["skill_id_short"] = resolved["skill_id_short"]
    elif entities.get("skill_id_short"):
        tool_args["skill_id_short"] = entities["skill_id_short"]
    if resolved.get("skill_name"):
        tool_args["skill_name"] = resolved["skill_name"]
    elif entities.get("skill_name"):
        tool_args["skill_name"] = entities["skill_name"]
    if resolved.get("shell_id"):
        tool_args["shell_id"] = resolved["shell_id"]
    elif entities.get("shell_id"):
        tool_args["shell_id"] = entities["shell_id"]
    elif submodel == "Agents" and resolved.get("asset_id"):
        tool_args["shell_id"] = resolved["asset_id"]
    if submodel and "submodel" not in tool_args:
        tool_args["submodel"] = submodel

    return {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "requires_confirmation": False,
    }


# ── 5b. select_tool_generic ────────────────────────────────────────────────────

def select_tool_generic(state: AgentState) -> dict[str, Any]:
    """
    Select the appropriate tool for opcua / rag / kafka / agent_management.
    """
    capability = state.get("capability", "rag")
    intent = state.get("intent", "")
    resolved = state.get("resolved_entities") or {}
    entities = state.get("entities") or {}

    tool_name: str
    tool_args: dict[str, Any] = {}
    requires_confirmation = False
    confirmation_message = ""

    if capability == "opcua":
        endpoint = (
            resolved.get("endpoint")
            or entities.get("endpoint")
            or settings.opcua_endpoint
        )
        machine_name = resolved.get("machine_name") or entities.get("machine_name")
        component_name = resolved.get("component_name") or entities.get("component_name")
        skill_name = resolved.get("skill_name") or entities.get("skill_name")
        parameter_name = resolved.get("parameter_name") or entities.get("parameter_name")
        scope = entities.get("scope") or "execution"
        value = entities.get("value")
        action = entities.get("action") or "start"
        username = entities.get("username")
        password = entities.get("password")

        if intent == "connect_to_server":
            tool_name = "connect_to_server"
            tool_args = {"endpoint": endpoint, "username": username, "password": password}
        elif intent == "disconnect":
            tool_name = "disconnect"
            tool_args = {"endpoint": endpoint}
            requires_confirmation = True
            confirmation_message = (
                f"OPC UA Server '{endpoint}' wirklich trennen?"
            )
        elif intent in {"list_skills", "get_skills"}:
            tool_name = "list_skills"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
            }
        elif intent == "read_component_parameters":
            tool_name = "read_component_parameters"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
            }
        elif intent == "read_component_monitoring":
            tool_name = "read_component_monitoring"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
            }
        elif intent == "read_component_attributes":
            tool_name = "read_component_attributes"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
            }
        elif intent == "read_skill_parameters":
            tool_name = "read_skill_parameters"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
                "skill_name": skill_name,
                "scope": scope,
            }
        elif intent == "read_skill_monitoring":
            tool_name = "read_skill_monitoring"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
                "skill_name": skill_name,
                "scope": scope,
            }
        elif intent == "write_skill_parameter":
            tool_name = "write_skill_parameter"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
                "skill_name": skill_name,
                "parameter_name": parameter_name,
                "value": value,
                "scope": scope,
            }
            requires_confirmation = True
            confirmation_message = "Skill-Parameter wirklich schreiben?"
        elif intent == "execute_skill":
            tool_name = "execute_skill"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
                "skill_name": skill_name,
                "scope": scope,
                "action": action,
                "write_parameters": bool(entities.get("write_parameters", False)),
            }
            requires_confirmation = True
            confirmation_message = "Skill wirklich ausfuehren?"
        else:
            tool_name = "list_skills"
            tool_args = {
                "endpoint": endpoint,
                "machine_name": machine_name,
                "component_name": component_name,
            }

    elif capability == "kafka":
        command = {
            "action": intent,
            "asset_id": resolved.get("asset_id"),
            **{k: v for k, v in entities.items() if k not in {"asset", "asset_name"}},
        }
        tool_name = "send_command"
        tool_args = {"command": command}
        requires_confirmation = True
        confirmation_message = (
            f"Soll der Befehl '{intent}' wirklich ausgeführt werden? "
            f"Asset: {resolved.get('asset_id') or '(unbekannt)'}"
        )

    elif capability == "agent_management":
        tool_name = "get_all_registered_agents"
        tool_args = {}

        agent_id = (
            resolved.get("agent_id")
            or entities.get("agent_id")
            or entities.get("id")
            or entities.get("receiver")
        )

        if intent in {"get_all_registered_agents", "list_agents", "get_agents"}:
            tool_name = "get_all_registered_agents"
        elif intent == "get_agent_details" and agent_id:
            tool_name = "get_agent_details"
            tool_args = {"agent_id": agent_id}
        elif intent == "get_agents_of_agent" and agent_id:
            tool_name = "get_agents_of_agent"
            tool_args = {"agent_id": agent_id}
        elif intent == "spawn_agent":
            tool_name = "spawn_agent"
            tool_args = {
                "receiver": entities.get("receiver") or agent_id,
                "agent_id": entities.get("agent_id") or entities.get("target_agent_id"),
            }
            requires_confirmation = True
            confirmation_message = "Agent wirklich starten (spawn)?"
        elif intent == "restart_agent":
            tool_name = "restart_agent"
            tool_args = {"receiver": entities.get("receiver") or agent_id}
            requires_confirmation = True
            confirmation_message = "Agent wirklich neu starten?"
        elif intent == "kill_agent":
            tool_name = "kill_agent"
            tool_args = {"receiver": entities.get("receiver") or agent_id}
            requires_confirmation = True
            confirmation_message = "Agent wirklich beenden?"
        elif intent == "register_agent":
            tool_name = "register_agent"
            tool_args = {
                "agent_id": entities.get("agent_id") or entities.get("id"),
                "name": entities.get("name"),
                "agent_type": entities.get("agent_type") or entities.get("type"),
                "url": entities.get("url"),
                "ref": entities.get("ref"),
                "agents": entities.get("agents"),
                "capabilities": entities.get("capabilities"),
                "subs": entities.get("subs"),
                "neighbors": entities.get("neighbors"),
            }
            requires_confirmation = True
            confirmation_message = "Agent wirklich registrieren?"
        elif intent == "unregister_agent" and agent_id:
            tool_name = "unregister_agent"
            tool_args = {"agent_id": agent_id}
            requires_confirmation = True
            confirmation_message = "Agent wirklich deregistrieren?"
        elif intent == "list_kafka_topics":
            tool_name = "list_kafka_topics"
            tool_args = {"category": entities.get("category")}
        elif intent == "get_kafka_topic_info":
            tool_name = "get_kafka_topic_info"
            tool_args = {"topic_name": entities.get("topic_name")}
        elif intent == "read_kafka_messages":
            tool_name = "read_kafka_messages"
            tool_args = {
                "topic_name": entities.get("topic_name"),
                "max_messages": entities.get("max_messages", 10),
                "timeout_seconds": entities.get("timeout_seconds", 10),
            }
        elif intent == "order_storage_module_step_retrieve_amr_step":
            tool_name = "order_storage_module_step_retrieve_amr_step"
            tool_args = {
                "productid": entities.get("productid") or entities.get("product_id"),
                "product_type": entities.get("product_type"),
                "carrier_id": entities.get("carrier_id"),
            }
            requires_confirmation = True
            confirmation_message = "Storage-Step wirklich bestellen?"

    else:  # rag
        tool_name = "search_docs"
        tool_args = {"query": state.get("user_input", "")}

    return {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "requires_confirmation": requires_confirmation,
        "confirmation_message": confirmation_message,
    }


# ── 6. check_confirmation ──────────────────────────────────────────────────────

def check_confirmation(state: AgentState) -> dict[str, Any]:
    """
    If confirmation is required, the graph terminates early (END) so that the
    API can return the confirmation_message to the frontend.
    If no confirmation needed, this node is a pass-through.
    The actual routing is done by the conditional edge, not here.
    """
    return {}


# ── Shared utility ─────────────────────────────────────────────────────────────

def clean_tool_args(tool_args: dict[str, Any]) -> dict[str, Any]:
    """
    Strip internal routing keys (e.g. 'submodel') that are not real
    tool-function parameters.  Centralised here to avoid duplication
    between execute_tool and the /chat/confirm endpoint.
    """
    cleaned = dict(tool_args)
    cleaned.pop("submodel", None)
    return cleaned


def _select_neo4j_skill_fallback_tool(state: AgentState, opcua_tool_name: str) -> str:
    """Map OPC UA skill tool failures to suitable Neo4j Skills tools."""
    user_input = (state.get("user_input") or "").lower()
    if _is_skill_endpoint_query(user_input):
        return "get_skill_endpoints"
    if opcua_tool_name in {"read_skill_parameters", "write_skill_parameter", "execute_skill"}:
        return "list_skill_input_parameters"
    return "list_skills"


def _try_neo4j_skills_fallback(
    state: AgentState,
    original_tool_name: str,
) -> dict[str, Any] | None:
    """Run Neo4j Skills tool as fallback when OPC UA skill access fails."""
    resolved = state.get("resolved_entities") or {}
    entities = state.get("entities") or {}
    asset_id = resolved.get("asset_id")
    if not asset_id:
        return None

    skills_tools = (SUBMODEL_REGISTRY.get("Skills") or {}).get("tools", {})
    fallback_tool_name = _select_neo4j_skill_fallback_tool(state, original_tool_name)
    fallback_fn = skills_tools.get(fallback_tool_name)
    if fallback_fn is None:
        return None

    fallback_args: dict[str, Any] = {"asset_id": asset_id}
    skill_name = resolved.get("skill_name") or entities.get("skill_name")
    skill_id_short = resolved.get("skill_id_short") or entities.get("skill_id_short")
    if skill_name:
        fallback_args["skill_name"] = skill_name
    if skill_id_short:
        fallback_args["skill_id_short"] = skill_id_short

    try:
        fallback_result = fallback_fn(**fallback_args)
        return {
            "tool_result": fallback_result,
            "error": None,
            "capability": "neo4j",
            "submodel": "Skills",
            "tool_name": fallback_tool_name,
            "fallback_used": "neo4j_skills",
            "fallback_tool_name": fallback_tool_name,
        }
    except Exception as exc:
        logger.warning("Neo4j skills fallback failed: %s", exc)
        return None


# ── 7. execute_tool ────────────────────────────────────────────────────────────

def execute_tool(state: AgentState) -> dict[str, Any]:
    """
    Dispatch to the appropriate tool based on capability + tool_name.
    """
    capability = state.get("capability", "rag")
    tool_name = state.get("tool_name", "")
    tool_args = clean_tool_args(dict(state.get("tool_args") or {}))

    tool_fn = None

    if capability == "neo4j":
        submodel = state.get("submodel", "Structure")
        registry = SUBMODEL_REGISTRY.get(submodel, {})
        tool_fn = registry.get("tools", {}).get(tool_name)

    elif capability == "opcua":
        tool_fn = opcua_tools.OPCUA_TOOL_REGISTRY.get(tool_name)

    elif capability == "kafka":
        tool_fn = kafka_tools.KAFKA_TOOL_REGISTRY.get(tool_name)

    elif capability == "agent_management":
        tool_fn = agent_management_tools.AGENT_MANAGEMENT_TOOL_REGISTRY.get(tool_name)

    else:  # rag
        tool_fn = rag_tools.RAG_TOOL_REGISTRY.get(tool_name)

    if tool_fn is None:
        logger.error("No tool found for capability=%s tool=%s", capability, tool_name)
        return {"tool_result": None, "error": f"Unknown tool: {tool_name}"}

    # Guard against TypeError explosions by validating required args before call.
    signature = inspect.signature(tool_fn)
    required_args = [
        p.name
        for p in signature.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        and p.default is inspect.Parameter.empty
    ]
    missing_args = [arg for arg in required_args if arg not in tool_args]
    if missing_args:
        logger.warning(
            "Missing required tool args for %s/%s: %s",
            capability,
            tool_name,
            missing_args,
        )
        if capability == "opcua" and tool_name in {"list_skills", "read_skill_parameters", "read_skill_monitoring", "write_skill_parameter", "execute_skill"}:
            fallback_result = _try_neo4j_skills_fallback(state, tool_name)
            if fallback_result:
                return fallback_result
        return {
            "tool_result": {
                "missing_args": missing_args,
                "tool_name": tool_name,
                "capability": capability,
                "submodel": state.get("submodel"),
            },
            "error": "missing_required_arguments",
        }

    try:
        result = tool_fn(**tool_args)
        return {"tool_result": result, "error": None}
    except Exception as exc:
        logger.error("Tool execution failed: %s", exc)
        error_text = str(exc)
        opcua_connection_markers = (
            "Reached maximum number of retries",
            "ConnectionRefusedError",
            "Connect call failed",
            "BadIdentityTokenRejected",
            "timed out",
        )
        if capability == "opcua" and tool_name in {"list_skills", "read_skill_parameters", "read_skill_monitoring", "write_skill_parameter", "execute_skill"}:
            if any(marker in error_text for marker in opcua_connection_markers):
                fallback_result = _try_neo4j_skills_fallback(state, tool_name)
                if fallback_result:
                    return fallback_result
        return {"tool_result": None, "error": str(exc)}


# ── 8. generate_response ───────────────────────────────────────────────────────

def _tool_icon_footer(capability: str) -> str:
    source = {
        "neo4j": "🕸 Neo4j",
        "opcua": "📡 OPC UA",
        "rag": "📚 RAG",
        "kafka": "🛰 Kafka",
        "agent_management": "🧩 Agent Registry",
    }.get((capability or "").lower())
    if not source:
        return ""
    return f"\n\n🔎 Quelle: {source}"


def _capability_names_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = row.get("idShort") or row.get("value")
        name = str(raw).strip() if raw is not None else ""
        if not name:
            continue
        if name.lower() == "capabilityset":
            continue
        names.append(name)
    return _unique_ordered(names)


def _asset_label(asset_id: str) -> str:
    parts = [p for p in str(asset_id).split("/") if p]
    return parts[-1] if parts else str(asset_id)


def _format_capability_response(asset_id: str, tool_result: Any, submodel: str) -> str:
    asset_label = _asset_label(asset_id)
    if not isinstance(tool_result, list) or not tool_result:
        return (
            f"Ich habe fuer das Modul ({asset_label}) keine konkreten Capabilities im Submodell "
            f"'{submodel}' gefunden."
        )

    capability_names = _capability_names_from_rows(tool_result)
    if not capability_names:
        return (
            f"Ich habe fuer das Modul ({asset_label}) zwar Eintraege gefunden, aber keine eindeutig "
            "benennbaren Capability-Namen."
        )

    lines = [f"Ich habe folgende Capabilities fuer das Modul ({asset_label}) gefunden:", ""]
    lines.extend(f"- {name}" for name in capability_names[:20])
    if len(capability_names) > 20:
        lines.append(f"- ... und {len(capability_names) - 20} weitere")
    return "\n".join(lines)


def _format_exhibition_insights_response(tool_name: str, tool_result: Any) -> str | None:
    if not isinstance(tool_result, list) or not tool_result:
        return "Ich konnte dazu aktuell keine Kennzahlen im Produktionsgraphen finden."

    row = tool_result[0] if isinstance(tool_result[0], dict) else {}

    if tool_name == "get_today_truck_production":
        try:
            produced_today = int(row.get("produced_today") or 0)
        except (TypeError, ValueError):
            produced_today = 0
        return f"Heute wurden {produced_today} Truck-Produkte erfolgreich fertiggestellt."

    if tool_name == "count_successfully_finished_products":
        try:
            finished = int(row.get("products_finished_successfully") or 0)
        except (TypeError, ValueError):
            finished = 0
        return f"Bisher wurden insgesamt {finished} Produkte erfolgreich fertiggestellt."

    if tool_name == "count_total_products":
        try:
            total = int(row.get("products_total") or 0)
        except (TypeError, ValueError):
            total = 0
        try:
            finished = int(row.get("products_finished_successfully") or 0)
        except (TypeError, ValueError):
            finished = 0
        try:
            unfinished = int(row.get("products_unfinished") or max(total - finished, 0))
        except (TypeError, ValueError):
            unfinished = max(total - finished, 0)
        return (
            f"Im Graph sind aktuell insgesamt {total} Produkte erfasst, "
            f"davon {finished} erfolgreich fertiggestellt und {unfinished} noch nicht fertig."
        )

    if tool_name == "get_production_kpi_overview":
        def _ival(key: str) -> int:
            try:
                return int(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0

        total = _ival("products_total")
        finished = _ival("products_finished_successfully")
        unfinished = _ival("products_unfinished")
        in_prod = _ival("products_in_production")
        return (
            f"Produktionsstatus gesamt: {total} Produkte im Graph, "
            f"{finished} erfolgreich fertiggestellt, {unfinished} noch nicht fertig, "
            f"davon {in_prod} aktuell in Produktion."
        )

    if tool_name == "count_products_in_production":
        try:
            in_prod = int(row.get("products_in_production") or 0)
        except (TypeError, ValueError):
            in_prod = 0
        return f"Aktuell sind {in_prod} Produkte in Produktion."

    if tool_name == "get_average_assembly_duration":
        try:
            avg_minutes = float(row.get("avg_assembly_duration_minutes") or 0.0)
        except (TypeError, ValueError):
            avg_minutes = 0.0
        try:
            sample_steps = int(row.get("sample_steps") or 0)
        except (TypeError, ValueError):
            sample_steps = 0
        return (
            f"Die durchschnittliche Dauer des Montageprozesses (Assemble-Step, Status done) "
            f"liegt bei {avg_minutes:.2f} Minuten (Stichprobe: {sample_steps} Steps)."
        )

    if tool_name == "count_products_with_quality_check_step":
        def _ival(key: str) -> int:
            try:
                return int(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0

        total = _ival("products_total")
        with_qc = _ival("products_with_quality_check_step")
        without_qc = _ival("products_without_quality_check_step")
        return (
            f"Von {total} Produkten enthalten {with_qc} einen QualityCheck-Step "
            f"und {without_qc} enthalten keinen QualityCheck-Step."
        )

    if tool_name == "count_finished_products_last_24h":
        try:
            value = int(row.get("products_finished_last_24h") or 0)
        except (TypeError, ValueError):
            value = 0
        return f"In den letzten 24 Stunden wurden {value} Produkte erfolgreich fertiggestellt."

    if tool_name == "count_finished_products_last_7d":
        try:
            value = int(row.get("products_finished_last_7d") or 0)
        except (TypeError, ValueError):
            value = 0
        return f"In den letzten 7 Tagen wurden {value} Produkte erfolgreich fertiggestellt."

    if tool_name == "breakdown_products_by_type":
        if not isinstance(tool_result, list) or not tool_result:
            return "Ich konnte keine Produkttyp-Verteilung ermitteln."
        parts: list[str] = []
        for row_i in tool_result[:8]:
            if not isinstance(row_i, dict):
                continue
            ptype = str(row_i.get("product_type") or "unknown")
            try:
                cnt = int(row_i.get("products_count") or 0)
            except (TypeError, ValueError):
                cnt = 0
            parts.append(f"{ptype}: {cnt}")
        if not parts:
            return "Ich konnte keine Produkttyp-Verteilung ermitteln."
        return "Produktverteilung nach Typ: " + "; ".join(parts) + "."

    if tool_name == "get_module_step_status_overview":
        if not isinstance(tool_result, list) or not tool_result:
            return "Ich konnte keine Step-Statusverteilung pro Modul finden."
        compact: dict[str, dict[str, int]] = {}
        for row_i in tool_result:
            if not isinstance(row_i, dict):
                continue
            module = str(row_i.get("module_station") or "unknown")
            status = str(row_i.get("step_status") or "unknown")
            try:
                cnt = int(row_i.get("step_count") or 0)
            except (TypeError, ValueError):
                cnt = 0
            compact.setdefault(module, {})[status] = cnt

        lines: list[str] = []
        for module, statuses in list(compact.items())[:8]:
            status_text = ", ".join(f"{k}={v}" for k, v in sorted(statuses.items()))
            lines.append(f"{module}: {status_text}")
        return "Step-Status pro Modul/Station: " + " | ".join(lines)

    return None

def generate_response(state: AgentState) -> dict[str, Any]:
    """
    Produce a natural-language response from the tool result.
    Appends an :class:`~langchain_core.messages.AIMessage` to ``messages``
    so the agent-chat-ui can render the answer.
    """
    error = state.get("error")
    tool_result = state.get("tool_result")
    capability = state.get("capability", "")
    selected_tool = state.get("tool_name", "")
    submodel = state.get("submodel", "")
    intent = state.get("intent", "")
    user_input = state.get("user_input", "")
    asset_id = (state.get("resolved_entities") or {}).get("asset_id", "")
    session_id = state.get("session_id")
    session_ctx: dict[str, Any] = {}
    if session_id:
        try:
            session_ctx = session_svc.get_session(session_id)
        except Exception as exc:
            logger.debug("Session context unavailable in generate_response: %s", exc)
    chat_history = session_ctx.get("chat_history") if isinstance(session_ctx, dict) else None

    has_tool_context = bool(selected_tool) or tool_result is not None

    if (not error) and (not has_tool_context) and _is_assistant_meta_query(user_input):
        text = _build_assistant_intro_response()
        return {
            "response": text,
            "messages": [AIMessage(content=text)],
        }

    if _is_summary_request(user_input):
        if _is_session_recap_request(user_input):
            text = _build_last_summary_response(session_ctx)
            return {
                "response": text,
                "messages": [AIMessage(content=text)],
            }

        rag_summary = _build_rag_fallback_response(user_input)
        if rag_summary:
            _store_summary_in_session(session_id, rag_summary)
            return {
                "response": rag_summary,
                "messages": [AIMessage(content=rag_summary)],
            }

        text = _build_last_summary_response(session_ctx)
        return {
            "response": text,
            "messages": [AIMessage(content=text)],
        }

    if (not error) and (not has_tool_context) and _is_tool_discovery_query(user_input):
        text = _build_tool_discovery_text(asset_id or None)
        return {
            "response": text,
            "messages": [AIMessage(content=text)],
        }

    if _is_agent_inventory_query(user_input) and capability != "agent_management":
        text = "Ich weiß es nicht und habe dafuer aktuell kein passendes Tool."
        return {
            "response": text,
            "messages": [AIMessage(content=text)],
        }

    if (not error) and (not has_tool_context) and _is_general_question(user_input):
        text = _build_no_tool_general_response()
        return {
            "response": text,
            "messages": [AIMessage(content=text)],
        }

    # ── Compute response text ─────────────────────────────────────────────────
    if error == "missing_required_arguments":
        missing_args = (tool_result or {}).get("missing_args") or []
        if "asset_id" in missing_args:
            rag_fallback = _build_rag_fallback_response(user_input)
            if rag_fallback:
                _store_summary_in_session(session_id, rag_fallback)
                text = (
                    f"{rag_fallback}\n\n"
                    "Wenn du zusatzlich exakte Asset-Daten aus Neo4j willst, "
                    "nenne bitte die Anlage oder Asset-ID (z. B. 'Anlage A')."
                )
            else:
                text = (
                    "Gerne helfe ich dir dabei. Fur diese Abfrage brauche ich ein Asset. "
                    "Bitte nenne die Anlage oder Asset-ID (z. B. 'Anlage A')."
                )
        else:
            text = (
                "Ich konnte das Tool noch nicht ausfuhren, weil Parameter fehlen: "
                f"{', '.join(missing_args)}"
            )
    elif error and (
        "Errno 113" in str(error)
        or "Connect call failed" in str(error)
        or "BadIdentityTokenRejected" in str(error)
    ):
        text = (
            "Ich konnte den OPC-UA-Server gerade nicht sauber verbinden. "
            "Bitte prufe Endpoint, Netzwerkroute und ggf. Benutzer/Passwort.\n\n"
            "Wenn du willst, helfe ich dir Schritt fur Schritt beim Verbindungscheck."
        )
    elif error:
        if capability == "agent_management":
            text = "Ich weiß es nicht, weil ich dafuer gerade kein passendes erreichbares Agent-Management-Tool habe."
        else:
            text = f"Das hat leider nicht geklappt. Fehler: {error}"
    elif tool_result is None:
        text = "Es wurden keine Daten gefunden."
    elif capability == "rag":
        if isinstance(tool_result, list) and tool_result:
            summary_text = _format_rag_summary_text(user_input, tool_result)
            if summary_text:
                text = summary_text
                _store_summary_in_session(session_id, summary_text)
            else:
                text = (
                    "Ich finde dazu keine ausreichend belastbaren Treffer in der Dokumentation. "
                    "Bitte nenne ein konkretes Thema (z. B. Referenzarchitektur, P17, Skills oder OPC-UA-Schnittstelle)."
                )
        else:
            text = (
                "Ich habe dazu in der Dokumentation nichts Eindeutiges gefunden. "
                "Wenn du magst, formuliere ich die Suche praziser oder wir wechseln "
                "auf eine konkrete Asset- oder Tool-Abfrage."
            )
    elif capability == "opcua":
        if isinstance(tool_result, dict):
            status = tool_result.get("status", "")
            endpoint = tool_result.get("endpoint", "")
            if status in ("connected", "disconnected", "not_registered", "locked"):
                text = f"Server '{endpoint}': {status}"
            elif isinstance(tool_result.get("machines"), dict):
                machines = tool_result.get("machines") or {}
                machine_parts: list[str] = []
                for machine_name, machine_data in list(machines.items())[:5]:
                    skills = machine_data.get("skills") or []
                    skill_names = [s.get("name") for s in skills[:3] if isinstance(s, dict) and s.get("name")]
                    if skill_names:
                        machine_parts.append(
                            f"{machine_name}: {len(skills)} Skills ({', '.join(skill_names)})"
                        )
                    else:
                        machine_parts.append(f"{machine_name}: {len(skills)} Skills")
                text = (
                    f"Ich habe {len(machines)} Maschine(n) gefunden. "
                    + " | ".join(machine_parts)
                )
            elif isinstance(tool_result.get("machines"), list):
                machines = tool_result.get("machines") or []
                text = f"Ich sehe {len(machines)} Maschine(n): {', '.join(str(m) for m in machines[:10])}"
            elif isinstance(tool_result.get("parameters"), list):
                params = tool_result.get("parameters") or []
                sample = [
                    f"{p.get('name')}={p.get('value')}"
                    for p in params[:5]
                    if isinstance(p, dict)
                ]
                text = (
                    f"Ich habe {len(params)} Parameter gelesen"
                    + (f" ({'; '.join(sample)})" if sample else "")
                )
            elif isinstance(tool_result.get("monitoring"), list):
                monitoring = tool_result.get("monitoring") or []
                sample = [
                    f"{m.get('name')}={m.get('value')}"
                    for m in monitoring[:5]
                    if isinstance(m, dict)
                ]
                text = (
                    f"Ich habe {len(monitoring)} Monitoring-Werte gelesen"
                    + (f" ({'; '.join(sample)})" if sample else "")
                )
            elif isinstance(tool_result.get("attributes"), list):
                attrs = tool_result.get("attributes") or []
                sample = [
                    f"{a.get('name')}={a.get('value')}"
                    for a in attrs[:5]
                    if isinstance(a, dict)
                ]
                text = (
                    f"Ich habe {len(attrs)} Attribute gelesen"
                    + (f" ({'; '.join(sample)})" if sample else "")
                )
            else:
                value = tool_result.get("value")
                node_id = tool_result.get("node_id", "")
                ts = tool_result.get("source_timestamp", "")
                text = f"Node {node_id} @ {endpoint}: {value} (Zeitstempel: {ts})"
        elif isinstance(tool_result, list):
            count = len(tool_result)
            names = [e.get("display_name") or e.get("node_id") for e in tool_result[:10]]
            text = f"{count} Knoten gefunden: {', '.join(str(n) for n in names)}"
        else:
            text = f"OPC UA Ergebnis erhalten: {_safe_result_hint(tool_result)}."
    elif capability == "kafka":
        text = f"Befehl gesendet: {tool_result}"
    elif capability == "agent_management":
        if state.get("tool_name") == "get_all_registered_agents" or _is_agent_inventory_query(user_input):
            if isinstance(tool_result, list):
                if tool_result:
                    shown = ", ".join(str(x) for x in tool_result[:25])
                    extra = "" if len(tool_result) <= 25 else f" (+{len(tool_result) - 25} weitere)"
                    text = f"Ich habe {len(tool_result)} Agenten gefunden: {shown}{extra}"
                else:
                    text = "Ich habe keine registrierten Agenten gefunden."
            elif isinstance(tool_result, dict) and isinstance(tool_result.get("agents"), list):
                agents = tool_result.get("agents") or []
                if agents:
                    names = ", ".join(str(a) for a in agents[:25])
                    extra = "" if len(agents) <= 25 else f" (+{len(agents) - 25} weitere)"
                    text = f"Ich habe {len(agents)} Agenten gefunden: {names}{extra}"
                else:
                    text = "Ich habe keine registrierten Agenten gefunden."
            else:
                text = "Ich konnte gerade keine eindeutige Agentenliste aus der Registry lesen."
        else:
            text = "Ich habe Agent-Management-Daten erhalten und bereite sie verstaendlich auf."
    elif capability == "neo4j":
        if submodel == "ExhibitionInsights":
            formatted = _format_exhibition_insights_response(selected_tool, tool_result)
            if formatted:
                text = formatted
            elif isinstance(tool_result, list):
                text = f"Ich habe {len(tool_result)} KPI-Eintraege gefunden."
            else:
                text = f"KPI-Ergebnis: {_safe_result_hint(tool_result)}."
        else:
            should_build_story = (
                _is_exploratory_query(user_input)
                or (isinstance(tool_result, list) and len(tool_result) > 10)
                or selected_tool in {"list_skills", "get_skill_endpoints", "list_skill_input_parameters", "get_properties"}
            )
            if asset_id:
                capability_focused = False
                if submodel in {"OfferedCapabilityDescription", "RequiredCapabilityDescription"} and selected_tool in {
                    "list_capabilities",
                    "list_required_capabilities",
                    "get_properties",
                }:
                    text = _format_capability_response(asset_id, tool_result, submodel)
                    capability_focused = True
                elif "capabil" in user_input.lower() and isinstance(tool_result, list):
                    text = _format_capability_response(asset_id, tool_result, submodel or "OfferedCapabilityDescription")
                    capability_focused = True

                if should_build_story and not capability_focused:
                    text = _build_neo4j_structured_summary(
                        asset_id=asset_id,
                        tool_name=selected_tool,
                        tool_result=tool_result,
                        user_input=user_input,
                    )
                elif not capability_focused and isinstance(tool_result, list):
                    text = f"Fuer Asset '{asset_id}' habe ich {len(tool_result)} passende Eintrage gefunden. Wenn du willst, fasse ich sie als kompakten Fach-Report zusammen."
                elif not capability_focused:
                    text = f"Fuer Asset '{asset_id}' liegen strukturierte Ergebnisse vor: {_safe_result_hint(tool_result)}."
            elif isinstance(tool_result, list):
                text = f"Ich habe {len(tool_result)} Eintrage gefunden, aber noch ohne eindeutigen Asset-Bezug. Nenne bitte das Asset (z. B. P17), dann fasse ich es gezielt zusammen."
            else:
                text = f"Ergebnis erhalten: {_safe_result_hint(tool_result)}."
    elif isinstance(tool_result, list):
        count = len(tool_result)
        text = f"Ergebnis: {count} Einträge gefunden."
    else:
        text = f"Ergebnis erhalten: {_safe_result_hint(tool_result)}."

    # Always run one post-tool LLM pass to translate technical outputs into
    # natural language for users. No silent fallback: fail fast if unavailable.
    if (
        settings.chat_enable_llm_tool_result_summarization
        and error is None
        and tool_result is not None
        and selected_tool
    ):
        try:
            text = llm.summarize_tool_result_for_visitors(
                user_input=user_input,
                capability=capability,
                tool_name=str(selected_tool),
                tool_result=tool_result,
                draft_response=text,
                chat_history=chat_history if isinstance(chat_history, list) else None,
            ) or ""
        except Exception as exc:
            logger.error("LLM tool-result summarization failed: %s", exc)
            # Keep the deterministic draft text instead of failing user output.
            text = text or "Ich kann das Tool-Ergebnis gerade nicht ausformulieren."

    if settings.chat_visitor_mode and settings.chat_enable_llm_response_polish:
        polished = llm.polish_response_for_visitors(
            user_input=user_input,
            draft_response=text,
            capability=capability,
            tool_name=str(state.get("tool_name") or ""),
            chat_history=chat_history if isinstance(chat_history, list) else None,
        )
        if polished:
            text = polished

    footer = _tool_icon_footer(capability)
    if footer and selected_tool:
        footer = f"{footer} [Tool: {selected_tool}]"
    text = f"{text}{footer}"

    return {
        "response": text,
        "messages": [AIMessage(content=text)],
    }
