"""Ontology package."""

from .models import Claim, Document, Entity, EntityType, Evidence, Polarity, Predicate

__all__ = [
    "Entity",
    "EntityType",
    "Claim",
    "Evidence",
    "Document",
    "Polarity",
    "Predicate",
]
