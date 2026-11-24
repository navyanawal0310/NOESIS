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
