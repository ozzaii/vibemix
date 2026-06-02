# MASTER — WHERE WE WIN (2026-06-01)

**The one doc Kaan reads to know where we win and what to do Monday.** Read-only synthesis of five section docs (`CRITIQUE-LOST-AND-MISSING`, `LICENSE-STRATEGY-APACHE-VS-GPL`, `WIRING-GAP-MAP-CODEGRAPH`, `POST-CODEX-FUTURE-AND-PACKET-BACKLOG`, `THE-WINNING-MOVE`). Every load-bearing claim re-verified by me at HEAD `1fbeaffb` (grep + codegraph evidence inline). The packets churned across `ed081570`→`970e165b`→`b98dd885`→`6150c80d`→`1fbeaffb`; I re-pinned the contested facts so this doc doesn't inherit a stale read.

---

## (1) THE THESIS — in 3 sentences

vibemix is **a genuinely rich product strangled by last-mile wiring, not a thin one** — the intelligence is clean-room-built, broadly tested, and honest, but the live voice is disconnected from most of it. The proof: the EQ-move physics keystone that every prior map called "the missing dependency" is now **built and wired** (`state/deck_context.py:16` imports `eq_move_model`, called at `:1873`, double-gated in `apply_live_claim_guard`), yet two of the highest-value engines — the 10-dimension `transition_scorer` and the `SuggestionService` recommendation engine — **run only in the silent pill and Viber, with zero callers in either coach loop** (verified: `grep` in `runtime/coach.py` + `state/coach.py` = NOT-FOUND; `score_transition` callers = `next_suggestion.py:657`, `toolset.py:313`, tests only). **Verdict: a rich engine behind bad wiring. The work left is wiring and reach, not invention — which is the best possible position to be in three weeks from a first dollar.**

---

## (2) WHAT WE LOST + buried treasure worth reviving (top 5)

Ranked by leverage ÷ revive-cost. "Revive" = reuse the orphaned engine, not rebuild it. All verified at HEAD.

1. **The 10-dim `transition_scorer` → live coach (L2 / W-TS).** Grades a blend on 10 signals (semantic/harmonic/bpm/energy-shape/role/phrase/cue-operability/taste/novelty/risk) — an order of magnitude richer than the shallow 2-signal Vibe Judge that's actually live. Orphaned to the pill + Viber only. **~0.5d call-site**, engine + inputs already assembled in `next_suggestion`. Lights `transitions` toward Mastered. *The single most under-valued thing in the tree.*

2. **The spoken next-track recommendation (M1).** `SuggestionService`/`next_suggestion` computes the "what's next" chip but the **voice never reads it** (absent from `coach.py`). The single most valuable spoken act a DJ friend performs — "9A→4A, phrases aligned, bring it in over 16 bars" — is computed and thrown away. **~0.5–1d pure wiring.** Fuse with L2 above into one cited line.

3. **The practice-deck loop → Mastered beatmatching (L1/B2).** Three test-enforced engines (`MiniDeck`, `grade_beatmatch`, the `BEATMATCH_GRADED` recognizer branch) sit dead because **no runtime emits `BEATMATCH_GRADED`** (verified: emitter NOT-FOUND; `practice_loop.py`/`practice_runtime.py` absent). Beatmatching — the #1 skill a learner pays to be graded on — is permanently capped at "Competent" (`_HONEST_UNCREDITABLE_V11=("beatmatching",)`). **~2–3d**, the highest-leverage NEW build. This is the credibility floor of the paid tier.

4. **Universal library readers (L4/B1a-d).** `library/sources/` = `base.py` + `rekordbox.py` ONLY, but the `LibrarySource` Protocol + `ingest_source` orchestrator are already wired — each new parser is a **collision-free island lighting the entire CLAP/Viber/pill/Earned stack for free**, and (per the license doc) all Apache-clean. Traktor `.nml` ~0.5d opens Francesco's base; Serato/Engine/master.db follow. *The only work that gets NEW users.*

5. **The cited debrief recap PNG (L5/B5).** The debrief already produces cited drills (`debrief/drills.py:51`, mandatory `citation`) and an mp3 TLDR — but **no canvas→PNG share-card producer exists**. This is "the moat made shareable": a static scorecard whose hero is the grounded coaching line. **~1–2d, offline, zero TTS cost, zero new dep** (`pillow`+`av` already shipped). The viral top-of-funnel.

*Honorable graveyard (don't forget):* the creative-forge ideas (Resident A&R, "Learning Your Tells" count-based personalization) are spec'd + scored but zero in `src/` — Resident A&R is the clearest Pro willingness-to-pay signal when you're ready for depth.

---

## (3) THE LICENSE CALL

**Recommendation (one line): STAY Apache-2.0 — do not flip to GPL; keep a dual-license / isolated-module split in your back pocket for one specific future module (RubberBand-grade keylock) and never for the core.**

The GPL romance solves a problem you don't have. The pitch is "flip, then vendor Mixxx's beat/key/sync DSP" — but those algorithms (onset detection, tempo tracker, key core, WSOLA keylock) **are not in the Mixxx source tree**; they live in external GPL libs (qm-dsp, RubberBand) the Mixxx checkout doesn't even contain. GPL's entire copyable yield is the grid-fitter + EQ + curve + planner ≈ **3–6 engineer-days, most already spent** (the EQ keystone landed this session, clean-room from the public-domain RBJ cookbook).

**The honest cost of flipping (why not to):** GPL's same-process combined-work test would **fence Bravoh out of its own warm-up project** — the single stated reason Apache was chosen (CLAUDE.md: "Permits Bravoh internal reuse"). vibemix is one Python process; `eq_move_model` is `import`ed in-interpreter, so there's no client/intelligence boundary to hide behind. Flipping re-papers 6 README mentions, every launch doc, and a **signed NDA** (`nda-meturavers.md:53`), and it's a **one-way door**. The proxy moat survives any license (network ≠ distribution; AGPL is NOT-FOUND in the tree), so GPL protects nothing you need.

**The one real compliance task, independent of the decision:** GPL `mutagen` already ships in the frozen DMG (`build/vibemix-core.macos/Analysis-00.toc`, 96 entries, pulled transitively through `library/export_serato.py`). Clean that up — exclude it from the bundle or write the ~1-afternoon clean-room ID3-GEOB tag writer — so the "Apache-licensed client" claim is actually true. Don't copyleft the whole stack to retroactively bless one optional cue-tag writer.

---

## (4) THE WIRING TRUTH — orphaned-gold (wire it) vs dead (cut it)

Structural health is **B+**: rich and honest, the disease is last-mile wiring. The pattern is diagnosable — **Codex landed the leaf graders/scorers but not the live producers that drive them.**

**ORPHANED-GOLD — wire it (top moves):**
- `score_transition` → coach-loop call-site on `TRACK_CHANGE`/`TRANSITION_OPPORTUNITY`. **~0.5d, pure + tested.** #1 cheapest high-leverage wire.
- `SuggestionService` → a `[track:]`-cited spoken line. **~0.5–1d.** Fuse with the above.
- `BEATMATCH_GRADED` emitter (build `learn/practice_loop.py`: MiniDeck→grade_beatmatch→`registry.write`+`Event`). **~2–3d, the one BUILD that cascades** — it alone lights `grade_beatmatch`, `BeatGrid`, `xfade`, `cue_placement_judge`, and `calculate_transition` at once.
- Traktor `.nml` parser into the dormant `library/sources/` seam. **~0.5d island.**
- `lufs.py` + `loop_geometry.py` + wire the existing-but-unwired `audio/xfade.py` into the live guard. **~½–1d each numpy**, widens "coach" past the single EQ axis.

**DEAD — cut or decide:**
- `[tend:<fact>]` grammar slot: offered to the model (`matrix.py:126`), in the grammar, but **no producer ever writes a `tend` atom** → every `[tend:]` is always stripped. Fail-safe but dishonest grammar. Cut the slot or feed it at profile-build. **5min–0.5d.**
- `grade_move` / `calculate_transition`: pill-only / demo-only. **Decide intent** — UI-only-by-design (fine) or add a coach consumer. 0.25d decision.
- `cue_placement_judge.grade_cue_placement`: both ends missing. **Build L1 first or it's a second orphan** — don't wire it standalone.
- `runtime/demo_mode.py`, `debrief/ear_test_capture.py`: already deleted ✓.

**The one stale-doc trap:** any plan still listing "build `eq_move_model`" as task #1 is chasing a ghost — it's BUILT+WIRED (`970e165b`). Re-baseline before routing.

---

## (5) THE WINNING MOVE — the money play + 90-day sequence

**The play: the Pro-Coach — "vibemix is the DJ coach that physically cannot lie to you."** It wins because **the moat and the product are the same object**: the double-gated citation spine surfaced as a skill-tree where "Mastered" unlocks only on a cited live demonstration (`runtime/coach.py` `_credit_live_skill_demo`). A fast-follower can't ship "you earn mastery on a real deck and we measured it" without first rebuilding the single-writer perception spine + CitationLinter underneath. It's not the highest-ceiling play (the streamer/OBS bet is, at €14.99) — it's the **highest expected-value** one: a defensible €4.99/€9.99 coach shippable in weeks, funding the bigger bets, whose own share-card doubles as the viral wedge.

**The graft (one product, four skins): coach makes you better (revenue) · cited share-card proves it publicly (top-funnel) · DJ-school report-card pays runway (margin lane, hard 90-day kill-trigger) · CLAP library-discovery box hooks the trial.** All four are the same grounded engine. Park the streamer play as Act 2 — it bets on charisma-under-starvation, the exact axis the engine is built to *avoid*.

**The 90-day sequence (grounded):**
- **Phase 0 — Unbreak the ship (Wk 1–3). Nothing counts until a stranger's machine speaks.** B-1 host+bundle MOSS (pin URL/SHA, first-run download) FIRST; X1 voice-picker bug fix; B-4 rebuild+sign DMG from clean HEAD (currently ~177 commits stale, born mute) AFTER B-1; B-3 one keyless proxy round-trip with a live Gemini key (Kaan/infra).
- **Phase 1 — Make the coach worth €4.99 + the share-card (Wk 3–7).** W1 spoken next-track + transition verdict (the demo that turns commentator into coach); B5 debrief Receipt PNG; B1a Traktor ingest + Crate discovery search box.
- **Phase 2 — Credibility floor + reach (Wk 7–12).** B2 practice-deck loop (uncaps Mastered beatmatching — non-optional credibility floor); **House + DnB genre detectors** (all 9 detectors are techno-shaped; without this a house DJ buys Pro and the coach narrates "unknown phase" → instant refund); B3 grounding siblings.

**Money model (decided pricing):** free funnel → €4.99 Pro → €9.99 Studio. Unit economics close **only because inference is on-device** (CLAP + MOSS = €0 marginal; sole cloud line = Gemini brain through the capped Bravoh proxy). Reliable outcome = **mid-six-figure ARR**; $1M is contingent on the taste flywheel actually compounding (unproven — CLAP text→audio is coarse) and the streamer SKU landing later.

**The single biggest risk:** the coaching surface is too thin and too techno-only to be worth €4.99 to the buyer who exists — the anti-slop gate that is the moat becomes a liability when it correctly refuses to coach a genre it can't detect, and says almost nothing. **The cheap de-risk:** a ~zero-cost **20-DJ willingness-to-pay + share-rate test on Francesco's network**, run the day a fresh machine speaks (after Phase 0 + W1 + B5), measuring (1) "would you pay €4.99," (2) raw share-rate of the Receipt card, (3) how often the coach abstains into silence on house. Let it gate every euro of Phase 2.

---

## (6) WHAT TO HAND CODEX TODAY

**Top 5 NEW packets to write (ranked, collision-free islands, fastest payback):**

1. **W1 — Spoken next-track + transition verdict (★★★★★).** Voice reads `SuggestionService` + the orphaned 10-dim `transition_scorer` into one `[track:]`/risk-cited line. The sharpest single move: the live voice is disconnected from BOTH the recommendation AND the best transition engine, both already running silently. WIRE, SRC→LIVE, gate `vibemix-grounding-review`. ~0.5–1d.
2. **B1a — Traktor `.nml` ingest (★★★★★ reach).** The cheapest Universal-Ingest packet, opens Francesco's base, and proves the dormant `sources/` seam (unlocking Serato/Engine/master.db as a parallel ~5-day milestone). The only build that *gets new users*. Apache-clean, own island. ~0.5d.
3. **X1 — Voice-picker bug fix (★★★★).** A live ship-blocker the source packets missed: default `"kore"` doesn't exist in MOSS (`config_store.py:169`), so all 8 picker options fall through `local_tts.py:276`'s `voices[0]` to **one wrong voice** — first thing a DJ does, does nothing. Repopulate `VOICE_OPTIONS` from MOSS `builtin_voices` + re-default. A real fix, not copy. <1d.
4. **B2 — Practice-deck loop → `BEATMATCH_GRADED` (★★★★).** Lights the whole own-player cluster and uncaps Mastered beatmatching — the headline competency the queue deliberately leaves greyed. Consumer waits at `skill_recognizer.py:154`; emitter NOT-FOUND. 2–3d.
5. **W2 — Prep→live set awareness (★★★★).** Thread the Viber-built set JSON into `MusicState` so coach can cite "you're ahead of your curve." `built_set`/`set_plan` absent from runtime/state/agent — never attempted, kills prep/live amnesia. ~1d.

**Existing queue items that matter most (route alongside the new packets):** B-1 (MOSS host/bundle — the #1 kill-shot, nothing else matters if it's silent); B-4 (rebuild DMG from clean HEAD, *after* B-1); W-TS (wire `transition_scorer` — folds into W1); S8 (surface the auto-cue export as a first-class Crate action — the named MOAT, currently undiscoverable). De-prioritize: B6 off-the-wire deck identity (hardware-gated, deferred), W5 `grade_move` decision (low).

**Sequencing:** W1 + B1a + X1 first (collide with nothing), then the Universal-Ingest body as a parallel milestone, then B2/W2 as the depth lane.

---

## (7) THE ONE NEXT MOVE

**Host + bundle MOSS-TTS-Nano and rebuild the DMG from clean HEAD (B-1 → B-4), in that order.**

Because **nothing else matters if the product is silent.** Today every machine but Kaan's boots mute — MOSS weights are neither in `vibemix-core.macos.spec` datas nor hostable by default (`moss_model_installable()` returns True only if an env URL is set; no URL/SHA pinned), and the only shippable DMG is ~177 commits stale and born mute. Every euro of the money model, the 20-DJ de-risk test, the share-card loop, and W1's "demo that turns commentator into coach" all sit behind this one ops gate. It is pure execution with a known fix, not invention. Fix it first; everything in this doc unlocks behind it.

---

*Source ledger (all under `.planning/packets/2026-06-01/`):* `CRITIQUE-LOST-AND-MISSING.md`, `LICENSE-STRATEGY-APACHE-VS-GPL.md`, `WIRING-GAP-MAP-CODEGRAPH.md`, `POST-CODEX-FUTURE-AND-PACKET-BACKLOG.md`, `THE-WINNING-MOVE.md`. *Re-verified at HEAD `1fbeaffb` by the synthesizer:* `transition_scorer`/`next_suggestion` zero coach callers; `eq_move_model` wired at `deck_context.py:16/1873`; `BEATMATCH_GRADED` no emitter + `practice_loop.py` absent; `library/sources/` = base+rekordbox; `lufs.py`/`loop_geometry.py` absent, `xfade.py` present-but-unwired.*
