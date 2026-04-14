"""
Central configuration using environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Redis (session storage)
    redis_url: str = "redis://localhost:6379"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_command_topic: str = "plant.commands"

    # Agent management / registry
    agent_registry_url: str = "https://agent-registry.phuket.plant.smartfactory.de/"
    agent_registry_key: str = ""
    agent_registry_timeout_seconds: int = 15

    # OPC UA
    opcua_endpoint: str = "opc.tcp://localhost:4840"
    opcua_credentials_file: str = "cred.json"
    opcua_enable_write_execute: bool = False

    # LLM
    # Use localhost by default — many dev environments run Ollama locally.
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "nemotron-3-super:120b"
    llm_api_key: str = "ollama"
    llm_timeout_seconds: int = 25

    # ChromaDB (RAG vector store)
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "plant_docs"
    rag_default_n_results: int = 8
    rag_max_distance: float = 1.6
    rag_min_lexical_overlap: int = 1

    # Embeddings
    embedding_provider: str = "ollama"  # ollama | chroma
    embedding_model: str = "embeddinggemma:latest"
    embedding_base_url: Optional[str] = None
    embedding_timeout_seconds: int = 60

    # Entity resolution
    entity_fuzzy_threshold: float = 0.6

    # Response style / UX
    chat_visitor_mode: bool = True
    chat_enable_llm_tool_result_summarization: bool = False
    chat_enable_llm_response_polish: bool = False


settings = Settings()
