# Learn Breakthrough — WRECK ROOM (v12 design)

**Date:** 2026-06-12 · **Author:** Fable session (ultracode), Kaan's challenge: "fix the boringness… make it a fun free selling breakthrough product"
**Status:** SLICE BUILT + AUDITED + LIVE-VERIFIED (2026-06-12). Design: 8 Fable readers + 3 concepts (game-designer / music-first / coach-personality) + 3 adversarial judges (founder / engineering / beginner lenses), wf_33ebcc52-783. Winner: **Wreck Room** (2 of 3 judges; founder + beginner lens both 33/40, kaan_fit 9/10). Open Decks grafts absorbed; Mixtape demoted to the own-track dealer + local recorder follow-ups.
**QA record:** live-verifier PROVEN twice on dev-source (full FSM cycle on the real ws bus, all barks verbatim authored fixtures, voice rendered, clean stop; second run = 4 unattended miss cycles, 13 wreck barks, ZERO generic `learn.grade` frames). Slop-audit round 1 HOLD → fixed: (H1) one-shot `_wreck_swallow_next_grade_text` — every wreck bark claims the next generic grade verdict-edge, double-voice dead; (H2) `_BARKS_HELD_CAP` — no escalation promise at difficulty 5; no-deck honest bark (`wreck_round.no_deck`) closes the silent-dead-button edge. Slop-audit round 2 found the real seam: `current_lesson_id` never clears after a completed lesson (the relaunch flow reads it), which permanently killed the booth + ALL free practice post-lesson → fixed with `_lesson_engaged()` (FSM-state gate, 5 call sites) + revival test. Booth UI: refusal barks (busy/no_deck markers) cancel the audio watchdog so Sven's honest line is never overruled by a false "check your sound output" diagnosis. Gates at close: pytest learn+ui_bus 1201 green (26 wreck tests), vitest 1650 green, build green.
**Supersedes:** the 36-lesson syllabus AS THE FRONT DOOR (lessons survive demoted, see below). The `mountLearnTease` plate dies.

---

## The one-line thesis

Stop teaching DJing. Start handing people a live mix that is about to fall apart — with Sven in their ear — and let the music itself teach them. **The game is: Sven wrecks the mix, you save it.**

The engine for this is ALREADY BUILT and buried as lesson L3.05 + the free-practice sandbox:
- `MiniDeck` (audio/miniplayer.py) — real two-deck physics: Mixxx-derived rate scaling, EQ, filter, equal-power crossfader, jog.
- `BeatmatchJudge` (learn/beatmatch_judge.py) — measured verdicts `locked/drifting/trainwreck/tempo_off` + 0-1 score at 6.7Hz (live_grade_loop, 150ms).
- Save machinery (learn/runtime.py:3186-3289) — countdown window, difficulty 1-5, streak, save-landed edge detection. **Lesson-lane only today; the slice generalizes it to the sandbox.**
- `save_mode_loader.py` — loads TWO REAL tracks from the user's library (ANLZ grids, harmonic-compatible via next_suggestion) into the decks. Bundled 128 BPM loops as the fresh-install fallback.
- UI: `LiveGradeMeter` (needle + save HUD + countdown + streak + lock pulse), `WaveformDisplay` (gallop beat-train that physically drifts apart with phase error and snaps on lock), `drag-control` (on-screen tempo fader / jog / xfader — no hardware needed).

Nothing above is speculative — verified first-hand at HEAD this session, file:line in body.

## Why the old Learn died (so we don't rebuild it)

Kaan, verbatim (2026-06-08): *"It's boring, it's not interactive, it's 36 courses of touch your set, I hate it so much that's why we parked it."*
The lesson FSM teaches by **instruction-then-drill** (read → dwell 45s → touch the highlighted control). The breakthrough inverts it: **play-then-meaning** — you act in the first 10 seconds, the concept gets named WHILE your hands are on it (Sven's line when you overshoot the fader teaches "tempo first, then phase" better than any text plate).

## The product: The Booth

Open Learn (Cmd+3) → you are IN a running booth. No syllabus. No tease. No reading.

**Core loop (one round ≈ 25-60s) — groove-first, judge-refined:**
1. ONE button: "drop the needle". No autoplay (a `can_play()` refusal over a live set surfaces as a designed honest state, never a dead button).
2. GROOVE (8-15s): both decks LOCKED and audible — the ear learns what right sounds like before it is taken away. Bundled loops; your own tracks later via the dealer.
3. THE BREAK: Sven shoves deck B — tempo shove at low difficulty (audible flam even on laptop speakers), sneakier phase-only shoves higher up (the existing `_arm_recovery_drill` math, sandbox lane). He owns it in voice: a callout, not an error toast.
4. THE HUNT: save window counts down (existing floor seconds, shrinking per level). You drag the on-screen tempo fader / jog (or real controller — same ack path) until the kicks fuse.
5. HOLD (16 beats): a grazed lock is not a save — sustained lock read from the grade STREAM before it counts. Then the WebAudio thunk fires INSTANTLY on the edge; Sven's bark trails (pre-synth PCM bark cache is the ship gate for <500ms barks; the thunk carries the slice).
6. MISS THEATER: window expires → Sven audibly pulls deck B's fader himself and owns it ("I pulled it. that was a trainwreck."). Failure is loud and funny, never punitive, never a fail card.
7. LEDGER: every round persists measured facts (time_to_lock, held, landed, difficulty) beside LearnProgress. Sven's verdicts cite them across days: "yesterday the pocket took you 1:40. today 0:41." This is the come-back-tomorrow engine — pure receipt, zero gamification.
8. Music never stops. Between rounds the booth is a free sandbox (EQ, filter, xfader, jog all live today via `handle_practice_audio_ack`).

**Why round 2 happens voluntarily (no XP, no confetti — anti-bloat law):**
- The failure is AUDIBLE (a flamming kick is viscerally wrong) and the fix is AUDIBLE (fused kicks are viscerally right). The reward signal is the music, not a badge.
- Difficulty ladder + streak (bounded engine concepts that already exist in `BeatmatchPracticeResult`) give the "one more round" pull.
- Sven is a personality, not a narrator: measured, honest, occasionally impressed. The free Booth IS the demo of the paid live co-host's voice.
- Your own music makes it identity-relevant (the Rocksmith insight: real songs day one).

**The 36 lessons demote to "moves".** The Booth is the front door; when the judge sees the same failure shape repeatedly (e.g. tempo never matched before phase attempts), Sven offers the matching drill ("tempo first. ninety seconds, want it?") which runs the existing lesson runtime. Lessons become contextual power-ups, not a wall. (Slice ships the Booth only; the drill-offer hook is a follow-up unit.)

## Vertical slice (this session) — ZERO new IPC types

**Python (new, small):**
- `learn/wreck_round.py` — `WreckRound` director: round FSM (idle→groove→hunt→hold→landed/missed→groove), difficulty 1-5, clean-save count, ledger append. Pure logic, DI, unit-tested. NEVER writes MusicState/LearnState; sandbox lane = NO evidence writes, NO credit (display only — judge kill: client/sandbox credit is the release-blocking sin).
- `BeatmatchPracticeDriver`: `wreck(kind, level)` (sandbox shove — `_arm_recovery_drill` math, sets `_sandbox_active`, never lesson `_armed`), `lock_b()` (groove), `yank_b()` (miss theater).
- Runtime hooks: sandbox tick consults the director → live_grade carries save fields outside lessons (the wire + `LiveGradeMeter` already speak them); director barks ride the existing `_emit_tutor_speak` channel — authored constants, measured slots, `citations=()` (Invariant #2 untouched).
- Round start: rides the EXISTING `ipc.learn.ack` with `control_id:"wreck_round"` (LearnAck schema takes any control_id; zero schema/codegen churn). A `handle_wreck_round_ack` joins the ack chain after `handle_practice_audio_ack` (which already auto-starts the sandbox player on the same ack).

**TS (new surface):**
- `learn/booth/wreck-booth.ts` + css — full-bleed tozpembe booth: WaveformDisplay top, LiveGradeMeter center, on-screen deck-B tempo fader + jog (drag-control), Sven line strip, ONE primary action ("drop the needle"). One-Rose: the save countdown is the single breath while a window is open; needle/gallop are data-driven instruments, not breathers. Copy = Sven first person, no em dashes.
- `shell/app.ts:63-65` mounts the booth instead of the tease (note: render-loop.ts learn call-site + the parked-Learn specs updated deliberately).
- Reuses LearnWsClient (Tauri bridge = shared Rust event bridge; one-socket safe) + `emitIpc`-with-ws-fallback send pattern from learn-window.

**Judge kills honored in the slice:**
- NO number chips for streak/difficulty (the banned-streak adjacency): the existing live-meter `x${streak}`/`L${level}` chips re-skinned as plain words ("third clean save", "window 10s now").
- No upsell PREVIEW in any bark; the paid bridge lives in surface copy only, if anywhere.
- No autoplay; honest "deck's busy with your set" state on `can_play()` refusal.
- Laptop-speaker reality: level-1 shove is a tempo shove (audible gallop), the meter assist is always visible, headphone nudge in surface copy.
- All barks authored fixtures/constants (no LLM, AST-gate compliant), anti-repeat variant picker, no "again?" nag copy — round two is pulled by the sound and the shrinking window.

**Honesty boundaries (unchanged invariants):**
- Sandbox/wreck lane stays feedback-only — credit stays in the lesson lane until a deliberate EARNED unit.
- `TwoDeckPlayer.can_play()` still refuses over a live set (Invariant #3).
- Idle ≠ fault: no library = "practice loops" labeling (already in WaveformDisplay), never an error paint.

## Out of scope for the slice (named so they don't creep)
- **Own-track dealer** (Mixtape graft, post-difficulty-3 offer): 2-3 candidate cards via `next_suggestion` + honest why-phrases, `seed_track_id` → `load_save_mode_sources`; PyAV decode goes off-thread behind a designed loading state; "key unknown, trust your ear" when camelot is None. Rekordbox-gridded libraries only — estimated grids are KILLED for v1 (grading against a guessed grid fabricates verdicts).
- ~~**Pre-synth bark PCM cache**~~ **SHIPPED 2026-06-12** (the ship gate): `learn/bark_cache.py` (pinned warm bank + byte-capped LRU for opportunistic stores) wired into the tutor voice sink. First ENGAGED-round bark triggers a one-time background warm of the fixed bank (refusal barks `busy`/`no_deck` deliberately do NOT warm — slop-audit caught that busy fires mid-live-set on the shared voice engine); landed lines stay live-synth (measured `{time_to_lock}` slots — never pre-bake an unmeasured number). Live-proven twice: warm 25 texts errors=0 in ~63s, cache-hit barks speak→playback in ~1ms (vs the <500ms gate). Same wave fixed the live-found stop→restart seam: booth controls (`wreck_round`/`wreck_stop`) are no longer free-practice gestures in `handle_practice_audio_ack`, so the stale-shove "tempo is far out" grade line can't voice 5ms before groove_open (3/3 boundaries clean, `learn.grade` count 0 in session 20260612-220250).
- **Local round recorder** ("hear your save", last wreck→save clip; strictly local playback, never an export/share CTA — copyrighted slabs).
- The drill-offer hook (failure-shape → lesson), EARNED credit from saves, Mastered hot-cue writer, EQ-swap/phrase-drop round types, licensed starter crate (content task, not code), blend/EQ judge (no EQ state in DeckState).

## Panel verdict record

Scores (fun/feasible/kaan_fit/wedge): founder judge — Wreck Room 33, Open Decks 33, Mixtape 28 (best: Wreck Room). Engineering judge — Open Decks 34, Wreck Room 31, Mixtape 29 (best: Open Decks). Beginner judge — Wreck Room 33, Open Decks 32.5, Mixtape 29 (best: Wreck Room; "Open Decks is Wreck Room with the beats reordered and a weaker first two minutes").
Full transcripts: workflow `wf_33ebcc52-783` under the session's subagents dir; raw result in tasks/wve3a0l3v.output.
