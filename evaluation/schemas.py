"""Schemas for Benchmark Execution, Tracking, and Export."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    """Configuration specification for an evaluation experiment run."""

    experiment_id: str = Field(..., description="Unique alphanumeric experiment identifier")
    system_name: str = Field(..., description="'noesis', 'noesis_no_eaqc', 'standard_kg', or 'rag'")
    mode: str = Field(default="structured", description="'structured' or 'natural'")
    corpus_id: str = Field(default="SYNTHETIC-CORPUS-V2", description="Corpus identifier")
    split: str = Field(default="all", description="'dev', 'test', or 'all'")
    category: str = Field(default="all", description="Benchmark category filter or 'all'")
    limit: Optional[int] = Field(default=None, description="Optional limit on number of executed cases")
    resume: bool = Field(default=False, description="Whether to resume prior incomplete run")
    cache_policy: str = Field(default="use_cache", description="'use_cache' or 'clear_cache'")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    device_info: Dict[str, Any] = Field(default_factory=dict)


class CaseExecutionRecord(BaseModel):
    """Granular execution and metric record for a single benchmark case."""

    case_id: str
    system_name: str
    question: str
    category: str
    difficulty: str
    split: str
    predicted_entities: List[str] = Field(default_factory=list)
    expected_entities: List[str] = Field(default_factory=list)
    is_exact_match: bool = False
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    executed_paths: List[List[str]] = Field(default_factory=list)
    expected_paths: List[List[str]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    expected_evidence: List[str] = Field(default_factory=list)
    contradiction_detected: bool = False
    expected_contradiction: bool = False
    abstained: bool = False
    expected_abstention: bool = False
    latency_ms: float = 0.0
    graph_traversal_ms: float = 0.0
    planning_ms: float = 0.0
    llm_calls: int = 0
    raw_response: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ExperimentSummary(BaseModel):
    """Consolidated summary metrics and metadata for an experiment."""

    experiment_id: str
    config: ExperimentConfig
    total_cases: int
    completed_cases: int
    failed_cases: int
    duration_seconds: float
    metrics: Dict[str, Any] = Field(default_factory=dict)
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
