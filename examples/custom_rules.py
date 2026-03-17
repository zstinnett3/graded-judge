"""
Custom rules: implement BaseRule and pass instances to Tier0.
"""

from graded_judge.models import EvaluationInput, GradedJudgeConfig
from graded_judge.rules.base import BaseRule
from graded_judge.tiers.tier0 import Tier0
from graded_judge.providers import MockProvider
from graded_judge.tiers import Tier1, Tier2
from graded_judge.pipeline import run_pipeline


class MustContainAnswerRule(BaseRule):
    """Custom rule: output must contain the substring 'answer:' (case-insensitive)."""

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        if "answer:" in input.output.lower():
            return (True, "Output contains 'answer:'")
        return (False, "Output missing 'answer:'")

    @property
    def name(self) -> str:
        return "MustContainAnswerRule"


def main():
    config = GradedJudgeConfig(
        tier0_enabled=True,
        tier1_enabled=True,
        tier2_enabled=True,
        tier1_provider="mock",
        tier2_provider="mock",
    )
    custom_rules = [MustContainAnswerRule()]
    tier0 = Tier0(rules=custom_rules, fail_threshold=1)
    tier1 = Tier1(
        MockProvider(response_text='{"score": 0.9, "reasoning": "Has answer."}'),
        "mock",
        512,
        0.7,
    )
    tier2 = Tier2(
        MockProvider(response_text='{"reasoning": "x", "score": 0.9, "passed": true, "confidence": "high"}'),
        "mock",
        1024,
    )

    # This will fail Tier0 (no "answer:" in output)
    inp_fail = EvaluationInput(
        input="What is 2+2?",
        output="Four",
        criteria="Must include answer: prefix.",
    )
    result_fail = run_pipeline(inp_fail, config, tier0, tier1, tier2)
    print(f"Without 'answer:': passed={result_fail.passed}, tier={result_fail.final_tier}")

    # This passes Tier0
    inp_pass = EvaluationInput(
        input="What is 2+2?",
        output="answer: 4",
        criteria="Must include answer: prefix.",
    )
    result_pass = run_pipeline(inp_pass, config, tier0, tier1, tier2)
    print(f"With 'answer:': passed={result_pass.passed}, tier={result_pass.final_tier}")


if __name__ == "__main__":
    main()
