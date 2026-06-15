"""
Tier 1 Godot build-integrity verifier for AgentInko.

Runs a Godot project headless, captures stdout/stderr, and decides whether the
build is "clean" — i.e. it LOADED and RAN to completion with no script, parse,
or resource-load errors, and emitted our runtime health markers.

This is the cheapest, most objective tier of game verification (see
../godot-agentinko-guidance.md, §3). It is *necessary but not sufficient*:
a clean build earns a small credit; it does NOT prove the game is fun. Tiers 2
(automated playtesting) and 3 (real human signals) sit above it.

Godot runs on the USER'S machine (the agent's execution surface). Where the
binary is unavailable, feed captured output to `evaluate_output(...)` directly —
that pure function is what the unit tests exercise, so the grading logic is
verifiable without the engine installed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field


# Lines matching any of these mean the build is NOT clean.
ERROR_PATTERNS = [
    r"SCRIPT ERROR",
    r"Parse Error",
    r"\bERROR:",                       # generic Godot engine error
    r"Failed to load",
    r"Cannot open file",
    r"Invalid call",
    r"Identifier .* not declared",
    r"Script inherits from native type .* so it can't be assigned",
]

# Health markers our game prints (see godot_game/scripts/main.gd).
READY_MARKER = "[INKO] game_ready"
DONE_MARKER = "[INKO] playtest_done"


@dataclass
class BuildResult:
    clean: bool                       # ran to completion AND no errors
    ran: bool                         # hit both ready + done markers
    errors: list[str] = field(default_factory=list)
    verified_value: float = 0.0       # what the incentive ledger will credit
    raw: str = ""

    def summary(self) -> str:
        if self.clean:
            return "CLEAN — game loaded, ran, and exited without errors."
        if not self.ran:
            return "NOT CLEAN — game did not reach its runtime markers (crash/early exit?)."
        return f"NOT CLEAN — {len(self.errors)} error line(s) detected."


def evaluate_output(output: str) -> BuildResult:
    """Pure grading function over Godot's combined stdout+stderr."""
    errors: list[str] = []
    for line in output.splitlines():
        for pat in ERROR_PATTERNS:
            if re.search(pat, line):
                errors.append(line.strip())
                break

    ran = (READY_MARKER in output) and (DONE_MARKER in output)
    clean = ran and not errors
    value = 1.0 if clean else 0.0
    return BuildResult(clean=clean, ran=ran, errors=errors,
                       verified_value=value, raw=output)


def run_godot_headless(project_path: str, godot_bin: str = "godot",
                       timeout: float = 60.0) -> BuildResult:
    """Invoke Godot headless on `project_path` and grade the result.

    Requires Godot on PATH (or an absolute `godot_bin`). Raises nothing for a
    failed *game* — a crash/timeout simply grades as not-clean.
    """
    bin_path = shutil.which(godot_bin) or godot_bin
    try:
        proc = subprocess.run(
            [bin_path, "--headless", "--path", project_path],
            capture_output=True, text=True, timeout=timeout,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except FileNotFoundError:
        raise RuntimeError(
            f"Godot binary not found ('{godot_bin}'). Install Godot 4.x or pass "
            f"godot_bin=/abs/path. To grade pre-captured output, call "
            f"evaluate_output() instead."
        )
    except subprocess.TimeoutExpired as exc:
        captured = (exc.stdout or "") + "\n[INKO] TIMEOUT: game did not exit"
        return evaluate_output(captured if isinstance(captured, str)
                               else captured.decode("utf-8", "replace"))
    return evaluate_output(output)


def make_build_checker(project_path: str | None = None,
                       godot_bin: str = "godot"):
    """Return an OutcomeVerifier checker for kind 'build_passes'.

    The agent submits a claim; the checker grades it independently. `detail`
    may contain:
      - "output": pre-captured Godot output to grade (no binary needed), OR
      - "project_path"/"godot_bin": overrides for a live headless run.
    Returns the verified value (1.0 clean, 0.0 otherwise) for the ledger.
    """
    def checker(detail: dict) -> float:
        if "output" in detail:
            return evaluate_output(detail["output"]).verified_value
        pp = detail.get("project_path", project_path)
        if not pp:
            raise ValueError("No project_path provided and no default set.")
        return run_godot_headless(pp, detail.get("godot_bin", godot_bin)).verified_value
    return checker
