"""Standard Knowledge Graph (Direct Triples) Baseline.

Executes direct entity-to-entity triple traversal without claim reification,
evidence provenance aggregation, contradiction detection, or counterfactual ablation.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.graph.in_memory import InMemoryGraphRepository
from datasets.synthetic.builder import populate_repository
from evaluation.baselines.base import BaselineExecutionResult, BaseReasoningSystem


class StandardKGSystem(BaseReasoningSystem):
    """Standard Direct-Triple KG traversal baseline."""

    def __init__(self, repository: Optional[InMemoryGraphRepository] = None):
        super().__init__(name="standard_kg")
        if repository is None:
            self.repo = InMemoryGraphRepository()
            populate_repository(self.repo)
        else:
            self.repo = repository

        # Build raw directed adjacency list: subj -> [(pred, obj_id)] and obj -> [(pred, subj_id)]
        self.outgoing_adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.incoming_adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.entity_names: Dict[str, str] = {}

        self._build_triple_index()

    def _build_triple_index(self) -> None:
        for ent in self.repo.list_entities():
            self.entity_names[ent.id] = ent.canonical_name

        for claim in self.repo.list_claims():
            if claim.polarity.lower() == "affirmed":
                self.outgoing_adj[claim.subject_id].append((claim.predicate.upper(), claim.object_id))
                self.incoming_adj[claim.object_id].append((claim.predicate.upper(), claim.subject_id))

    def _resolve_start(self, identifier: str) -> Optional[str]:
        target = identifier.strip().lower()
        for eid, name in self.entity_names.items():
            if eid.lower() == target or name.lower() == target:
                return eid
        for ent in self.repo.list_entities():
            for alias in ent.aliases:
                if alias.lower() == target:
                    return ent.id
        return None

    def execute(
        self,
        question: str,
        case_id: Optional[str] = None,
        structured_plan: Optional[Dict[str, Any]] = None,
        mode: str = "structured",
        **kwargs: Any,
    ) -> BaselineExecutionResult:
        total_start = time.perf_counter()

        if not structured_plan:
            return BaselineExecutionResult(
                system_name=self.name,
                case_id=case_id,
                question=question,
                abstained=True,
                raw_response="Standard KG baseline requires structured query plan steps.",
            )

        start_raw = structured_plan.get("start_entity", "")
        start_id = self._resolve_start(start_raw)
        steps = structured_plan.get("steps", [])

        if not start_id or not steps:
            return BaselineExecutionResult(
                system_name=self.name,
                case_id=case_id,
                question=question,
                abstained=True,
                raw_response=f"Unable to resolve start entity: '{start_raw}'",
            )

        t_start = time.perf_counter()

        # Multi-step BFS traversal across raw triples
        # Queue holds: (current_node_id, current_step_idx, path_nodes)
        queue: deque[Tuple[str, int, List[str]]] = deque([(start_id, 0, [start_id])])
        terminal_nodes: Set[str] = set()
        executed_paths: List[List[str]] = []

        while queue:
            curr_id, step_idx, path_so_far = queue.popleft()

            if step_idx == len(steps):
                terminal_nodes.add(curr_id)
                executed_paths.append(path_so_far)
                continue

            step = steps[step_idx]
            pred = step["predicate"].strip().upper()
            direction = step.get("direction", "outgoing").strip().lower()

            candidates: List[Tuple[str, str]]
            if direction == "outgoing":
                candidates = self.outgoing_adj.get(curr_id, [])
            else:
                candidates = self.incoming_adj.get(curr_id, [])

            for c_pred, next_id in candidates:
                if c_pred == pred and next_id not in path_so_far:  # Prevent immediate cycles
                    queue.append((next_id, step_idx + 1, path_so_far + [next_id]))

        graph_traversal_ms = (time.perf_counter() - t_start) * 1000.0
        total_latency_ms = (time.perf_counter() - total_start) * 1000.0

        answer_entities = [self.entity_names.get(tid, tid) for tid in terminal_nodes]
        path_name_reprs = [
            [self.entity_names.get(nid, nid) for nid in p]
            for p in executed_paths
        ]

        abstained = (len(answer_entities) == 0)

        return BaselineExecutionResult(
            system_name=self.name,
            case_id=case_id,
            question=question,
            answer_entities=answer_entities,
            reasoning_paths=path_name_reprs,
            predicates=[s["predicate"] for s in steps],
            directions=[s.get("direction", "outgoing") for s in steps],
            citations=[],  # Standard triple stores have no evidence provenance
            contradiction_detected=False,  # Standard triple stores do not detect contradictions
            abstained=abstained,
            latency_ms=total_latency_ms,
            graph_traversal_ms=graph_traversal_ms,
            planning_ms=0.0,
            llm_calls=0,
            raw_response=f"Found {len(answer_entities)} entity matches via direct triple traversal.",
            metadata={"terminal_ids": list(terminal_nodes)},
        )
