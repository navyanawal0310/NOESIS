"""Dependency Injection Providers for NOESIS FastAPI Backend."""

from fastapi import Depends

from backend.app.graph.base import BaseGraphRepository
from backend.app.graph.factory import get_graph_repository
from backend.app.reasoning.engine import BoundedReasoningEngine


def get_repository() -> BaseGraphRepository:
    """Provides the active graph repository singleton."""
    return get_graph_repository()


def get_reasoning_engine(
    repo: BaseGraphRepository = Depends(get_repository),
) -> BoundedReasoningEngine:
    """Provides a BoundedReasoningEngine instance configured with the active repository."""
    return BoundedReasoningEngine(repository=repo)
