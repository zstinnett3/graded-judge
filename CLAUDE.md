# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install    # pip install -e ".[dev]"
make test       # pytest tests/ -v --cov=src/graded_judge --cov-report=term-missing
make lint       # ruff check src/ tests/ && mypy src/
make format     # ruff format src/ tests/
make clean      # remove __pycache__ and .pytest_cache
```

Run a single test file:
```bash
pytest tests/test_pipeline.py -v
```

Run a specific test:
```bash
pytest tests/test_pipeline.py::test_function_name -v
```

## Architecture

**graded-judge** is a tiered LLM evaluation library. The core idea is to minimize cost by short-circuiting: only escalate to a more expensive judge when needed.

### Tier hierarchy

| Tier | Type | Cost | Escalates when |
|------|------|------|----------------|
| 0 | Deterministic rules | $0 | fail count ≥ threshold |
| 1 | Fast LLM (e.g., gpt-4o-mini) | Low | score < threshold |
| 2 | Slow LLM (e.g., gpt-4o) | High | never |

### Data flow

```
GradedJudge.evaluate()
  → EvaluationInput
  → pipeline.run_pipeline()
      → Tier0.run()  →  (escalate?) → Tier1.run() → (escalate?) → Tier2.run()
  → EvaluationResult (tier_results[], final_tier, passed, score, total_cost)
  → CostTracker.add_result()
```

### Key abstractions

- **`BaseRule`** (`rules/base.py`): implement `name` + `check(input) -> (passed, reason)`. Used by Tier0.
- **`BaseProvider`** (`providers/base.py`): implement `complete(prompt, model, max_tokens, temp) -> (text, cost, latency_ms)`. Used by Tier1/Tier2.
- **`BaseTier`** (`tiers/base.py`): implement `run(input) -> TierResult`.

### Configuration

Config is a `GradedJudgeConfig` Pydantic model, loadable from YAML (`configs/default.yaml`). Key fields:
- `tier{0,1,2}_enabled` — toggle tiers
- `tier0_fail_threshold` — how many rule failures before escalating
- `tier1_pass_threshold` — score (0.0–1.0) above which Tier1 doesn't escalate
- `tier1_provider` / `tier2_provider` — `"openai"`, `"bedrock"`, `"ollama"`, or `"mock"`
- `rules` — list of built-in rule class names (parameterization is hardcoded; see known limitations)

### Built-in rules (Tier 0)

`NonEmptyRule`, `MinLengthRule`, `MaxLengthRule`, `ForbiddenPatternRule`, `RequiredPatternRule`, `JsonSchemaRule` — all in `src/graded_judge/rules/`.

### Providers

`openai.py`, `bedrock.py`, `ollama.py`, `mock.py` — all in `src/graded_judge/providers/`. Provider is resolved by name via hardcoded if/else in `evaluator.py` (known limitation).

### Testing

All tests use `MockProvider` — no real LLM calls or network I/O. Fixtures are in `tests/conftest.py`.

## Known limitations (from README)

1. Provider resolution is hardcoded if/else in `evaluator.py` — no pluggable registry.
2. Config `rules` field only accepts class names; rule parameters (e.g., `min_chars`) are hardcoded defaults.
3. No retry logic for transient LLM failures.
4. Token counting uses `len(text.split()) * 1.3` — not tiktoken.
5. `log_level` config field is never applied to the logging framework.
6. Batch evaluation is sequential; no async/parallel support.
