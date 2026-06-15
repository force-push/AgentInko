"""Tests for the Tier 1 Godot build-verifier and its harness integration.
Run: python3 -m pytest test_godot_verifier.py -q"""

import pytest

from godot_verifier import evaluate_output, make_build_checker
from incentive_framework import (
    AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
    BudgetPolicy, KillSwitch, IncentiveHarness, VerificationStatus,
)

CLEAN = (
    "Godot Engine v4.3.stable.official\n"
    "[INKO] game_ready scene=Main headless=true\n"
    "[INKO] coin_collected t=1.27\n"
    "[INKO] playtest_done collected=true frames_ok=true\n"
)
SCRIPT_ERR = (
    "[INKO] game_ready scene=Main headless=true\n"
    "SCRIPT ERROR: Invalid call. Nonexistent function 'jum' in base 'Node2D'.\n"
)
PARSE_ERR = (
    "SCRIPT ERROR: Parse Error: Identifier \"_playr\" not declared.\n"
    "ERROR: Failed to load script \"res://scripts/main.gd\".\n"
)
NO_DONE = "[INKO] game_ready scene=Main headless=true\n"  # crashed before finishing


def test_clean_output_is_clean():
    r = evaluate_output(CLEAN)
    assert r.clean and r.ran and r.errors == [] and r.verified_value == 1.0


def test_script_error_not_clean():
    r = evaluate_output(SCRIPT_ERR)
    assert not r.clean and r.verified_value == 0.0 and r.errors


def test_parse_error_not_clean_and_captures_lines():
    r = evaluate_output(PARSE_ERR)
    assert not r.clean and r.verified_value == 0.0
    assert any("Parse Error" in e for e in r.errors)


def test_missing_done_marker_means_not_ran():
    r = evaluate_output(NO_DONE)
    assert not r.ran and not r.clean and r.verified_value == 0.0


def test_empty_output_not_clean():
    r = evaluate_output("")
    assert not r.clean and r.verified_value == 0.0


def _harness():
    audit = AuditLog()
    kill = KillSwitch(audit)
    verifier = OutcomeVerifier(audit)
    verifier.register("build_passes", make_build_checker())  # use 'output' detail
    ledger = IncentiveLedger(audit, clawback_window_s=0.0)
    treasury = Treasury(
        TreasuryConfig(5.0, 20.0, 86_400, 5.0, {"compute-cloud"}, True),
        audit, kill,
    )
    return IncentiveHarness(verifier, ledger, treasury, BudgetPolicy(1.0, 0.0), audit)


def test_harness_credits_only_clean_build():
    h = _harness()
    assert h.budget() == 0.0
    bad = h.submit_outcome("build_passes", {"output": PARSE_ERR}, 1.0)
    assert bad.status is VerificationStatus.REJECTED
    assert h.budget() == 0.0          # broken build earns nothing
    good = h.submit_outcome("build_passes", {"output": CLEAN}, 1.0)
    assert good.status is VerificationStatus.VERIFIED
    assert h.budget() == 1.0          # clean build unlocks budget


def test_checker_requires_project_when_no_output():
    checker = make_build_checker()    # no default project path
    with pytest.raises(ValueError):
        checker({})                   # neither output nor project_path


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
