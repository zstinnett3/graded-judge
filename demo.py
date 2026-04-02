#!/usr/bin/env python3
"""
graded-judge live demo.

Runs 6 staged scenarios showing all three tiers in action.
No API keys required — uses mock providers with realistic simulated costs.

Usage:
    python demo.py           # pause between scenarios (recommended for live demos)
    python demo.py --auto    # run without pauses (good for screen recordings)
"""

import argparse
import time

from graded_judge.models import EvaluationInput, GradedJudgeConfig
from graded_judge.pipeline import run_pipeline
from graded_judge.providers.mock import MockProvider
from graded_judge.reporting.summary import generate_run_summary, print_summary
from graded_judge.rules import (
    ForbiddenPatternRule,
    MinLengthRule,
    NonEmptyRule,
    RequiredPatternRule,
)
from graded_judge.tiers import Tier0, Tier1, Tier2

# ── ANSI helpers ─────────────────────────────────────────────────────────────

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

PASS_TAG = f"{GREEN}PASS{RESET}"
FAIL_TAG = f"{RED}FAIL{RESET}"
W = 64  # line width


def rule(char="─"):
    return char * W


# ── DemoMockProvider ──────────────────────────────────────────────────────────


class DemoMockProvider(MockProvider):
    """MockProvider that returns a configurable simulated cost (for demo realism)."""

    def __init__(self, response_text: str, latency_ms: float = 50.0, cost_usd: float = 0.0):
        super().__init__(response_text, latency_ms)
        self._cost_usd = cost_usd

    def complete(self, prompt, model, max_tokens, temperature=0.0):
        time.sleep(self._latency_ms / 1000.0)
        return (self._response_text, self._cost_usd, self._latency_ms)


# ── Display helpers ───────────────────────────────────────────────────────────


def header(title: str, n: int, total: int = 6):
    print(f"\n{BOLD}{rule('━')}{RESET}")
    print(f"{BOLD}  Scenario {n}/{total}  —  {title}{RESET}")
    print(f"{BOLD}{rule('━')}{RESET}\n")


def show_inputs(prompt: str, output: str, criteria: str):
    display = f'"{output}"' if output.strip() else f'{DIM}(empty){RESET}'
    print(f"  {DIM}Prompt  :{RESET}  {prompt}")
    print(f"  {DIM}Output  :{RESET}  {display}")
    print(f"  {DIM}Criteria:{RESET}  {criteria}")


def show_tier0_result(result):
    tr = result.tier_results[0]
    print(f"\n  {CYAN}Tier 0{RESET}  {DIM}[deterministic rules — $0.00]{RESET}")
    for name in tr.rules_applied:
        tag = FAIL_TAG if name in tr.rule_failures else PASS_TAG
        print(f"          {name:<28} {tag}")
    if tr.escalated:
        print(f"    {YELLOW}↳ Rule failure — escalating to Tier 1{RESET}")
    else:
        print(f"    ✓ All rules passed — no LLM call needed")


def show_tier1_result(result):
    tr = next((t for t in result.tier_results if t.tier == 1), None)
    if tr is None:
        return
    score_str = f"{tr.score:.2f}" if tr.score is not None else "n/a"
    tag = PASS_TAG if tr.passed else FAIL_TAG
    print(f"\n  {CYAN}Tier 1{RESET}  {DIM}[fast LLM judge (gpt-4o-mini) — ${tr.cost_usd:.4f}, {tr.latency_ms:.0f}ms]{RESET}")
    print(f"          Score: {score_str}  {tag}")
    if tr.reasoning:
        print(f"          {DIM}{tr.reasoning[:72]}{RESET}")
    if tr.escalated:
        print(f"    {YELLOW}↳ Score below threshold — escalating to Tier 2{RESET}")
    else:
        print(f"    ✓ Confident verdict — Tier 2 not needed")


def show_tier2_result(result):
    tr = next((t for t in result.tier_results if t.tier == 2), None)
    if tr is None:
        return
    score_str = f"{tr.score:.2f}" if tr.score is not None else "n/a"
    tag = PASS_TAG if tr.passed else FAIL_TAG
    print(f"\n  {CYAN}Tier 2{RESET}  {DIM}[high-accuracy LLM judge (gpt-4o) — ${tr.cost_usd:.4f}, {tr.latency_ms:.0f}ms]{RESET}")
    print(f"          Score: {score_str}  {tag}")
    if tr.reasoning:
        print(f"          {DIM}{tr.reasoning[:72]}{RESET}")


def show_verdict(result):
    tag = PASS_TAG if result.passed else FAIL_TAG
    path = " → ".join(f"Tier {t}" for t in result.escalation_path)
    print(f"\n  {rule('─')}")
    print(f"  Verdict : {tag}  |  Final tier: {result.final_tier}  |  Cost: ${result.total_cost_usd:.4f}")
    print(f"  Path    : {path}")
    print(f"  {rule('─')}")


def wait(auto: bool):
    if not auto:
        input(f"\n  {YELLOW}Press Enter for next scenario…{RESET}")


# ── Tier factory ──────────────────────────────────────────────────────────────


def make_tiers(
    rules,
    t1_json: str,
    t1_cost: float = 0.00031,
    t1_latency: float = 118.0,
    t2_json: str = "",
    t2_cost: float = 0.0087,
    t2_latency: float = 1040.0,
):
    tier0 = Tier0(rules, fail_threshold=1)
    tier1 = Tier1(
        DemoMockProvider(t1_json, t1_latency, t1_cost),
        model="gpt-4o-mini",
        max_tokens=512,
        pass_threshold=0.7,
    )
    tier2 = Tier2(
        DemoMockProvider(t2_json, t2_latency, t2_cost),
        model="gpt-4o",
        max_tokens=1024,
    )
    return tier0, tier1, tier2


CONFIG = GradedJudgeConfig(
    tier0_enabled=True,
    tier1_enabled=True,
    tier2_enabled=True,
    tier0_fail_threshold=1,
    tier1_pass_threshold=0.7,
    tier1_provider="mock",
    tier2_provider="mock",
)

# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="graded-judge demo")
    parser.add_argument("--auto", action="store_true", help="Skip pauses between scenarios")
    args = parser.parse_args()
    auto = args.auto

    all_results = []

    # ── Banner ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{rule('═')}{RESET}")
    print(f"{BOLD}  graded-judge  ·  Live Demo{RESET}")
    print(f"  Tiered LLM evaluation with cost-aware escalation")
    print(f"{BOLD}{rule('═')}{RESET}")
    print()
    print("  Tier 0  Deterministic rules  —  zero cost, instant")
    print("  Tier 1  Fast LLM judge       —  low cost,  ~100ms")
    print("  Tier 2  High-accuracy LLM    —  full cost, ~1s")
    print()
    print("  The pipeline short-circuits as soon as a tier is confident.")
    print("  Only failures and borderline cases escalate further.")
    wait(auto)

    # ── Scenario 1: Pure Tier 0 PASS ─────────────────────────────────────────
    header("Tier 0 fast path — obvious good answer", 1)
    show_inputs(
        prompt="What is the boiling point of water at sea level?",
        output="Water boils at 100°C (212°F) at standard atmospheric pressure.",
        criteria="Correct in both Celsius and Fahrenheit.",
    )
    tier0, tier1, tier2 = make_tiers(
        rules=[NonEmptyRule(), MinLengthRule(10)],
        t1_json='{"score": 0.97, "reasoning": "Correct in both units with pressure context."}',
    )
    inp = EvaluationInput(
        input="What is the boiling point of water at sea level?",
        output="Water boils at 100°C (212°F) at standard atmospheric pressure.",
        criteria="Correct in both Celsius and Fahrenheit.",
    )
    result = run_pipeline(inp, CONFIG, tier0, tier1, tier2)
    all_results.append(result)
    show_tier0_result(result)
    show_verdict(result)
    wait(auto)

    # ── Scenario 2: Pure Tier 0 PASS ─────────────────────────────────────────
    header("Tier 0 fast path — clean code answer", 2)
    show_inputs(
        prompt="Write a Python function to check if a number is even.",
        output="def is_even(n):\n    return n % 2 == 0",
        criteria="Correct, idiomatic Python with no unnecessary complexity.",
    )
    tier0, tier1, tier2 = make_tiers(
        rules=[NonEmptyRule(), MinLengthRule(10)],
        t1_json='{"score": 0.95, "reasoning": "Clean and idiomatic Python using modulo."}',
    )
    inp = EvaluationInput(
        input="Write a Python function to check if a number is even.",
        output="def is_even(n):\n    return n % 2 == 0",
        criteria="Correct, idiomatic Python with no unnecessary complexity.",
    )
    result = run_pipeline(inp, CONFIG, tier0, tier1, tier2)
    all_results.append(result)
    show_tier0_result(result)
    show_verdict(result)
    wait(auto)

    # ── Scenario 3: T0 escalates → T1 PASS ───────────────────────────────────
    header("Tier 0 flags missing keyword → Tier 1 resolves it", 3)
    show_inputs(
        prompt="What are the benefits of doing code reviews?",
        output="Code reviews catch bugs early, improve overall quality, and spread knowledge across the team.",
        criteria="Must mention bug detection, quality, and team knowledge sharing. Security mention preferred.",
    )
    tier0, tier1, tier2 = make_tiers(
        rules=[NonEmptyRule(), RequiredPatternRule([r"securit"])],
        t1_json='{"score": 0.87, "reasoning": "Covers three core benefits clearly; security omission is minor given the criteria."}',
        t1_cost=0.00029,
        t1_latency=112.0,
    )
    inp = EvaluationInput(
        input="What are the benefits of doing code reviews?",
        output="Code reviews catch bugs early, improve overall quality, and spread knowledge across the team.",
        criteria="Must mention bug detection, quality, and team knowledge sharing. Security mention preferred.",
    )
    result = run_pipeline(inp, CONFIG, tier0, tier1, tier2)
    all_results.append(result)
    show_tier0_result(result)
    show_tier1_result(result)
    show_verdict(result)
    wait(auto)

    # ── Scenario 4: T0 escalates → T1 PASS ───────────────────────────────────
    header("Tier 0 flags short translation → Tier 1 resolves it", 4)
    show_inputs(
        prompt="Translate 'Good morning, how are you?' into French.",
        output="Bonjour, comment allez-vous ?",
        criteria="Accurate French translation.",
    )
    tier0, tier1, tier2 = make_tiers(
        rules=[NonEmptyRule(), MinLengthRule(40)],
        t1_json='{"score": 0.92, "reasoning": "Accurate and natural French translation with formal register."}',
        t1_cost=0.00027,
        t1_latency=104.0,
    )
    inp = EvaluationInput(
        input="Translate 'Good morning, how are you?' into French.",
        output="Bonjour, comment allez-vous ?",
        criteria="Accurate French translation.",
    )
    result = run_pipeline(inp, CONFIG, tier0, tier1, tier2)
    all_results.append(result)
    show_tier0_result(result)
    show_tier1_result(result)
    show_verdict(result)
    wait(auto)

    # ── Scenario 5: Full escalation → T2 FAIL ────────────────────────────────
    header("Full escalation — Tier 2 rejects a too-vague answer", 5)
    show_inputs(
        prompt="Explain the CAP theorem and when to apply it.",
        output="It means you can't have all three. Pick two.",
        criteria="Define Consistency, Availability, and Partition Tolerance. Include practical guidance.",
    )
    tier0, tier1, tier2 = make_tiers(
        rules=[NonEmptyRule(), MinLengthRule(80)],
        t1_json='{"score": 0.41, "reasoning": "Too vague — omits definitions of all three properties."}',
        t1_cost=0.00033,
        t1_latency=126.0,
        t2_json='{"reasoning": "Omits all three property definitions and offers no practical guidance on when to apply the theorem.", "score": 0.22, "passed": false, "confidence": "high"}',
        t2_cost=0.0089,
        t2_latency=1080.0,
    )
    inp = EvaluationInput(
        input="Explain the CAP theorem and when to apply it.",
        output="It means you can't have all three. Pick two.",
        criteria="Define Consistency, Availability, and Partition Tolerance. Include practical guidance.",
    )
    result = run_pipeline(inp, CONFIG, tier0, tier1, tier2)
    all_results.append(result)
    show_tier0_result(result)
    show_tier1_result(result)
    show_tier2_result(result)
    show_verdict(result)
    wait(auto)

    # ── Scenario 6: Full escalation → T2 PASS ────────────────────────────────
    header("Full escalation — Tier 2 approves a borderline answer", 6)
    show_inputs(
        prompt="What are the trade-offs between SQL and NoSQL databases?",
        output=(
            "SQL databases offer ACID transactions, structured schemas, and strong consistency — "
            "ideal for transactional workloads. NoSQL provides horizontal scalability and flexible "
            "schemas, trading consistency for availability. Choose SQL for financial or relational "
            "data; NoSQL for large-scale, unstructured, or rapidly changing data."
        ),
        criteria="Balanced comparison covering transactions, scalability, schema flexibility, and when to choose each.",
    )
    tier0, tier1, tier2 = make_tiers(
        rules=[NonEmptyRule(), MinLengthRule(300)],
        t1_json='{"score": 0.63, "reasoning": "Covers key trade-offs but borderline depth on schema flexibility specifics."}',
        t1_cost=0.00034,
        t1_latency=131.0,
        t2_json='{"reasoning": "Addresses transactions, scalability, schema flexibility, and selection guidance. Meets all criteria despite being concise.", "score": 0.81, "passed": true, "confidence": "medium"}',
        t2_cost=0.0088,
        t2_latency=1020.0,
    )
    inp = EvaluationInput(
        input="What are the trade-offs between SQL and NoSQL databases?",
        output=(
            "SQL databases offer ACID transactions, structured schemas, and strong consistency — "
            "ideal for transactional workloads. NoSQL provides horizontal scalability and flexible "
            "schemas, trading consistency for availability. Choose SQL for financial or relational "
            "data; NoSQL for large-scale, unstructured, or rapidly changing data."
        ),
        criteria="Balanced comparison covering transactions, scalability, schema flexibility, and when to choose each.",
    )
    result = run_pipeline(inp, CONFIG, tier0, tier1, tier2)
    all_results.append(result)
    show_tier0_result(result)
    show_tier1_result(result)
    show_tier2_result(result)
    show_verdict(result)

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{rule('═')}{RESET}")
    print(f"{BOLD}  Run Summary  —  All 6 scenarios{RESET}")
    print(f"{BOLD}{rule('═')}{RESET}\n")

    summary = generate_run_summary(all_results)
    print_summary(summary)

    t0_n = summary.tier_invocation_counts.get("tier0", 0)
    t1_n = summary.tier_invocation_counts.get("tier1", 0)
    t2_n = summary.tier_invocation_counts.get("tier2", 0)
    t0_c = summary.cost_by_tier.get("tier0", 0.0)
    t1_c = summary.cost_by_tier.get("tier1", 0.0)
    t2_c = summary.cost_by_tier.get("tier2", 0.0)

    all_tier2_cost = len(all_results) * 0.0088
    savings_pct = (1.0 - summary.total_cost_usd / all_tier2_cost) * 100

    print(f"\n  Cost by tier:")
    print(f"    Tier 0  {t0_n} calls   ${t0_c:.4f}   (rules only)")
    print(f"    Tier 1  {t1_n} calls   ${t1_c:.4f}   (fast LLM)")
    print(f"    Tier 2  {t2_n} calls   ${t2_c:.4f}   (high-accuracy LLM)")
    print()
    print(f"  {GREEN}{BOLD}Only {t2_n} of {len(all_results)} evaluations needed the expensive Tier 2 judge.{RESET}")
    print(f"  {GREEN}Estimated cost savings vs. always using Tier 2: ~{savings_pct:.0f}%{RESET}")
    print()


if __name__ == "__main__":
    main()
