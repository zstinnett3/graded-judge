"""
Tier 0: deterministic rule-based checks. No LLM calls.
"""

import logging
import time
from graded_judge.models import EvaluationInput, TierResult
from graded_judge.rules.base import BaseRule
from graded_judge.tiers.base import BaseTier

logger = logging.getLogger(__name__)


class Tier0(BaseTier):
    """Applies configurable rules; escalates when failures >= fail_threshold."""

    def __init__(self, rules: list[BaseRule], fail_threshold: int = 1) -> None:
        self._rules = rules
        self._fail_threshold = fail_threshold

    def run(self, input: EvaluationInput) -> TierResult:
        """Run all rules. Pass if failures < threshold; else escalate."""
        start = time.perf_counter()
        applied: list[str] = []
        failures: list[str] = []
        for rule in self._rules:
            applied.append(rule.name)
            passed, reason = rule.check(input)
            if not passed:
                failures.append(rule.name)
                logger.debug("Tier0 rule %s failed: %s", rule.name, reason)

        failed_count = len(failures)
        passed = failed_count < self._fail_threshold
        escalated = failed_count >= self._fail_threshold
        latency_ms = (time.perf_counter() - start) * 1000

        return TierResult(
            tier=0,
            passed=passed,
            score=None,
            reasoning=None,
            escalated=escalated,
            cost_usd=0.0,
            latency_ms=latency_ms,
            provider=None,
            model=None,
            rules_applied=applied,
            rule_failures=failures,
        )
