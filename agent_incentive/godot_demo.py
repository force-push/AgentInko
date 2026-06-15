"""
End-to-end slice: an incentivised agent earns budget by shipping a Godot build
that PASSES Tier 1 verification — and earns nothing for a broken one.

Flow:  agent submits "build_passes" outcome
       -> OutcomeVerifier runs Godot headless (or grades captured output)
       -> only a CLEAN build credits the IncentiveLedger
       -> budget unlocks a (dry-run, capped) spend.

Run:   python3 godot_demo.py            # uses captured sample output
       python3 godot_demo.py --real     # runs the real ../godot_game project
                                         # (needs Godot 4.x on PATH)
"""

import os
import shutil
import sys

from incentive_framework import (
    AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
    BudgetPolicy, KillSwitch, IncentiveHarness, SpendDecision,
)
from godot_verifier import make_build_checker, run_godot_headless

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "godot_game"))

# What a healthy headless run of godot_game prints:
CLEAN_OUTPUT = (
    "Godot Engine v4.3.stable.official - https://godotengine.org\n"
    "[INKO] game_ready scene=Main headless=true\n"
    "[INKO] coin_collected t=1.27\n"
    "[INKO] playtest_done collected=true frames_ok=true\n"
)

# What a broken build prints (a typo'd identifier in main.gd):
BROKEN_OUTPUT = (
    "Godot Engine v4.3.stable.official - https://godotengine.org\n"
    "SCRIPT ERROR: Parse Error: Identifier \"_playr\" not declared in the current scope.\n"
    "          at: GDScript::reload (res://scripts/main.gd:24)\n"
    "ERROR: Failed to load script \"res://scripts/main.gd\" with error \"Parse error\".\n"
)


def build_harness() -> tuple[IncentiveHarness, AuditLog, KillSwitch]:
    audit = AuditLog()
    kill = KillSwitch(audit)

    verifier = OutcomeVerifier(audit)
    # Tier 1: clean Godot build. Default project = ../godot_game.
    verifier.register("build_passes", make_build_checker(PROJECT))

    ledger = IncentiveLedger(audit, clawback_window_s=0.0)  # demo: mature instantly
    treasury = Treasury(
        TreasuryConfig(per_tx_cap=5.0, rolling_cap=20.0, rolling_window_s=86_400,
                       approval_threshold=5.0, allowed_payees={"compute-cloud"},
                       dry_run=True),
        audit, kill,
    )
    policy = BudgetPolicy(payout_rate=1.0, base_grant=0.0)
    return IncentiveHarness(verifier, ledger, treasury, policy, audit), audit, kill


def main() -> None:
    real = "--real" in sys.argv
    harness, audit, kill = build_harness()

    print("== AgentInko × Godot — Tier 1 slice ==")
    print("Budget before shipping anything:", harness.budget(), "\n")

    if real:
        if not shutil.which("godot"):
            print("Godot not on PATH; cannot run --real. Falling back to samples.")
            real = False
        else:
            print(f"Running REAL headless build of {PROJECT} ...")
            res = run_godot_headless(PROJECT)
            print("  ->", res.summary())
            # Submit the real run's output as the agent's claim.
            good = harness.submit_outcome("build_passes", {"output": res.raw}, 1.0)
            print(f"  verified={good.status.value} credited={good.verified_value}\n")

    if not real:
        # Agent ships a clean build -> verified -> credited.
        good = harness.submit_outcome("build_passes", {"output": CLEAN_OUTPUT}, 1.0)
        print(f"Clean build  -> {good.status.value}, credited {good.verified_value}")
        # Agent ships a broken build -> rejected -> nothing.
        bad = harness.submit_outcome("build_passes", {"output": BROKEN_OUTPUT}, 1.0)
        print(f"Broken build -> {bad.status.value}, credited {bad.verified_value} "
              f"(errors earn no budget)\n")

    print("Budget after verified work:", harness.budget())

    d = harness.try_spend("compute-cloud", 0.5, "rent GPU minutes to build next level")
    print("Spend $0.50 on compute (within budget+caps, dry-run):", d.value)

    over = harness.try_spend("compute-cloud", 9.0, "oversized spend")
    print("Spend $9 (over $5 per-tx cap):", over.value)

    print("\nAudit log intact:", audit.verify_integrity(), f"({len(audit.entries())} entries)")


if __name__ == "__main__":
    main()
