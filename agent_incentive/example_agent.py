"""
Worked example: an incentivised agent that earns budget by delivering verified
outcomes, then spends (within caps) to do more work. Runs in DRY-RUN by default.

Run:  python example_agent.py
"""

import time

from incentive_framework import (
    AuditLog, OutcomeVerifier, IncentiveLedger, Treasury, TreasuryConfig,
    BudgetPolicy, KillSwitch, IncentiveHarness, SpendDecision,
)


# --- Your independent verifiers. In production these read your DB / payment ---
# --- API / git host — a source the AGENT CANNOT WRITE TO. Here: a fake one. ---
PAID_INVOICES = {"INV-001": 1000.0, "INV-002": 250.0}  # ground truth you control


def verify_invoice_paid(detail: dict) -> float:
    """Return the real paid amount, or 0 if not actually paid."""
    return PAID_INVOICES.get(detail.get("invoice_id"), 0.0)


def human_approval(req: dict) -> bool:
    """Stand-in for a real human approval (Slack button, email, etc.).
    Default-deny. Here we auto-approve nothing to demonstrate the gate."""
    print(f"  [APPROVAL NEEDED] {req} -> denied (no human in this demo)")
    return False


def build_harness() -> IncentiveHarness:
    audit = AuditLog()
    kill = KillSwitch(audit)

    verifier = OutcomeVerifier(audit)
    verifier.register("invoice_paid", verify_invoice_paid)

    ledger = IncentiveLedger(audit, clawback_window_s=0.0)  # 0 for demo; use hours/days

    treasury = Treasury(
        TreasuryConfig(
            per_tx_cap=100.0,
            rolling_cap=300.0,
            rolling_window_s=86_400,
            approval_threshold=100.0,   # >= $100 needs a human
            allowed_payees={"api-vendor", "compute-cloud"},
            dry_run=True,               # NO REAL MONEY until you flip this
        ),
        audit, kill, approval_hook=human_approval, send_funds=None,
    )

    policy = BudgetPolicy(payout_rate=0.5, base_grant=0.0)
    return IncentiveHarness(verifier, ledger, treasury, policy, audit), audit, kill


def main() -> None:
    harness, audit, kill = build_harness()

    print("Budget before any verified work:", harness.budget())

    # Agent claims two outcomes. One is real, one is fabricated.
    real = harness.submit_outcome("invoice_paid", {"invoice_id": "INV-001"}, 1000.0)
    fake = harness.submit_outcome("invoice_paid", {"invoice_id": "FAKE-999"}, 5000.0)
    print(f"Real claim   -> {real.status.value}, credited {real.verified_value}")
    print(f"Fake claim   -> {fake.status.value}, credited {fake.verified_value}  "
          f"(gaming the metric earns nothing)")

    time.sleep(0.01)  # let credit mature
    print("Budget after verified work:", harness.budget())   # 0.5 * 1000 = 500

    # Spend within caps + allow-list (dry-run).
    d1 = harness.try_spend("api-vendor", 80.0, "buy API credits")
    print("Spend $80 to api-vendor:", d1.value)

    # Over per-tx cap -> blocked.
    d2 = harness.try_spend("compute-cloud", 150.0, "big GPU batch")
    print("Spend $150 (over $100 cap):", d2.value)

    # Disallowed payee -> blocked (this is how you stop 'pay myself' behaviour).
    d3 = harness.try_spend("agent-personal-wallet", 50.0, "self-funding")
    print("Spend $50 to unlisted payee:", d3.value)

    # Human pulls the kill switch; further spends blocked regardless of budget.
    kill.engage("operator paused the agent")
    d4 = harness.try_spend("api-vendor", 20.0, "more credits")
    print("Spend after kill switch:", d4.value)

    print("Audit log intact:", audit.verify_integrity())
    print(f"Audit entries: {len(audit.entries())}")


if __name__ == "__main__":
    main()
