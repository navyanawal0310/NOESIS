"""Automated Tests for NOESIS Research Evaluation Framework."""

from pathlib import Path

from backend.app.api.v1.router import (
    get_benchmark_overview,
    get_evaluation_summary,
    list_experiments,
)
from evaluation.baselines.full_noesis import FullNOESISSystem
from evaluation.baselines.standard_kg import StandardKGSystem
from evaluation.metrics import (
    abstention_accuracy,
    answer_exact_match,
    compute_f1,
    contradiction_precision,
    contradiction_recall,
    entity_set_f1,
    entity_set_precision,
    entity_set_recall,
    reasoning_path_validity,
    safe_div,
    unsupported_constraint_handling,
)
from evaluation.verify_benchmark import verify_benchmark

BENCHMARK_FILE = Path(__file__).resolve().parent.parent.parent / "datasets" / "benchmarks" / "nvs100.json"


def test_nvs100_benchmark_integrity():
    """Verify that NVS-100 passes all integrity, category, and zero-leakage checks."""
    assert verify_benchmark() is True


def test_safe_div_zero_handling():
    """Verify zero-denominator handling does not raise ZeroDivisionError."""
    assert safe_div(10.0, 0.0) == 0.0
    assert safe_div(0.0, 0.0) == 0.0
    assert safe_div(10.0, 2.0) == 5.0
    assert compute_f1(0.0, 0.0) == 0.0


def test_metrics_entity_set_f1():
    """Verify set precision, recall, and F1 calculations."""
    pred = ["Cognitive Dynamics", "Synapse Bio"]
    gold = ["Cognitive Dynamics", "Apex Robotics Systems"]

    p = entity_set_precision(pred, gold)
    r = entity_set_recall(pred, gold)
    f = entity_set_f1(pred, gold)

    assert p.value == 0.5
    assert r.value == 0.5
    assert f.value == 0.5

    # Empty sets
    p_empty = entity_set_precision([], [])
    assert p_empty.value == 1.0


def test_metrics_answer_exact_match():
    """Verify Answer Exact Match metric."""
    assert answer_exact_match(["Cognitive Dynamics"], ["Cognitive Dynamics"]).value == 1.0
    assert answer_exact_match(["Cognitive Dynamics"], ["Synapse Bio"]).value == 0.0


def test_metrics_path_validity():
    """Verify reasoning path validity matches canonical path sequences."""
    exec_paths = [["Dr. Alyssa Vance", "Cognitive Dynamics", "Axiom Semantic Reasoner"]]
    exp_paths = [["ent_alyssa_vance", "Cognitive Dynamics", "Axiom Semantic Reasoner"]]

    res = reasoning_path_validity(exec_paths, exp_paths)
    assert res.value == 1.0


def test_metrics_contradiction_and_abstention():
    """Verify dialectical contradiction and abstention metrics."""
    assert contradiction_precision(1, 1).value == 1.0
    assert contradiction_recall(1, 2).value == 0.5
    assert abstention_accuracy(True, True).value == 1.0
    assert abstention_accuracy(False, True).value == 0.0
    assert unsupported_constraint_handling(1, 1).value == 1.0


def test_full_noesis_baseline_execution(seeded_repository):
    """Verify FullNOESISSystem executes structured queries on seeded graph."""
    system = FullNOESISSystem(repository=seeded_repository)
    plan = {
        "start_entity": "Dr. Alyssa Vance",
        "steps": [{"predicate": "FOUNDED", "direction": "outgoing", "target_type": "ORGANIZATION"}],
    }
    result = system.execute(
        question="What organization was founded by Dr. Alyssa Vance?",
        case_id="TEST-01",
        structured_plan=plan,
        mode="structured",
    )
    assert "Cognitive Dynamics" in result.answer_entities
    assert result.latency_ms > 0
    assert result.graph_traversal_ms > 0


def test_standard_kg_baseline_execution(seeded_repository):
    """Verify StandardKGSystem executes raw triple traversal."""
    system = StandardKGSystem(repository=seeded_repository)
    plan = {
        "start_entity": "Dr. Alyssa Vance",
        "steps": [{"predicate": "FOUNDED", "direction": "outgoing"}],
    }
    result = system.execute(
        question="What organization was founded by Dr. Alyssa Vance?",
        case_id="TEST-02",
        structured_plan=plan,
        mode="structured",
    )
    assert "Cognitive Dynamics" in result.answer_entities
    assert result.citations == []
    assert result.contradiction_detected is False


def test_evaluation_api_endpoints():
    """Verify evaluation REST endpoints return valid benchmark data and experiments."""
    data_bench = get_benchmark_overview()
    assert data_bench["total_cases"] == 100
    assert data_bench["split_distribution"]["dev"] == 60
    assert data_bench["split_distribution"]["test"] == 40

    data_exp = list_experiments()
    assert "experiments" in data_exp
    assert len(data_exp["experiments"]) >= 2
    for exp in data_exp["experiments"]:
        assert "status" in exp
        assert "experiment_id" in exp

    data_sum = get_evaluation_summary()
    assert "systems_evaluated" in data_sum
    assert "incomplete_experiments" in data_sum
    assert "infrastructure_failures" in data_sum
    assert "human_study_status" in data_sum

    # Test individual experiment retrieval
    from backend.app.api.v1.router import get_experiment_details

    details_struct = get_experiment_details("nvs100-noesis-structured")
    assert details_struct["status"] == "completed"
    assert details_struct["cases_evaluated"] == 100

    details_incomplete = get_experiment_details("nvs100-noesis-natural")
    assert details_incomplete["status"] == "incomplete"
