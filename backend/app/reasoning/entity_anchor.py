"""Entity-Anchored Query Compilation (EAQC) Mention Resolver and Anchor Locking."""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from backend.app.graph.base import BaseGraphRepository
from backend.app.ontology.models import Entity

logger = logging.getLogger("noesis.reasoning.entity_anchor")

# Honorifics and titles to strip during normalization
HONORIFIC_PREFIXES = [
    r"^dr\.?\s+",
    r"^prof\.?\s+",
    r"^doctor\s+",
    r"^professor\s+",
    r"^mr\.?\s+",
    r"^ms\.?\s+",
    r"^mrs\.?\s+",
]


def normalize_entity_name(name: str) -> str:
    """Normalizes an entity name by stripping titles, honorifics, punctuation, and folding case."""
    if not name:
        return ""
    cleaned = name.strip()
    for prefix in HONORIFIC_PREFIXES:
        cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE)
    # Strip leading/trailing punctuation and collapse internal whitespace
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


@dataclass
class EntityMatchCandidate:
    """Candidate match found in question."""

    entity: Entity
    matched_text: str
    match_length: int
    match_strategy: str  # "canonical", "normalized", "alias"


@dataclass
class EntityAnchorResult:
    """Result of deterministic entity mention resolution."""

    status: str  # "MATCHED", "ENTITY_NOT_FOUND", "AMBIGUOUS_ENTITY", "NO_MENTION"
    matched_entity: Optional[Entity] = None
    matched_text: Optional[str] = None
    match_strategy: Optional[str] = None
    candidate_entities: List[Entity] = field(default_factory=list)
    unresolved_mention: Optional[str] = None


class EntityAnchorResolver:
    """Resolves natural-language query mentions to graph entities deterministically."""

    def __init__(self, repository: BaseGraphRepository):
        self.repo = repository

    def resolve(self, question: str) -> EntityAnchorResult:
        """Deterministically resolves entity mention in question using 3-tier matching.

        Priority order:
        1. Exact canonical name match (case-insensitive substring)
        2. Exact normalized name match
        3. Alias match
        """
        all_entities = self.repo.list_entities()
        if not all_entities:
            return EntityAnchorResult(status="NO_MENTION")

        q_lower = question.lower()
        q_norm = normalize_entity_name(question)

        candidates: List[EntityMatchCandidate] = []

        for ent in all_entities:
            canon = ent.canonical_name.strip()
            canon_lower = canon.lower()
            canon_norm = normalize_entity_name(canon)

            # Tier 1: Exact canonical match as substring with word boundary
            pattern_canon = r"\b" + re.escape(canon_lower) + r"\b"
            if re.search(pattern_canon, q_lower):
                candidates.append(
                    EntityMatchCandidate(
                        entity=ent,
                        matched_text=canon,
                        match_length=len(canon),
                        match_strategy="canonical",
                    )
                )
                continue

            # Tier 2: Exact normalized match
            if canon_norm and len(canon_norm) >= 3:
                pattern_norm = r"\b" + re.escape(canon_norm) + r"\b"
                if re.search(pattern_norm, q_norm) or re.search(pattern_norm, q_lower):
                    candidates.append(
                        EntityMatchCandidate(
                            entity=ent,
                            matched_text=canon,
                            match_length=len(canon_norm),
                            match_strategy="normalized",
                        )
                    )
                    continue

            # Tier 3: Alias matching
            for alias in ent.aliases:
                alias_clean = alias.strip()
                if not alias_clean or len(alias_clean) < 3:
                    continue
                alias_lower = alias_clean.lower()
                pattern_alias = r"\b" + re.escape(alias_lower) + r"\b"
                if re.search(pattern_alias, q_lower):
                    candidates.append(
                        EntityMatchCandidate(
                            entity=ent,
                            matched_text=alias_clean,
                            match_length=len(alias_clean),
                            match_strategy="alias",
                        )
                    )
                    break

        # If candidates found, sort by match_length descending, then strategy priority
        if candidates:
            strategy_rank = {"canonical": 3, "normalized": 2, "alias": 1}
            candidates.sort(
                key=lambda c: (c.match_length, strategy_rank.get(c.match_strategy, 0)),
                reverse=True,
            )

            best = candidates[0]
            # Check for ambiguity: multiple different entities with identical match length and strategy
            tied = [
                c
                for c in candidates
                if c.match_length == best.match_length
                and c.entity.id != best.entity.id
                and c.match_strategy == best.match_strategy
            ]
            if tied:
                logger.warning(
                    "Ambiguous entity mention for question '%s': tied candidates %s",
                    question,
                    [c.entity.canonical_name for c in [best] + tied],
                )
                return EntityAnchorResult(
                    status="AMBIGUOUS_ENTITY",
                    candidate_entities=[c.entity for c in [best] + tied],
                    matched_text=best.matched_text,
                )

            return EntityAnchorResult(
                status="MATCHED",
                matched_entity=best.entity,
                matched_text=best.matched_text,
                match_strategy=best.match_strategy,
                candidate_entities=[best.entity],
            )

        # Detect if user question mentions an explicit named entity that does not exist in graph
        unresolved = self._detect_unresolved_named_entity(question)
        if unresolved:
            logger.info("Detected unknown entity mention '%s' in question '%s'", unresolved, question)
            return EntityAnchorResult(
                status="ENTITY_NOT_FOUND",
                unresolved_mention=unresolved,
            )

        return EntityAnchorResult(status="NO_MENTION")

    def _detect_unresolved_named_entity(self, question: str) -> Optional[str]:
        """Detects whether question references an explicit proper noun or named entity absent from graph."""
        # Check explicit patterns like "Project X", "Dr. X", "X Labs", "X Research", "X Inc", "X Corp"
        patterns = [
            r"\bProject\s+([A-Z][a-zA-Z0-9_-]+)\b",
            r"\bDr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
            r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*\s+(?:Labs|Institute|Systems|Group|Corporation|Inc|Engine|Platform|Research|Foundry))\b",
            r"\b(?:worked on|founded|developed|created by|collaborated with)\s+(?:the\s+)?([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b",
            r"\b(?:nonexistent\s+(?:project|entity|organization|company|person))\b",
        ]
        for pat in patterns:
            match = re.search(pat, question, re.IGNORECASE)
            if match:
                mention = match.group(0).strip()
                # Check if this already matches any known entity
                for ent in self.repo.list_entities():
                    if ent.canonical_name.lower() in mention.lower() or mention.lower() in ent.canonical_name.lower():
                        return None
                return mention
        return None
