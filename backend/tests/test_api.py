"""Tests for FastAPI API Routers and Schema Validation."""

from backend.app.api.v1.router import (
    CounterfactualRequest,
    execute_structured_query,
    get_claim,
    get_claim_evidence,
    get_contradictions,
    get_document,
    get_entity,
    get_graph,
    get_health,
    list_documents,
    list_entities,
    run_counterfactual_ablation,
)
from backend.app.reasoning.models import StructuredQueryPlan, TraversalStep


def test_api_health_endpoint(seeded_repository):
    """Verify health endpoint telemetry and active storage mode."""
    res = get_health(repo=seeded_repository)
    assert res.status == "healthy"
    assert res.storage_mode == "in_memory"
    assert res.is_database_healthy is True
    assert res.total_entities >= 25
    assert res.total_claims >= 35
    assert res.total_documents == 10


def test_api_graph_endpoint(seeded_repository):
    """Verify full graph export payload schema."""
    res = get_graph(repo=seeded_repository)
    assert "storage_mode" in res
    assert "elements" in res
    assert len(res["elements"]["nodes"]) > 0
    assert len(res["elements"]["edges"]) > 0


def test_api_documents_endpoints(seeded_repository):
    """Verify document list and single document retrieval."""
    docs = list_documents(repo=seeded_repository)
    assert len(docs) == 10

    doc1 = get_document("DOC_001", repo=seeded_repository)
    assert doc1.id == "DOC_001"
    assert "Project Prometheus" in doc1.title
    assert doc1.source_type == "synthetic"


def test_api_entities_endpoints(seeded_repository):
    """Verify entity list and detail retrieval."""
    entities = list_entities(repo=seeded_repository)
    assert len(entities) >= 25

    ent = get_entity("ent_alyssa_vance", repo=seeded_repository)
    assert ent.id == "ent_alyssa_vance"
    assert ent.canonical_name == "Dr. Alyssa Vance"


def test_api_claims_and_evidence_endpoints(seeded_repository):
    """Verify claim retrieval and grounded evidence mapping."""
    # Find claim for Marcus Chen founding Synapse Bio
    claims = seeded_repository.list_claims(predicate="FOUNDED", subject_id="ent_marcus_chen")
    assert len(claims) > 0
    claim = claims[0]

    fetched_claim = get_claim(claim.id, repo=seeded_repository)
    assert fetched_claim.id == claim.id

    evidence_list = get_claim_evidence(claim.id, repo=seeded_repository)
    assert len(evidence_list) > 0
    assert evidence_list[0].document_id == "DOC_003"
    assert "Dr. Marcus Chen founded Synapse Bio" in evidence_list[0].quote


def test_api_structured_query_endpoint(reasoning_engine):
    """Verify POST /api/v1/query/structured response model."""
    plan = StructuredQueryPlan(
        start_entity="ent_proj_prometheus",
        steps=[
            TraversalStep(predicate="WORKED_ON", direction="incoming"),
            TraversalStep(predicate="FOUNDED", direction="outgoing"),
            TraversalStep(predicate="DEVELOPED", direction="outgoing"),
        ],
        max_hops=3,
    )
    result = execute_structured_query(plan=plan, engine=reasoning_engine)
    assert result.status == "contradiction_detected"
    assert len(result.matching_entities) >= 2
    assert result.hop_count == 3


def test_api_contradictions_and_counterfactual_endpoints(seeded_repository, reasoning_engine):
    """Verify contradiction detection and counterfactual ablation endpoints."""
    contradictions = get_contradictions(repo=seeded_repository)
    assert contradictions["total_contradictions"] >= 2

    plan = StructuredQueryPlan(
        start_entity="ent_proj_prometheus",
        steps=[
            TraversalStep(predicate="WORKED_ON", direction="incoming"),
            TraversalStep(predicate="FOUNDED", direction="outgoing"),
            TraversalStep(predicate="DEVELOPED", direction="outgoing"),
        ],
        max_hops=3,
    )
    req = CounterfactualRequest(query_plan=plan, target_entity_id="ent_tech_synaptic_core")
    ablation_res = run_counterfactual_ablation(request=req, engine=reasoning_engine)
    assert ablation_res["baseline_supported"] is True
    assert "DOC_003" in ablation_res["critical_sources"]
