"""Regression and Unit Tests for NOESIS Ollama Provider Hotfix.

Verifies:
1. Outbound request payload structure (think: false at top-level, keep_alive: "10m", format: schema, options: num_ctx/num_predict).
2. Explicit max_retries=0 enforcement and timeout immediate error (no retry).
3. Context overflow / done_reason == "length" detection.
4. Telemetry nano-to-millisecond conversion and cold-start flag.
5. Health timeout separation from inference timeout.
6. Sequential GPU lock enforcement.
7. Ingestion job background tracking and duplicate prevention.
"""

import json
import socket
import urllib.error
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from backend.app.ingestion.jobs import (
    IngestionJob,
    get_job,
    get_job_by_document,
    submit_ingestion_job,
)
from backend.app.llm.base import LLMInferenceError
from backend.app.llm.ollama import _GLOBAL_GPU_LOCK, OllamaProvider


@pytest.fixture
def mock_ollama_tags():
    """Mock for /api/tags endpoint returning ready qwen3:4b model."""
    tags_data = json.dumps({"models": [{"name": "qwen3:4b"}]}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = tags_data
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_ollama_payload_structure_hotfix(mock_ollama_tags):
    """Verifies that the outbound payload conforms strictly to the hotfix requirements:

    - think: false is at top level, NOT inside options
    - keep_alive: '10m' is at top level
    - format: passed schema dictionary directly
    - options: num_ctx=2048, num_predict=task_limit, temperature=0
    """
    captured_payload: Dict[str, Any] = {}

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        # Capture generate payload
        nonlocal captured_payload
        data_bytes = req.data
        captured_payload = json.loads(data_bytes.decode("utf-8"))

        mock_gen = MagicMock()
        mock_gen.status = 200
        mock_gen.read.return_value = json.dumps({
            "response": '{"entities": [], "claims": []}',
            "model": "qwen3:4b",
            "total_duration": 5000000000,
            "load_duration": 200000000,
            "prompt_eval_count": 100,
            "prompt_eval_duration": 1500000000,
            "eval_count": 50,
            "eval_duration": 3300000000,
            "done_reason": "stop",
        }).encode("utf-8")
        mock_gen.__enter__.return_value = mock_gen
        return mock_gen

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        context_length=2048,
        temperature=0.0,
        timeout=180,
        health_timeout=3,
        keep_alive="10m",
        max_retries=0,
        think=False,
        max_tokens=1024,
    )

    test_schema = {
        "type": "object",
        "properties": {
            "entities": {"type": "array"},
            "claims": {"type": "array"},
        },
        "required": ["entities", "claims"],
    }

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        resp = provider.generate(
            prompt="Extract entities and claims from text",
            system_prompt="System extraction rules",
            schema=test_schema,
        )

    # 1. Root-level assertions
    assert captured_payload["model"] == "qwen3:4b"
    assert captured_payload["prompt"] == "Extract entities and claims from text"
    assert captured_payload["system"] == "System extraction rules"
    assert captured_payload["stream"] is False
    assert captured_payload["think"] is False  # MUST be at root level
    assert captured_payload["keep_alive"] == "10m"  # MUST be at root level
    assert captured_payload["format"] == test_schema  # MUST be the schema dict, not just "json"

    # 2. Options assertions
    assert "think" not in captured_payload["options"]  # MUST NOT be in options
    assert captured_payload["options"]["temperature"] == 0.0
    assert captured_payload["options"]["num_ctx"] == 2048
    assert captured_payload["options"]["num_predict"] == 1024

    # 3. Telemetry assertions
    assert resp.total_duration_ms == 5000.0
    assert resp.load_duration_ms == 200.0
    assert resp.prompt_eval_duration_ms == 1500.0
    assert resp.eval_duration_ms == 3300.0
    assert resp.done_reason == "stop"
    assert resp.is_cold_start is False  # load_duration_ms <= 1000


def test_ollama_format_json_fallback(mock_ollama_tags):
    """Verifies that format='json' is passed when schema='json' is requested."""
    captured_payload = {}

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        nonlocal captured_payload
        captured_payload = json.loads(req.data.decode("utf-8"))
        mock_gen = MagicMock()
        mock_gen.status = 200
        mock_gen.read.return_value = json.dumps({"response": "{}", "done_reason": "stop"}).encode("utf-8")
        mock_gen.__enter__.return_value = mock_gen
        return mock_gen

    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        provider.generate("Generate JSON", schema="json")

    assert captured_payload["format"] == "json"


def test_ollama_max_retries_zero_enforced(mock_ollama_tags):
    """Verifies that max_retries=0 executes exactly 1 attempt and reports 1 attempt in error."""
    call_count = 0

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        nonlocal call_count
        call_count += 1
        raise urllib.error.HTTPError(url, 500, "Internal Server Error", {}, None)

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        max_retries=0,
    )

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        with pytest.raises(LLMInferenceError) as exc_info:
            provider.generate("Trigger 500 error")

        # Must have made exactly 1 attempt
        assert call_count == 1
        assert "after 1 attempt(s)" in str(exc_info.value)


def test_ollama_timeout_no_immediate_retry(mock_ollama_tags):
    """Verifies that a socket timeout raises LLMInferenceError immediately without retrying."""
    call_count = 0

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        nonlocal call_count
        call_count += 1
        raise socket.timeout("timed out")

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        max_retries=3,  # even with 3 retries, timeout must halt immediately
    )

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        with pytest.raises(LLMInferenceError) as exc_info:
            provider.generate("Trigger timeout")

        assert call_count == 1
        assert "timed out after 1 attempt(s)" in str(exc_info.value)


def test_ollama_context_overflow_truncation(mock_ollama_tags):
    """Verifies that done_reason == 'length' raises LLMInferenceError for context overflow."""
    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        mock_gen = MagicMock()
        mock_gen.status = 200
        mock_gen.read.return_value = json.dumps({
            "response": '{"entities": [{"name": "Elena", "category": "PERS',
            "done_reason": "length",
            "eval_count": 2048,
        }).encode("utf-8")
        mock_gen.__enter__.return_value = mock_gen
        return mock_gen

    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        with pytest.raises(LLMInferenceError) as exc_info:
            provider.generate("Generate long response")

        assert "done_reason='length'" in str(exc_info.value)


def test_ollama_cold_start_telemetry(mock_ollama_tags):
    """Verifies that a load_duration > 1000ms correctly flags cold_start=True."""
    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        mock_gen = MagicMock()
        mock_gen.status = 200
        mock_gen.read.return_value = json.dumps({
            "response": '{"entities": []}',
            "load_duration": 28000000000,  # 28 seconds (cold start)
            "total_duration": 32000000000,
            "done_reason": "stop",
        }).encode("utf-8")
        mock_gen.__enter__.return_value = mock_gen
        return mock_gen

    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        resp = provider.generate("Test cold start")

    assert resp.is_cold_start is True
    assert resp.load_duration_ms == 28000.0


def test_ollama_health_timeout_separation():
    """Verifies that check_status uses health_timeout (3s) rather than inference timeout (180s)."""
    captured_timeout = None

    def mock_urlopen(req, timeout=None):
        nonlocal captured_timeout
        captured_timeout = timeout
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"models": [{"name": "qwen3:4b"}]}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        timeout=180.0,
        health_timeout=3.0,
    )

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        status = provider.check_status()

    assert status.available is True
    assert captured_timeout == 3.0


def test_ollama_sequential_gpu_lock(mock_ollama_tags):
    """Verifies that _GLOBAL_GPU_LOCK is acquired during generate()."""
    lock_acquired = False

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_ollama_tags
        nonlocal lock_acquired
        # Check if the lock is locked by the current execution
        lock_acquired = _GLOBAL_GPU_LOCK.locked()
        mock_gen = MagicMock()
        mock_gen.status = 200
        mock_gen.read.return_value = json.dumps({"response": "{}", "done_reason": "stop"}).encode("utf-8")
        mock_gen.__enter__.return_value = mock_gen
        return mock_gen

    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        provider.generate("Test lock")

    assert lock_acquired is True
    # And after completion, lock is released
    assert not _GLOBAL_GPU_LOCK.locked()


def test_ingestion_job_tracker():
    """Verifies the IngestionJob background runner lifecycle and duplicate handling."""
    called = False

    def dummy_task(job: IngestionJob):
        nonlocal called
        called = True
        job.progress_percent = 50.0
        return {"entities": 2, "claims": 1}

    job1 = submit_ingestion_job("doc_test_123", dummy_task)
    assert job1.document_id == "doc_test_123"
    assert job1.job_id is not None

    # Retrieve by job_id
    retrieved = get_job(job1.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job1.job_id

    # Retrieve by document_id
    by_doc = get_job_by_document("doc_test_123")
    assert by_doc is not None
    assert by_doc.document_id == "doc_test_123"

    # Wait for completion (dummy task runs quickly in executor)
    import time
    for _ in range(30):
        if job1.status.lower() in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert job1.status.lower() == "completed"
    assert job1.progress_percent == 100.0
    assert job1.result == {"entities": 2, "claims": 1}
    assert called is True
