"""
Cost tracking: costs accumulate correctly, run summary math correct.
"""

import pytest
from graded_judge.models import EvaluationInput, EvaluationResult, TierResult
from graded_judge.cost import CostTracker
from graded_judge.reporting.summary import generate_run_summary


def test_cost_tracker_accumulates():
    """CostTracker adds cost and latency from multiple results."""
    tracker = CostTracker()
    inp = EvaluationInput(input="q", output="x", criteria="x")
    r1 = EvaluationResult(
        evaluation_id="1",
        input=inp,
        final_tier=1,
        passed=True,
        final_score=0.8,
        tier_results=[
            TierResult(tier=0, passed=True, escalated=False, cost_usd=0.0, latency_ms=1.0),
            TierResult(tier=1, passed=True, escalated=False, cost_usd=0.002, latency_ms=100.0),
        ],
        total_cost_usd=0.002,
        total_latency_ms=101.0,
        escalation_path=[0, 1],
    )
    r2 = EvaluationResult(
        evaluation_id="2",
        input=inp,
        final_tier=1,
        passed=False,
        final_score=0.5,
        tier_results=[
            TierResult(tier=0, passed=True, escalated=False, cost_usd=0.0, latency_ms=0.5),
            TierResult(tier=1, passed=False, escalated=True, cost_usd=0.003, latency_ms=120.0),
        ],
        total_cost_usd=0.003,
        total_latency_ms=120.5,
        escalation_path=[0, 1],
    )
    tracker.add_result(r1)
    tracker.add_result(r2)
    report = tracker.report()
    assert report.total_cost_usd == pytest.approx(0.005)
    assert report.total_latency_ms == pytest.approx(221.5)
    assert report.evaluation_count == 2
    assert report.average_cost_per_evaluation == pytest.approx(0.0025)
    assert report.cost_by_tier.get("tier0") == 0.0
    assert report.cost_by_tier.get("tier1") == pytest.approx(0.005)
    assert report.tier_invocation_counts.get("tier1") == 2


def test_run_summary_math():
    """generate_run_summary produces correct passed/failed and cost breakdown."""
    inp = EvaluationInput(input="q", output="x", criteria="x")
    results = [
        EvaluationResult(
            evaluation_id="1",
            input=inp,
            final_tier=0,
            passed=True,
            final_score=None,
            tier_results=[TierResult(tier=0, passed=True, escalated=False, cost_usd=0.0, latency_ms=2.0)],
            total_cost_usd=0.0,
            total_latency_ms=2.0,
            escalation_path=[0],
        ),
        EvaluationResult(
            evaluation_id="2",
            input=inp,
            final_tier=1,
            passed=True,
            final_score=0.8,
            tier_results=[
                TierResult(tier=0, passed=True, escalated=False, cost_usd=0.0, latency_ms=1.0),
                TierResult(tier=1, passed=True, escalated=False, cost_usd=0.01, latency_ms=50.0),
            ],
            total_cost_usd=0.01,
            total_latency_ms=51.0,
            escalation_path=[0, 1],
        ),
        EvaluationResult(
            evaluation_id="3",
            input=inp,
            final_tier=2,
            passed=False,
            final_score=0.4,
            tier_results=[
                TierResult(tier=0, passed=True, escalated=False, cost_usd=0.0, latency_ms=1.0),
                TierResult(tier=1, passed=False, escalated=True, cost_usd=0.01, latency_ms=50.0),
                TierResult(tier=2, passed=False, escalated=False, cost_usd=0.02, latency_ms=200.0),
            ],
            total_cost_usd=0.03,
            total_latency_ms=251.0,
            escalation_path=[0, 1, 2],
        ),
    ]
    summary = generate_run_summary(results)
    assert summary.total_evaluations == 3
    assert summary.passed == 2
    assert summary.failed == 1
    assert summary.total_cost_usd == pytest.approx(0.04)
    assert summary.average_cost_per_evaluation == pytest.approx(0.04 / 3)
    assert summary.average_latency_ms == pytest.approx((2 + 51 + 251) / 3)
    assert summary.cost_by_tier.get("tier0") == 0.0
    assert summary.tier_invocation_counts.get("tier2") == 1
    assert summary.escalations_to_tier2 == 1
