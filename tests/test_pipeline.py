"""
Pipeline: short-circuit at Tier 0, Tier 1; full escalation to Tier 2; disabled tiers skipped.
"""

import pytest
from graded_judge.models import EvaluationInput, GradedJudgeConfig
from graded_judge.providers import MockProvider
from graded_judge.rules import NonEmptyRule, MinLengthRule
from graded_judge.tiers import Tier0, Tier1, Tier2
from graded_judge.pipeline import run_pipeline


def test_short_circuit_at_tier0():
    """When Tier0 passes and does not escalate, pipeline returns without calling Tier1."""
    config = GradedJudgeConfig(
        tier0_enabled=True,
        tier1_enabled=True,
        tier2_enabled=True,
        tier0_fail_threshold=1,
        tier1_provider="mock",
        tier2_provider="mock",
    )
    tier0 = Tier0(rules=[NonEmptyRule()], fail_threshold=1)
    tier1 = Tier1(MockProvider(response_text='{"score":0.8,"reasoning":"x"}'), "mock", 512, 0.7)
    tier2 = Tier2(MockProvider(response_text='{"reasoning":"x","score":0.9,"passed":true,"confidence":"high"}'), "mock", 1024)
    inp = EvaluationInput(input="q", output="hello", criteria="x")
    result = run_pipeline(inp, config, tier0, tier1, tier2)
    assert result.final_tier == 0
    assert len(result.tier_results) == 1
    assert result.escalation_path == [0]
    assert result.passed is True


def test_short_circuit_at_tier1():
    """When Tier0 escalates and Tier1 passes (score >= threshold), pipeline stops at Tier1."""
    config = GradedJudgeConfig(
        tier0_enabled=True,
        tier1_enabled=True,
        tier2_enabled=True,
        tier0_fail_threshold=1,
        tier1_pass_threshold=0.7,
        tier1_provider="mock",
        tier2_provider="mock",
    )
    tier0 = Tier0(rules=[MinLengthRule(100)], fail_threshold=1)  # always fails -> escalate
    tier1 = Tier1(MockProvider(response_text='{"score": 0.85, "reasoning": "Good."}'), "mock", 512, 0.7)
    tier2 = Tier2(MockProvider(response_text='{"reasoning":"x","score":0.9,"passed":true,"confidence":"high"}'), "mock", 1024)
    inp = EvaluationInput(input="q", output="short", criteria="x")
    result = run_pipeline(inp, config, tier0, tier1, tier2)
    assert result.final_tier == 1
    assert len(result.tier_results) == 2
    assert result.escalation_path == [0, 1]
    assert result.passed is True
    assert result.final_score == 0.85


def test_full_escalation_to_tier2():
    """Tier0 escalates, Tier1 score below threshold -> Tier2 gives final verdict."""
    config = GradedJudgeConfig(
        tier0_enabled=True,
        tier1_enabled=True,
        tier2_enabled=True,
        tier0_fail_threshold=1,
        tier1_pass_threshold=0.7,
        tier1_provider="mock",
        tier2_provider="mock",
    )
    tier0 = Tier0(rules=[MinLengthRule(100)], fail_threshold=1)
    tier1 = Tier1(MockProvider(response_text='{"score": 0.5, "reasoning": "Weak."}'), "mock", 512, 0.7)
    tier2 = Tier2(
        MockProvider(response_text='{"reasoning": "Detailed.", "score": 0.9, "passed": true, "confidence": "high"}'),
        "mock",
        1024,
    )
    inp = EvaluationInput(input="q", output="short", criteria="x")
    result = run_pipeline(inp, config, tier0, tier1, tier2)
    assert result.final_tier == 2
    assert len(result.tier_results) == 3
    assert result.escalation_path == [0, 1, 2]
    assert result.passed is True
    assert result.final_score == 0.9


def test_disabled_tier0_skipped():
    """With tier0_enabled=False, only Tier1 and Tier2 are used; first run is Tier1."""
    config = GradedJudgeConfig(
        tier0_enabled=False,
        tier1_enabled=True,
        tier2_enabled=True,
        tier1_pass_threshold=0.7,
        tier1_provider="mock",
        tier2_provider="mock",
    )
    tier1 = Tier1(MockProvider(response_text='{"score": 0.8, "reasoning": "OK."}'), "mock", 512, 0.7)
    tier2 = Tier2(MockProvider(response_text='{"reasoning":"x","score":0.9,"passed":true,"confidence":"high"}'), "mock", 1024)
    inp = EvaluationInput(input="q", output="anything", criteria="x")
    result = run_pipeline(inp, config, None, tier1, tier2)
    assert result.final_tier == 1
    assert len(result.tier_results) == 1
    assert result.tier_results[0].tier == 1


def test_disabled_tier1_skipped():
    """With tier1_enabled=False, Tier0 escalates directly to Tier2."""
    config = GradedJudgeConfig(
        tier0_enabled=True,
        tier1_enabled=False,
        tier2_enabled=True,
        tier0_fail_threshold=1,
        tier2_provider="mock",
    )
    tier0 = Tier0(rules=[MinLengthRule(100)], fail_threshold=1)
    tier2 = Tier2(
        MockProvider(response_text='{"reasoning": "x", "score": 0.88, "passed": true, "confidence": "high"}'),
        "mock",
        1024,
    )
    inp = EvaluationInput(input="q", output="short", criteria="x")
    result = run_pipeline(inp, config, tier0, None, tier2)
    assert result.final_tier == 2
    assert len(result.tier_results) == 2  # tier0, tier2
    assert result.tier_results[0].tier == 0
    assert result.tier_results[1].tier == 2
