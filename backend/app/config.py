"""Application Configuration using Pydantic Settings."""

import json
from typing import Any, List

from pydantic import Field, field_validator
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

    # Neo4j Settings (Local Development Default - Override in production via env)
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j bolt URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="noesis_dev_secret", description="Neo4j password")

    # Local LLM (Ollama) Settings
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_CONTEXT_LENGTH: int = Field(default=2048, gt=0, description="Ollama context window in tokens")
    OLLAMA_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature")
    OLLAMA_CONCURRENCY: int = Field(default=1, gt=0, description="Max concurrent inferences on GPU")
    ALLOW_CLOUD_LLM: bool = False
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=180.0, gt=0.0, description="Inference timeout in seconds")
    OLLAMA_HEALTH_TIMEOUT_SECONDS: float = Field(default=3.0, gt=0.0, description="Health check probe timeout")
    OLLAMA_KEEP_ALIVE: str = Field(default="10m", description="Ollama model keep-alive duration")
    OLLAMA_MAX_RETRIES: int = Field(default=0, ge=0, description="Retry attempts (0 = fail-fast)")
    OLLAMA_THINK: bool = Field(default=False, description="Enable or suppress internal reasoning thoughts")
    OLLAMA_MAX_GENERATED_TOKENS: int = Field(default=1024, gt=0, description="Maximum tokens to generate")

    # Ingestion & Chunking Settings
    MAX_DOCUMENT_SIZE_MB: int = Field(default=15, gt=0)
    MAX_UPLOAD_FILE_SIZE_BYTES: int = Field(default=15 * 1024 * 1024, gt=0)  # 15 MB
    CHUNK_SIZE_CHARS: int = Field(default=2400, gt=0)  # ~600 tokens
    CHUNK_OVERLAP_CHARS: int = Field(default=350, ge=0)  # ~85 tokens
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
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8042",
    ]

    # Reasoning Constraints
    MAX_TRAVERSAL_HOPS: int = Field(default=5, ge=1, le=5)
    MAX_REASONING_PATHS: int = Field(default=20, gt=0)
    REASONING_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0.0)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Supports parsing comma-separated strings or JSON arrays into List[str]."""
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [origin.strip() for origin in v_clean.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["*"]


settings = Settings()
