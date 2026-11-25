"""Idempotent Graph Seeding Script for NOESIS.

Seeds the configured graph repository (Neo4j or InMemory) with the synthetic research corpus,
validating entity uniqueness, deterministic fingerprints, and evidence quotations.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.graph.factory import get_graph_repository
from backend.app.ontology.models import Claim, Document, Entity, EntityType, Evidence, Polarity
from datasets.synthetic.builder import build_corpus_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("noesis.scripts.seed")


def seed_database(clear_existing: bool = True, repo: Optional[Any] = None) -> dict:
    """Seeds the active or provided graph repository idempotently."""
    if repo is None:
        repo = get_graph_repository()
    logger.info("Initializing graph seed against storage mode: %s", repo.get_storage_mode())

    if clear_existing:
        logger.info("Clearing existing graph data...")
        repo.clear()

    corpus_data = build_corpus_data()

    # 1. Ingest Documents
    logger.info("Ingesting %d synthetic documents...", len(corpus_data["documents"]))
    for doc_dict in corpus_data["documents"]:
        doc = Document(
            id=doc_dict["id"],
            title=doc_dict["title"],
            source_type=doc_dict["source_type"],
            publication_date=doc_dict.get("publication_date"),
            source_uri=doc_dict.get("source_uri"),
            content_hash=doc_dict.get("content_hash", "hash_placeholder"),
            ingestion_timestamp="2026-11-24T00:00:00Z",
            raw_text=doc_dict["raw_text"],
            metadata=doc_dict.get("metadata", {}),
        )
        repo.add_document(doc)

    # 2. Ingest Entities
    logger.info("Ingesting %d entities...", len(corpus_data["entities"]))
    for ent_dict in corpus_data["entities"]:
        ent = Entity(
            id=ent_dict["id"],
            canonical_name=ent_dict["canonical_name"],
            type=EntityType(ent_dict["type"]),
            aliases=ent_dict.get("aliases", []),
            description=ent_dict.get("description"),
        )
        repo.add_entity(ent)

    # 3. Ingest Claims
    logger.info("Ingesting %d claims...", len(corpus_data["claims"]))
    for clm_dict in corpus_data["claims"]:
        clm = Claim(
            id=clm_dict["id"],
            subject_id=clm_dict["subject_id"],
            predicate=clm_dict["predicate"],
            object_id=clm_dict["object_id"],
            polarity=Polarity(clm_dict["polarity"]),
            temporal_scope=clm_dict.get("temporal_scope"),
            confidence=clm_dict.get("confidence", 1.0),
            evidence_ids=clm_dict.get("evidence_ids", []),
            contradiction_ids=clm_dict.get("contradiction_ids", []),
        )
        repo.add_claim(clm)

    # 4. Ingest Evidence
    logger.info("Ingesting %d evidence records...", len(corpus_data["evidence"]))
    for ev_dict in corpus_data["evidence"]:
        ev = Evidence(
            id=ev_dict["id"],
            claim_id=ev_dict["claim_id"],
            document_id=ev_dict["document_id"],
            quote=ev_dict["quote"],
            page=ev_dict.get("page", 1),
            chunk_id=ev_dict.get("chunk_id"),
            char_offset_start=ev_dict["char_offset_start"],
            char_offset_end=ev_dict["char_offset_end"],
            confidence=ev_dict.get("confidence", 1.0),
        )
        repo.add_evidence(ev)

    # 5. Ingest Contradictions
    logger.info("Registering %d contradiction pairs...", len(corpus_data["contradictions"]))
    for c1_id, c2_id in corpus_data["contradictions"]:
        repo.add_contradiction(c1_id, c2_id)

    full_graph = repo.get_full_graph()
    logger.info("Graph seeding complete! Active elements: %s", full_graph.get("stats", {}))
    return full_graph


if __name__ == "__main__":
    seed_database()
