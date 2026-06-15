# AgentInko — Market & Distribution Strategy

*Where these games should ship, and which genres/styles win. June 2026.*

---

## TL;DR

**Go web-first, not Steam-first.** For a pipeline that produces *many tightly-
scoped 2D games*, web portals (CrazyGames, Poki) are the right channel and Steam
is the wrong one — for three reasons that map directly onto how AgentInko works:

1. **Discovery is the portal's job, not yours.** Steam's organic discovery is
   effectively dead; web portals push your game to their audience for you.
2. **The model rewards a catalogue.** AgentInko's whole thesis is volume × a
   quality gate. Portals monetise a catalogue; Steam's per-title fee + saturation
   punish volume.
3. **Web gives you the Tier 3 "fun" signal as data.** Plays, retention, session
   length, completion, rewarded-ad views — exactly the real-human signal the
   incentive framework needs to close its loop. Steam gives you that far more
   slowly and only after a sale.

Use **Steam later and selectively** — only for a standout, *meatier* flagship
(e.g. a roguelite), priced premium, in a genre that actually sells there.

---

## 1. Steam: brutal for small games right now

The 2026 data is stark:

- **~18,000 new games in 2024; ~60 launching daily** — "organic discovery is
  effectively dead." ([games-stats Q1 2026](https://games-stats.com/blog/Steam_in_Q12026/), [Catch&Shoot 2026 trends](https://catch-and-shoot.com/the-definitive-ranking-of-indie-game-development-trends-that-will-define-2026/))
- **Wishlist-to-sale conversion ~0.125**, and without a big pre-launch wishlist
  and community a title is "statistically likely to fall into the sub-$350
  revenue bracket." ([Entalto Studios](https://entaltostudios.com/what-makes-indie-game-successful/))
- **Marketing now eats 30–50% of budget** (up from 10–20%), as ad auctions favour
  deep-pocketed AAA buyers. ([Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/indie-game-market))

Net: Steam is a *premium, wishlist-driven* storefront. A stream of small arcade
games with no community will drown. It only pays off for a polished, meatier
title you can market behind.

## 2. Web portals: built for exactly this

- **Audience is huge and the portal does discovery:** Poki ~60M MAU, CrazyGames
  ~35M MAU; the HTML5 game market passed **$6B** in 2026. ([Naavik: Web Gaming Strikes Back](https://naavik.co/digest/web-gaming-strikes-back/), [Playgama](https://playgama.com/blog/main/10-ways-to-monetize-html5-games-that-actually-work-in-2026/))
- **Instant play, no install** — zero friction, which is the whole reason small
  arcade games convert on web.
- **Revenue share is favourable and multi-portal:** aggregators like Playgama
  Bridge let you ship **one build to Poki + CrazyGames + Facebook Instant** and
  keep **~80%**; CrazyGames offers **+50% revenue share** for a 2-month launch
  exclusivity. ([Playgama](https://playgama.com/blog/main/10-ways-to-monetize-html5-games-that-actually-work-in-2026/), [CrazyGames dev portal](https://developer.crazygames.com/))
- **Monetisation fits free players:** rewarded video carries ~95% of players,
  IAP + daily-login the paying ~5%. No upfront sale needed; revenue scales with
  plays. ([Playgama](https://playgama.com/blog/main/10-ways-to-monetize-html5-games-that-actually-work-in-2026/))

Caveat: revenue *per* game is modest (CPM-based). The model only works at
**volume + quality** — which is precisely AgentInko's design (cheap Kimi builds,
gated by Tier 1/2 verification and Tier 3 human signal).

Godot exports cleanly to **HTML5/WebAssembly**, so the existing build lane targets
web natively — just mind build size and load time against portal guidelines.

## 3. Best-performing genres & styles

**Web portals — where AgentInko should focus** (top categories): **match-3,
puzzle, arcade, .io (multiplayer arena), mahjong, word, casual/hyper-casual.**
([FGL browser guide 2026](https://fgl.com/blog/ultimate-guide-to-browser-games-2026/), [GAMES.GG](https://games.gg/news/top-3-browser-game-websites-for-the-best-gaming-in-2026/)) These are easy to learn, instant-play — and conveniently the
**easiest to auto-playtest-verify** (clear completion/difficulty signals), so
they fit Tier 2 perfectly.

**Steam — premium, for a later flagship** (share of copies / revenue): **action-
adventure (~23–28%), RPG (~19%), survival / "crafty-buildy-sim" (~18%), shooters
(~15%)**, with **roguelite and strategy showing high *median* revenue.** ([web-game genre split](https://www.globenewswire.com/news-release/2026/04/03/3268097/0/en/gamivo-unveils-analysis-on-2026-s-most-popular-video-game-genres.html), [Steam indie genres](https://games.gg/news/steam-indie-golden-age-every-genre/))

**The AgentInko sweet spot** = genres that are *both* top-performing on web *and*
cleanly verifiable: **arcade, puzzle, match-3, and .io.** That's where to point
the pipeline.

## 4. How this lands on your concepts

- **Camouflage** (reflex arcade / color-match) is a textbook **web arcade/casual**
  title — ship it to CrazyGames/Poki. Its score + retention are the Tier 3 signal.
- **Inko's Ink Dash** (score-attack runner) and a **match-3 / .io** twist on the
  Inko world are the strongest web-catalogue bets.
- Save **Krakencrawl** (roguelite) as the candidate **Steam flagship** later —
  roguelite has high median revenue there and justifies a premium price.

## 5. Recommended plan

1. **Target web first.** Export Camouflage to HTML5, publish via an aggregator
   (Playgama Bridge → Poki + CrazyGames; consider CrazyGames' exclusivity boost).
2. **Wire portal analytics into Tier 3.** Plays, D1/D7 retention, session length,
   completion, rewarded-ad views become the verified "fun" signal feeding the
   incentive ledger — the loop finally closes with *real* players.
3. **Build a catalogue** of arcade/puzzle/.io titles in the Inko universe so they
   cross-promote.
4. **Graduate the best idea to Steam** as a premium flagship once it earns it.

---

### Sources

- Steam saturation/economics: [games-stats Q1 2026](https://games-stats.com/blog/Steam_in_Q12026/), [Entalto](https://entaltostudios.com/what-makes-indie-game-successful/), [Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/indie-game-market), [Catch & Shoot](https://catch-and-shoot.com/the-definitive-ranking-of-indie-game-development-trends-that-will-define-2026/)
- Web portals/monetisation: [Naavik](https://naavik.co/digest/web-gaming-strikes-back/), [Playgama](https://playgama.com/blog/main/10-ways-to-monetize-html5-games-that-actually-work-in-2026/), [CrazyGames dev portal](https://developer.crazygames.com/), [Metaplay](https://www.metaplay.io/blog/return-of-the-web-why-your-game-should-have-a-web-version-in-2024)
- Genres: [FGL browser guide](https://fgl.com/blog/ultimate-guide-to-browser-games-2026/), [GAMES.GG browser sites](https://games.gg/news/top-3-browser-game-websites-for-the-best-gaming-in-2026/), [GAMIVO genre analysis](https://www.globenewswire.com/news-release/2026/04/03/3268097/0/en/gamivo-unveils-analysis-on-2026-s-most-popular-video-game-genres.html), [Steam indie genres](https://games.gg/news/steam-indie-golden-age-every-genre/)
