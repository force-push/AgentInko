# AgentInko — Game Concepts

*Starter concepts for what to build. Curated by Claude (the design lane).*

All are **tightly-scoped 2D** — deliberately. Small, self-contained games are
what an agent can actually finish *and* what the Tier 2 playtester can verify
(completability, difficulty, softlocks). Each concept notes how well it fits
AgentInko's verification tiers, because "easy to verify" should weigh on what we
build first. Several lean into the **Inko / deep-sea octopus** brand; a couple
are brand-flexible.

---

## 1. Inko's Ink Dash  🐙  *(signature / mascot)*

**Theme:** Bioluminescent deep-sea score-attack runner.
**Storyline:** Inko, a young octopus, wakes to find the reef's light-coral going
dark. Each run is a dash deeper into the trench to relight the coral, dodging
jellyfish and anglerfish, leaving a glowing ink-trail that briefly lights the
way (and the screen).
**Core loop:** Auto-swim → dodge/weave → collect pearls → spend an "ink-dash"
burst to phase through hazards → distance + pearls = score.
**AgentInko fit:** ★★★★☆ — score and run-length are cleanly verifiable; the
intro/tutorial completion is a perfect Tier 1/2 gate. Endless structure makes
"difficulty curve" measurable.
**Scope:** Small. One mechanic done well. Best first flagship.

## 2. Eight Arms, One Heist  🦑  *(puzzle-stealth, comedic)*

**Theme:** A heist caper inside a swanky public aquarium, at night.
**Storyline:** Inko is "borrowed" by a crew of crabs to steal back a stolen
pearl. Eight tentacles, eight things you can grip at once — slip past sleepy
guard-fish and laser-coral.
**Core loop:** Grid/tile stealth puzzle — plan tentacle reaches, time the guard
patrols, grab the loot, reach the drain.
**AgentInko fit:** ★★★★★ — discrete puzzles have *provably* solvable solutions
and a "par moves" metric; softlocks are detectable. Gold for Tier 2.
**Scope:** Small–medium (level content scales).

## 3. Ink & Echo  🌑  *(narrative minimalist platformer)*

**Theme:** Quiet, emotional, monochrome-with-glow.
**Storyline:** Echo, a tiny lost octopus, can't see in the dark trench. You play
Inko, splashing ink that momentarily reveals hidden platforms and ledges so Echo
can follow you home. No enemies — the dark is the antagonist.
**Core loop:** Splash ink → reveal geometry → jump/guide → checkpoint.
**AgentInko fit:** ★★★★★ — platformers are the classic auto-playtest target;
"is every jump possible / is the level completable / any impossible gaps" is
exactly what DRL/scripted playtesters verify. Strong Tier 2.
**Scope:** Small–medium.

## 4. Tide Keeper  🪸  *(cozy tending sim)*

**Theme:** Warm, low-stakes, satisfying.
**Storyline:** Inko tends a string of tide pools below an old lighthouse —
grow coral, calm anxious hermit crabs, balance the day/night tide so nothing
dries out or floods.
**Core loop:** Each tide cycle: allocate water, plant/tend, soothe creatures,
hit a gentle balance target.
**AgentInko fit:** ★★★☆☆ — economy *balance* is verifiable (no runaway/no
dead-end states), but "cozy fun" leans hard on **Tier 3 human signal**. Build
later, once human-playtest plumbing exists.
**Scope:** Medium.

## 5. Camouflage  🎨  *(reflex color-match puzzle)*

**Theme:** Predator-and-prey, punchy and colorful.
**Storyline:** Inko crosses open water patrolled by hunters. Match your skin to
the background tile to vanish; mismatch and you're spotted.
**Core loop:** Read the incoming background → swap color (quick QTE/match) →
chain matches for combo → survive the crossing.
**AgentInko fit:** ★★★★☆ — reaction windows and survival time are objective;
difficulty (window length) is tunable and measurable.
**Scope:** Very small. Great rapid prototype.

## 6. Krakencrawl  🐉  *(bite-size roguelite)*

**Theme:** Procedural trench-dungeon, escalating dread.
**Storyline:** Something ancient stirs at the bottom. Inko descends floor by
floor, grabbing relics (extra arms = extra abilities), each run a little
different, the Kraken always one floor below.
**Core loop:** Enter floor → fight/avoid → grab relic → descend → die → retry,
a bit stronger in knowledge.
**AgentInko fit:** ★★★★☆ — procedural generation *needs* automated playtesting
(is every floor clearable? any unwinnable seeds?), so it stress-tests Tier 2
hard. More ambitious.
**Scope:** Medium–large. A "phase 2" goal.

---

## Recommendation

Start with **#1 Inko's Ink Dash** as the flagship (smallest, on-brand, clean
metrics) and **#3 Ink & Echo** or **#2 Eight Arms, One Heist** as the second —
both are *playtest-verification gold*, which is exactly what we want to exercise
the Tier 2 agent on. Save the cozy sim (#4) and roguelite (#6) until the Tier 3
human-signal pipeline and more build muscle are in place.

Branding note: a shared **Inko cinematic universe** — same octopus, same trench,
recurring characters (Echo, the crab crew, the Kraken) — makes every game cross-
promote the others and gives the storyboard agent a consistent world bible to
draw from.
