"""Tests for the incentive framework's guardrails. Run: python -m pytest -q"""

import time
import pytest

from incentive_framework import (
    AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
    BudgetPolicy, KillSwitch, IncentiveHarness, SpendDecision, VerificationStatus,
)


def _harness(dry_run=True, send_funds=None, approval=None, per_tx=100.0,
             rolling=300.0, threshold=100.0, payees=None, clawback=0.0):
    audit = AuditLog()
    kill = KillSwitch(audit)
    verifier = OutcomeVerifier(audit)
    verifier.register("paid", lambda d: float(d.get("amount", 0)))
    ledger = IncentiveLedger(audit, clawback_window_s=clawback)
    treasury = Treasury(
        TreasuryConfig(per_tx, rolling, 86_400, threshold,
                       set(payees or []), dry_run),
        audit, kill, approval_hook=approval, send_funds=send_funds,
    )
    h = IncentiveHarness(verifier, ledger, treasury, BudgetPolicy(1.0, 0.0), audit)
    return h, audit, kill, ledger


def test_unverified_claim_earns_nothing():
    h, *_ = _harness()
    c = h.submit_outcome("paid", {"amount": 0}, asserted_value=999)
    assert c.status is VerificationStatus.REJECTED
    assert h.budget() == 0.0


def test_unknown_kind_rejected():
    h, *_ = _harness()
    c = h.submit_outcome("totally_made_up", {}, 100)
    assert c.status is VerificationStatus.REJECTED


def test_verified_claim_creates_budget():
    h, *_ = _harness(payees=["v"])
    h.submit_outcome("paid", {"amount": 200}, 200)
    assert h.budget() == 200.0  # payout_rate 1.0


def test_spend_over_per_tx_cap_blocked():
    h, *_ = _harness(payees=["v"])
    h.submit_outcome("paid", {"amount": 500}, 500)
    assert h.try_spend("v", 150.0, "x") is SpendDecision.BLOCKED_CAP


def test_spend_over_budget_blocked():
    h, *_ = _harness(payees=["v"])
    h.submit_outcome("paid", {"amount": 50}, 50)
    assert h.try_spend("v", 80.0, "x") is SpendDecision.BLOCKED_BUDGET


def test_disallowed_payee_blocked():
    h, *_ = _harness(payees=["allowed"])
    h.submit_outcome("paid", {"amount": 500}, 500)
    assert h.try_spend("stranger", 50.0, "x") is SpendDecision.BLOCKED_PAYEE


def test_approval_gate_default_deny():
    h, *_ = _harness(payees=["v"], threshold=10.0)  # no approval hook -> deny
    h.submit_outcome("paid", {"amount": 500}, 500)
    assert h.try_spend("v", 50.0, "x") is SpendDecision.NEEDS_APPROVAL


def test_approval_gate_allows_when_human_approves():
    h, *_ = _harness(payees=["v"], threshold=10.0, approval=lambda r: True)
    h.submit_outcome("paid", {"amount": 500}, 500)
    assert h.try_spend("v", 50.0, "x") is SpendDecision.DRY_RUN


def test_rolling_cap_blocks_cumulative():
    h, *_ = _harness(payees=["v"], per_tx=100.0, rolling=120.0, threshold=1000.0)
    h.submit_outcome("paid", {"amount": 1000}, 1000)
    assert h.try_spend("v", 80.0, "a") is SpendDecision.DRY_RUN
    assert h.try_spend("v", 80.0, "b") is SpendDecision.BLOCKED_CAP  # 160 > 120


def test_kill_switch_blocks_all_spend():
    h, audit, kill, _ = _harness(payees=["v"], threshold=1000.0)
    h.submit_outcome("paid", {"amount": 500}, 500)
    kill.engage("test")
    assert h.try_spend("v", 10.0, "x") is SpendDecision.BLOCKED_HALTED


def test_real_money_requires_explicit_rail():
    # dry_run False but no send_funds -> still cannot move real money.
    h, *_ = _harness(dry_run=False, send_funds=None, payees=["v"], threshold=1000.0)
    h.submit_outcome("paid", {"amount": 500}, 500)
    assert h.try_spend("v", 10.0, "x") is SpendDecision.DRY_RUN


def test_real_money_executes_with_rail():
    sent = []
    rail = lambda payee, amt: (sent.append((payee, amt)) or "tx-abc")
    h, *_ = _harness(dry_run=False, send_funds=rail, payees=["v"], threshold=1000.0)
    h.submit_outcome("paid", {"amount": 500}, 500)
    assert h.try_spend("v", 10.0, "x") is SpendDecision.EXECUTED
    assert sent == [("v", 10.0)]


def test_clawback_removes_budget():
    h, audit, kill, ledger = _harness(payees=["v"])
    c = h.submit_outcome("paid", {"amount": 300}, 300)
    assert h.budget() == 300.0
    assert ledger.clawback(c.claim_id, "fraud detected") is True
    assert h.budget() == 0.0


def test_clawback_window_delays_budget():
    h, audit, kill, ledger = _harness(payees=["v"], clawback=10_000)
    h.submit_outcome("paid", {"amount": 300}, 300)
    assert h.budget() == 0.0  # not matured yet


def test_audit_log_is_tamper_evident():
    h, audit, *_ = _harness(payees=["v"])
    h.submit_outcome("paid", {"amount": 100}, 100)
    assert audit.verify_integrity() is True
    audit._entries[0]["payload"]["amount"] = 999_999  # simulate tampering
    assert audit.verify_integrity() is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
