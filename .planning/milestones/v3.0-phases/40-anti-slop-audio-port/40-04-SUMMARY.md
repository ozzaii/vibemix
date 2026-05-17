---
phase: 40-anti-slop-audio-port
plan: 04
subsystem: audio
tags: [cooldowns, event-detector, replay-harness, anti-slop, v4-baseline, audit-trail, observational-warning]
requires: [01]
provides:
  - HEARTBEAT_SEC=45.0
  - MIN_EVENT_GAP_PER_TYPE (re-tuned baseline entries)
  - --print-cooldowns flag on replay_harness
  - _emit_cooldown_report
  - _accumulate_session_gaps
  - COOLDOWN_REPORT_TOLERANCE_S=1.0
affects:
  - src/vibemix/audio/constants.py
  - src/vibemix/state/event_detector.py  # behavior change via constants
  - tests/audio/test_constants.py
  - tests/state/test_event_detector.py
  - tests/state/detectors/test_dsp_primitives.py
  - scripts/eval/replay_harness.py
tech_stack:
  added: []  # zero new pip deps — only stdlib (statistics, collections.defaultdict)
  patterns:
    - "audit-trail comments cite Plan id + old value + v4 chat-test date (2026-05-11) per RESEARCH §State of the Art"
    - "per-session last_per_type_at reset — cross-session boundaries don't synthesize fake 'gaps'"
    - "WARNING line uses strictly-greater comparison (delta == ±1.0 edge case is silent)"
    - "single-fire event types omitted from report (no inter-event gap to median)"
    - "observational-only — Phase 42 GATE-04 hardens into exit-non-zero CI gate post real-corpus baseline"
key_files:
  created:
    - tests/eval/test_replay_harness_cooldowns.py
  modified:
    - src/vibemix/audio/constants.py
    - tests/audio/test_constants.py
    - tests/state/test_event_detector.py
    - tests/state/detectors/test_dsp_primitives.py
    - scripts/eval/replay_harness.py
    - .planning/phases/40-anti-slop-audio-port/deferred-items.md
decisions:
  - "Locked target = v4 chat-tested 2026-05-11 baseline literal (10/10/14/45/5), NOT the v4 source file literal (18/16/20/70/6) — per RESEARCH §Key Findings and project memory project_v4_canonical_baseline"
  - "WARNING uses strict `> 1.0` (not `>= 1.0`) — measured-gap exactly at tolerance is locked-target-respecting, not drift"
  - "Per-session last_per_type_at reset between sessions inside _run — cross-session 'gap' would be wall-clock noise"
  - "Bootstrap zero-gap (first fire of each type in each session) skipped — would pollute median"
  - "Single-fire event types omit row entirely (cleaner report than '0.0 median' noise)"
  - "Stale-snapshot test (DEFERRED-40-01-03 / DEFERRED-40-02-01) closed naturally — expected set now includes DISTORTION_CLIMB + ACID_LINE_ENTRY from Phase 30 SENSE-17/18"
metrics:
  duration_minutes: 11
  completed_at: 2026-05-16
  tests_added: 8
  tests_modified: 4
  source_loc_added: 117
  source_loc_changed: 11
---

# Phase 40 Plan 04: Cooldown Re-tune + Replay-Harness `--print-cooldowns` Summary

Re-tune `MIN_EVENT_GAP_PER_TYPE` + `HEARTBEAT_SEC` from v3-era ship-cut values to the v4 chat-tested 2026-05-11 "harikaydı" baseline, closing the "AI didn't react when it should have" anti-slop class. Add additive `--print-cooldowns` observational mode to `scripts/eval/replay_harness.py` for empirical validation of locked values against real-corpus replays. Also closes the stale-snapshot test (DEFERRED-40-01-03 / DEFERRED-40-02-01) that had been failing on `main` since Phase 30 SENSE-17/18 landed without updating the expected-key set.

## Before / After Cooldown Table

| Constant                                 | OLD (v4-shipped-file) | NEW (v4-chat-tested 2026-05-11) | Source |
| ---------------------------------------- | --------------------: | ------------------------------: | ------ |
| `HEARTBEAT_SEC` (module-level)           |                  70.0 |                            45.0 | `src/vibemix/audio/constants.py:65` |
| `MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"]` |                   6.0 |                             5.0 | `:70` |
| `MIN_EVENT_GAP_PER_TYPE["PHASE"]`        |                  18.0 |                            10.0 | `:71` |
| `MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"]`|                  16.0 |                            10.0 | `:72` |
| `MIN_EVENT_GAP_PER_TYPE["MIX_MOVE"]`     |                  20.0 |                            14.0 | `:73` |
| `MIN_EVENT_GAP_PER_TYPE["HEARTBEAT"]`    |                  70.0 |    `HEARTBEAT_SEC` (= 45.0)     | `:74` |

**Unchanged** (Phase 17 SENSE-12 / Phase 30 SENSE-17/18 / baseline):
`MIC` (3.0), `MANUAL` (1.5), `KICK_SWAP` (14.0), `SUB_LAYER_ARRIVAL` (16.0), `KICK_DENSITY_SHIFT` (18.0), `BREAKDOWN_KICK_KILL` (20.0), `REENTRY_KICK_LAND` (12.0), `PHRASE_BOUNDARY` (24.0), `DISTORTION_CLIMB` (6.0), `ACID_LINE_ENTRY` (8.0).

## Test Pin Sites Updated

| File | Lines | What Changed |
| ---- | ----- | ------------ |
| `tests/audio/test_constants.py` | 47-61 | `test_engine_constants_match_v4` — `HEARTBEAT_SEC == 70.0` → `== 45.0` + docstring updated to cite Plan 40-04 |
| `tests/audio/test_constants.py` | 86-146 | `test_event_gap_dict_shape_and_values` — expected key set now includes `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` (closes DEFERRED-40-01-03 / DEFERRED-40-02-01); value pins updated for 5 re-tuned keys + audit comments + identity preservation for HEARTBEAT_SEC |
| `tests/state/test_event_detector.py` | 9-19 | Module docstring constants table updated to (5/10/10/14/45) + Plan 40-04 audit note |
| `tests/state/test_event_detector.py` | 273, 330 | 2 inline comment refs updated ("past 6s TRACK_CHANGE" → "past 5s TRACK_CHANGE"; "LAYER_ARRIVAL cooldown (16.0s)" → "(10.0s, Plan 40-04)"). Test wall-clock arithmetic (`t.return_value = 1200.0` / `1030.0`) was already comfortably past even the smaller new cooldowns; no numeric test logic broken. |
| `tests/state/detectors/test_dsp_primitives.py` | 101-107 | `test_min_event_gap_per_type_extended_with_three_kick_side_entries` — `TRACK_CHANGE == 6.0` → `== 5.0` and `LAYER_ARRIVAL == 16.0` → `== 10.0` (extra pin site outside the plan-spec list; T-40-04-01 mitigation found via grep audit) |

`tests/audio/test_phase17_constants.py` was inspected — it pins genre BPM bands + spectral-centroid floor only, no cooldown values. No edit needed.

## `--print-cooldowns` Surface

**CLI:**
```bash
python -m scripts.eval.replay_harness \
    --corpus tests/eval/fixtures \
    --judges noop \
    --output /tmp/eval-out \
    --print-cooldowns
```

**Module API:**

```python
COOLDOWN_REPORT_TOLERANCE_S: float = 1.0

def _emit_cooldown_report(measured_gaps: dict[str, list[float]]) -> None:
    """Per-type median + delta + WARNING report → stderr."""

def _accumulate_session_gaps(
    events: list[dict[str, Any]],
    measured_gaps: dict[str, list[float]],
    last_per_type_at: dict[str, float],
) -> None:
    """Walk sorted events; append inter-event gaps; skip bootstrap zero."""
```

**Output format (grep-able fixed-width, stderr):**

```
[cooldown-report] measured inter-event gaps:
  PHASE                    median_gap= 12.00s expected_min=10.00s delta= +2.00s
  WARNING: PHASE measured gap outside ±1.0s of locked value (10.00s)
  MIX_MOVE                 median_gap= 15.00s expected_min=14.00s delta= +1.00s
```

**Sample run against the fixture corpus (`tests/eval/fixtures`):**

```
$ PYTHONPATH=src python -m scripts.eval.replay_harness \
    --corpus tests/eval/fixtures --judges noop \
    --output /tmp/plan-40-04-eval --print-cooldowns 2>&1
[cooldown-report] no events recorded — empty accumulator
```

Expected — the synthetic_session fixture has 3 events of distinct types (`TRACK_CHANGE`, `PHRASE_BOUNDARY`, `MIX_MOVE`), so no inter-event gaps exist. The "no events recorded" marker is the documented empty-accumulator path. A real-corpus run (eval/corpus/sessions/*) will produce populated rows.

## Commits

| Step | Hash | Message |
| ---- | ---- | ------- |
| Task 1 RED | `c73219c` | `test(40-04): RED — pin updated cooldown values for v4 2026-05-11 baseline` |
| Task 1 GREEN | `7116d0d` | `feat(40-04): GREEN — re-tune cooldowns to v4 chat-tested 2026-05-11 baseline` |
| Task 2 RED | `14b3a60` | `test(40-04): RED — pin replay_harness --print-cooldowns observational contract` |
| Task 2 GREEN | `d46c703` | `feat(40-04): GREEN — --print-cooldowns observational mode in replay_harness` |

## Verification

- `pytest tests/audio/test_constants.py tests/audio/test_phase17_constants.py tests/state/test_event_detector.py tests/eval/test_replay_harness_cooldowns.py tests/eval/test_replay_harness.py` → **74 passed**.
- `pytest tests/audio/ tests/state/` → **559 passed, 1 skipped** (skipped = `test_genre_router_integration` indirect-coverage skip, unrelated).
- `pytest tests/eval/` → **104 passed, 1 failed**. The 1 failure is `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` — confirmed pre-existing (logged as DEFERRED-40-04-01); reproduces on `main` without Plan 40-04 changes.
- `python -m scripts.eval.replay_harness --help | grep -- "--print-cooldowns"` → present, with full help text.
- Manual `--print-cooldowns` against `tests/eval/fixtures` → emits the empty-accumulator marker; scorecard artifacts produced; exit code 0.
- POC immutability gate: `git status cohost_v4*.py cohost.py cohost_v2.py cohost_lk.py mascot.html` → clean (POC files are not tracked in this repo at all; worktree-status confirms no edits introduced).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test pin drift] Extra pin site in `tests/state/detectors/test_dsp_primitives.py`**
- **Found during:** Task 1 GREEN regression sweep (after source constants updated, `pytest tests/audio/ tests/state/` flagged this site).
- **Issue:** `test_min_event_gap_per_type_extended_with_three_kick_side_entries` (lines 105-106) pinned `MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"] == 6.0` and `MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"] == 16.0` — old values. Plan-spec named 3 known pin sites but the grep audit (T-40-04-01 mitigation) found a fourth.
- **Fix:** Updated to new values (5.0 / 10.0) with Plan 40-04 audit comments.
- **Commit:** Folded into `7116d0d` (Task 1 GREEN) per Rule 1 scope ("auto-fix bugs directly caused by current task's changes").

**No Rule 2 / Rule 3 / Rule 4 events.** Auth gates: none.

## Hallucination Class Closed

> "AI didn't react when it should have"

Old 18s `PHASE` cooldown could silently swallow 3 distinct phase shifts in a single 4-minute track. New 10s cooldown allows real moments through while still preventing back-to-back same-event noise (global 10s gate still enforces "let the music breathe"). 70s → 45s `HEARTBEAT_SEC` reduces silent-period drift — the AI won't go 70s without a heartbeat reaction during a flat groove.

## Open / Follow-on

- **Phase 42 GATE-04** will harden the `--print-cooldowns` ±1s observational warning into a CI exit-non-zero gate once the real-corpus baseline is signed. Surface is already in place; only the exit-code wiring is deferred.
- **DEFERRED-40-04-01**: `eval/corpus/sessions/hard_tek_01/events.jsonl` missing — diversity-gate test fails pre-existing.
- **DEFERRED-40-04-02**: `tests/eval/fixtures/synthetic_session/genre.txt` not whitelisted in `.gitignore` (conftest regenerates as untracked).

## Self-Check: PASSED

- `src/vibemix/audio/constants.py:65` `HEARTBEAT_SEC = 45.0` — FOUND.
- `src/vibemix/audio/constants.py:70` `"TRACK_CHANGE": 5.0` — FOUND.
- `src/vibemix/audio/constants.py:71` `"PHASE": 10.0` — FOUND.
- `scripts/eval/replay_harness.py` `_emit_cooldown_report` symbol — FOUND.
- `scripts/eval/replay_harness.py` `--print-cooldowns` argparse hook — FOUND.
- `tests/eval/test_replay_harness_cooldowns.py` — FOUND (8 tests, all passing).
- Commits `c73219c`, `7116d0d`, `14b3a60`, `d46c703` — all present in `git log`.
- POC files (`cohost_v4*.py` / `cohost.py` / `cohost_v2.py` / `cohost_lk.py` / `mascot.html`) — untracked & untouched.
