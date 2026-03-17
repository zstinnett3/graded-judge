"""
Tier orchestration: run tiers in sequence, short-circuit when a tier passes without escalation.
"""

import logging
from uuid import uuid4

from graded_judge.models import (
    EvaluationInput,
    EvaluationResult,
    GradedJudgeConfig,
    TierResult,
)
from graded_judge.tiers.tier0 import Tier0
from graded_judge.tiers.tier1 import Tier1
from graded_judge.tiers.tier2 import Tier2

logger = logging.getLogger(__name__)


def run_pipeline(
    input: EvaluationInput,
    config: GradedJudgeConfig,
    tier0: Tier0 | None,
    tier1: Tier1 | None,
    tier2: Tier2 | None,
) -> EvaluationResult:
    """
    Run the tiered pipeline. Short-circuit when a tier passes without escalation.
    Track full tier_results and escalation_path.
    """
    evaluation_id = str(uuid4())
    tier_results: list[TierResult] = []
    escalation_path: list[int] = []
    total_cost = 0.0
    total_latency = 0.0
    final_tier = 0
    passed = False
    final_score: float | None = None

    if config.tier0_enabled and tier0 is not None:
        r0 = tier0.run(input)
        tier_results.append(r0)
        escalation_path.append(0)
        total_cost += r0.cost_usd
        total_latency += r0.latency_ms
        if r0.escalated:
            pass  # continue to tier1
        else:
            return EvaluationResult(
                evaluation_id=evaluation_id,
                input=input,
                final_tier=0,
                passed=r0.passed,
                final_score=None,
                tier_results=tier_results,
                total_cost_usd=total_cost,
                total_latency_ms=total_latency,
                escalation_path=escalation_path,
            )

    if config.tier1_enabled and tier1 is not None:
        r1 = tier1.run(input)
        tier_results.append(r1)
        escalation_path.append(1)
        total_cost += r1.cost_usd
        total_latency += r1.latency_ms
        final_tier = 1
        passed = r1.passed
        final_score = r1.score
        if r1.escalated:
            pass  # continue to tier2
        else:
            return EvaluationResult(
                evaluation_id=evaluation_id,
                input=input,
                final_tier=1,
                passed=passed,
                final_score=final_score,
                tier_results=tier_results,
                total_cost_usd=total_cost,
                total_latency_ms=total_latency,
                escalation_path=escalation_path,
            )

    if config.tier2_enabled and tier2 is not None:
        r2 = tier2.run(input)
        tier_results.append(r2)
        escalation_path.append(2)
        total_cost += r2.cost_usd
        total_latency += r2.latency_ms
        final_tier = 2
        passed = r2.passed
        final_score = r2.score
        return EvaluationResult(
            evaluation_id=evaluation_id,
            input=input,
            final_tier=2,
            passed=passed,
            final_score=final_score,
            tier_results=tier_results,
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
            escalation_path=escalation_path,
        )

    # No tier ran (all disabled) – use last result or default
    return EvaluationResult(
        evaluation_id=evaluation_id,
        input=input,
        final_tier=final_tier,
        passed=passed,
        final_score=final_score,
        tier_results=tier_results,
        total_cost_usd=total_cost,
        total_latency_ms=total_latency,
        escalation_path=escalation_path,
    )
