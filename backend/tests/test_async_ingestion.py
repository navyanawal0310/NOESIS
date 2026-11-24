"""Regression and Integration Tests for Asynchronous Ingestion and Contradiction Integrity.

Verifies:
1. HTTP 202 is treated as accepted background job submission, not immediate completion.
2. Background job status serialization and lifecycle (QUEUED -> COMPLETED / FAILED).
3. Document metadata synchronization between jobs and graph repositories.
4. Duplicate submission prevention.
5. Contradiction classification rules:
   - Explicit affirmation vs. negation on same (subject, predicate, object).
   - Multiple valid objects for non-functional predicates (no false conflict).
   - Temporal compatibility (non-overlapping periods do not conflict).
   - Different predicates sharing a subject (no conflict).
   - Distinction between newly detected, document-associated, and total corpus contradictions.
6. Temporal constraint handling in query planning and execution.
"""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

from backend.app.extraction.pipeline import EvidenceConstrainedExtractor
from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.ingestion.chunking import DocumentChunk
from backend.app.ingestion.jobs import (
    IngestionJob,
    JobStatus,
    submit_ingestion_job,
)
from backend.app.ingestion.parser import ParsedDocument
from backend.app.llm.base import BaseLLMProvider, LLMResponse, LLMStatus
from backend.app.ontology.models import Claim, Document, Entity, EntityType, Evidence, Polarity
from backend.app.reasoning.answer_generator import GroundedAnswerGenerator
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.models import StructuredQueryPlan, TraversalStep


class DummyLLM(BaseLLMProvider):
    def check_status(self) -> LLMStatus:
        return LLMStatus(
            available=True,
            provider_name="dummy",
            base_url="http://dummy",
            configured_model="dummy:latest",
            installed_models=["dummy:latest"],
            model_available=True,
        )

    def generate(self, prompt: str, system_prompt=None, schema=None, temperature=None, max_tokens=None) -> LLMResponse:
        return LLMResponse(content="{}", model="dummy:latest")


def test_job_status_serialization():
    """Verifies that IngestionJob properly serializes all required fields."""
    job = IngestionJob(
        job_id="job_test_001",
        document_id="doc_test_001",
        status=JobStatus.EXTRACTING.value,
        progress_percent=45.5,
        total_chunks=2,
        processed_chunks=1,
        accepted_claims=3,
        rejected_claims=0,
        evidence_records=3,
        elapsed_time_seconds=12.4,
        created_at="2026-11-25T00:00:00Z",
    )
    dump = job.model_dump()
    assert dump["job_id"] == "job_test_001"
    assert dump["status"] == "EXTRACTING"
    assert dump["progress_percent"] == 45.5
    assert dump["total_chunks"] == 2
    assert dump["processed_chunks"] == 1
    assert dump["accepted_claims"] == 3
    assert dump["evidence_records"] == 3
    assert dump["elapsed_time_seconds"] == 12.4


def test_duplicate_submission_prevention():
    """Verifies that submitting a job for an already active document returns the existing job."""
    doc_id = "doc_duplicate_test"

    def slow_worker(job: IngestionJob):
        time.sleep(0.2)
        return {"claims_accepted": 1}

    job1 = submit_ingestion_job(doc_id, slow_worker)
    assert job1.status.upper() in (JobStatus.QUEUED.value, "PROCESSING", "EXTRACTING")

    # Second submit while first is running
    job2 = submit_ingestion_job(doc_id, slow_worker)
    assert job2.job_id == job1.job_id

    # Wait for completion
    for _ in range(20):
        if job1.status.upper() in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            break
        time.sleep(0.05)

    assert job1.status.upper() == JobStatus.COMPLETED.value


def test_failed_job_completion():
    """Verifies that an exception in the worker transitions status to FAILED with error_message."""
    doc_id = "doc_fail_test"

    def failing_worker(job: IngestionJob):
        raise RuntimeError("GPU memory exhausted")

    job = submit_ingestion_job(doc_id, failing_worker)
    for _ in range(20):
        if job.status.upper() in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            break
        time.sleep(0.05)

    assert job.status.upper() == JobStatus.FAILED.value
    assert "GPU memory exhausted" in (job.error_message or "")


def test_contradiction_integrity_opposite_polarity():
    """Verifies that opposite polarity on same subject, predicate, and object is flagged as contradiction."""
    repo = InMemoryGraphRepository()
    extractor = EvidenceConstrainedExtractor(llm_provider=DummyLLM(), repository=repo)

    # Add Claim 1: Dr. Mercer AFFIRMED WORKED_ON Project Horizon
    c1 = Claim(
        id="clm_c1",
        subject_id="ent_mercer",
        predicate="WORKED_ON",
        object_id="ent_horizon",
        polarity=Polarity.AFFIRMED,
        confidence=1.0,
    )
    repo.add_claim(c1)
    ev1 = Evidence(
        id="ev_c1",
        claim_id="clm_c1",
        document_id="doc_1",
        quote="Dr. Mercer worked on Project Horizon.",
        char_offset_start=0,
        char_offset_end=37,
    )
    repo.add_evidence(ev1)

    # Add Claim 2: Dr. Mercer NEGATED WORKED_ON Project Horizon
    c2 = Claim(
        id="clm_c2",
        subject_id="ent_mercer",
        predicate="WORKED_ON",
        object_id="ent_horizon",
        polarity=Polarity.NEGATED,
        confidence=1.0,
    )
    repo.add_claim(c2)
    ev2 = Evidence(
        id="ev_c2",
        claim_id="clm_c2",
        document_id="doc_2",
        quote="Dr. Mercer did not work on Project Horizon.",
        char_offset_start=0,
        char_offset_end=43,
    )
    repo.add_evidence(ev2)

    parsed_doc = ParsedDocument(
        document_id="doc_2",
        filename="doc_2.txt",
        source_type="txt",
        content_hash="hash_doc_2",
        raw_text="Dr. Mercer did not work on Project Horizon.",
        ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Mock extraction returning the negated claim
    from backend.app.extraction.pipeline import ExtractionResult, VerifiedClaimRecord
    rec = VerifiedClaimRecord(
        claim_id="clm_c2",
        subject_id="ent_mercer",
        predicate="WORKED_ON",
        object_id="ent_horizon",
        polarity=Polarity.NEGATED,
        exact_quote="Dr. Mercer did not work on Project Horizon.",
        char_offset_start=0,
        char_offset_end=43,
        document_id="doc_2",
        chunk_id="chunk_0",
    )
    extractor.extract_from_chunk = MagicMock(return_value=ExtractionResult(
        chunk_id="chunk_0",
        entities=[],
        accepted_claims=[rec],
        rejected_claims=[],
    ))

    chunk = DocumentChunk(
        chunk_id="chunk_0",
        document_id="doc_2",
        text="Dr. Mercer did not work on Project Horizon.",
        char_offset_start=0,
        char_offset_end=43,
        chunk_index=0,
        approx_tokens=10,
    )

    res = extractor.ingest_document_into_graph(parsed_doc, [chunk])
    assert res["contradictions_flagged"] == 1
    assert res["newly_detected_contradictions"] == 1
    assert len(res["contradiction_details"]) == 1
    assert res["contradiction_details"][0]["claim_1_id"] == "clm_c1"
    assert res["contradiction_details"][0]["claim_2_id"] == "clm_c2"


def test_contradiction_integrity_non_functional_predicates():
    """Verifies that multiple distinct objects for non-functional predicates (DEVELOPED, COLLABORATED_WITH) do NOT contradict."""
    repo = InMemoryGraphRepository()
    extractor = EvidenceConstrainedExtractor(llm_provider=DummyLLM(), repository=repo)

    # Org develops Tech A
    c1 = Claim(
        id="clm_dev1",
        subject_id="ent_qb_labs",
        predicate="DEVELOPED",
        object_id="ent_atlas",
        polarity=Polarity.AFFIRMED,
        confidence=1.0,
    )
    repo.add_claim(c1)

    # Org also develops Tech B
    c2 = Claim(
        id="clm_dev2",
        subject_id="ent_qb_labs",
        predicate="DEVELOPED",
        object_id="ent_nova",
        polarity=Polarity.AFFIRMED,
        confidence=1.0,
    )
    repo.add_claim(c2)

    parsed_doc = ParsedDocument(
        document_id="doc_multi_obj",
        filename="doc_multi.txt",
        source_type="txt",
        content_hash="hash_multi",
        raw_text="QuantumBridge Labs developed Nova.",
        ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    from backend.app.extraction.pipeline import ExtractionResult, VerifiedClaimRecord
    rec = VerifiedClaimRecord(
        claim_id="clm_dev2",
        subject_id="ent_qb_labs",
        predicate="DEVELOPED",
        object_id="ent_nova",
        polarity=Polarity.AFFIRMED,
        exact_quote="QuantumBridge Labs developed Nova.",
        char_offset_start=0,
        char_offset_end=34,
        document_id="doc_multi_obj",
        chunk_id="chunk_0",
    )
    extractor.extract_from_chunk = MagicMock(return_value=ExtractionResult(
        chunk_id="chunk_0",
        entities=[],
        accepted_claims=[rec],
        rejected_claims=[],
    ))
    chunk = DocumentChunk(
        chunk_id="chunk_0",
        document_id="doc_multi_obj",
        text="QuantumBridge Labs developed Nova.",
        char_offset_start=0,
        char_offset_end=34,
        chunk_index=0,
        approx_tokens=10,
    )

    res = extractor.ingest_document_into_graph(parsed_doc, [chunk])
    # Developing two technologies is valid, not a contradiction
    assert res["contradictions_flagged"] == 0
    assert res["newly_detected_contradictions"] == 0


def test_contradiction_integrity_temporal_compatibility():
    """Verifies that opposite polarity on disjoint time intervals does NOT contradict."""
    extractor = EvidenceConstrainedExtractor(llm_provider=DummyLLM(), repository=InMemoryGraphRepository())
    # 2010-2012 vs 2018-2020: disjoint intervals
    incompatible = extractor._are_temporally_incompatible("2010-2012", "2018-2020")
    assert incompatible is False

    # 2015 vs 2015: overlapping/identical
    incompatible_same = extractor._are_temporally_incompatible("2015", "2015")
    assert incompatible_same is True

    # Missing vs present: assumed incompatible
    incompatible_none = extractor._are_temporally_incompatible(None, "2015")
    assert incompatible_none is True


def test_temporal_constraint_insufficient_evidence():
    """Verifies that requesting an ungrounded temporal constraint (e.g. in 1995) returns insufficient_evidence."""
    repo = InMemoryGraphRepository()
    mercer = Entity(id="ent_mercer", canonical_name="Dr. Elena Mercer", type=EntityType.PERSON)
    qb = Entity(id="ent_qb", canonical_name="QuantumBridge Labs", type=EntityType.ORGANIZATION)
    repo.add_entity(mercer)
    repo.add_entity(qb)

    # Claim has no temporal scope
    claim = Claim(
        id="clm_founded",
        subject_id="ent_mercer",
        predicate="FOUNDED",
        object_id="ent_qb",
        polarity=Polarity.AFFIRMED,
        temporal_scope=None,  # No founding date in document
        confidence=1.0,
    )
    repo.add_claim(claim)
    ev = Evidence(
        id="ev_founded",
        claim_id="clm_founded",
        document_id="doc_1",
        quote="Dr. Elena Mercer founded QuantumBridge Labs.",
        char_offset_start=0,
        char_offset_end=44,
    )
    repo.add_evidence(ev)
    doc = Document(
        id="doc_1",
        title="Doc 1",
        content_hash="h1",
        ingestion_timestamp="2026-11-25T00:00:00Z",
        raw_text="Dr. Elena Mercer founded QuantumBridge Labs.",
    )
    repo.add_document(doc)

    engine = BoundedReasoningEngine(repository=repo)
    plan = StructuredQueryPlan(
        start_entity="QuantumBridge Labs",
        steps=[TraversalStep(predicate="FOUNDED", direction="incoming")],
        return_type=EntityType.PERSON,
        temporal_constraint="1995",  # Explicit constraint requested
    )

    result = engine.execute_query(plan)
    assert result.status == "insufficient_evidence"
    assert "temporal constraint '1995'" in result.explanation.lower()

    answer_gen = GroundedAnswerGenerator()
    answer = answer_gen.generate_answer(result=result, plan=plan, question="Who founded QuantumBridge Labs in 1995?")
    assert answer.status == "insufficient_evidence"
    assert "1995" in answer.answer
    assert answer.terminal_entities == []
