"""
Full pipeline: batch evaluation with cost summary printed at end.
"""

from graded_judge import GradedJudge, GradedJudgeConfig, EvaluationInput
from graded_judge.reporting import print_summary

config = GradedJudgeConfig(
    tier1_provider="mock",
    tier2_provider="mock",
    rules=[],
)
judge = GradedJudge(config=config)

inputs = [
    EvaluationInput(
        input="What is the capital of France?",
        output="Paris.",
        criteria="Correct and concise.",
    ),
    EvaluationInput(
        input="What is 2+2?",
        output="4",
        criteria="Numeric correctness.",
    ),
    EvaluationInput(
        input="Name a color.",
        output="Blue",
        criteria="Single word color.",
    ),
]

results = judge.evaluate_batch(inputs)
print(f"Ran {len(results)} evaluations.\n")

summary = judge.summarize()
print_summary(summary)
