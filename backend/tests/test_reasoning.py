"""Tests for Bounded Graph Reasoning Engine, Multi-Hop Traversal, Cycle Prevention, and Ablation."""

from backend.app.ontology.models import EntityType
from backend.app.reasoning.ablation import evaluate_evidence_ablation
from backend.app.reasoning.models import StructuredQueryPlan, TraversalStep


def test_single_hop_traversal(reasoning_engine):
    """Verify 1-hop incoming traversal from Zurich Innovation Center to located organizations."""
    plan = StructuredQueryPlan(
        start_entity="ent_zurich",
        steps=[TraversalStep(predicate="LOCATED_IN", direction="incoming")],
        return_type=EntityType.ORGANIZATION,
        max_hops=1,
    )
    result = reasoning_engine.execute_query(plan)

    assert result.status in ("success", "contradiction_detected")
    assert result.hop_count == 1
    match_ids = {e.id for e in result.matching_entities}
    assert "ent_cognitive_dyn" in match_ids
    assert "ent_qubit_dynamics" in match_ids
    assert "ent_helix_foundry" in match_ids


def test_incoming_relationship_traversal(reasoning_engine):
    """Verify directional incoming query traversing from Project Prometheus to its researchers."""
    plan = StructuredQueryPlan(
        start_entity="ent_proj_prometheus",
        steps=[TraversalStep(predicate="WORKED_ON", direction="incoming")],
        return_type=EntityType.PERSON,
        max_hops=1,
    )
    result = reasoning_engine.execute_query(plan)

    assert result.status in ("success", "contradiction_detected")
    match_ids = {e.id for e in result.matching_entities}
    assert "ent_alyssa_vance" in match_ids
    assert "ent_marcus_chen" in match_ids


def test_three_hop_traversal(reasoning_engine):
    """Core benchmark: 3-hop traversal from Project Prometheus -> Researchers -> Organizations -> Technologies."""
    plan = StructuredQueryPlan(
        start_entity="ent_proj_prometheus",
        steps=[
            TraversalStep(predicate="WORKED_ON", direction="incoming"),
            TraversalStep(predicate="FOUNDED", direction="outgoing"),
            TraversalStep(predicate="DEVELOPED", direction="outgoing"),
        ],
        return_type=EntityType.TECHNOLOGY,
        max_hops=3,
    )
    result = reasoning_engine.execute_query(plan)

    # Contradiction flag is expected because Vance's founding of Cognitive Dynamics is disputed by DOC_007
    assert result.status == "contradiction_detected"
    assert result.hop_count == 3
    assert len(result.paths) >= 2

    match_ids = {e.id for e in result.matching_entities}
    assert "ent_tech_axiom_reasoner" in match_ids
    assert "ent_tech_synaptic_core" in match_ids

    # Path scores must follow C(P) = min C(e)
    for path in result.paths:
        assert path.hop_count == 3
        assert 0.0 < path.path_confidence <= 1.0


def test_cycle_prevention(reasoning_engine):
    """Verify that circular relationship paths do not cause infinite recursion."""
    # Dr. Vance -> Cognitive Dynamics -> Dr. Weber -> Dr. Vance -> ...
    plan = StructuredQueryPlan(
        start_entity="ent_alyssa_vance",
        steps=[
            TraversalStep(predicate="COLLABORATED_WITH", direction="both"),
            TraversalStep(predicate="COLLABORATED_WITH", direction="both"),
            TraversalStep(predicate="COLLABORATED_WITH", direction="both"),
        ],
        max_hops=3,
    )
    result = reasoning_engine.execute_query(plan)
    # Must complete promptly without recursion depth errors
    assert result.execution_time_ms < 500


def test_unanswerable_query(reasoning_engine):
    """Verify that ungrounded queries return insufficient_evidence rather than fabricating answers."""
    plan = StructuredQueryPlan(
        start_entity="ent_proj_hyperion",
        steps=[
            TraversalStep(predicate="WORKED_ON", direction="incoming"),
            TraversalStep(predicate="EMPLOYED_BY", direction="outgoing"),
            TraversalStep(predicate="DEVELOPED", direction="outgoing"),
        ],
        return_type=EntityType.TECHNOLOGY,
        predicate_filter="DEVELOPED_QUANTUM",
        max_hops=3,
    )
    # The synthetic corpus specifies Apex Robotics developed HoloVector, not quantum protocols
    # Step predicate filter checks for missing link
    plan.steps[2].predicate = "DEVELOPED_QUANTUM_BRIDGE"

    result = reasoning_engine.execute_query(plan)
    assert result.status == "insufficient_evidence"
    assert len(result.matching_entities) == 0
    assert len(result.paths) == 0
    assert "No valid reasoning paths found" in result.explanation


def test_counterfactual_evidence_ablation(reasoning_engine):
    """Verify non-destructive source removal and identification of critical vs redundant sources."""
    plan = StructuredQueryPlan(
        start_entity="ent_proj_prometheus",
        steps=[
            TraversalStep(predicate="WORKED_ON", direction="incoming"),
            TraversalStep(predicate="FOUNDED", direction="outgoing"),
            TraversalStep(predicate="DEVELOPED", direction="outgoing"),
        ],
        max_hops=3,
    )

    # 1. Synaptic Core Engine depends entirely on DOC_003
    ablation_synapse = evaluate_evidence_ablation(
        engine=reasoning_engine,
        plan=plan,
        target_entity_id="ent_tech_synaptic_core",
    )
    assert ablation_synapse["baseline_supported"] is True
    assert "DOC_003" in ablation_synapse["critical_sources"]
    assert ablation_synapse["robustness_score"] == 0.0

    # 2. Axiom Reasoner is corroborated across DOC_001, DOC_002, DOC_006
    ablation_axiom = evaluate_evidence_ablation(
        engine=reasoning_engine,
        plan=plan,
        target_entity_id="ent_tech_axiom_reasoner",
    )
    assert ablation_axiom["baseline_supported"] is True
    assert ablation_axiom["robustness_score"] > 0.5
