"""Tests for the gateway, MCP client/mock, skills, and Tier 2 playtest agent,
plus a full-pipeline integration test. Run: python3 -m pytest test_pipeline.py -q"""

import pytest

from model_gateway import ModelGateway, ModelSpec
from godot_mcp_client import GodotMCPClient
from mock_godot_mcp import MockGodotMCP
from skills import GameDevSkills
from playtest_agent import PlaytestAgent, make_playtest_checker
from godot_verifier import evaluate_output
from incentive_framework import (
    AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
    BudgetPolicy, KillSwitch, IncentiveHarness, VerificationStatus,
)


def _gateway():
    def invoke(spec, prompt):
        if "JSON game spec" in prompt:
            return ('{"title":"T","genre":"arcade","goal":"g","mechanics":[],'
                    '"win_condition":"w","fail_condition":"f","entities":[]}'), 100, 50
        return "extends Node2D\n", 200, 100
    return ModelGateway(invoke)


# --- model gateway --------------------------------------------------------- #
def test_routes_design_to_claude_build_to_kimi():
    gw = _gateway()
    assert gw.model_for("storyboard").name.startswith("claude")
    assert gw.model_for("build_script").name.startswith("kimi")


def test_unknown_route_raises():
    with pytest.raises(KeyError):
        _gateway().model_for("nonexistent_task")


def test_cost_accumulates_and_splits_by_model():
    gw = _gateway()
    gw.run("storyboard", "JSON game spec: x")  # claude
    gw.run("build_script", "make GDScript")    # kimi
    assert gw.total_cost_usd > 0
    assert set(gw.cost_by_model()) == {"claude-opus-4-8", "kimi-k2.6"}


def test_kimi_cheaper_than_claude_per_call():
    gw = _gateway()
    c = gw.run("storyboard", "JSON game spec: x")
    k = gw.run("build_script", "make GDScript")
    # same-ish tokens, Kimi must be materially cheaper per the configured rates
    assert k.cost_usd < c.cost_usd


# --- mock MCP + client ----------------------------------------------------- #
def test_clean_build_output_from_mock():
    c = GodotMCPClient(MockGodotMCP().call_tool)
    out = c.run_headless("res://x")["output"]
    assert evaluate_output(out).clean


def test_faulty_build_reports_errors():
    c = GodotMCPClient(MockGodotMCP(fault="parse_error").call_tool)
    assert c.read_errors("res://x")["errors"]
    assert not evaluate_output(c.run_headless("res://x")["output"]).clean


def test_send_input_scripted_completes():
    c = GodotMCPClient(MockGodotMCP().call_tool)
    res = c.send_input("res://x", [{"dir": 1, "frames": 120}])["result"]
    assert res["completed"] is True


# --- skills ---------------------------------------------------------------- #
def test_storyboard_parses_to_struct():
    skills = GameDevSkills(_gateway(), GodotMCPClient(MockGodotMCP().call_tool))
    sb = skills.storyboard("JSON game spec: anything")
    assert sb.title == "T" and sb.genre == "arcade"


def test_build_from_storyboard_runs_clean():
    skills = GameDevSkills(_gateway(), GodotMCPClient(MockGodotMCP().call_tool))
    sb = skills.storyboard("JSON game spec: anything")
    build = skills.build_from_storyboard(sb, "res://x")
    assert build["errors"] == []


# --- Tier 2 playtest grading ----------------------------------------------- #
def test_healthy_game_scores_high():
    # coin reachable by scripted, missed by most random -> mid/high completion
    mcp = GodotMCPClient(MockGodotMCP(seed=3).call_tool)
    report = PlaytestAgent(mcp).run("res://x", sessions=50)
    assert report.verified_value > 0
    assert report.softlock_rate == 0.0


def test_softlocking_game_scores_zero():
    mcp = GodotMCPClient(MockGodotMCP(softlock_zone=(120, 200), seed=3).call_tool)
    report = PlaytestAgent(mcp).run("res://x", sessions=50)
    assert report.verified_value == 0.0


def test_broken_build_unplayable_scores_zero():
    mcp = GodotMCPClient(MockGodotMCP(fault="parse_error").call_tool)
    report = PlaytestAgent(mcp).run("res://x", sessions=20)
    assert report.completion_rate == 0.0


def test_playtest_checker_requires_inputs():
    checker = make_playtest_checker()
    with pytest.raises(ValueError):
        checker({})


# --- full pipeline integration --------------------------------------------- #
def test_full_pipeline_credits_budget():
    audit = AuditLog()
    kill = KillSwitch(audit)
    gw = _gateway()
    mcp = GodotMCPClient(MockGodotMCP(seed=1).call_tool)
    skills = GameDevSkills(gw, mcp)

    verifier = OutcomeVerifier(audit)
    verifier.register("build_passes", lambda d: evaluate_output(d["output"]).verified_value)
    verifier.register("playtest_clears", lambda d: float(d["report_value"]))
    ledger = IncentiveLedger(audit, clawback_window_s=0.0)
    treasury = Treasury(TreasuryConfig(2.0, 10.0, 86_400, 2.0,
                        {"model-inference"}, True), audit, kill)
    harness = IncentiveHarness(verifier, ledger, treasury, BudgetPolicy(1.0, 0.0), audit)

    sb = skills.storyboard("JSON game spec: x")
    build = skills.build_from_storyboard(sb, "res://x")
    t1 = harness.submit_outcome("build_passes", {"output": build["output"]}, 1.0)
    report = PlaytestAgent(mcp).run("res://x", sessions=50)
    t2 = harness.submit_outcome("playtest_clears", {"report_value": report.verified_value}, 1.0)

    assert t1.status is VerificationStatus.VERIFIED
    assert t2.status is VerificationStatus.VERIFIED
    assert harness.budget() == t1.verified_value + t2.verified_value > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
