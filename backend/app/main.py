"""FastAPI Application Entrypoint for NOESIS."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import router as api_v1_router
from backend.app.config import settings
from backend.app.graph.factory import get_graph_repository
from scripts.seed_graph import seed_database

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("noesis.main")

app = FastAPI(
    title="NOESIS — Neural-Ontological Evidence Synthesis and Inference System",
    description=(
        "Research prototype for KG-RS-01 (Knowledge Graph Reasoning). "
        "Provides an evidence-centric knowledge graph substrate, bounded multi-hop reasoning, "
        "contradiction detection, and counterfactual evidence ablation."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Startup initialization: auto-seed synthetic corpus if repository is empty."""
    logger.info("Initializing NOESIS (%s) in %s mode...", settings.APP_VERSION, settings.APP_ENV)
    repo = get_graph_repository()
    full_graph = repo.get_full_graph()
    stats = full_graph.get("stats", {})

    if stats.get("entities", 0) == 0:
        logger.info("Graph store is empty. Auto-seeding synthetic research corpus...")
        try:
            seed_database(clear_existing=False)
            logger.info("Auto-seeding completed successfully.")
        except Exception as e:
            logger.error("Auto-seeding encountered an error: %s", str(e))
    else:
        logger.info(
            "Graph store already seeded (%d entities, %d claims).",
            stats.get("entities", 0),
            stats.get("claims", 0),
        )


@app.on_event("shutdown")
def shutdown_event():
    """Shutdown cleanup."""
    logger.info("Shutting down NOESIS application...")
    repo = get_graph_repository()
    if hasattr(repo, "close"):
        repo.close()


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception on %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An internal server error occurred during graph processing.",
            "detail": str(exc) if settings.DEBUG else None,
            "path": request.url.path,
        },
    )


# Register Routers
app.include_router(api_v1_router)


@app.get("/", tags=["Root"])
def root():
    """Welcome endpoint providing service info and links to documentation."""
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
    }
