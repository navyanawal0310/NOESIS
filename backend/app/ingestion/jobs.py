"""Background Ingestion Job Runner with Concurrency Controls."""

import concurrent.futures
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("noesis.ingestion.jobs")

# Single inference worker to guarantee no GPU competition
_JOB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest_worker")
_ACTIVE_JOBS: Dict[str, "IngestionJob"] = {}
_DOC_TO_JOB: Dict[str, str] = {}
_JOB_START_TIMES: Dict[str, float] = {}


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestionJob(BaseModel):
    """Telemetry and status tracking for background document ingestion."""

    job_id: str
    document_id: str
    status: str = Field(default=JobStatus.QUEUED.value, description="Job status enum or string representation")
    progress_percent: float = Field(default=0.0)
    total_chunks: int = 0
    processed_chunks: int = 0
    accepted_claims: int = 0
    rejected_claims: int = 0
    evidence_records: int = 0
    elapsed_time_seconds: Optional[float] = 0.0
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


def get_job(job_id: str) -> Optional[IngestionJob]:
    """Retrieves an ingestion job record by job_id with dynamic elapsed time computation."""
    job = _ACTIVE_JOBS.get(job_id)
    if job:
        start_t = _JOB_START_TIMES.get(job_id)
        if start_t:
            if job.status.upper() in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
                pass
            else:
                job.elapsed_time_seconds = round(time.time() - start_t, 2)
    return job


def get_job_by_document(doc_id: str) -> Optional[IngestionJob]:
    """Retrieves active or completed ingestion job for a document."""
    job_id = _DOC_TO_JOB.get(doc_id)
    if job_id:
        return get_job(job_id)
    return None


def submit_ingestion_job(
    document_id: str,
    worker_fn: Callable[["IngestionJob"], Dict[str, Any]],
) -> IngestionJob:
    """Submits a single-worker background job to process document ingestion."""
    existing_job = get_job_by_document(document_id)
    if existing_job and existing_job.status.upper() in (
        JobStatus.QUEUED.value,
        "PENDING",
        "PROCESSING",
        JobStatus.PARSING.value,
        JobStatus.CHUNKING.value,
        JobStatus.EXTRACTING.value,
        JobStatus.VALIDATING.value,
        JobStatus.INDEXING.value,
    ):
        return existing_job

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    job = IngestionJob(
        job_id=job_id,
        document_id=document_id,
        status=JobStatus.QUEUED.value,
        created_at=now_iso,
        elapsed_time_seconds=0.0,
    )

    _ACTIVE_JOBS[job_id] = job
    _DOC_TO_JOB[document_id] = job_id
    start_time = time.time()
    _JOB_START_TIMES[job_id] = start_time

    def _execute():
        job.status = JobStatus.EXTRACTING.value
        try:
            res = worker_fn(job)
            job.status = JobStatus.COMPLETED.value
            job.progress_percent = 100.0
            job.result = res
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.elapsed_time_seconds = round(time.time() - start_time, 2)
        except Exception as e:
            logger.error("Ingestion job %s failed: %s", job_id, str(e), exc_info=True)
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.elapsed_time_seconds = round(time.time() - start_time, 2)

    _JOB_EXECUTOR.submit(_execute)
    return job
