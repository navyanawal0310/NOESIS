"""Bounded Multi-Hop Graph Reasoning Engine."""

import time
import uuid
from typing import Dict, List, Optional, Set, Tuple
from backend.app.extraction.validator import validate_evidence_quotation
from backend.app.graph.base import BaseGraphRepository
from backend.app.ontology.models import Claim, Entity, EntityType, Evidence
from backend.app.reasoning.confidence import compute_claim_confidence, compute_path_confidence
from backend.app.reasoning.models import (
    PathSegment,
    ReasoningPath,
    ReasoningResult,
    StructuredQueryPlan,
)


class BoundedReasoningEngine:
    """Engine executing deterministic, bounded graph traversals with cycle prevention

    and provenance preservation.
    """

    def __init__(self, repository: BaseGraphRepository):
        self.repo = repository

    def _resolve_start_entity(self, identifier: str) -> Optional[Entity]:
        """Resolves start entity by ID, canonical name, or aliases."""
        entity = self.repo.get_entity(identifier)
        if entity:
            return entity

        # Search by canonical name or alias
        all_entities = self.repo.list_entities()
        target_norm = identifier.strip().lower()
        for e in all_entities:
            if e.canonical_name.strip().lower() == target_norm:
                return e
            for alias in e.aliases:
                if alias.strip().lower() == target_norm:
                    return e
        return None

    def execute_query(self, plan: StructuredQueryPlan) -> ReasoningResult:
        """Executes a structured query plan and returns comprehensive reasoning results."""
        start_time = time.perf_counter()
        query_id = f"qry_{uuid.uuid4().hex[:12]}"

        # 1. Resolve start entity
        start_entity = self._resolve_start_entity(plan.start_entity)
        if not start_entity:
            elapsed = (time.perf_counter() - start_time) * 1000
            return ReasoningResult(
                query_id=query_id,
                status="insufficient_evidence",
                start_entity=None,
                matching_entities=[],
                paths=[],
                hop_count=0,
                conflicting_claims=[],
                evidence_records=[],
                execution_time_ms=round(elapsed, 2),
                confidence=0.0,
                explanation=f"Start entity '{plan.start_entity}' could not be resolved in the knowledge graph.",
            )

        # 2. Check hop bounds
        num_steps = len(plan.steps)
        if num_steps > plan.max_hops:
            elapsed = (time.perf_counter() - start_time) * 1000
            return ReasoningResult(
                query_id=query_id,
                status="insufficient_evidence",
                start_entity=start_entity,
                matching_entities=[],
                paths=[],
                hop_count=0,
                conflicting_claims=[],
                evidence_records=[],
                execution_time_ms=round(elapsed, 2),
                confidence=0.0,
                explanation=f"Query specifies {num_steps} steps which exceeds max_hops={plan.max_hops}.",
            )

        # 3. Recursive path search with cycle prevention
        completed_paths: List[ReasoningPath] = []
        excluded_docs = set(plan.excluded_document_ids)

        def search_step(
            current_entity: Entity,
            step_idx: int,
            current_segments: List[PathSegment],
            visited_entity_ids: Set[str],
        ):
            if step_idx >= num_steps:
                # Terminal step reached
                if plan.return_type and current_entity.type != plan.return_type:
                    return

                # Calculate path confidence and aggregate documents
                segment_confs = [seg.segment_confidence for seg in current_segments]
                p_conf = compute_path_confidence(segment_confs)
                all_docs = []
                for seg in current_segments:
                    for ev in seg.evidence:
                        if ev.document_id not in all_docs:
                            all_docs.append(ev.document_id)

                completed_paths.append(
                    ReasoningPath(
                        segments=current_segments,
                        terminal_entity=current_entity,
                        hop_count=len(current_segments),
                        path_confidence=p_conf,
                        supporting_document_ids=all_docs,
                    )
                )
                return

            step = plan.steps[step_idx]

            # Query adjacent claims in specified direction
            adjacent = self.repo.get_adjacent_claims(
                entity_id=current_entity.id,
                direction=step.direction,
                predicate=step.predicate,
            )

            for claim, next_entity in adjacent:
                # Cycle prevention: Do not revisit entities already in path
                if next_entity.id in visited_entity_ids:
                    continue

                # Target type check if specified in step
                if step.target_type and next_entity.type != step.target_type:
                    continue

                # Evidence retrieval
                evidence = self.repo.get_evidence_for_claim(claim.id)

                # Filter out excluded documents (Ablation support)
                active_evidence = [ev for ev in evidence if ev.document_id not in excluded_docs]
                if not active_evidence and evidence:
                    # Claim is entirely dependent on ablated sources, so path is blocked
                    continue

                # Contradiction check
                contra_claims = []
                for cid in claim.contradiction_ids:
                    c = self.repo.get_claim(cid)
                    if c:
                        contra_claims.append(c)

                # Validate evidence quotations against source document text
                all_quotes_valid = True
                for ev in active_evidence:
                    doc = self.repo.get_document(ev.document_id)
                    if doc:
                        v_res = validate_evidence_quotation(
                            doc.raw_text, ev.quote, ev.char_offset_start, ev.char_offset_end
                        )
                        if not v_res.is_valid:
                            all_quotes_valid = False

                seg_conf = compute_claim_confidence(
                    claim=claim,
                    evidence_list=active_evidence,
                    has_contradiction=len(contra_claims) > 0,
                    all_quotes_valid=all_quotes_valid,
                )

                segment = PathSegment(
                    from_entity=current_entity,
                    claim=claim,
                    to_entity=next_entity,
                    direction=step.direction,
                    evidence=active_evidence,
                    segment_confidence=seg_conf,
                    is_disputed=len(contra_claims) > 0,
                    contradictions=contra_claims,
                )

                search_step(
                    current_entity=next_entity,
                    step_idx=step_idx + 1,
                    current_segments=current_segments + [segment],
                    visited_entity_ids=visited_entity_ids | {next_entity.id},
                )

        search_step(
            current_entity=start_entity,
            step_idx=0,
            current_segments=[],
            visited_entity_ids={start_entity.id},
        )

        elapsed = (time.perf_counter() - start_time) * 1000

        # 4. Formulate response
        if not completed_paths:
            return ReasoningResult(
                query_id=query_id,
                status="insufficient_evidence",
                start_entity=start_entity,
                matching_entities=[],
                paths=[],
                hop_count=num_steps,
                conflicting_claims=[],
                evidence_records=[],
                execution_time_ms=round(elapsed, 2),
                confidence=0.0,
                explanation="No valid reasoning paths found within the evidentiary bounds of the knowledge graph.",
            )

        # Collect unique matching entities and evidence
        matching_map: Dict[str, Entity] = {}
        all_evidence: Dict[str, Evidence] = {}
        all_conflicts: Dict[str, Claim] = {}
        has_disputes = False

        for path in completed_paths:
            matching_map[path.terminal_entity.id] = path.terminal_entity
            for seg in path.segments:
                if seg.is_disputed:
                    has_disputes = True
                for ev in seg.evidence:
                    all_evidence[ev.id] = ev
                for cc in seg.contradictions:
                    all_conflicts[cc.id] = cc

        overall_confidence = max((p.path_confidence for p in completed_paths), default=0.0)
        status = "contradiction_detected" if has_disputes else "success"

        summary_entities = ", ".join(e.canonical_name for e in matching_map.values())
        explanation = (
            f"Successfully established {len(completed_paths)} reasoning path(s) spanning {num_steps} hops. "
            f"Matching entities: {summary_entities}."
        )
        if has_disputes:
            explanation += " Note: One or more underlying claims are subject to active factual disputes."

        return ReasoningResult(
            query_id=query_id,
            status=status,
            start_entity=start_entity,
            matching_entities=list(matching_map.values()),
            paths=completed_paths,
            hop_count=num_steps,
            conflicting_claims=list(all_conflicts.values()),
            evidence_records=list(all_evidence.values()),
            execution_time_ms=round(elapsed, 2),
            confidence=round(overall_confidence, 4),
            explanation=explanation,
        )
