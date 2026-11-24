"""Local Ollama Provider Implementation with Strict Formatting and Concurrency Control."""

import json
import logging
import socket
import threading
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

# Global sequential inference lock to prevent GPU memory/concurrency contention
_GLOBAL_GPU_LOCK = threading.Lock()


class OllamaProvider(BaseLLMProvider):
    """Provider connecting to local Ollama instance via HTTP API with strict payload conformance."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        context_length: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        health_timeout: Optional[float] = None,
        keep_alive: Optional[str] = None,
        max_retries: Optional[int] = None,
        think: Optional[bool] = None,
        max_tokens: Optional[int] = None,
    ):
        self.base_url = (base_url if base_url is not None else settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model if model is not None else settings.OLLAMA_MODEL
        self.context_length = context_length if context_length is not None else settings.OLLAMA_CONTEXT_LENGTH
        self.temperature = temperature if temperature is not None else settings.OLLAMA_TEMPERATURE
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS
        self.health_timeout = (
            health_timeout if health_timeout is not None else settings.OLLAMA_HEALTH_TIMEOUT_SECONDS
        )
        self.keep_alive = keep_alive if keep_alive is not None else settings.OLLAMA_KEEP_ALIVE
        self.max_retries = max_retries if max_retries is not None else settings.OLLAMA_MAX_RETRIES
        self.think = think if think is not None else settings.OLLAMA_THINK
        self.max_tokens = max_tokens if max_tokens is not None else settings.OLLAMA_MAX_GENERATED_TOKENS

        if settings.ALLOW_CLOUD_LLM:
            logger.warning("ALLOW_CLOUD_LLM is enabled in config, but NOESIS strictly enforces local inference.")

    def check_status(self) -> LLMStatus:
        """Queries /api/tags with health_timeout to detect running Ollama service without blocking inference."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOESIS-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=self.health_timeout) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in payload.get("models", [])]
                    # Check exact or tag-normalized match (e.g. qwen3:4b vs qwen3:4b-latest)
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
        schema: Optional[Any] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context_length: Optional[int] = None,
    ) -> LLMResponse:
        """Executes a completion request against Ollama /api/generate with sequential GPU locking."""
        # 1. Enforce sequential inference lock on the single local GPU
        with _GLOBAL_GPU_LOCK:
            # 2. Verify service and model availability
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

            # 3. Build options dictionary
            options: Dict[str, Any] = {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_ctx": context_length if context_length is not None else self.context_length,
                "num_predict": max_tokens if max_tokens is not None else self.max_tokens,
            }

            # 4. Build exact top-level request payload
            request_body: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": self.think,
                "keep_alive": self.keep_alive,
                "options": options,
            }

            # Include system prompt only when required
            if system_prompt and system_prompt.strip():
                request_body["system"] = system_prompt.strip()

            # Pass actual JSON schema dictionary when provided, or format="json" if explicitly requested
            if schema:
                if isinstance(schema, (dict, list)):
                    request_body["format"] = schema
                elif schema == "json" or str(schema).lower() == "json":
                    request_body["format"] = "json"

            data_bytes = json.dumps(request_body).encode("utf-8")

            start_time = time.perf_counter()
            last_exception = None
            actual_attempts = 0

            # 5. Bounded retry loop with explicit attempts tracking
            for attempt in range(self.max_retries + 1):
                actual_attempts += 1
                req_start = time.perf_counter()
                try:
                    req = urllib.request.Request(
                        url,
                        data=data_bytes,
                        headers={"Content-Type": "application/json", "User-Agent": "NOESIS-Agent/1.0"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        body_bytes = resp.read()
                        http_elapsed_ms = (time.perf_counter() - req_start) * 1000

                        if resp.status == 200:
                            res_data = json.loads(body_bytes.decode("utf-8"))
                            raw_content = res_data.get("response", "").strip()

                            # Check for truncated context overflow
                            done_reason = res_data.get("done_reason")
                            if done_reason == "length":
                                raise LLMInferenceError(
                                    f"Ollama generation truncated due to context window or token limit (done_reason='length'). "
                                    f"Eval count: {res_data.get('eval_count')}, context limit: {options['num_ctx']}."
                                )

                            # Strip potential thinking tags if model emitted them anyway
                            if "<think>" in raw_content and "</think>" in raw_content:
                                parts = raw_content.split("</think>", 1)
                                raw_content = parts[1].strip()

                            # Extract telemetry metrics
                            total_dur = res_data.get("total_duration")
                            load_dur = res_data.get("load_duration")
                            p_eval_dur = res_data.get("prompt_eval_duration")
                            eval_dur = res_data.get("eval_duration")

                            total_ms = (total_dur / 1e6) if total_dur else None
                            load_ms = (load_dur / 1e6) if load_dur else None
                            p_eval_ms = (p_eval_dur / 1e6) if p_eval_dur else None
                            eval_ms = (eval_dur / 1e6) if eval_dur else None
                            is_cold = bool(load_ms and load_ms > 1000)

                            return LLMResponse(
                                content=raw_content,
                                model=res_data.get("model", self.model),
                                inference_duration_ms=round(http_elapsed_ms, 2),
                                prompt_tokens=res_data.get("prompt_eval_count"),
                                completion_tokens=res_data.get("eval_count"),
                                total_duration_ms=round(total_ms, 2) if total_ms else None,
                                load_duration_ms=round(load_ms, 2) if load_ms else None,
                                prompt_eval_duration_ms=round(p_eval_ms, 2) if p_eval_ms else None,
                                eval_duration_ms=round(eval_ms, 2) if eval_ms else None,
                                done_reason=done_reason,
                                is_cold_start=is_cold,
                                raw_response=res_data,
                            )
                        else:
                            raise LLMInferenceError(f"Ollama returned unexpected HTTP status {resp.status}")

                except urllib.error.HTTPError as he:
                    last_exception = he
                    elapsed_total = (time.perf_counter() - start_time) * 1000
                    if he.code == 404:
                        raise LLMUnavailableError(
                            f"Model '{self.model}' was not found in local Ollama (HTTP 404). "
                            f"Run `ollama pull {self.model}` to install."
                        )
                    logger.warning("Ollama HTTP %d on attempt %d: %s", he.code, actual_attempts, str(he))
                    if attempt < self.max_retries:
                        time.sleep(0.5 * (2**attempt))
                except (socket.timeout, TimeoutError) as te:
                    elapsed_total = (time.perf_counter() - start_time) * 1000
                    logger.error("Ollama inference timed out after %d attempt(s) (%.1fms)", actual_attempts, elapsed_total)
                    # Do not retry timed-out generation immediately
                    raise LLMInferenceError(
                        f"Ollama inference timed out after {actual_attempts} attempt(s) ({elapsed_total:.1f}ms): {str(te)}"
                    ) from te
                except urllib.error.URLError as ue:
                    last_exception = ue
                    elapsed_total = (time.perf_counter() - start_time) * 1000
                    if isinstance(ue.reason, (socket.timeout, TimeoutError)) or "timed out" in str(ue).lower():
                        logger.error(
                            "Ollama connection timed out after %d attempt(s) (%.1fms)", actual_attempts, elapsed_total
                        )
                        raise LLMInferenceError(
                            f"Ollama inference timed out after {actual_attempts} attempt(s) ({elapsed_total:.1f}ms): {str(ue)}"
                        ) from ue
                    logger.warning("Ollama URLError on attempt %d: %s", actual_attempts, str(ue))
                    if attempt < self.max_retries:
                        time.sleep(0.5 * (2**attempt))
                except Exception as e:
                    last_exception = e
                    logger.error("Unexpected error during Ollama inference: %s", str(e))
                    break

            elapsed_total = (time.perf_counter() - start_time) * 1000
            raise LLMInferenceError(
                f"Ollama inference failed after {actual_attempts} attempt(s) ({elapsed_total:.1f}ms): {str(last_exception)}"
            )
