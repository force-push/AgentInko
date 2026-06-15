# agent_incentive

The AgentInko framework: principal-aligned, outcome-contingent incentives plus
the game-dev pipeline (model gateway, Godot MCP client, skills, verifiers, Tier 2
playtester). Full rationale: [`../incentivised-agents-plan.md`](../incentivised-agents-plan.md)
and [`../godot-agentinko-guidance.md`](../godot-agentinko-guidance.md).

## Core idea

An agent earns operating budget **only** by delivering outcomes an *independent*
verifier confirms. Money is a consequence of verified value, never the goal.
Self-preservation is never an objective. A human can halt at any time.

## Modules

| File | Role |
|---|---|
| `incentive_framework.py` | `AuditLog`, `OutcomeVerifier`, `IncentiveLedger`, `Treasury`, `BudgetPolicy`, `KillSwitch`, `IncentiveHarness` |
| `model_gateway.py` | Model-agnostic router — Claude for design, Kimi for build — with per-call cost tracking |
| `godot_mcp_client.py` | Adapter over an installed Godot MCP server (build/run/screenshot/read-errors/send-input) |
| `mock_godot_mcp.py` | In-memory mock Godot MCP server, so the pipeline runs with no engine |
| `skills.py` | `GameDevSkills` (ideate, storyboard, build_from_storyboard, fix_bug) + `Storyboard` handoff contract |
| `godot_verifier.py` | Tier 1 build-integrity verifier (`evaluate_output`, `run_godot_headless`) |
| `playtest_agent.py` | Tier 2 automated playtester (completion / difficulty / softlock → verified value) |

## Demos

- `example_agent.py` — incentive harness + guardrails (dry-run).
- `godot_demo.py` — Tier 1 verifier wired into the harness (`--real` for real Godot).
- `pipeline_demo.py` — full pipeline: idea → storyboard → Kimi build → T1 → T2 → budget.

## Tests

```bash
python3 -m pytest -q     # 36 tests
```

- `test_incentive_framework.py` — guardrail tests (caps, approval, kill switch, clawback, audit).
- `test_godot_verifier.py` — Tier 1 verifier + harness integration.
- `test_pipeline.py` — gateway routing/cost, MCP mock, skills, Tier 2 grading, full pipeline.

## Guardrails (enforced in code)

| Control | Where |
|---|---|
| Unverified/fabricated outcomes earn nothing | `OutcomeVerifier` |
| Hard per-transaction cap + rolling cap | `Treasury` |
| Payee allow-list (blocks "pay myself") | `Treasury` |
| Human approval above a threshold (default-deny) | `Treasury` |
| Real money requires an explicit rail; defaults to dry-run | `Treasury` |
| Budget matures on a delay + clawback | `IncentiveLedger` / `BudgetPolicy` |
| Kill switch the agent can't disengage | `KillSwitch` |
| Tamper-evident hash-chained audit log | `AuditLog` |

## To productionise

1. Replace mock verifiers with checks against sources the **agent cannot write to**.
2. Wire `model_gateway.invoke` to real Claude/Kimi APIs (and an image lane for assets).
3. Wire `GodotMCPClient` to a real Godot MCP server.
4. Only then set `Treasury(dry_run=False)` with a real `send_funds` rail — after legal/compliance sign-off.
