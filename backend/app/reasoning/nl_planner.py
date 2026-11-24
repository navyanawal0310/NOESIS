"""Natural-Language Query Planner with Entity-Anchored Query Compilation (EAQC)."""

import json
import logging
import re
import time
from typing import Dict, Optional, Tuple

from pydantic import ValidationError

from backend.app.graph.base import BaseGraphRepository
from backend.app.llm.base import BaseLLMProvider, LLMInferenceError, LLMUnavailableError
from backend.app.ontology.models import EntityType, Predicate
from backend.app.reasoning.entity_anchor import EntityAnchorResolver, EntityAnchorResult
from backend.app.reasoning.models import StructuredQueryPlan, TraversalStep

logger = logging.getLogger("noesis.reasoning.nl_planner")

ALLOWED_PREDICATES = {p.value for p in Predicate}


class EntityNotFoundError(ValueError):
    """Raised when an explicit entity mentioned in the query does not exist in the graph."""

    def __init__(self, mention: str, message: Optional[str] = None):
        self.mention = mention
        super().__init__(
            message or f"Entity '{mention}' referenced in query was not found in the knowledge graph."
        )


class AmbiguousEntityError(ValueError):
    """Raised when an entity mention in the query matches multiple distinct entities."""

    def __init__(self, candidates: list, message: Optional[str] = None):
        self.candidates = candidates
        super().__init__(
            message
            or f"Entity mention matches multiple candidates ambiguously: {[c.canonical_name for c in candidates]}"
        )


class QueryPlanningError(ValueError):
    """Raised when query plan generation fails schema or ontology validation."""

    pass


SYSTEM_PLANNER_PROMPT = """You are an expert graph query planner for the NOESIS Evidence Graph.
Translate the user's natural language question into a strict JSON StructuredQueryPlan.

AVAILABLE ENTITY TYPES:
PERSON, ORGANIZATION, TECHNOLOGY, PROJECT, PUBLICATION, LOCATION, CONCEPT

ALLOWED PREDICATES:
FOUNDED, WORKED_ON, DEVELOPED, EMPLOYED_BY, COLLABORATED_WITH, AUTHORED, PUBLISHED, ACQUIRED, FUNDED, LOCATED_IN, USES, DISPUTES

JSON SCHEMA:
{
  "start_entity": "<canonical entity name or entity ID>",
  "steps": [
    {
      "predicate": "<ONE_OF_THE_ALLOWED_PREDICATES>",
      "direction": "outgoing" | "incoming",
      "target_type": "<ENTITY_TYPE>" | null
    }
  ],
  "return_type": "<ENTITY_TYPE>" | null,
  "max_hops": 3
}

DIRECTION RULES:
- "who worked on [Project]" -> predicate: WORKED_ON, direction: incoming (from project back to person)
- "who founded [Organization]" -> predicate: FOUNDED, direction: incoming (from org back to person)
- "[Person] founded [Organization]" -> predicate: FOUNDED, direction: outgoing (from person to org)
- "[Organization] developed [Tech]" -> predicate: DEVELOPED, direction: outgoing (from org to tech)
- "technology developed by organization founded by researcher who worked on [Project]":
  Step 1: predicate WORKED_ON, direction incoming (reaches researcher)
  Step 2: predicate FOUNDED, direction outgoing (reaches organization)
  Step 3: predicate DEVELOPED, direction outgoing, target_type TECHNOLOGY (reaches technology)

RULES:
1. Output ONLY a valid raw JSON object. No Markdown fences, no explanation, no backticks.
2. The traversal must have 1 to 5 steps.
3. Every step's predicate MUST be chosen from the ALLOWED PREDICATES list.
4. Do NOT output Cypher, SQL, SPARQL, or arbitrary query code.
5. Use the provided anchored start entity.
"""


class NLQueryPlanner:
    """Translates natural language questions into verified StructuredQueryPlan instances using EAQC."""

    def __init__(
        self,
        repository: BaseGraphRepository,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.repo = repository
        self.llm_provider = llm_provider
        self.anchor_resolver = EntityAnchorResolver(repository)

    def plan_query(self, question: str) -> StructuredQueryPlan:
        """Translates question into a StructuredQueryPlan."""
        plan, _, _ = self.plan_query_with_telemetry(question)
        return plan

    def plan_query_with_telemetry(
        self, question: str
    ) -> Tuple[StructuredQueryPlan, str, Dict[str, float]]:
        """Translates question with EAQC mention resolution, prompt minimization, and latency telemetry.

        Returns:
            Tuple of (plan, status_code, latencies)
        """
        latencies: Dict[str, float] = {
            "entity_resolution_ms": 0.0,
            "llm_planning_ms": 0.0,
            "total_planning_ms": 0.0,
        }
        t_start = time.perf_counter()

        # Step 1: Deterministic Entity Mention Resolution (EAQC)
        t_ent_0 = time.perf_counter()
        anchor_res = self.anchor_resolver.resolve(question)
        latencies["entity_resolution_ms"] = round((time.perf_counter() - t_ent_0) * 1000, 2)

        if anchor_res.status == "ENTITY_NOT_FOUND":
            latencies["total_planning_ms"] = round((time.perf_counter() - t_start) * 1000, 2)
            raise EntityNotFoundError(anchor_res.unresolved_mention or "Unknown")

        if anchor_res.status == "AMBIGUOUS_ENTITY":
            latencies["total_planning_ms"] = round((time.perf_counter() - t_start) * 1000, 2)
            raise AmbiguousEntityError(anchor_res.candidate_entities)

        # Detect explicit temporal constraints in question (e.g., 'in 1995', 'during 2021-2023')
        temporal_match = re.search(
            r"\b(?:in|during|before|after|since)\s+(\d{4}(?:-\d{4})?)\b",
            question,
            re.IGNORECASE,
        )
        detected_temporal = temporal_match.group(1) if temporal_match else None

        # Step 2: Check for canonical semantic pattern match first (deterministic fast-path)
        pattern_plan = self._match_relational_patterns(question, anchor_res, detected_temporal)
        if pattern_plan:
            latencies["total_planning_ms"] = round((time.perf_counter() - t_start) * 1000, 2)
            return pattern_plan, "SUCCESS", latencies

        # Step 3: Local LLM Generation with Context Reduction & Anchor Locking
        if not self.llm_provider:
            raise LLMUnavailableError("No LLM provider configured for natural-language query planning.")

        if not self.llm_provider.is_available():
            raise LLMUnavailableError(
                f"Local LLM provider '{self.llm_provider.model_name}' is offline. "
                "Natural language query planning requires an active local LLM."
            )

        t_llm_0 = time.perf_counter()
        plan = self._generate_plan_with_llm(question, anchor_res, detected_temporal)
        latencies["llm_planning_ms"] = round((time.perf_counter() - t_llm_0) * 1000, 2)
        latencies["total_planning_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        return plan, "SUCCESS", latencies

    def _match_relational_patterns(
        self,
        question: str,
        anchor_res: EntityAnchorResult,
        detected_temporal: Optional[str],
    ) -> Optional[StructuredQueryPlan]:
        """Detects canonical multi-hop and single-hop question patterns deterministically."""
        if not anchor_res.matched_entity:
            return None

        ent = anchor_res.matched_entity
        q_clean = question.strip()

        # Pattern A: 3-Hop Chain: "What technology was developed by the organization founded by the researcher who worked on {Entity}?"
        # Also matches paraphrases like "technology created by the lab started by the scientist involved in {Entity}"
        three_hop_match = re.search(
            r"(?:technology|tech|software|system|engine|platform)\s+(?:was\s+)?(?:developed|created|built)\s+by\s+(?:the\s+)?(?:organization|org|company|lab|institute|firm)\s+(?:founded|started|established)\s+by\s+(?:the\s+)?(?:researcher|scientist|person|investigator)\s+(?:who\s+)?(?:worked\s+on|involved\s+in|contributed\s+to)",
            q_clean,
            re.IGNORECASE,
        )
        if three_hop_match:
            return StructuredQueryPlan(
                start_entity=ent.id,
                steps=[
                    TraversalStep(predicate="WORKED_ON", direction="incoming", target_type=EntityType.PERSON),
                    TraversalStep(predicate="FOUNDED", direction="outgoing", target_type=EntityType.ORGANIZATION),
                    TraversalStep(predicate="DEVELOPED", direction="outgoing", target_type=EntityType.TECHNOLOGY),
                ],
                return_type=EntityType.TECHNOLOGY,
                max_hops=3,
                temporal_constraint=detected_temporal,
            )

        # Pattern B: Direct single-hop "Who worked on {Entity}?" / "Who researched {Entity}?"
        if re.search(r"\bwho\s+(?:worked\s+on|researched|contributed\s+to|was\s+involved\s+in)\b", q_clean, re.IGNORECASE):
            return StructuredQueryPlan(
                start_entity=ent.id,
                steps=[
                    TraversalStep(predicate="WORKED_ON", direction="incoming", target_type=EntityType.PERSON)
                ],
                return_type=EntityType.PERSON,
                max_hops=1,
                temporal_constraint=detected_temporal,
            )

        # Pattern C: Direct single-hop "Who founded {Entity}?" / "Who started {Entity}?"
        if re.search(r"\bwho\s+(?:founded|started|established|created)\b", q_clean, re.IGNORECASE):
            return StructuredQueryPlan(
                start_entity=ent.id,
                steps=[
                    TraversalStep(predicate="FOUNDED", direction="incoming", target_type=EntityType.PERSON)
                ],
                return_type=EntityType.PERSON,
                max_hops=1,
                temporal_constraint=detected_temporal,
            )

        # Pattern D: Direct single-hop "What technology did {Entity} develop directly?"
        if re.search(r"\b(?:what\s+technology\s+did|what\s+tech\s+did)\s+.*\s+(?:develop|create|build)\s+directly\b", q_clean, re.IGNORECASE):
            return StructuredQueryPlan(
                start_entity=ent.id,
                steps=[
                    TraversalStep(predicate="DEVELOPED", direction="outgoing", target_type=EntityType.TECHNOLOGY)
                ],
                return_type=EntityType.TECHNOLOGY,
                max_hops=1,
                temporal_constraint=detected_temporal,
            )

        # Pattern E: Direct single-hop "What technology did {Entity} develop?" / "What did {Entity} develop?"
        if re.search(r"\bwhat\s+(?:technology\s+)?did\s+.*\s+(?:develop|create|build)\b", q_clean, re.IGNORECASE):
            return StructuredQueryPlan(
                start_entity=ent.id,
                steps=[
                    TraversalStep(predicate="DEVELOPED", direction="outgoing", target_type=EntityType.TECHNOLOGY)
                ],
                return_type=EntityType.TECHNOLOGY,
                max_hops=1,
                temporal_constraint=detected_temporal,
            )

        return None

    def _generate_plan_with_llm(
        self,
        question: str,
        anchor_res: EntityAnchorResult,
        detected_temporal: Optional[str],
    ) -> StructuredQueryPlan:
        """Invokes LLM with reduced anchor context and locks the starting entity."""
        if not self.llm_provider:
            raise LLMUnavailableError("No LLM provider configured.")

        # Provide focused anchor context rather than entire corpus
        if anchor_res.matched_entity:
            ent = anchor_res.matched_entity
            anchor_context = (
                f"Anchored Starting Entity (LOCKED):\n"
                f"- Name: {ent.canonical_name}\n"
                f"- ID: {ent.id}\n"
                f"- Type: {ent.type.value}\n"
                f"- Aliases: {ent.aliases}\n\n"
                f"INSTRUCTION: Your plan MUST use start_entity='{ent.id}' and trace outward from this entity."
            )
        else:
            anchor_context = "No specific starting entity detected in question. Identify the primary subject."

        user_prompt = (
            f"{anchor_context}\n\n"
            f"User Question: {question.strip()}\n\n"
            "Generate the strict JSON StructuredQueryPlan for this question:"
        )

        try:
            response = self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=SYSTEM_PLANNER_PROMPT,
                schema="json",
            )
        except Exception as e:
            logger.error("LLM query plan generation failed: %s", e)
            raise LLMInferenceError(f"Failed to generate query plan from LLM: {str(e)}") from e

        # Extract JSON from response
        raw_text = response.text.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if fence_match:
            json_str = fence_match.group(1)
        else:
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}")
            if json_start != -1 and json_end != -1:
                json_str = raw_text[json_start : json_end + 1]
            else:
                json_str = raw_text

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as jde:
            raise QueryPlanningError(f"LLM produced non-JSON output for query plan: {raw_text[:200]}") from jde

        # Reject any Cypher/SQL injection attempts
        for key in ("cypher", "query", "sql", "statement"):
            if key in parsed:
                raise QueryPlanningError("Direct query execution language detected; Cypher/SQL injection rejected.")

        # Anchor Locking: Force start_entity to the resolved anchor entity
        if anchor_res.matched_entity:
            parsed["start_entity"] = anchor_res.matched_entity.id

        # Normalize entity type strings
        valid_types = {et.value for et in EntityType}
        if parsed.get("return_type"):
            rt = str(parsed["return_type"]).upper().strip()
            parsed["return_type"] = next((et for et in valid_types if et in rt or rt[:5] in et), None)

        for step_dict in parsed.get("steps", []):
            if isinstance(step_dict, dict) and step_dict.get("target_type"):
                tt = str(step_dict["target_type"]).upper().strip()
                step_dict["target_type"] = next((et for et in valid_types if et in tt or tt[:5] in et), None)

        if detected_temporal and not parsed.get("temporal_constraint"):
            parsed["temporal_constraint"] = detected_temporal

        # Validate with Pydantic
        try:
            plan = StructuredQueryPlan(**parsed)
        except ValidationError as ve:
            raise QueryPlanningError(f"Generated query plan failed schema validation: {ve}") from ve

        # Validate predicates against ontology
        for idx, step in enumerate(plan.steps):
            pred_upper = step.predicate.strip().upper()
            if pred_upper not in ALLOWED_PREDICATES:
                raise QueryPlanningError(
                    f"Step {idx} uses unsupported predicate '{step.predicate}'. "
                    f"Allowed predicates: {sorted(ALLOWED_PREDICATES)}"
                )
            step.predicate = pred_upper

        return plan
