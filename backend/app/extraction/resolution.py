"""Deterministic Entity Resolution and Alias Normalization."""

import re
from typing import Dict, List, Optional

from backend.app.ontology.models import Entity, EntityType


def normalize_entity_name(name: str) -> str:
    """Standardizes casing and whitespace for entity matching."""
    norm = re.sub(r"\s+", " ", name.strip().lower())
    # Strip honorifics for matching purposes if beneficial
    return norm


def slugify_name(name: str) -> str:
    """Constructs a deterministic canonical ID slug from entity name."""
    clean = re.sub(r"[^\w\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "_", clean)
    return slug[:40]


class EntityResolutionResult:
    """Outcome of resolving an entity mention against the repository."""

    def __init__(
        self,
        entity_id: str,
        canonical_name: str,
        entity_type: EntityType,
        is_new: bool,
        aliases: List[str] = None,
        ambiguous_candidates: List[str] = None,
    ):
        self.entity_id = entity_id
        self.canonical_name = canonical_name
        self.entity_type = entity_type
        self.is_new = is_new
        self.aliases = aliases or []
        self.ambiguous_candidates = ambiguous_candidates or []


class EntityResolver:
    """Resolves raw entity mentions against existing knowledge graph entities

    using strict deterministic normalization and explicit alias registries.
    Never merges unrelated entities solely via fuzzy similarity.
    """

    def __init__(self, existing_entities: List[Entity]):
        self.canonical_map: Dict[str, Entity] = {}
        self.alias_map: Dict[str, Entity] = {}
        self.id_map: Dict[str, Entity] = {}

        for ent in existing_entities:
            self.id_map[ent.id] = ent
            norm_canon = normalize_entity_name(ent.canonical_name)
            self.canonical_map[norm_canon] = ent

            for alias in ent.aliases:
                norm_alias = normalize_entity_name(alias)
                self.alias_map[norm_alias] = ent

    def resolve(
        self,
        name: str,
        entity_type: EntityType,
        aliases: Optional[List[str]] = None,
    ) -> EntityResolutionResult:
        """Resolves an entity mention deterministically."""
        norm_name = normalize_entity_name(name)

        # 1. Check exact canonical match
        if norm_name in self.canonical_map:
            ent = self.canonical_map[norm_name]
            return EntityResolutionResult(
                entity_id=ent.id,
                canonical_name=ent.canonical_name,
                entity_type=ent.type,
                is_new=False,
                aliases=ent.aliases,
            )

        # 2. Check registered alias match
        if norm_name in self.alias_map:
            ent = self.alias_map[norm_name]
            return EntityResolutionResult(
                entity_id=ent.id,
                canonical_name=ent.canonical_name,
                entity_type=ent.type,
                is_new=False,
                aliases=ent.aliases,
            )

        # 3. Check if any supplied alias matches existing entities
        if aliases:
            for alias in aliases:
                norm_a = normalize_entity_name(alias)
                if norm_a in self.canonical_map:
                    ent = self.canonical_map[norm_a]
                    return EntityResolutionResult(
                        entity_id=ent.id,
                        canonical_name=ent.canonical_name,
                        entity_type=ent.type,
                        is_new=False,
                        aliases=ent.aliases,
                    )
                if norm_a in self.alias_map:
                    ent = self.alias_map[norm_a]
                    return EntityResolutionResult(
                        entity_id=ent.id,
                        canonical_name=ent.canonical_name,
                        entity_type=ent.type,
                        is_new=False,
                        aliases=ent.aliases,
                    )

        # 4. New entity creation
        new_id = f"ent_{slugify_name(name)}"
        new_entity = Entity(
            id=new_id,
            canonical_name=name.strip(),
            type=entity_type,
            aliases=aliases or [],
        )

        # Register in resolver indexes
        self.id_map[new_id] = new_entity
        self.canonical_map[norm_name] = new_entity
        if aliases:
            for a in aliases:
                self.alias_map[normalize_entity_name(a)] = new_entity

        return EntityResolutionResult(
            entity_id=new_id,
            canonical_name=name.strip(),
            entity_type=entity_type,
            is_new=True,
            aliases=aliases or [],
        )
