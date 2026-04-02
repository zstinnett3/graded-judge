# Demo Guide

## Setup

Install the package in dev mode if you haven't already:

```bash
make install
```

No API keys are required. The demo uses mock providers with realistic simulated costs — everything runs locally.

## Running the Demo

**Live / interactive mode** (recommended for presenting):
```bash
python demo.py
```
Pauses between each scenario so you can narrate. Press **Enter** to advance.

**Auto mode** (good for screen recordings):
```bash
python demo.py --auto
```
Runs all 6 scenarios without pausing.

## What the Demo Shows

The demo runs 6 staged evaluation scenarios, each building on the previous to tell a complete cost-savings story.

| Scenario | Tier path | Result | Point illustrated |
|---|---|---|---|
| 1 | Tier 0 only | PASS | Clear good answer short-circuits instantly, $0 cost |
| 2 | Tier 0 only | PASS | Same fast path for a code answer |
| 3 | Tier 0 → Tier 1 | PASS | Rule flagged a missing keyword; LLM overrides and approves |
| 4 | Tier 0 → Tier 1 | PASS | Rule rejected short translation; LLM confirms it's correct |
| 5 | Tier 0 → Tier 1 → Tier 2 | FAIL | Vague answer escalates all the way; Tier 2 rejects it |
| 6 | Tier 0 → Tier 1 → Tier 2 | PASS | Borderline answer escalates; Tier 2 approves it |

The final summary shows that only 2 of 6 evaluations needed the expensive Tier 2 judge, with roughly **64% cost savings** versus calling Tier 2 for everything.

## Talking Points

**On Tier 0 (scenarios 1–2):**
> "When an output clearly passes our deterministic checks — non-empty, minimum length, no forbidden patterns — we're done. No LLM call at all. This handles the easy majority."

**On Tier 0 → Tier 1 (scenarios 3–4):**
> "When a rule fires, we don't auto-fail the response. We ask a fast, cheap LLM to make the call. Here the rule was a strict policy check that the LLM judged wasn't critical — so it passed at low cost without needing the expensive model."

**On full escalation (scenarios 5–6):**
> "Only when the fast LLM is uncertain — score below the threshold — do we escalate to the high-accuracy model. That's the expensive judge, but it's reserved for genuinely ambiguous or borderline cases."

**On the summary:**
> "Across these 6 evaluations: 2 resolved at Tier 0 for free, 2 more at Tier 1 for fractions of a cent, and only 2 needed Tier 2. Total cost is about one-third of what you'd spend sending everything to the big model."

## Customising for Your Audience

The demo scenarios in `demo.py` are straightforward to swap out. Each scenario is a self-contained block that specifies:
- `EvaluationInput` — the prompt, output, and criteria
- `rules` list — which Tier 0 rules to apply
- `t1_json` / `t2_json` — the mocked LLM responses (score + reasoning)
- `t1_cost` / `t2_cost` — simulated per-call costs in USD

To add a domain-specific scenario (e.g., customer support, SQL generation, summarization), copy one of the existing blocks and adjust those four things.
