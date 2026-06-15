"""
run_pipeline.py — Real AgentInko pipeline with live Claude + Kimi + Godot MCP.

Usage:
    cd agent_incentive/
    source ../.venv/bin/activate
    python run_pipeline.py                   # real models, mock Godot
    python run_pipeline.py --real-godot      # real models + real Godot MCP

Game target: games/camouflage/storyboard.json → Camouflage
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Load .env from project root before any imports
from dotenv import load_dotenv
load_dotenv(dotenv_path=str(Path(__file__).parent.parent / ".env"))

from real_invoke import make_invoke
from model_gateway import ModelGateway, ModelSpec
from godot_mcp_client import GodotMCPClient
from mock_godot_mcp import MockGodotMCP
from skills import GameDevSkills, Storyboard
from playtest_agent import PlaytestAgent
from godot_verifier import evaluate_output
from incentive_framework import (
    AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
    BudgetPolicy, KillSwitch, IncentiveHarness,
)

STORYBOARD_PATH = Path(__file__).parent.parent / "games" / "camouflage" / "storyboard.json"
PROJECT = "res://camouflage"


def load_storyboard() -> Storyboard:
    """Load Camouflage spec from storyboard.json into the Storyboard dataclass."""
    with open(STORYBOARD_PATH) as f:
        raw = json.load(f)
    return Storyboard(
        title=raw["title"],
        genre=raw["genre"],
        goal=raw["goal"],
        mechanics=raw.get("mechanics", []),
        win_condition=raw["win_condition"],
        fail_condition=raw["fail_condition"],
        entities=raw.get("entities", []),
    )


def main(use_real_godot: bool = False) -> None:
    print("=" * 60)
    print("AgentInko — Camouflage Build Pipeline")
    print("  Claude (design) + Kimi K2.6 (codegen)")
    print("=" * 60)
    print()

    # --- Live model backends ---
    print("[init] Loading real API backends (Claude + Kimi K2.6)...")
    invoke = make_invoke()
    gateway = ModelGateway(invoke)
    print("       ✓ Claude Haiku + Kimi K2.6 ready")

    # --- Godot backend ---
    if use_real_godot:
        print("[init] Connecting to real Godot MCP server...")
        mcp = GodotMCPClient()
        print("       ✓ Godot MCP connected")
    else:
        print("[init] Using mock Godot MCP (pass --real-godot to use live Godot)...")
        mcp = GodotMCPClient(MockGodotMCP(seed=42).call_tool)
        print("       ✓ Mock Godot MCP ready")

    # --- Incentive framework ---
    audit   = AuditLog()
    kill    = KillSwitch(audit)
    verifier = OutcomeVerifier(audit)
    verifier.register("build_passes",    lambda d: evaluate_output(d["output"]).verified_value)
    verifier.register("playtest_clears", lambda d: float(d["report_value"]))
    ledger  = IncentiveLedger(audit, clawback_window_s=0.0)
    treasury = Treasury(
        TreasuryConfig(
            per_tx_cap=5.0,
            rolling_cap=20.0,
            rolling_window_s=86_400,
            approval_threshold=5.0,
            allowed_payees={"model-inference", "compute-cloud"},
            dry_run=False,
        ),
        audit, kill,
    )
    policy = BudgetPolicy()
    policy.payout_rate = 1.0  # 100% of verified value available as budget
    policy.base_grant  = 0.0
    harness = IncentiveHarness(verifier, ledger, treasury, policy, audit)
    skills = GameDevSkills(gateway, mcp)

    # ------------------------------------------------------------------ #
    # STAGE 1: IDEATE — Claude imagines the game
    # ------------------------------------------------------------------ #
    print("\n[1/6] IDEATE — Claude generating game concept...")
    idea = skills.ideate(
        "an octopus arcade game where the player must camouflage against scrolling "
        "seabed colour bands to dodge hunter scans"
    )
    print(f"  → {idea[:240]}")
    print(f"  Cost so far: ${gateway.total_cost_usd:.4f}")

    # ------------------------------------------------------------------ #
    # STAGE 2: STORYBOARD — Load Camouflage spec (pre-built by Cowork)
    # ------------------------------------------------------------------ #
    print("\n[2/6] STORYBOARD — Loading Camouflage spec from games/camouflage/storyboard.json...")
    storyboard = load_storyboard()
    print(f"  Title:  {storyboard.title}")
    print(f"  Genre:  {storyboard.genre}")
    print(f"  Goal:   {storyboard.goal[:100]}...")
    print(f"  Mech:   {len(storyboard.mechanics)} mechanics, {len(storyboard.entities)} entities")
    print(f"  Win:    {storyboard.win_condition}")
    print(f"  Fail:   {storyboard.fail_condition}")

    # ------------------------------------------------------------------ #
    # STAGE 3: BUILD — Kimi K2.6 generates GDScript from spec
    # ------------------------------------------------------------------ #
    print("\n[3/6] BUILD — Kimi K2.6 generating GDScript from storyboard...")
    build = skills.build_from_storyboard(storyboard, PROJECT)
    print(f"  Script: {build.get('script_res','?')}")
    errors = build.get("errors", [])
    print(f"  Errors: {len(errors)} {'(none 🎉)' if not errors else ''}")
    if errors:
        for e in errors[:3]:
            print(f"    ⚠  {e}")
    output_snippet = str(build.get("output", ""))[:200]
    print(f"  Output: {output_snippet or '(empty)'}...")
    print(f"  Cost so far: ${gateway.total_cost_usd:.4f}")

    # ------------------------------------------------------------------ #
    # STAGE 4: TIER 1 VERIFY — Build integrity
    # ------------------------------------------------------------------ #
    print("\n[4/6] TIER 1 — Build integrity verification...")
    t1 = harness.submit_outcome("build_passes", {"output": build["output"]}, asserted_value=1.0)
    print(f"  Status:        {t1.status.value}")
    print(f"  Verified val:  {t1.verified_value:.2f}")
    print(f"  Earned:        +${t1.verified_value:.4f}")

    # ------------------------------------------------------------------ #
    # STAGE 5: TIER 2 PLAYTEST — Automated playtesting
    # ------------------------------------------------------------------ #
    print("\n[5/6] TIER 2 — Automated playtesting (50 sessions)...")
    report = PlaytestAgent(mcp).run(PROJECT, sessions=50)
    print(f"  Completion rate: {report.completion_rate:.0%}")
    print(f"  Softlock rate:   {report.softlock_rate:.0%}")
    print(f"  Verified value:  {report.verified_value:.2f}")
    if report.notes:
        print(f"  Notes: {report.notes[0]}")
    t2 = harness.submit_outcome("playtest_clears", {"report_value": report.verified_value}, asserted_value=1.0)
    print(f"  Status:        {t2.status.value}")
    print(f"  Earned:        +${t2.verified_value:.4f}")

    # ------------------------------------------------------------------ #
    # STAGE 6: BUDGET SETTLEMENT — Cost vs earned
    # ------------------------------------------------------------------ #
    print("\n[6/6] BUDGET — Settling inference cost against earned budget...")
    earned  = harness.budget()
    cost    = gateway.total_cost_usd
    by_model = gateway.cost_by_model()
    print(f"  Total earned:    ${earned:.4f}")
    print(f"  Model spend:     ${cost:.4f}")
    for model_name, model_cost in by_model.items():
        print(f"    {model_name}: ${model_cost:.4f}")
    charge = harness.try_spend("model-inference", round(cost, 4),
                                "Camouflage build inference cost")
    print(f"  Charge result:   {charge.value}")
    print(f"  Net budget:      ${harness.budget():.4f}")

    # --- Audit ---
    entries = audit.entries()
    print(f"\n  Audit log:       {len(entries)} entries, integrity={audit.verify_integrity()}")

    print()
    if t1.verified_value > 0 and t2.verified_value > 0:
        print("✅ PIPELINE COMPLETE — Camouflage built, verified, and costed.")
        print("   Next: export to HTML5 and submit to CrazyGames/Poki portal.")
    else:
        print("⚠️  Pipeline complete with warnings — check T1/T2 results above.")

    return {
        "t1": t1, "t2": t2,
        "build": build,
        "earned": earned,
        "cost": cost,
        "report": report,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentInko — Camouflage build pipeline")
    parser.add_argument("--real-godot", action="store_true",
                        help="Use real Godot MCP server instead of mock")
    args = parser.parse_args()
    main(use_real_godot=args.real_godot)
