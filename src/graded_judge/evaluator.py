"""
Main public interface. Users import GradedJudge and GradedJudgeConfig.
"""

import json
import logging
from pathlib import Path
from uuid import uuid4

from graded_judge.config import load_config
from graded_judge.cost import CostTracker
from graded_judge.models import (
    EvaluationInput,
    EvaluationResult,
    GradedJudgeConfig,
    RunSummary,
)
from graded_judge.pipeline import run_pipeline
from graded_judge.reporting.summary import generate_run_summary
from graded_judge.rules.base import BaseRule
from graded_judge.tiers.tier0 import Tier0
from graded_judge.tiers.tier1 import Tier1
from graded_judge.tiers.tier2 import Tier2

logger = logging.getLogger(__name__)


def _resolve_provider(name: str, tier: int):
    """Resolve provider by name. TODO: replace with real provider registry/env."""
    import os
    from graded_judge.providers import MockProvider, OpenAIProvider, BedrockProvider, OllamaProvider

    provider_name = name
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        return OpenAIProvider(api_key=os.environ.get("OPENAI_API_KEY"))
    if provider_name == "bedrock":
        return BedrockProvider(region_name=os.environ.get("AWS_REGION"))
    if provider_name == "ollama":
        return OllamaProvider()
    return MockProvider()


def _build_rules(config: GradedJudgeConfig) -> list[BaseRule]:
    """Build rule instances from config rule class names. Default: empty list."""
    from graded_judge.rules import (
        MinLengthRule,
        MaxLengthRule,
        ForbiddenPatternRule,
        RequiredPatternRule,
        JsonSchemaRule,
        NonEmptyRule,
    )
    registry = {
        "MinLengthRule": MinLengthRule,
        "MaxLengthRule": MaxLengthRule,
        "ForbiddenPatternRule": ForbiddenPatternRule,
        "RequiredPatternRule": RequiredPatternRule,
        "JsonSchemaRule": JsonSchemaRule,
        "NonEmptyRule": NonEmptyRule,
    }
    rules: list[BaseRule] = []
    for name in config.rules:
        if name in registry:
            # Config only has names; for parameterized rules we'd need config structure.
            # Spec says "rules: list[str] = []  # Rule class names"
            if name == "MinLengthRule":
                rules.append(MinLengthRule(1))
            elif name == "MaxLengthRule":
                rules.append(MaxLengthRule(10000))
            elif name == "NonEmptyRule":
                rules.append(NonEmptyRule())
            else:
                rules.append(registry[name]([] if "Pattern" in name else {}))
        else:
            logger.warning("Unknown rule name %s, skipping", name)
    return rules


class GradedJudge:
    """
    Primary public interface. Accepts GradedJudgeConfig or loads from YAML.
    Maintains session results and exposes evaluate(), evaluate_batch(), summarize(), export_results().
    """

    def __init__(
        self,
        config: GradedJudgeConfig | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        """
        Args:
            config: Use this config directly. If None, load from config_path or default.
            config_path: YAML file path. If config is None and path given, load from here.
        """
        if config is not None:
            self._config = config
        elif config_path is not None:
            self._config = GradedJudgeConfig.from_yaml(config_path)
        else:
            self._config = load_config()
        self._results: list[EvaluationResult] = []
        self._cost_tracker = CostTracker()
        self._run_id = str(uuid4())

        # Build tiers
        rules = _build_rules(self._config)
        self._tier0 = Tier0(rules, fail_threshold=self._config.tier0_fail_threshold) if rules or self._config.tier0_enabled else None
        if not self._tier0 and self._config.tier0_enabled:
            self._tier0 = Tier0([], fail_threshold=self._config.tier0_fail_threshold)

        p1 = _resolve_provider(self._config.tier1_provider, 1)
        self._tier1 = Tier1(
            p1,
            model=self._config.tier1_model,
            max_tokens=self._config.tier1_max_tokens,
            pass_threshold=self._config.tier1_pass_threshold,
        )
        p2 = _resolve_provider(self._config.tier2_provider, 2)
        self._tier2 = Tier2(
            p2,
            model=self._config.tier2_model,
            max_tokens=self._config.tier2_max_tokens,
        )

    def evaluate(
        self,
        input: str,
        output: str,
        criteria: str,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> EvaluationResult:
        """
        Run a single evaluation. Returns EvaluationResult and appends to session.
        """
        inp = EvaluationInput(
            input=input,
            output=output,
            criteria=criteria,
            reference=reference,
            metadata=metadata or {},
        )
        result = run_pipeline(
            inp,
            self._config,
            self._tier0,
            self._tier1,
            self._tier2,
        )
        self._results.append(result)
        if self._config.cost_tracking_enabled:
            self._cost_tracker.add_result(result)
        return result

    def evaluate_batch(self, inputs: list[EvaluationInput]) -> list[EvaluationResult]:
        """Run evaluations for each input. Appends all results to session."""
        results: list[EvaluationResult] = []
        for inp in inputs:
            r = run_pipeline(
                inp,
                self._config,
                self._tier0,
                self._tier1,
                self._tier2,
            )
            self._results.append(r)
            if self._config.cost_tracking_enabled:
                self._cost_tracker.add_result(r)
            results.append(r)
        return results

    def summarize(self) -> RunSummary:
        """Return RunSummary across all evaluations in this session."""
        return generate_run_summary(self._results, run_id=self._run_id)

    def export_results(self, path: str | Path) -> None:
        """Write all session results to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump(mode="json") for r in self._results]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
