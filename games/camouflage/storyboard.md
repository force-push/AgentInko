# Camouflage — Storyboard & Build Spec

*Design lane: Claude. Build lane: Kimi (consumes `storyboard.json`).*
*Engine: Godot 4.x · Genre: reflex color-match arcade · Scope: very small (1 mechanic).*

---

## 1. Pitch

You are an octopus crossing open water that hunters patrol. The seabed beneath
you streams past as bands of color. **Match your skin to the band you're sitting
over, and you vanish. Mismatch when a hunter's scan sweeps past, and you're
spotted.** Keep matched, chain the streak, grab ink-pearls, and reach the reef
on the far side.

One verb — *change color at the right moment* — tuned into a tightening reaction
loop. Easy to learn in five seconds, hard to master, and (importantly for
AgentInko) **completely deterministic and measurable**.

## 2. Story & tone

Light, standalone (lore kept loose per the per-game branding call). A lone
octopus, a stretch of moonlit open water, silhouetted hunters cruising overhead.
No dialogue, no cutscenes — the tension *is* the story. Punchy, colorful,
arcade-y; a touch of held-breath dread on each scan.

## 3. Core loop

```
seabed scrolls  →  read the band you're over  →  swap to its color
   →  stay matched as the scan telegraph flashes  →  scan passes (safe!)
   →  combo + pearls  →  repeat until you reach the reef
```

- The octopus is **fixed** on screen (x ≈ 120); the colored seabed scrolls
  leftward at `scroll_speed`. The **active band** is whatever segment is under
  the octopus right now.
- The player sets the octopus's color with the palette keys. Matching the active
  band = camouflaged.
- Every `scan_interval` seconds a **hunter scan** sweeps the screen, preceded by
  a `telegraph` warning flash. **At the scan tick, octopus color must equal the
  active band color** — else *spotted* (lose a life).
- Staying matched builds a **combo** multiplier; **ink-pearls** float in some
  bands and bank points when collected while matched.
- Reach distance `D` (the reef) with at least one life → **level clear**.

## 4. Controls

| Input | Action |
|---|---|
| `1` `2` `3` `4` `5` | Set skin to palette color N (only first `palette_size` active) |
| `Left/Right` arrows or `A/D` | Optional nudge to grab a pearl / sit on a band edge |
| `R` | Restart level |

Designed to also be drivable headless/by the playtest agent via a simple input
sequence of "set color N at time T".

## 5. Difficulty design (the knobs the Tier 2 agent tunes)

**Principle: change one knob at a time.** Each level introduces a single new
source of pressure (a new colour, OR more speed, OR tighter scans) — never all
at once. Level 0 is a no-fail tutorial. The healthy target is completable by a
~250 ms reaction model but NOT by random play.

| Level | new pressure | palette | scroll (px/s) | scan (s) | telegraph (s) | distance (m) | target |
|---|---|---|---|---|---|---|---|
| 0 (tutorial) | learn swap + scan | 2 | 70 | 3.0 | 0.9 | 15 | 0.95 |
| 1 | +1 colour | 3 | 70 | 3.0 | 0.9 | 25 | 0.88 |
| 2 | faster scroll | 3 | 100 | 3.0 | 0.9 | 35 | 0.80 |
| 3 | tighter scans | 3 | 100 | 2.4 | 0.7 | 45 | 0.70 |
| 4 | +1 colour | 4 | 120 | 2.2 | 0.6 | 55 | 0.60 |
| 5 | full palette | 5 | 140 | 1.9 | 0.5 | 70 | 0.50 |

Feasibility rule (build agent must honor): `scan_interval - telegraph` must stay
**≥ human reaction floor (0.25 s)** so every level is *possible*. The playtest
agent flags any level that violates this or that a competent policy can't clear.

## 5a. Refinements (v2 — accessibility, feel, onboarding)

These came out of the mockup pass and matter for whether the game is actually
*playable and fun*, not just functional:

- **Colourblind accessibility (essential for a colour-match game):** every colour
  is paired with a **distinct symbol** — coral ● circle, teal ▲ triangle,
  magenta ■ square, lime ◆ diamond, amber ✚ cross. Symbols appear on the bands,
  on the octopus, and on the number keys, so the game never relies on colour
  alone.
- **Upcoming-bands preview lane:** a strip along the top shows the next 2–3 bands
  (colour + symbol) so play is *anticipation*, not pure twitch — and it's what
  makes the reaction windows feel fair.
- **Telegraph is audio + visual:** a rising hum pitches up toward the scan, so
  the "get matched now" cue isn't colour- or even sight-dependent.
- **Feel / juice:** satisfying pop + sparkle on each match and combo-up; a
  "close!" spark for a save within 0.15 s of the scan; spotted = red vignette and
  a brief slow-mo beat (punchy, not punishing).
- **Fail-forward fairness:** 3 lives, ~1 s invulnerability after being spotted,
  and an occasional **shield-pearl** that absorbs one mismatch — so a single slip
  isn't a run-ender.
- **Onboarding:** Level 0 is unfailable — 2 colours, slow scroll, huge telegraph
  — and teaches "swap colour" then "match before the scan" before any stakes.

## 6. Scoring

- +10 per second camouflaged (matched).
- Combo multiplier: ×1 → ×2 (5 s matched) → ×3 (10 s) → resets on mismatch.
- Ink-pearl: +50 × combo, only banked if collected while matched.
- Level-clear bonus: remaining lives × 200.

## 7. Art & audio direction

- **Palette:** high-contrast band colors (coral, teal, magenta, lime, amber) on
  a dark moonlit-water background; octopus glows faintly in its current color.
- **Scan telegraph:** screen-edge sweep line + low rising hum; the moment of scan
  is a brief desaturation flash.
- **Feedback:** satisfying "pop" + sparkle on match/combo-up; muffled thud +
  red vignette on spotted.
- **Vibe:** minimal HUD (distance bar, lives, combo, score). Readable at a glance.

## 8. Verifiable outcomes (the AgentInko contract)

**Tier 1 — build integrity (auto).** Project loads, no script/parse errors,
launches to the level, a headless run reaches the reef and emits
`[INKO] result completed=true time=… deaths=…`.

**Tier 2 — automated playtest (auto).** The playtest agent runs each level under
two policies:
- *competent* (a ~250 ms reaction model that swaps to the upcoming band in time),
- *random* (swaps colors at random).

Healthy game = **competent clears at/above the level's target completion**,
**random clears well below it** (proves skill matters, not luck), **no softlocks**
(the scroll guarantees progress, so a softlock = a bug), and **every level
satisfies the feasibility rule**. These map onto the existing playtest grader
(completion in the 40–95% band, softlock_rate ≈ 0).

**Tier 3 — fun (humans only).** Session length, ret­ry rate, "one more go" pull,
and rating from real testers. Never an LLM judge.

## 9. Build notes for the agent

- Single scene `Main` with: `Octopus` (player), a `Seabed` band-spawner, a
  `ScanController`, a `PearlSpawner`, and a `HUD`.
- Drive everything from `storyboard.json` `levels[]` so difficulty is data, not
  code — this is what lets the playtest agent retune without a rewrite.
- Emit the `[INKO]` markers (`game_ready`, `result completed=… time=… deaths=…`)
  so Tier 1/2 verification works out of the box.
- Keep it one mechanic. No feature creep. Ship level 1 first, verify, then add
  levels via data.
