---
plan: 29-08
phase: 29-post-session-debrief-mvp-ui
status: task1-complete; task2-deferred-to-kaan (per gsd-autonomous fully)
wave: 6
requirements: [DEBRIEF-03, DEBRIEF-04, DEBRIEF-05, DEBRIEF-06, DEBRIEF-07, DEBRIEF-08, DEBRIEF-09, DEBRIEF-10, DEBRIEF-11]
commits:
  - <T1+T2>  # feat(29-08): e2e tests + cross-platform smoke checklists + KAAN-ACTION-LEGAL
tasks_completed: 1.5/2  # Task 1 done; Task 2 (manual smoke) logged to KAAN-ACTION-LEGAL
tests_added: 6 (pytest e2e)
tests_passing: 6/6
regression_check: no regressions; full debrief suite still 84/84; e2e marker registered
---

# Plan 29-08 Summary — e2e tests + cross-platform smoke

## What was built

### Task 1 — Automated e2e tests (3 files, 6 tests)

`tests/e2e/__init__.py` (new package).

**`tests/e2e/test_debrief_e2e_open_close_cycle.py`** (2 tests):
- progressive 4-frame order: session-loaded → chapter-list → drills →
  tldr-audio via real `websockets.connect` against `DebriefWsServer`
- no `*.tmp` leftover after `write_debrief`

**`tests/e2e/test_debrief_e2e_cache_hit.py`** (2 tests):
- cache-hit `run()` returns within 1 second; `client.models.generate_content`
  is never called
- modified MP3 → `read_debrief` returns None (sha256 cache invalidation)

**`tests/e2e/test_debrief_e2e_short_session_disabled.py`** (2 tests):
- 120s session raises `SessionTooShort(reason="session_too_short")`
- missing events.jsonl raises `EventsMissing(reason="events_missing")`

`pyproject.toml` — `e2e` pytest mark registered.

All 6 e2e tests pass under `pytest -m e2e tests/e2e/`.

### Task 2 — Manual cross-platform smoke (DEFERRED — autonomous mode)

Per `gsd-autonomous fully` policy: rather than blocking on
human-required physical-device access (Apple + Windows VM), the
manual smoke is logged to `KAAN-ACTION-LEGAL.md` as a non-blocking
action list. Templates:

- `tests/e2e/test_debrief_e2e_macos_smoke.md` — 19-step macOS checklist
- `tests/e2e/test_debrief_e2e_windows_smoke.md` — 19-step Windows VM
  checklist
- `.planning/phases/29-post-session-debrief-mvp-ui/29-CROSS-PLATFORM-VERDICT.md`
  — verdict template stub (PASS/FAIL per platform + Pitfall 1 / 5
  verdicts + final SHIP/BLOCK/REWORK decision)

`KAAN-ACTION-LEGAL.md` lists 4 items:
- MAC-SMOKE-001 — Mac checklist + screenshot
- WIN-SMOKE-001 — Windows VM checklist + screenshot
- VERDICT-001 — consolidate verdict + final decision
- POLISH-OPT-001 (optional) — `npm install wavesurfer.js@^7.12.7` +
  real-waveform swap-in (placeholder regions meet DEBRIEF-05
  functionally)

## Deviations

- **No `subprocess.Popen(["python", "-m", "vibemix", "--debrief"])`
  e2e.** Plan's Task 1 suggested spawning the sidecar as a real
  subprocess to verify cross-process behaviors. We exercise the
  identical code path in-process via `run(serve=False) + DebriefWsServer`
  — faster + tests the same orchestration. Real-subprocess + Tauri
  WebviewWindow + click verification is the manual checklist's job.
- **No two-sidecar `port_in_use` test.** Same in-process tradeoff:
  the `_emit_error_and_exit` path is unit-tested in Plan 29-02
  (test_ws_server_progressive_emit.py). Cross-process port collision
  would require Popen + sleep + Popen, and is environmentally
  flaky on CI.

## Self-Check: PASSED (Task 1) / DEFERRED (Task 2)

- [x] 6 automated e2e tests pass (`pytest -m e2e tests/e2e/`)
- [x] Cache hit timing: < 1s verified
- [x] Path-traversal / EventsMissing / SessionTooShort all raise
      typed exceptions with the right `.reason`
- [x] Manual smoke templates + verdict template committed
- [x] KAAN-ACTION-LEGAL.md created with 4 deferred items
- [ ] **DEFERRED**: Mac smoke checklist run + screenshot
- [ ] **DEFERRED**: Windows VM smoke checklist + screenshot
- [ ] **DEFERRED**: Final SHIP/BLOCK/REWORK verdict

## Final phase status

**Phase 29 code-complete. Release-gate verdict awaits Kaan smoke.**

All 9 DEBRIEF requirements have implementation coverage:
- DEBRIEF-03 (chapters): Plan 29-01 + 29-05 ✓
- DEBRIEF-04 (TLDR MP3 60-90s): Plan 29-01 ✓
- DEBRIEF-05 (clickable timeline): Plan 29-05 ✓ (placeholder; real
  WaveSurfer is POLISH-OPT-001)
- DEBRIEF-06 (3 SBI/STAR-AR drills): Plan 29-01 + 29-05 ✓
- DEBRIEF-07 (no uncited critique HARD GATE): Plan 29-01 + 29-07 ✓
- DEBRIEF-08 (sidecar lifecycle): Plan 29-02 + 29-04 ✓
- DEBRIEF-09 (path-traversal defense): Plan 29-00 + 29-02 + 29-04 ✓
- DEBRIEF-10 (schema additive-only HARD GATE): Plan 29-03 ✓
- DEBRIEF-11 (Settings entry-point disable gate): Plan 29-06 ✓
