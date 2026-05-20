# Phase 54: Hype Mode Live — Research

**Researched:** 2026-05-21
**Verified against:** HEAD `9137a91` (live `src/vibemix/` + `recordings/` + `eval/` + `tests/`, this session)
**Mode:** Orchestrator-grounded inline research (autonomous `fully`). Every claim below was read off the live source or a real captured trace, not assumed.

> **Scope reminder (from 54-CONTEXT.md):** the reaction machinery ALREADY EXISTS and ships at HEAD — EventDetector + per-type cooldowns + the HYPE_* persona matrix + the coach loop firing path + the EvidenceRegistry/CitationLinter anti-slop chain. This phase HARDENS grounding + TUNES timing with test-pinned, real-trace regressions. It does **not** rebuild any of it. The across-≥2-genres "feels alive" sign-off is Kaan-action (his ears — the hard quality gate per CLAUDE.md).

---

## Question 0 (the critical one) — What is the ACTUAL current hype firing behavior? Is the "32s-silent-on-drop" bug real at HEAD, or already closed?

**Answer: the co-host fires RELIABLY at HEAD. The "32s-silent-on-drop" framing is HISTORICAL (pre-fix). A real captured trace proves 52 events → 52 LLM invocations → 52 spoken reactions with ZERO suppressions. The plan must HARDEN grounding + TUNE timing, NOT chase a phantom firing bug.**

Hard evidence from the real captured session `recordings/20260515-112139/events.jsonl` (a real ~25-minute live drive on Kaan's Mac):

| Metric | Value | Source |
|---|---|---|
| `event` lines fired | 52 | parsed live |
| `llm_invoke` lines | 52 (1:1 with events) | parsed live |
| `ai_text` (spoken reactions) | 52 (1:1 with invokes) | parsed live |
| suppressions (`silence_short_circuit` / `slop_suppressed` / `citation_strip`) | **0** | parsed live |
| event-type histogram | PHASE 21, MIX_MOVE 20, HEARTBEAT 8, LAYER_ARRIVAL 2, TRACK_CHANGE 1 | parsed live |
| events span | 687.9s → 1541.7s (~14 min of active reactions) | parsed live |
| **max gap between consecutive events** | **29.6s** (a PHASE@1190.7 → MIX_MOVE@1220.3 pair) | parsed live |
| gap median / min / max | 15.5s / 14.0s / 29.6s | parsed live |

The 29.6s max gap is **the** ~32s window the roadmap remembers — but it is NOT a dropped reaction. It is the natural cooldown spacing: after a PHASE fires, PHASE has a 10s per-type cooldown, EVENT_GLOBAL_MIN_GAP is 10s, the coach loop holds 7s after the AI stops talking (`now - last_ai_voice_at < 7.0`), HEARTBEAT_SEC is 45s, and PHASE only re-fires when `state.phase` actually transitions to a *different* non-silent label. A 21-PHASE-event session with median 15.5s spacing is the system working: reactions present at the right density, not a dead loop.

**Why the bug was real once and is closed now (the firing path verified at HEAD):**
- `runtime/coach.py::coach_loop` (the firing loop) — polls at 10Hz, calls `event_detector.detect(...)`, and on a non-None Event sets `agent.set_next_event(ev)` then `session.generate_reply(...)`, then `await handle.wait_for_playout()` with a 20s timeout. Single-in-flight via `trigger_state["in_flight"]` (stale-cleared at 12s). Verified `coach.py:189-248`.
- The historical silence had several plausible contributors that are ALL now mitigated at HEAD:
  - `max_output_tokens` was once 220, then lifted to 1024 for gemini-3.5-flash (`dj_cohost.py:417, 683` — Kaan WIP comment "don't cap output"). A 220-cap could truncate a reaction the thinking budget ate into → empty `full_text` → "skip TTS" (no voice). At 1024 the reaction has room. **This is the most likely root cause of the historical dead window.**
  - The CitationLinter `strip` path (`dj_cohost.py:1042-1058`) yields NO chunks when a citation is invalid — a real anti-slop mechanism, but if mis-tuned it can silence a turn. At HEAD the linter is opt-in (all-4-kwargs-or-nothing wiring) and the captured trace shows 0 strips — so it is not silencing real sessions today.
  - The 7s post-AI cooldown + 12s stale-in-flight clear together bound any "stuck" window to ≲12s, not 32s.

**Honest LIVE-01 framing (locked):** the voice fires (proven, 52/52). The remaining engineering job is to make firing fire RELIABLY-AND-GROUNDED — i.e. (a) **pin** the firing path so a future regression can't silently re-introduce a dead window (a trace-replay test that asserts every detected drop/build event produces an Event within an in-bar tolerance, respecting cooldowns), and (b) **harden** anti-slop so a fired reaction always traces to real evidence (empty/weak evidence → no hallucinated hype line). The "feels alive across ≥2 genres" call is Kaan's ear.

---

## Question 1 — What is the precise event→voice firing path, and where can a reaction be silently dropped?

**Answer: the path is `EventDetector.detect → coach_loop sets in_flight + set_next_event → session.generate_reply → llm_node builds grounded multimodal prompt → Gemini stream → silence/slop/citation gate → yield chunks → TTS → PlaybackQueue`. There are exactly four places a turn produces no voice, and all four are INTENTIONAL anti-slop / anti-pile-up gates — none is a bug at HEAD.**

The four no-voice exits (verified live, `dj_cohost.py::llm_node`):
1. **`<silence/>` short-circuit** (`:887-889, 930-939`) — the LLM explicitly chose to stay quiet. Intentional.
2. **Slop filter** (`:890-893, 940-950`) — `filter_for_slop` matched a banned phrase. Intentional anti-slop.
3. **Citation linter `strip`** (`:1042-1058`) — a citation didn't resolve to a registry observation; silence > invented citation. Intentional anti-hallucination (the anti-slop spine).
4. **Empty `full_text`** (`:996-997, 1079-1080` "skip TTS") — the model returned nothing (or the 220-token cap ate it pre-fix). At max_output_tokens=1024 this is now rare.

The coach-loop-level no-fire reasons (verified `coach.py`):
- `in_flight` true (a generation is running) → drop the tick. Stale-cleared at 12s (`:146-154`).
- `levels.voice > AI_TALK_THRESHOLD` (AI is currently talking) → drop (`:157-161`).
- `now - last_ai_voice_at < 7.0` (post-AI breathe window) → drop (`:162-165`).
- `event_detector.detect` returned None (no qualifying event this tick) → continue.

**Pin target for the plan:** a deterministic test that drives a real-trace MusicState sequence (or the captured `events.jsonl` ground-truth) through `EventDetector` and asserts the drop/build events (PHASE transitions, LAYER_ARRIVAL) fire at the real timestamps within an in-bar tolerance and respect the locked per-type cooldowns — closing the "a clear event passes with no Event" regression class at the detector boundary (the coach-loop wiring above is already exercised by `tests/state/test_coach.py`).

---

## Question 2 — Where exactly do hype reactions get GROUNDED, and how do we pin "empty evidence → no hallucinated hype line"?

**Answer: grounding is built in `AICoach.build_prompt` (the evidence packet: `evidence_line` + `task_for_event`) and enforced at emit time by the CitationLinter chokepoint. The anti-slop guarantee = a reaction whose citations don't resolve in the EvidenceRegistry is STRIPPED (no voice). The plan pins this with an empty/weak-evidence regression.**

The grounding chain (verified live):
- `state/coach.py::AICoach.evidence_line` builds the grounded-state string from REAL `MusicState` fields: `hearing[rms/sub/low/mid/high/bpm]` (or `hearing[silent]`), `track=...`/`track=unknown` (gated at confidence ≥ 0.3), `deck`, `set_time`, `recent_moves[8s]`, `set_arc`, `phase_history`, `recent_tracks`, and an `evidence_corpus[ev=N,aud=M,mix=K]` footer when the registry snapshot is non-empty. **Load-bearing anti-hallucination invariant** (`coach.py:14-18, 85-86`): NO `phase=` field — the RMS-derived phase label primed the AI to invent kicks/drops; the AI must hear the phase from the audio Part itself. **Do not reintroduce.**
- `state/coach.py::task_for_event` is the per-event instruction tail. For PHASE: "React to what the new section FEELS like, not the label." For MIX_MOVE: "describe the SONIC EFFECT… If the audio didn't actually change, output a single space to stay silent" — the built-in no-fire-on-no-change escape hatch.
- `dj_cohost.py::llm_node` attaches the grounded text + the last 6s (diet) or 18s (full) of REAL audio as a Gemini Part (`:501, 609-612`) — the model literally hears the moment. Screen Part is `None` (v4 anti-hallucination invariant, `:525`).
- **CitationLinter** (`coach/citation_linter.py::check` → `LintResult{valid, reason, missing}`) is the chokepoint: a reaction citing `[ev:DROP@45.2]` is valid only if the EvidenceRegistry has that observation. Invalid → `strip` (no voice) unless a one-shot bypass is active. `_build_citation_strip` (`dj_cohost.py:146-231`) additionally DROPS any UI chip whose citation doesn't resolve — "invented timestamps" hallucination class closed at the wire.

**The empty/weak-evidence anti-slop regression (the plan's spine, from CONTEXT §specifics):** build a MusicState with NO real events (silent or weak/ambiguous audio, empty registry) and assert hype mode does NOT emit a hallucinated hype line. Two complementary assertions, both automatable without a live LLM:
- **Detector level:** with `audible=False` (or BPM out of valid range), `EventDetector.detect(..., kaan_just_spoke=False, manual=False)` returns None — no Event, so no fire. Already true; pin it explicitly as the anti-slop floor.
- **Emit level:** feed the CitationLinter a reaction text that cites an event NOT in an empty registry snapshot and assert `LintResult.valid is False` (→ strip path → no voice). This pins the "fired prompt with no real backing → silence, never a fabricated line" contract end-to-end at the gate, using REAL primitives (`EvidenceRegistry()` + `CitationLinter()`), no network.

---

## Question 3 — How do we replay REAL psytrance + house/techno traces and assert in-bar firing + cooldown respect, without a live LLM or audio device?

**Answer: two substrates already exist — (a) the real captured `recordings/20260515-112139/events.jsonl` ground-truth (52 real events with timestamps + types), and (b) the offline `scripts/eval/replay_harness.py` that drives REAL EventDetector + EvidenceRegistry + CitationLinter at a 1Hz tick from a session dir. The plan adds a focused trace-replay regression that reconstructs a MusicState sequence and asserts the detector fires drop/build events at the real timestamps within an in-bar tolerance.**

What exists (verified live):
- **Real captured trace:** `recordings/20260515-112139/events.jsonl` — 52 `event` lines each with `t` (session-relative seconds), `type`, `audible`, `deck`, `track`, `track_conf`, `phase`. This is the "psytrance trace already captured" CONTEXT references (the `source.txt` placeholder says "house" but it's a real grounded live session — the substrate is the timestamps + types, not the genre label). Use it as the ground-truth firing-cadence fixture.
- **Offline replay harness:** `scripts/eval/replay_harness.py` walks a corpus of session dirs, loads `input.wav` into a real AudioBuffer via `AudioBuffer.fill_from_wav`, drives EvidenceRegistry + EventDetector + CitationLinter at 1Hz (REAL primitives, NOT mocks), and scores via judges. It already has a `--print-cooldowns` mode (`_emit_cooldown_report`) that reports per-type measured median inter-event gaps vs the locked `MIN_EVENT_GAP_PER_TYPE`, WARNING when `|delta| > 1.0s` — exactly the cooldown-tuning surface this phase needs.
- **`eval/corpus/sessions/{house,techno,hard_tek}_NN/`** dirs EXIST but their `events.jsonl` are EMPTY placeholders pending a Kaan-action corpus-acquisition step (`manifest.json._note`, `source.txt` "corpus acquisition pending"). **Landmine:** do NOT build the trace-replay regression to depend on these empty corpus WAVs — they have no audio. Build it on the real captured `events.jsonl` ground-truth (≥1 real genre) plus a SECOND synthetic-but-grounded MusicState sequence (a house/techno-tempo build→drop pattern) so "≥2 genres" is satisfied in the automated suite. The real ≥2-genre live drive across Kaan's library remains Kaan-action.

**The trace-replay regression shape (from CONTEXT §specifics):**
- Parse the real `recordings/20260515-112139/events.jsonl` ground-truth (or a checked-in fixture copy under `tests/fixtures/` so the suite doesn't reach into a mutable recordings dir). For each ground-truth PHASE / LAYER_ARRIVAL event, drive a MusicState reflecting that transition (phase flip, band jump) into a fresh `EventDetector` at the recorded `t`, with the clock patched (`mocker.patch('vibemix.state.event_detector.time.time')`, the pattern `tests/state/test_event_detector.py` already uses). Assert the detector emits the matching Event type within an in-bar tolerance and that consecutive same-type fires respect the locked per-type cooldown (no double-fire inside `MIN_EVENT_GAP_PER_TYPE`).
- **In-bar tolerance:** one bar at 130–145 BPM ≈ 4 beats × (60 / bpm) ≈ 1.65–1.85s. The coach loop ticks at 10Hz so detection granularity is 0.1s; the meaningful tolerance is "the Event fires within ±1 bar of the real transition" — express it as a tolerance constant (e.g. `IN_BAR_TOLERANCE_S = 2.0`, the conservative upper bound) so a tuning change is a one-line edit (per [[feedback_no_gsd_orchestra_for_trivial_tweaks]]).
- The SECOND genre: a synthetic house/techno build→drop MusicState sequence (BPM ~125–135, a `build`→`drop` phase transition + a high-band LAYER_ARRIVAL jump) — drive it through the same detector and assert the drop fires. Two genres, both automated.

**Cooldown-tuning surface (LIVE-03):** the values live in `vibemix/audio/constants.py` (`MIN_EVENT_GAP_PER_TYPE`, `EVENT_GLOBAL_MIN_GAP`, `HEARTBEAT_SEC`) — all module-level, test-pinned, one-line editable. The `--print-cooldowns` harness mode is the data-driven tuning instrument: run it over a real trace, read the measured-vs-locked deltas, adjust a constant if a drop is landing late. The plan pins a test that asserts the trace-replay measured gaps stay within tolerance of the locked values (so a tuning change is deliberate + visible), and documents the `--print-cooldowns` recipe in the live-drive doc.

---

## Question 4 — UI hint: yes. What is the Phase 54 UI surface, and is a UI-SPEC warranted?

**Answer: a THIN additive surface — a hype-mode-active indicator + reaction-cadence pulse on the existing live session UI. The live cohost-reaction stream + citation strip ALREADY exist (`SessionCohostReaction`, debrief timeline, `tokens.css` chip styling). A focused UI-SPEC is warranted to lock the mode-indicator visuals against the frontend-enforcement skill — but it must be SMALL (no rebuild of the reaction stream).**

What exists (verified live):
- `tauri/ui/src/session/{SessionLayout,ws-bridge,state}.ts` — the live session UI + ws bridge. `SessionCohostReaction` (the reaction-with-citation-strip envelope) is already published by `dj_cohost.py` and consumed by the UI; `tokens.css:260` documents the `[<verb> @ <mm:ss>]` chip render.
- `mocks/vibemix-app-ui.html` — the live-session UI design contract. It has an `interaction` rocker (`role="radiogroup"`, lines 1191-1193) with a `hype` option (`<span class="led"></span> hype`) and a `cohost-panel` with a status LED + foot. The mode indicator is already in the design vocabulary.
- `mocks/vibemix-direction-final.html` — the locked palette: amber accent (`--amber #ff8a3d`, intensities `--amber-22/40/65`), anodised charcoal dominant, phosphor glow tokens. This is the `frontend-enforcement` baseline ([[project_visual_direction_cdj_whisper]]).

**UI-SPEC decision: YES, create `54-UI-SPEC.md` — scoped to the hype-mode indicator only.** The surface is: (1) a clear "HYPE MODE · LIVE" indicator (the active interaction mode is unambiguous on screen), and (2) a reaction-cadence pulse — a subtle amber LED/glow that pulses each time a hype reaction lands, giving the "cadence feels alive" Success-Criterion-4 a visible heartbeat. It reuses the existing `SessionCohostReaction` event (no new wire field strictly required — the pulse keys off reaction arrivals already on the bus) and the existing amber/charcoal tokens. It does NOT touch the reaction-stream renderer, the citation strip, or the mascot (Phase 56). The UI-SPEC exists to hold the 20/80 rule + retro-futurist hardware vocabulary on the new indicator and to keep it from becoming AI slop.

---

## Validation Architecture

> Required section — drives `54-VALIDATION.md` (Nyquist). All commands runnable from repo root.

### Test framework
- **pytest** (`pyproject.toml [tool.pytest.ini_options]`, `addopts` includes `--strict-markers`).
- Quick run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <files>` (or `uv run pytest -q <files>`).
- Full suite: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`.
- Opt-in markers used here: `macos_audio` (real BlackHole live drive — Kaan-action). Frontend: `npm test` (vitest) under `tauri/ui/` for the indicator unit test.

### What is automatable (engineering, default + opt-in suites)
| Behavior | Requirement | Test type | Command |
|---|---|---|---|
| Trace-replay: real captured ground-truth drop/build events fire matching Event types within in-bar tolerance, respecting per-type cooldowns (genre 1) | LIVE-01 | unit (clock-patched detector replay) | `pytest -q tests/state/test_hype_trace_replay.py` |
| Trace-replay: synthetic house/techno build→drop sequence fires the drop Event (genre 2 → ≥2 genres) | LIVE-01 | unit | `pytest -q tests/state/test_hype_trace_replay.py` |
| Cooldown respect: consecutive same-type events inside `MIN_EVENT_GAP_PER_TYPE` do NOT double-fire; measured gaps stay within tolerance of locked values | LIVE-03 | unit | `pytest -q tests/state/test_hype_cooldown_grounding.py` |
| In-bar tolerance constant exists + is one-line editable; pinned by a test that reads it | LIVE-03 | unit | `pytest -q tests/state/test_hype_cooldown_grounding.py` |
| Anti-slop floor (detector): empty/silent/weak-evidence MusicState → `detect()` returns None (no Event → no fire) | LIVE-01 | unit | `pytest -q tests/state/test_hype_anti_slop.py` |
| Anti-slop spine (emit gate): a reaction citing an event NOT in an empty EvidenceRegistry snapshot → `CitationLinter.check(...).valid is False` (→ strip → no voice) | LIVE-01 | unit (REAL registry + linter, no network) | `pytest -q tests/state/test_hype_anti_slop.py` |
| HYPE persona cell selected for (hype, intermediate/beginner/pro) — reaction is built from the hype matrix, grounded in `evidence_line` | LIVE-01 | unit | `pytest -q tests/agent/test_hype_prompt_grounding.py` |
| `--print-cooldowns` harness runs over the captured trace fixture and reports per-type deltas (tuning instrument) | LIVE-03 | unit/cli | `pytest -q tests/eval/test_replay_harness_cooldowns.py` |
| Hype-mode indicator + reaction-cadence pulse renders/updates on reaction arrival (UI) | LIVE-01 (SC4 surface) | unit (vitest) | `cd tauri/ui && npm test -- hype-mode-indicator` |
| Full default suite still green (no golden-equivalence regression) | all | suite | `PYTHONPATH=src python3 -m pytest -q` |

### What is manual / Kaan-action (real hardware — autonomous carveout)
| Behavior | Requirement | Why manual | Instructions |
|---|---|---|---|
| Hype mode feels alive across ≥2 genres, in-bar, no slop — reactions land on real drops, like a friend not a script | LIVE-01 (SC2/SC4) | needs his library + his ear (the hard quality gate per CLAUDE.md + [[project_phase_16_kaan_dj_testing]]) | `VIBEMIX_MODE=hype uv run python -m vibemix`; play ≥2 genres into BlackHole 2ch; listen — do reactions land in-bar on real drops, across genres, no scripted/late/fake lines? |
| Cooldown/latency final tuning pass after the live drive | LIVE-03 | needs his ear on real cadence | Run `python -m scripts.eval.replay_harness --corpus recordings --print-cooldowns` to see measured-vs-locked gaps; if a drop lands late, edit the one constant in `vibemix/audio/constants.py` + restart ([[feedback_no_gsd_orchestra_for_trivial_tweaks]]). |

### Sampling rate
- After every task commit: run that task's quick command.
- After every wave: run the full default suite.
- Before verify: full default suite green; the `macos_audio` live drive is Kaan-action and recorded as deferred.

---

## Pitfalls (verified, must respect)
1. **Do NOT rebuild the reaction machinery.** EventDetector, cooldowns, the HYPE_* matrix, coach_loop, EvidenceRegistry, CitationLinter all ship at HEAD. Harden + tune only.
2. **The "32s-silent-on-drop" bug is HISTORICAL.** The real trace proves 52/52 fires, 0 suppressions. Frame LIVE-01 as "fires reliably + grounded", not "fix the silent voice".
3. **Do NOT depend on the empty `eval/corpus/sessions/*` WAVs** — they are placeholders pending Kaan-action corpus acquisition (no audio). Build trace-replay on the real captured `recordings/20260515-112139/events.jsonl` ground-truth (checked-in fixture copy) + a synthetic second-genre sequence.
4. **Do NOT reintroduce `phase=` into `evidence_line`** (`coach.py:14-18, 85-86`) — it primes the AI to invent drops. Load-bearing anti-hallucination invariant.
5. **Do NOT touch the v4-tuned cooldown VALUES casually.** Any change must be data-driven from a real-trace `--print-cooldowns` delta and pinned by a test. Keep them one-line editable in `constants.py` (no orchestra for a constant tweak — [[feedback_no_gsd_orchestra_for_trivial_tweaks]]).
6. **Do NOT touch Kaan's WIP files** — `tauri/src-tauri/src/mascot_window.rs` and `tauri/src-tauri/tauri.conf.json5` are uncommitted; stage only planning + new test/UI files this phase creates.
7. **Citation linter strip = silence, by design.** When pinning anti-slop, assert `LintResult.valid is False` on unbacked citations — do NOT "fix" the strip to emit; silence > invented citation is the spine.
8. **UI-SPEC stays SMALL** — mode indicator + cadence pulse only. The reaction stream + citation strip already exist; the mascot is Phase 56. 20/80 rule + retro-futurist hardware vocabulary per `frontend-enforcement` / `mocks/vibemix-direction-final.html`.
9. **gemini-3.5-flash + max_output_tokens=1024 are Kaan WIP** (`dj_cohost.py:417/683`, `agent/config.py`/router) — the plan must not regress these; they are the most likely fix for the historical dead window (220-cap truncation).

---

## RESEARCH COMPLETE
