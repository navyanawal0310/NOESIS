"""Extraction Schema and Models for Evidence-Constrained Claim Ingestion."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.ontology.models import EntityType, Polarity


class ExtractedEntity(BaseModel):
    """Raw entity identified in document chunk."""

    canonical_name: str = Field(..., description="Canonical or most formal name appearing in text")
    entity_type: EntityType = Field(..., description="Recognized entity classification")
    aliases: List[str] = Field(default_factory=list, description="Direct aliases or synonyms mentioned in chunk")


class ExtractedClaim(BaseModel):
    """Raw factual assertion extracted from document chunk."""

    subject_name: str = Field(..., description="Subject entity name matching an extracted entity")
    predicate: str = Field(..., description="Relationship predicate from ontology")
    object_name: str = Field(..., description="Object entity name matching an extracted entity")
    polarity: Polarity = Field(default=Polarity.AFFIRMED, description="affirmed or negated assertion")
    temporal_scope: Optional[str] = Field(default=None, description="Explicit date or range (e.g. '2022')")
    exact_quote: str = Field(..., description="Exact verbatim substring from the chunk supporting this fact")


class ExtractionOutput(BaseModel):
    """Structured LLM extraction response conforming to schema."""

    entities: List[ExtractedEntity] = Field(default_factory=list)
    claims: List[ExtractedClaim] = Field(default_factory=list)


class VerifiedClaimRecord(BaseModel):
    """Claim that has undergone lexical verification and entity resolution."""

    claim_id: str
    subject_id: str
    predicate: str
    object_id: str
    polarity: Polarity
    temporal_scope: Optional[str] = None
    exact_quote: str
    document_id: str
    chunk_id: str
    char_offset_start: int
    char_offset_end: int
    page: int
    is_lexically_verified: bool
    review_status: str = Field(default="accepted", description="'accepted', 'unverified', or 'rejected'")
    rejection_reason: Optional[str] = None


class ExtractionResult(BaseModel):
    """Complete outcome of chunk or document extraction."""

    model_config = ConfigDict(protected_namespaces=())

    document_id: str
    total_extracted_claims: int
    accepted_claims: List[VerifiedClaimRecord]
    rejected_claims: List[Dict[str, Any]]
    resolved_entities: List[Dict[str, Any]]
    ambiguous_entities: List[Dict[str, Any]]
    model_used: str
    inference_duration_ms: float
    from_cache: bool = False
