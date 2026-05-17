---
phase: 43-visual-ship-lock
plan: 09
subsystem: ops
tags: [launch-prep, hero-demo, demo-mode, francesco-discharge, vis-09, kaan-action-legal, capture-day, runtime]

# Dependency graph
requires:
  - phase: 43-visual-ship-lock
    provides: "Plan 43-05 §VIS-04 runbook canonical format (KAAN-ACTION-LEGAL.md); Plan 43-08 8-cut storyboard + scripts/launch/check_cut_count.py gate"
provides:
  - "docs/launch-prep/ handoff package (4 docs) — Francesco's complete pre-production reference"
  - "src/vibemix/runtime/demo_mode.py — deterministic 30-event sequencer (track_start @ 0:00, kick_swap @ 2:33, layer_drop @ 4:50, track_end @ 6:00)"
  - "tests/runtime/test_demo_mode_sequence.py — 10 pytest pins locking anchor timestamps + sequence length + API surface"
  - "KAAN-ACTION-LEGAL.md §VIS-09 — Francesco capture day discharge runbook (canonical format, dual sign-off)"
affects: ["Phase 44 (Launch Pre-stage; README hero demo.mp4)", "Phase 45 (External Discharge; social-publish demo cuts)", "Francesco capture day (post-Phase 43, runbook discharge)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Demo-mode pattern: module-level invariant asserts + frozen tuple sequence + module-singleton cursor state for bit-identical playback across repeated runs"
    - "Discharge runbook pattern: dual sign-off (Francesco + Kaan) for shared-discharge gates (vs. §VIS-04 solo Kaan sign-off precedent)"

key-files:
  created:
    - "src/vibemix/runtime/demo_mode.py"
    - "tests/runtime/test_demo_mode_sequence.py"
    - "docs/launch-prep/SHOT-LIST.md"
    - "docs/launch-prep/AUDIO-CAPTURE.md"
    - "docs/launch-prep/DEMO-MODE-CONFIG.md"
    - "docs/launch-prep/README.md"
  modified:
    - "KAAN-ACTION-LEGAL.md"

key-decisions:
  - "Step-index-driven sequencer (not wall-clock-driven): step() returns the next event regardless of real-time elapsed; simpler test pinning + works in test environments without a real audio clock"
  - "Module-singleton cursor state (not per-call factory): matches the single-process single-event-loop runtime; load_sequence() resets + returns the same _state instance for diagnostic inspection"
  - "Filler events left unpinned in the test suite: only the 4 anchors (track_start, kick_swap, layer_drop, track_end) are load-bearing per CONTEXT — filler timings can be tuned without breaking the demo"
  - "Dual sign-off block (Francesco + Kaan) on §VIS-09 vs. §VIS-04 solo Kaan: capture-day is shared discharge — Francesco owns logistics + craft, Kaan owns aesthetic gate (Pioneer-CDJ headbob feel + CDJ Whisper palette)"

patterns-established:
  - "Deterministic sequencer with invariant asserts at import time (T-43-09-01 tamper-detect): both module-level assert + pytest pins guarantee the anchors cannot drift without CI catching it"
  - "Inert-by-default safety on demo-mode (T-43-09-02): module loads but does nothing until explicit load_sequence()/step() — shipping the wheel with demo_mode.py present has zero behavioural impact unless --demo-mode CLI flag invokes it"
  - "1-to-1 storyboard-to-shot-list derivation: 8 data-cut frames in mocks/vibemix-cinematic-storyboard.html → 8 numbered rows in docs/launch-prep/SHOT-LIST.md; parity enforced by `grep -cE '^\| [1-8] \|'` checks alongside check_cut_count.py"

requirements-completed: [VIS-09]

# Metrics
duration: 8min
completed: 2026-05-16
---

# Phase 43 Plan 09: Francesco pre-production handoff package + §VIS-09 discharge runbook Summary

**Deterministic 30-event demo-mode sequencer (anchored at 2:33 kick_swap / 4:50 layer_drop / 6:00 track_end) + 4-doc launch-prep handoff package + canonical §VIS-09 Francesco discharge runbook — engineering side of the hero-demo capture day complete.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-16T17:04:54Z
- **Completed:** 2026-05-16T17:12:29Z
- **Tasks:** 3
- **Files created:** 6
- **Files modified:** 1

## Accomplishments

- **Demo-mode sequencer (`src/vibemix/runtime/demo_mode.py`):** 30-event frozen-tuple `DEMO_SEQUENCE` with module-level invariant asserts pinning the 4 anchors (track_start @ 0:00, kick_swap @ 2:33, layer_drop @ 4:50, track_end @ 6:00). Public API `load_sequence` / `step` / `reset` per CONTEXT spec. Inert-by-default — module only mutates state when explicitly invoked, so shipping it in the wheel is zero-risk.
- **Pytest pins (`tests/runtime/test_demo_mode_sequence.py`):** 10/10 green, locking sequence length + anchor timestamps + monotonic invariant + API contract + exhaustion semantics (31st step() returns `None` sentinel, not `StopIteration`) + reset behaviour.
- **Launch-prep handoff package (`docs/launch-prep/`):**
  - `SHOT-LIST.md` — 8-cut sequenced shot list with per-cut timing budget + B-roll suggestions; Pioneer-CDJ-headbob aesthetic gate surfaced on Cut 7.
  - `AUDIO-CAPTURE.md` — 3-track capture plan (Gemini voice + ambient + headphone return); clapboard sync; vibemix's `session.wav` called out as canonical reference mix; full AV spec table.
  - `DEMO-MODE-CONFIG.md` — `--demo-mode` CLI spec; 30-event anchor table; storyboard cut↔anchor cross-mapping; threat-model surface.
  - `README.md` — index for all three docs + cross-refs to the sequencer / storyboard / §VIS-09 runbook; surfaces the 3 non-negotiable aesthetic gates.
- **§VIS-09 discharge runbook (`KAAN-ACTION-LEGAL.md`):** canonical format matching §VIS-04 / §GATE-* precedent; dual sign-off block (Francesco + Kaan); verification suite includes pre-shoot pytest pins, cut-count parity, ffprobe AV spec check, no-regression runtime suite.
- **No regression:** full `tests/runtime/` suite stays at 157/157 green.

## Task Commits

1. **Task 1 RED: Failing demo-mode sequencer pins (10 tests)** — `ade4f31` (test)
2. **Task 1 GREEN: Implement demo-mode deterministic 30-event sequencer** — `81393c4` (feat)
3. **Task 2: Add Francesco capture-day handoff package (3 docs + index)** — `3cd9fa7` (docs)
4. **Task 3: Append §VIS-09 Francesco capture day discharge runbook** — `1a26815` (docs)

## Files Created/Modified

**Created:**
- `src/vibemix/runtime/demo_mode.py` — 30-event deterministic sequencer with module-level invariant asserts + module-singleton cursor; public surface load_sequence/step/reset.
- `tests/runtime/test_demo_mode_sequence.py` — 10 pytest pins (sequence length, 3 anchor events, monotonic invariant, full API surface, exhaustion sentinel, reset behaviour, anchor ordering during traversal).
- `docs/launch-prep/SHOT-LIST.md` — 8-cut shot list (1-to-1 from `mocks/vibemix-cinematic-storyboard.html`).
- `docs/launch-prep/AUDIO-CAPTURE.md` — 3-track capture plan + clapboard sync + take workflow + post alignment recipe + AV spec table.
- `docs/launch-prep/DEMO-MODE-CONFIG.md` — `--demo-mode` CLI doc + 30-event sequence anchor table + threat model.
- `docs/launch-prep/README.md` — handoff package index + 3 aesthetic gates + handoff status checklist.

**Modified:**
- `KAAN-ACTION-LEGAL.md` — appended new `## §VIS-09 — Francesco capture day discharge` section (97 lines) in canonical format.

## Decisions Made

- **Step-index-driven sequencer** (vs. wall-clock-driven): the runtime hook eventually dispatches each event based on a real-time scheduler, but the `step()` API itself is index-driven. This means tests run without an audio clock, and the deterministic ordering is the load-bearing contract — not the wall-clock pacing (which is the dispatcher's job, layered separately on top of demo-mode in v1.x runtime).
- **Module-singleton cursor state**: `_state` is a module-level singleton because the vibemix runtime is single-process single-event-loop. `load_sequence()` returns the same instance for diagnostic inspection; mutation goes through `step()` / `reset()`. Per-call factory pattern was rejected — it would create state divergence between the test fixture and the real runtime caller.
- **Filler timestamps unpinned**: CONTEXT calls them "filler events to give the demo natural texture" — pinning them would over-constrain future tuning. Only the 4 anchors (track_start at index 0, kick_swap @ 153.0s, layer_drop @ 290.0s, track_end @ 360.0s) are pytest-locked.
- **Dual sign-off block on §VIS-09**: §VIS-04 has solo Kaan sign-off because Mixamo discharge is solo Kaan work. §VIS-09 is shared discharge — Francesco owns capture day logistics + craft, Kaan owns the qualitative aesthetic gate (Pioneer-CDJ headbob, CDJ Whisper palette). Dual signature line reflects that.
- **`None` sentinel on exhaustion** (vs. `StopIteration`): simpler error semantics for the dispatcher loop calling `step()` per tick; the test pins this behaviour explicitly (Test 8) so it cannot regress.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test import path corrected from `src.vibemix.runtime.demo_mode` to `vibemix.runtime.demo_mode`**
- **Found during:** Task 1 (Test authoring)
- **Issue:** Plan 43-09's sample Test 1 listed the import as `from src.vibemix.runtime.demo_mode import ...`. The actual project convention (and every existing test in `tests/runtime/`, e.g. `test_diag.py:13`) imports from the wheel-installed package root `vibemix.*`. `pyproject.toml` declares `[tool.hatch.build.targets.wheel] packages = ["src/vibemix"]` — the `src/` prefix is a layout convention, not part of the import path. Using `src.vibemix.*` would have failed import in the installed-wheel test environment.
- **Fix:** All test imports use `from vibemix.runtime.demo_mode import ...` (matches `tests/runtime/test_diag.py` + `tests/runtime/conftest.py` precedent). A comment in the test module documents the deviation for future maintainers.
- **Files modified:** `tests/runtime/test_demo_mode_sequence.py`
- **Verification:** Test suite collected without `ModuleNotFoundError`; 10/10 pins green via `uv run pytest tests/runtime/test_demo_mode_sequence.py -q`.
- **Committed in:** `ade4f31` (Task 1 RED commit)

**2. [Rule 2 - Missing Critical] Added module-level invariant asserts on DEMO_SEQUENCE anchors (T-43-09-01 tamper-detect mitigation)**
- **Found during:** Task 1 (sequencer implementation)
- **Issue:** Plan called out one assert (`len(DEMO_SEQUENCE) == 30`). The threat model lists T-43-09-01 (Tampering with DEMO_SEQUENCE timestamps) with disposition `mitigate`. A single length assert leaves the kick_swap / layer_drop / track_end anchors unguarded at import time — pytest catches it but only in test environment. Adding the additional anchor-position asserts at import time means a tampered sequence fails the import itself in production, before any demo-mode tick runs.
- **Fix:** Added 4 module-level asserts at import time: sequence length == 30, monotonic timestamp ordering, kick_swap anchor present at 153.0s, layer_drop anchor present at 290.0s, last event is track_end at 360.0s.
- **Files modified:** `src/vibemix/runtime/demo_mode.py`
- **Verification:** Asserts execute on every import; pytest run exercises them; tampering with any anchor in the source raises `AssertionError` at module load.
- **Committed in:** `81393c4` (Task 1 GREEN commit)

**3. [Rule 2 - Missing Critical] Added explicit `CDJ WHISPER PALETTE OK` line to §VIS-09 sign-off block**
- **Found during:** Task 3 (runbook authoring)
- **Issue:** Plan's sample sign-off block listed `PIONEER-HEADBOB FEEL OK` as the only aesthetic gate. CONTEXT §VIS-08 also locks "CDJ Whisper v5 vocab" + amber-only chip overlays. The §VIS-09 final cut review needs both gates explicit on the sign-off block — one is mascot motion craft, the other is palette compliance.
- **Fix:** Added `VIS-09 CDJ WHISPER PALETTE OK: _____________________ (yes / no — 5 warm blacks + single amber)` line to the sign-off block.
- **Files modified:** `KAAN-ACTION-LEGAL.md`
- **Verification:** Section renders correctly; both aesthetic gates now explicit; sign-off block matches the 3 "aesthetic gates" in `docs/launch-prep/README.md`.
- **Committed in:** `1a26815` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 bug — import path; 2 missing-critical — invariant asserts + palette sign-off line)
**Impact on plan:** All 3 deviations are corrections to plan boilerplate, not scope changes. Net effect is tighter tamper-detect + tighter aesthetic-gate documentation. No drift from the §VIS-09 deliverables.

## Issues Encountered

None — all 3 tasks executed in order; RED → GREEN cycle clean; verification block passed first try; full `tests/runtime/` suite stayed green at 157 tests throughout.

## User Setup Required

None — no external service configuration needed. The post-Phase-43 Francesco discharge (capture day) is tracked in `KAAN-ACTION-LEGAL.md §VIS-09`, not in user-setup terms.

## Next Phase Readiness

- **Phase 44 (Launch Pre-stage)** can now reference `docs/launch-prep/` + the eventual `demo.mp4` master output of §VIS-09 discharge. README hero artefact path is unblocked from the engineering side.
- **Phase 45 (External Discharge)** social cuts derive from the same master; engineering side is unblocked.
- **Francesco discharge:** the §VIS-09 runbook is review-ready; pre-production review with Kaan + Francesco can be scheduled whenever booth + camera availability aligns.
- **Demo-mode sequencer ready for runtime dispatcher wiring:** when the live `--demo-mode` CLI flag wiring lands in the runtime entrypoint (deferred / not in Phase 43 scope per CONTEXT split), the sequencer API surface `load_sequence` / `step` / `reset` is stable and contract-tested.

## Self-Check

**Files claimed:**
- `src/vibemix/runtime/demo_mode.py` — FOUND
- `tests/runtime/test_demo_mode_sequence.py` — FOUND
- `docs/launch-prep/SHOT-LIST.md` — FOUND
- `docs/launch-prep/AUDIO-CAPTURE.md` — FOUND
- `docs/launch-prep/DEMO-MODE-CONFIG.md` — FOUND
- `docs/launch-prep/README.md` — FOUND
- `KAAN-ACTION-LEGAL.md §VIS-09` — FOUND (section header at line 1270)

**Commits claimed:**
- `ade4f31` (test RED) — FOUND
- `81393c4` (feat GREEN) — FOUND
- `3cd9fa7` (docs handoff) — FOUND
- `1a26815` (docs runbook) — FOUND

## Self-Check: PASSED

---
*Phase: 43-visual-ship-lock*
*Plan: 09*
*Completed: 2026-05-16*
