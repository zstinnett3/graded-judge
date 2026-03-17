"""
Built-in rules: each rule passes and fails on appropriate inputs.
"""

import pytest
from graded_judge.models import EvaluationInput
from graded_judge.rules import (
    MinLengthRule,
    MaxLengthRule,
    ForbiddenPatternRule,
    RequiredPatternRule,
    JsonSchemaRule,
    NonEmptyRule,
)


def test_min_length_rule():
    """MinLengthRule passes/fails by length."""
    rule = MinLengthRule(5)
    assert rule.check(EvaluationInput(input="q", output="hello", criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output="hi", criteria="x"))[0] is False
    assert rule.name == "MinLengthRule"


def test_max_length_rule():
    """MaxLengthRule passes/fails by length."""
    rule = MaxLengthRule(5)
    assert rule.check(EvaluationInput(input="q", output="hi", criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output="hello world", criteria="x"))[0] is False
    assert rule.name == "MaxLengthRule"


def test_forbidden_pattern_rule():
    """ForbiddenPatternRule fails when pattern matches."""
    rule = ForbiddenPatternRule(patterns=[r"secret", r"\bNOPE\b"])
    assert rule.check(EvaluationInput(input="q", output="this is fine", criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output="do not say secret", criteria="x"))[0] is False
    assert rule.check(EvaluationInput(input="q", output="NOPE allowed", criteria="x"))[0] is False


def test_required_pattern_rule():
    """RequiredPatternRule fails when no pattern matches."""
    rule = RequiredPatternRule(patterns=[r"yes", r"\d+"])
    assert rule.check(EvaluationInput(input="q", output="yes indeed", criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output="answer 42", criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output="nothing here", criteria="x"))[0] is False


def test_json_schema_rule():
    """JsonSchemaRule validates JSON and schema."""
    rule = JsonSchemaRule(schema={"type": "object", "required": ["status"]})
    assert rule.check(EvaluationInput(input="q", output='{"status": "ok"}', criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output='{"other": 1}', criteria="x"))[0] is False
    assert rule.check(EvaluationInput(input="q", output="not json", criteria="x"))[0] is False


def test_non_empty_rule():
    """NonEmptyRule fails on empty or whitespace."""
    rule = NonEmptyRule()
    assert rule.check(EvaluationInput(input="q", output="x", criteria="x"))[0] is True
    assert rule.check(EvaluationInput(input="q", output="", criteria="x"))[0] is False
    assert rule.check(EvaluationInput(input="q", output="   \n\t", criteria="x"))[0] is False
    assert rule.name == "NonEmptyRule"
