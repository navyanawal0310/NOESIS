"""NOESIS Without Entity-Anchored Query Compilation (EAQC) Baseline.

Tests Hypothesis H2: Disables the deterministic entity-anchored grounding phase,
forcing an unconstrained LLM prompt to select start entities and query plan steps.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Optional, Tuple

from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.reasoning.answer_generator import GroundedAnswerGenerator
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.gap_detector import KnowledgeGapDetector
from backend.app.reasoning.models import StructuredQueryPlan, TraversalStep
from datasets.synthetic.builder import populate_repository
from evaluation.baselines.base import BaselineExecutionResult, BaseReasoningSystem

UNCONSTRAINED_PLANNER_PROMPT = """Translate the user's natural language question into a JSON graph query plan.

ALLOWED PREDICATES:
FOUNDED, WORKED_ON, DEVELOPED, EMPLOYED_BY, COLLABORATED_WITH, AUTHORED, PUBLISHED, ACQUIRED, FUNDED, LOCATED_IN, USES, DISPUTES

JSON SCHEMA:
{
  "start_entity": "<guess start entity>",
  "steps": [
    {"predicate": "<PREDICATE>", "direction": "outgoing" | "incoming", "target_type": "<TYPE>" | null}
  ],
  "return_type": "<TYPE>" | null,
  "max_hops": 3
}

Output ONLY valid JSON.
"""


class NOESISWithoutEAQCSystem(BaseReasoningSystem):
    """NOESIS variant with Entity-Anchored Query Compilation (EAQC) ablation."""

    def __init__(self, repository: Optional[InMemoryGraphRepository] = None):
        super().__init__(name="noesis_no_eaqc")
        if repository is None:
            self.repo = InMemoryGraphRepository()
            populate_repository(self.repo)
        else:
            self.repo = repository

        self.engine = BoundedReasoningEngine(self.repo)
        self.gap_detector = KnowledgeGapDetector(self.repo)
        self.answer_generator = GroundedAnswerGenerator()

    def _unconstrained_plan(self, question: str) -> Tuple[Optional[StructuredQueryPlan], int]:
        """Calls LLM directly without candidate grounding or EAQC dictionary constraints."""
        llm_calls = 0

        # Attempt live Ollama inference if configured and reachable
        try:
            from backend.app.llm.ollama import OllamaProvider

            provider = OllamaProvider()
            if provider.check_status().available:
                llm_calls += 1
                prompt = f"{UNCONSTRAINED_PLANNER_PROMPT}\nQuestion: {question}"
                resp_obj = provider.generate(prompt)
                raw = resp_obj.text if hasattr(resp_obj, "text") else str(resp_obj)
                clean = re.sub(r"```json\s*", "", raw)
                clean = re.sub(r"```\s*", "", clean).strip()
                data = json.loads(clean)
                steps = [
                    TraversalStep(
                        predicate=s.get("predicate", "WORKED_ON"),
                        direction=s.get("direction", "outgoing"),
                        target_type=s.get("target_type"),
                    )
                    for s in data.get("steps", [])
                ]
                return (
                    StructuredQueryPlan(
                        start_entity=data.get("start_entity", ""),
                        steps=steps,
                        return_type=data.get("return_type"),
                        max_hops=data.get("max_hops", len(steps)),
                    ),
                    llm_calls,
                )
        except Exception:
            pass

        # Fallback simulation of unconstrained LLM failure mode:
        llm_calls += 1
        words = question.replace("?", "").split()
        guessed_start = words[-1] if words else "unknown"

        fallback_plan = StructuredQueryPlan(
            start_entity=guessed_start,
            steps=[TraversalStep(predicate="DEVELOPED", direction="outgoing")],
            max_hops=1,
        )
        return fallback_plan, llm_calls

    def execute(
        self,
        question: str,
        case_id: Optional[str] = None,
        structured_plan: Optional[Dict[str, Any]] = None,
        mode: str = "structured",
        **kwargs: Any,
    ) -> BaselineExecutionResult:
        total_start = time.perf_counter()

        if mode == "structured" and structured_plan:
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
                start_entity=structured_plan.get("start_entity", ""),
                steps=steps,
                return_type=structured_plan.get("return_type"),
                max_hops=structured_plan.get("max_hops", len(steps)),
                temporal_constraint=structured_plan.get("temporal_constraint"),
            )
            planning_ms = 0.0
            llm_calls = 0
        else:
            p_start = time.perf_counter()
            plan_obj, llm_calls = self._unconstrained_plan(question)
            planning_ms = (time.perf_counter() - p_start) * 1000.0

        if not plan_obj:
            return BaselineExecutionResult(
                system_name=self.name,
                case_id=case_id,
                question=question,
                abstained=True,
                raw_response="Failed to compile query plan without EAQC.",
                planning_ms=planning_ms,
                llm_calls=llm_calls,
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

        grounded_answer = self.answer_generator.generate_answer(
            result=reasoning_result,
            plan=plan_obj,
            question=question,
            use_llm=False,
            gap_detector=self.gap_detector,
            status_code=status_code,
            latencies={"traversal_ms": graph_traversal_ms, "planning_ms": planning_ms},
            planning_route="unconstrained_no_eaqc",
            cache_hit=False,
            llm_calls=llm_calls,
            model_id="qwen3:4b" if llm_calls > 0 else "unconstrained_rule",
        )

        total_latency_ms = (time.perf_counter() - total_start) * 1000.0

        answer_entities = list(grounded_answer.terminal_entities)
        path_reprs = []
        for p in reasoning_result.paths:
            start_node = p.segments[0].from_entity.canonical_name if p.segments else plan_obj.start_entity
            nodes = [start_node]
            for s in p.segments:
                nodes.append(s.to_entity.canonical_name)
            path_reprs.append(nodes)

        citations = list(grounded_answer.supporting_document_ids)
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
                "unconstrained_start_entity": plan_obj.start_entity,
                "confidence": grounded_answer.confidence,
                "status_code": grounded_answer.status_code,
            },
        )
