"""
Basic usage: single evaluation with default config using mock provider.
"""

from graded_judge import GradedJudge, GradedJudgeConfig

# Use mock provider so no API key is needed
config = GradedJudgeConfig(
    tier1_provider="mock",
    tier2_provider="mock",
    rules=[],
)
judge = GradedJudge(config=config)

result = judge.evaluate(
    input="What is the capital of France?",
    output="The capital of France is Paris.",
    criteria="The answer must be factually correct and concise.",
)

print(f"Passed: {result.passed}")
print(f"Final tier: {result.final_tier}")
print(f"Escalation path: {result.escalation_path}")
print(f"Total cost: ${result.total_cost_usd:.4f}")

summary = judge.summarize()
print(f"Session: {summary.total_evaluations} evaluation(s), {summary.passed} passed")
