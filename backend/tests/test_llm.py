"""Unit Tests for Local LLM Provider and Ollama Integration."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from backend.app.llm.base import (
    LLMStatus,
    LLMUnavailableError,
)
from backend.app.llm.ollama import OllamaProvider


def test_llm_status_serialization():
    """Verifies LLMStatus model serialization and dictionary export."""
    status = LLMStatus(
        available=True,
        provider_name="ollama",
        base_url="http://127.0.0.1:11434",
        configured_model="qwen3:4b",
        installed_models=["qwen3:4b", "llama3:8b"],
        model_available=True,
        details="Operational",
    )
    dumped = status.to_dict()
    assert dumped["available"] is True
    assert dumped["configured_model"] == "qwen3:4b"
    assert "qwen3:4b" in dumped["installed_models"]


def test_ollama_offline_status():
    """Ensures OllamaProvider gracefully reports offline status when daemon is not reachable."""
    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        timeout=1,
        max_retries=1,
    )
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        status = provider.check_status()
        assert status.available is False
        assert status.model_available is False
        assert provider.is_available() is False


def test_ollama_offline_generate_raises():
    """Verifies that calling generate() when Ollama is offline raises LLMUnavailableError."""
    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        timeout=1,
        max_retries=1,
    )
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(LLMUnavailableError) as exc_info:
            provider.generate("Test prompt")
        assert "unavailable" in str(exc_info.value).lower()


def test_ollama_generate_with_mock_success():
    """Verifies successful generation, latency measurement, and thinking-tag suppression."""
    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:4b",
        timeout=5,
        max_retries=1,
    )

    tags_response = json.dumps({"models": [{"name": "qwen3:4b"}]}).encode("utf-8")
    generate_response = json.dumps({
        "response": "<think>some internal thought</think>{\"result\": \"success\"}",
        "model": "qwen3:4b",
        "prompt_eval_count": 24,
        "eval_count": 12,
    }).encode("utf-8")

    mock_tags_cm = MagicMock()
    mock_tags_cm.status = 200
    mock_tags_cm.read.return_value = tags_response
    mock_tags_cm.__enter__.return_value = mock_tags_cm

    mock_gen_cm = MagicMock()
    mock_gen_cm.status = 200
    mock_gen_cm.read.return_value = generate_response
    mock_gen_cm.__enter__.return_value = mock_gen_cm

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/tags" in url:
            return mock_tags_cm
        return mock_gen_cm

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        resp = provider.generate("Generate test")
        assert resp.model == "qwen3:4b"
        assert resp.content == '{"result": "success"}'
        assert resp.text == '{"result": "success"}'
        assert resp.prompt_tokens == 24
        assert resp.completion_tokens == 12
        assert resp.inference_duration_ms > 0
