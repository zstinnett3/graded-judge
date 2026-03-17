"""
Run summary and human-readable cost/escalation report.
"""

import logging
from uuid import uuid4

from graded_judge.models import EvaluationResult, RunSummary

logger = logging.getLogger(__name__)


def generate_run_summary(
    results: list[EvaluationResult],
    run_id: str | None = None,
) -> RunSummary:
    """Build RunSummary from a list of evaluation results."""
    rid = run_id or str(uuid4())
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    escalations_t1 = sum(1 for r in results if 1 in r.escalation_path and r.final_tier >= 1)
    escalations_t2 = sum(1 for r in results if 2 in r.escalation_path)
    total_cost = sum(r.total_cost_usd for r in results)
    total_latency = sum(r.total_latency_ms for r in results)
    avg_cost = total_cost / total if total else 0.0
    avg_latency = total_latency / total if total else 0.0

    cost_by_tier: dict[str, float] = {"tier0": 0.0, "tier1": 0.0, "tier2": 0.0}
    tier_invocation_counts: dict[str, int] = {"tier0": 0, "tier1": 0, "tier2": 0}
    for r in results:
        for tr in r.tier_results:
            key = f"tier{tr.tier}"
            cost_by_tier[key] = cost_by_tier.get(key, 0) + tr.cost_usd
            tier_invocation_counts[key] = tier_invocation_counts.get(key, 0) + 1

    return RunSummary(
        run_id=rid,
        total_evaluations=total,
        passed=passed,
        failed=failed,
        escalations_to_tier1=escalations_t1,
        escalations_to_tier2=escalations_t2,
        total_cost_usd=total_cost,
        average_cost_per_evaluation=avg_cost,
        average_latency_ms=avg_latency,
        cost_by_tier=cost_by_tier,
        tier_invocation_counts=tier_invocation_counts,
    )


def print_summary(summary: RunSummary) -> None:
    """Print a human-readable cost and escalation report to stdout."""
    t0_cost = summary.cost_by_tier.get("tier0", 0)
    t1_cost = summary.cost_by_tier.get("tier1", 0)
    t2_cost = summary.cost_by_tier.get("tier2", 0)
    t0_count = summary.tier_invocation_counts.get("tier0", 0)
    t1_count = summary.tier_invocation_counts.get("tier1", 0)
    t2_count = summary.tier_invocation_counts.get("tier2", 0)

    lines = [
        "graded-judge run summary",
        "------------------------",
        f"Total evaluations : {summary.total_evaluations}",
        f"Passed            : {summary.passed}",
        f"Failed            : {summary.failed}",
        f"Tier 0 only       : {t0_count} (cost: ${t0_cost:.2f})",
        f"Tier 1 invoked    : {t1_count} (cost: ${t1_cost:.3f})",
        f"Tier 2 invoked    : {t2_count} (cost: ${t2_cost:.3f})",
        f"Total cost        : ${summary.total_cost_usd:.3f}",
        f"Avg cost/eval     : ${summary.average_cost_per_evaluation:.6f}",
        f"Avg latency       : {summary.average_latency_ms:.0f}ms",
    ]
    print("\n".join(lines))
