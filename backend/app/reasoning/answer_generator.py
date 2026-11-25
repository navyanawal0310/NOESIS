"""Grounded Answer Generation from Reasoning Results and Evidentiary Provenance."""

import time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.llm.base import BaseLLMProvider, LLMUnavailableError
from backend.app.reasoning.gap_detector import KnowledgeGap, KnowledgeGapDetector
from backend.app.reasoning.models import ReasoningResult, StructuredQueryPlan


class GroundedAnswer(BaseModel):
    """Provenance-backed answer synthesized strictly from verified graph evidence."""

    answer: str
    status: str
    confidence: float
    hop_count: int
    terminal_entities: List[str]
    supporting_document_ids: List[str]
    supporting_quotes: List[str]
    has_contradictions: bool
    contradiction_notes: List[str] = Field(default_factory=list)
    gap_diagnostics: Optional[KnowledgeGap] = None
    synthesized_by_llm: bool = False
    execution_time_ms: float = 0.0
    status_code: str = "SUCCESS"
    executed_plan: Optional[StructuredQueryPlan] = None
    latencies: Dict[str, float] = Field(default_factory=dict)


class GroundedAnswerGenerator:
    """Generates structured, provenance-constrained answers from ReasoningResult instances."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider

    def generate_answer(
        self,
        result: ReasoningResult,
        plan: StructuredQueryPlan,
        question: Optional[str] = None,
        use_llm: bool = False,
        gap_detector: Optional[KnowledgeGapDetector] = None,
        status_code: Optional[str] = None,
        latencies: Optional[Dict[str, float]] = None,
    ) -> GroundedAnswer:
        """Synthesizes a grounded answer from reasoning results and evidence quotations."""
        start_time = time.perf_counter()
        latencies_dict = dict(latencies or {})

        # Handle Insufficient Evidence
        if result.status == "insufficient_evidence":
            gap: Optional[KnowledgeGap] = None
            if gap_detector:
                gap = gap_detector.analyze_gap(plan=plan, result=result)

            diag = gap.diagnostic_message if gap else result.explanation
            answer_text = (
                f"Insufficient evidence in the knowledge graph. A factual conclusion cannot be established. "
                f"Diagnostic: {diag}"
            )
            elapsed = (time.perf_counter() - start_time) * 1000

            resolved_status_code = status_code or ("UNSUPPORTED_CONSTRAINT" if plan.temporal_constraint else "INSUFFICIENT_EVIDENCE")

            return GroundedAnswer(
                answer=answer_text,
                status="insufficient_evidence",
                status_code=resolved_status_code,
                confidence=0.0,
                hop_count=result.hop_count,
                terminal_entities=[],
                supporting_document_ids=[],
                supporting_quotes=[],
                has_contradictions=False,
                contradiction_notes=[],
                gap_diagnostics=gap,
                synthesized_by_llm=False,
                execution_time_ms=round(elapsed + result.execution_time_ms, 2),
                executed_plan=plan,
                latencies=latencies_dict,
            )

        # Extract verified facts
        matching_names = [e.canonical_name for e in result.matching_entities]
        supporting_docs = list({doc_id for path in result.paths for doc_id in path.supporting_document_ids})
        supporting_quotes = [ev.quote for ev in result.evidence_records]

        has_contradictions = len(result.conflicting_claims) > 0 or result.status == "contradiction_detected"
        contradiction_notes: List[str] = []
        if has_contradictions:
            for cc in result.conflicting_claims:
                contradiction_notes.append(
                    f"Claim {cc.id[:8]} asserting '{cc.predicate}' between {cc.subject_id} and {cc.object_id} is contested."
                )

        # 1. Deterministic template synthesis (baseline)
        start_name = result.start_entity.canonical_name if result.start_entity else plan.start_entity
        target_str = ", ".join(matching_names) if matching_names else "None"
        doc_str = ", ".join(supporting_docs) if supporting_docs else "None"

        deterministic_text = (
            f"Based on {result.hop_count}-hop evidentiary traversal from '{start_name}', "
            f"the verified target entity is: {target_str} (Confidence: {result.confidence:.2f}). "
            f"Grounding documents: [{doc_str}]."
        )
        if has_contradictions:
            deterministic_text += " Note: Active factual contradictions exist for one or more claims."

        synthesized_by_llm = False
        final_answer = deterministic_text

        # 2. Optional local LLM prose summary (constrained)
        if use_llm and self.llm_provider and self.llm_provider.is_available():
            try:
                system_prompt = (
                    "You are a strict evidence synthesist for the NOESIS scientific intelligence system. "
                    "Summarize the provided multi-hop reasoning path into 2-3 clear sentences answering the query. "
                    "CRITICAL CONSTRAINTS:\n"
                    "- State ONLY facts present in the verified entities and quotes provided.\n"
                    "- Do NOT invent, assume, or extrapolate outside the provided evidence.\n"
                    "- Explicitly mention the target entities, confidence score, and supporting document IDs.\n"
                    "- If contradictions are noted, explicitly mention them."
                )
                user_prompt = (
                    f"Query: {question or 'Find connection from ' + start_name}\n"
                    f"Start Entity: {start_name}\n"
                    f"Target Entities: {target_str}\n"
                    f"Hops: {result.hop_count}\n"
                    f"Confidence: {result.confidence:.2f}\n"
                    f"Supporting Documents: {doc_str}\n"
                    f"Contradictions: {contradiction_notes}\n"
                    f"Verified Quotations:\n" + "\n".join(f'- "{q}"' for q in supporting_quotes[:5])
                )
                resp = self.llm_provider.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )
                if resp.text and len(resp.text.strip()) > 10:
                    final_answer = resp.text.strip()
                    synthesized_by_llm = True
            except (LLMUnavailableError, Exception):
                # Graceful fallback to deterministic answer
                final_answer = deterministic_text
                synthesized_by_llm = False

        elapsed = (time.perf_counter() - start_time) * 1000

        resolved_status_code = status_code or ("CONTRADICTION_DETECTED" if has_contradictions else "SUCCESS")

        return GroundedAnswer(
            answer=final_answer,
            status=result.status,
            status_code=resolved_status_code,
            confidence=result.confidence,
            hop_count=result.hop_count,
            terminal_entities=matching_names,
            supporting_document_ids=supporting_docs,
            supporting_quotes=supporting_quotes,
            has_contradictions=has_contradictions,
            contradiction_notes=contradiction_notes,
            gap_diagnostics=None,
            synthesized_by_llm=synthesized_by_llm,
            execution_time_ms=round(elapsed + result.execution_time_ms, 2),
            executed_plan=plan,
            latencies=latencies_dict,
        )
