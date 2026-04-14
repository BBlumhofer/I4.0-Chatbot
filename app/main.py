"""
FastAPI application entry point for the I4.0 Chatbot.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.openai_routes import router as openai_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)

app = FastAPI(
    title="I4.0 Produktionsanlagen-Assistent",
    description=(
        "LLM-gestützter, zustandsbasierter Assistent für industrielle "
        "Produktionsanlagen. Unterstützt Neo4j/AAS, OPC UA, RAG und Kafka."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom REST API (existing endpoints: /chat, /chat/stream, /chat/confirm, etc.)
app.include_router(router)

# OpenAI-compatible API consumed by Open WebUI (/v1/models, /v1/chat/completions)
app.include_router(openai_router)
