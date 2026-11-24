"""Natural-Language Query Planner for Bounded Graph Traversal."""

import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from backend.app.graph.base import BaseGraphRepository
from backend.app.llm.base import BaseLLMProvider, LLMInferenceError, LLMUnavailableError
from backend.app.ontology.models import Predicate
from backend.app.reasoning.models import StructuredQueryPlan

logger = logging.getLogger("noesis.reasoning.nl_planner")

ALLOWED_PREDICATES = {p.value for p in Predicate}

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

RULES:
1. Output ONLY a valid raw JSON object. No Markdown fences, no explanation, no backticks.
2. The traversal must have 1 to 5 steps.
3. Every step's predicate MUST be chosen from the ALLOWED PREDICATES list.
4. Do NOT output Cypher, SQL, SPARQL, or arbitrary query code.
5. Identify the primary subject entity mentioned in the query as 'start_entity'.
"""


class NLQueryPlanner:
    """Translates natural language questions into validated StructuredQueryPlan instances."""

    def __init__(
        self,
        repository: BaseGraphRepository,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.repo = repository
        self.llm_provider = llm_provider

    def _get_candidate_entities_prompt(self, limit: int = 25) -> str:
        entities = self.repo.list_entities()[:limit]
        return ", ".join(f"{e.canonical_name} ({e.type.value})" for e in entities)

    def plan_query(self, question: str) -> StructuredQueryPlan:
        """Translates a natural language question into a verified StructuredQueryPlan.

        Raises:
            LLMUnavailableError: If the local LLM is offline or not configured.
            ValueError: If the generated plan is malformed or violates ontology constraints.
        """
        if not self.llm_provider:
            raise LLMUnavailableError("No LLM provider configured for natural-language query planning.")

        if not self.llm_provider.is_available():
            raise LLMUnavailableError(
                f"Local LLM provider '{self.llm_provider.model_name}' is offline. "
                "Natural language query planning requires an active local LLM."
            )

        candidate_entities = self._get_candidate_entities_prompt()
        user_prompt = (
            f"Known entities in graph:\n{candidate_entities}\n\n"
            f"User Question: {question.strip()}\n\n"
            "Generate the JSON StructuredQueryPlan for this question:"
        )

        try:
            response = self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=SYSTEM_PLANNER_PROMPT,
            )
        except Exception as e:
            logger.error("LLM query plan generation failed: %s", e)
            raise LLMInferenceError(f"Failed to generate query plan from LLM: {str(e)}") from e

        # Extract JSON from response
        raw_text = response.text.strip()
        # Strip potential markdown code fences ```json ... ```
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
            raise ValueError(f"LLM produced non-JSON output for query plan: {raw_text[:200]}") from jde

        # Reject any Cypher/SQL injection attempts
        for key in ("cypher", "query", "sql", "statement"):
            if key in parsed:
                raise ValueError("Direct query execution language detected; Cypher/SQL injection rejected.")

        # Validate with Pydantic
        try:
            plan = StructuredQueryPlan(**parsed)
        except ValidationError as ve:
            raise ValueError(f"Generated query plan failed schema validation: {ve}") from ve

        # Validate predicates against ontology
        for idx, step in enumerate(plan.steps):
            pred_upper = step.predicate.strip().upper()
            if pred_upper not in ALLOWED_PREDICATES:
                raise ValueError(
                    f"Step {idx} uses unsupported predicate '{step.predicate}'. "
                    f"Allowed predicates: {sorted(ALLOWED_PREDICATES)}"
                )
            step.predicate = pred_upper

        return plan
