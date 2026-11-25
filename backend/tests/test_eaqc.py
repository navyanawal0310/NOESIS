"""Comprehensive Verification Suite for Entity-Anchored Query Compilation (EAQC).

Verifies:
1. Mention resolution 3-tier matching (canonical, normalized, alias).
2. Longest mention prioritization.
3. Ambiguity detection (AMBIGUOUS_ENTITY).
4. Unknown entity detection (ENTITY_NOT_FOUND).
5. Anchor locking against LLM hallucinatory entity substitutions.
6. Context reduction (prompt contains only anchored entity).
7. All 9 test cases specified in Prompt 002.3:
   - Case 1: "Who worked on Project Horizon?"
   - Case 2: "Who founded QuantumBridge Labs?"
   - Case 3: "What technology did QuantumBridge Labs develop?"
   - Case 4: "What technology was developed by the organization founded by the researcher who worked on Project Horizon?"
   - Case 5: "What did Vertex Research develop?"
   - Case 6: "What technology did Project Horizon develop directly?"
   - Case 7: "Who founded QuantumBridge Labs in 1995?"
   - Case 8: "Who worked on a nonexistent project?" / "Who worked on Project Chimera?"
   - Case 9: Paraphrased 3-hop query.
8. Generality with an independent synthetic test document.
"""

import json
from unittest.mock import MagicMock

import pytest

from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.llm.base import BaseLLMProvider, LLMResponse, LLMStatus
from backend.app.ontology.models import Claim, Document, Entity, EntityType, Evidence, Polarity
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.entity_anchor import EntityAnchorResolver
from backend.app.reasoning.gap_detector import KnowledgeGapDetector
from backend.app.reasoning.nl_planner import (
    EntityNotFoundError,
    NLQueryPlanner,
)


class MockLLM(BaseLLMProvider):
    def __init__(self, response_text: str = "{}"):
        self.response_text = response_text
        self.last_prompt = ""

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
        self.last_prompt = prompt
        return LLMResponse(content=self.response_text, model="mock:latest", inference_duration_ms=10.0)


def setup_validation_graph() -> InMemoryGraphRepository:
    """Populates repository with the synthetic validation corpus entities and claims."""
    repo = InMemoryGraphRepository()

    # Entities
    mercer = Entity(
        id="ent_mercer",
        canonical_name="Dr. Elena Mercer",
        type=EntityType.PERSON,
        aliases=["Elena Mercer", "Dr. Mercer", "E. Mercer"],
    )
    horizon = Entity(
        id="ent_project_horizon",
        canonical_name="Project Horizon",
        type=EntityType.PROJECT,
        aliases=["Horizon Project", "Horizon"],
    )
    qb_labs = Entity(
        id="ent_quantumbridge_labs",
        canonical_name="QuantumBridge Labs",
        type=EntityType.ORGANIZATION,
        aliases=["QuantumBridge", "QBL"],
    )
    atlas = Entity(
        id="ent_atlas_reasoning_engine",
        canonical_name="Atlas Reasoning Engine",
        type=EntityType.TECHNOLOGY,
        aliases=["Atlas Engine", "Atlas"],
    )
    vertex = Entity(
        id="ent_vertex_research",
        canonical_name="Vertex Research",
        type=EntityType.ORGANIZATION,
        aliases=["Vertex"],
    )
    nova = Entity(
        id="ent_nova_intelligence_platform",
        canonical_name="Nova Intelligence Platform",
        type=EntityType.TECHNOLOGY,
        aliases=["Nova Platform", "Nova"],
    )

    for e in (mercer, horizon, qb_labs, atlas, vertex, nova):
        repo.add_entity(e)

    # Document
    doc = Document(
        id="doc_val_001",
        title="Synthetic Validation Document",
        source_type="txt",
        content_hash="hash_val_001",
        ingestion_timestamp="2026-11-25T00:00:00Z",
        raw_text=(
            "Dr. Elena Mercer worked on Project Horizon. "
            "Dr. Elena Mercer founded QuantumBridge Labs. "
            "QuantumBridge Labs developed the Atlas Reasoning Engine. "
            "QuantumBridge Labs collaborated with Vertex Research. "
            "Vertex Research developed the Nova Intelligence Platform."
        ),
    )
    repo.add_document(doc)

    # Claims & Evidence
    claims_data = [
        ("clm_1", "ent_mercer", "WORKED_ON", "ent_project_horizon", "Dr. Elena Mercer worked on Project Horizon.", 0, 43),
        ("clm_2", "ent_mercer", "FOUNDED", "ent_quantumbridge_labs", "Dr. Elena Mercer founded QuantumBridge Labs.", 44, 88),
        ("clm_3", "ent_quantumbridge_labs", "DEVELOPED", "ent_atlas_reasoning_engine", "QuantumBridge Labs developed the Atlas Reasoning Engine.", 89, 146),
        ("clm_4", "ent_quantumbridge_labs", "COLLABORATED_WITH", "ent_vertex_research", "QuantumBridge Labs collaborated with Vertex Research.", 147, 201),
        ("clm_5", "ent_vertex_research", "DEVELOPED", "ent_nova_intelligence_platform", "Vertex Research developed the Nova Intelligence Platform.", 202, 261),
    ]

    for cid, s, p, o, quote, start, end in claims_data:
        clm = Claim(
            id=cid,
            subject_id=s,
            predicate=p,
            object_id=o,
            polarity=Polarity.AFFIRMED,
            confidence=1.0,
        )
        repo.add_claim(clm)
        ev = Evidence(
            id=f"ev_{cid}",
            claim_id=cid,
            document_id="doc_val_001",
            quote=quote,
            char_offset_start=start,
            char_offset_end=end,
            confidence=1.0,
        )
        repo.add_evidence(ev)

    return repo


# 1. Mention Resolution Tests
def test_eaqc_mention_resolution_canonical():
    """Verifies tier-1 exact canonical name matching."""
    repo = setup_validation_graph()
    resolver = EntityAnchorResolver(repo)

    res = resolver.resolve("What technology was developed by QuantumBridge Labs?")
    assert res.status == "MATCHED"
    assert res.matched_entity is not None
    assert res.matched_entity.id == "ent_quantumbridge_labs"
    assert res.match_strategy == "canonical"


def test_eaqc_mention_resolution_normalized():
    """Verifies tier-2 normalized name matching (honorific stripping)."""
    repo = setup_validation_graph()
    resolver = EntityAnchorResolver(repo)

    res = resolver.resolve("What did elena mercer do?")
    assert res.status == "MATCHED"
    assert res.matched_entity is not None
    assert res.matched_entity.id == "ent_mercer"
    assert res.match_strategy in ("canonical", "normalized")


def test_eaqc_mention_resolution_alias():
    """Verifies tier-3 alias matching."""
    repo = setup_validation_graph()
    resolver = EntityAnchorResolver(repo)

    res = resolver.resolve("Who developed the Atlas Engine?")
    assert res.status == "MATCHED"
    assert res.matched_entity is not None
    assert res.matched_entity.id == "ent_atlas_reasoning_engine"
    assert res.match_strategy == "alias"


def test_eaqc_longest_mention_priority():
    """Verifies that longer matching entity spans take precedence."""
    repo = setup_validation_graph()
    # Add a shorter entity "Horizon"
    shorter = Entity(id="ent_horizon_short", canonical_name="Horizon", type=EntityType.CONCEPT)
    repo.add_entity(shorter)
    resolver = EntityAnchorResolver(repo)

    res = resolver.resolve("Tell me about Project Horizon")
    assert res.status == "MATCHED"
    assert res.matched_entity.id == "ent_project_horizon"


def test_eaqc_ambiguity_detection():
    """Verifies that tied matches between distinct entities trigger AMBIGUOUS_ENTITY."""
    repo = setup_validation_graph()
    # Add two entities with the same canonical name
    e1 = Entity(id="ent_dup1", canonical_name="OmniCore", type=EntityType.TECHNOLOGY)
    e2 = Entity(id="ent_dup2", canonical_name="OmniCore", type=EntityType.PROJECT)
    repo.add_entity(e1)
    repo.add_entity(e2)

    resolver = EntityAnchorResolver(repo)
    res = resolver.resolve("What is OmniCore?")
    assert res.status == "AMBIGUOUS_ENTITY"
    assert len(res.candidate_entities) == 2


def test_eaqc_entity_not_found_detection():
    """Verifies that queries referencing unindexed named entities trigger ENTITY_NOT_FOUND."""
    repo = setup_validation_graph()
    resolver = EntityAnchorResolver(repo)

    res = resolver.resolve("Who worked on Project Chimera?")
    assert res.status == "ENTITY_NOT_FOUND"
    assert "Project Chimera" in (res.unresolved_mention or "")


# 2. Anchor Locking & Context Reduction Tests
def test_eaqc_anchor_locking_overrides_llm():
    """Verifies that even if LLM substitutes an entity, anchor locking enforces the resolved entity."""
    repo = setup_validation_graph()
    # Mock LLM returns a plan with an unrelated entity "Nexus Advanced Research Institute"
    hallucinated_plan = {
        "start_entity": "Nexus Advanced Research Institute",
        "steps": [
            {"predicate": "WORKED_ON", "direction": "incoming", "target_type": "PERSON"},
        ],
        "return_type": "PERSON",
        "max_hops": 1,
    }
    mock_llm = MockLLM(json.dumps(hallucinated_plan))
    planner = NLQueryPlanner(repo, mock_llm)

    # Disable pattern matching for this unit test to force LLM generation path
    planner._match_relational_patterns = MagicMock(return_value=None)

    plan, status_code, latencies = planner.plan_query_with_telemetry("Who worked on Project Horizon?")
    # Anchor locking MUST override the hallucinated entity
    assert plan.start_entity == "ent_project_horizon"
    assert status_code == "SUCCESS"
    assert "entity_resolution_ms" in latencies
    assert "llm_planning_ms" in latencies


def test_eaqc_context_reduction():
    """Verifies that LLM prompt contains ONLY the anchored entity rather than 25 random corpus entities."""
    repo = setup_validation_graph()
    # Add 10 dummy entities
    for i in range(10):
        repo.add_entity(Entity(id=f"ent_dummy_{i}", canonical_name=f"Dummy Entity {i}", type=EntityType.CONCEPT))

    mock_llm = MockLLM(json.dumps({
        "start_entity": "ent_project_horizon",
        "steps": [{"predicate": "WORKED_ON", "direction": "incoming"}],
        "max_hops": 1,
    }))
    planner = NLQueryPlanner(repo, mock_llm)
    planner._match_relational_patterns = MagicMock(return_value=None)

    planner.plan_query("Who worked on Project Horizon?")
    # Verify that dummy entities are NOT in the LLM prompt
    assert "Dummy Entity 0" not in mock_llm.last_prompt
    assert "Dummy Entity 9" not in mock_llm.last_prompt
    assert "Project Horizon" in mock_llm.last_prompt


# 3. All 9 Regression Test Cases
def test_case_1_who_worked_on_project_horizon():
    """Case 1: 'Who worked on Project Horizon?' -> Dr. Elena Mercer"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)
    plan = planner.plan_query("Who worked on Project Horizon?")
    assert plan.start_entity == "ent_project_horizon"
    assert plan.steps[0].predicate == "WORKED_ON"
    assert plan.steps[0].direction == "incoming"

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "Dr. Elena Mercer"


def test_case_2_who_founded_quantumbridge_labs():
    """Case 2: 'Who founded QuantumBridge Labs?' -> Dr. Elena Mercer"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)

    plan = planner.plan_query("Who founded QuantumBridge Labs?")
    assert plan.start_entity == "ent_quantumbridge_labs"
    assert plan.steps[0].predicate == "FOUNDED"
    assert plan.steps[0].direction == "incoming"

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "Dr. Elena Mercer"


def test_case_3_what_technology_did_quantumbridge_labs_develop():
    """Case 3: 'What technology did QuantumBridge Labs develop?' -> Atlas Reasoning Engine"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)

    plan = planner.plan_query("What technology did QuantumBridge Labs develop?")
    assert plan.start_entity == "ent_quantumbridge_labs"
    assert plan.steps[0].predicate == "DEVELOPED"
    assert plan.steps[0].direction == "outgoing"

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "Atlas Reasoning Engine"


def test_case_4_three_hop_reasoning_atlas():
    """Case 4: 'What technology was developed by the organization founded by the researcher who worked on Project Horizon?' -> Atlas Reasoning Engine"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)

    query = "What technology was developed by the organization founded by the researcher who worked on Project Horizon?"
    plan = planner.plan_query(query)
    assert plan.start_entity == "ent_project_horizon"
    assert len(plan.steps) == 3
    assert plan.steps[0].predicate == "WORKED_ON" and plan.steps[0].direction == "incoming"
    assert plan.steps[1].predicate == "FOUNDED" and plan.steps[1].direction == "outgoing"
    assert plan.steps[2].predicate == "DEVELOPED" and plan.steps[2].direction == "outgoing"

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "Atlas Reasoning Engine"
    assert res.hop_count == 3
    assert res.confidence >= 0.8


def test_case_5_what_did_vertex_research_develop():
    """Case 5: 'What did Vertex Research develop?' -> Nova Intelligence Platform"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)

    plan = planner.plan_query("What did Vertex Research develop?")
    assert plan.start_entity == "ent_vertex_research"
    assert plan.steps[0].predicate == "DEVELOPED"

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "Nova Intelligence Platform"


def test_case_6_project_horizon_no_direct_technology():
    """Case 6: 'What technology did Project Horizon develop directly?' -> Insufficient evidence"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)
    gap_detector = KnowledgeGapDetector(repo)

    plan = planner.plan_query("What technology did Project Horizon develop directly?")
    assert plan.start_entity == "ent_project_horizon"
    assert plan.steps[0].predicate == "DEVELOPED"

    res = engine.execute_query(plan)
    assert res.status == "insufficient_evidence"

    gap = gap_detector.analyze_gap(plan, res)
    assert gap.completed_hops == 0
    assert gap.missing_predicate == "DEVELOPED"


def test_case_7_temporal_constraint_insufficient():
    """Case 7: 'Who founded QuantumBridge Labs in 1995?' -> Insufficient evidence / unsupported constraint"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)

    plan = planner.plan_query("Who founded QuantumBridge Labs in 1995?")
    assert plan.temporal_constraint == "1995"

    res = engine.execute_query(plan)
    assert res.status == "insufficient_evidence"
    assert "1995" in res.explanation


def test_case_8_nonexistent_entity_not_found():
    """Case 8: 'Who worked on Project Chimera?' -> EntityNotFoundError / ENTITY_NOT_FOUND"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())

    with pytest.raises(EntityNotFoundError) as exc_info:
        planner.plan_query("Who worked on Project Chimera?")
    assert "Project Chimera" in str(exc_info.value)


def test_case_9_paraphrased_three_hop_reasoning():
    """Case 9: Paraphrased: 'Find the technology created by the lab started by the scientist involved in Project Horizon.' -> Atlas Reasoning Engine"""
    repo = setup_validation_graph()
    planner = NLQueryPlanner(repo, MockLLM())
    engine = BoundedReasoningEngine(repo)

    query = "Find the technology created by the lab started by the scientist involved in Project Horizon."
    plan = planner.plan_query(query)
    assert plan.start_entity == "ent_project_horizon"
    assert len(plan.steps) == 3

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "Atlas Reasoning Engine"


# 4. Generality Verification with Second Independent Document
def test_eaqc_generality_independent_document():
    """Verifies that EAQC generalizes to an entirely new, unseen domain document."""
    repo = InMemoryGraphRepository()

    # Domain: Biotech
    thorne = Entity(id="ent_thorne", canonical_name="Dr. Aris Thorne", type=EntityType.PERSON)
    bionano = Entity(id="ent_bionano", canonical_name="BioNano Dynamics", type=EntityType.ORGANIZATION)
    nanoheal = Entity(id="ent_nanoheal", canonical_name="NanoHeal Matrix", type=EntityType.TECHNOLOGY)

    repo.add_entity(thorne)
    repo.add_entity(bionano)
    repo.add_entity(nanoheal)

    doc = Document(
        id="doc_biotech",
        title="Biotech Advances",
        content_hash="hash_bio",
        ingestion_timestamp="2026-11-25T00:00:00Z",
        raw_text="Dr. Aris Thorne founded BioNano Dynamics. BioNano Dynamics developed NanoHeal Matrix.",
    )
    repo.add_document(doc)

    c1 = Claim(id="clm_b1", subject_id="ent_thorne", predicate="FOUNDED", object_id="ent_bionano", polarity=Polarity.AFFIRMED, confidence=1.0)
    c2 = Claim(id="clm_b2", subject_id="ent_bionano", predicate="DEVELOPED", object_id="ent_nanoheal", polarity=Polarity.AFFIRMED, confidence=1.0)
    repo.add_claim(c1)
    repo.add_claim(c2)

    ev1 = Evidence(id="ev_b1", claim_id="clm_b1", document_id="doc_biotech", quote="Dr. Aris Thorne founded BioNano Dynamics.", char_offset_start=0, char_offset_end=41)
    ev2 = Evidence(id="ev_b2", claim_id="clm_b2", document_id="doc_biotech", quote="BioNano Dynamics developed NanoHeal Matrix.", char_offset_start=42, char_offset_end=84)
    repo.add_evidence(ev1)
    repo.add_evidence(ev2)

    # Question on new document
    mock_llm = MockLLM(json.dumps({
        "start_entity": "ent_thorne",
        "steps": [
            {"predicate": "FOUNDED", "direction": "outgoing", "target_type": "ORGANIZATION"},
            {"predicate": "DEVELOPED", "direction": "outgoing", "target_type": "TECHNOLOGY"},
        ],
        "return_type": "TECHNOLOGY",
        "max_hops": 2,
    }))
    planner = NLQueryPlanner(repo, mock_llm)
    planner._match_relational_patterns = MagicMock(return_value=None)
    engine = BoundedReasoningEngine(repo)

    plan, status_code, latencies = planner.plan_query_with_telemetry("What technology was developed by the organization founded by Dr. Aris Thorne?")
    assert status_code == "SUCCESS"
    assert plan.start_entity == "ent_thorne"
    assert len(plan.steps) == 2

    res = engine.execute_query(plan)
    assert res.status == "success"
    assert len(res.matching_entities) == 1
    assert res.matching_entities[0].canonical_name == "NanoHeal Matrix"
