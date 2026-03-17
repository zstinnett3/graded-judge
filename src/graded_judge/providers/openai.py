"""
OpenAI provider. Uses published per-token pricing for gpt-4o-mini and gpt-4o.
"""

import logging
import time
from graded_judge.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Published per-1M token pricing (input, output). Fallback for unknown models.
_OPENAI_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),   # input $0.15/1M, output $0.60/1M
    "gpt-4o": (2.50, 10.00),       # input $2.50/1M, output $10.00/1M
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4o-2024-11-20": (2.50, 10.00),
}
_DEFAULT_PRICE = (1.0, 3.0)  # fallback per 1M tokens


def _estimate_tokens(text: str) -> int:
    """Estimate token count: words * 1.3."""
    return int(len(text.split()) * 1.3)


def _cost_openai(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD from token counts using published pricing."""
    prices = _OPENAI_PRICES.get(model, _DEFAULT_PRICE)
    input_per_m = prices[0] / 1_000_000
    output_per_m = prices[1] / 1_000_000
    return input_tokens * input_per_m + output_tokens * output_per_m


class OpenAIProvider(BaseProvider):
    """OpenAI API provider. Real SDK calls with structured logging on failure."""

    def __init__(self, api_key: str | None = None) -> None:
        """
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY from environment.
        """
        self._api_key = api_key

    def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str, float, float]:
        """Call OpenAI API; return (response_text, cost_usd, latency_ms)."""
        try:
            from openai import OpenAI
        except ImportError as e:
            logger.exception("openai package not installed")
            raise RuntimeError("OpenAI provider requires openai package") from e

        client = OpenAI(api_key=self._api_key)
        input_est = _estimate_tokens(prompt)
        start = time.perf_counter()

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            logger.exception("OpenAI API call failed: %s", e)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        content = response.choices[0].message.content or ""
        output_est = _estimate_tokens(content)
        cost = _cost_openai(model, input_est, output_est)
        return (content, cost, latency_ms)

    def name(self) -> str:
        """Return the provider name."""
        return "openai"
