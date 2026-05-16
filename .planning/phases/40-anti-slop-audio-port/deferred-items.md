# Phase 40 — Deferred Items

Out-of-scope discoveries logged during execution. Each item names the plan
that discovered it; the phase planner / verifier triages.

---

## DEFERRED-40-02-01: `tests/audio/test_constants.py::test_event_gap_dict_shape_and_values` is stale

**Discovered by:** Plan 40-02 (no-regression sweep over `tests/audio/`).

**Issue:** The test pins `MIN_EVENT_GAP_PER_TYPE.keys()` to the Phase 17 SENSE-12 + 17-03 + 17-04 set (10 keys), but `src/vibemix/audio/constants.py` already includes Phase 30 SENSE-17/18 additions (`DISTORTION_CLIMB`, `ACID_LINE_ENTRY` — bringing the set to 12 keys). The test fails on `main` with:

```
Extra items in the left set:
'ACID_LINE_ENTRY'
'DISTORTION_CLIMB'
```

**Root cause:** Test was not updated when Phase 30 landed (SENSE-17/18, the Hard Tek detectors). Pre-existing failure on every commit of `main` for the past 200+ commits — not caused by Plan 40-02.

**Why deferred:** Out-of-scope (Phase 30 test debt, not Phase 40 audio-port work). Plan 40-02 changes are strictly additive (`src/vibemix/audio/lookahead.py` + 5 re-exports in `__init__.py` + new test file); none modify `constants.py` or `test_constants.py`.

**Where to fix:** Update the expected key set in `tests/audio/test_constants.py:87-101` to include `DISTORTION_CLIMB` and `ACID_LINE_ENTRY`, then add their numeric pins (6.0 and 8.0 per Phase 30 plan) to the value-assertion block below. One-line follow-up plan, or fold into Phase 40-03's prep sweep.

**Impact on Plan 40-02:** None — Plan 40-02's own 8 tests pass cleanly. CI gate is locally green for `tests/audio/test_lookahead.py`.
