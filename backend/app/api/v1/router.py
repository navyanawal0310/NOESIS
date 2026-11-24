"""FastAPI REST API Routers - v1."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from backend.app.api.deps import (
    get_answer_generator,
    get_extractor,
    get_gap_detector,
    get_llm,
    get_query_planner,
    get_reasoning_engine,
    get_repository,
)
from backend.app.config import settings
from backend.app.extraction.pipeline import EvidenceConstrainedExtractor
from backend.app.graph.base import BaseGraphRepository
from backend.app.ingestion.chunking import DocumentChunker
from backend.app.ingestion.jobs import (
    IngestionJob,
    get_job,
    get_job_by_document,
    submit_ingestion_job,
)
from backend.app.ingestion.parser import (
    DocumentParser,
    PageSpan,
    ParsedDocument,
    UnsupportedDocumentError,
)
from backend.app.llm.base import BaseLLMProvider, LLMInferenceError, LLMUnavailableError
from backend.app.ontology.models import Claim, Document, Entity, Evidence
from backend.app.reasoning.ablation import evaluate_evidence_ablation
from backend.app.reasoning.answer_generator import GroundedAnswer, GroundedAnswerGenerator
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.gap_detector import KnowledgeGapDetector
from backend.app.reasoning.models import ReasoningResult, StructuredQueryPlan
from backend.app.reasoning.nl_planner import NLQueryPlanner

router = APIRouter(prefix="/api/v1", tags=["NOESIS API v1"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    storage_mode: str
    is_database_healthy: bool
    total_entities: int
    total_claims: int
    total_documents: int


class CounterfactualRequest(BaseModel):
    query_plan: StructuredQueryPlan
    target_entity_id: str


class NaturalQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question to query against the graph")
    max_hops: Optional[int] = Field(default=3, ge=1, le=5, description="Maximum traversal hops")
    use_llm_synthesis: Optional[bool] = Field(
        default=False,
        description="Whether to use local LLM to summarize verified results into prose",
    )


# 1. GET /api/v1/health
@router.get("/health", response_model=HealthResponse)
def get_health(repo: BaseGraphRepository = Depends(get_repository)):
    """Returns application health, version, and the active graph storage mode."""
    stats = repo.get_full_graph().get("stats", {})
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        storage_mode=repo.get_storage_mode(),
        is_database_healthy=repo.is_healthy(),
        total_entities=stats.get("entities", 0),
        total_claims=stats.get("claims", 0),
        total_documents=stats.get("documents", 0),
    )


# 2. GET /api/v1/graph
@router.get("/graph")
def get_graph(repo: BaseGraphRepository = Depends(get_repository)):
    """Retrieves the full Cytoscape-compatible knowledge graph payload."""
    return repo.get_full_graph()


# 3. GET /api/v1/documents
@router.get("/documents", response_model=List[Document])
def list_documents(repo: BaseGraphRepository = Depends(get_repository)):
    """Lists all ingested documents with provenance metadata."""
    return repo.list_documents()


# 4. POST /api/v1/documents/upload
@router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    repo: BaseGraphRepository = Depends(get_repository),
):
    """Uploads, validates, and stores a PDF, TXT, or Markdown document without executing extraction."""
    filename = file.filename or "upload.txt"
    content_bytes = await file.read()

    # File size limit check
    max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_DOCUMENT_SIZE_MB}MB.",
        )

    # Parse and validate file format
    try:
        parsed = DocumentParser.parse_file(
            filename=filename,
            content_bytes=content_bytes,
            corpus="uploaded",
        )
    except UnsupportedDocumentError as ude:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ude),
        )

    # Check for empty or scanned OCR-required documents
    if parsed.is_scanned_ocr_required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported document: Scanned PDF without extractable text requires OCR, which is currently unavailable.",
        )
    if not parsed.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document contains no extractable text.",
        )

    # Duplicate content check via SHA-256
    existing_docs = repo.list_documents()
    for d in existing_docs:
        if d.content_hash == parsed.content_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate document detected. Content matches existing document '{d.id}' ({d.title}).",
            )

    doc_node = Document(
        id=parsed.document_id,
        title=parsed.filename,
        source_type=parsed.source_type,
        publication_date=None,
        source_uri=parsed.filename,
        content_hash=parsed.content_hash,
        ingestion_timestamp=parsed.ingestion_timestamp,
        raw_text=parsed.raw_text,
        metadata={
            **parsed.metadata,
            "total_pages": parsed.total_pages,
            "total_chars": parsed.total_chars,
            "page_spans": [ps.model_dump() for ps in parsed.page_spans],
            "ingestion_status": "uploaded",
        },
    )
    repo.add_document(doc_node)

    return {
        "document_id": doc_node.id,
        "title": doc_node.title,
        "source_type": doc_node.source_type,
        "content_hash": doc_node.content_hash,
        "total_pages": parsed.total_pages,
        "total_chars": parsed.total_chars,
        "status": "uploaded",
        "message": "Document uploaded and parsed successfully. Ready for claim extraction.",
    }


# 5. POST /api/v1/documents/{id}/ingest
@router.post("/documents/{doc_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_document_claims(
    doc_id: str,
    sync: bool = Query(default=False, description="Run synchronously instead of queuing background worker"),
    repo: BaseGraphRepository = Depends(get_repository),
    extractor: EvidenceConstrainedExtractor = Depends(get_extractor),
):
    """Executes evidence-constrained extraction and graph integration via background worker or sync mode."""
    doc = repo.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    # Prevent duplicate ingestion
    if doc.metadata.get("ingestion_status") == "ingested":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document '{doc_id}' has already been processed and ingested.",
        )

    if not extractor.llm or not extractor.llm.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Local LLM service (Ollama) is required for claim extraction but is currently unavailable. "
                f"Please ensure Ollama is running at {settings.OLLAMA_BASE_URL} with model '{settings.OLLAMA_MODEL}'."
            ),
        )

    page_spans_data = doc.metadata.get("page_spans", [])
    page_spans = [PageSpan(**ps) for ps in page_spans_data]
    parsed_doc = ParsedDocument(
        document_id=doc.id,
        filename=doc.title,
        source_type=doc.source_type,
        content_hash=doc.content_hash,
        raw_text=doc.raw_text,
        page_spans=page_spans,
        total_pages=doc.metadata.get("total_pages", 1),
        total_chars=len(doc.raw_text),
        ingestion_timestamp=doc.ingestion_timestamp,
        metadata=doc.metadata,
    )

    chunker = DocumentChunker()
    chunks = chunker.chunk_document(parsed_doc)

    def _worker(job: Optional[IngestionJob] = None) -> Dict[str, Any]:
        if job:
            job.total_chunks = len(chunks)

        def _on_progress(processed, total, accepted, rejected):
            if job:
                job.processed_chunks = processed
                job.progress_percent = round((processed / total) * 100, 1) if total > 0 else 100.0
                job.accepted_claims = accepted
                job.rejected_claims = rejected

        ingest_result = extractor.ingest_document_into_graph(parsed_doc, chunks, progress_callback=_on_progress)
        doc.metadata["ingestion_status"] = "ingested"
        doc.metadata["chunks_count"] = len(chunks)
        doc.metadata["accepted_claims_count"] = ingest_result.get("claims_accepted", 0)
        doc.metadata["rejected_claims_count"] = ingest_result.get("claims_rejected", 0)
        return ingest_result

    if sync:
        try:
            res = _worker()
            return {
                "document_id": doc_id,
                "status": "ingested",
                "chunks_processed": len(chunks),
                "results": res,
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Extraction pipeline failed: {str(e)}",
            )

    # Asynchronous single-worker queue
    job = submit_ingestion_job(doc_id, _worker)
    return {
        "job_id": job.job_id,
        "document_id": doc_id,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "message": "Document ingestion job submitted to sequential worker.",
    }


# 6. GET /api/v1/jobs/{job_id}
@router.get("/jobs/{job_id}", response_model=IngestionJob)
def get_ingestion_job_status(job_id: str):
    """Retrieves real-time processing progress of a background ingestion job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job '{job_id}' not found.",
        )
    return job


# 7. GET /api/v1/documents/{id}/status
@router.get("/documents/{doc_id}/status")
def get_document_status(
    doc_id: str,
    repo: BaseGraphRepository = Depends(get_repository),
):
    """Retrieves processing and evidentiary status for a document."""
    doc = repo.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    all_claims = repo.list_claims()
    doc_evidence: List[Evidence] = []
    for clm in all_claims:
        for ev in repo.get_evidence_for_claim(clm.id):
            if ev.document_id == doc_id:
                doc_evidence.append(ev)

    ingestion_status = doc.metadata.get(
        "ingestion_status",
        "ingested" if doc.source_type == "synthetic" else "uploaded",
    )

    active_job = get_job_by_document(doc_id)

    return {
        "document_id": doc.id,
        "title": doc.title,
        "source_type": doc.source_type,
        "content_hash": doc.content_hash,
        "status": ingestion_status,
        "total_pages": doc.metadata.get("total_pages", 1),
        "total_chars": len(doc.raw_text),
        "chunks_count": doc.metadata.get("chunks_count", 0),
        "accepted_claims": doc.metadata.get("accepted_claims_count", len(doc_evidence)),
        "rejected_claims": doc.metadata.get("rejected_claims_count", 0),
        "evidence_records": len(doc_evidence),
        "job": active_job.model_dump() if active_job else None,
    }


# 7. GET /api/v1/documents/{id}
@router.get("/documents/{doc_id}", response_model=Document)
def get_document(doc_id: str, repo: BaseGraphRepository = Depends(get_repository)):
    """Retrieves a specific document by its unique ID."""
    doc = repo.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found",
        )
    return doc


# 8. GET /api/v1/entities
@router.get("/entities", response_model=List[Entity])
def list_entities(
    type: Optional[str] = Query(default=None, description="Optional entity type filter"),
    repo: BaseGraphRepository = Depends(get_repository),
):
    """Lists all entities, optionally filtered by type."""
    type_filter = type if isinstance(type, str) else None
    return repo.list_entities(type_filter=type_filter)


# 9. GET /api/v1/entities/{id}
@router.get("/entities/{entity_id}", response_model=Entity)
def get_entity(entity_id: str, repo: BaseGraphRepository = Depends(get_repository)):
    """Retrieves an entity and its metadata by ID."""
    ent = repo.get_entity(entity_id)
    if not ent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID '{entity_id}' not found",
        )
    return ent


# 10. GET /api/v1/claims/{id}
@router.get("/claims/{claim_id}", response_model=Claim)
def get_claim(claim_id: str, repo: BaseGraphRepository = Depends(get_repository)):
    """Retrieves a claim node by its deterministic fingerprint ID."""
    claim = repo.get_claim(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID '{claim_id}' not found",
        )
    return claim


# 11. GET /api/v1/claims/{id}/evidence
@router.get("/claims/{claim_id}/evidence", response_model=List[Evidence])
def get_claim_evidence(claim_id: str, repo: BaseGraphRepository = Depends(get_repository)):
    """Retrieves all supporting evidence records for a given claim."""
    claim = repo.get_claim(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID '{claim_id}' not found",
        )
    return repo.get_evidence_for_claim(claim_id)


# 12. POST /api/v1/query/structured
@router.post("/query/structured", response_model=ReasoningResult)
def execute_structured_query(
    plan: StructuredQueryPlan,
    engine: BoundedReasoningEngine = Depends(get_reasoning_engine),
):
    """Executes a bounded multi-hop graph reasoning query (1 to 5 hops) without LLM Cypher execution."""
    return engine.execute_query(plan)


# 13. POST /api/v1/query/natural
@router.post("/query/natural", response_model=GroundedAnswer)
def execute_natural_query(
    request: NaturalQueryRequest,
    planner: NLQueryPlanner = Depends(get_query_planner),
    engine: BoundedReasoningEngine = Depends(get_reasoning_engine),
    answer_gen: GroundedAnswerGenerator = Depends(get_answer_generator),
    gap_detector: KnowledgeGapDetector = Depends(get_gap_detector),
):
    """Translates a natural-language question into a StructuredQueryPlan, executes bounded traversal,

    and returns a provenance-grounded answer with gap diagnostics. Returns 503 if Ollama is unavailable.
    """
    if not planner.llm_provider or not planner.llm_provider.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Local LLM service (Ollama) is required for natural language query planning but is currently offline. "
                f"Please ensure Ollama is running at {settings.OLLAMA_BASE_URL} with model '{settings.OLLAMA_MODEL}', "
                "or execute bounded graph queries directly using POST /api/v1/query/structured."
            ),
        )

    try:
        plan = planner.plan_query(request.question)
    except (LLMUnavailableError, LLMInferenceError) as lue:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(lue))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    if request.max_hops and 1 <= request.max_hops <= 5:
        plan.max_hops = request.max_hops

    result = engine.execute_query(plan)

    grounded_ans = answer_gen.generate_answer(
        result=result,
        plan=plan,
        question=request.question,
        use_llm=request.use_llm_synthesis or False,
        gap_detector=gap_detector,
    )
    return grounded_ans


# 14. GET /api/v1/llm/status
@router.get("/llm/status")
def get_llm_status(llm: BaseLLMProvider = Depends(get_llm)):
    """Returns local LLM availability, configured model, and connectivity status."""
    status_info = llm.check_status()
    return status_info.to_dict()


# 15. GET /api/v1/contradictions
@router.get("/contradictions")
def get_contradictions(repo: BaseGraphRepository = Depends(get_repository)):
    """Returns detected pairs of contradictory claims."""
    pairs = repo.get_contradictions()
    results = []
    for c1, c2 in pairs:
        results.append(
            {
                "claim_1": c1,
                "claim_2": c2,
                "subject_id": c1.subject_id,
                "predicate": c1.predicate,
                "conflict_type": "polarity_inversion" if c1.object_id == c2.object_id else "attribute_dispute",
            }
        )
    return {"total_contradictions": len(results), "contradictions": results}


# 16. POST /api/v1/counterfactual
@router.post("/counterfactual")
def run_counterfactual_ablation(
    request: CounterfactualRequest,
    engine: BoundedReasoningEngine = Depends(get_reasoning_engine),
):
    """Executes counterfactual evidence ablation testing by systematically removing supporting documents."""
    return evaluate_evidence_ablation(
        plan=request.query_plan,
        target_entity_id=request.target_entity_id,
        engine=engine,
    )
