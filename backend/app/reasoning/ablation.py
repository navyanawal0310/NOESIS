"""Counterfactual Evidence Ablation Engine.

Evaluates conclusion survival when individual source documents are systematically excluded.
"""

from typing import Any, Dict

from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.models import StructuredQueryPlan


def evaluate_evidence_ablation(
    engine: BoundedReasoningEngine,
    plan: StructuredQueryPlan,
    target_entity_id: str,
) -> Dict[str, Any]:
    """Tests non-destructive source removal against a specific target conclusion.

    Returns:
      - baseline_supported: bool
      - ablation_results: List of per-document survival results
      - robustness_score: Fraction of document removals survived (R(a))
      - critical_sources: Documents whose removal breaks the conclusion
      - redundant_sources: Documents whose removal preserves the conclusion
    """
    # 1. Run baseline query with all sources
    baseline_plan = plan.model_copy(update={"excluded_document_ids": []})
    baseline_res = engine.execute_query(baseline_plan)

    baseline_targets = {e.id for e in baseline_res.matching_entities}
    if target_entity_id not in baseline_targets:
        return {
            "target_entity_id": target_entity_id,
            "baseline_supported": False,
            "robustness_score": 0.0,
            "critical_sources": [],
            "redundant_sources": [],
            "ablation_results": [],
            "summary": "Target entity was not supported even under baseline full-corpus conditions.",
        }

    # 2. Extract all supporting documents for target entity paths
    relevant_doc_ids = set()
    for path in baseline_res.paths:
        if path.terminal_entity.id == target_entity_id:
            relevant_doc_ids.update(path.supporting_document_ids)

    doc_list = sorted(list(relevant_doc_ids))
    critical_sources = []
    redundant_sources = []
    ablation_details = []

    # 3. Simulate exclusion of each document individually
    for doc_id in doc_list:
        ablated_plan = plan.model_copy(update={"excluded_document_ids": [doc_id]})
        ablated_res = engine.execute_query(ablated_plan)

        survived = target_entity_id in {e.id for e in ablated_res.matching_entities}
        ablation_details.append(
            {
                "excluded_document_id": doc_id,
                "conclusion_survived": survived,
                "active_paths_count": len([p for p in ablated_res.paths if p.terminal_entity.id == target_entity_id]),
            }
        )

        if survived:
            redundant_sources.append(doc_id)
        else:
            critical_sources.append(doc_id)

    # 4. Compute robustness score R(a)
    n = len(doc_list)
    robustness_score = (len(redundant_sources) / n) if n > 0 else 1.0

    return {
        "target_entity_id": target_entity_id,
        "baseline_supported": True,
        "total_supporting_documents": n,
        "robustness_score": round(robustness_score, 4),
        "critical_sources": critical_sources,
        "redundant_sources": redundant_sources,
        "ablation_results": ablation_details,
        "summary": (
            f"Conclusion survives {len(redundant_sources)}/{n} source removal tests "
            f"(Robustness R(a) = {round(robustness_score, 4)}). "
            f"Critical evidence: {critical_sources}."
        ),
    }
