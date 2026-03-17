"""
All Pydantic data models for graded-judge. Import from this module everywhere.
"""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TierResult(BaseModel):
    """Result from a single tier evaluation."""

    tier: int  # 0, 1, or 2
    passed: bool
    score: float | None = None  # None for deterministic tiers that don't produce scores
    reasoning: str | None = None
    escalated: bool  # Whether this tier triggered escalation to next
    cost_usd: float = 0.0  # Cost of this tier evaluation (0.0 for Tier 0)
    latency_ms: float = 0.0
    provider: str | None = None  # None for Tier 0
    model: str | None = None  # None for Tier 0
    rules_applied: list[str] = Field(default_factory=list)  # Rule names applied (Tier 0 only)
    rule_failures: list[str] = Field(default_factory=list)  # Rule names that failed (Tier 0 only)


class EvaluationInput(BaseModel):
    """Input for a single evaluation."""

    input: str  # The original prompt or question
    output: str  # The LLM output being evaluated
    criteria: str  # Plain English description of what good looks like
    reference: str | None = None  # Optional reference answer for comparison
    metadata: dict = Field(default_factory=dict)  # Passthrough metadata


class EvaluationResult(BaseModel):
    """Full result of an evaluation run through the tiered pipeline."""

    evaluation_id: str  # UUID
    input: EvaluationInput
    final_tier: int  # Which tier produced the final verdict
    passed: bool  # Final pass/fail verdict
    final_score: float | None = None  # Final score if applicable
    tier_results: list[TierResult] = Field(default_factory=list)  # Full result chain
    total_cost_usd: float = 0.0  # Sum of all tier costs
    total_latency_ms: float = 0.0
    escalation_path: list[int] = Field(default_factory=list)  # e.g. [0, 1] means Tier 0 -> Tier 1


class RunSummary(BaseModel):
    """Summary of a run across all evaluations in a session."""

    run_id: str
    total_evaluations: int
    passed: int
    failed: int
    escalations_to_tier1: int
    escalations_to_tier2: int
    total_cost_usd: float
    average_cost_per_evaluation: float
    average_latency_ms: float
    cost_by_tier: dict[str, float] = Field(default_factory=dict)  # {"tier0": 0.0, "tier1": x, ...}
    tier_invocation_counts: dict[str, int] = Field(default_factory=dict)


class CostReport(BaseModel):
    """Structured cost report for a session."""

    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    evaluation_count: int = 0
    average_cost_per_evaluation: float = 0.0
    average_latency_ms: float = 0.0
    cost_by_tier: dict[str, float] = Field(default_factory=dict)
    cost_by_provider: dict[str, float] = Field(default_factory=dict)
    tier_invocation_counts: dict[str, int] = Field(default_factory=dict)


class GradedJudgeConfig(BaseModel):
    """Configuration for the graded-judge pipeline."""

    tier0_enabled: bool = True
    tier1_enabled: bool = True
    tier2_enabled: bool = True
    tier0_fail_threshold: int = 1  # Number of rule failures before escalation
    tier1_pass_threshold: float = 0.7  # Score below this triggers escalation to Tier 2
    tier1_model: str = "gpt-4o-mini"
    tier2_model: str = "gpt-4o"
    tier1_provider: str = "openai"
    tier2_provider: str = "openai"
    tier1_max_tokens: int = 512
    tier2_max_tokens: int = 1024
    rules: list[str] = Field(default_factory=list)  # Rule class names to apply at Tier 0
    cost_tracking_enabled: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "GradedJudgeConfig":
        """Load config from a YAML file."""
        p = Path(path)
        if not p.is_file():
            return cls()
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return cls()
        return cls.model_validate(data)
