"""
Tier 2: slow, high-accuracy LLM judge. Extended chain-of-thought; never escalates.
"""

import json
import logging
import re
from graded_judge.models import EvaluationInput, TierResult
from graded_judge.providers.base import BaseProvider
from graded_judge.tiers.base import BaseTier

logger = logging.getLogger(__name__)

TIER2_PROMPT = """You are an expert evaluator. Reason step by step, then give a final verdict.

Input (prompt/question):
{input}

Output to evaluate:
{output}

Criteria (what good looks like):
{criteria}
{reference_block}

First reason through each criterion step by step. Then output a single JSON object only, no other text after it:
{{"reasoning": "<extended step-by-step reasoning>", "score": <float 0.0 to 1.0>, "passed": <true or false>, "confidence": "high"|"medium"|"low"}}
"""


def _build_tier2_prompt(inp: EvaluationInput) -> str:
    reference_block = ""
    if inp.reference:
        reference_block = f"\nReference answer (for comparison):\n{inp.reference}"
    return TIER2_PROMPT.format(
        input=inp.input,
        output=inp.output,
        criteria=inp.criteria,
        reference_block=reference_block,
    )


def _parse_tier2_response(text: str) -> tuple[bool, float | None, str | None]:
    """Extract passed, score, reasoning. Returns (passed, score, reasoning). Defaults on parse failure."""
    stripped = text.strip()
    m = re.search(r"\{[\s\S]*\}", stripped)
    if not m:
        return (False, None, None)
    try:
        data = json.loads(m.group(0))
        passed = data.get("passed")
        if isinstance(passed, bool):
            pass
        elif isinstance(passed, str):
            passed = passed.lower() in ("true", "1", "yes")
        else:
            passed = False
        score = data.get("score")
        if score is not None and isinstance(score, (int, float)):
            score = float(score)
            if score < 0:
                score = 0.0
            if score > 1:
                score = 1.0
        else:
            score = None
        reasoning = data.get("reasoning")
        if reasoning is not None:
            reasoning = str(reasoning)
        else:
            reasoning = None
        return (passed, score, reasoning)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Tier2 JSON parse failed: %s", e)
        return (False, None, None)


class Tier2(BaseTier):
    """Slow LLM judge. Final verdict; never escalates."""

    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        max_tokens: int,
    ) -> None:
        self._provider = provider
        self._model = model
        self._max_tokens = max_tokens

    def run(self, input: EvaluationInput) -> TierResult:
        """Call slow LLM; parse verdict. Never escalate."""
        prompt = _build_tier2_prompt(input)
        response_text, cost_usd, latency_ms = self._provider.complete(
            prompt=prompt,
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=0.0,
        )
        passed, score, reasoning = _parse_tier2_response(response_text)

        return TierResult(
            tier=2,
            passed=passed,
            score=score,
            reasoning=reasoning,
            escalated=False,  # Tier 2 never escalates
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider=self._provider.name(),
            model=self._model,
            rules_applied=[],
            rule_failures=[],
        )
