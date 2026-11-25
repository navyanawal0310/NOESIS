"""NOESIS Research Evaluation Metrics Module.

Implements all 25 scientific metrics across 5 evaluation phases:
Phase A: Extraction Fidelity (entity/relation F1, quote accuracy, durations)
Phase B: Multi-Hop Traversal (EM, precision, recall, F1, path validity, citations, traversal latency)
Phase C: Query Planning (start entity, predicates, directions, complete plan, planning latency, LLM calls)
Phase D: Dialectical Reasoning (contradiction P/R/F1, ablation, abstention, false gap rate, constraint handling)
Phase E: End-to-End Performance (end-to-end latency, tokens/sec)

Zero-division safe: All functions return structured MetricResult with numerator,
denominator, and sample size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class MetricResult:
    """Structured container for evaluation metric calculation."""

    name: str
    value: float
    numerator: float = 0.0
    denominator: float = 0.0
    sample_size: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "numerator": round(self.numerator, 4),
            "denominator": round(self.denominator, 4),
            "sample_size": self.sample_size,
            "details": self.details,
        }


# ==============================================================================
# Helper Utilities
# ==============================================================================

ENTITY_ID_TO_CANONICAL: Dict[str, str] = {}
try:
    from datasets.synthetic.builder import ENTITIES_DATA
    for ent in ENTITIES_DATA:
        ENTITY_ID_TO_CANONICAL[ent["id"].strip().lower()] = ent["canonical_name"].strip().lower()
        for alias in ent.get("aliases", []):
            ENTITY_ID_TO_CANONICAL[alias.strip().lower()] = ent["canonical_name"].strip().lower()
except Exception:
    pass


def normalize_entity_str(s: str) -> str:
    """Normalize entity name or ID for robust comparison."""
    if not s:
        return ""
    norm = s.strip().lower()
    return ENTITY_ID_TO_CANONICAL.get(norm, norm)


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division returning default if denominator is zero."""
    if abs(denominator) < 1e-9:
        return default
    return numerator / denominator


def compute_f1(precision: float, recall: float) -> float:
    """Compute harmonic mean of precision and recall."""
    if precision + recall < 1e-9:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


# ==============================================================================
# Phase A: Knowledge Graph Extraction Fidelity
# ==============================================================================

def entity_extraction_f1(
    predicted_entities: List[str],
    gold_entities: List[str],
) -> MetricResult:
    """Compute precision, recall, and F1 for extracted entity mentions."""
    pred_set = {normalize_entity_str(e) for e in predicted_entities if e}
    gold_set = {normalize_entity_str(e) for e in gold_entities if e}

    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = compute_f1(precision, recall)

    return MetricResult(
        name="entity_extraction_f1",
        value=f1,
        numerator=tp,
        denominator=len(gold_set),
        sample_size=len(pred_set),
        details={"precision": round(precision, 4), "recall": round(recall, 4), "tp": tp, "fp": fp, "fn": fn},
    )


def relationship_extraction_f1(
    predicted_triples: List[Tuple[str, str, str]],
    gold_triples: List[Tuple[str, str, str]],
) -> MetricResult:
    """Compute precision, recall, and F1 for extracted (subject, predicate, object) triples."""
    def norm_triple(t: Tuple[str, str, str]) -> Tuple[str, str, str]:
        return (normalize_entity_str(t[0]), t[1].strip().upper(), normalize_entity_str(t[2]))

    pred_set = {norm_triple(t) for t in predicted_triples if len(t) == 3}
    gold_set = {norm_triple(t) for t in gold_triples if len(t) == 3}

    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = compute_f1(precision, recall)

    return MetricResult(
        name="relationship_extraction_f1",
        value=f1,
        numerator=tp,
        denominator=len(gold_set),
        sample_size=len(pred_set),
        details={"precision": round(precision, 4), "recall": round(recall, 4), "tp": tp, "fp": fp, "fn": fn},
    )


def exact_quote_character_accuracy(
    quotes_verified: int,
    total_quotes: int,
) -> MetricResult:
    """Verify exact character offset matching of evidence in raw documents."""
    val = safe_div(quotes_verified, total_quotes, default=1.0 if total_quotes == 0 else 0.0)
    return MetricResult(
        name="exact_quote_character_accuracy",
        value=val,
        numerator=quotes_verified,
        denominator=total_quotes,
        sample_size=total_quotes,
    )


def initial_ingestion_duration(duration_seconds: float) -> MetricResult:
    """Measure single document or chunk ingestion latency."""
    return MetricResult(
        name="initial_ingestion_duration",
        value=duration_seconds,
        numerator=duration_seconds,
        denominator=1.0,
        sample_size=1,
    )


def cumulative_processing_duration(total_seconds: float, doc_count: int) -> MetricResult:
    """Measure cumulative ingestion latency over N documents."""
    return MetricResult(
        name="cumulative_processing_duration",
        value=total_seconds,
        numerator=total_seconds,
        denominator=float(doc_count) if doc_count > 0 else 1.0,
        sample_size=doc_count,
        details={"avg_per_doc": round(safe_div(total_seconds, doc_count), 4)},
    )


# ==============================================================================
# Phase B: Deterministic Multi-Hop Traversal (Oracle Graph)
# ==============================================================================

def answer_exact_match(
    predicted_entities: List[str],
    gold_entities: List[str],
) -> MetricResult:
    """Exact Match (EM): 1.0 if predicted entity set equals gold entity set, else 0.0."""
    pred_set = {normalize_entity_str(e) for e in predicted_entities if e}
    gold_set = {normalize_entity_str(e) for e in gold_entities if e}

    is_match = 1.0 if (pred_set == gold_set) else 0.0
    return MetricResult(
        name="answer_exact_match",
        value=is_match,
        numerator=is_match,
        denominator=1.0,
        sample_size=1,
        details={"pred_count": len(pred_set), "gold_count": len(gold_set)},
    )


def entity_set_precision(
    predicted_entities: List[str],
    gold_entities: List[str],
) -> MetricResult:
    """Entity set precision: |pred ∩ gold| / |pred|."""
    pred_set = {normalize_entity_str(e) for e in predicted_entities if e}
    gold_set = {normalize_entity_str(e) for e in gold_entities if e}

    if not pred_set and not gold_set:
        return MetricResult(name="entity_set_precision", value=1.0, numerator=0, denominator=0, sample_size=0)
    if not pred_set:
        return MetricResult(name="entity_set_precision", value=0.0, numerator=0, denominator=0, sample_size=0)

    tp = len(pred_set & gold_set)
    val = safe_div(tp, len(pred_set))
    return MetricResult(
        name="entity_set_precision",
        value=val,
        numerator=tp,
        denominator=len(pred_set),
        sample_size=len(pred_set),
    )


def entity_set_recall(
    predicted_entities: List[str],
    gold_entities: List[str],
) -> MetricResult:
    """Entity set recall: |pred ∩ gold| / |gold|."""
    pred_set = {normalize_entity_str(e) for e in predicted_entities if e}
    gold_set = {normalize_entity_str(e) for e in gold_entities if e}

    if not pred_set and not gold_set:
        return MetricResult(name="entity_set_recall", value=1.0, numerator=0, denominator=0, sample_size=0)
    if not gold_set:
        return MetricResult(name="entity_set_recall", value=0.0, numerator=0, denominator=0, sample_size=0)

    tp = len(pred_set & gold_set)
    val = safe_div(tp, len(gold_set))
    return MetricResult(
        name="entity_set_recall",
        value=val,
        numerator=tp,
        denominator=len(gold_set),
        sample_size=len(gold_set),
    )


def entity_set_f1(
    predicted_entities: List[str],
    gold_entities: List[str],
) -> MetricResult:
    """Entity set F1 score."""
    p_res = entity_set_precision(predicted_entities, gold_entities)
    r_res = entity_set_recall(predicted_entities, gold_entities)
    f1 = compute_f1(p_res.value, r_res.value)
    return MetricResult(
        name="entity_set_f1",
        value=f1,
        numerator=2 * p_res.numerator,
        denominator=p_res.denominator + r_res.denominator,
        sample_size=max(len(predicted_entities), len(gold_entities)),
        details={"precision": p_res.value, "recall": r_res.value},
    )


def reasoning_path_validity(
    executed_paths: List[List[str]],
    expected_paths: List[List[str]],
) -> MetricResult:
    """1.0 if at least one executed path matches an expected canonical reasoning path."""
    if not expected_paths and not executed_paths:
        return MetricResult(name="reasoning_path_validity", value=1.0, numerator=1, denominator=1, sample_size=1)
    if not executed_paths or not expected_paths:
        return MetricResult(name="reasoning_path_validity", value=0.0, numerator=0, denominator=1, sample_size=1)

    norm_exp = [
        [normalize_entity_str(node) for node in path]
        for path in expected_paths
    ]
    norm_exec = [
        [normalize_entity_str(node) for node in path]
        for path in executed_paths
    ]

    matched = any(p in norm_exp for p in norm_exec)
    val = 1.0 if matched else 0.0
    return MetricResult(
        name="reasoning_path_validity",
        value=val,
        numerator=val,
        denominator=1.0,
        sample_size=len(executed_paths),
    )


def lexical_citation_validity(
    verified_citations: int,
    total_citations: int,
) -> MetricResult:
    """% of citations whose quote string matches source document verbatim."""
    val = safe_div(verified_citations, total_citations, default=1.0 if total_citations == 0 else 0.0)
    return MetricResult(
        name="lexical_citation_validity",
        value=val,
        numerator=verified_citations,
        denominator=total_citations,
        sample_size=total_citations,
    )


def semantic_citation_correctness(
    correct_citations: int,
    total_citations: int,
) -> MetricResult:
    """% of citations that logically entail the relational claim."""
    val = safe_div(correct_citations, total_citations, default=1.0 if total_citations == 0 else 0.0)
    return MetricResult(
        name="semantic_citation_correctness",
        value=val,
        numerator=correct_citations,
        denominator=total_citations,
        sample_size=total_citations,
    )


def graph_traversal_latency(traversal_ms: float) -> MetricResult:
    """Time in milliseconds spent exclusively executing graph traversal."""
    return MetricResult(
        name="graph_traversal_latency",
        value=traversal_ms,
        numerator=traversal_ms,
        denominator=1.0,
        sample_size=1,
    )


# ==============================================================================
# Phase C: Natural-Language Query Planning & Compilation
# ==============================================================================

def start_entity_accuracy(
    predicted_start_entity: str,
    gold_start_entity: str,
) -> MetricResult:
    """1.0 if EAQC or planner selected the correct start anchor entity."""
    matched = normalize_entity_str(predicted_start_entity) == normalize_entity_str(gold_start_entity)
    val = 1.0 if matched else 0.0
    return MetricResult(
        name="start_entity_accuracy",
        value=val,
        numerator=val,
        denominator=1.0,
        sample_size=1,
    )


def predicate_sequence_accuracy(
    predicted_predicates: List[str],
    gold_predicates: List[str],
) -> MetricResult:
    """1.0 if the planned sequence of predicates matches gold exactly."""
    norm_pred = [p.strip().upper() for p in predicted_predicates]
    norm_gold = [p.strip().upper() for p in gold_predicates]
    matched = (norm_pred == norm_gold)
    val = 1.0 if matched else 0.0
    return MetricResult(
        name="predicate_sequence_accuracy",
        value=val,
        numerator=val,
        denominator=1.0,
        sample_size=1,
        details={"predicted": norm_pred, "gold": norm_gold},
    )


def traversal_direction_accuracy(
    predicted_directions: List[str],
    gold_directions: List[str],
) -> MetricResult:
    """1.0 if the planned sequence of traversal directions matches gold exactly."""
    norm_pred = [d.strip().lower() for d in predicted_directions]
    norm_gold = [d.strip().lower() for d in gold_directions]
    matched = (norm_pred == norm_gold)
    val = 1.0 if matched else 0.0
    return MetricResult(
        name="traversal_direction_accuracy",
        value=val,
        numerator=val,
        denominator=1.0,
        sample_size=1,
    )


def complete_query_plan_accuracy(
    predicted_start: str,
    predicted_predicates: List[str],
    predicted_directions: List[str],
    gold_start: str,
    gold_predicates: List[str],
    gold_directions: List[str],
) -> MetricResult:
    """1.0 if start entity, predicate sequence, and directions ALL match gold."""
    c_start = start_entity_accuracy(predicted_start, gold_start).value
    c_pred = predicate_sequence_accuracy(predicted_predicates, gold_predicates).value
    c_dir = traversal_direction_accuracy(predicted_directions, gold_directions).value
    full_match = 1.0 if (c_start == 1.0 and c_pred == 1.0 and c_dir == 1.0) else 0.0
    return MetricResult(
        name="complete_query_plan_accuracy",
        value=full_match,
        numerator=full_match,
        denominator=1.0,
        sample_size=1,
        details={"start_ok": bool(c_start), "pred_ok": bool(c_pred), "dir_ok": bool(c_dir)},
    )


def planning_latency(planning_ms: float) -> MetricResult:
    """Time in milliseconds spent compiling natural-language query to plan."""
    return MetricResult(
        name="planning_latency",
        value=planning_ms,
        numerator=planning_ms,
        denominator=1.0,
        sample_size=1,
    )


def llm_calls_per_query(call_count: int) -> MetricResult:
    """Explicit count of LLM inferences executed for query."""
    return MetricResult(
        name="llm_calls_per_query",
        value=float(call_count),
        numerator=float(call_count),
        denominator=1.0,
        sample_size=1,
    )


# ==============================================================================
# Phase D: Dialectical Reasoning (Contradiction & Ablation)
# ==============================================================================

def contradiction_precision(
    detected_contradictions: int,
    total_reported_contradictions: int,
) -> MetricResult:
    """Precision of contradiction detection: TP / (TP + FP)."""
    val = safe_div(detected_contradictions, total_reported_contradictions, default=1.0 if total_reported_contradictions == 0 else 0.0)
    return MetricResult(
        name="contradiction_precision",
        value=val,
        numerator=detected_contradictions,
        denominator=total_reported_contradictions,
        sample_size=total_reported_contradictions,
    )


def contradiction_recall(
    detected_contradictions: int,
    gold_contradictions: int,
) -> MetricResult:
    """Recall of contradiction detection: TP / (TP + FN)."""
    val = safe_div(detected_contradictions, gold_contradictions, default=1.0 if gold_contradictions == 0 else 0.0)
    return MetricResult(
        name="contradiction_recall",
        value=val,
        numerator=detected_contradictions,
        denominator=gold_contradictions,
        sample_size=gold_contradictions,
    )


def contradiction_f1(
    precision: float,
    recall: float,
) -> MetricResult:
    """Harmonic mean of contradiction precision and recall."""
    f1 = compute_f1(precision, recall)
    return MetricResult(
        name="contradiction_f1",
        value=f1,
        numerator=f1,
        denominator=1.0,
        sample_size=1,
    )


def evidence_ablation_correctness(
    ablation_caused_failure: bool,
    expected_failure: bool,
) -> MetricResult:
    """1.0 if non-destructive ablation correctly disrupted reasoning when expected."""
    matched = (ablation_caused_failure == expected_failure)
    val = 1.0 if matched else 0.0
    return MetricResult(
        name="evidence_ablation_correctness",
        value=val,
        numerator=val,
        denominator=1.0,
        sample_size=1,
    )


def abstention_accuracy(
    system_abstained: bool,
    expected_abstention: bool,
) -> MetricResult:
    """1.0 if system abstains when unanswerable, and answers when answerable."""
    matched = (system_abstained == expected_abstention)
    val = 1.0 if matched else 0.0
    return MetricResult(
        name="abstention_accuracy",
        value=val,
        numerator=val,
        denominator=1.0,
        sample_size=1,
    )


def false_knowledge_gap_rate(
    false_gap_count: int,
    answerable_query_count: int,
) -> MetricResult:
    """Rate at which answerable queries are incorrectly rejected as knowledge gaps."""
    val = safe_div(false_gap_count, answerable_query_count, default=0.0)
    return MetricResult(
        name="false_knowledge_gap_rate",
        value=val,
        numerator=false_gap_count,
        denominator=answerable_query_count,
        sample_size=answerable_query_count,
    )


def unsupported_constraint_handling(
    rejected_count: int,
    total_unsupported_queries: int,
) -> MetricResult:
    """% of ungrounded constraint queries (e.g. year 1850) properly rejected."""
    val = safe_div(rejected_count, total_unsupported_queries, default=1.0 if total_unsupported_queries == 0 else 0.0)
    return MetricResult(
        name="unsupported_constraint_handling",
        value=val,
        numerator=rejected_count,
        denominator=total_unsupported_queries,
        sample_size=total_unsupported_queries,
    )


# ==============================================================================
# Phase E: End-to-End Performance & Aggregation
# ==============================================================================

def end_to_end_latency(total_ms: float) -> MetricResult:
    """Total wall-clock duration from question arrival to final answer."""
    return MetricResult(
        name="end_to_end_latency",
        value=total_ms,
        numerator=total_ms,
        denominator=1.0,
        sample_size=1,
    )


def aggregate_metric_results(results: List[MetricResult]) -> MetricResult:
    """Aggregate multiple case-level results into a micro/macro averaged metric."""
    if not results:
        return MetricResult(name="empty", value=0.0, numerator=0, denominator=0, sample_size=0)

    name = results[0].name
    total_num = sum(r.numerator for r in results)
    total_den = sum(r.denominator for r in results)
    total_samples = sum(r.sample_size for r in results)

    # If denominator exists, micro-average (sum_num / sum_den); otherwise macro-average mean(values)
    if total_den > 1e-9:
        val = safe_div(total_num, total_den)
    else:
        val = sum(r.value for r in results) / len(results)

    return MetricResult(
        name=name,
        value=val,
        numerator=total_num,
        denominator=total_den,
        sample_size=len(results),
        details={"total_subsamples": total_samples},
    )


def compute_benchmark_summary(case_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute consolidated summary dictionary across all evaluated benchmark cases."""
    if not case_evaluations:
        return {"total_cases": 0, "metrics": {}}

    metric_buckets: Dict[str, List[MetricResult]] = {}

    for case in case_evaluations:
        for metric_name, m_dict in case.get("metrics", {}).items():
            if isinstance(m_dict, dict) and "value" in m_dict:
                mr = MetricResult(
                    name=metric_name,
                    value=m_dict.get("value", 0.0),
                    numerator=m_dict.get("numerator", 0.0),
                    denominator=m_dict.get("denominator", 0.0),
                    sample_size=m_dict.get("sample_size", 1),
                )
                metric_buckets.setdefault(metric_name, []).append(mr)

    summary_metrics = {}
    for mname, mlist in metric_buckets.items():
        agg = aggregate_metric_results(mlist)
        summary_metrics[mname] = agg.to_dict()

    return {
        "total_cases_evaluated": len(case_evaluations),
        "metrics": summary_metrics,
    }
