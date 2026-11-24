"""Evidence-Centric Ontology Models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Recognized entity categories."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    TECHNOLOGY = "TECHNOLOGY"
    PROJECT = "PROJECT"
    PUBLICATION = "PUBLICATION"
    LOCATION = "LOCATION"
    CONCEPT = "CONCEPT"


class Polarity(str, Enum):
    """Assertion polarity."""

    AFFIRMED = "affirmed"
    NEGATED = "negated"


class Predicate(str, Enum):
    """Canonical relationship predicates."""

    FOUNDED = "FOUNDED"
    WORKED_ON = "WORKED_ON"
    DEVELOPED = "DEVELOPED"
    EMPLOYED_BY = "EMPLOYED_BY"
    COLLABORATED_WITH = "COLLABORATED_WITH"
    AUTHORED = "AUTHORED"
    PUBLISHED = "PUBLISHED"
    ACQUIRED = "ACQUIRED"
    FUNDED = "FUNDED"
    LOCATED_IN = "LOCATED_IN"
    USES = "USES"
    DISPUTES = "DISPUTES"


class Entity(BaseModel):
    """Entity node in knowledge graph."""

    id: str = Field(..., description="Unique canonical identifier (e.g., ent_alyssa_vance)")
    canonical_name: str = Field(..., description="Canonical human-readable name")
    type: EntityType = Field(..., description="Entity classification")
    aliases: List[str] = Field(default_factory=list, description="Known synonyms and aliases")
    description: Optional[str] = Field(default=None, description="Brief description or role")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary attributes")


class Evidence(BaseModel):
    """Evidence record grounding a claim in source text."""

    id: str = Field(..., description="Unique evidence ID (e.g., ev_doc001_01)")
    claim_id: str = Field(..., description="Identifier of the claim this substantiates")
    document_id: str = Field(..., description="Source document ID (e.g., DOC_001)")
    quote: str = Field(..., description="Exact verbatim quotation from the document")
    page: Optional[int] = Field(default=1, description="Page number where quotation appears")
    chunk_id: Optional[str] = Field(default=None, description="Chunk identifier")
    char_offset_start: int = Field(..., ge=0, description="Exact start character offset")
    char_offset_end: int = Field(..., ge=0, description="Exact end character offset")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence quality score")


class Claim(BaseModel):
    """Reified claim node representing a verifiable factual assertion."""

    id: str = Field(..., description="Deterministic SHA-256 fingerprint ID")
    subject_id: str = Field(..., description="Subject Entity ID")
    predicate: str = Field(..., description="Predicate relationship name")
    object_id: str = Field(..., description="Object Entity ID")
    polarity: Polarity = Field(default=Polarity.AFFIRMED, description="Assertion polarity")
    temporal_scope: Optional[str] = Field(default=None, description="Time validity range (e.g., 2021-2023)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Calculated confidence score")
    evidence_ids: List[str] = Field(default_factory=list, description="Associated evidence IDs")
    contradiction_ids: List[str] = Field(default_factory=list, description="IDs of contradicting claims")


class Document(BaseModel):
    """Source document node."""

    id: str = Field(..., description="Unique document identifier (e.g., DOC_001)")
    title: str = Field(..., description="Document title")
    source_type: str = Field(default="synthetic", description="Document type (txt, pdf, synthetic)")
    publication_date: Optional[str] = Field(default=None, description="ISO publication date")
    source_uri: Optional[str] = Field(default=None, description="Source URI or file path")
    content_hash: str = Field(..., description="SHA-256 hash of raw_text")
    ingestion_timestamp: str = Field(..., description="ISO timestamp of ingestion")
    raw_text: str = Field(..., description="Complete source text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
