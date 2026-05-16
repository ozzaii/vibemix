---
phase: 41-gemini-sku-upgrade-latency-stack-v2
plan: 06
subsystem: llm
tags: [spike, gemini-live, kaan-action, lat-09]
dependency-graph:
  requires: [41-01]
  provides: [LAT-09 scaffolding]
  affects: []
tech-stack:
  added: []
  patterns: ["spike entry point", "kaan-action discharge", "verdict template"]
key-files:
  created:
    - spikes/__init__.py
    - spikes/scripts/__init__.py
    - spikes/scripts/recording_harness.py
    - spikes/scripts/run_live_spike.py
    - spikes/gemini-3-1-flash-live-music.md
    - spikes/recordings/.gitkeep
    - tests/repo/test_live_spike_scaffold.py
  modified:
    - .planning/KAAN-ACTION-PROXY.md
decisions:
  - "Append §LAT-09 to existing .planning/KAAN-ACTION-PROXY.md instead of creating a new repo-root KAAN-ACTION-PROXY.md — single canonical discharge surface; Phase 29 entries set the precedent"
  - "Spike entry point is audio-only (no MIDI / screen / nowplaying) per RESEARCH-recommended minimum to isolate Live's audio grounding signal"
  - "Verdict template Status field is a 3-state machine: engineering-scaffolded → kaan-action-discharge → verdict-written"
  - "Spike model literal lives ONLY in spikes/scripts/run_live_spike.py — Plan 41-01 grep gate scopes to src/vibemix/ so spikes/ is naturally excluded; redundant pytest assertion (test_live_model_id_NOT_in_src_vibemix) is positive defense against future accidental promotion"
metrics:
  duration: ~30 min
  completed: 2026-05-16
  tasks_total: 4
  tasks_completed: 4
  files_created: 7
  files_modified: 1
  loc_total: 700
---

# Phase 41 Plan 41-06: Gemini 3.1 Flash Live spike framework + KAAN-ACTION discharge runbook Summary

**One-liner:** Engineering scaffold for the Gemini 3.1 Flash Live music spike — verdict template + clean-port runner from `cohost_lk.py:1670+` + audio recording harness + Kaan-action discharge runbook. Real-DJ-clip investigation deferred per `gsd-autonomous fully` mode.

## What Shipped

| Artifact | LOC | Provides |
|---|---|---|
| `spikes/gemini-3-1-flash-live-music.md` | 107 | Verdict template with 6 H2 sections + Status state machine + Sign-off block. Status starts at `engineering-scaffolded`. |
| `spikes/scripts/run_live_spike.py` | 304 | Runnable Python entry point: opens Gemini 3.1 Flash Live `RealtimeModel` with music-tolerant VAD (`START_SENSITIVITY_LOW` + `END_SENSITIVITY_LOW`) + `proactivity=True`, captures output via `RecordingHarness`, writes `spike_<UTC-timestamp>.wav` + `.metrics.json`. Smoke-import path returns 0 without `GEMINI_API_KEY`. |
| `spikes/scripts/recording_harness.py` | 91 | `RecordingHarness` — stdlib-only wav writer (16-bit PCM mono @ 24kHz). Context-manager and frame-count instrumentation. |
| `spikes/__init__.py` + `spikes/scripts/__init__.py` + `spikes/recordings/.gitkeep` | 3 | Package markers + sink dir scaffold. `.gitkeep` force-added through the `recordings/` gitignore rule. |
| `.planning/KAAN-ACTION-PROXY.md §LAT-09` | +53 | Discharge runbook: env setup → 5-min representative clip → `python -m spikes.scripts.run_live_spike --duration-s 300` → offline listen → fill verdict → flip status. Expected time 1-2h. |
| `tests/repo/test_live_spike_scaffold.py` | 198 | 9 sanity tests — file existence, section structure, import cleanness, CLI behavior, runbook alignment, CI gate boundary (spike literal allowed in `spikes/`, banned in `src/vibemix/`). |

**Total:** 700 LOC across 7 created + 1 modified file. 4/4 tasks complete. 4 commits.

## Architectural Shape Mapping (cohost_lk.py:1670+ → run_live_spike.py)

Clean port — no import from `cohost_lk.py` (READ-ONLY per Phase 37-06 immutability gate). Architecture lifted, code rewritten to current SDK conventions:

| cohost_lk.py:1670+ element | run_live_spike.py port |
|---|---|
| `RealtimeModel(model=MODEL, voice=VOICE, api_key=..., modalities=[AUDIO], output_audio_transcription=...)` | Identical kwarg shape; `model=SPIKE_MODEL_ID`, `voice=SPIKE_VOICE`. |
| No explicit `realtime_input_config` (POC relied on default VAD) | Explicit music-tolerant `RealtimeInputConfig(automaticActivityDetection=AutomaticActivityDetection(startOfSpeechSensitivity=START_SENSITIVITY_LOW, endOfSpeechSensitivity=END_SENSITIVITY_LOW))` — the "low" sensitivity per CONTEXT.md is the load-bearing music-tolerance setting. |
| No Proactive Audio (Gemini 2.5 baseline didn't have it) | `proactivity=True` — the v3.1 Live new mode under test. |
| Levels / AudioBuffer / MicBuffer / PassthroughBuffer / PlaybackQueue + ScreenBuffer + TrackInfo + ControllerState | DROPPED — spike v1 is audio-only minimum-viable. Operator-tuned plumbing adapters on first real run. |
| `start_input_to_session(...)` + `consume_response(...)` (full audio I/O pipeline) | Placeholder comment block; minimum-viable spike measures session-open → first-output-audio TTFT and runs for `--duration-s`. Real-run plumbing adapters tuned on first discharge attempt. |
| `trigger_loop(...)` + manual trigger event | DROPPED — Proactive Audio replaces the heuristic trigger; that's the test. |
| MIDI listener daemon thread, ws_broadcast, diag_loop, track_poll_loop | DROPPED — out of scope for grounding/latency observation. |
| `session.aclose() + model.aclose()` cleanup | Preserved verbatim, wrapped in best-effort try/except + metrics-error capture. |

## Open Question for Operator (Discharge Phase)

The script verified against installed `livekit-plugins-google` v1.5.8 at scaffold time (constructor signature inspected — `proactivity` and `realtime_input_config` are real kwargs; `StartSensitivity` / `EndSensitivity` enums exist with `_LOW` variants). However:

- **Output audio capture wiring:** the v1.5.8 plugin's exact event/property surface for streaming output audio out of `model.session()` was NOT exercised in the scaffold (the spike v1 measures session-open / first-chunk timing only; full audio plumbing is operator-tuned on first real run). `OPERATOR_NOTES` in `run_live_spike.py` flags this.
- **Sample rate confirmation:** spike defaults to 24kHz output (matches Gemini Live observed format). Operator confirms or adjusts `SAMPLE_RATE_OUT` constant on first real run.
- **15-min session cap:** noted in `OPERATOR_NOTES` and the verdict template's `Session Cap Workaround Status` section. Not stressed in scaffold (default duration 60s).

These are all `OPERATOR NOTE:` comments in the script — none block the scaffold landing.

## POC Immutability Gate Status (Phase 37-06)

`cohost_lk.py` untouched. Verified via:

```
$ uv run pytest tests/repo/test_g5_poc_files_untouched.py -x
... 7 passed ...
```

The clean-port discipline held: zero imports from `cohost_lk`, zero edits to the POC file.

## CI Gate Status

- **Plan 41-01 grep gate** (`scripts/release/check_no_hardcoded_model.sh`): clean. Scope is `src/vibemix/` only; `spikes/` is naturally out of scope, so the live model literal in `spikes/scripts/run_live_spike.py` does NOT trip it.
- **Plan 41-06 pytest gate** (`tests/repo/test_live_spike_scaffold.py`): 9/9 green. Includes positive-defense assertion `test_live_model_id_NOT_in_src_vibemix` that mirrors the grep gate for this specific literal.
- **POC immutability gate** (`tests/repo/test_g5_poc_files_untouched.py`): 7/7 green.

Combined verification: **26/26 tests pass** across the three relevant gate suites.

## Decisions Made

1. **KAAN-ACTION-PROXY destination:** Appended to existing `.planning/KAAN-ACTION-PROXY.md` instead of creating a new repo-root `KAAN-ACTION-PROXY.md` as the plan body literally specified. Reason: single canonical surface (Phase 29 set the precedent with A5-VOICE-LISTEN / A7-PROXY entries living in `.planning/KAAN-ACTION-PROXY.md`). Forking the surface would silently bifurcate the discharge index. The plan verify command's hardcoded `/Users/ozai/projects/dj-set-ai/KAAN-ACTION-PROXY.md` path was treated as an oversight in the plan, not a contract. Task 4's test (`test_kaan_action_proxy_has_lat09`) points to `.planning/KAAN-ACTION-PROXY.md` to match reality.

2. **Audio-only spike (no MIDI / screen / nowplaying):** Per CONTEXT.md "1-2 day spike" framing and the goal of isolating Live's grounding signal — bringing the full v4 evidence stack into the spike would muddy what the spike is testing (is Live good or did MIDI save it?). Operator can re-add later if Phase 41 wants a "Live + full evidence" follow-up spike.

3. **Smoke-import path returns 0 without `GEMINI_API_KEY`:** Lets CI sanity tests verify the script imports + the CLI renders without spending API quota. Operator gets a clear hint pointing to `.planning/KAAN-ACTION-PROXY.md §LAT-09` if they run without setting the env var. Plan task body explicitly called for this pattern.

4. **VAD sensitivity:** `LOW` for both start and end of speech, matching the "music-tolerant" spec from CONTEXT.md / RESEARCH. The Gemini Live default is `UNSPECIFIED` which the API resolves to a value tuned for typical voice input, not music backdrop.

## Deviations from Plan

### [Rule 2 — Surface consolidation] Append §LAT-09 to `.planning/KAAN-ACTION-PROXY.md` instead of creating repo-root `KAAN-ACTION-PROXY.md`
- **Found during:** Task 3 (initial check `test -f KAAN-ACTION-PROXY.md` returned missing at root, but `.planning/KAAN-ACTION-PROXY.md` existed with Phase 29 entries)
- **Issue:** Plan frontmatter `files_modified` listed `KAAN-ACTION-PROXY.md` (root); existing canonical surface lives at `.planning/KAAN-ACTION-PROXY.md`. Creating a second top-level file would silently fork the discharge index — operator would discover only half of pending items.
- **Fix:** Appended §LAT-09 to the existing planning-tier file; adjusted Task 4's `test_kaan_action_proxy_has_lat09` to point at the real path.
- **Files modified:** `.planning/KAAN-ACTION-PROXY.md`, `tests/repo/test_live_spike_scaffold.py`
- **Commit:** `87723c5`

### [Rule 3 — Blocking issue] `.gitignore recordings/` blocked spike output sink dir scaffold
- **Found during:** Task 1 (git add `spikes/recordings/.gitkeep` failed with "paths are ignored")
- **Issue:** `.gitignore:68` has a generic `recordings/` rule for vibemix session recordings.
- **Fix:** Force-added the `.gitkeep` via `git add -f`. Did NOT modify `.gitignore` — the rule correctly protects user session audio elsewhere; force-adding the scaffold marker is the minimal change.
- **Files modified:** none (force-add only)
- **Commit:** `74ae281`

## Known Stubs

- `run_live_spike.py` lines under the `Audio I/O wiring placeholder` comment — TTFT measurement and full sounddevice→`session.push_audio` plumbing are placeholders. Resolution: operator wires these on first real discharge attempt per `OPERATOR_NOTES`. Documented in the runbook expected-time (1-2h) and in the verdict template's "Setup" section as `OPERATOR NOTE`. This is intentional — the plan ships engineering scaffolding only; real wiring requires real DJ source + real ear.

## Self-Check: PASSED

### Files
- spikes/__init__.py: FOUND
- spikes/scripts/__init__.py: FOUND
- spikes/scripts/recording_harness.py: FOUND
- spikes/scripts/run_live_spike.py: FOUND
- spikes/gemini-3-1-flash-live-music.md: FOUND
- spikes/recordings/.gitkeep: FOUND
- tests/repo/test_live_spike_scaffold.py: FOUND

### Commits
- 74ae281 (Task 1 — verdict template + recording harness): FOUND
- 90dbf1c (Task 2 — spike runner clean port): FOUND
- 87723c5 (Task 3 — KAAN-ACTION-PROXY §LAT-09): FOUND
- d15e9f6 (Task 4 — scaffold sanity tests): FOUND

### Test Suites
- tests/repo/test_live_spike_scaffold.py: 9/9 passed
- tests/repo/test_g5_poc_files_untouched.py: 7/7 passed (POC immutability)
- tests/repo/test_model_literal_gate.py: 10/10 passed (grep gate parity)
- scripts/release/check_no_hardcoded_model.sh: clean
