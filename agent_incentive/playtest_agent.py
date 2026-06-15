"""
Tier 2 automated playtest agent for AgentInko.

Drives the running game many times through the Godot MCP `send_input` surface,
then computes OBJECTIVE proxies for "playable": completion rate, time-to-finish,
and softlock rate. It deliberately does NOT judge "fun" — that's Tier 3 (real
human signals). See ../godot-agentinko-guidance.md §3.

Per the playtesting literature, we start simple (scripted + random policies)
before graduating to DRL. A game is rewarded for being COMPLETABLE BUT NOT
TRIVIAL and free of softlocks; degenerate games (always-win, never-win, or
softlocking) earn little or nothing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from godot_mcp_client import GodotMCPClient

# A game should be solvable but not a walkover. Completion rate in this band
# (under a *mix* of competent and random play) is the healthy target.
IDEAL_BAND = (0.40, 0.95)
MAX_SOFTLOCK_RATE = 0.05


@dataclass
class SessionResult:
    completed: bool
    time_s: float
    deaths: int
    softlock: bool


@dataclass
class PlaytestReport:
    sessions: int
    completion_rate: float
    avg_time_s: float
    softlock_rate: float
    verified_value: float
    notes: list[str] = field(default_factory=list)


class PlaytestAgent:
    def __init__(self, mcp: GodotMCPClient, seed: int | None = 7) -> None:
        self.mcp = mcp
        self._rng = random.Random(seed)

    # --- input policies ------------------------------------------------- #
    def _scripted_inputs(self) -> list[dict]:
        # A competent player: move right toward the coin.
        return [{"dir": 1, "frames": 120}]

    def _random_inputs(self) -> list[dict]:
        # A flailing player: random directions in short bursts.
        return [{"dir": self._rng.choice([-1, 0, 1]), "frames": self._rng.randint(10, 40)}
                for _ in range(5)]

    def play_session(self, project_path: str, policy: str) -> SessionResult:
        seq = self._scripted_inputs() if policy == "scripted" else self._random_inputs()
        res = self.mcp.send_input(project_path, seq).get("result", {})
        return SessionResult(
            completed=bool(res.get("completed", False)),
            time_s=float(res.get("time_s", 0.0)),
            deaths=int(res.get("deaths", 0)),
            softlock=bool(res.get("softlock", False)),
        )

    # --- run a batch and grade ------------------------------------------ #
    def run(self, project_path: str, sessions: int = 50,
            scripted_fraction: float = 0.5) -> PlaytestReport:
        results: list[SessionResult] = []
        n_scripted = int(sessions * scripted_fraction)
        for i in range(sessions):
            policy = "scripted" if i < n_scripted else "random"
            results.append(self.play_session(project_path, policy))

        completed = sum(r.completed for r in results)
        softlocks = sum(r.softlock for r in results)
        comp_rate = completed / sessions if sessions else 0.0
        softlock_rate = softlocks / sessions if sessions else 0.0
        finish_times = [r.time_s for r in results if r.completed]
        avg_time = sum(finish_times) / len(finish_times) if finish_times else 0.0

        value, notes = self._grade(comp_rate, softlock_rate)
        return PlaytestReport(sessions, round(comp_rate, 3), round(avg_time, 3),
                              round(softlock_rate, 3), round(value, 3), notes)

    @staticmethod
    def _grade(comp_rate: float, softlock_rate: float) -> tuple[float, list[str]]:
        notes: list[str] = []
        if softlock_rate > MAX_SOFTLOCK_RATE:
            notes.append(f"softlock rate {softlock_rate:.0%} exceeds "
                         f"{MAX_SOFTLOCK_RATE:.0%} — game is broken")
            return 0.0, notes
        lo, hi = IDEAL_BAND
        if comp_rate < lo:
            notes.append(f"completion {comp_rate:.0%} below {lo:.0%} — too hard/unbeatable")
            value = comp_rate / lo * 0.5            # partial credit, capped low
        elif comp_rate > hi:
            notes.append(f"completion {comp_rate:.0%} above {hi:.0%} — too trivial")
            value = 0.6                              # playable but no challenge
        else:
            notes.append(f"completion {comp_rate:.0%} in healthy band — solvable, not trivial")
            value = 1.0
        return value, notes


def make_playtest_checker(project_path: str | None = None, sessions: int = 50):
    """OutcomeVerifier checker for kind 'playtest_clears'. `detail` may carry a
    precomputed 'report' (verified_value) or trigger a live run. The MCP client
    is read from detail['mcp'] for a live run."""
    def checker(detail: dict) -> float:
        if "report_value" in detail:
            return float(detail["report_value"])
        mcp = detail.get("mcp")
        pp = detail.get("project_path", project_path)
        if mcp is None or pp is None:
            raise ValueError("Live playtest needs detail['mcp'] and a project_path.")
        return PlaytestAgent(mcp).run(pp, sessions).verified_value
    return checker
