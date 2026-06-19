"""
autonomous_loop.py — AgentInko's self-driving build cycle.

This is the engine of true autonomy. The loop:
  1. Picks the next game concept from the build queue
  2. Runs the full pipeline: ideate → storyboard → build → T1 verify → T2 playtest
  3. If build passes, attempts HTML5 export and records T3 signal (portal analytics)
  4. Earns budget proportional to verified player value
  5. Uses earned budget to fund the next build cycle
  6. Repeats until the queue is exhausted or budget hits zero

The agent cannot fund itself. It cannot modify its own verifiers, caps, or
audit log. A human can halt it at any time (kill switch) or inspect the full
audit trail. The loop is kill-switch-aware: it checks before every stage.

Usage:
    python autonomous_loop.py                  # run all pending games
    python autonomous_loop.py --game camouflage  # run one specific game
    python autonomous_loop.py --dry-run        # full loop, no real spending
    python autonomous_loop.py --real-godot     # use live Godot MCP

The loop writes a build journal to logs/build_journal.jsonl after each cycle.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")


# ────────────────────────────────────────────────────────────────────────── #
# Build queue — ordered by readiness (storyboard.json exists = ready)
# ────────────────────────────────────────────────────────────────────────── #

GAME_QUEUE = [
    {
        "id": "camouflage",
        "title": "Camouflage",
        "storyboard": "games/camouflage/storyboard.json",
        "priority": 1,
        "status": "ready",         # storyboard.json exists, ready to build
        "concept_prompt": (
            "an octopus arcade game where the player must camouflage against "
            "scrolling seabed colour bands to dodge hunter scans"
        ),
    },
    {
        "id": "ink-dash",
        "title": "Inko's Ink Dash",
        "storyboard": None,        # needs storyboarding first
        "priority": 2,
        "status": "concept",
        "concept_prompt": (
            "a bioluminescent deep-sea auto-runner where Inko the octopus dashes "
            "through the trench, firing ink bursts to phase through hazards and "
            "leaving a glowing trail that lights the darkness. score-attack, endless."
        ),
    },
    {
        "id": "eight-arms",
        "title": "Eight Arms, One Heist",
        "storyboard": None,
        "priority": 3,
        "status": "concept",
        "concept_prompt": (
            "a grid-based stealth puzzle game where Inko the octopus uses 8 tentacles "
            "to simultaneously grip, distract, and manipulate guard-fish and laser-coral "
            "in a sunken ship, working with a crab crew to steal back captive corals"
        ),
    },
]


# ────────────────────────────────────────────────────────────────────────── #
# Build journal
# ────────────────────────────────────────────────────────────────────────── #

@dataclass
class BuildRecord:
    game_id: str
    title: str
    ts: float
    t1_passed: bool
    t2_value: float
    cost_usd: float
    earned_usd: float
    net_usd: float
    notes: str = ""


class BuildJournal:
    def __init__(self, path: str = "logs/build_journal.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, r: BuildRecord) -> None:
        with open(self._path, "a") as f:
            f.write(json.dumps(asdict(r)) + "\n")
        print(f"  [journal] {r.game_id}: T1={r.t1_passed}, "
              f"T2={r.t2_value:.2f}, net=${r.net_usd:.4f}")

    def load(self) -> list[BuildRecord]:
        if not self._path.exists():
            return []
        records = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(BuildRecord(**json.loads(line)))
        return records

    def already_built(self, game_id: str) -> bool:
        return any(r.game_id == game_id and r.t1_passed for r in self.load())


# ────────────────────────────────────────────────────────────────────────── #
# T3 signal — portal analytics (mock until real portal integration)
# ────────────────────────────────────────────────────────────────────────── #

def fetch_t3_signal(game_id: str) -> float:
    """
    Fetch Tier 3 human-play signal from the portal analytics API.
    Returns verified_value in [0.0, 1.0]:
      0.0 = no plays / no retention
      1.0 = excellent retention (D1 > 40%, D7 > 15%, avg session > 3 min)

    Currently returns a mock value. Wire real CrazyGames/Poki analytics API here.
    Portal API reference: docs/t3-signal-integration.md
    """
    # TODO: wire real portal analytics
    # CrazyGames API: https://api.crazygames.com/v1/games/{game_id}/analytics
    # Poki API: contact portal@poki.com for API access
    print(f"  [T3] mock signal for {game_id} (real portal not yet wired)")
    return 0.0   # 0.0 = unverified; agent earns nothing from T3 until wired


# ────────────────────────────────────────────────────────────────────────── #
# Main loop
# ────────────────────────────────────────────────────────────────────────── #

def run_loop(
    target_game: str | None = None,
    use_real_godot: bool = False,
    dry_run: bool = False,
    skip_built: bool = True,
) -> list[BuildRecord]:
    # ── deferred imports (only after .env loaded above) ──────────────────
    sys.path.insert(0, str(Path(__file__).parent / "agent_incentive"))

    from real_invoke import make_invoke, design_models_override
    from model_gateway import ModelGateway
    from godot_mcp_client import GodotMCPClient
    from mock_godot_mcp import MockGodotMCP
    from real_godot_mcp import RealGodotMCP
    from skills import GameDevSkills, Storyboard
    from playtest_agent import PlaytestAgent
    from godot_verifier import evaluate_output
    from incentive_framework import (
        AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
        BudgetPolicy, KillSwitch, IncentiveHarness,
    )

    print("\n" + "═" * 62)
    print("  AgentInko — Autonomous Build Loop")
    print("═" * 62)

    # ── shared infrastructure (one audit log + kill switch per loop run) ─
    audit = AuditLog()
    kill = KillSwitch(audit)
    verifier = OutcomeVerifier(audit)
    verifier.register("build_passes",    lambda d: evaluate_output(d["output"]).verified_value)
    verifier.register("playtest_clears", lambda d: float(d["report_value"]))
    ledger = IncentiveLedger(audit, clawback_window_s=0.0)
    treasury = Treasury(
        TreasuryConfig(
            per_tx_cap=10.0,
            rolling_cap=50.0,
            rolling_window_s=86_400,
            approval_threshold=10.0,
            allowed_payees={"model-inference", "compute-cloud"},
            dry_run=dry_run,
        ),
        audit, kill,
    )
    policy = BudgetPolicy()
    policy.payout_rate = 1.0
    policy.base_grant = 0.0
    harness = IncentiveHarness(verifier, ledger, treasury, policy, audit)
    journal = BuildJournal()

    invoke = make_invoke()
    gateway = ModelGateway(invoke, models=design_models_override())

    real_godot_adapter = None
    if use_real_godot:
        real_godot_adapter = RealGodotMCP()
        real_godot_adapter.start()
        mcp_factory = lambda: GodotMCPClient(real_godot_adapter.call_tool)
    else:
        mcp_factory = lambda: GodotMCPClient(MockGodotMCP(seed=42).call_tool)

    records: list[BuildRecord] = []
    queue = [g for g in GAME_QUEUE if target_game is None or g["id"] == target_game]

    for game in queue:
        if kill.is_triggered():
            print("\n⛔ Kill switch triggered — stopping loop.")
            break

        gid = game["id"]
        title = game["title"]

        if skip_built and journal.already_built(gid):
            print(f"\n  [{gid}] Already built and passed T1 — skipping.")
            continue

        print(f"\n{'─' * 62}")
        print(f"  Building: {title}  [{gid}]")
        print(f"{'─' * 62}")

        mcp = mcp_factory()
        skills = GameDevSkills(gateway, mcp)
        project_path = f"res://{gid}" if not use_real_godot else str(
            Path(__file__).parent / "godot_game"
        )

        cost_before = gateway.total_cost_usd
        t1_passed = False
        t2_value = 0.0
        notes = ""

        try:
            # ── 1. Ideate ─────────────────────────────────────────────
            if kill.is_triggered():
                break
            print("\n  [1/5] IDEATE...")
            idea = skills.ideate(game["concept_prompt"])
            print(f"    → {idea[:160]}...")

            # ── 2. Storyboard ─────────────────────────────────────────
            if kill.is_triggered():
                break
            print("\n  [2/5] STORYBOARD...")
            storyboard_path = game.get("storyboard")
            if storyboard_path and Path(storyboard_path).exists():
                with open(storyboard_path) as f:
                    raw = json.load(f)
                sb = Storyboard(
                    title=raw["title"], genre=raw["genre"], goal=raw["goal"],
                    mechanics=raw.get("mechanics", []),
                    win_condition=raw["win_condition"],
                    fail_condition=raw["fail_condition"],
                    entities=raw.get("entities", []),
                )
                print(f"    Loaded pre-built storyboard: {sb.title}")
            else:
                print(f"    No storyboard.json — generating via Claude/Kimi...")
                sb = skills.create_storyboard(idea)
                out_path = Path(f"games/{gid}/storyboard.json")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(
                        {"title": sb.title, "genre": sb.genre, "goal": sb.goal,
                         "mechanics": sb.mechanics, "win_condition": sb.win_condition,
                         "fail_condition": sb.fail_condition, "entities": sb.entities}, f, indent=2
                    )
                print(f"    Generated storyboard → {out_path}")

            # ── 3. Build ──────────────────────────────────────────────
            if kill.is_triggered():
                break
            print("\n  [3/5] BUILD (Kimi K2.6 codegen)...")
            build = skills.build_from_storyboard(sb, project_path)
            errors = build.get("errors", [])
            print(f"    Script: {build.get('script_res', '?')}")
            print(f"    Errors: {len(errors)}")

            # ── 4. T1 Verify ──────────────────────────────────────────
            if kill.is_triggered():
                break
            print("\n  [4/5] T1 VERIFY (build integrity)...")
            t1 = harness.submit_outcome("build_passes", {"output": build["output"]},
                                         asserted_value=1.0)
            t1_passed = t1.verified_value > 0.5
            print(f"    Status: {t1.status.value} | Value: {t1.verified_value:.2f}")
            if not t1_passed:
                notes = "T1 failed — build did not produce clean output"
                print(f"    ⚠ T1 failed. Moving to next game.")
                continue

            # ── 5. T2 Playtest ────────────────────────────────────────
            if kill.is_triggered():
                break
            print("\n  [5/5] T2 PLAYTEST (50 sessions)...")
            report = PlaytestAgent(mcp).run(project_path, sessions=50)
            print(f"    Completion: {report.completion_rate:.0%} | "
                  f"Softlock: {report.softlock_rate:.0%}")
            t2_value = report.verified_value
            t2 = harness.submit_outcome("playtest_clears",
                                         {"report_value": t2_value}, asserted_value=1.0)
            print(f"    Earned: +${t2.verified_value:.4f}")

        except Exception as exc:
            notes = f"Exception: {exc}"
            print(f"\n  ⚠ Exception during {gid}: {exc}")

        finally:
            cost = gateway.total_cost_usd - cost_before
            earned = harness.budget()
            net = earned - cost

            if t1_passed:
                harness.try_spend("model-inference", round(cost, 6),
                                   f"{gid} inference cost")

            rec = BuildRecord(
                game_id=gid, title=title, ts=time.time(),
                t1_passed=t1_passed, t2_value=t2_value,
                cost_usd=cost, earned_usd=earned, net_usd=net,
                notes=notes,
            )
            journal.record(rec)
            records.append(rec)

            print(f"\n  Budget snapshot: earned=${earned:.4f} cost=${cost:.4f} net=${net:.4f}")

    if real_godot_adapter:
        real_godot_adapter.stop()

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "═" * 62)
    passed = [r for r in records if r.t1_passed]
    print(f"  Loop complete: {len(passed)}/{len(records)} games built and verified")
    for r in records:
        status = "✅" if r.t1_passed else "⚠️"
        print(f"  {status} {r.title}: T2={r.t2_value:.2f} net=${r.net_usd:.4f}")
    total_net = sum(r.net_usd for r in records)
    print(f"\n  Total net: ${total_net:.4f}")
    print("═" * 62)

    return records


# ────────────────────────────────────────────────────────────────────────── #
# CLI entry point
# ────────────────────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentInko autonomous build loop")
    parser.add_argument("--game", metavar="ID", help="Run only this game (e.g. camouflage)")
    parser.add_argument("--real-godot", action="store_true", help="Use live Godot MCP")
    parser.add_argument("--dry-run", action="store_true", help="Simulate spending (no real treasury charges)")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild even if already in journal")
    args = parser.parse_args()

    run_loop(
        target_game=args.game,
        use_real_godot=args.real_godot,
        dry_run=args.dry_run,
        skip_built=not args.rebuild,
    )
