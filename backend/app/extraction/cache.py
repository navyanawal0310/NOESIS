"""Persistent Extraction Cache for Document Chunks."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.config import settings

logger = logging.getLogger("noesis.extraction.cache")

PROMPT_VERSION = "v1.2_evidence_constrained"
SCHEMA_VERSION = "v1.0"


class ExtractionCache:
    """Caches LLM extraction payloads on disk to avoid redundant inference."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or settings.EXTRACTION_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_key(self, chunk_text: str, model_id: str) -> str:
        """Constructs a deterministic cache key from text, model, prompt, and schema versions."""
        payload = f"{chunk_text}|{model_id}|{PROMPT_VERSION}|{SCHEMA_VERSION}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, chunk_text: str, model_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached extraction output if valid."""
        key = self._compute_key(chunk_text, model_id)
        path = self.cache_dir / f"{key}.json"

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.debug("Extraction cache hit for key %s", key[:12])
                return data
            except Exception as e:
                logger.warning("Failed to read cache file %s: %s", path, str(e))
        return None

    def set(self, chunk_text: str, model_id: str, extraction_data: Dict[str, Any]) -> None:
        """Stores extraction output in cache."""
        key = self._compute_key(chunk_text, model_id)
        path = self.cache_dir / f"{key}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(extraction_data, f, indent=2)
            logger.debug("Saved extraction cache for key %s", key[:12])
        except Exception as e:
            logger.warning("Failed to write extraction cache to %s: %s", path, str(e))

    def clear(self) -> int:
        """Removes all cached extraction entries."""
        count = 0
        for p in self.cache_dir.glob("*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        return count
