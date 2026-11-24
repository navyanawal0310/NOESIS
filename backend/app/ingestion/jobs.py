"""Background Ingestion Job Runner with Concurrency Controls."""

import concurrent.futures
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("noesis.ingestion.jobs")

# Single inference worker to guarantee no GPU competition
_JOB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest_worker")
_ACTIVE_JOBS: Dict[str, "IngestionJob"] = {}
_DOC_TO_JOB: Dict[str, str] = {}


class IngestionJob(BaseModel):
    """Telemetry and status tracking for background document ingestion."""

    job_id: str
    document_id: str
    status: str = Field(default="pending", description="'pending', 'processing', 'completed', or 'failed'")
    progress_percent: float = Field(default=0.0)
    total_chunks: int = 0
    processed_chunks: int = 0
    accepted_claims: int = 0
    rejected_claims: int = 0
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


def get_job(job_id: str) -> Optional[IngestionJob]:
    """Retrieves an ingestion job record by job_id."""
    return _ACTIVE_JOBS.get(job_id)


def get_job_by_document(doc_id: str) -> Optional[IngestionJob]:
    """Retrieves active or completed ingestion job for a document."""
    job_id = _DOC_TO_JOB.get(doc_id)
    if job_id:
        return _ACTIVE_JOBS.get(job_id)
    return None


def submit_ingestion_job(
    document_id: str,
    worker_fn: Callable[["IngestionJob"], Dict[str, Any]],
) -> IngestionJob:
    """Submits a single-worker background job to process document ingestion."""
    existing_job = get_job_by_document(document_id)
    if existing_job and existing_job.status in ("pending", "processing"):
        return existing_job

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    job = IngestionJob(
        job_id=job_id,
        document_id=document_id,
        status="pending",
        created_at=now_iso,
    )

    _ACTIVE_JOBS[job_id] = job
    _DOC_TO_JOB[document_id] = job_id

    def _execute():
        job.status = "processing"
        try:
            res = worker_fn(job)
            job.status = "completed"
            job.progress_percent = 100.0
            job.result = res
            job.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            logger.error("Ingestion job %s failed: %s", job_id, str(e), exc_info=True)
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc).isoformat()

    _JOB_EXECUTOR.submit(_execute)
    return job
