"""Local Ollama Provider Implementation."""

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from backend.app.config import settings
from backend.app.llm.base import (
    BaseLLMProvider,
    LLMInferenceError,
    LLMResponse,
    LLMStatus,
    LLMUnavailableError,
)

logger = logging.getLogger("noesis.llm.ollama")


class OllamaProvider(BaseLLMProvider):
    """Provider connecting to local Ollama instance via HTTP API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        context_length: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.context_length = context_length or settings.OLLAMA_CONTEXT_LENGTH
        self.temperature = temperature if temperature is not None else settings.OLLAMA_TEMPERATURE
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.OLLAMA_MAX_RETRIES

        if settings.ALLOW_CLOUD_LLM:
            logger.warning("ALLOW_CLOUD_LLM is enabled in config, but NOESIS strictly enforces local inference.")

    def check_status(self) -> LLMStatus:
        """Queries /api/tags to detect running Ollama service and installed models."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOESIS-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=min(3.0, self.timeout)) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in payload.get("models", [])]
                    # Check exact or prefix match (e.g. qwen3:4b vs qwen3:4b-latest)
                    model_found = any(
                        self.model == m or m.startswith(f"{self.model}:") or self.model.startswith(m) for m in models
                    )
                    return LLMStatus(
                        available=True,
                        provider_name="ollama",
                        base_url=self.base_url,
                        configured_model=self.model,
                        installed_models=models,
                        model_available=model_found,
                        details=(
                            f"Ollama online with {len(models)} model(s) installed. "
                            f"Target '{self.model}' {'is ready' if model_found else 'NOT installed'}."
                        ),
                    )
        except Exception as e:
            logger.debug("Ollama availability check failed at %s: %s", url, str(e))
            return LLMStatus(
                available=False,
                provider_name="ollama",
                base_url=self.base_url,
                configured_model=self.model,
                installed_models=[],
                model_available=False,
                details=f"Ollama is unreachable at {self.base_url}: {str(e)}",
            )

        return LLMStatus(
            available=False,
            provider_name="ollama",
            base_url=self.base_url,
            configured_model=self.model,
            installed_models=[],
            model_available=False,
            details="Unknown connection state.",
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Executes a completion request against Ollama /api/generate."""
        # 1. First verify service and model availability
        status = self.check_status()
        if not status.available:
            raise LLMUnavailableError(
                f"Local Ollama service is unavailable at {self.base_url}. "
                "Ensure Ollama is installed and running (`ollama serve`)."
            )
        if not status.model_available:
            raise LLMUnavailableError(
                f"Configured model '{self.model}' is not installed in local Ollama. "
                f"Installed models: {status.installed_models}. "
                f"Please install it using: `ollama pull {self.model}`."
            )

        url = f"{self.base_url}/api/generate"

        options: Dict[str, Any] = {
            "temperature": temperature if temperature is not None else self.temperature,
            "num_ctx": self.context_length,
        }
        if max_tokens:
            options["num_predict"] = max_tokens

        # For models supporting thinking/reasoning suppression (e.g. Qwen / DeepSeek-R1)
        # We instruct strict JSON output and pass think: false in options where accepted
        options["think"] = False

        request_body: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }

        effective_system = system_prompt or ""
        if schema:
            request_body["format"] = "json"
            effective_system += (
                "\nCRITICAL: Respond strictly with valid JSON conforming to the requested schema. "
                "Do NOT include conversational preamble, markdown formatting, or <think> reasoning tags."
            )

        if effective_system.strip():
            request_body["system"] = effective_system.strip()

        data_bytes = json.dumps(request_body).encode("utf-8")

        start_time = time.perf_counter()
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "NOESIS-Agent/1.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    if resp.status == 200:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        raw_content = res_data.get("response", "").strip()

                        # Strip potential thinking tags if model emitted them anyway
                        if "<think>" in raw_content and "</think>" in raw_content:
                            parts = raw_content.split("</think>", 1)
                            raw_content = parts[1].strip()

                        return LLMResponse(
                            content=raw_content,
                            model=res_data.get("model", self.model),
                            inference_duration_ms=round(elapsed_ms, 2),
                            prompt_tokens=res_data.get("prompt_eval_count"),
                            completion_tokens=res_data.get("eval_count"),
                            raw_response=res_data,
                        )
                    else:
                        raise LLMInferenceError(f"Ollama returned HTTP status {resp.status}")
            except urllib.error.URLError as e:
                last_exception = e
                logger.warning("Ollama inference attempt %d failed: %s", attempt + 1, str(e))
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2**attempt))
            except Exception as e:
                last_exception = e
                logger.error("Unexpected error during Ollama inference: %s", str(e))
                break

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        raise LLMInferenceError(
            f"Ollama inference failed after {self.max_retries + 1} attempt(s) ({elapsed_ms:.1f}ms): {str(last_exception)}"
        )
