"""Graph Repository Factory and Lifecycle Management."""

import logging
from backend.app.config import settings
from backend.app.graph.base import BaseGraphRepository
from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.graph.neo4j import Neo4jGraphRepository

logger = logging.getLogger("noesis.graph.factory")

_repository_instance: BaseGraphRepository = None


def get_graph_repository() -> BaseGraphRepository:
    """Returns the singleton graph repository instance.

    Attempts Neo4j if configured; falls back gracefully to InMemoryGraphRepository
    if Neo4j is unavailable or Docker is not running.
    """
    global _repository_instance
    if _repository_instance is not None:
        return _repository_instance

    mode = settings.GRAPH_STORAGE_MODE.lower()

    if mode == "neo4j":
        logger.info("Attempting Neo4j connection at %s...", settings.NEO4J_URI)
        try:
            repo = Neo4jGraphRepository(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
            )
            if repo.is_healthy():
                logger.info("Using Neo4j persistent graph repository.")
                _repository_instance = repo
                return _repository_instance
            else:
                logger.warning(
                    "Neo4j is not reachable at %s. Falling back to InMemoryGraphRepository.",
                    settings.NEO4J_URI,
                )
        except Exception as e:
            logger.warning(
                "Failed to initialize Neo4j repository (%s). Falling back to InMemoryGraphRepository.",
                str(e),
            )

    logger.info("Active storage mode: InMemoryGraphRepository (native traversal engine).")
    _repository_instance = InMemoryGraphRepository()
    return _repository_instance


def set_graph_repository(repo: BaseGraphRepository) -> None:
    """Explicitly sets the graph repository instance (primarily for tests)."""
    global _repository_instance
    _repository_instance = repo
