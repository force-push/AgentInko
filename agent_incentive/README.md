# agent_incentive

Reference scaffold for **principal-aligned, outcome-contingent** agents.
Full rationale and evidence: [`../incentivised-agents-plan.md`](../incentivised-agents-plan.md).

## Core idea

An agent earns operating budget **only** by delivering outcomes an *independent*
verifier confirms. Money is a consequence of verified value, never the agent's
goal. Self-preservation is never an objective. A human can halt at any time.

## Files

- `incentive_framework.py` — the framework: `AuditLog`, `OutcomeVerifier`,
  `IncentiveLedger`, `Treasury`, `BudgetPolicy`, `KillSwitch`, `IncentiveHarness`.
- `example_agent.py` — worked demo (dry-run). `python3 example_agent.py`
- `test_incentive_framework.py` — guardrail tests. `python3 -m pytest -q`

### Godot Tier 1 slice (end-to-end)

- `godot_verifier.py` — Tier 1 build-integrity verifier. Runs the Godot project
  in `../godot_game` headless, parses output for script/parse/resource errors,
  and credits a clean build only. `evaluate_output()` is a pure function the
  tests exercise without the engine installed.
- `godot_demo.py` — agent ships a build → verifier grades it → only a clean
  build earns budget → unlocks a capped dry-run spend.
  `python3 godot_demo.py` (captured samples) or `--real` (needs Godot 4.x on PATH).
- `test_godot_verifier.py` — verifier + harness-integration tests.

The game itself lives in `../godot_game/` (`project.godot`, `scenes/main.tscn`,
`scripts/main.gd`). Run it directly with `godot --headless --path ../godot_game`
once Godot 4.x is installed.

## The guardrails (enforced in code)

| Control | Where |
|---|---|
| Unverified/fabricated outcomes earn nothing | `OutcomeVerifier` |
| Hard per-transaction cap | `Treasury` |
| Rolling spend cap | `Treasury` |
| Payee allow-list (blocks "pay myself") | `Treasury` |
| Human approval above a threshold (default-deny) | `Treasury` |
| Real money requires an explicit rail; defaults to dry-run | `Treasury` |
| Budget matures on a delay + clawback | `IncentiveLedger` / `BudgetPolicy` |
| Kill switch the agent can't disengage | `KillSwitch` |
| Tamper-evident hash-chained audit log | `AuditLog` |

## To productionise

1. Replace the demo verifiers with checks against sources the **agent cannot
   write to** (your DB, payment API, git host).
2. Wire `approval_hook` to a real human channel (Slack/email approval).
3. Only when ready: set `dry_run=False` and pass a real `send_funds` rail.
   Get legal/compliance sign-off first (money transmission, tax, securities).
4. Start in simulation (Phase 0), then tiny gated real money (Phase 1),
   then earned autonomy (Phase 2). See the plan doc.
