"""
Central configuration using environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # OPC UA
    opcua_endpoint: str = "opc.tcp://localhost:4840"

    # LLM
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3"
    llm_api_key: str = "ollama"

    # ChromaDB (RAG vector store)
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "plant_docs"

    # Entity resolution
    entity_fuzzy_threshold: float = 0.6


settings = Settings()
