"""LLM Provider Factory."""

from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.ollama import OllamaProvider

_provider_instance: BaseLLMProvider = None


def get_llm_provider() -> BaseLLMProvider:
    """Returns the configured local LLM provider singleton."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            context_length=settings.OLLAMA_CONTEXT_LENGTH,
            temperature=settings.OLLAMA_TEMPERATURE,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            health_timeout=settings.OLLAMA_HEALTH_TIMEOUT_SECONDS,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
            max_retries=settings.OLLAMA_MAX_RETRIES,
            think=settings.OLLAMA_THINK,
            max_tokens=settings.OLLAMA_MAX_GENERATED_TOKENS,
        )
    return _provider_instance


def set_llm_provider(provider: BaseLLMProvider) -> None:
    """Explicitly overrides the LLM provider instance (primarily for tests)."""
    global _provider_instance
    _provider_instance = provider
