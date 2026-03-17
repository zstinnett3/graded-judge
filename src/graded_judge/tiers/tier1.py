"""
Tier 1: fast, low-cost LLM judge. Returns score 0.0–1.0; escalates if below threshold.
"""

import json
import logging
import re
from graded_judge.models import EvaluationInput, TierResult
from graded_judge.providers.base import BaseProvider
from graded_judge.tiers.base import BaseTier

logger = logging.getLogger(__name__)

TIER1_PROMPT = """You are an evaluator. Score the following output against the criteria.

Input (prompt/question):
{input}

Output to evaluate:
{output}

Criteria (what good looks like):
{criteria}
{reference_block}

Respond with a single JSON object only, no other text:
{{"score": <float 0.0 to 1.0>, "reasoning": "<one sentence explanation>"}}
"""


def _build_tier1_prompt(inp: EvaluationInput) -> str:
    reference_block = ""
    if inp.reference:
        reference_block = f"\nReference answer (for comparison):\n{inp.reference}"
    return TIER1_PROMPT.format(
        input=inp.input,
        output=inp.output,
        criteria=inp.criteria,
        reference_block=reference_block,
    )


def _parse_tier1_response(text: str) -> tuple[float | None, str | None]:
    """Extract score and reasoning from JSON. Returns (score, reasoning) or (None, None) on failure."""
    # Allow optional markdown code block
    stripped = text.strip()
    m = re.search(r"\{[\s\S]*\}", stripped)
    if not m:
        return (None, None)
    try:
        data = json.loads(m.group(0))
        score = data.get("score")
        reasoning = data.get("reasoning")
        if score is not None and isinstance(score, (int, float)):
            score = float(score)
            if score < 0:
                score = 0.0
            if score > 1:
                score = 1.0
        else:
            score = None
        if reasoning is not None:
            reasoning = str(reasoning)
        else:
            reasoning = None
        return (score, reasoning)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Tier1 JSON parse failed: %s", e)
        return (None, None)


class Tier1(BaseTier):
    """Fast LLM judge. Escalates to Tier 2 when score < pass_threshold or parse fails."""

    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        max_tokens: int,
        pass_threshold: float,
    ) -> None:
        self._provider = provider
        self._model = model
        self._max_tokens = max_tokens
        self._pass_threshold = pass_threshold

    def run(self, input: EvaluationInput) -> TierResult:
        """Call fast LLM; parse score/reasoning; escalate if score < threshold or parse fails."""
        prompt = _build_tier1_prompt(input)
        response_text, cost_usd, latency_ms = self._provider.complete(
            prompt=prompt,
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=0.0,
        )
        score, reasoning = _parse_tier1_response(response_text)

        if score is None:
            logger.warning("Tier1 parse failure; escalating to Tier 2")
            return TierResult(
                tier=1,
                passed=False,
                score=None,
                reasoning=reasoning,
                escalated=True,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                provider=self._provider.name(),
                model=self._model,
                rules_applied=[],
                rule_failures=[],
            )

        passed = score >= self._pass_threshold
        escalated = not passed

        return TierResult(
            tier=1,
            passed=passed,
            score=score,
            reasoning=reasoning,
            escalated=escalated,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider=self._provider.name(),
            model=self._model,
            rules_applied=[],
            rule_failures=[],
        )
