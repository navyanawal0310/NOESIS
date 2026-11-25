"""Base Interface for Evaluation Baselines and Systems."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BaselineExecutionResult:
    """Standardized output container for any evaluated architecture."""

    system_name: str
    case_id: Optional[str] = None
    question: str = ""
    answer_entities: List[str] = field(default_factory=list)
    reasoning_paths: List[List[str]] = field(default_factory=list)
    predicates: List[str] = field(default_factory=list)
    directions: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    contradiction_detected: bool = False
    abstained: bool = False
    latency_ms: float = 0.0
    graph_traversal_ms: float = 0.0
    planning_ms: float = 0.0
    llm_calls: int = 0
    raw_response: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "case_id": self.case_id,
            "question": self.question,
            "answer_entities": self.answer_entities,
            "reasoning_paths": self.reasoning_paths,
            "predicates": self.predicates,
            "directions": self.directions,
            "citations": self.citations,
            "contradiction_detected": self.contradiction_detected,
            "abstained": self.abstained,
            "latency_ms": round(self.latency_ms, 2),
            "graph_traversal_ms": round(self.graph_traversal_ms, 2),
            "planning_ms": round(self.planning_ms, 2),
            "llm_calls": self.llm_calls,
            "raw_response": self.raw_response,
            "metadata": self.metadata,
        }


class BaseReasoningSystem(ABC):
    """Abstract interface for all reasoning systems under evaluation."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(
        self,
        question: str,
        case_id: Optional[str] = None,
        structured_plan: Optional[Dict[str, Any]] = None,
        mode: str = "structured",
        **kwargs: Any,
    ) -> BaselineExecutionResult:
        """Execute evaluation query.

        mode: 'structured' (Oracle Graph Execution) or 'natural' (Natural-Language Query Compilation).
        """
        pass
