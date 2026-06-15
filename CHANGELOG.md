# Changelog

All notable work on AgentInko, by phase. Dates are when the work was done.

## 2026-06 — Initial build

### Incentive framework
- Principal-aligned, outcome-contingent incentive harness: `OutcomeVerifier`,
  `IncentiveLedger`, `Treasury` (per-tx + rolling caps, payee allow-list, human
  approval gate, dry-run default), `BudgetPolicy` (matured value + clawback),
  `KillSwitch`, tamper-evident `AuditLog`.
- Evidence-based design rationale and guardrails: `incentivised-agents-plan.md`.

### Godot Tier 1 slice
- Minimal Godot 4.x game "Inko Coin Dash" (`godot_game/`).
- Tier 1 build-integrity verifier (`godot_verifier.py`) wired into the harness:
  clean build earns credit, broken build earns nothing.
- Guidance: `godot-agentinko-guidance.md` (3-tier verification model).

### MCP connection + model gateway + skills
- `godot_mcp_client.py` adapter over a Godot MCP server, with `mock_godot_mcp.py`.
- `model_gateway.py` — Claude for design / Kimi for build, per-call cost tracking.
- `skills.py` — `GameDevSkills` with a structured `Storyboard` handoff contract.

### Tier 2 playtest agent + full pipeline
- `playtest_agent.py` — completion / difficulty / softlock proxies → verified value.
- `pipeline_demo.py` end-to-end (idea → storyboard → build → T1 → T2 → budget).
- Test suites totalling 36 passing tests.

### Dashboard
- `dashboard/` — zero-dependency local octopus-themed web UI over the live
  pipeline, with Healthy / Too-hard / Softlock / Broken scenarios.

### Game design & strategy
- `game-concepts.md` — six concepts with storylines, themes, verification fit.
- `games/camouflage/` — full storyboard spec (v2): accessibility (colour+symbol),
  preview lane, fail-forward fairness, tutorial, one-knob-at-a-time difficulty.
- `market-strategy.md` — web-first distribution recommendation + best-performing
  genres (arcade/puzzle/match-3/.io for web; roguelite/action-adventure for Steam).

### Notes
- Everything runs in dry-run with mock model + mock Godot backends (no keys, no
  engine required). Real Claude/Kimi APIs, a real Godot MCP server, and a real
  funds rail are wired in deliberately when productionising.
