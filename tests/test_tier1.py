"""
Tier 1: mock provider score, escalation below threshold, JSON parse failure escalates.
"""

import pytest
from graded_judge.models import EvaluationInput
from graded_judge.providers import MockProvider
from graded_judge.tiers import Tier1


def test_tier1_mock_returns_correct_score():
    """Mock provider response is parsed and score/reasoning returned."""
    provider = MockProvider(response_text='{"score": 0.8, "reasoning": "Good answer."}')
    t1 = Tier1(provider=provider, model="mock", max_tokens=512, pass_threshold=0.7)
    inp = EvaluationInput(input="q", output="Paris", criteria="Capital of France?")
    r = t1.run(inp)
    assert r.tier == 1
    assert r.score == 0.8
    assert r.reasoning == "Good answer."
    assert r.passed is True
    assert r.escalated is False
    assert r.provider == "mock"
    assert r.cost_usd == 0.0


def test_tier1_escalation_triggers_below_threshold():
    """Score below pass_threshold sets escalated=True."""
    provider = MockProvider(response_text='{"score": 0.5, "reasoning": "Weak."}')
    t1 = Tier1(provider=provider, model="mock", max_tokens=512, pass_threshold=0.7)
    inp = EvaluationInput(input="q", output="Nope", criteria="x")
    r = t1.run(inp)
    assert r.passed is False
    assert r.escalated is True
    assert r.score == 0.5


def test_tier1_at_threshold_passes():
    """Score exactly at threshold passes."""
    provider = MockProvider(response_text='{"score": 0.7, "reasoning": "OK."}')
    t1 = Tier1(provider=provider, model="mock", max_tokens=512, pass_threshold=0.7)
    inp = EvaluationInput(input="q", output="x", criteria="x")
    r = t1.run(inp)
    assert r.passed is True
    assert r.escalated is False


def test_tier1_json_parse_failure_escalates():
    """Invalid JSON response yields passed=False, escalated=True."""
    provider = MockProvider(response_text="not valid json at all")
    t1 = Tier1(provider=provider, model="mock", max_tokens=512, pass_threshold=0.7)
    inp = EvaluationInput(input="q", output="x", criteria="x")
    r = t1.run(inp)
    assert r.passed is False
    assert r.escalated is True
    assert r.score is None


def test_tier1_json_with_markdown_code_block():
    """Response with markdown code block still parsed."""
    provider = MockProvider(response_text='Here is the result:\n```json\n{"score": 0.9, "reasoning": "Great."}\n```')
    t1 = Tier1(provider=provider, model="mock", max_tokens=512, pass_threshold=0.7)
    inp = EvaluationInput(input="q", output="x", criteria="x")
    r = t1.run(inp)
    assert r.score == 0.9
    assert r.passed is True
