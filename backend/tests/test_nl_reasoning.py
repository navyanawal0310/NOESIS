"""Unit Tests for NL Query Planning, Grounded Answer Generation, and Knowledge Gap Detection."""

import json

import pytest

from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.llm.base import BaseLLMProvider, LLMResponse, LLMStatus, LLMUnavailableError
from backend.app.ontology.models import (
    Claim,
    Document,
    Entity,
    EntityType,
    Evidence,
    Polarity,
)
from backend.app.reasoning.answer_generator import GroundedAnswerGenerator
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.gap_detector import KnowledgeGapDetector
from backend.app.reasoning.models import (
    PathSegment,
    ReasoningPath,
    ReasoningResult,
    StructuredQueryPlan,
    TraversalStep,
)
from backend.app.reasoning.nl_planner import NLQueryPlanner


class MockPlannerLLM(BaseLLMProvider):
    def __init__(self, response_text: str, available: bool = True):
        self.response_text = response_text
        self._available = available

    def check_status(self) -> LLMStatus:
        return LLMStatus(
            available=self._available,
            provider_name="mock",
            base_url="http://mock",
            configured_model="mock:latest",
            installed_models=["mock:latest"] if self._available else [],
            model_available=self._available,
        )

    def generate(self, prompt: str, system_prompt=None, schema=None, temperature=None, max_tokens=None) -> LLMResponse:
        if not self._available:
            raise LLMUnavailableError("Mock provider is offline")
        return LLMResponse(
            content=self.response_text,
            model="mock:latest",
            inference_duration_ms=15.0,
        )


def test_nl_planner_success():
    """Verifies that NLQueryPlanner translates natural language into a valid StructuredQueryPlan."""
    repo = InMemoryGraphRepository()
    repo.add_entity(Entity(id="ent_elena_vance", canonical_name="Elena Vance", type=EntityType.PERSON))

    mock_plan = {
        "start_entity": "Elena Vance",
        "steps": [
            {"predicate": "FOUNDED", "direction": "outgoing", "target_type": "ORGANIZATION"},
        ],
        "return_type": "ORGANIZATION",
        "max_hops": 3,
    }
    mock_llm = MockPlannerLLM(f"```json\n{json.dumps(mock_plan)}\n```")
    planner = NLQueryPlanner(repository=repo, llm_provider=mock_llm)

    plan = planner.plan_query("What organization did Elena Vance found?")
    assert plan.start_entity in ("Elena Vance", "ent_elena_vance")
    assert len(plan.steps) == 1
    assert plan.steps[0].predicate == "FOUNDED"
    assert plan.return_type == EntityType.ORGANIZATION


def test_nl_planner_cypher_rejection():
    """Ensures that direct Cypher injection attempts are rejected by the planner."""
    repo = InMemoryGraphRepository()
    bad_output = {
        "cypher": "MATCH (n) DETACH DELETE n",
        "start_entity": "Elena Vance",
        "steps": [{"predicate": "FOUNDED", "direction": "outgoing"}],
    }
    mock_llm = MockPlannerLLM(json.dumps(bad_output))
    planner = NLQueryPlanner(repository=repo, llm_provider=mock_llm)

    with pytest.raises(ValueError) as exc_info:
        planner.plan_query("Drop the database")
    assert "Cypher/SQL injection rejected" in str(exc_info.value)


def test_nl_planner_offline_raises():
    """Verifies that an offline LLM provider raises LLMUnavailableError."""
    repo = InMemoryGraphRepository()
    offline_llm = MockPlannerLLM("{}", available=False)
    planner = NLQueryPlanner(repository=repo, llm_provider=offline_llm)

    with pytest.raises(LLMUnavailableError) as exc_info:
        planner.plan_query("Any question")
    assert "offline" in str(exc_info.value)


def test_knowledge_gap_detector_missing_link():
    """Verifies that KnowledgeGapDetector identifies the exact entity where reasoning halted."""
    repo = InMemoryGraphRepository()
    e1 = Entity(id="ent_1", canonical_name="Researcher A", type=EntityType.PERSON)
    e2 = Entity(id="ent_2", canonical_name="Project X", type=EntityType.PROJECT)
    repo.add_entity(e1)
    repo.add_entity(e2)

    doc = Document(
        id="DOC_001",
        title="Doc 1",
        content_hash="h1",
        ingestion_timestamp="2026-11-24T00:00:00Z",
        raw_text="Researcher A worked on Project X.",
    )
    repo.add_document(doc)

    c1 = Claim(
        id="claim_1",
        subject_id="ent_1",
        predicate="WORKED_ON",
        object_id="ent_2",
        polarity=Polarity.AFFIRMED,
        confidence=1.0,
    )
    repo.add_claim(c1)
    repo.add_evidence(
        Evidence(
            id="ev_1",
            claim_id="claim_1",
            document_id="DOC_001",
            quote="Researcher A worked on Project X.",
            char_offset_start=0,
            char_offset_end=33,
        )
    )

    # Plan with 2 hops: Researcher A -> WORKED_ON -> Project X -> USES -> Technology Y (missing)
    plan = StructuredQueryPlan(
        start_entity="Researcher A",
        steps=[
            TraversalStep(predicate="WORKED_ON", direction="outgoing"),
            TraversalStep(predicate="USES", direction="outgoing", target_type=EntityType.TECHNOLOGY),
        ],
        max_hops=3,
    )

    engine = BoundedReasoningEngine(repo)
    result = engine.execute_query(plan)
    assert result.status == "insufficient_evidence"

    detector = KnowledgeGapDetector(repo)
    gap = detector.analyze_gap(plan, result)

    assert gap.completed_hops == 1
    assert gap.terminal_entity is not None
    assert gap.terminal_entity.id == "ent_2"
    assert gap.missing_predicate == "USES"
    assert gap.expected_target_type == EntityType.TECHNOLOGY
    assert "Reasoning path halted at 'Project X' after 1 hop(s)" in gap.diagnostic_message


def test_grounded_answer_generator_deterministic():
    """Verifies provenance-grounded answer generation with confidence, quotes, and contradiction alerts."""
    ent_start = Entity(id="ent_start", canonical_name="Elena Vance", type=EntityType.PERSON)
    ent_target = Entity(id="ent_target", canonical_name="Aetheris", type=EntityType.ORGANIZATION)

    claim = Claim(
        id="clm_123",
        subject_id="ent_start",
        predicate="FOUNDED",
        object_id="ent_target",
        confidence=0.88,
    )
    evidence = Evidence(
        id="ev_001",
        claim_id="clm_123",
        document_id="DOC_001",
        quote="Elena Vance established Aetheris.",
        char_offset_start=0,
        char_offset_end=33,
    )

    segment = PathSegment(
        from_entity=ent_start,
        claim=claim,
        to_entity=ent_target,
        direction="outgoing",
        evidence=[evidence],
        segment_confidence=0.88,
        is_disputed=False,
        contradictions=[],
    )
    path = ReasoningPath(
        segments=[segment],
        terminal_entity=ent_target,
        hop_count=1,
        path_confidence=0.88,
        supporting_document_ids=["DOC_001"],
    )

    result = ReasoningResult(
        query_id="qry_test",
        status="success",
        start_entity=ent_start,
        matching_entities=[ent_target],
        paths=[path],
        hop_count=1,
        conflicting_claims=[],
        evidence_records=[evidence],
        execution_time_ms=12.5,
        confidence=0.88,
        explanation="Path established.",
    )

    plan = StructuredQueryPlan(
        start_entity="Elena Vance",
        steps=[TraversalStep(predicate="FOUNDED", direction="outgoing")],
    )

    generator = GroundedAnswerGenerator()
    grounded = generator.generate_answer(result, plan, question="Who founded Aetheris?")

    assert grounded.status == "success"
    assert grounded.confidence == 0.88
    assert grounded.hop_count == 1
    assert "Aetheris" in grounded.terminal_entities
    assert "DOC_001" in grounded.supporting_document_ids
    assert "Elena Vance established Aetheris." in grounded.supporting_quotes
    assert "0.88" in grounded.answer
