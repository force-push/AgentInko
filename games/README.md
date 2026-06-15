# games

Game specs and storyboards produced by the design lane (Claude), consumed by the
build lane (Kimi) via the `Storyboard` contract in `agent_incentive/skills.py`.

Concept shortlist and ratings: [`../game-concepts.md`](../game-concepts.md).
Distribution & genre strategy: [`../market-strategy.md`](../market-strategy.md).

## Titles

| Folder | Title | Genre | Status |
|---|---|---|---|
| `camouflage/` | Camouflage | reflex color-match arcade | storyboard complete (v2, refined) |

Each game folder holds:

- `storyboard.md` — human-readable design doc (pitch, loop, difficulty, art, verifiable outcomes).
- `storyboard.json` — structured build contract (mechanics, entities, levels[], accessibility, feedback) that the build agent consumes; difficulty lives in `levels[]` as data so the Tier 2 playtester can retune without a rewrite.

## Camouflage highlights

Reflex color-match: match your skin to the seabed band you sit over and survive
the hunter scans to reach the reef. Refined for accessibility (every colour paired
with a symbol), an upcoming-bands preview lane, fail-forward fairness, an
unfailable tutorial, and one-knob-at-a-time difficulty. A textbook web-arcade
title (see market strategy).
