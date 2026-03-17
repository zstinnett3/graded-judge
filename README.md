# graded-judge

**Tiered LLM evaluation with deterministic pre-filtering and cost-aware escalation.**

graded-judge is a production-quality Python library that evaluates LLM outputs through a tiered escalation framework. Instead of sending every evaluation to an expensive LLM judge, it uses cheaper tiers first and only escalates when needed, reducing cost while preserving accuracy.

## The problem

Evaluating every LLM output with a powerful (and costly) judge is expensive and often unnecessary. Many outputs can be rejected by simple rules (empty, too short, wrong format) or scored by a fast, cheap model. Only borderline or ambiguous cases need a slow, high-accuracy judge.

## Tiered escalation (plain English)

1. **Tier 0 — Rules.** Run deterministic checks (length, regex, JSON schema, non-empty). No LLM call, zero cost. If all rules pass, you're done. If too many fail, escalate to Tier 1.

2. **Tier 1 — Fast judge.** A low-cost LLM scores the output 0.0–1.0 and gives one sentence of reasoning. If the score meets your threshold, that's the verdict. If not, escalate to Tier 2.

3. **Tier 2 — Slow judge.** A more capable LLM does step-by-step reasoning and returns a final pass/fail and score. This tier never escalates; it's the final verdict.

Result: you pay for Tier 2 only when Tier 0 and Tier 1 can't confidently pass or fail the output.

## Architecture

| Tier | What it does              | Cost   | When it runs                    |
|------|---------------------------|--------|----------------------------------|
| 0    | Rule-based checks         | $0     | Always first (if enabled)       |
| 1    | Fast LLM (e.g. gpt-4o-mini) | Low  | When Tier 0 escalates (or is skipped) |
| 2    | Slow LLM (e.g. gpt-4o)    | Higher | When Tier 1 score is below threshold |

Each tier has configurable pass/fail thresholds that control escalation.

## Installation

```bash
pip install -e ".[dev]"   # from project root, for development
# or
pip install graded-judge   # when published
```

Requires Python 3.11+.

## Quick start

```python
from graded_judge import GradedJudge, GradedJudgeConfig

config = GradedJudgeConfig(
    tier1_provider="mock",   # use "openai" for real API
    tier2_provider="mock",
)
judge = GradedJudge(config=config)

result = judge.evaluate(
    input="What is the capital of France?",
    output="The capital of France is Paris.",
    criteria="The answer must be factually correct and concise.",
)

print(result.passed)        # True/False
print(result.final_tier)    # 0, 1, or 2
print(result.total_cost_usd)

summary = judge.summarize()  # RunSummary for the session
```

## Config reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tier0_enabled` | bool | True | Run Tier 0 rule-based checks |
| `tier1_enabled` | bool | True | Run Tier 1 fast LLM judge |
| `tier2_enabled` | bool | True | Run Tier 2 slow LLM judge |
| `tier0_fail_threshold` | int | 1 | Number of rule failures before escalating to Tier 1 |
| `tier1_pass_threshold` | float | 0.7 | Tier 1 score below this escalates to Tier 2 |
| `tier1_model` | str | "gpt-4o-mini" | Model for Tier 1 |
| `tier2_model` | str | "gpt-4o" | Model for Tier 2 |
| `tier1_provider` | str | "openai" | Provider for Tier 1 (openai, bedrock, ollama, mock) |
| `tier2_provider` | str | "openai" | Provider for Tier 2 |
| `tier1_max_tokens` | int | 512 | Max tokens for Tier 1 response |
| `tier2_max_tokens` | int | 1024 | Max tokens for Tier 2 response |
| `rules` | list[str] | [] | Rule class names for Tier 0 (e.g. NonEmptyRule, MinLengthRule) |
| `cost_tracking_enabled` | bool | True | Track cost and latency per run |
| `log_level` | str | "INFO" | Logging level |

Load from YAML:

```python
config = GradedJudgeConfig.from_yaml("configs/default.yaml")
judge = GradedJudge(config=config)
```

## Built-in rules (Tier 0)

| Rule | Description | Example |
|------|-------------|---------|
| `NonEmptyRule()` | Fails if output is empty or whitespace | — |
| `MinLengthRule(min_chars)` | Fails if output is shorter than `min_chars` | `MinLengthRule(10)` |
| `MaxLengthRule(max_chars)` | Fails if output is longer than `max_chars` | `MaxLengthRule(5000)` |
| `ForbiddenPatternRule(patterns)` | Fails if any regex matches | `ForbiddenPatternRule([r"\\bNOPE\\b"])` |
| `RequiredPatternRule(patterns)` | Fails if none of the regexes match | `RequiredPatternRule([r"\\d+"])` |
| `JsonSchemaRule(schema)` | Fails if output is not valid JSON matching the schema | `JsonSchemaRule({"type": "object", "required": ["key"]})` |

Use rule class names in config `rules: [NonEmptyRule, MinLengthRule]` or instantiate and pass to a custom Tier0.

## Adding custom rules

Implement `BaseRule` and pass instances to Tier0 (or register by name in your config loader):

```python
from graded_judge.rules.base import BaseRule
from graded_judge.models import EvaluationInput

class MustContainAnswerRule(BaseRule):
    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        if "answer:" in input.output.lower():
            return (True, "Output contains 'answer:'")
        return (False, "Output missing 'answer:'")

    @property
    def name(self) -> str:
        return "MustContainAnswerRule"
```

See `examples/custom_rules.py` for a full example.

## Supported providers

| Provider | Config value | Notes |
|----------|--------------|--------|
| **OpenAI** | `openai` | Set `OPENAI_API_KEY`. Uses gpt-4o-mini / gpt-4o pricing. |
| **AWS Bedrock** | `bedrock` | Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`. Claude model IDs. |
| **Ollama** | `ollama` | Local REST API at `http://localhost:11434`. Cost always $0. |
| **Mock** | `mock` | For tests and examples. No API key; configurable canned response. |

All LLM calls go through the provider abstraction; cost is estimated from token counts (OpenAI/Bedrock) or set to 0 (Ollama, Mock).

## Cost tracking and run summary

Cost and latency are tracked per evaluation and aggregated in the session. Use `judge.summarize()` to get a `RunSummary` and `print_summary(summary)` for human-readable output:

```
graded-judge run summary
------------------------
Total evaluations : 100
Passed            : 87
Failed            : 13
Tier 0 only       : 45 (cost: $0.00)
Tier 1 invoked    : 55 (cost: $0.012)
Tier 2 invoked    : 12 (cost: $0.031)
Total cost        : $0.043
Avg cost/eval     : $0.00043
Avg latency       : 312ms
```

Export results to JSON:

```python
judge.export_results("results.json")
```

## Contributing

1. Install dev deps: `pip install -e ".[dev]"`
2. Run tests: `pytest tests/ -v`
3. Lint: `ruff check src/ tests/` and `mypy src/`
4. Format: `ruff format src/ tests/`

All tests use the mock provider; no real LLM API calls are made.

## License

Apache 2.0
