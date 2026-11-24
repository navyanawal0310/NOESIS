"""Knowledge Gap Detector for Unanswerable or Incomplete Queries."""

from typing import List, Optional, Set

from pydantic import BaseModel

from backend.app.graph.base import BaseGraphRepository
from backend.app.ontology.models import Entity, EntityType
from backend.app.reasoning.models import ReasoningResult, StructuredQueryPlan


class KnowledgeGap(BaseModel):
    """Structured diagnostic representation of a missing evidentiary link in the graph."""

    query_id: str
    completed_hops: int
    terminal_entity: Optional[Entity] = None
    missing_predicate: Optional[str] = None
    expected_target_type: Optional[EntityType] = None
    diagnostic_message: str


class KnowledgeGapDetector:
    """Detects missing evidentiary links when reasoning paths fail to connect."""

    def __init__(self, repository: BaseGraphRepository):
        self.repo = repository

    def _resolve_entity(self, identifier: str) -> Optional[Entity]:
        entity = self.repo.get_entity(identifier)
        if entity:
            return entity
        all_entities = self.repo.list_entities()
        target_norm = identifier.strip().lower()
        for e in all_entities:
            if e.canonical_name.strip().lower() == target_norm:
                return e
            for alias in e.aliases:
                if alias.strip().lower() == target_norm:
                    return e
        return None

    def analyze_gap(
        self,
        plan: StructuredQueryPlan,
        result: Optional[ReasoningResult] = None,
        query_id: Optional[str] = None,
    ) -> KnowledgeGap:
        """Traces a query plan step-by-step to identify the exact point of evidentiary discontinuity."""
        qid = query_id or (result.query_id if result else "gap_query")

        # 1. Check if start entity can be resolved
        start_entity = self._resolve_entity(plan.start_entity)
        if not start_entity:
            first_pred = plan.steps[0].predicate if plan.steps else None
            first_target = plan.steps[0].target_type if plan.steps else None
            return KnowledgeGap(
                query_id=qid,
                completed_hops=0,
                terminal_entity=None,
                missing_predicate=first_pred,
                expected_target_type=first_target,
                diagnostic_message=(
                    f"Start entity '{plan.start_entity}' does not exist in the knowledge graph. "
                    "Cannot initiate multi-hop traversal."
                ),
            )

        # 2. Trace step-by-step to find where traversal breaks
        current_entities = [start_entity]
        last_entity = start_entity
        completed_hops = 0
        excluded_docs = set(plan.excluded_document_ids)

        for step_idx, step in enumerate(plan.steps):
            next_entities: List[Entity] = []
            visited_ids: Set[str] = set()

            for ent in current_entities:
                adjacent = self.repo.get_adjacent_claims(
                    entity_id=ent.id,
                    direction=step.direction,
                    predicate=step.predicate,
                )
                for claim, next_ent in adjacent:
                    if next_ent.id in visited_ids:
                        continue
                    if step.target_type and next_ent.type != step.target_type:
                        continue

                    # Evidence check with ablation
                    evidence = self.repo.get_evidence_for_claim(claim.id)
                    active_evidence = [ev for ev in evidence if ev.document_id not in excluded_docs]
                    if not active_evidence and evidence:
                        continue

                    visited_ids.add(next_ent.id)
                    next_entities.append(next_ent)

            if not next_entities:
                # Traversal broke at step_idx
                expected_target = step.target_type or (plan.return_type if step_idx == len(plan.steps) - 1 else None)
                return KnowledgeGap(
                    query_id=qid,
                    completed_hops=step_idx,
                    terminal_entity=last_entity,
                    missing_predicate=step.predicate,
                    expected_target_type=expected_target,
                    diagnostic_message=(
                        f"Reasoning path halted at '{last_entity.canonical_name}' after {step_idx} hop(s). "
                        f"Missing {step.direction} relationship with predicate '{step.predicate}' "
                        f"targeting '{expected_target or 'any entity'}'."
                    ),
                )

            current_entities = next_entities
            last_entity = next_entities[0]
            completed_hops = step_idx + 1

        # Check return_type filter on final step if specified
        if plan.return_type:
            matching_final = [e for e in current_entities if e.type == plan.return_type]
            if not matching_final:
                return KnowledgeGap(
                    query_id=qid,
                    completed_hops=len(plan.steps),
                    terminal_entity=last_entity,
                    missing_predicate=None,
                    expected_target_type=plan.return_type,
                    diagnostic_message=(
                        f"All {len(plan.steps)} hops completed to '{last_entity.canonical_name}', "
                        f"but its entity type ({last_entity.type}) does not match expected return type '{plan.return_type}'."
                    ),
                )

        return KnowledgeGap(
            query_id=qid,
            completed_hops=completed_hops,
            terminal_entity=last_entity,
            missing_predicate=None,
            expected_target_type=plan.return_type,
            diagnostic_message="All planned traversal steps succeeded in the graph.",
        )
