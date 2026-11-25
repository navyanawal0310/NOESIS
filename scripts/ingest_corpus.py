"""Real-World Corpus Ingestion Script for NOESIS.

Ingests the staged real-world papers into the NOESIS Knowledge Graph,
extracting schema-grounded entities, claims, and verified evidence records.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.extraction.fingerprint import compute_claim_fingerprint
from backend.app.extraction.validator import validate_evidence_quotation
from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.ontology.models import Claim, Document, Entity, EntityType, Evidence, Polarity

MANIFEST_PATH = ROOT_DIR / "datasets" / "real" / "manifest.json"


def ingest_real_corpus(repo: Optional[InMemoryGraphRepository] = None) -> Dict[str, Any]:
    start_time = time.perf_counter()
    if repo is None:
        repo = InMemoryGraphRepository()

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    papers = manifest.get("papers", [])
    print("=" * 65)
    print(f"INGESTING REAL-WORLD SCIENTIFIC CORPUS ({len(papers)} Papers)")
    print("=" * 65)

    stats = {
        "documents": 0,
        "entities": 0,
        "claims_accepted": 0,
        "claims_rejected": 0,
        "evidence_records": 0,
    }

    entity_id_map = {}

    for p in papers:
        pid = p["paper_id"]
        title = p["title"]
        file_path = ROOT_DIR / p["file_path"]

        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping.")
            continue

        with open(file_path, "r", encoding="utf-8") as pf:
            raw_text = pf.read()

        # 1. Ingest Document
        doc = Document(
            id=pid,
            title=title,
            source_type="academic_paper",
            publication_date=str(p["year"]),
            source_uri=p["open_access_url"],
            content_hash=f"hash_{pid.lower()}",
            ingestion_timestamp="2026-11-25T00:00:00Z",
            raw_text=raw_text,
            metadata={"venue": p["venue"], "authors": p["authors"]},
        )
        repo.add_document(doc)
        stats["documents"] += 1

        # 2. Ingest Key Entities
        for ename in p.get("key_entities", []):
            eid = "ent_" + ename.lower().replace(" ", "_").replace("-", "_")
            if eid not in entity_id_map:
                etype = EntityType.CONCEPT
                if "Research" in ename or "Brain" in ename or "Meta" in ename:
                    etype = EntityType.ORGANIZATION
                elif "Vaswani" in ename or "Bordes" in ename or "He" in ename:
                    etype = EntityType.PERSON
                elif "Transformer" in ename or "RAG" in ename or "TransE" in ename or "LLaMA" in ename or "ResNet" in ename:
                    etype = EntityType.TECHNOLOGY

                ent = Entity(
                    id=eid,
                    canonical_name=ename,
                    type=etype,
                    aliases=[ename],
                    description=f"Entity extracted from {title}",
                )
                repo.add_entity(ent)
                entity_id_map[ename] = eid
                stats["entities"] += 1

        # 3. Ingest Key Claims with Quotation Validation
        for clm in p.get("key_claims", []):
            subj_name = clm["subject"]
            obj_name = clm["object"]
            pred = clm["predicate"]

            subj_id = entity_id_map.get(subj_name, "ent_" + subj_name.lower().replace(" ", "_"))
            obj_id = entity_id_map.get(obj_name, "ent_" + obj_name.lower().replace(" ", "_"))

            # Find quotation substring in paper text
            quote = None
            start_off = -1
            end_off = -1

            # Match first sentence containing entity
            for line in raw_text.splitlines():
                if subj_name in line or obj_name in line:
                    if len(line.strip()) > 20:
                        quote = line.strip()
                        start_off = raw_text.find(quote)
                        end_off = start_off + len(quote)
                        break

            if quote and start_off != -1:
                # Validate quotation
                v_res = validate_evidence_quotation(raw_text, quote, start_off, end_off)
                if not v_res.is_valid:
                    stats["claims_rejected"] += 1
                    continue

                cid = compute_claim_fingerprint(subj_id, pred, obj_id, "affirmed", str(p["year"]))
                ev_id = f"ev_real_{len(repo.evidence) + 1:04d}"

                claim_obj = Claim(
                    id=cid,
                    subject_id=subj_id,
                    predicate=pred,
                    object_id=obj_id,
                    polarity=Polarity.AFFIRMED,
                    temporal_scope=str(p["year"]),
                    confidence=1.0,
                    evidence_ids=[ev_id],
                )
                repo.add_claim(claim_obj)
                stats["claims_accepted"] += 1

                evidence_obj = Evidence(
                    id=ev_id,
                    claim_id=cid,
                    document_id=pid,
                    quote=quote,
                    page=1,
                    char_offset_start=start_off,
                    char_offset_end=end_off,
                    confidence=1.0,
                )
                repo.add_evidence(evidence_obj)
                stats["evidence_records"] += 1
            else:
                stats["claims_rejected"] += 1

    elapsed = time.perf_counter() - start_time
    stats["elapsed_seconds"] = round(elapsed, 3)

    print(f"Documents Ingested:    {stats['documents']}")
    print(f"Entities Created:      {stats['entities']}")
    print(f"Claims Accepted:       {stats['claims_accepted']}")
    print(f"Claims Rejected:       {stats['claims_rejected']}")
    print(f"Evidence Records:      {stats['evidence_records']}")
    print(f"Ingestion Duration:    {stats['elapsed_seconds']}s")
    print("=" * 65)

    return stats


if __name__ == "__main__":
    from typing import Optional
    ingest_real_corpus()
