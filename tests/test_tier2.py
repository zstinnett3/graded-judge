"""
Tier 2: mock provider final verdict, never escalates.
"""

import pytest
from graded_judge.models import EvaluationInput
from graded_judge.providers import MockProvider
from graded_judge.tiers import Tier2


def test_tier2_mock_returns_final_verdict():
    """Tier2 parses passed/score/reasoning and never escalates."""
    provider = MockProvider(
        response_text='{"reasoning": "Step by step.", "score": 0.9, "passed": true, "confidence": "high"}'
    )
    t2 = Tier2(provider=provider, model="mock", max_tokens=1024)
    inp = EvaluationInput(input="q", output="Paris", criteria="Capital?")
    r = t2.run(inp)
    assert r.tier == 2
    assert r.passed is True
    assert r.score == 0.9
    assert r.reasoning == "Step by step."
    assert r.escalated is False
    assert r.provider == "mock"
    assert r.cost_usd == 0.0


def test_tier2_never_escalates_even_on_fail():
    """Tier2 escalated is always False."""
    provider = MockProvider(
        response_text='{"reasoning": "Bad.", "score": 0.2, "passed": false, "confidence": "high"}'
    )
    t2 = Tier2(provider=provider, model="mock", max_tokens=1024)
    inp = EvaluationInput(input="q", output="wrong", criteria="x")
    r = t2.run(inp)
    assert r.passed is False
    assert r.escalated is False


def test_tier2_parse_failure_defaults_to_fail():
    """Invalid JSON yields passed=False, still no escalation."""
    provider = MockProvider(response_text="garbage")
    t2 = Tier2(provider=provider, model="mock", max_tokens=1024)
    inp = EvaluationInput(input="q", output="x", criteria="x")
    r = t2.run(inp)
    assert r.passed is False
    assert r.escalated is False
