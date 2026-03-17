"""
AWS Bedrock provider. Uses published per-token pricing for Claude models.
"""

import logging
import time
from graded_judge.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Published per-1M token pricing (input, output) for Claude on Bedrock.
_BEDROCK_PRICES: dict[str, tuple[float, float]] = {
    "anthropic.claude-3-5-sonnet-20241022-v2:0": (3.0, 15.0),
    "anthropic.claude-3-5-sonnet-v2:0": (3.0, 15.0),
    "anthropic.claude-3-5-sonnet-20240620-v1:0": (3.0, 15.0),
    "anthropic.claude-3-sonnet-20240229-v1:0": (3.0, 15.0),
    "anthropic.claude-3-haiku-20240307-v1:0": (0.25, 1.25),
    "anthropic.claude-3-opus-20240229-v1:0": (15.0, 75.0),
}
_DEFAULT_BEDROCK_PRICE = (3.0, 15.0)


def _estimate_tokens(text: str) -> int:
    """Estimate token count: words * 1.3."""
    return int(len(text.split()) * 1.3)


def _cost_bedrock(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD from token counts using published pricing."""
    prices = _BEDROCK_PRICES.get(model, _DEFAULT_BEDROCK_PRICE)
    input_per_m = prices[0] / 1_000_000
    output_per_m = prices[1] / 1_000_000
    return input_tokens * input_per_m + output_tokens * output_per_m


class BedrockProvider(BaseProvider):
    """AWS Bedrock provider. Real SDK calls with structured logging on failure."""

    def __init__(self, region_name: str | None = None) -> None:
        """
        Args:
            region_name: AWS region for Bedrock. If None, uses AWS_REGION or default.
        """
        self._region_name = region_name

    def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str, float, float]:
        """Call Bedrock API; return (response_text, cost_usd, latency_ms)."""
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as e:
            logger.exception("boto3 not installed")
            raise RuntimeError("Bedrock provider requires boto3") from e

        client = boto3.client("bedrock-runtime", region_name=self._region_name)
        input_est = _estimate_tokens(prompt)
        start = time.perf_counter()

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }

        try:
            response = client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=bytes(__import__("json").dumps(body), "utf-8"),
            )
        except (BotoCoreError, ClientError) as e:
            logger.exception("Bedrock API call failed: %s", e)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        import json as _json
        payload = _json.loads(response["body"].read())
        content = ""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        output_est = _estimate_tokens(content)
        cost = _cost_bedrock(model, input_est, output_est)
        return (content, cost, latency_ms)

    def name(self) -> str:
        """Return the provider name."""
        return "bedrock"
