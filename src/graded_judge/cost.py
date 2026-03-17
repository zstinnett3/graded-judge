"""
Cost tracking and aggregation at the evaluation run level.
"""

import logging
from collections import defaultdict

from graded_judge.models import CostReport, EvaluationResult

logger = logging.getLogger(__name__)


class CostTracker:
    """Accumulates cost and latency across tier invocations in a session."""

    def __init__(self) -> None:
        self._total_cost: float = 0.0
        self._total_latency: float = 0.0
        self._evaluation_count: int = 0
        self._cost_by_tier: dict[str, float] = defaultdict(float)
        self._cost_by_provider: dict[str, float] = defaultdict(float)
        self._tier_invocation_counts: dict[str, int] = defaultdict(int)

    def add_result(self, result: EvaluationResult) -> None:
        """Record one evaluation result."""
        self._evaluation_count += 1
        self._total_cost += result.total_cost_usd
        self._total_latency += result.total_latency_ms
        for tr in result.tier_results:
            tier_key = f"tier{tr.tier}"
            self._cost_by_tier[tier_key] += tr.cost_usd
            self._tier_invocation_counts[tier_key] = self._tier_invocation_counts.get(tier_key, 0) + 1
            if tr.provider:
                self._cost_by_provider[tr.provider] += tr.cost_usd

    def report(self) -> CostReport:
        """Return a structured CostReport for the session."""
        avg_cost = self._total_cost / self._evaluation_count if self._evaluation_count else 0.0
        avg_latency = self._total_latency / self._evaluation_count if self._evaluation_count else 0.0
        return CostReport(
            total_cost_usd=self._total_cost,
            total_latency_ms=self._total_latency,
            evaluation_count=self._evaluation_count,
            average_cost_per_evaluation=avg_cost,
            average_latency_ms=avg_latency,
            cost_by_tier=dict(self._cost_by_tier),
            cost_by_provider=dict(self._cost_by_provider),
            tier_invocation_counts=dict(self._tier_invocation_counts),
        )

    def reset(self) -> None:
        """Clear accumulated data."""
        self._total_cost = 0.0
        self._total_latency = 0.0
        self._evaluation_count = 0
        self._cost_by_tier = defaultdict(float)
        self._cost_by_provider = defaultdict(float)
        self._tier_invocation_counts = defaultdict(int)
