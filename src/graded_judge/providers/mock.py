"""
Mock provider for testing. Returns configurable canned responses; cost always 0.0.
"""

import logging
import time
from graded_judge.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MockProvider(BaseProvider):
    """Mock LLM provider returning configurable responses. No real API calls."""

    def __init__(
        self,
        response_text: str = '{"score": 0.8, "reasoning": "Mock pass."}',
        latency_ms: float = 10.0,
    ) -> None:
        """
        Args:
            response_text: Canned response returned by complete().
            latency_ms: Simulated latency in milliseconds.
        """
        self._response_text = response_text
        self._latency_ms = latency_ms

    def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str, float, float]:
        """Return canned response with simulated latency. Cost is always 0.0."""
        time.sleep(self._latency_ms / 1000.0)
        return (self._response_text, 0.0, self._latency_ms)

    def name(self) -> str:
        """Return the provider name."""
        return "mock"
