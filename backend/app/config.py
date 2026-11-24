"""Application Configuration using Pydantic Settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System settings for NOESIS runtime."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "NOESIS"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Graph Storage Mode: "neo4j" or "in_memory"
    GRAPH_STORAGE_MODE: str = Field(
        default="in_memory",
        description="Graph storage engine: 'neo4j' or 'in_memory'",
    )

    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "noesis_secret_pass"

    # Local LLM (Ollama) Settings
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_CONTEXT_LENGTH: int = 4096
    OLLAMA_TEMPERATURE: float = 0.0
    OLLAMA_CONCURRENCY: int = 1
    ALLOW_CLOUD_LLM: bool = False
    OLLAMA_TIMEOUT_SECONDS: float = 30.0
    OLLAMA_MAX_RETRIES: int = 2

    # Ingestion & Chunking Settings
    MAX_DOCUMENT_SIZE_MB: int = 15
    MAX_UPLOAD_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    CHUNK_SIZE_CHARS: int = 2400  # ~600 tokens
    CHUNK_OVERLAP_CHARS: int = 350  # ~85 tokens
    EXTRACTION_CACHE_DIR: str = ".cache/extraction"

    # Logging Level
    LOG_LEVEL: str = "INFO"

    # Server Networking
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Reasoning Constraints
    MAX_TRAVERSAL_HOPS: int = 5
    MAX_REASONING_PATHS: int = 20
    REASONING_TIMEOUT_SECONDS: float = 10.0


settings = Settings()
