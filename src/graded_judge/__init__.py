"""
graded-judge: Tiered LLM evaluation with deterministic pre-filtering and cost-aware escalation.
"""

from graded_judge.evaluator import GradedJudge
from graded_judge.models import (
    EvaluationInput,
    EvaluationResult,
    GradedJudgeConfig,
    RunSummary,
    TierResult,
)

__all__ = [
    "GradedJudge",
    "GradedJudgeConfig",
    "EvaluationInput",
    "EvaluationResult",
    "TierResult",
    "RunSummary",
]

__version__ = "0.1.0"
