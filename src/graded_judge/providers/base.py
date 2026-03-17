"""
Abstract base class for all LLM providers.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str, float, float]:
        """
        Call the LLM and return (response_text, cost_usd, latency_ms).
        Temperature defaults to 0.0 for deterministic judge behavior.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the provider name string."""
        ...
