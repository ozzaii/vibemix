# STATE OF ALL LANES — End of Day 2026-06-04

> Chief-organizer synthesis of six verified per-area reports (audit + survivor opportunities + flags). Every claim below was re-verified against committed artifacts, HEAD source, or a reproduced run. Where an upstream audit overclaimed, the corrected figure is stated inline.

## Headline

The engine got materially more honest today and the human-facing layer got materially less dark, but nothing crossed the "a stranger heard the real co-host over a real set" line. Five lanes shipped real, committed, single-parent work: a coach-identity speak-gate (9/9 routing), a forward-coach cue-lookahead that writes real `[cue:...]` evidence, 28-of-37 Learn lessons now audible with grade-to-advance closing, a GiantSteps key bench that reports unflattering-but-real numbers, a built-and-grounded particle organism ambient layer, and a Chatterbox-Turbo TTS wire that never mutes. The catch is uniform across lanes: the load-bearing proofs are code-without-a-run. The Sven friend-score lift is aspiration, the Learn gains predate today's commits, the organism has never compiled on a real WebView, the new TTS voice has never reached a human through the product pipeline (the dep is not in the project venv; voice provenance is cleared, not a blocker), and the ship keystone (real master audio into the brain) is end-to-end-unproven because the doctor's recommended capture device flips between two runs on the same rig. Today bought integrity and reach. Tomorrow has to buy one real captured set that fires all of it at once.

---

## Sven — live co-host voice/coaching

**DONE-FOR-REAL**
- Speak-gate is live-wired: `decide_speak_gate` called at `coach.py:818` after the voice payload attaches; `--gate-only` sim runs deterministic and offline, 9/9, inside the `.venv` (it imports `dj_cohost` at module top, so it needs livekit on the path).
- Coach-identity persona is the live cell: `HYPE_INTERMEDIATE = SVEN_COACH_IDENTITY` (`matrix.py:432`); the "every automatic turn is one complete speaker-ready sentence" contract line is real prose (425).
- Forward-coach (`bb708077`) is genuinely wired and grounded: `_build_cue_lookahead_voice_line` fires on `suggestion is None`, gates confidence >= 0.7 / ETA <= 64s, writes `[cue:...]` to EvidenceRegistry via the real signature (Invariant #2 held). State fields live on `MusicState:216-218`, written only by `refresh.py:1505-1507` (Invariant #1 held). Built unconditionally, outside the suggestion-service guard.
- `d9168ef1` widened the describe-bank to include `PHRASE_BOUNDARY` + `SUB_LAYER_ARRIVAL`; scaffold-repair (`f5d8b6b8`+`bb708077`) wired both `dj_cohost.py` paths with recorder tags. Focused tests green (20 passed across `test_suggestion_voice` + `test_speak_gate`).

**DARK**
- No committed Sven model+judge artifacts. `git ls-files | grep respan_sven` returns only the two scripts; no `.planning/eval-runs/*sven*`. The "friend 1.4 -> >=2" claim is un-rerun aspiration, resting entirely on the prior `project_sven_prompt_bench_measured` run, not the new move-less cue-lookahead scenarios.
- The cue-lookahead branch has zero direct test coverage. The `tests/learn/*` and `test_live_course3_lens_probe.py` hits are state fixtures and lens probes; none call `_build_cue_lookahead_voice_line` with `state=`.

**SUSPECT**
- Heartbeat-judge `--apply-current-gate` over-silences: `apply_current_gate_replay` builds `Event(event_type, MusicState(), extra={})` and its own docstring admits it does not reconstruct old `event.extra` payloads. The flag name implies "what the gate keeps" but measures a no-payload worst case.
- Sim/live persona divergence: sim sets `include_citation_grammar=False` (`263`), live sets `True` (`dj_cohost.py:1345`). Any sim model-leg number for the cue-lookahead is not live behavior, so a bench run that does not flip this flag judges the wrong prompt.

---

## Learn — hands-on practice + teaching loop

**DONE-FOR-REAL**
- Audible-lesson count re-verified by running the real HEAD gate over the live `CURRICULUM`: 28 audible / 9 silent of 37 (silent set `L0.00`, `L1.01`, `L1.09`, `L3.01`-`L3.06`). The "33-of-37 silent" framing in `RETASK-AND-RESEARCH.md` is stale (predates `2b50d143`).
- EQ/filter/fader DSP is real and wired: `learn/dj_eq.py` is 548 lines of RBJ biquads, instantiated in `MiniDeck` (`audio/miniplayer.py:181,194-197`); EQ lessons L1.03/L1.14/L2.04/L2.05/L2.06 carry deck-bound actions and play.
- Grade -> credit -> advance closes (`_advance_to_next_lesson_if_needed`, `runtime.py:1583`); citation grounding is honest (`_emit_live_beatmatch_grade` sets `citations=()` unless `result.event is not None`); Invariant A1 intact (`can_play()` refuses during a live audible set).
- By-bus proof is genuine: `CODEX_VERDICT-LEARN-FUSED-BEATMATCH-LIVE-PROOF.md` (committed `4c0eed9a`) carries a real ws payload with `"verdict":"locked"` and `"citation":"[ev:BEATMATCH_GRADED@138.318]"`. Cue grade no longer fed faked-perfect input (`cue_frame = target_frame` is gone). IPC two-ended; graduation summary wired (`__main__.py:2884`); wavs bundled (`vibemix-core.macos.spec:260-262`).

**DARK**
- The strong by-bus proof (`4c0eed9a`, 00:05) predates today's playable-decks / auto-advance commits (`c015cd6d`/`d67b85da`/`2b50d143`/`2b847c79`, 12:35-12:52). The 28-lesson reach and auto-advance are SRC-green but unproven live at HEAD. The only learn eval-run on disk (`learn-live-hands-20260602`) is older.

**SUSPECT**
- L1.13 "real, bundled waveform" overstates: the audio is synthesized (sine base + band-exemplar layers + programmatic `section_gain` at fixed quarters) and `_demo_cues()` are authored fixed bands, not a detected arrangement. Adequate for "spot the breakdown by eye"; do not let ship copy imply a real track.
- Cue-grade timebase grades `action_elapsed_s = monotonic() - lesson_started_at` (wall-clock) against a fixed beat-16, not the owned MiniDeck `b_frame`. Grounded but musically loose; a deliberate learner is penalized.

---

## Library + Engine/DSP — embeddings, key, cue, next-suggestion

**DONE-FOR-REAL**
- Key estimator (`bd797971`) is real on GiantSteps-604 (604/604 audio found): MIREX `0.191` -> `0.512` (cqt-profiles) -> `0.558` (tuned); exact `0.124` -> `0.439`. Reimplement-clean confirmed (KK/Temperley/EDMA arrays carry "no Essentia/libKeyFinder source copied"; repo-wide vendored-DSP grep is clean).
- ANLZ cue agreement (`ad35ec8f`) is real: 44 PSYMIND tracks, 352 DJ refs, mean agreement `0.236`, mean abs offset `0.59s`, status ok. The negative finding (PSSI phrase anchors are not where this DJ places cues) is honest.
- Section vectors (`c9462365`) are real and wired: `section_vector_cache` table, the <=80s clamp, `_ensure_section_vectors_for_track` in `ingest.py:844`, and live readers (`next_suggestion.py:726/734`, `toolset.py:1798`) with an explicit `track_vector_fallback` basis.
- Real-library similarity (`574ae16d`): 84 tracks, raw p@1 `0.798`, centered LOO `0.583`, with an honest `proxy_caveat` (bootstrap folder labels, not human truth). S2 MK3 HID (`c578c89d`) clean-room.

**DARK**
- `auto_tags.py` is built but has zero product callers (the lone `library_auto_tag` hit is a model alias). Its bench is honest-null `unproven_no_hand_labels`. Correction to the upstream audit: it is git-tracked and committed (in `c9462365`'s tree), not "dirty/untracked." So it is committed-but-dark.
- The section-vector live payoff is unobserved by-ear/by-bus.

**SUSPECT**
- `"section_beats_whole": true` is cherry-picked: it rests on centered p@1 `+0.026` (n=38) and reverses everywhere else (centered p@5 `-0.137`, raw p@1 `-0.158`, whole-track MRR 0.695 > section 0.678). Noise-band, not a validated win.
- Zero regression guard on any real accuracy number: `test_key_estimator_bench.py` asserts only scoring math on synthetic inputs. The 0.558 / 0.80 / 0.236 / +0.026 numbers live only in JSON; any CLAP/CQT/profile change can silently regress them with every test green.
- One-owner-library risk: cue, similarity, and section all run on one psytrance collection with bootstrap folder labels. Key (GiantSteps) is the honest public exception.

---

## Frontend + Organism — Crate, settings, debrief, session, pill, organism

**DONE-FOR-REAL**
- Build/test green re-verified: `npm test` -> 158 files, 1491 passed + 1 todo, 0 fail (15.2s).
- Kill-list strips across 5 surfaces are real deletions: session top-strip + "made by bravoh" sig (`12b4e919`/`2b654c44`), settings reload-overlay theater that flashed "RELOADING PROFILE..." with no sidecar confirmation (`46ead19e`), debrief Format/Hash cells (`b756abe5`/`980558ec`/`78cac647`), shell (`e148d054`), pill 4254 deletions with 9 gamification mock-transfer wires removed (`826fddc9`).
- Crate fixes real: 720/760px centered column (`2bf1e2d5`), composer grid + fixed mode-tab strip (`222b3f3e`), chip pre-fill -> `run()` (`918839a0`).
- Organism ambient layer is real physics and grounded: `SIM_SIDE=128` (16,384 pts), golden-angle distribution, curl-style tangent drift, `uBeatPulse`, UnrealBloom. Beat pulse fires only when `bpmConfidence > 0.6` AND a real downbeat wrap; signals fed from real ws-bus frames (`index.ts:413`). Honors Invariant #3. Opt-in gated `visible:false` (`config.rs`, rc1).

**DARK**
- The organism's expressive layer (`morphToPill`/`morphToMask`/`focusAt`/`reform`) is unreachable from the bus/event path: `renderer.ts` calls only `tick/setSignals/enableBloomLayer/dispose`, and `index.ts` has no path to focus or morph. The MorphController is built and unit-tested but the human can never trigger it today.
- The organism has never compiled on a real WebView. Every "real physics not dots" and "blooms" claim is code-true and runtime-unproven (jsdom never compiles WebGL).

**SUSPECT**
- Residual gamification vocabulary survived the pill kill-list: `src/pill/move-grade-vocabulary.ts` ("SEXY"/"overdrive"/grade verbs) still exists and ships in the bundle, reachable only via the DEV-gated demo path (`pill/index.ts:494/547`). Shipped users do not see it, but the audit's "all of it goes" was an overclaim.
- The two biggest new builds (`93540ee9`/`bbe851a0`, 471 lines of shader/bloom; `46ead19e`, settings) carry bare/sign-off-only commit bodies with no by-eye/by-bus receipt committed.

---

## Voice / TTS — Chatterbox-Turbo wiring

**DONE-FOR-REAL**
- `e4fff670` touches exactly 3 files (`chatterbox_tts.py`, `tts_chain.py`, test). No edits to `coach.py`/`dj_cohost.py`/`prompts/`/`event_detector.py`/`refresh.py`/`evidence_registry.py` — speech-render-only, Invariants #1/#2/#3 untouched.
- Default path byte-for-byte unchanged: with `VIBEMIX_TTS_ENGINE` unset the new branch is skipped and reaches the identical `_build_moss_chain`.
- Never-mute at build time: chatterbox-selected-but-unavailable -> stderr note -> MOSS. `chatterbox_available()` gates on both `mlx_audio` importable AND the ref clip. MOSS structural parity confirmed (same caps, channels, FallbackAdapter shape, reuses `pcm16_mono_le`). 18 TTS tests green; `test_chunked_stream_pushes_engine_pcm` drives `_run` through a real emitter (not a tautology). Model-literal gate passes.

**DARK**
- The feature is dark in-app: `mlx_audio` is not in the project venv, so `chatterbox_available()=False` and the path silently falls to MOSS. The voice has never reached the human through the product pipeline. The ref clip `~/.cache/vibemix/cohost_voice_ref.wav` (720k) does exist, so the dep install is the only thing between the committed code and a live render.
- Learn tutor voice is hardcoded MOSS: `_build_learn_tutor_speak_audio` calls `moss.synthesize_pcm` directly (`__main__.py:294`), bypassing `build_tts_chain`. A chatterbox session would speak two different voices in one app. Bench numbers (0.21s TTFT / 0.15 RTF) are not committed; they live only in the ephemeral `~/.cache/vibemix-tts-bench/` scripts.

**SUSPECT**
- `engine_selected()` is dead outside its own two tests; `build_tts_chain` reads env directly, so the "what means chatterbox" logic is duplicated and can drift.
- Runtime engine-failure has no MOSS floor: `build_chatterbox_adapter` returns a single-provider `FallbackAdapter`. Never-mute is proven for selection, not for a mid-session synth failure (which goes silent).
- Minor: `live_moss_tts` is gated on `local_tts_enabled()`, not "constructed unconditionally" as the audit said. The wasted-load only happens when MOSS is also enabled.

---

## Bench & proof integrity

**Real benches (ran, produced honest numbers, committed against artifacts):**
- GiantSteps key bench — real GiantSteps-604, `0.124` -> `0.439` exact, `0.191` -> `0.558` MIREX, all reproduced against committed reports.
- ANLZ cue-agreement — `0.235919` mean over 44 DJ-reference tracks, low number reported straight (honest negative).
- Respan gate-only — re-ran, 9/9 routing matched; harness imports the real `decide_speak_gate` / `build_system_instruction` / `resolve_model`, zero hardcoded model literals.
- Real-library similarity — raw p@1 `0.798` over 84 tracks with the bootstrap-label caveat stated.
- Chatterbox default-OFF — `engine_selected()` defaults to `"moss"`; never-mute fallthrough verified; model-literal grep gate green (31 passed).

**Proof-integrity flags — verdicts:**
- `45f67cd1` (retroactive summary edit) — **HONEST.** Diff is exactly 2 lines, `mic_was_muted`/`voice_was_muted` flipped false->true to match the file's own `VIBEMIX_ENABLE_MIC=0` launch env and `mic_values:[0.0]`/`voice_values:[0.0]` probe data. It corrects a wrong verdict to match its own untouched evidence. Not a green-wash.
- `5f129f88` (blocked bench) — **HONEST.** Commits `exit_code=2`, stderr "beatgrid manifest not found... needs Kaan/Rekordbox truth BPMs", empty stdout. Records a blocked run; never claims a success.
- `5eea9a8e` (amend-blob from the Sven reset/resplit) — **dropped and unreachable**; `f5d8b6b8` (the real Sven fix) is in HEAD ancestry. No content lost. 131 commits today, all single-parent, zero merges, zero reverts.

**Caveats that must not calcify into ship copy (green but misleading if quoted raw):**
- GiantSteps `0.124 -> 0.439` conflates abstain-elimination with accuracy: baseline abstained 348/604 (42% emission), tuned abstains 0 (100% emission). The honest emitted-vs-emitted figure is `0.293 -> 0.439`. The "0 abstained" claim is tuned-run-only.
- `numeric_agreement_claimable` is `null`, not `true`; the cue grounding is asserted via `agreement_score_is_not_fabricated_without_dj_refs: false`. The `0.236`/44-ref numbers live in `psymind-hotcues.json`, not the `anlz-cue-agreement-local` file some prose pointed at.
- `section_beats_whole: true` is a +0.026/n=38 noise-band edge that reverses on every other metric.
- Fabricated test counts in an upstream Learn audit ("139 dj_eq tests" actual 15; "878 learn+audio tests" actual 1059). The suites genuinely pass; the cited numbers are invented and must not appear in any ship doc.

**Verdict: honest, not green-washed.** No green-washing pattern was found across any lane. The benches that ran produced real and sometimes unflattering numbers. The only gap is code-without-a-run (Respan full-generation Sven bench) plus a keystone not yet heard end-to-end.

---

## Ship keystone — real master audio into the brain

The single thing standing between all of today's work and a stranger hearing the real co-host over a real set is the audio-capture device routing. Two committed doctor runs on the same rig disagree about which device is the master-capture path:
- `input-only-multioutput-20260604-110537` (11:05): BlackHole **2ch** rank #1, `live_signal:true`, peak 0.213, rms 0.038.
- `multioutput-doctor-20260604-112527` (11:25, 37 min later): BlackHole **16ch** rank #1, **2ch dropped to rank #2 with `live_signal:FALSE`**, and `auto_master_recommendation` points to 16ch.

The keystone fix-logic is sound and the bus-proof is real (92 frames, music heard), but "the doctor recommends BlackHole 2ch" is not a stable fact — the winning device flips between the two runs. The earlier `rms=0.0` symptom is the failure mode when the DJ app, system output, or a Multi-Output device feed the wrong BlackHole channel set (or the co-host hears its own voice as phantom music — see the CLAUDE.md Audio MIDI Setup note).

**Cleanest fix:** before treating the keystone as settled, nail down *why* the same rig ranks 2ch versus 16ch differently across two runs minutes apart (routing-state change, or a sampling-window artifact in the doctor). Then make `auto_master_recommendation` deterministic across repeated runs, and only after that capture one sustained driven set with library enabled (so cue-lookahead fires), proving hundreds of frames with sustained nonzero `music_rms` and grounded coach lines whose citations resolve in EvidenceRegistry. In Audio MIDI Setup, route only the DJ app into BlackHole; do not let system output or a Multi-Output device also feed it. That single captured set feeds every downstream bench and is the by-ear "real DJ friend" gate the quality bar demands.
