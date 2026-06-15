# dashboard

A funky deep-sea **octopus** dashboard for AgentInko — a zero-dependency local
web app (Python stdlib only) that runs the real pipeline and visualizes it.

## Run

```bash
python3 server.py          # from this folder, or: python3 dashboard/server.py
# open http://localhost:8777
```

No pip installs, no API keys, no Godot needed — it uses the mock model + mock
Godot backends behind the real `agent_incentive` pipeline.

## What it shows

- Inko, an animated octopus (swaying tentacles, blinking eyes) over a
  bioluminescent deep-sea backdrop with drifting bubbles.
- The pipeline ribbon: idea → storyboard → build → Tier 1 → Tier 2 → Tier 3.
- Model gateway Claude/Kimi cost split, treasury + guardrails, a live playtest
  gauge with the healthy 40–95% band, and the hash-chained audit log.
- Four scenario buttons — **Healthy / Too hard / Softlock / Broken** — re-run the
  pipeline live so you can watch the verifier reward or reject each outcome.

## Files

- `server.py` — stdlib HTTP server; `/api/state?scenario=…` runs the pipeline and returns JSON.
- `index.html` — single-file UI; fetches `/api/state`, falls back to embedded sample data if opened via `file://`.
