"""
Abstract base for evaluation tiers.
"""

import logging
from abc import ABC, abstractmethod

from graded_judge.models import EvaluationInput, TierResult

logger = logging.getLogger(__name__)


class BaseTier(ABC):
    """Abstract base for Tier 0, 1, and 2."""

    @abstractmethod
    def run(self, input: EvaluationInput) -> TierResult:
        """Run this tier and return a TierResult."""
        ...
