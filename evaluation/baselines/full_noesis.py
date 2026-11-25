"""Full NOESIS Architecture Wrapper for Benchmark Evaluation."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.llm.ollama import OllamaProvider
from backend.app.reasoning.answer_generator import GroundedAnswerGenerator
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.gap_detector import KnowledgeGapDetector
from backend.app.reasoning.models import StructuredQueryPlan, TraversalStep
from backend.app.reasoning.nl_planner import NLQueryPlanner
from datasets.synthetic.builder import populate_repository
from evaluation.baselines.base import BaselineExecutionResult, BaseReasoningSystem


class FullNOESISSystem(BaseReasoningSystem):
    """Full NOESIS architecture: EAQC + Provenance KG + Dialectical Verification."""

    def __init__(self, repository: Optional[InMemoryGraphRepository] = None):
        super().__init__(name="noesis")
        if repository is None:
            self.repo = InMemoryGraphRepository()
            populate_repository(self.repo)
        else:
            self.repo = repository

        self.engine = BoundedReasoningEngine(self.repo)
        self.gap_detector = KnowledgeGapDetector(self.repo)
        self.answer_generator = GroundedAnswerGenerator()
        self.llm_provider = OllamaProvider()
        self.planner = NLQueryPlanner(self.repo, llm_provider=self.llm_provider)

    def execute(
        self,
        question: str,
        case_id: Optional[str] = None,
        structured_plan: Optional[Dict[str, Any]] = None,
        mode: str = "structured",
        **kwargs: Any,
    ) -> BaselineExecutionResult:
        total_start = time.perf_counter()
        planning_ms = 0.0
        llm_calls = 0
        planning_route = "structured_direct"
        plan_obj: Optional[StructuredQueryPlan] = None

        if mode == "structured" and structured_plan:
            # Build Pydantic StructuredQueryPlan from oracle dict
            start_ent = structured_plan.get("start_entity", "")
            steps_data = structured_plan.get("steps", [])
            steps = [
                TraversalStep(
                    predicate=s["predicate"],
                    direction=s.get("direction", "outgoing"),
                    target_type=s.get("target_type"),
                )
                for s in steps_data
            ]
            plan_obj = StructuredQueryPlan(
                start_entity=start_ent,
                steps=steps,
                return_type=structured_plan.get("return_type"),
                max_hops=structured_plan.get("max_hops", len(steps)),
                temporal_constraint=structured_plan.get("temporal_constraint"),
            )
        else:
            # Natural language mode: compile plan via EAQC + NLQueryPlanner
            try:
                p_start = time.perf_counter()
                plan_tuple = self.planner.plan_query_with_telemetry(question)
                plan_obj, _, telemetry = plan_tuple
                planning_ms = telemetry.get("total_planning_ms", (time.perf_counter() - p_start) * 1000.0)
                planning_route = telemetry.get("planning_route", "llm_generated")
                llm_calls = telemetry.get("llm_calls", 1)
            except Exception as e:
                total_latency_ms = (time.perf_counter() - total_start) * 1000.0
                return BaselineExecutionResult(
                    system_name=self.name,
                    case_id=case_id,
                    question=question,
                    abstained=True,
                    latency_ms=total_latency_ms,
                    planning_ms=total_latency_ms,
                    llm_calls=0,
                    raw_response=f"Natural language query compilation failed: {e}",
                    metadata={"error": str(e)},
                )

        # Execute bounded graph traversal
        t_start = time.perf_counter()
        reasoning_result = self.engine.execute_query(plan_obj)
        graph_traversal_ms = (time.perf_counter() - t_start) * 1000.0

        status_code = "SUCCESS"
        if reasoning_result.status == "insufficient_evidence":
            if plan_obj.temporal_constraint:
                status_code = "UNSUPPORTED_CONSTRAINT"
            else:
                status_code = "INSUFFICIENT_EVIDENCE"
        elif reasoning_result.status == "contradiction_detected":
            status_code = "CONTRADICTION_DETECTED"

        contradiction_detected = (reasoning_result.status == "contradiction_detected")

        # Grounded answer generation
        grounded_answer = self.answer_generator.generate_answer(
            result=reasoning_result,
            plan=plan_obj,
            question=question,
            use_llm=False,
            gap_detector=self.gap_detector,
            status_code=status_code,
            latencies={"traversal_ms": graph_traversal_ms, "planning_ms": planning_ms},
            planning_route=planning_route,
            cache_hit=(planning_route == "cached_plan"),
            llm_calls=llm_calls,
            model_id="qwen3:4b" if llm_calls > 0 else "deterministic_rule_engine",
        )

        total_latency_ms = (time.perf_counter() - total_start) * 1000.0

        # Extract answer entities and paths
        answer_entities = list(grounded_answer.terminal_entities)
        path_reprs = []
        for p in reasoning_result.paths:
            start_node = p.segments[0].from_entity.canonical_name if p.segments else plan_obj.start_entity
            nodes = [start_node]
            for s in p.segments:
                nodes.append(s.to_entity.canonical_name)
            path_reprs.append(nodes)

        citations = list(grounded_answer.supporting_document_ids)

        # Check for abstention
        abstained = (
            grounded_answer.status_code in ["INSUFFICIENT_EVIDENCE", "UNSUPPORTED_CONSTRAINT"]
            or len(grounded_answer.terminal_entities) == 0
            or "insufficient evidence" in grounded_answer.answer.lower()
        )

        return BaselineExecutionResult(
            system_name=self.name,
            case_id=case_id,
            question=question,
            answer_entities=answer_entities,
            reasoning_paths=path_reprs,
            predicates=[s.predicate for s in plan_obj.steps],
            directions=[s.direction for s in plan_obj.steps],
            citations=citations,
            contradiction_detected=contradiction_detected,
            abstained=abstained,
            latency_ms=total_latency_ms,
            graph_traversal_ms=graph_traversal_ms,
            planning_ms=planning_ms,
            llm_calls=llm_calls,
            raw_response=grounded_answer.answer,
            metadata={
                "confidence": grounded_answer.confidence,
                "planning_route": planning_route,
                "plan_start_entity": plan_obj.start_entity,
                "status_code": grounded_answer.status_code,
            },
        )
