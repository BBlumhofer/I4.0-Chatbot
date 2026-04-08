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

Regeln:
- Antworte NUR im JSON-Format – keine weiteren Texte
- Wenn kein Submodell nötig → null
- Keine Halluzinationen
- Nutze nur bekannte Werte

Antworte stets mit folgendem JSON:
{
  "intent": "<string>",
  "capability": "<neo4j|opcua|rag|kafka>",
  "submodel": "<submodel_name oder null>",
  "entities": { "<key>": "<value>", ... }
}
"""


def _build_client() -> OpenAI:
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


def interpret(user_input: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Send *user_input* to the LLM and return the parsed JSON dict.

    Falls back to a safe default on parse errors so the graph can continue.
    """
    client = _build_client()

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        ctx_text = (
            f"Aktueller Kontext: Asset={context.get('current_asset')}, "
            f"Submodell={context.get('current_submodel')}"
        )
        messages.append({"role": "system", "content": ctx_text})

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
        logger.error("LLM interpretation failed: %s", exc)
        return {
            "intent": "unknown",
            "capability": "rag",
            "submodel": None,
            "entities": {},
        }
