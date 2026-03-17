"""
Length-based rules for Tier 0.
"""

import logging
from graded_judge.models import EvaluationInput
from graded_judge.rules.base import BaseRule

logger = logging.getLogger(__name__)


class MinLengthRule(BaseRule):
    """Fails if output is shorter than min_chars."""

    def __init__(self, min_chars: int) -> None:
        self._min_chars = min_chars

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        n = len(input.output)
        if n < self._min_chars:
            return (False, f"Output length {n} is below minimum {self._min_chars} characters")
        return (True, f"Output length {n} meets minimum {self._min_chars}")

    @property
    def name(self) -> str:
        return "MinLengthRule"


class MaxLengthRule(BaseRule):
    """Fails if output is longer than max_chars."""

    def __init__(self, max_chars: int) -> None:
        self._max_chars = max_chars

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        n = len(input.output)
        if n > self._max_chars:
            return (False, f"Output length {n} exceeds maximum {self._max_chars} characters")
        return (True, f"Output length {n} within maximum {self._max_chars}")

    @property
    def name(self) -> str:
        return "MaxLengthRule"
