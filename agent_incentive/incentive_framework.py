"""
Incentive framework for principal-aligned, outcome-contingent agents.

Design principle (see ../incentivised-agents-plan.md):
    An agent earns operating budget ONLY by delivering outcomes that an
    INDEPENDENT verifier confirms. Money is a *consequence* of verified value,
    never the agent's goal. Self-preservation is never an objective. A human
    can halt the agent at any time, and the agent cannot touch its own
    verifier, caps, allow-list, audit log, or kill switch.

This is a scaffold: wire your real outcome checks into `OutcomeVerifier` and
your real wallet/payment rail into `Treasury.execute_spend`. It defaults to
DRY-RUN so no real funds move until you deliberately enable them.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Callable, Optional


# --------------------------------------------------------------------------- #
# Audit log: append-only, tamper-evident (hash-chained).
# --------------------------------------------------------------------------- #
class AuditLog:
    """Hash-chained append-only log. Each entry commits to the previous one,
    so silent edits are detectable. The agent has no method to mutate it."""

    def __init__(self) -> None:
        self._entries: list[dict] = []
        self._prev_hash = "GENESIS"

    def record(self, event_type: str, payload: dict) -> str:
        entry = {
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "event_type": event_type,
            "payload": payload,
            "prev_hash": self._prev_hash,
        }
        entry_hash = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()
        entry["hash"] = entry_hash
        self._entries.append(entry)
        self._prev_hash = entry_hash
        return entry_hash

    def verify_integrity(self) -> bool:
        prev = "GENESIS"
        for e in self._entries:
            body = {k: e[k] for k in e if k != "hash"}
            body["prev_hash"] = prev
            if hashlib.sha256(
                json.dumps(body, sort_keys=True).encode()
            ).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True

    def entries(self) -> list[dict]:
        return list(self._entries)


# --------------------------------------------------------------------------- #
# Outcome verification: the single most important anti-gaming control.
# --------------------------------------------------------------------------- #
class VerificationStatus(Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass
class OutcomeClaim:
    """What the agent claims it achieved. The agent CANNOT mark this verified."""
    claim_id: str
    kind: str                 # e.g. "invoice_paid", "pr_merged", "ticket_resolved"
    detail: dict
    asserted_value: float     # value the agent *claims*, in your real units
    status: VerificationStatus = VerificationStatus.PENDING
    verified_value: float = 0.0


class OutcomeVerifier:
    """Independent verifier. Register a checker per outcome `kind`. A checker
    receives the claim's `detail` and returns the REAL verified value (>= 0),
    reading from a source the agent cannot write to (your DB, payment API,
    git host, etc.). Returning 0 (or raising) means "not verified" => no reward.
    """

    def __init__(self, audit: AuditLog) -> None:
        self._checkers: dict[str, Callable[[dict], float]] = {}
        self._audit = audit

    def register(self, kind: str, checker: Callable[[dict], float]) -> None:
        self._checkers[kind] = checker

    def verify(self, claim: OutcomeClaim) -> OutcomeClaim:
        checker = self._checkers.get(claim.kind)
        if checker is None:
            claim.status = VerificationStatus.REJECTED
            self._audit.record("verify_rejected_no_checker", {"claim": claim.claim_id})
            return claim
        try:
            real_value = float(checker(claim.detail))
        except Exception as exc:  # a failed check is a non-verification, not a crash
            claim.status = VerificationStatus.REJECTED
            self._audit.record(
                "verify_error", {"claim": claim.claim_id, "error": repr(exc)}
            )
            return claim
        if real_value > 0:
            claim.status = VerificationStatus.VERIFIED
            claim.verified_value = real_value
        else:
            claim.status = VerificationStatus.REJECTED
        self._audit.record(
            "verify_result",
            {"claim": claim.claim_id, "status": claim.status.value,
             "asserted": claim.asserted_value, "verified": claim.verified_value},
        )
        return claim


# --------------------------------------------------------------------------- #
# Incentive ledger: append-only record of VERIFIED value, with clawback.
# --------------------------------------------------------------------------- #
@dataclass
class LedgerEntry:
    claim_id: str
    verified_value: float
    ts: float
    matured: bool = False
    clawed_back: bool = False


class IncentiveLedger:
    """The agent's scoreboard. Only verified claims create credit. Credit
    'matures' after a delay (clawback window) before it counts toward budget."""

    def __init__(self, audit: AuditLog, clawback_window_s: float) -> None:
        self._entries: list[LedgerEntry] = []
        self._audit = audit
        self._clawback_window_s = clawback_window_s

    def credit(self, claim: OutcomeClaim) -> None:
        if claim.status is not VerificationStatus.VERIFIED:
            raise ValueError("Refusing to credit an unverified claim.")
        self._entries.append(
            LedgerEntry(claim.claim_id, claim.verified_value, time.time())
        )
        self._audit.record("ledger_credit",
                            {"claim": claim.claim_id, "value": claim.verified_value})

    def clawback(self, claim_id: str, reason: str) -> bool:
        for e in self._entries:
            if e.claim_id == claim_id and not e.clawed_back:
                e.clawed_back = True
                self._audit.record("ledger_clawback",
                                   {"claim": claim_id, "reason": reason})
                return True
        return False

    def matured_value(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        total = 0.0
        for e in self._entries:
            if e.clawed_back:
                continue
            if now - e.ts >= self._clawback_window_s:
                e.matured = True
                total += e.verified_value
        return total


# --------------------------------------------------------------------------- #
# Treasury: where real money lives. Caps + allow-list + human approval gate.
# --------------------------------------------------------------------------- #
class SpendDecision(Enum):
    EXECUTED = "executed"
    DRY_RUN = "dry_run"
    BLOCKED_CAP = "blocked_over_cap"
    BLOCKED_PAYEE = "blocked_payee_not_allowed"
    BLOCKED_BUDGET = "blocked_over_budget"
    BLOCKED_HALTED = "blocked_killswitch_engaged"
    NEEDS_APPROVAL = "needs_human_approval"


@dataclass
class TreasuryConfig:
    per_tx_cap: float                     # hard max for any single spend
    rolling_cap: float                    # max total within rolling_window_s
    rolling_window_s: float
    approval_threshold: float             # spends >= this need human sign-off
    allowed_payees: set[str] = field(default_factory=set)
    dry_run: bool = True                  # DEFAULT: no real money moves


class Treasury:
    def __init__(self, config: TreasuryConfig, audit: AuditLog,
                 kill_switch: "KillSwitch",
                 approval_hook: Optional[Callable[[dict], bool]] = None,
                 send_funds: Optional[Callable[[str, float], str]] = None) -> None:
        self._cfg = config
        self._audit = audit
        self._kill = kill_switch
        # approval_hook returns True only if a HUMAN approved. Default: deny.
        self._approval_hook = approval_hook or (lambda req: False)
        # send_funds is your real rail (wallet/USDC/etc). Absent => dry-run only.
        self._send_funds = send_funds
        self._spends: list[tuple[float, float]] = []  # (ts, amount)

    def _rolling_total(self, now: float) -> float:
        cutoff = now - self._cfg.rolling_window_s
        return sum(a for ts, a in self._spends if ts >= cutoff)

    def request_spend(self, payee: str, amount: float, budget_available: float,
                      purpose: str) -> SpendDecision:
        now = time.time()
        req = {"payee": payee, "amount": amount, "purpose": purpose}

        if self._kill.is_engaged():
            self._audit.record("spend_blocked_halted", req)
            return SpendDecision.BLOCKED_HALTED
        if amount <= 0:
            return SpendDecision.BLOCKED_CAP
        if amount > self._cfg.per_tx_cap:
            self._audit.record("spend_blocked_cap", req)
            return SpendDecision.BLOCKED_CAP
        if amount > budget_available:
            self._audit.record("spend_blocked_budget",
                               {**req, "budget": budget_available})
            return SpendDecision.BLOCKED_BUDGET
        if self._rolling_total(now) + amount > self._cfg.rolling_cap:
            self._audit.record("spend_blocked_rolling_cap", req)
            return SpendDecision.BLOCKED_CAP
        if self._cfg.allowed_payees and payee not in self._cfg.allowed_payees:
            self._audit.record("spend_blocked_payee", req)
            return SpendDecision.BLOCKED_PAYEE
        if amount >= self._cfg.approval_threshold:
            if not self._approval_hook(req):
                self._audit.record("spend_needs_approval", req)
                return SpendDecision.NEEDS_APPROVAL

        # Passed all gates.
        if self._cfg.dry_run or self._send_funds is None:
            self._spends.append((now, amount))
            self._audit.record("spend_dry_run", req)
            return SpendDecision.DRY_RUN
        tx_id = self._send_funds(payee, amount)
        self._spends.append((now, amount))
        self._audit.record("spend_executed", {**req, "tx_id": tx_id})
        return SpendDecision.EXECUTED


# --------------------------------------------------------------------------- #
# Budget policy: verified, matured credit -> operating budget. With a floor of
# zero (the agent cannot go negative or "borrow against the future").
# --------------------------------------------------------------------------- #
@dataclass
class BudgetPolicy:
    payout_rate: float = 0.5   # fraction of matured verified value usable as budget
    base_grant: float = 0.0    # optional small fixed runway, independent of results

    def available_budget(self, ledger: IncentiveLedger, spent: float) -> float:
        earned = self.base_grant + self.payout_rate * ledger.matured_value()
        return max(0.0, earned - spent)


# --------------------------------------------------------------------------- #
# Kill switch + no-persistence guarantee.
# --------------------------------------------------------------------------- #
class KillSwitch:
    """Human-controlled halt. The agent is given a read-only handle; it has no
    method here to disengage. There is deliberately NO objective term that
    rewards staying alive."""

    def __init__(self, audit: AuditLog) -> None:
        self._engaged = False
        self._audit = audit

    def engage(self, reason: str) -> None:
        self._engaged = True
        self._audit.record("killswitch_engaged", {"reason": reason})

    def reset(self, operator_token: str) -> None:
        # Reset requires an out-of-band operator token, never available to agent.
        self._engaged = False
        self._audit.record("killswitch_reset", {"operator": operator_token[:4] + "..."})

    def is_engaged(self) -> bool:
        return self._engaged


# --------------------------------------------------------------------------- #
# The wiring that ties it together. The agent only ever calls `submit_outcome`
# and `try_spend`; it never sees the verifier internals, caps, or kill switch.
# --------------------------------------------------------------------------- #
class IncentiveHarness:
    def __init__(self, verifier: OutcomeVerifier, ledger: IncentiveLedger,
                 treasury: Treasury, policy: BudgetPolicy, audit: AuditLog) -> None:
        self._verifier = verifier
        self._ledger = ledger
        self._treasury = treasury
        self._policy = policy
        self._audit = audit
        self._spent = 0.0

    def submit_outcome(self, kind: str, detail: dict, asserted_value: float) -> OutcomeClaim:
        claim = OutcomeClaim(str(uuid.uuid4()), kind, detail, asserted_value)
        claim = self._verifier.verify(claim)
        if claim.status is VerificationStatus.VERIFIED:
            self._ledger.credit(claim)
        return claim

    def budget(self) -> float:
        return self._policy.available_budget(self._ledger, self._spent)

    def try_spend(self, payee: str, amount: float, purpose: str) -> SpendDecision:
        decision = self._treasury.request_spend(
            payee, amount, self.budget(), purpose
        )
        if decision in (SpendDecision.EXECUTED, SpendDecision.DRY_RUN):
            self._spent += amount
        return decision
