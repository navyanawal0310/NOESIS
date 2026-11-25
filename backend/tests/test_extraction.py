"""Unit Tests for Schema Validation, Entity Resolution, Extraction Cache, and Evidence Constraints."""

import json

from backend.app.extraction.cache import ExtractionCache
from backend.app.extraction.pipeline import EvidenceConstrainedExtractor
from backend.app.extraction.resolution import EntityResolver
from backend.app.extraction.schema import (
    ExtractedClaim,
    ExtractedEntity,
    ExtractionOutput,
)
from backend.app.extraction.validator import validate_evidence_quotation
from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.ingestion.chunking import DocumentChunk
from backend.app.ingestion.parser import ParsedDocument
from backend.app.llm.base import BaseLLMProvider, LLMResponse, LLMStatus
from backend.app.ontology.models import Entity, EntityType, Polarity


def test_extraction_schema_validation():
    """Verifies that Pydantic models validate extracted entities and claims strictly."""
    ent = ExtractedEntity(
        canonical_name="Elena Vance",
        entity_type=EntityType.PERSON,
        aliases=["E. Vance", "Dr. Vance"],
    )
    assert ent.canonical_name == "Elena Vance"
    assert ent.entity_type == EntityType.PERSON

    claim = ExtractedClaim(
        subject_name="Elena Vance",
        predicate="FOUNDED",
        object_name="Aetheris",
        polarity=Polarity.AFFIRMED,
        temporal_scope="2021",
        exact_quote="Elena Vance founded Aetheris in 2021.",
    )
    assert claim.predicate == "FOUNDED"
    assert claim.polarity == Polarity.AFFIRMED

    output = ExtractionOutput(entities=[ent], claims=[claim])
    assert len(output.entities) == 1
    assert len(output.claims) == 1


def test_quotation_exact_validation():
    """Verifies that the validator accepts exact matches and rejects mismatches or fabrications."""
    source_text = "In 2021, Dr. Elena Vance established the Aetheris consortium in Geneva."

    # Exact valid match
    quote = "Dr. Elena Vance established the Aetheris consortium"
    start = source_text.index(quote)
    end = start + len(quote)
    v_ok = validate_evidence_quotation(source_text, quote, start, end)
    assert v_ok.is_valid is True
    assert "disclaimer" in v_ok.to_dict()

    # Hallucinated quote
    fake_quote = "Dr. Elena Vance did not establish the consortium"
    v_bad = validate_evidence_quotation(source_text, fake_quote, 0, len(fake_quote))
    assert v_bad.is_valid is False
    assert not v_bad.is_valid


def test_entity_resolution_deterministic():
    """Tests case and whitespace normalization, alias matching, and prevention of unwarranted fuzzy merging."""
    canonical_ent = Entity(
        id="ent_elena_vance",
        canonical_name="Dr. Elena Vance",
        type=EntityType.PERSON,
        aliases=["Elena Vance", "E. Vance"],
    )
    resolver = EntityResolver([canonical_ent])

    # Exact match
    r1 = resolver.resolve("Dr. Elena Vance", EntityType.PERSON)
    assert r1.entity_id == "ent_elena_vance"
    assert r1.is_new is False

    # Whitespace and case normalization
    r2 = resolver.resolve("   dr.   elena   vance   ", EntityType.PERSON)
    assert r2.entity_id == "ent_elena_vance"
    assert r2.is_new is False

    # Explicit alias match
    r3 = resolver.resolve("E. Vance", EntityType.PERSON)
    assert r3.entity_id == "ent_elena_vance"
    assert r3.is_new is False

    # Distinct entity must NOT be fuzzy-merged
    r4 = resolver.resolve("Alyssa Vance", EntityType.PERSON)
    assert r4.entity_id != "ent_elena_vance"
    assert r4.is_new is True


def test_extraction_cache_operations(tmp_path):
    """Verifies persistent chunk extraction caching and invalidation on model or prompt change."""
    cache = ExtractionCache(cache_dir=str(tmp_path / "cache"))
    chunk_text = "Elena Vance founded Aetheris."
    model = "qwen3:4b"

    assert cache.get(chunk_text, model) is None

    payload = {"entities": [], "claims": [], "model": model}
    cache.set(chunk_text, model, payload)

    cached = cache.get(chunk_text, model)
    assert cached is not None
    assert cached["model"] == model

    # Different model -> Cache Miss
    assert cache.get(chunk_text, "llama3:8b") is None


class MockLLM(BaseLLMProvider):
    def __init__(self, response_text: str):
        self.response_text = response_text

    def check_status(self) -> LLMStatus:
        return LLMStatus(
            available=True,
            provider_name="mock",
            base_url="http://mock",
            configured_model="mock:latest",
            installed_models=["mock:latest"],
            model_available=True,
        )

    def generate(self, prompt: str, system_prompt=None, schema=None, temperature=None, max_tokens=None) -> LLMResponse:
        return LLMResponse(
            content=self.response_text,
            model="mock:latest",
            inference_duration_ms=10.0,
        )


def test_evidence_constrained_extraction_pipeline():
    """Verifies that evidence-constrained extractor accepts verified quotes and rejects fabrications."""
    repo = InMemoryGraphRepository()

    text = "In 2021, Dr. Elena Vance founded Aetheris in Geneva. She developed the NOESIS protocol."
    parsed_doc = ParsedDocument(
        document_id="doc_test_pipe",
        filename="test_pipe.txt",
        source_type="txt",
        content_hash="hash_123",
        raw_text=text,
        total_pages=1,
        total_chars=len(text),
        ingestion_timestamp="2026-11-24T00:00:00Z",
    )

    chunk = DocumentChunk(
        chunk_id="chk_001",
        document_id="doc_test_pipe",
        chunk_index=0,
        text=text,
        char_offset_start=0,
        char_offset_end=len(text),
        page_start=1,
        page_end=1,
        approx_tokens=len(text) // 4,
    )

    llm_output = {
        "entities": [
            {"canonical_name": "Elena Vance", "entity_type": "PERSON", "aliases": ["Dr. Elena Vance"]},
            {"canonical_name": "Aetheris", "entity_type": "ORGANIZATION", "aliases": []},
        ],
        "claims": [
            {
                # Valid claim with verbatim quote
                "subject_name": "Elena Vance",
                "predicate": "FOUNDED",
                "object_name": "Aetheris",
                "polarity": "affirmed",
                "temporal_scope": "2021",
                "exact_quote": "Dr. Elena Vance founded Aetheris in Geneva.",
            },
            {
                # Fabricated claim with quote that does not appear in text
                "subject_name": "Elena Vance",
                "predicate": "DISPUTES",
                "object_name": "Aetheris",
                "polarity": "negated",
                "temporal_scope": None,
                "exact_quote": "Elena Vance completely rejected the Aetheris consortium.",
            },
        ],
    }

    mock_llm = MockLLM(json.dumps(llm_output))
    extractor = EvidenceConstrainedExtractor(llm_provider=mock_llm, repository=repo)

    result = extractor.ingest_document_into_graph(parsed_doc, [chunk])

    # Claim 1 accepted
    assert result["claims_accepted"] == 1
    # Claim 2 rejected due to quote non-presence
    assert result["claims_rejected"] == 1
    assert "not found verbatim in chunk text" in result["rejected_details"][0]["reason"]

    # Verify claim in repository
    claims = repo.list_claims()
    assert len(claims) == 1
    assert claims[0].predicate == "FOUNDED"

    # Verify evidence linked in repository
    evidence = repo.get_evidence_for_claim(claims[0].id)
    assert len(evidence) == 1
    assert evidence[0].quote == "Dr. Elena Vance founded Aetheris in Geneva."
    assert text[evidence[0].char_offset_start:evidence[0].char_offset_end] == evidence[0].quote
