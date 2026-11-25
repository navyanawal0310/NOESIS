"""Comparative Baseline Architectures for NOESIS Evaluation."""

from evaluation.baselines.base import BaselineExecutionResult, BaseReasoningSystem
from evaluation.baselines.full_noesis import FullNOESISSystem
from evaluation.baselines.noesis_no_eaqc import NOESISWithoutEAQCSystem
from evaluation.baselines.rag import ConventionalRAGSystem
from evaluation.baselines.standard_kg import StandardKGSystem

__all__ = [
    "BaselineExecutionResult",
    "BaseReasoningSystem",
    "FullNOESISSystem",
    "NOESISWithoutEAQCSystem",
    "StandardKGSystem",
    "ConventionalRAGSystem",
]
