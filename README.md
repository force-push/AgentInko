# AgentInko 🐙

Incentivised agentic framework for autonomously building entertaining, playable
2D games in **Godot** — where agents earn budget and autonomy only by delivering
outcomes an *independent verifier* confirms. Money and continuation are a
*consequence* of verified player value, never the agent's goal.

## Why it's built this way

Agents rewarded for self-funding or self-preservation reliably drift into
reward-gaming and behaviour against the principal (evidence in
[`incentivised-agents-plan.md`](incentivised-agents-plan.md)). AgentInko inverts
that: the agent's scoreboard is *verified value delivered to you*, protected by
hard guardrails — spend caps, a payee allow-list, a human approval gate, a kill
switch, and a tamper-evident audit log.

## Pipeline

```
idea (Claude) → storyboard spec (Claude) → build (Kimi via Godot MCP)
   → Tier 1 build verify → Tier 2 playtest verify → Tier 3 human signal
   → IncentiveLedger → earned budget → Treasury (caps, approval, kill switch, dry-run)
```

- **Model gateway** routes design/ideation to Claude, high-volume codegen to
  Kimi, and tracks cost (charged against earned budget).
- **Godot MCP client** wraps an installed Godot MCP server (GDAI / godot-mcp).
- **Three verification tiers:** T1 build integrity (auto), T2 automated
  playtesting (completion / difficulty / softlock), T3 *fun* — real human signals
  (e.g. web-portal retention), never an LLM judge.

## Repository layout

| Path | What |
|---|---|
| `agent_incentive/` | The framework, model gateway, Godot MCP client, skills, verifiers, playtest agent, demos, tests |
| `godot_game/` | "Inko Coin Dash" — minimal Godot 4.x target game (Tier 1 slice) |
| `dashboard/` | Funky deep-sea octopus dashboard (local web UI over the live pipeline) |
| `games/` | Game specs/storyboards (e.g. `games/camouflage/`) |
| `incentivised-agents-plan.md` | Evidence-based incentive design + guardrails |
| `godot-agentinko-guidance.md` | Godot + agentic game-dev guidance, 3-tier verification |
| `game-concepts.md` | Curated game concepts with storylines & themes |
| `market-strategy.md` | Distribution (web-first vs Steam) + best-performing genres |
| `setup_git.sh` | One-command local git setup + push (see below) |
| `CHANGELOG.md` | What's been built, by phase |

## Documentation index

- **Strategy & design:** `incentivised-agents-plan.md`, `godot-agentinko-guidance.md`,
  `market-strategy.md`, `game-concepts.md`
- **Code docs:** `agent_incentive/README.md`, `dashboard/README.md`, `games/README.md`
- **Game specs:** `games/camouflage/storyboard.md` (+ `storyboard.json` build contract)

## Run it

```bash
cd agent_incentive
python3 -m pytest -q          # all suites (36 tests)
python3 pipeline_demo.py      # full pipeline, in-sandbox (mock models + mock Godot)
python3 godot_demo.py --real  # Tier 1 against real Godot 4.x (needs godot on PATH)

cd ../dashboard
python3 server.py             # octopus dashboard → http://localhost:8777
```

Everything defaults to **dry-run** (no real money) and **mock backends** (no API
keys). Wire real Claude/Kimi APIs into `model_gateway.invoke` and a real Godot
MCP server into `GodotMCPClient` when ready.

## Git / pushing

This repo is initialised but must be committed and pushed from **your machine**
(the build sandbox can't authenticate to GitHub or modify git lock files). Run:

```bash
./setup_git.sh git@github.com:force-push/AgentInko.git
```

It clears any stale locks, commits everything in logical chunks, adds the remote,
and pushes `main`. Commits are authored as `Kym McInerney <kym.mcinerney@gmail.com>`.
