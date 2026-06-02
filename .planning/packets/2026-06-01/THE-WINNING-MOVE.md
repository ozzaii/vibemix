# THE WINNING MOVE — where vibemix goes to win

**Role:** Money Synthesizer (read-only, final call). **Date:** 2026-06-01. **HEAD:** `ed081570` (EQ keystone `970e165b` already in tree).
**Inputs:** 5 strategy pitches (viral-clip / pro-coach / streamer / B2B-education / moat) + 3 judge panels (feasibility / revenue-ceiling / defensibility). Every load-bearing claim is file:line or packet-grounded.
**Sources:** `RED-TEAM-SHIP-REALITY.md`, `GOLD-WIRING-MAP.md`, `POST-CODEX-FUTURE-AND-PACKET-BACKLOG.md`, `recovered/wf_6a7ea8f4-751__the-vibemix-creative-idea-forge.md`, `FEATURE-STATE-OF-THE-UNION.md`.
**Verified this session:** `predicted_band_gains` (eq keystone) is wired into `state/deck_context.py:1873` → `_licensed_move_effect:1847` → `apply_live_claim_guard:2519` returning `policy="move_effect_supported"`. The narrator→coach flip for the EQ/filter axis is **BUILT+WIRED in source**, not planned. This single fact reshapes the ranking.

---

## 1. AGGREGATE JUDGE SCORES (ranked)

| Rank | Strategy | Feasibility | Revenue Ceiling | Defensibility | **Total /30** | One-line |
|------|----------|:-----------:|:---------------:|:-------------:|:-------------:|----------|
| **1** | **#2 Pro-Coach (Learn/Earned skill-tree)** | **8** | 6 | **8** | **22** | Most-built engine; the moat and the product are the same object; its depth keystone landed this session. |
| 2 | #4 B2B / Education | 5 | 4 | 7 | 16 | Owns the single best wedge (cited debrief PNG, routes around the MOSS kill-shot), but a €1–3M-TAM niche, not a business. |
| 3 | #5 Moat / Universal-Ingest | 5 | 5 | 6 | 16 | Names the real compound moat, but 2 of 3 pillars are NOT-FOUND/unwired and the flywheel's compounding is unproven. |
| 4 | #1 Viral-Wedge (auto-clip) | 6 | 6 | 4 | 16 | Cheap render (deps shipped), CAC≈€0, highest unit-economics — but explicitly "don't build yet" and the most copyable asset. |
| 5 | #3 Streamer / OBS overlay | 4 | 8 | 5 | 17 | Highest ceiling (escapes €4.99 floor) but most-fragile: bets the product on charisma-under-starvation, its weakest axis, into an incumbent-owned market. |

**Read of the table.** Pro-Coach wins decisively on the two judges that gate execution and durability (feasibility 8, defensibility 8) and is mid on ceiling. Streamer outscores three runner-ups on raw total only because of an 8 on the one lens (ceiling) that is *conditional on everything else working first* — the same judge called it "highest variance" and "most fragile." Ceiling without feasibility is a lottery ticket; the other two judges priced that. The three 16-point ties (B2B, Moat, Viral) each own one genuinely best-in-class asset that the winner should *graft*, not discard.

---

## 2. THE WINNING PLAY

**#2 — The Pro-Coach. vibemix is the DJ coach that physically cannot lie to you.**

It wins for one structural reason no other play has: **the moat and the product are the same object.** Every other strategy either borrows the grounding gate into a copyable wrapper (clip renderer, OBS overlay) or builds its differentiator on unbuilt seams (universal readers, taste flywheel) or in a market too thin to fund the build (DJ schools). The Pro-Coach sells the one asset that is uncopyable *and* already built: the double-gated citation spine, surfaced as a skill-tree where **"Mastered" unlocks only on a cited live demonstration** (`runtime/coach.py:123` `_credit_live_skill_demo`, callers verified at `:276`/`:405`). A fast-follower cannot ship the feature a buyer sees ("you can't buy mastery, you earn it on a real deck and we measured it") without first rebuilding the single-writer perception spine + `CitationLinter` underneath it. The keystone that turns the live brain from narrator to coach — `eq_move_model.py` → `apply_live_claim_guard` — **landed and wired this session**, which every prior analyst flagged as the missing dependency. The load-bearing risk just collapsed from "invention" to "wiring + reach."

It is not the highest-ceiling play. It is the play with the **highest expected value**: a defensible €4.99/€9.99 coach you can actually ship in weeks, that funds the bigger bets, and whose own growth loop (the share-card) doubles as the viral wedge.

---

## 3. THE GRAFT — one sequenced motion, not five strategies

The winner absorbs the best organ from each runner-up. The motion is **a single product with a coach core, a viral top-funnel, and a B2B margin lane bolted to the same engine:**

- **GRAFT the viral wedge (#1) as the share-card, not a screencap clip.** The Pro-Coach's debrief already produces cited drills (`debrief/drills.py:51`, mandatory `citation` field) and an mp3 TLDR (`debrief/tldr.py:9`, PyAV `libmp3lame`). Render that into the **Receipt scorecard PNG** (creative-forge "The Receipt" / Why-It-Worked Receipts, B5 in backlog) — a static card off `events.jsonl` + `EvidenceRegistry`, drawn with `pillow>=12.2.0` + `av>=17.0.1` (**already shipped deps**, zero new dependency, zero server, zero API cost). The hero line is the *grounded coaching quote* ("your low-cut thinned the bass — sub cratered 18 dB"), which the keystone now makes real. This is the top-of-funnel: "the moat IS the marketing." The viral analyst's own kill-shot — "do not build the clip until the brain coaches well" — is now *satisfied* for the EQ axis, so the share-card is unblocked exactly where it wasn't a week ago.
- **GRAFT the B2B wedge (#4) as a margin lane, not a business.** The same cited debrief PNG is the DJ-school "report card." It is text-first and routes around the MOSS-mute kill-shot entirely (no TTS needed). Treat it as a **concierge cash lane funded by Francesco's network with a hard 90-day kill-trigger** (3 paid pilots or stop) — never as the company. The grounding-gate-as-liability-shield reframe is real selling copy, but the TAM ceiling (€1–3M) means it pays for runway, not the roadmap.
- **GRAFT the moat-play's discovery wedge (#5) as the in-app hook.** "Rediscover your own library" (text→track via CLAP, centered-cosine REAL-proven `test_clap_real_retrieval.py`) is currently CLI-only — surface it as a Crate search box. It is the cheapest "holy shit" demo in the product and it sells the Studio tier. Pair with **Traktor `.nml` ingest (B1a, ~0.5d)** to open Francesco's base — the only build that *gets new users* and the seam-proof for Universal Ingest.
- **PARK the streamer play (#3) as Act 2.** Highest ceiling, but it bets on charisma-under-starved-input — the exact axis the engine is built to *avoid* (it shuts up rather than entertain). Ship the coach to bedroom DJs first where failure is cheap and private; point the same engine at an OBS overlay *after* the charisma problem is solved on private sessions. The one cheap experiment worth running now: a single OBS overlay off the existing ws bus + mascot with 2–3 of Francesco's DJ streamers, measured purely on "does one clip travel." <1 week, kills-or-validates the whole second act.

**The combined motion in one sentence:** the coach makes you better (revenue), the cited share-card proves it publicly (top-funnel), the school report-card pays the runway (margin), the library-discovery box hooks the trial — all four are the **same grounded engine wearing four skins**, which is why this is one product, not a portfolio.

---

## 4. THE 90-DAY EXECUTION SEQUENCE (grounded in what's built/landing)

**Phase 0 — Unbreak the ship (Weeks 1–3). Nothing else counts until a stranger's machine speaks.**
Every strategy's first dollar sits behind two PKG kill-shots (`RED-TEAM` ①②). These are pure execution, not invention:
1. **B-1: Host + bundle MOSS-TTS-Nano ONNX**, pin URL+SHA+size, first-run auto-download (`model_assets.py:624` "not hosted by default" → fixed). *Sequenced FIRST — the DMG must not be rebuilt before this or it re-ships mute.*
2. **X1: Voice-picker bug** — default `"kore"` doesn't exist in MOSS (`config_store.py:169`), all 8 picks resolve to one wrong voice (`local_tts.py:276`). Repopulate `VOICE_OPTIONS` from MOSS `builtin_voices`, re-default. `<1d`, ship-blocker the source packets missed.
3. **B-4: Rebuild + sign + notarize the DMG from clean HEAD** (currently 177 commits stale, arm64-only, born mute). Scope "Apple Silicon v1" or add x86_64 — Kaan decision.
4. **B-3 (Kaan/infra): one keyless proxy round-trip** on `api.altidus.world` with a live Gemini key.

**Phase 1 — Make the coach worth €4.99 + the share-card that markets it (Weeks 3–7).** Pure wiring of already-running engines (`POST-CODEX §3`, `GOLD-WIRING-MAP` Cards 4):
5. **W1: Spoken next-track + transition verdict (★★★★★).** The voice reads `SuggestionService` (silent today, `coach.py:644`) + the orphaned 10-dim `transition_scorer` (`intel/transition_scorer.py`, zero coach callers) into a `[track:]`/risk-cited line. ~0.5–1d. *This is the demo that turns commentator into coach — "9A→4A, phrases aligned, bring it in over 16 bars."* Gate: `vibemix-grounding-review`.
6. **B5: Debrief Receipt scorecard PNG (★★).** The viral graft. 1–2d, `frontend-enforcement` gate. The share-card whose hero is the now-real grounded coaching line.
7. **B1a: Traktor `.nml` ingest (★★★★★ reach) + Crate discovery search box.** Opens Francesco's base; surfaces the REAL-proven CLAP discovery wedge. ~0.5d parser + a frontend search surface.

**Phase 2 — The credibility floor + reach (Weeks 7–12).** The two gaps that, left open, cause churn:
8. **B2: Practice-deck loop → `BEATMATCH_GRADED` (★★★★).** The consumer already waits at `skill_recognizer.py:154`; the emitter is NOT-FOUND. Beatmatching — the #1 skill a learner pays to be graded on — is permanently capped at "Competent" (`_HONEST_UNCREDITABLE_V11=("beatmatching",)`) until this lands. **Non-optional: it is the credibility floor of the paid tier.** 2–3d.
9. **House + DnB genre detectors.** All 9 structure detectors are techno-shaped; `GenreRouter→"unknown"` for house/DnB/disco = *most of the paying market*. Without this, a house DJ buys Pro and the coach narrates "unknown phase" → instant refund. Land BEFORE any paid GTM beyond Francesco's (techno-leaning) network.
10. **B3: grounding siblings (`lufs.py` + `loop_geometry.py`, wire `xfade.py`) (★★★).** Each ~½–1d numpy. Widens "coach" past the single EQ axis — every axis you don't add is an axis where the co-host keeps narrating.

**GTM in parallel (the whole 90 days):** Francesco's DJ network is the first-$1k channel (warm outreach, 20–40 DJs at €4.99). The marketing asset is a 90-second video of the coach *refusing to praise a sloppy transition* — the anti-slop gate as the hook. €150–200 IG spend drives the share-card loop once B5 ships.

---

## 5. THE REALISTIC MONEY MODEL

**Structure:** free desktop app (live co-host, grounded reactions, CLAP discovery — the funnel) → **€4.99 Pro** (Learn/Earned skill-tree, full coaching, spoken recommendation, debrief + share-card) → **€9.99 Studio** (Viber set-prep, cross-format ingest, advanced debrief, taste personalization). Decided pricing, memory `project_viber_launch_and_pro_pricing`. Unit economics close **only because inference is on-device**: CLAP + MOSS = €0 marginal; the sole cloud line is the Gemini reaction brain through the Bravoh proxy with per-client caps (built + deployed, `project_vibemix_proxy_deployed_altidus`). A cloud-TTS competitor bleeds ~70%/turn (cost study); vibemix doesn't.

- **First $1k (~200 Pro-months / ~40 annual Pro).** Requires **only Phase 0** (kill-shots cleared) + Francesco's network. No new feature — the engine already earns it. The 90-second "refuses to lie" clip is the entire marketing spend. **Assumption:** packaging lands in ~3 weeks and ≥40 warm DJs convert at €4.99. Reachable on the budgeted €150–200.
- **First $100k (~1,700 Pro-months sustained / ~1k active subs).** Requires **Phase 1 + Phase 2**: spoken recommendation (W1) justifies the tier, the share-card loop (B5) drives organic installs past paid CAC, beatmatching is gradable (B2) so the skill-tree's headline isn't greyed out, and **house+DnB detectors exist** so the buyer isn't the techno minority. **Assumption:** share-card viral coefficient is *positive* (not necessarily >1) and genre reach covers ≥3 genres. This is the gated milestone — without genre breadth the clip says "heavy grinding synth" and nobody shares it.
- **First $1M (~17k Pro-months sustained, real retention).** Requires depth + personalization + the flywheel *measured to compound*: live taste learning (W3, off the 0.05 floor), prep→live set awareness (W2), the personal-tells layer (creative-forge "Learning Your Tells" — count-based only, the safe family), and Studio carrying weight via genuine set-prep. **Assumption that must be tested, not believed:** the taste model actually improves with library size (CLAP text→audio is coarse-only — `project_clap_text_audio_unreliable` — so the compounding curve may be flat). If it compounds, the per-user flywheel keeps CAC sane at scale and the moat is felt. If it doesn't, fall back to competing on grounding-quality + genre breadth (a narrower but still-real moat) and the realistic ceiling is mid-six-figures, not $1M. **The B2B school lane and a possible "vibemix-verified competency" certification are the optionality that bends the $1M case from consumer-only — but only if the consumer core is alive first.**

**Honest envelope:** this is a freemium content-loop with low ARPU and real churn, not a B2B SaaS rocket. The reliable, defensible outcome is **mid-six-figure ARR**; $1M is achievable but contingent on the flywheel compounding (unproven) and the streamer Act-2 SKU (€14.99, the one lever that escapes the €4.99 ceiling) landing later.

---

## 6. THE SINGLE BIGGEST RISK + THE CHEAP DE-RISK

**The risk:** **the coaching surface is too thin and too techno-only to be worth €4.99 to the buyer who actually exists.** Today the coach credits exactly two skills live (`harmonic_mixing` + `eq_mixing`/`deck_control`), beatmatching is permanently capped, and the genre detectors abstain on house/DnB/disco — *most of the paying market*. The anti-slop gate that is the moat becomes the liability: it correctly *refuses* to coach what it can't detect, which on the wrong genre means it says almost nothing. The product can be honest into uselessness for the buyer it's pitched to. Every other risk (packaging, mute voice) is pure execution with a known fix; this one is "is the product actually good enough for the market," and it is the one that doesn't have a guaranteed answer.

**The cheap de-risk (do this BEFORE Phase 2 spend):** a **20-DJ structured willingness-to-pay + share-rate test on Francesco's network**, costing ~zero. After Phase 0 (a build that speaks) + W1 (spoken recommendation) + B5 (the share-card), hand it to 20 DJs across techno AND house. Measure three numbers: (1) does ≥1 in 3 say "this actually made me better / I'd pay €4.99"; (2) what is the raw share-rate of the Receipt card (does the demographic actually post self-critique — the loop dies at step one if they won't); (3) on house sets, how often does the coach abstain into silence. If (1) clears on techno but house abstains hard, you've *proven* the genre-detector lane is the gate and you build it with conviction instead of hope. If the share-rate is near-zero, you've killed the viral graft for ~€0 before building the full loop. This test answers the one question the whole money model rests on — *is the grounded coach good enough that people pay and share* — for the price of a weekend and a network Francesco already owns. Run it the day a fresh machine speaks; let it gate every euro of Phase 2.
