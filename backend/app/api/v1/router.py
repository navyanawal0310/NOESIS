"""FastAPI REST API Routers - v1."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from backend.app.api.deps import get_reasoning_engine, get_repository
from backend.app.config import settings
from backend.app.graph.base import BaseGraphRepository
from backend.app.ontology.models import Claim, Document, Entity, Evidence
from backend.app.reasoning.ablation import evaluate_evidence_ablation
from backend.app.reasoning.engine import BoundedReasoningEngine
from backend.app.reasoning.models import ReasoningResult, StructuredQueryPlan

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


# 4. GET /api/v1/documents/{id}
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


# 5. GET /api/v1/entities
@router.get("/entities", response_model=List[Entity])
def list_entities(
    type: Optional[str] = Query(default=None, description="Optional entity type filter"),
    repo: BaseGraphRepository = Depends(get_repository),
):
    """Lists all entities, optionally filtered by type."""
    return repo.list_entities(type_filter=type)


# 6. GET /api/v1/entities/{id}
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


# 7. GET /api/v1/claims/{id}
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


# 8. GET /api/v1/claims/{id}/evidence
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


# 9. POST /api/v1/query/structured
@router.post("/query/structured", response_model=ReasoningResult)
def execute_structured_query(
    plan: StructuredQueryPlan,
    engine: BoundedReasoningEngine = Depends(get_reasoning_engine),
):
    """Executes a bounded multi-hop graph reasoning query (1 to 5 hops) without LLM Cypher execution."""
    return engine.execute_query(plan)


# 10. GET /api/v1/contradictions
@router.get("/contradictions")
def get_contradictions(repo: BaseGraphRepository = Depends(get_repository)):
    """Returns detected pairs of contradictory claims."""
    pairs = repo.get_contradictions()
    results = []
    for c1, c2 in pairs:
        results.append({
            "claim_1": c1,
            "claim_2": c2,
            "subject_id": c1.subject_id,
            "predicate": c1.predicate,
            "conflict_type": "polarity_inversion" if c1.object_id == c2.object_id else "attribute_dispute",
        })
    return {"total_contradictions": len(results), "contradictions": results}


# 11. POST /api/v1/counterfactual
@router.post("/counterfactual")
def run_counterfactual_ablation(
    request: CounterfactualRequest,
    engine: BoundedReasoningEngine = Depends(get_reasoning_engine),
):
    """Performs non-destructive evidence ablation across supporting documents to determine source criticality."""
    return evaluate_evidence_ablation(
        engine=engine,
        plan=request.query_plan,
        target_entity_id=request.target_entity_id,
    )
