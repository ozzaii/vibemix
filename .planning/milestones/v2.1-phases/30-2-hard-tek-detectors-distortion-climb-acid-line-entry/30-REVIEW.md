---
phase: 30-2-hard-tek-detectors-distortion-climb-acid-line-entry
reviewed_at: 2026-05-15
depth: standard
files_reviewed: 16
status: clean
findings:
  blocker: 0
  warning: 0
  info: 2
  total: 2
---

# Phase 30 — Code Review Report

**Depth:** standard
**Files reviewed:** 16 (10 source + 6 test)
**Status:** clean (no Blocker, no Warning, 2 Info-level observations)

## Scope

Files reviewed (from git diff `2ff8907^..beb7fe4`):

Source (10):
- `src/vibemix/state/detectors/_dsp.py`
- `src/vibemix/state/detectors/distortion_climb.py`
- `src/vibemix/state/detectors/acid_line_entry.py`
- `src/vibemix/state/detectors/__init__.py`
- `src/vibemix/state/event.py`
- `src/vibemix/state/genre_router.py`
- `src/vibemix/events/genres/__init__.py`
- `src/vibemix/events/genres/hard_tek.py`
- `src/vibemix/audio/constants.py`
- `scripts/tune_detectors.py`

Tests (5):
- `tests/state/detectors/test_distortion_climb.py`
- `tests/state/detectors/test_acid_line_entry.py`
- `tests/state/test_genre_router.py`
- `tests/state/test_genre_router_race.py`
- `tests/scripts/test_tune_detectors.py`

Docs (1):
- `eval/corpus/hard_tek/README.md`

## Findings

### BLOCKER — none

### WARNING — none

### INFO

#### IN-01: Private-attribute access `audio_buf._sr` propagates to two new detectors

**Files:** `src/vibemix/state/detectors/distortion_climb.py` (lines 127, 131, 134, 147), `src/vibemix/state/detectors/acid_line_entry.py` (lines 101, 103, 109, 115)

Both new detectors read `audio_buf._sr` directly — accessing a single-underscore-private attribute on `AudioBuffer`. This is a pre-existing project convention (also used in `kick_swap.py:97-99` and `phrase_boundary.py:163-165` from Phase 17), not introduced by Phase 30. Flagged here only to make the convention visible: if/when `AudioBuffer` ever needs to expose a public `sample_rate` property, **all** kick-side detectors should be updated in one sweep, not piecemeal. Not actionable for Phase 30.

#### IN-02: `chain_position` increments only in `DistortionClimbDetector`, not `AcidLineEntryDetector`

**Files:** `src/vibemix/state/detectors/distortion_climb.py:82,159,170`, `src/vibemix/state/detectors/acid_line_entry.py`

`DistortionClimbDetector` carries an int counter `chain_position` and emits it in the event payload (`extra["chain_position"]`). `AcidLineEntryDetector` does **not** emit a chain_position — it emits `formant_hz` + `resonance_q` instead. The two plans (30-01 vs 30-02) deliberately ship different payload shapes per CONTEXT D, so this is **by design** rather than a bug. Documenting the inconsistency for any downstream consumer (debrief, mascot) that wants to surface a sequential index across overlay events.

## Adversarial pass — what I tried to break

- **Race in `GenreRouter._chain` rebind.** Verified by the 1000-cycle threaded race test (`test_genre_router_1000_cycle_concurrent_swap_no_race`); the swap is a single attribute assignment + CPython GIL, and the new immutable `MappingProxyType` ensures readers can never observe a half-mutated registry. **Holds.**

- **Stale density-streak survives silence.** `DistortionClimbDetector` clears `_density_streak_start` on `state.rms < LOW_RMS` (line 102-104). Test `test_distortion_climb_no_fire_on_silence` pins it. **Holds.**

- **Acid sweep slope numerics on degenerate input.** `np.polyfit` would raise on `freqs <= 0`; defended at line 150 (`if np.any(freqs <= 0.0): return None`) — and the out-of-band guard at line 122-123 ensures only > 0 frequencies are appended. **Holds.**

- **Cooldown bypass via direct `last_event_at` reset.** No code path resets `last_event_at` except inside the fire branch. **Holds.**

- **harmonic_distortion_proxy divide-by-zero.** Defended by `even_energy + 1e-12` (line 200). **Holds.**

- **band_spectral_flatness collapse on zero-magnitude bins.** Defended by log-sum trick `log(band_mag + eps)` (line 149). **Holds.**

- **Circular import on `events.genres → state.detectors → genre_router → events.genres`.** Closed by Plan 30-02 — `GENRE_REGISTRY` import in `genre_router.swap()` is lazy. Verified by `test_genre_router_*` running cleanly. **Holds.**

- **MappingProxyType immutability.** Direct test `test_genre_registry_is_immutable_mapping` raises `TypeError` on both `__setitem__` and `__delitem__`. **Holds.**

- **`build_hard_tek_chain` ordering — does `KICK_SWAP` come before overlays?** Yes, asserted in `test_hard_tek_chain_is_techno_plus_overlay_detectors:228-230`. **Holds.**

- **Genre leakage — do overlays appear in techno/house chains?** Negative tests `test_techno_chain_does_not_contain_hard_tek_overlays` + `test_house_chain_does_not_contain_hard_tek_overlays` cover both negatives. **Holds.**

## Anti-pattern scan

- [x] No hardcoded secrets (grep `AIza`, `api_key`, `password`, `token` — clean across all 10 source files).
- [x] No dangerous functions (`eval`, `exec`, `system`, `shell_exec`, `innerHTML`, etc.).
- [x] No debug artifacts (`print` debug, `breakpoint`, `pdb.set_trace`).
- [x] No empty `except` clauses; all error paths either re-raise or log.
- [x] No commented-out code (>3-line blocks) in new files.
- [x] No POC file modifications (`cohost_v4.py` / `cohost_v3.py` / `cohost.py` untouched — verified via git diff).
- [x] No CLAP / LAION-CLAP / MERT / OpenL3 imports (Kaan's "Gemini Embedding 2 only" rule — N/A here, no embeddings).
- [x] Type hints present on all public function signatures.
- [x] SPDX license header on all 10 new source files.

## Project-rule compliance

- **CLAUDE.md "POC = reference, devour it":** Phase 30 does not touch any `cohost_*.py` file. Confirmed via git diff scope.
- **CLAUDE.md "trust the audio" anti-hallucination rule:** Both detectors have a silence-gate FIRST (`state.rms < LOW_RMS`) and an out-of-band guard in their underlying DSP primitives (`dominant_freq_in_band` 1% in-band-energy floor; `band_spectral_flatness` returns 0.0 on `total <= 0.0`).
- **CLAUDE.md "Gemini-only":** No third-party AI library imports; pure DSP + numpy.
- **`MIN_EVENT_GAP_PER_TYPE` extension:** Both new entries are non-zero positive floats; no regression of Phase 17 entries.

## Test posture

| Test file | Tests | Status |
|-----------|-------|--------|
| test_distortion_climb.py | 6 | 6/6 PASS |
| test_acid_line_entry.py | 6 | 6/6 PASS |
| test_genre_router.py | 12 | 12/12 PASS |
| test_genre_router_race.py | 4 | 4/4 PASS (incl. 1000-cycle race) |
| test_tune_detectors.py | 12 | 12/12 PASS (3 Phase 30 + 9 existing) |
| test_dsp_primitives.py | 6 | 6/6 PASS (pre-existing, no Phase 30 regression) |

Broader regression: `pytest tests/state/ tests/scripts/test_tune_detectors.py` → **478 passed / 1 skipped / 0 failed** in 5.15s.

## Verdict

**No Blocker, no Warning findings.** Phase 30 ships green from a code-review perspective. The two Info items are documentation-grade observations on pre-existing project conventions, not defects.
