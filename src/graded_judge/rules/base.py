"""
Abstract base for Tier 0 rules.
"""

import logging
from abc import ABC, abstractmethod

from graded_judge.models import EvaluationInput

logger = logging.getLogger(__name__)


class BaseRule(ABC):
    """Abstract base class for deterministic evaluation rules."""

    @abstractmethod
    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        """Return (passed, reason)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Rule name for reporting."""
        ...
