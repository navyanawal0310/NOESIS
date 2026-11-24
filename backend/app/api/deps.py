"""Dependency Injection Providers for NOESIS FastAPI Backend."""

from fastapi import Depends

from backend.app.extraction.pipeline import EvidenceConstrainedExtractor
from backend.app.graph.base import BaseGraphRepository
from backend.app.graph.factory import get_graph_repository
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.factory import get_llm_provider
from backend.app.reasoning.answer_generator import GroundedAnswerGenerator
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.gap_detector import KnowledgeGapDetector
from backend.app.reasoning.nl_planner import NLQueryPlanner


def get_repository() -> BaseGraphRepository:
    """Provides the active graph repository singleton."""
    return get_graph_repository()


def get_reasoning_engine(
    repo: BaseGraphRepository = Depends(get_repository),
) -> BoundedReasoningEngine:
    """Provides a BoundedReasoningEngine instance configured with the active repository."""
    return BoundedReasoningEngine(repository=repo)


def get_llm() -> BaseLLMProvider:
    """Provides the active local LLM provider singleton."""
    return get_llm_provider()


def get_gap_detector(
    repo: BaseGraphRepository = Depends(get_repository),
) -> KnowledgeGapDetector:
    """Provides a KnowledgeGapDetector instance."""
    return KnowledgeGapDetector(repository=repo)


def get_query_planner(
    repo: BaseGraphRepository = Depends(get_repository),
    llm: BaseLLMProvider = Depends(get_llm),
) -> NLQueryPlanner:
    """Provides an NLQueryPlanner configured with the graph repo and local LLM."""
    return NLQueryPlanner(repository=repo, llm_provider=llm)


def get_answer_generator(
    llm: BaseLLMProvider = Depends(get_llm),
) -> GroundedAnswerGenerator:
    """Provides a GroundedAnswerGenerator instance."""
    return GroundedAnswerGenerator(llm_provider=llm)


def get_extractor(
    repo: BaseGraphRepository = Depends(get_repository),
    llm: BaseLLMProvider = Depends(get_llm),
) -> EvidenceConstrainedExtractor:
    """Provides an EvidenceConstrainedExtractor configured with repo and local LLM."""
    return EvidenceConstrainedExtractor(llm_provider=llm, repository=repo)
