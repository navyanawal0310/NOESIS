"""Reasoning Engine Data Models and Structured Query Plans."""

from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.ontology.models import Claim, Entity, EntityType, Evidence


class TraversalStep(BaseModel):
    """A single step in a multi-hop traversal plan."""

    predicate: str = Field(..., description="Predicate relationship name to traverse")
    direction: str = Field(
        default="outgoing",
        description="Direction: 'outgoing' (from subject), 'incoming' (from object), or 'both'",
    )
    target_type: Optional[EntityType] = Field(
        default=None,
        description="Optional entity type constraint for the step target",
    )


class StructuredQueryPlan(BaseModel):
    """Declarative, bounded query plan for multi-hop graph reasoning."""

    start_entity: str = Field(..., description="Starting entity ID or canonical name")
    steps: List[TraversalStep] = Field(..., min_length=1, max_length=5, description="1 to 5 traversal steps")
    return_type: Optional[EntityType] = Field(default=None, description="Expected terminal entity type")
    predicate_filter: Optional[str] = Field(default=None, description="Optional global predicate filter")
    max_hops: int = Field(default=3, ge=1, le=5, description="Maximum hop limit")
    excluded_document_ids: List[str] = Field(
        default_factory=list,
        description="List of document IDs to ablate/exclude for counterfactual testing",
    )
    temporal_constraint: Optional[str] = Field(
        default=None,
        description="Optional temporal constraint (e.g., '1995', '2021-2023')",
    )
    unsupported_constraints: List[str] = Field(
        default_factory=list,
        description="List of user constraints requested in natural language that cannot be represented in the query",
    )


class PathSegment(BaseModel):
    """An individual hop segment within a multi-hop reasoning path."""

    from_entity: Entity
    claim: Claim
    to_entity: Entity
    direction: str
    evidence: List[Evidence]
    segment_confidence: float
    is_disputed: bool = False
    contradictions: List[Claim] = Field(default_factory=list)


class ReasoningPath(BaseModel):
    """A complete multi-hop reasoning path from start entity to target."""

    segments: List[PathSegment]
    terminal_entity: Entity
    hop_count: int
    path_confidence: float
    supporting_document_ids: List[str]


class ReasoningResult(BaseModel):
    """Comprehensive output of the multi-hop reasoning engine."""

    query_id: str
    status: str = Field(..., description="'success', 'insufficient_evidence', or 'contradiction_detected'")
    start_entity: Optional[Entity] = None
    matching_entities: List[Entity] = Field(default_factory=list)
    paths: List[ReasoningPath] = Field(default_factory=list)
    hop_count: int = 0
    conflicting_claims: List[Claim] = Field(default_factory=list)
    evidence_records: List[Evidence] = Field(default_factory=list)
    execution_time_ms: float
    confidence: float = 0.0
    robustness_score: Optional[float] = None
    critical_documents: List[str] = Field(default_factory=list)
    explanation: str
