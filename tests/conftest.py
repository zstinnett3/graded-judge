"""
Pytest fixtures. Mock provider used for all tests; no real LLM calls.
"""

import pytest

from graded_judge.models import EvaluationInput, GradedJudgeConfig
from graded_judge.providers import MockProvider
from graded_judge.rules import NonEmptyRule, MinLengthRule
from graded_judge.tiers import Tier0, Tier1, Tier2


@pytest.fixture
def config() -> GradedJudgeConfig:
    """Default config with mock provider for tier1/tier2."""
    return GradedJudgeConfig(
        tier0_enabled=True,
        tier1_enabled=True,
        tier2_enabled=True,
        tier0_fail_threshold=1,
        tier1_pass_threshold=0.7,
        tier1_provider="mock",
        tier2_provider="mock",
        rules=[],
    )


@pytest.fixture
def mock_provider_pass():
    """Mock provider that returns a passing Tier1-style JSON."""
    return MockProvider(response_text='{"score": 0.85, "reasoning": "Looks good."}')


@pytest.fixture
def mock_provider_fail():
    """Mock provider that returns a failing score (below 0.7)."""
    return MockProvider(response_text='{"score": 0.5, "reasoning": "Below threshold."}')


@pytest.fixture
def mock_provider_tier2_pass():
    """Mock provider for Tier2 returning passed=True."""
    return MockProvider(
        response_text='{"reasoning": "Step by step.", "score": 0.9, "passed": true, "confidence": "high"}'
    )


@pytest.fixture
def sample_input() -> EvaluationInput:
    """Sample evaluation input."""
    return EvaluationInput(
        input="What is 2+2?",
        output="4",
        criteria="Answer must be correct.",
        reference=None,
    )


@pytest.fixture
def tier0_no_rules(config: GradedJudgeConfig) -> Tier0:
    """Tier0 with no rules (all pass)."""
    return Tier0(rules=[], fail_threshold=config.tier0_fail_threshold)


@pytest.fixture
def tier0_with_rules(config: GradedJudgeConfig) -> Tier0:
    """Tier0 with NonEmptyRule and MinLengthRule(1)."""
    return Tier0(
        rules=[NonEmptyRule(), MinLengthRule(1)],
        fail_threshold=config.tier0_fail_threshold,
    )
