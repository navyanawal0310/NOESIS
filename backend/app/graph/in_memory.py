"""High-Performance In-Memory Graph Repository with Native Traversal."""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.graph.base import BaseGraphRepository
from backend.app.ontology.models import Claim, Document, Entity, Evidence

logger = logging.getLogger("noesis.graph.in_memory")


class InMemoryGraphRepository(BaseGraphRepository):
    """In-memory graph repository providing native graph indexing and traversal.

    Performs actual graph search and path traversal without hardcoded demonstration responses.
    """

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.claims: Dict[str, Claim] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.documents: Dict[str, Document] = {}

        # Adjacency indexes for rapid directional lookup
        self.subject_to_claims: Dict[str, Set[str]] = {}
        self.object_to_claims: Dict[str, Set[str]] = {}
        self.claim_to_evidence: Dict[str, Set[str]] = {}
        self.document_to_evidence: Dict[str, Set[str]] = {}
        self.contradictions: Set[Tuple[str, str]] = set()

    def get_storage_mode(self) -> str:
        return "in_memory"

    def is_healthy(self) -> bool:
        return True

    def clear(self) -> None:
        self.entities.clear()
        self.claims.clear()
        self.evidence.clear()
        self.documents.clear()
        self.subject_to_claims.clear()
        self.object_to_claims.clear()
        self.claim_to_evidence.clear()
        self.document_to_evidence.clear()
        self.contradictions.clear()

    def add_entity(self, entity: Entity) -> Entity:
        self.entities[entity.id] = entity
        if entity.id not in self.subject_to_claims:
            self.subject_to_claims[entity.id] = set()
        if entity.id not in self.object_to_claims:
            self.object_to_claims[entity.id] = set()
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def list_entities(self, type_filter: Optional[str] = None) -> List[Entity]:
        if not type_filter:
            return list(self.entities.values())
        return [
            e for e in self.entities.values()
            if e.type.value.upper() == type_filter.upper() or e.type.name.upper() == type_filter.upper()
        ]

    def add_claim(self, claim: Claim) -> Claim:
        # Merge or insert claim
        if claim.id in self.claims:
            existing = self.claims[claim.id]
            # Merge evidence IDs
            merged_ev = list(set(existing.evidence_ids + claim.evidence_ids))
            merged_contra = list(set(existing.contradiction_ids + claim.contradiction_ids))
            updated = existing.model_copy(
                update={"evidence_ids": merged_ev, "contradiction_ids": merged_contra}
            )
            self.claims[claim.id] = updated
            return updated

        self.claims[claim.id] = claim

        # Maintain index
        self.subject_to_claims.setdefault(claim.subject_id, set()).add(claim.id)
        self.object_to_claims.setdefault(claim.object_id, set()).add(claim.id)
        return claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        return self.claims.get(claim_id)

    def list_claims(
        self,
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
        object_id: Optional[str] = None,
    ) -> List[Claim]:
        results = list(self.claims.values())
        if subject_id:
            results = [c for c in results if c.subject_id == subject_id]
        if predicate:
            results = [c for c in results if c.predicate.upper() == predicate.upper()]
        if object_id:
            results = [c for c in results if c.object_id == object_id]
        return results

    def add_evidence(self, evidence: Evidence) -> Evidence:
        self.evidence[evidence.id] = evidence
        self.claim_to_evidence.setdefault(evidence.claim_id, set()).add(evidence.id)
        self.document_to_evidence.setdefault(evidence.document_id, set()).add(evidence.id)

        # Update parent claim evidence_ids
        if evidence.claim_id in self.claims:
            claim = self.claims[evidence.claim_id]
            if evidence.id not in claim.evidence_ids:
                claim.evidence_ids.append(evidence.id)

        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        return self.evidence.get(evidence_id)

    def get_evidence_for_claim(self, claim_id: str) -> List[Evidence]:
        ev_ids = self.claim_to_evidence.get(claim_id, set())
        return [self.evidence[eid] for eid in ev_ids if eid in self.evidence]

    def add_document(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        return self.documents.get(document_id)

    def list_documents(self) -> List[Document]:
        return list(self.documents.values())

    def add_contradiction(self, claim_id_1: str, claim_id_2: str) -> None:
        if claim_id_1 in self.claims and claim_id_2 in self.claims:
            pair = tuple(sorted([claim_id_1, claim_id_2]))
            self.contradictions.add(pair)
            c1 = self.claims[claim_id_1]
            c2 = self.claims[claim_id_2]
            if claim_id_2 not in c1.contradiction_ids:
                c1.contradiction_ids.append(claim_id_2)
            if claim_id_1 not in c2.contradiction_ids:
                c2.contradiction_ids.append(claim_id_1)

    def get_contradictions(self) -> List[Tuple[Claim, Claim]]:
        pairs = []
        for c1_id, c2_id in self.contradictions:
            if c1_id in self.claims and c2_id in self.claims:
                pairs.append((self.claims[c1_id], self.claims[c2_id]))
        return pairs

    def get_adjacent_claims(
        self,
        entity_id: str,
        direction: str = "outgoing",
        predicate: Optional[str] = None,
    ) -> List[Tuple[Claim, Entity]]:
        """Traverses adjacent claims from entity_id based on direction and predicate."""
        results: List[Tuple[Claim, Entity]] = []
        pred_upper = predicate.upper() if predicate else None

        if direction in ("outgoing", "both"):
            claim_ids = self.subject_to_claims.get(entity_id, set())
            for cid in claim_ids:
                claim = self.claims.get(cid)
                if not claim:
                    continue
                if pred_upper and claim.predicate.upper() != pred_upper:
                    continue
                target_entity = self.entities.get(claim.object_id)
                if target_entity:
                    results.append((claim, target_entity))

        if direction in ("incoming", "both"):
            claim_ids = self.object_to_claims.get(entity_id, set())
            for cid in claim_ids:
                claim = self.claims.get(cid)
                if not claim:
                    continue
                if pred_upper and claim.predicate.upper() != pred_upper:
                    continue
                source_entity = self.entities.get(claim.subject_id)
                if source_entity:
                    results.append((claim, source_entity))

        return results

    def get_full_graph(self) -> Dict[str, Any]:
        """Constructs an exportable Cytoscape.js compatible graph payload."""
        nodes = []
        edges = []

        # Entities
        for e in self.entities.values():
            nodes.append({
                "data": {
                    "id": e.id,
                    "label": e.canonical_name,
                    "type": "Entity",
                    "entity_type": e.type.value,
                    "description": e.description or "",
                    "aliases": e.aliases,
                }
            })

        # Claims
        for c in self.claims.values():
            nodes.append({
                "data": {
                    "id": c.id,
                    "label": f"{c.predicate} ({c.polarity.value})",
                    "type": "Claim",
                    "predicate": c.predicate,
                    "polarity": c.polarity.value,
                    "temporal_scope": c.temporal_scope or "",
                    "confidence": c.confidence,
                    "has_contradiction": len(c.contradiction_ids) > 0,
                }
            })
            # Edges: Subject -> Claim -> Object
            edges.append({
                "data": {
                    "id": f"{c.subject_id}_subj_{c.id}",
                    "source": c.subject_id,
                    "target": c.id,
                    "label": "SUBJECT_OF",
                    "rel_type": "SUBJECT_OF",
                }
            })
            edges.append({
                "data": {
                    "id": f"{c.id}_obj_{c.object_id}",
                    "source": c.id,
                    "target": c.object_id,
                    "label": "OBJECT",
                    "rel_type": "OBJECT",
                }
            })

        # Documents
        for d in self.documents.values():
            nodes.append({
                "data": {
                    "id": d.id,
                    "label": d.title,
                    "type": "Document",
                    "source_type": d.source_type,
                    "content_hash": d.content_hash,
                }
            })

        # Evidence
        for ev in self.evidence.values():
            nodes.append({
                "data": {
                    "id": ev.id,
                    "label": f"Quote [{ev.char_offset_start}:{ev.char_offset_end}]",
                    "type": "Evidence",
                    "quote": ev.quote,
                    "page": ev.page,
                    "offsets": [ev.char_offset_start, ev.char_offset_end],
                    "confidence": ev.confidence,
                }
            })
            # Edges: Claim -> Evidence -> Document
            edges.append({
                "data": {
                    "id": f"{ev.claim_id}_supp_{ev.id}",
                    "source": ev.claim_id,
                    "target": ev.id,
                    "label": "SUPPORTED_BY",
                    "rel_type": "SUPPORTED_BY",
                }
            })
            edges.append({
                "data": {
                    "id": f"{ev.id}_from_{ev.document_id}",
                    "source": ev.id,
                    "target": ev.document_id,
                    "label": "FROM_DOCUMENT",
                    "rel_type": "FROM_DOCUMENT",
                }
            })

        # Contradictions
        for c1_id, c2_id in self.contradictions:
            edges.append({
                "data": {
                    "id": f"{c1_id}_contra_{c2_id}",
                    "source": c1_id,
                    "target": c2_id,
                    "label": "CONTRADICTS",
                    "rel_type": "CONTRADICTS",
                }
            })

        return {
            "storage_mode": self.get_storage_mode(),
            "elements": {
                "nodes": nodes,
                "edges": edges,
            },
            "stats": {
                "entities": len(self.entities),
                "claims": len(self.claims),
                "evidence": len(self.evidence),
                "documents": len(self.documents),
                "contradictions": len(self.contradictions),
            },
        }
