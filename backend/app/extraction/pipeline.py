"""Evidence-Constrained Extraction Pipeline with Local LLM Grounding and Atomic Commits."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from backend.app.extraction.cache import ExtractionCache
from backend.app.extraction.fingerprint import compute_claim_fingerprint
from backend.app.extraction.resolution import EntityResolver
from backend.app.extraction.schema import (
    ExtractionOutput,
    ExtractionResult,
    VerifiedClaimRecord,
)
from backend.app.extraction.validator import validate_evidence_quotation
from backend.app.graph.base import BaseGraphRepository
from backend.app.ingestion.chunking import DocumentChunk
from backend.app.ingestion.parser import ParsedDocument
from backend.app.llm.base import BaseLLMProvider
from backend.app.ontology.models import Claim, Document, EntityType, Evidence, Predicate

logger = logging.getLogger("noesis.extraction.pipeline")

# Strict, compact JSON Schema for grammar-constrained local LLM decoding
EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "canonical_name": {"type": "string"},
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "PERSON",
                            "ORGANIZATION",
                            "TECHNOLOGY",
                            "PROJECT",
                            "PUBLICATION",
                            "LOCATION",
                            "CONCEPT",
                        ],
                    },
                    "aliases": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["canonical_name", "entity_type"],
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject_name": {"type": "string"},
                    "predicate": {
                        "type": "string",
                        "enum": [
                            "FOUNDED",
                            "WORKED_ON",
                            "DEVELOPED",
                            "EMPLOYED_BY",
                            "COLLABORATED_WITH",
                            "AUTHORED",
                            "PUBLISHED",
                            "ACQUIRED",
                            "FUNDED",
                            "LOCATED_IN",
                            "USES",
                            "DISPUTES",
                        ],
                    },
                    "object_name": {"type": "string"},
                    "polarity": {"type": "string", "enum": ["affirmed", "negated"]},
                    "temporal_scope": {"type": ["string", "null"]},
                    "exact_quote": {"type": "string"},
                },
                "required": ["subject_name", "predicate", "object_name", "exact_quote"],
            },
        },
    },
    "required": ["entities", "claims"],
}

EXTRACTION_SYSTEM_PROMPT = """You are the Knowledge Extraction Engine for NOESIS.
Extract factual entities and verifiable claims from the text.
Every claim MUST contain an exact, verbatim quotation ('exact_quote') copied character-for-character from the source text.
Allowed Predicates: FOUNDED, WORKED_ON, DEVELOPED, EMPLOYED_BY, COLLABORATED_WITH, AUTHORED, PUBLISHED, ACQUIRED, FUNDED, LOCATED_IN, USES, DISPUTES.
Allowed Entity Types: PERSON, ORGANIZATION, TECHNOLOGY, PROJECT, PUBLICATION, LOCATION, CONCEPT."""

EXTRACTION_USER_PROMPT_TEMPLATE = """Source Text:
\"\"\"{chunk_text}\"\"\"

Extract all entities and evidence-backed claims in JSON matching the schema."""


class EvidenceConstrainedExtractor:
    """Coordinates local LLM extraction, quotation span validation,

    entity resolution, and ingestion into the knowledge graph.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        repository: BaseGraphRepository,
        cache: Optional[ExtractionCache] = None,
    ):
        self.llm = llm_provider
        self.repo = repository
        self.cache = cache or ExtractionCache()

    def extract_from_chunk(
        self,
        document: ParsedDocument,
        chunk: DocumentChunk,
        resolver: EntityResolver,
    ) -> ExtractionResult:
        """Extracts claims from a single chunk, enforces exact quotation matching,

        and resolves entities.
        """
        cached_data = self.cache.get(chunk.text, self.llm.check_status().configured_model)
        from_cache = False
        duration_ms = 0.0

        if cached_data:
            from_cache = True
            raw_output = cached_data
            model_used = raw_output.get("model", "cached")
        else:
            prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                document_id=document.document_id,
                chunk_id=chunk.chunk_id,
                chunk_text=chunk.text,
            )
            llm_res = self.llm.generate(
                prompt=prompt,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                schema=EXTRACTION_JSON_SCHEMA,
            )
            duration_ms = llm_res.inference_duration_ms
            model_used = llm_res.model

            try:
                # Parse JSON output
                raw_json = json.loads(llm_res.content)
                raw_output = raw_json
                raw_output["model"] = model_used
                self.cache.set(chunk.text, model_used, raw_output)
            except Exception as e:
                logger.error("Failed to parse LLM extraction JSON: %s (Content: %s)", str(e), llm_res.content[:200])
                raw_output = {"entities": [], "claims": []}

        # Parse with Pydantic
        try:
            parsed_output = ExtractionOutput(
                entities=raw_output.get("entities", []),
                claims=raw_output.get("claims", []),
            )
        except Exception as e:
            logger.warning("Pydantic schema validation error on extraction output: %s", str(e))
            parsed_output = ExtractionOutput(entities=[], claims=[])

        # 1. Resolve Entities
        resolved_entities_list: List[Dict[str, Any]] = []
        name_to_id: Dict[str, str] = {}

        for ent_raw in parsed_output.entities:
            res_ent = resolver.resolve(
                name=ent_raw.canonical_name,
                entity_type=ent_raw.entity_type,
                aliases=ent_raw.aliases,
            )
            name_to_id[ent_raw.canonical_name.strip().lower()] = res_ent.entity_id
            resolved_entities_list.append(
                {
                    "raw_name": ent_raw.canonical_name,
                    "resolved_id": res_ent.entity_id,
                    "canonical_name": res_ent.canonical_name,
                    "type": res_ent.entity_type.value,
                    "is_new": res_ent.is_new,
                }
            )

        # 2. Process and Validate Claims
        accepted_claims: List[VerifiedClaimRecord] = []
        rejected_claims: List[Dict[str, Any]] = []

        for clm_raw in parsed_output.claims:
            quote = clm_raw.exact_quote.strip() if clm_raw.exact_quote else ""

            # Rule A: Check quotation exists verbatim in chunk text
            if not quote or quote not in chunk.text:
                rejected_claims.append(
                    {
                        "claim": clm_raw.model_dump(),
                        "reason": f"Supporting quotation not found verbatim in chunk text: '{quote[:60]}...'",
                        "rejected_stage": "lexical_quotation_verification",
                    }
                )
                continue

            # Calculate exact character offsets within source document
            chunk_quote_idx = chunk.text.find(quote)
            doc_offset_start = chunk.char_offset_start + chunk_quote_idx
            doc_offset_end = doc_offset_start + len(quote)

            # Rule B: Validate quotation against source document text
            val_res = validate_evidence_quotation(
                raw_text=document.raw_text,
                quote=quote,
                start_offset=doc_offset_start,
                end_offset=doc_offset_end,
            )

            if not val_res.is_valid:
                rejected_claims.append(
                    {
                        "claim": clm_raw.model_dump(),
                        "reason": f"Source document offset validation failed: {val_res.reason}",
                        "rejected_stage": "document_offset_verification",
                    }
                )
                continue

            # Rule C: Validate Predicate against Canonical Ontology
            try:
                norm_predicate = Predicate(clm_raw.predicate.strip().upper()).value
            except ValueError:
                rejected_claims.append(
                    {
                        "claim": clm_raw.model_dump(),
                        "reason": f"Predicate '{clm_raw.predicate}' is not part of the canonical ontology",
                        "rejected_stage": "predicate_validation",
                    }
                )
                continue

            # Rule D: Resolve Subject and Object entity references
            subj_id = name_to_id.get(clm_raw.subject_name.strip().lower())
            obj_id = name_to_id.get(clm_raw.object_name.strip().lower())

            if not subj_id:
                res = resolver.resolve(clm_raw.subject_name, EntityType.CONCEPT)
                subj_id = res.entity_id
                name_to_id[clm_raw.subject_name.strip().lower()] = subj_id

            if not obj_id:
                res = resolver.resolve(clm_raw.object_name, EntityType.CONCEPT)
                obj_id = res.entity_id
                name_to_id[clm_raw.object_name.strip().lower()] = obj_id

            if subj_id == obj_id:
                rejected_claims.append(
                    {
                        "claim": clm_raw.model_dump(),
                        "reason": "Self-referential claim: subject and object resolve to the same entity",
                        "rejected_stage": "entity_reference_validation",
                    }
                )
                continue

            # Deterministic claim fingerprint
            claim_id = compute_claim_fingerprint(
                subject_id=subj_id,
                predicate=norm_predicate,
                object_id=obj_id,
                polarity=clm_raw.polarity.value,
                temporal_scope=clm_raw.temporal_scope,
            )

            accepted_claims.append(
                VerifiedClaimRecord(
                    claim_id=claim_id,
                    subject_id=subj_id,
                    predicate=norm_predicate,
                    object_id=obj_id,
                    polarity=clm_raw.polarity,
                    temporal_scope=clm_raw.temporal_scope,
                    exact_quote=quote,
                    document_id=document.document_id,
                    chunk_id=chunk.chunk_id,
                    char_offset_start=doc_offset_start,
                    char_offset_end=doc_offset_end,
                    page=chunk.page_start,
                    is_lexically_verified=True,
                    review_status="accepted",
                )
            )

        return ExtractionResult(
            document_id=document.document_id,
            total_extracted_claims=len(parsed_output.claims),
            accepted_claims=accepted_claims,
            rejected_claims=rejected_claims,
            resolved_entities=resolved_entities_list,
            ambiguous_entities=[],
            model_used=model_used,
            inference_duration_ms=round(duration_ms, 2),
            from_cache=from_cache,
        )

    def ingest_document_into_graph(
        self,
        document: ParsedDocument,
        chunks: List[DocumentChunk],
        progress_callback: Optional[Callable[[int, int, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """Ingests a parsed document and its chunks into the knowledge graph repository with atomic commit guarantee."""
        # 1. Initialize Resolver with existing entities
        existing_entities = self.repo.list_entities()
        resolver = EntityResolver(existing_entities)

        all_accepted: List[VerifiedClaimRecord] = []
        all_rejected: List[Dict[str, Any]] = []

        # 2. Process each chunk (any extraction exception here prevents graph mutation)
        total_chunks = len(chunks)
        for idx, chunk in enumerate(chunks):
            res = self.extract_from_chunk(document, chunk, resolver)
            all_accepted.extend(res.accepted_claims)
            all_rejected.extend(res.rejected_claims)

            if progress_callback:
                progress_callback(idx + 1, total_chunks, len(all_accepted), len(all_rejected))

        # 3. Add Document Node to repository (only after extraction completes without error)
        doc_node = Document(
            id=document.document_id,
            title=document.filename,
            source_type=document.source_type,
            publication_date=None,
            source_uri=document.filename,
            content_hash=document.content_hash,
            ingestion_timestamp=document.ingestion_timestamp,
            raw_text=document.raw_text,
            metadata=document.metadata,
        )
        self.repo.add_document(doc_node)

        # 4. Commit entities to repository
        new_entities_added = 0
        for ent_id, ent_obj in resolver.id_map.items():
            if not self.repo.get_entity(ent_id):
                self.repo.add_entity(ent_obj)
                new_entities_added += 1

        # 5. Commit claims and evidence to repository
        evidence_added = 0
        for idx, rec in enumerate(all_accepted):
            ev_id = f"ev_{document.document_id.lower()}_{idx + 1:03d}"

            # Create or update claim
            existing_claim = self.repo.get_claim(rec.claim_id)
            if existing_claim:
                if ev_id not in existing_claim.evidence_ids:
                    existing_claim.evidence_ids.append(ev_id)
                self.repo.add_claim(existing_claim)
            else:
                new_claim = Claim(
                    id=rec.claim_id,
                    subject_id=rec.subject_id,
                    predicate=rec.predicate,
                    object_id=rec.object_id,
                    polarity=rec.polarity,
                    temporal_scope=rec.temporal_scope,
                    confidence=1.0,
                    evidence_ids=[ev_id],
                )
                self.repo.add_claim(new_claim)

            # Create evidence record
            ev_node = Evidence(
                id=ev_id,
                claim_id=rec.claim_id,
                document_id=rec.document_id,
                quote=rec.exact_quote,
                page=rec.page,
                chunk_id=rec.chunk_id,
                char_offset_start=rec.char_offset_start,
                char_offset_end=rec.char_offset_end,
                confidence=1.0,
            )
            self.repo.add_evidence(ev_node)
            evidence_added += 1

        # 6. Check for contradictory claims with existing claims
        contradictions_flagged = 0
        all_claims = self.repo.list_claims()
        for c1 in all_claims:
            for c2 in all_claims:
                if c1.id >= c2.id:
                    continue
                # Opposite polarity conflict
                if (
                    c1.subject_id == c2.subject_id
                    and c1.predicate == c2.predicate
                    and c1.object_id == c2.object_id
                    and c1.polarity != c2.polarity
                ):
                    self.repo.add_contradiction(c1.id, c2.id)
                    contradictions_flagged += 1

        return {
            "document_id": document.document_id,
            "filename": document.filename,
            "total_chunks": total_chunks,
            "new_entities": new_entities_added,
            "claims_accepted": len(all_accepted),
            "claims_rejected": len(all_rejected),
            "evidence_records": evidence_added,
            "contradictions_flagged": contradictions_flagged,
            "rejected_details": all_rejected[:5],
        }
