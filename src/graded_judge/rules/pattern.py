"""
Regex pattern rules for Tier 0.
"""

import re
import logging
from graded_judge.models import EvaluationInput
from graded_judge.rules.base import BaseRule

logger = logging.getLogger(__name__)


class ForbiddenPatternRule(BaseRule):
    """Fails if any of the regex patterns matches the output."""

    def __init__(self, patterns: list[str]) -> None:
        self._patterns = [re.compile(p) for p in patterns]

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        for pat in self._patterns:
            if pat.search(input.output):
                return (False, f"Forbidden pattern matched: {pat.pattern}")
        return (True, "No forbidden patterns matched")

    @property
    def name(self) -> str:
        return "ForbiddenPatternRule"


class RequiredPatternRule(BaseRule):
    """Fails if none of the regex patterns match the output."""

    def __init__(self, patterns: list[str]) -> None:
        self._patterns = [re.compile(p) for p in patterns]

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        for pat in self._patterns:
            if pat.search(input.output):
                return (True, f"Required pattern matched: {pat.pattern}")
        return (False, "No required pattern matched")

    @property
    def name(self) -> str:
        return "RequiredPatternRule"
