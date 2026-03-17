"""
Ollama local provider. Calls REST API at http://localhost:11434. Cost always 0.0.
"""

import logging
import time
from graded_judge.providers.base import BaseProvider

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    """Ollama local provider. Cost is always 0.0."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL) -> None:
        """
        Args:
            base_url: Base URL for Ollama API (default http://localhost:11434).
        """
        self._base_url = base_url.rstrip("/")

    def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str, float, float]:
        """Call Ollama REST API; return (response_text, 0.0, latency_ms)."""
        try:
            import httpx
        except ImportError as e:
            logger.exception("httpx not installed")
            raise RuntimeError("Ollama provider requires httpx") from e

        url = f"{self._base_url}/api/generate"
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        start = time.perf_counter()

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=body)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.exception("Ollama API call failed: %s", e)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        data = response.json()
        content = data.get("response", "")
        return (content, 0.0, latency_ms)

    def name(self) -> str:
        """Return the provider name."""
        return "ollama"
