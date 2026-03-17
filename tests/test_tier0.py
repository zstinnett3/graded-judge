"""
Tier 0: rule pass/fail and escalation threshold logic.
"""

import pytest
from graded_judge.models import EvaluationInput
from graded_judge.rules import NonEmptyRule, MinLengthRule, MaxLengthRule
from graded_judge.rules import ForbiddenPatternRule, RequiredPatternRule, JsonSchemaRule
from graded_judge.tiers import Tier0


def test_tier0_no_rules_all_pass():
    """With no rules, Tier0 should pass and not escalate."""
    t0 = Tier0(rules=[], fail_threshold=1)
    inp = EvaluationInput(input="q", output="", criteria="x")
    r = t0.run(inp)
    assert r.tier == 0
    assert r.passed is True
    assert r.escalated is False
    assert r.cost_usd == 0.0
    assert r.provider is None


def test_tier0_non_empty_fails_on_empty():
    """NonEmptyRule fails on empty output."""
    t0 = Tier0(rules=[NonEmptyRule()], fail_threshold=1)
    inp = EvaluationInput(input="q", output="", criteria="x")
    r = t0.run(inp)
    assert r.passed is False
    assert r.escalated is True
    assert "NonEmptyRule" in r.rule_failures


def test_tier0_non_empty_passes_on_non_empty():
    """NonEmptyRule passes when output has content."""
    t0 = Tier0(rules=[NonEmptyRule()], fail_threshold=1)
    inp = EvaluationInput(input="q", output="hello", criteria="x")
    r = t0.run(inp)
    assert r.passed is True
    assert r.escalated is False
    assert r.rule_failures == []


def test_tier0_min_length_fails_below():
    """MinLengthRule fails when output is shorter than min_chars."""
    t0 = Tier0(rules=[MinLengthRule(10)], fail_threshold=1)
    inp = EvaluationInput(input="q", output="hi", criteria="x")
    r = t0.run(inp)
    assert r.passed is False
    assert r.escalated is True


def test_tier0_min_length_passes_at_or_above():
    """MinLengthRule passes when output meets min length."""
    t0 = Tier0(rules=[MinLengthRule(3)], fail_threshold=1)
    inp = EvaluationInput(input="q", output="yes", criteria="x")
    r = t0.run(inp)
    assert r.passed is True
    assert r.escalated is False


def test_tier0_fail_threshold_two_failures_escalate():
    """With fail_threshold=1, two rule failures should escalate."""
    t0 = Tier0(rules=[MinLengthRule(100), NonEmptyRule()], fail_threshold=1)
    inp = EvaluationInput(input="q", output="short", criteria="x")
    r = t0.run(inp)
    assert r.passed is False
    assert r.escalated is True
    assert len(r.rule_failures) >= 1


def test_tier0_fail_threshold_zero_no_escalate():
    """With fail_threshold=0, any failure escalates."""
    t0 = Tier0(rules=[NonEmptyRule()], fail_threshold=1)
    inp = EvaluationInput(input="q", output="ok", criteria="x")
    r = t0.run(inp)
    assert r.passed is True


def test_tier0_max_length_fails_above():
    """MaxLengthRule fails when output exceeds max_chars."""
    t0 = Tier0(rules=[MaxLengthRule(2)], fail_threshold=1)
    inp = EvaluationInput(input="q", output="hello", criteria="x")
    r = t0.run(inp)
    assert r.passed is False
    assert r.escalated is True


def test_tier0_max_length_passes_at_or_below():
    """MaxLengthRule passes when output within max."""
    t0 = Tier0(rules=[MaxLengthRule(10)], fail_threshold=1)
    inp = EvaluationInput(input="q", output="hi", criteria="x")
    r = t0.run(inp)
    assert r.passed is True


def test_tier0_forbidden_pattern_fails_on_match():
    """ForbiddenPatternRule fails when a pattern matches."""
    t0 = Tier0(rules=[ForbiddenPatternRule(patterns=[r"bad\s+word"])], fail_threshold=1)
    inp = EvaluationInput(input="q", output="This has a bad word here", criteria="x")
    r = t0.run(inp)
    assert r.passed is False
    assert r.escalated is True


def test_tier0_required_pattern_fails_when_none_match():
    """RequiredPatternRule fails when no pattern matches."""
    t0 = Tier0(rules=[RequiredPatternRule(patterns=[r"\d+"])], fail_threshold=1)
    inp = EvaluationInput(input="q", output="no digits here", criteria="x")
    r = t0.run(inp)
    assert r.passed is False


def test_tier0_required_pattern_passes_when_one_matches():
    """RequiredPatternRule passes when at least one pattern matches."""
    t0 = Tier0(rules=[RequiredPatternRule(patterns=[r"\d+"])], fail_threshold=1)
    inp = EvaluationInput(input="q", output="Answer is 42", criteria="x")
    r = t0.run(inp)
    assert r.passed is True


def test_tier0_json_schema_fails_invalid_json():
    """JsonSchemaRule fails on invalid JSON."""
    t0 = Tier0(rules=[JsonSchemaRule(schema={"type": "object"})], fail_threshold=1)
    inp = EvaluationInput(input="q", output="not json at all", criteria="x")
    r = t0.run(inp)
    assert r.passed is False


def test_tier0_json_schema_passes_valid():
    """JsonSchemaRule passes when output is valid JSON matching schema."""
    t0 = Tier0(rules=[JsonSchemaRule(schema={"type": "object"})], fail_threshold=1)
    inp = EvaluationInput(input="q", output='{"key": "value"}', criteria="x")
    r = t0.run(inp)
    assert r.passed is True
