"""
LLM Interpretation Service.

Uses a local OpenAI-compatible endpoint (e.g. Ollama) to extract:
  intent, capability, submodel, entities
from a user's natural-language message.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Du bist ein Assistent für eine industrielle Produktionsanlage.

Deine Aufgabe:
1. Bestimme die Capability (Datenquelle)
2. Bestimme die Intention
3. Extrahiere relevante Entitäten
4. Wenn Capability = neo4j → bestimme das passende Submodell

Capabilities:
- neo4j: Struktur, AAS, Produktionsdaten, MES-Informationen
- opcua: Live-Zustände und Sensorwerte
- rag: Dokumentation und Erklärungen
- kafka: Aktionen / Steuerbefehle
- agent_management: AgentRegistry, Agent-Lifecycle, Agent-Hierarchie

Submodelle (nur für neo4j relevant):
- ProductionPlan: Produktionsschritte, Dauer, Status
- Nameplate: Typschild-Informationen zur Anlage
- BillOfMaterial: Stückliste, Teile
- MaterialData: Materialeigenschaften
- Skills: Fähigkeiten einer Ressource
- AssetInterfaceDescription: Schnittstellenbeschreibung
- FaultDescription: Fehlerbeschreibungen
- Structure: allgemeiner Aufbau und Hierarchie
- ConditionMonitoring: Zustände, historische Werte
- Agents: Agent-Topologie und verbundene Knoten
- ExhibitionInsights: Flexible Messe-KPIs (Produktion, Module, Agenten, Lager)
- OfferedCapabilityDescription: angebotene Capabilities/Faehigkeiten eines Moduls
- RequiredCapabilityDescription: benoetigte/erforderliche Capabilities

Regeln:
- Antworte NUR im JSON-Format – keine weiteren Texte
- Wenn kein Submodell nötig → null
- Keine Halluzinationen
- Nutze nur bekannte Werte
- Für Capability opcua nutze bevorzugt diese Intents:
    connect_to_server, disconnect, list_skills, read_component_parameters,
    read_component_monitoring, read_component_attributes, read_skill_parameters,
    read_skill_monitoring, write_skill_parameter, execute_skill
- Für Capability agent_management nutze bevorzugt diese Intents:
    get_all_registered_agents, get_agent_details, get_agents_of_agent,
    register_agent, unregister_agent, spawn_agent, restart_agent, kill_agent,
    list_kafka_topics, get_kafka_topic_info, read_kafka_messages,
    order_storage_module_step_retrieve_amr_step

Antworte stets mit folgendem JSON:
{
  "intent": "<string>",
    "capability": "<neo4j|opcua|rag|kafka|agent_management>",
  "submodel": "<submodel_name oder null>",
  "entities": { "<key>": "<value>", ... }
}
"""


def _build_client(timeout_seconds: float | None = None) -> OpenAI:
    timeout = float(timeout_seconds) if timeout_seconds is not None else float(settings.llm_timeout_seconds)
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=timeout,
        max_retries=0,
    )


def interpret(user_input: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Send *user_input* to the LLM and return the parsed JSON dict.

    Falls back to a safe default on parse errors so the graph can continue.
    """
    client = _build_client(timeout_seconds=float(settings.llm_timeout_seconds))

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        ctx_text = (
            f"Aktueller Kontext: Asset={context.get('current_asset')}, "
            f"Submodell={context.get('current_submodel')}"
        )
        messages.append({"role": "system", "content": ctx_text})

        history = context.get("chat_history")
        if isinstance(history, list) and history:
            last_turns = history[-8:]
            lines: list[str] = []
            for turn in last_turns:
                if not isinstance(turn, dict):
                    continue
                role = str(turn.get("role") or "user")
                text = str(turn.get("text") or "").strip()
                if not text:
                    continue
                speaker = "Nutzer" if role == "user" else "Assistent"
                lines.append(f"- {speaker}: {text[:240]}")
            if lines:
                messages.append(
                    {
                        "role": "system",
                        "content": "Letzte Chat-Historie (fuer Kontext):\n" + "\n".join(lines),
                    }
                )

    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        result: dict[str, Any] = json.loads(raw)
        logger.debug("LLM interpretation: %s", result)
        return result
    except Exception as exc:
        if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
            logger.warning("LLM interpretation timeout; using fallback routing: %s", exc)
        else:
            logger.error("LLM interpretation failed: %s", exc)
        return {
            "intent": "unknown",
            "capability": "rag",
            "submodel": None,
            "entities": {},
        }


def summarize_rag(question: str, snippets: list[str]) -> str | None:
    """
    Summarize retrieved RAG snippets into the required response schema.

    Returns text in this format:
      Habe das gefunden:
      - ...

      Zusammenfassend:
      ...
    """
    if not snippets:
        return None

    client = _build_client()

    system_prompt = """\
Du bist ein technischer Assistent. Du bekommst eine Nutzerfrage und Dokument-Snippets.
Nutze nur diese Snippets, erfinde nichts.

Antworte exakt in diesem Format:
Habe das gefunden:
- <Punkt 1>
- <Punkt 2>
- <Punkt 3>

Zusammenfassend:
<ausfuhrliche, inhaltlich konkrete Zusammenfassung in 4-7 Satzen>

Regeln:
- Maximal 3 Punkte unter 'Habe das gefunden'.
- Keine langen Zitate, sondern eigene kurze Aussagen.
- Wenn Informationen unklar oder widerspruchlich sind, klar markieren.
- Erklaere Zusammenhange und Nutzen, nicht nur Stichworte.
- Bei Architekturfragen benenne mindestens: Zielbild, zentrale Bausteine, Nutzen in der Praxis.
"""

    snippet_block = "\n\n".join(
        f"[Snippet {idx + 1}]\n{snippet[:1200]}" for idx, snippet in enumerate(snippets[:4])
    )
    user_prompt = (
        f"Frage:\n{question}\n\n"
        f"Dokument-Snippets:\n{snippet_block}\n"
    )

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            return None
        if "Habe das gefunden:" not in content or "Zusammenfassend:" not in content:
            return None
        return content
    except Exception as exc:
        logger.warning("LLM RAG summarization failed: %s", exc)
        return None


def polish_response_for_visitors(
    user_input: str,
    draft_response: str,
    capability: str,
    tool_name: str,
    chat_history: Optional[list[dict[str, str]]] = None,
) -> str | None:
    """
    Rewrite a draft answer into visitor-friendly German for exhibition use.

    Returns None if polishing fails so callers can safely keep the draft text.
    """
    if not draft_response.strip():
        return None

    client = _build_client()
    system_prompt = """\
Du bist ein Erklaer-Assistent fuer Messebesucher in einer Smart-Factory-Demo.
Formuliere in klarem, freundlichem Deutsch ohne Fachjargon-Overload.

Regeln:
- Behalte alle Fakten aus dem Entwurf bei, erfinde nichts.
- Maximal 5 Saetze.
- Wenn Tools genutzt wurden, erwaehne es kurz und einfach (z. B. "Ich habe Live-Daten geprueft").
- Keine JSON-Ausgabe, kein Markdown-Overkill.
"""

    user_prompt = (
        f"Nutzerfrage: {user_input}\n"
        f"Capability: {capability}\n"
        f"Tool: {tool_name}\n"
        f"Entwurf:\n{draft_response}\n\n"
        "Bitte liefere nur den finalen, natuerlichen Antworttext."
    )

    if chat_history:
        history_lines: list[str] = []
        for turn in chat_history[-8:]:
            role = str(turn.get("role") or "user")
            text = str(turn.get("text") or "").strip()
            if not text:
                continue
            speaker = "Nutzer" if role == "user" else "Assistent"
            history_lines.append(f"- {speaker}: {text[:240]}")
        if history_lines:
            user_prompt += "\n\nBisheriger Verlauf:\n" + "\n".join(history_lines)

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        return content or None
    except Exception as exc:
        logger.debug("LLM response polishing skipped due to error: %s", exc)
        return None


def summarize_tool_result_for_visitors(
    user_input: str,
    capability: str,
    tool_name: str,
    tool_result: Any,
    draft_response: str,
    chat_history: Optional[list[dict[str, str]]] = None,
) -> str | None:
    """
    Convert structured tool output into a natural visitor-facing answer.

    Raises on failure so callers do not silently fall back to raw/heuristic text.
    """
    if not draft_response.strip():
        raise ValueError("draft_response is empty")

    client = _build_client()
    system_prompt = """\
Du bist ein Erklaer-Assistent fuer Messebesucher.
Formuliere aus Tool-Ergebnissen eine klare, hilfreiche Antwort auf Deutsch.

Regeln:
- Erfinde keine Daten, nutze nur Tool-Ergebnis und Entwurf.
- Keine rohe Python-Dict/List-Ausgabe, keine JSON-Dumps.
- Erklaere die wichtigsten Punkte in natuerlicher Sprache.
- Wenn Felder fehlen oder leer sind, benenne das kurz (z. B. "Name nicht gesetzt").
- Maximal 7 Saetze.
"""

    serialized_result = json.dumps(tool_result, ensure_ascii=False, default=str)
    user_prompt = (
        f"Nutzerfrage: {user_input}\n"
        f"Capability: {capability}\n"
        f"Tool: {tool_name}\n"
        f"Tool-Ergebnis (JSON):\n{serialized_result}\n\n"
        f"Entwurf/Fallback:\n{draft_response}\n\n"
        "Gib nur den finalen Antworttext aus."
    )

    if chat_history:
        history_lines: list[str] = []
        for turn in chat_history[-8:]:
            role = str(turn.get("role") or "user")
            text = str(turn.get("text") or "").strip()
            if not text:
                continue
            speaker = "Nutzer" if role == "user" else "Assistent"
            history_lines.append(f"- {speaker}: {text[:240]}")
        if history_lines:
            user_prompt += "\n\nBisheriger Verlauf:\n" + "\n".join(history_lines)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("LLM returned empty summarization content")
    return content
