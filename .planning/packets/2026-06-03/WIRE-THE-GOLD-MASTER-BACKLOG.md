# WIRE-THE-GOLD — Master Backlog (single source of truth for Codex)

> Read-only staff-architect synthesis. HEAD `f3fc4964`. Repo: `/Users/ozai/projects/dj-set-ai`.
> Every wiring claim below is codegraph/file:line-verified. Where a source roadmap was STALE, the correction is inline and marked.
> Cardinal Law binds every item: single-writer `MusicState` (Inv #1) · citation grounding / un-cited strips to ack-bank (Inv #2) · trust-the-audio (Inv #3) · one socket (Inv #4) · idle≠fault (Inv #5) · cross-island import law · `model_router` no-literal · `messages.schema.json` edit ⇒ `npm run codegen:ipc` · surgical staging on the shared tree.

---

## 1. THE ONE-SCREEN THESIS

The product is **built, tested, on the wire, and dark.** Across LEARN, ENGINES, DSP, and the LIVE co-host, the same pattern repeats: the intelligence Kaan already paid to build and test is sitting one wire away from the user — discarded at the call site, fed silence instead of audio, graded on a degenerate signal, orphaned from the live brain, or rendered nowhere. The teaching loop closes 1.5 of 5 stages; the next-track pill computes deterministic grounded "why" reasons and shows none of them; the beatmatch judge — the v11.0 moat — grades every phase as a perfect lock because the practice deck cursor never moves; the auto-cue moat ships in weak-heuristic mode because the real CUE-DETR model isn't hosted. **The 10x is WIRE-not-BUILD.** Almost nothing here is a new engine; it is lighting gold that already exists, in dependency order, while never touching the deliberate silence that is the anti-slop moat. One genuine BUILD remains (keyless gig-prep `auto_crate.py`); one genuine external dependency remains (a hosted CUE-DETR URL — Bravoh release infra, not engineering).

---

## 2. QUICK-WIN LANE — codegraph-CONFIRMED, <1 day, no/low risk

> Ordered cheapest-first. Each carries its file:line and its packet (or "needs 1-pager"). Items the Verify phase REFUTED are listed at the bottom of this section with the correction, so nobody re-litigates them.

| # | Quick win | dark-signal → wire (file:line) | packet | risk |
|---|-----------|-------------------------------|--------|------|
| **Q1** | **Render the next-song `reasons[]` receipt in the pill** | Producer `_reasons()` `intel/transition_scorer.py:707` (deterministic threshold-gated English) → assigned `transition_scorer.py:422` → serialized `library/next_suggestion.py:813` → typed `tauri/ui/src/pill/next-suggestion.ts:122` → **rendered NOWHERE** (`renderNextSuggestion` reads `risk_flags` at :847 but never `t.reasons`). Sibling `risk_flags` proves the same JSON shape reaches the frontend and renders. Append a `textContent`-only chip list near the existing `why`/risk block (~:1139). **No schema edit, no codegen.** | `CODEX_READY-ENGINES-10X-TOP.md` (ready as-is) | very low (frontend-only, field already on wire) |
| **Q2** | **Render the CUE-confidence receipt** (same pill card as Q1) | `cue_confidence`/`cue_source`/top-dims serialized `next_suggestion.py:800-807`, type-only `next-suggestion.ts:108-109`, dark in render. Render a curated phrase, NOT a 10-number dump. | sibling of Q1 in `CODEX_READY-ENGINES-10X-TOP.md` (needs the cue-card paragraph written) | very low |
| **Q3** | **Voice the discarded beatmatch grade** (closes teaching Stage 5 today) | The tick return is discarded as a bare statement at `learn/runtime.py:2088` (and `:924`). Add `_emit_live_grade(result)` → `LearnTutorSpeak`. LOCKED carries `[ev:BEATMATCH_GRADED@t]` (producer ALREADY writes it — `learn/practice_loop.py:81`, fired via `runtime.py:1468` `_grade_beatmatch_practice_tick`, pinned by `tests/repo/test_live_reality_pins.py`). Honest-null rule: drift/trainwreck/tempo_off emit with `citations=()`; abstain emits nothing. | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 1 | low — **MANDATORY `vibemix-grounding-review` on the emit**; pure-additive inside `learn/runtime.py` (impact depth-2 = 5 symbols, all in-file). Do NOT touch `coach.py` (parallel session). |
| **Q4** | **Honest-completion flag (close the 45s skip-credit leak)** | A 45s-timer-then-skip records `completed=True` at `WEIGHT_FIRST_TRY=1.0`, indistinguishable from a flawless demo. Persist a `demonstrated` flag (True only on `action_match`) `learn/progress.py:245-254`; `skill_tree.py:_weight_for` (`:254-274`) returns `WEIGHT_FLOOR` for skip-rows. (Skip itself stays — anti-frustration escape; only the full-weight credit is the leak. Recital honest-score gate at `skill_tree.py:319` already ANDs in, so skip alone can't reach Competent.) | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 6 / LEARN L7 | low (under-guarded moat, pure logic) |
| **Q5** | **Fix the cue-judge faked-perfect input** (before any cue voicing) | `learn/cue_placement_practice_driver.py:57` feeds the judge `=target_frame` (a faked-perfect press) instead of the real press frame. Voicing graded theater is worse than silence — fix this BEFORE Q3 is templated to cue. | LEARN PR2 §7 / L6 | low (bug) |
| **Q6** | **Fix the octave-fold phase bug** (2:1 / 1:2 beatmatch falsely reads "trainwreck") | `learn/beatmatch_judge.py:114` `_phase_error` compares `grid_b.beat_distance` vs `grid_a.beat_distance` **without** folding to a common beat. The tempo fold (`_octave_fold_multiplier`, `:47-60`) is itself correct (verified: ratio 2.0→1.0), but the phase compare is one layer down and un-folded — a true 70↔140 lock at any non-anchor frame grades `phase_error=-0.5`, `verdict="trainwreck"`, `score=0.0`. The recognizer credits beatmatch only on LOCKED (`skill_recognizer.py:160`), so half/double matches earn **zero** credit. ~12 lines: fold B's beat into A's frame before the phase diff. Thresholds are correct — do NOT loosen them. **Land WITH Q7/B1 — masked until the cursor advances.** | MINE-sync-phase §3 (clean-room) | low (math bug + 1 non-anchor test) — **CONFIRMED with diagnosis correction: the bug is the un-folded phase compare, not the multiplier.** |
| **Q7** | **Visible learn empty-state** (silent bail reads as "broken") | `runtime.py:1009-1017,1040-1045` bails to stderr only on no-controller/invalid-lesson. Emit one on-screen reason ("plug in your controller to start"). | LEARN L9 | low (additive) |
| **Q8** | **In-app voice-muted / model-missing banner** | Missing/corrupt MOSS = total silence + stderr only, no in-GUI cue. Broadcast a `voice_muted` / `model_setup_needed` ws event from `__main__.py:212-228` (`_build_tts_chain_or_mute`) → render the existing `deriveModelSetupView`-style banner (`library/index.ts:830-877`) in live + learn windows. Keeps MOSS-only moat (no cloud fallback). | LEARN V3/V6 | low (ends silent-failure footgun) |

**REFUTED quick-wins (do NOT build — the Verify phase killed these):**
- ~~"`MiniDeck.render_block` has ZERO callers"~~ — **PARTIAL/REFUTED.** It has 4 callers (`scripts/miniplayer_smoke.py:95`, `scripts/automix_demo_smoke.py:260`, 2 tests). The TRUE statement is "**zero callers from the live learn driver**" — `beatmatch_practice_driver.py` feeds `np.zeros` (`:65-66`) and only mutates `rate_a/rate_b`, never calls `render_block`, so the cursor stays at 0.0 → the phase grade is degenerate. The headline ("phase grade degenerate today") is CONFIRMED; this is a BUILD-lane structural fix (B1), not a same-day quick-win.
- ~~"`score_transition_slate` is orphaned, wire it into the live coach"~~ — **PARTIAL.** Its *output* already reaches the live mouth via the pill suggestion on `TRACK_CHANGE`/`TRANSITION_OPPORTUNITY` (`coach.py:741` `build_transition_verdict_voice_line` ← `suggestion_service.current_for_state`). The code DELIBERATELY avoids a second live scorer invocation (`transition_verdict_voice.py:17` docstring: "consume that bounded payload, not re-derive a second verdict"). The real gap is the *render-side receipt* (Q1/Q2) + the gated voice upgrade (B7), NOT a second scorer call. Do not bolt the scorer onto the coach.
- ~~"Taste has zero prod callers / the pill taste hook is unfed"~~ — **REFUTED for the pill.** `_load_live_taste_scores()` (`__main__.py:1146`, consent-gated, called from `main:870`) → `suggestion_service.update_taste_scores()` (`:1142`) → `next_suggestion(taste_scores=...)` (`suggestion.py:976/1192/1228/1276`) → `TransitionScoringInput.taste_scores`. Taste is LIVE in the pill engine today. Unfed ONLY on the Viber/`toolset` set-builder path. Re-scoped to B11 (lowest priority).
- ~~"MOSS ships mute day-one"~~ — **OVER-STATED.** `VIBEMIX_LOCAL_TTS` self-enables via `setdefault` (`__main__.py:837`, survives launchd strip); the signed DMG bundles the model; `--require-moss-source` blocks a mute build. Residual risk is narrow (clean CI / build bypass / model-less clone) = the V2 owner gate, not a default-state bug.

---

## 3. BUILD LANE — bigger grounded wins, in dependency order

> Each: **dark-signal → wire → packet → depends-on.** Spans learn + engines + DSP. By-EAR (drive-vibemix) is the ship gate for the audio/voice items, not green tests — the discarded-grade bug passed every test while being totally invisible to the user.

### The fused audible BEATMATCH loop (LEARN-10X P1 — the flagship; closes 5/5 stages on one skill)

**B1 — Audible practice decks (the structural unblock; un-degenerates the phase grade).**
*Dark-signal:* `render_block` (`audio/miniplayer.py:130`) — the ONLY method that advances `_frame_a/_frame_b` (`:132-133`, init 0.0 at `:127-128`) — is never called by the live learn driver, which feeds `np.zeros` (`beatmatch_practice_driver.py:65-66`) and routes to no stream. Cursors frozen → `beatmatch_judge.py` phase axis is identically locked.
*Wire:* NEW `learn/two_deck_player.py` cloning `ExemplarPlayer`'s headphone `sd.OutputStream` + lock + mic-gate-bypass (`audio_cue.py:104-263`); callback body `outdata[:] = mini_deck.render_block(frames)`; replace the `np.zeros` slabs with two decoded intro/build loops; `__main__` hands the same `MiniDeck` to the player. This makes decks audible AND advances cursors → **the phase grade becomes real for the first time** (hard prereq for honestly voicing Q3 and for Q6 to be observable).
*Packet:* `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 2+3 + MINE-twodeck-mix (adopt per-block anti-zipper gain ramp, clamp-once-at-device-boundary).
*Depends-on:* none to build; B5 (WAV bundling) + loop-licensing for the packaged app. Land Q6 with this.

**B2 — Route the tutor through MOSS (kill the silent subtitle) + dead voice-picker fix.**
*Dark-signal:* `LearnTutorSpeak`/`tts_marker` is text-only; `MossEngine.synthesize` (`local_tts.py:293`) is never reached from the lesson; `config.voice` is never read (`local_tts.py:454-460`).
*Wire:* inject a `tutor_speak_audio` callback into `LessonRuntime` (default `None` = today's silence, back-compat), supplied by `__main__` via `MossEngine.synthesize(text, on_pcm)` → headphone stream, gated on `local_tts_enabled()`. Read `config.voice` at boot → `MossLocalTTS(voice=...)` so tutor + live co-host are one Sven.
*Packet:* `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 4 + LEARN V4. *Depends-on:* Q3.

**B3 — Grade-carrying IPC + lock-meter HUD (first canvas in the learn UI).**
*Dark-signal:* the voiced grade (Q3) has no visual; the learn UI shows no needle.
*Wire:* NEW `ipc.learn.live_grade {verdict, phase_error_beats, score, citation}` → **schema edit + `npm run codegen:ipc`** + `LearnLiveGrade` dataclass + the `LEARN_INBOUND_TYPES` allowlist entry (`ws-client.ts:71-81`). **Relay trap (verified dead-feature risk): a new inbound type needs THREE edits — schema, dataclass, allowlist — miss the allowlist and the meter ships dead with a green schema. Run `ipc-wiring-checker`.** NEW `live-meter.ts` canvas via the proven `drainFrame` rAF coalesce; needle centers as `phase_error_beats → 0`. Repaint optimistically.
*Packet:* `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 5 / LEARN PR2 Seam B. *Depends-on:* Q3, B1.

> **By-EAR ship gate for Q3/B1/B2/B3/Q6:** in drive-vibemix, hear the two kicks drift then lock, hear Sven say it, see the needle center, confirm `[ev:BEATMATCH_GRADED@t]` resolves on the ws bus. **Kill criterion:** a beginner on L2.01 hears no kicks, or locks a beat and Sven says nothing → loop not closed.

### Force-multiplier model + engine reach

**B4 — Ship the real CUE-DETR ONNX model (host + first-run auto-download).** *(ENGINES R3 / QW-D CONFIRMED)*
*Dark-signal:* `_cue_download_config()` (`library/model_assets.py:708-711`) returns `None` when `VIBEMIX_CUE_ONNX_URL` is unset → `install_cue_model()` (`:456-461`) never downloads; the `"required"` first-run target (`install_models():755-769`) installs only CLAP+MOSS; `cue_detr.py:66-73` raises `CueProducerUnavailable` → falls to the heuristic that **failed on hardtechno**.
*Wire:* set the three `VIBEMIX_CUE_ONNX_*` pins (URL/SHA-256/size) to a hosted artifact mirroring `install_clap_model` (`:346` — download/SHA/atomic-rename/progress-UI/`library models --install cue` CLI already exist); add CUE to the `"required"` branch. `detect_cues_auto` (`cue_engine.py:164`) is the single seam for ingest + `library cue` + every cue-anchored embedding + the pill payload → **upgrading the producer upgrades all of them with zero call-site edits.** This is what makes Q1/Q2's receipts populate for most users.
*Packet:* `CODEX_READY-ENGINES-10X-TOP.md` (R3 section — needs the host/accuracy paragraph). *Depends-on:* OWNER gate (hosting + accuracy bar). **Unblocks B5/B6/B7-voice/B8.**

**B5 — Keyless gig-prep `auto_crate.py` (the one genuine BUILD).** *(ENGINES R4)*
*Dark-signal:* the structured "build from N refs on a curve" flow today drags the three hardest gates (Codex install + login + `VIBEMIX_CODEX_ALLOW_SHELL`).
*Wire:* NEW `library/auto_crate.py` builds ONE `LibraryToolset` (no Codex dep — `toolset.py:118`) and calls `discover_pool`→`sequence_set`→`transition_slate`→`export_set` directly, inheriting the seen-set anti-hallucination spine + gate-#2 re-validation free. Removes the LLM from the structured task entirely (no brain swap, **keeps the Viber=Codex lock**). Inputs = ref track_ids and/or curve+slot-count (NOT a fuzzy NL brief — that stays Codex's job).
*Packet:* NEEDS-WRITING (`ENGINES-10X-ROADMAP.md` R4 is the spec source). *Depends-on:* soft-dep B4 (so auto-built cues are real); OWNER framing (default front door vs Codex power path).

**B6 — Multi-ecosystem export fan-out (`--export all`).** *(ENGINES R6)*
*Dark-signal:* `export_set` is Rekordbox-only (`toolset.py:890`; CLI `choices=("rekordbox",)` `__main__.py:3274`) while the universal Serato-Markers2 carriers (`export_cued_folder`/`tag_folder_serato` → Mixxx + Rekordbox + M3U8) exist, are tested, and are wired ONLY into `_cmd_library_cue` (`__main__.py:6968`).
*Wire:* additive pure file I/O after gate-#2 re-validation; folds MINE-cue (round-robin hot-cue color, point-vs-range, sample-exact −60 dB trim).
*Packet:* NEEDS-WRITING + MINE-cue. *Depends-on:* pairs with B5; cue quality gated on B4.

### Voice changes (highest-risk surface — every item hard-gated through `vibemix-grounding-review`)

**B7 — Voice the section pairing + dominant grounded dimension.** *(ENGINES R7 — the principled answer to the narrator→coach gap)*
*Dark-signal:* `rolePairLabel` is rendered as a glyph (`next-suggestion.ts:591`) but never spoken; the dominant `reasons[]` dimension is never named in voice.
*Wire:* two one-noun upgrades routing through the SAME already-firing, already-citing `build_next_suggestion_voice_line` (`suggestion_voice.py:24`, sole caller `coach_loop`). Does NOT raise speak frequency (rides existing gated events) — compatible with the rare+earned moat. Note: this is the *next-track* voice, not an in-set move grader (the code deliberately avoids a second live verdict).
*Packet:* NEEDS-WRITING. *Depends-on:* Q1 (prove the reason copy is good before it's spoken); **MANDATORY grounding-review — if any clause is un-citable, cut the voice half, keep only the Q1 render.**

**B8 — Live cue VOICE via the drop-call flag.** *(ENGINES R8 — boldest + most slop-dangerous; build LAST)*
*Dark-signal:* the real source-agnostic live-voice channel is the drop-call (`predict_drop_in_sec`, `drop_predict.py:25` — no source gate, runs every tick outside the lesson gate, floor 0.5, in EvidenceRegistry), held back only by `VIBEMIX_DROP_CALL` (`event_detector.py:67-71`, dormant by an explicit anti-slop comment). NOT the count-in line (`refresh.py:783` — wrapped in `if state.session_active:` = Course-3-only, never reaches a plain live set; KILLED as a live lever).
*Wire:* flip the flag behind a real-model accuracy bar.
*Packet:* NEEDS-WRITING. *Depends-on:* **hard-gated on B4** (heuristic mis-detects drops on hardtechno → unsafe until the real model ships) + accuracy bar against a real drop + grounding-review. OWNER ship gate.

### Teaching depth + DSP (depend on the fused loop)

**B9 — Wire the ZPD drill router into lessons.** *(LEARN-10X P3 / QW-E CONFIRMED)*
*Dark-signal:* `resolve_coaching_aim` (`learn/coaching_aim.py:36`, built+tested) is reached ONLY through `resolve_coaching_aim_skill:61`, whose sole non-test caller is the **live brain** `agent/dj_cohost.py:896` (`_resolve_prompt_cell`). It shapes the live system prompt but never selects a *lesson's* next drill.
*Wire:* call `resolve_coaching_aim(progress)` from the lesson next-drill FSM advance in `learn/runtime.py` so the lesson teaches the Competent-not-Mastered skill the learner is ready for, not the script's fixed order. Function-local import (in-island; `learn/` already owns the wrapper — cross-island law clean).
*Packet:* LEARN PR5. *Depends-on:* Q3/B1/B2/B3 (need a real graded drill to route to).

**B10 — Template the loop to a second skill (EQ-swap, cue-placement) + biquad-EQ node.** *(LEARN-10X P2)*
*Dark-signal:* the cue producer `grade_owned_cue_placement_attempt` already writes `CUE_PLACEMENT_GRADED`; 36/37 "twist EQ and listen" lessons filter nothing.
*Wire:* reuse the Tier-1 seams; add the **biquad-EQ DSP node** between the CC handler and B1's stream (3 RBJ-cookbook biquads in series, ~120-160 LOC, the **dual-filter anti-zipper crossfade on knob moves is the non-obvious clean-room part**). Plus the first-principles concept-beat content pass (text fixtures, AST-gated) and Q4's honest-completion fix riding alongside.
*Packet:* LEARN-10X P2 + MINE-biquad-eq. *Depends-on:* B1 (audio sink), Q5 (cue input fixed).

**B11 — Cited debrief reel.** *(LEARN-10X P4)*
*Dark-signal:* the debrief substrate exists (port 8766, `load_session` reads `events.jsonl` + `evidence_registry.json` + `voice.wav`) but there's no "what you earned tonight" reel of the cited Mastered/graded moments.
*Wire:* render layer on existing data — the honest, grounded "share" (real recorded cited events, NOT a fabricated highlight; NOT a real-time auto-cut clip — that engine doesn't exist).
*Packet:* LEARN-10X P4. *Depends-on:* Q3/B1-B3 + B9 (need live-set graded moments).

**B12 — Taste-aware Viber sequencing — RE-SCOPED.** *(ENGINES R9, corrected)*
*Dark-signal (corrected):* taste is ALREADY live in the pill (verified above). The remaining gap is ONLY the Viber/set-builder `toolset` path, where `transition_slate` is called without `taste_scores`. The VISION's named seam (`sequencer.library_bias`) is a TYPE MISMATCH (role-pair-keyed vs track_id-keyed); the correct seam is `TransitionScoringInput.taste_scores`.
*Wire:* feed `taste_scores` into `toolset`'s `transition_slate` call only.
*Packet:* NEEDS-REWRITING (the roadmap packet is stale). *Depends-on:* none; **lowest priority** — 0.05 weight = a nudge, not a differentiator; do NOT surface a "your taste!" label (over-claim slop); consent-gated, fail-closed.

### Launchd-dark safe live features (accidental muteness — distinguish from the KEEP list)

**B13 — Light the SAFE launchd-stripped live features (mic, deck-vision).**
*Dark-signal:* under `open -a`/Dock/launchd the parent env is stripped and the sidecar relays only a 16-key allow-list (`sidecar.rs:42-59`), so mic capture (`__main__.py:1351`) and deck vision (`__main__.py:684/2807`) ship OFF with no UI toggle for 100% of installed users. **This is accidental muteness, not principled silence.**
*Wire:* `setdefault` the safe-grounded ones in `_apply_packaged_defaults()` (mirroring the TTS rescue at `:837`), OR drive from persisted `ConfigStore` + a UI toggle. **Do NOT auto-flip F3 secondary-ear (grounding change), F5 drop-call, F6 harmonic-clash — those are OWNER ship gates (§6).** Mic = privacy-gate the toggle; deck-vision = clean FIX.
*Packet:* SELF-BLOCK-CENSUS F1/F4. *Depends-on:* none (mic unblocks any future KAAN_SPOKE upgrade).

---

## 4. PACKET INDEX — what Codex builds from

| Backlog item | Packet | Status |
|---|---|---|
| Q1 reasons receipt | `CODEX_READY-ENGINES-10X-TOP.md` | **EXISTS — ready as-is** |
| Q2 cue-confidence receipt | `CODEX_READY-ENGINES-10X-TOP.md` (sibling) | EXISTS — needs the cue-card paragraph appended |
| Q3 voice discarded grade | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 1 | **EXISTS** |
| Q4 honest-completion | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 6 | EXISTS |
| Q5 cue-judge faked input | `learn-10x/PR2.md` §7 | EXISTS (detail) |
| Q6 octave-fold phase bug | `mixxx-cleanroom/MINE-sync-phase.md` §3 | **EXISTS — clean-room spec** |
| Q7 learn empty-state | LEARN-10X L9 (`LEARN-10X-ROADMAP.md`) | reference only — NEEDS 1-pager |
| Q8 voice-muted banner | SELF-BLOCK-CENSUS V3/V6 | reference only — NEEDS 1-pager |
| B1 audible decks | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 2+3 + `MINE-twodeck-mix.md` | **EXISTS** |
| B2 tutor MOSS voice | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 4 | **EXISTS** |
| B3 grade IPC + HUD | `CODEX_READY-LEARN-FUSED-BEATMATCH.md` Inc 5 | **EXISTS** |
| B4 host CUE-DETR | `CODEX_READY-ENGINES-10X-TOP.md` (R3) | EXISTS — needs host/accuracy paragraph |
| B5 keyless `auto_crate.py` | `ENGINES-10X-ROADMAP.md` R4 | **NEEDS-WRITING** (CODEX_READY) |
| B6 `--export all` fan-out | `ENGINES-10X-ROADMAP.md` R6 + `MINE-cue.md` | **NEEDS-WRITING** |
| B7 voice section pairing | `ENGINES-10X-ROADMAP.md` R7 | **NEEDS-WRITING** |
| B8 drop-call voice | `ENGINES-10X-ROADMAP.md` R8 | **NEEDS-WRITING** |
| B9 ZPD drill router | `learn-10x/PR5.md` | EXISTS (detail) |
| B10 EQ template + biquad | `LEARN-10X-ROADMAP.md` P2 + `MINE-biquad-eq.md` | EXISTS (spec) |
| B11 cited debrief reel | `LEARN-10X-ROADMAP.md` P4 | reference — NEEDS 1-pager |
| B12 Viber taste (re-scoped) | `ENGINES-10X-ROADMAP.md` R9 | **NEEDS-REWRITING** (stale) |
| B13 launchd-dark features | `SELF-BLOCK-CENSUS.md` F1/F4 | reference — NEEDS 1-pager |

**STALE — do NOT follow:** `/Users/ozai/projects/dj-set-ai/.planning/LEARN-MOAT-PLAN.md` §1/§7 — its premise ("no code fires `BEATMATCH_GRADED` / `MiniDeck` never instantiated") is FALSE at HEAD (producer wired `runtime.py:1468`→`practice_loop.py:81`; `MiniDeck` at `beatmatch_practice_driver.py:66`). Build per `CODEX_READY-LEARN-FUSED-BEATMATCH.md`.

---

## 5. KEEP-vs-FIX MOAT BOUNDARY

**KEEP — deliberate silence; test-enforced; touching it breaks the release gate. The co-host's quiet IS the moat:**
- Un-cited live utterance strips to the ack-bank (Inv #2); the `<silence/>` short-circuit; whole-turn citation strip.
- `grade_beatmatch` abstains when a deck is stopped (`beatmatch_judge.py:93-103`) — calibrated honesty on no-attempt, not a bug.
- `CueProducerUnavailable` → heuristic fallback is a graceful degrade — **keep the fallback**; the FIX (B4) is to host the model, not remove the catch.
- `in_flight` gate + 12s stale-clear; mic / AI-talk gating; `HEARTBEAT_SEC=180` speak-gated idle (Inv #5); per-type cooldowns; `_music_truly_playing` 4s gate.
- Vibe Judge abstain / honest-null; master-only abstain is correct (only the *missing single-deck path* is fix-worthy — D1 in §6).
- The idle-aware grounding-failure timer (already fixed the empty-screen bug); single-socket bind (Inv #4); `PASSTHROUGH_GAIN=0.0` silent passthrough.
- MOSS-only / no-cloud-TTS-fallback (Kaan-locked); `VIBEMIX_CITATION_LINT` OFF and `VIBEMIX_LOOKAHEAD` OFF (flipping these HURTS the co-host).
- `apply_live_claim_guard` IS wired (`dj_cohost.py:3017` → `deck_context.py:2909/2909`; codegraph "no callers" was an import-alias parse artifact) — do NOT "re-wire" it.
- The 45s skip ITSELF (anti-frustration escape) — only its full-weight *credit* is the leak (Q4).

**FIX — accidental muteness; the gold is dark by mistake, not by design:**
- Discarded beatmatch grade (Q3); degenerate phase grade from a frozen cursor (B1); octave-fold false trainwreck (Q6); faked cue-judge input (Q5); full-weight skip credit (Q4); silent learn bail (Q7); silent MOSS failure (Q8); text-only tutor (B2); dead voice picker (B2).
- Computed-but-unrendered receipts: `reasons[]` (Q1), cue-confidence (Q2).
- Unhosted CUE-DETR model → heuristic-only moat (B4).
- Launchd-stripped SAFE live features — mic, deck-vision (B13).
- Rekordbox-only export while universal carriers exist (B6); Viber set-builder taste hook unfed (B12).

**CUT — verified rationale; do NOT relitigate:** Mastered shareable clip / signed passport / honest leaderboard / verdict sticker (no media-encode/signing/server infra); genre-prototype text search (no text→genre substrate); mid-set vibe-drift commentary (no buffer, new speak trigger); raw 10-dim number dump (slop); real-time CUE-DETR on the live stream (offline-only); LLM-placed cues (breaks Inv #3); Gemini Viber fallback (Viber=Codex locked); cross-session Viber memory (single-turn by contract); count-in `=="dj"` flip (lesson-only, never reaches a live set); "your taste is shaping this" track-level label (0.05 weight = over-claim). Whys in `ENGINES-10X-ROADMAP.md` §4 + `LEARN-10X-ROADMAP.md` §4.

---

## 6. OWNER-DECISION REGISTER — flagged, NOT decided

Every gate that needs Kaan to rule before engineering proceeds. None of these is an engineering call.

| ID | Gate | Blocks | Decision needed |
|----|------|--------|-----------------|
| **O1** | **CUE-DETR hosting + accuracy bar** | B4 → B5/B6/B7/B8 | Where is the ONNX artifact hosted (HF mirror vs Bravoh release infra)? What accuracy threshold against real Rekordbox cues before it writes cues into a user's library? |
| **O2** | **MOSS CI hosting** | a guaranteed-voiced clean-CI build | Set `VIBEMIX_MOSS_TTS_ARCHIVE_URL/SHA/SIZE` so `release.yml` fetches+bundles on a clean runner — 728MB hosting + bandwidth cost. (DMG is NOT mute today; this closes the clean-CI / `cargo tauri build` bypass / model-less-clone residual.) |
| **O3** | **Drop-call live-validation** | B8 | Flip `VIBEMIX_DROP_CALL` only after an accuracy bar against a real drop (heuristic mis-fires on hardtechno). Keep OFF until then — document as a ship gate, not accidental dark. |
| **O4** | **Harmonic-clash / secondary-ear** | F3/F6 in B13 | Secondary-ear is a prompt-grounding change (run grounding-review); harmonic-clash is unsafe-until-live-validated. Keep OFF until ruled. |
| **O5** | **Mic + recall privacy posture** | B13 mic toggle; F2 recall | Privacy posture + stale ear-pass for recall; mic ships with a privacy-gated toggle. |
| **O6** | **Mastered-cue write to user library** | F7 (Mastered-moment→hot-cue) | Writes to the user's Rekordbox/Serato — opt-in default? |
| **O7** | **Keyless-builder vs Codex framing** | B5 | Is `auto_crate.py` the default front door, with Codex the "interpret a fuzzy brief" power path? |
| **O8** | **Master-only harmonic path (D1)** | a single-deck "key context" verdict | Add a single-deck Camelot+BPM verdict so stereo-only users get harmonic coaching, keeping the 2-deck executed-blend path? (Medium — the abstain stays; only the missing single-deck path is the FIX.) |
| **O9** | **Practice-loop WAV licensing + bundling** | B1 packaged app | Which intro/build loops ship, and their licensing? (PyInstaller spec collects only `.json`/`.txt` today — add `**/*.wav` at `vibemix-core.macos.spec:260-264`.) |
| **O10** | **Free-vs-Pro cost shape** | gating of B5/B6 (gig-prep) + B8 (live voice cost) | Which of these sit behind the €4.99 Pro / €9.99 Studio tier vs Free? |

---

## 7. DEPENDENCY SPINE (build order)

```
Q1+Q2 (read receipts, zero risk) ─────────────── ship FIRST
Q3 (voice grade) → B1 (audible decks, un-degenerate phase) → B2 (tutor MOSS) → B3 (HUD)
   └ land Q6 (octave-fold) WITH B1 (masked until cursor moves)
Q4,Q5,Q7,Q8 (cheap correctness flips + light dark) ── ship alongside Tier-1
B4 (host CUE-DETR) ── force-multiplier ──► B5, B6, B7-voice, B8; fills Q1/Q2 for most users
B7, B8 (voice — grounding-review gated; B8 LAST, hard-gated B4)
B9 → B10, B11 (depend on the fused loop)
B12, B13 (low priority / launchd-dark)
```

---

> Source docs (all under `/Users/ozai/projects/dj-set-ai/.planning/packets/2026-06-03/`):
> `SELF-BLOCK-CENSUS.md` (canonical KEEP-vs-FIX), `LEARN-UX-REALITY.md` (1.5/5 loop), `CODEX_READY-LEARN-FUSED-BEATMATCH.md` (Q3/B1/B2/B3/Q4), `CODEX_READY-ENGINES-10X-TOP.md` (Q1/B4), `ENGINES-10X-ROADMAP.md`, `LEARN-10X-ROADMAP.md`, `MIXXX-CLEANROOM-SPECS.md`, `mixxx-cleanroom/MINE-{twodeck-mix,biquad-eq,sync-phase,beatgrid,cue,key,autodj}.md`, `learn-10x/PR1..PR6.md`, `wire-the-gold/RECON-{learn,engines,live-dsp}.md`.
> STALE: `.planning/LEARN-MOAT-PLAN.md` §1/§7.

---

## 8. CHECK-IN — completeness-critic pass (added post-synthesis)

Two read-only completeness critics combed all 24 raw docs against this backlog to catch gold the exec-summary synthesis might have dropped. **Verdict: the backlog is CONFIRMED** — the Verify phase (§2 REFUTED list) had already independently caught the four big would-be misses (TasteModel-stale, `render_block`-callers, scorer-already-reaches-mouth, MOSS-not-mute). Genuine additions below — fold into the named items. Full lists: `DROPPED-GOLD-LEARN-DSP.md` + `DROPPED-GOLD-ENGINES.md`.

- **A1 — GUARD-RAIL on B1/B10 (anti-slop — do NOT miss): `exemplar_audio_forbidden`.** 5/6 Course-3 lessons set this flag (`learn/lesson_flow.py:115/266`). B1/B10's "register audio for the listen-lessons" MUST respect it — injecting practice/exemplar audio into a lesson that runs DURING a live set would play over the user's master output = Invariant-#3 / anti-slop regression. Add as an explicit gate: audio sink only for lessons NOT flagged `exemplar_audio_forbidden`. *(This is the single highest-value critic addition — a blanket audio fix without it is a slop regression.)*
- **A2 — transition EXECUTOR orphan (new item B14, MEDIUM).** `score_transition_slate` is scored but NO executor turns a scored transition into a played fade (`transition_executor` not found; spec in `MINE-autodj.md`). This is the "demonstrate-half" engine for a future transition-practice loop (Sven *performs* the graded blend so the learner hears the target). Park as B14, gated like B1 (audible, owned-deck) + grounding-review.
- **A3 — scope-correct B2.** Reading `config.voice` at boot fixes the DEFAULT voice, but live voice-swap won't take effect without an engine rebuild — the voice is baked at `_OrtCpuEngine.load` (`local_tts.py:308`). B2 must reload/rebuild the MOSS engine on a voice change, not only read at boot.
- **A4 — UX note on Q4.** Q4 fixes the skip CREDIT leak, not the 44.5s forced-dwell silence a bored beginner endures before skip unlocks (`runtime.py:839-863`). Pair B10's concept-beat-deepening with a shorter / where-earned dwell so the wait isn't dead air.
- **Minor / already-covered:** beatgrid fixture constants (`kMaxSecsPhaseError=0.025`, `kMinRegionBeatCount=16`, BPM-snap ladder — in `MINE-beatgrid.md`; attach to B1 fixture-minting); Viber `build_set_progress_voice_line` is already live (B12-adjacent, one persisted curve-target field short); the semantic *visual* headline upgrade folds into Q1's render receipt.

- **A5 — Rekordbox ANLZ phrase/cue persistence is DONE; B15 is verify-only, not a build.** vibemix ALREADY parses Rekordbox PSSI **phrase** (intro/build/breakdown/drop/outro) + hot/memory cues + beatgrid (`library/anlz_ingest.py`, `library/sources/rekordbox.py`), and has full IMPORT for Serato/Traktor/VirtualDJ/EngineDJ cues (`library/sources/`), all normalizing to one `TrackEntry`/`CuePoint` shape, with correct precedence (DJ-cues → ANLZ-phrase → CUE-DETR last). Current-source correction: `library ingest` materializes matched ANLZ phrases into persisted `TrackEntry.cues source="anlz"` before `library.pkl`, and `sections_for_entry()` reads those cached cues back with `source_detail="pssi"`. **Do not build a second ANLZ→cue path.**
  - **Re-rank B4/O1 DOWN:** for the library/embedding lane a Rekordbox DJ's own cues already win (heuristic fallback beneath) → CUE-DETR is a fallback there, not a requirement; O1 (hosting + accuracy bar) eases — it's no longer on the critical path for the target (Rekordbox) user.
  - **B15 (VERIFY-not-build):** prove the already-persisted ANLZ cues survive `library.pkl`, reach section consumers, and correct the stale docs. DROP-call/live voice remains owner-gated behind the real accuracy bar; do not flip `VIBEMIX_DROP_CALL`. Packet: `CODEX_READY-B15-VERIFY-ANLZ-CUES-LIVE.md`.
