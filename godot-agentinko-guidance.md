# AgentInko × Godot: Building Incentivised Game-Making Agents

*Guidance for Kym — June 2026*

---

## TL;DR

- **"OpenClaw" is two unrelated projects.** Use the **agent framework** (heartbeat + skills + memory) as your orchestration model. Ignore the **Captain Claw game engine** of the same name — it's a single-game preservation project, GPLv3, needs the original 1997 assets, and is irrelevant to building new games.
- **Godot is a strong choice** for agentic generation: it's free/open, scriptable, runs headless, and already has mature **MCP servers** that let an agent create scenes/scripts, run the game, send inputs, capture screenshots, and read errors. That screenshot+input loop is exactly the *verification surface* AgentInko needs.
- **The hard part is the incentive signal, not the plumbing.** "Compiles and runs" is cheaply verifiable. "Fun" is not — the research is explicit that fun/engagement is subjective and resists algorithmic measurement. So tier your verified outcomes and gate the "fun" reward on **real human signals**, never an LLM's self-judgment (that's textbook reward hacking).

---

## 1. What to borrow from the OpenClaw *framework*

The OpenClaw agent framework (formerly Clawdbot/Moltbot; model-agnostic, large open-source community) is built around four patterns worth copying into AgentInko ([Milvus](https://milvus.io/blog/openclaw-formerly-clawdbot-moltbot-explained-a-complete-guide-to-the-autonomous-ai-agent.md), [Medium architecture write-up](https://bibek-poudel.medium.com/how-openclaw-works-understanding-ai-agents-through-a-real-architecture-5d59cc7a4764)):

1. **Heartbeat loop** — the agent wakes on a schedule to make progress and check state without a human prompt. Maps to your AgentInko "do work → submit outcome → earn budget" cycle.
2. **Modular AgentSkills** — capabilities are pluggable units. For games: `scaffold_project`, `write_gdscript`, `build_level`, `run_playtest`, `read_errors`, `fix_bug`, `publish_build`.
3. **Persistent memory** — survives across runs, so the agent accumulates a design knowledge base instead of starting cold each session.
4. **Model-agnostic gateway** — route to whichever model is best/cheapest per task; lets cost feed your treasury directly.

*Source caveat:* much of the published OpenClaw-framework detail comes from secondary write-ups rather than primary docs. Treat the specific stats (e.g. star counts) as indicative, and confirm against the actual repo before you commit architecture to it. The four patterns above are sound regardless of which framework you adopt.

---

## 2. The Godot execution + verification surface

This is the genuinely strong part of the stack. Several Godot MCP servers expose the engine to an agent:

- **godot-mcp (tugcantopaloglu)** — full Godot 4.x control, ~149 tools. ([GitHub](https://github.com/tugcantopaloglu/godot-mcp))
- **GDAI MCP (3ddelano)** — create scenes/resources/scripts, **read errors, run the game, press keys/input actions, and auto-screenshot the editor and running game** to verify output. ([GitHub](https://github.com/3ddelano/gdai-mcp-plugin-godot), [gdaimcp.com](https://gdaimcp.com/))
- **Godot Runtime / RTS MCP** — headless editing, live runtime control, batched input sequences, PNG viewport capture. ([LobeHub](https://lobehub.com/mcp/mikeumus-godot-mcp-rts))

The decisive capability: **the agent can run a build headless, drive it with scripted inputs, screenshot the result, and read the error log.** That closes the loop — AgentInko can independently check "did the thing the agent claims it built actually run and play?" rather than trusting the agent's word. ([DEV writeup](https://dev.to/y1uda/i-built-a-godot-mcp-server-because-existing-ones-couldnt-let-ai-test-my-game-47dl))

---

## 3. Turning "playable and fun" into verifiable outcomes

This is where it connects to the incentive framework you already have (`agent_incentive/`). The `OutcomeVerifier` should grade games in **three tiers of increasing difficulty and decreasing objectivity** — and budget/autonomy should weight them accordingly.

**Tier 1 — Build & integrity (cheap, fully objective). Verify automatically; necessary, not sufficient.**
Project compiles, zero script errors, launches to main menu, a scripted session runs N minutes without crashing, no null-reference/asset-missing errors, target framerate met. The Godot MCP error-read + headless-run + screenshot loop verifies all of this. *No Tier 1 pass → zero reward, full stop.*

**Tier 2 — Automated playtesting (medium cost, measurable proxies for "playable").**
Use AI/DRL playtest agents to play thousands of sessions and surface objective signals: level is completable, difficulty curve isn't a wall or a cakewalk, no softlocks/unreachable areas, economy/balance isn't degenerate, win/lose conditions trigger. The research base for this is solid — DRL playtesters detect design defects, balance issues, and visual glitches, and predict difficulty/engagement. ([Winning Isn't Everything (EA/arXiv)](https://arxiv.org/pdf/1903.10545), [Predicting Game Engagement & Difficulty](https://arxiv.org/pdf/2107.12061), [Automated platformer playtesting w/ RL](https://repository.library.northeastern.edu/files/neu:m0455c95d))

**Tier 3 — Fun (expensive, irreducibly subjective). Gate on REAL HUMANS, never on an LLM judge.**
The literature is blunt: *"fun and engagement are subjective qualities that are difficult to quantify algorithmically."* ([Towards Automated Playtesting](https://www.academia.edu/90536320/Towards_Automated_Playtesting_in_Game_Development)) So the "fun" reward must come from human signals with a verification source the agent can't write to: playtester ratings, session length / retention (D1/D7), completion rate, wishlists/downloads, store reviews. **Do not let an LLM "rate the fun" and feed that into the reward** — sycophantic/format-gaming LLM judges are a known reward-hacking failure (see the main plan, §2/§3). An LLM can *summarise* human feedback; it cannot *be* the fun signal.

### How this wires into `agent_incentive/`

Register verifiers keyed to outcome tiers, e.g.:

```python
verifier.register("build_passes",    check_godot_build_clean)     # Tier 1, MCP error log
verifier.register("playtest_clears", check_drl_completes_level)   # Tier 2, playtest agent
verifier.register("human_retention", check_real_player_retention) # Tier 3, analytics/store API
```

Budget weighting (illustrative): Tier 1 earns a small "you didn't waste compute" credit; Tier 2 earns moderate credit; **Tier 3 earns the large credit and unlocks autonomy** — because real players enjoying the game is the only outcome that actually benefits you. This makes the agent's incentive to ship *fun* games, not games that merely *compile*. Money/autonomy remains a consequence of verified player value, never the agent's goal — consistent with the guardrails in the main plan.

---

## 4. Recommended architecture

```
        ┌──────────────────────── AgentInko orchestrator ────────────────────────┐
        │  heartbeat loop · AgentSkills · persistent design memory · model gateway │
        └───────────────┬─────────────────────────────────────────┬───────────────┘
                        │ skills call                              │ outcomes
                        ▼                                          ▼
              ┌───────────────────┐                     ┌────────────────────────┐
              │  Godot MCP server │  build / run /       │  OutcomeVerifier (T1–3)│
              │  (GDAI / godot-mcp)│  input / screenshot  │  build · playtest · ppl│
              └─────────┬─────────┘  / read errors        └───────────┬────────────┘
                        ▼                                             ▼
                 Godot 4.x project  ───────── verified value ──▶  IncentiveLedger
                 (the actual game)                                   │
                                                                     ▼
                                          BudgetPolicy → Treasury (caps, approval,
                                                              kill switch, dry-run)
```

The incentive harness, treasury, caps, kill switch, and audit log are already built and tested in `agent_incentive/`. The new work is: (a) the Godot MCP skills, and (b) the three-tier verifiers.

---

## 5. Suggested build order

1. **Spike the Godot MCP loop manually.** Connect one MCP server (GDAI is the most agent-test-oriented) and have a model build a trivial game (one-screen platformer), run it headless, screenshot it, and read errors. Confirm the loop works end-to-end before adding incentives.
2. **Wire Tier 1 verification** into `agent_incentive/` so "compiles + runs clean" earns dry-run credit. Run in simulation.
3. **Add a Tier 2 playtest agent** (start with a scripted/random walker, graduate to DRL) for completability/balance.
4. **Only then add Tier 3** with real human playtesters and an analytics/store hook — and keep money in dry-run until you've watched the agent's behaviour against the §2/§3 failure signatures in the main plan.
5. **Earned autonomy:** raise caps/approval thresholds only for agents with a clean record of shipping Tier-3-verified games.

---

## 6. Open decisions for you

- **Game scope/genre.** Tightly-scoped 2D (arcade, puzzle, platformer) is far more tractable for an agent — and far easier to playtest-verify — than open-ended 3D. Recommend starting there.
- **Which MCP server** to standardise on (GDAI vs godot-mcp vs runtime MCP).
- **Where the "fun" signal comes from** in practice (internal testers? a small itch.io release? a Discord playtest group?). This determines your Tier 3 verifier.

---

### Sources

- OpenClaw game engine (Captain Claw): [GalaxyWing](https://www.galaxywing.com/openclaw-explained-the-open-source-engine-keeping-captain-claw-alive/)
- OpenClaw agent framework: [Milvus guide](https://milvus.io/blog/openclaw-formerly-clawdbot-moltbot-explained-a-complete-guide-to-the-autonomous-ai-agent.md), [architecture write-up](https://bibek-poudel.medium.com/how-openclaw-works-understanding-ai-agents-through-a-real-architecture-5d59cc7a4764)
- Godot MCP servers: [godot-mcp (tugcantopaloglu)](https://github.com/tugcantopaloglu/godot-mcp), [GDAI MCP (3ddelano)](https://github.com/3ddelano/gdai-mcp-plugin-godot), [gdaimcp.com](https://gdaimcp.com/), [Godot MCP RTS](https://lobehub.com/mcp/mikeumus-godot-mcp-rts), [DEV: AI testing my game](https://dev.to/y1uda/i-built-a-godot-mcp-server-because-existing-ones-couldnt-let-ai-test-my-game-47dl)
- Automated playtesting / measuring fun: [Winning Isn't Everything](https://arxiv.org/pdf/1903.10545), [Predicting Game Engagement & Difficulty](https://arxiv.org/pdf/2107.12061), [Automated platformer playtesting w/ RL](https://repository.library.northeastern.edu/files/neu:m0455c95d), [Towards Automated Playtesting](https://www.academia.edu/90536320/Towards_Automated_Playtesting_in_Game_Development)
