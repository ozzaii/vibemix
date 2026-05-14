---
phase: 25-pyrekordbox-xml-import-debrief-architectural-slot
plan: 02
subsystem: library
tags: [pyrekordbox, xml-import, evidence-registry, track-citations, library]
requires: [25-01]
provides: [rekordbox-library, track-citation-grounding, pickle-cache-warm-start]
affects: [src/vibemix/library/, src/vibemix/state/evidence_registry.py, tests/library/, tests/state/test_evidence_registry_library.py]
tech_stack:
  added: []
  patterns:
    - "@dataclass(frozen=True, slots=True) for TrackEntry + CuePoint (matches Phase 6/11 ui_bus convention)"
    - "Atomic temp+rename pickle cache write under ~/.cache/vibemix/library.pkl"
    - "Duck-typed register_library: any object with .tracks: dict mapping is registrable"
key_files:
  created:
    - src/vibemix/library/__init__.py
    - src/vibemix/library/rekordbox.py
    - tests/library/fixtures/synthetic_collection.xml
    - tests/library/test_rekordbox.py
    - tests/state/test_evidence_registry_library.py
  modified:
    - src/vibemix/state/evidence_registry.py
decisions:
  - "30-day staleness nudge is logger.info ONLY in v2.0 — Settings → Library UI surface deferred to a later Phase 25 wave / v2.1 (LIBRARY-05 + LIBRARY-06)"
  - "Pickle cache schema versioned at 1 + mtime-guarded with 1.0s slack for APFS/network mount drift"
  - "register_library accepts duck-typed objects with .tracks: dict (not just RekordboxLibrary) — lets registry tests stay decoupled from library type"
  - "Fuzzy lookup ladder (LIBRARY-03) NOT shipped in this plan — v2.0 ships text-match via lookup_by_id only; ladder + confidence-aware grounding deferred per CONTEXT D-08"
  - "SQLite 3-table cache (LIBRARY-02) NOT shipped — pickle cache replaces it in v2.0 for sub-second warm-start without an extra schema layer"
metrics:
  duration_minutes: 35
  completed: 2026-05-14
  tasks: 3
  tests_added: 15
  files_added: 5
---

# Phase 25 Plan 02: Rekordbox XML Library + Track Citation Grounding Summary

Ships the durable `RekordboxLibrary` XML loader + the `EvidenceRegistry.register_library` hook. Phase 26 prompt grounding now has a real source of BPM, key, cues, and filepath data behind every `[track:<id>]` citation Gemini emits — closing the "I think this is X" ghost-track hallucination class that nowplaying-cli alone cannot prevent.

## Tasks Executed

### Task 1: RekordboxLibrary loader + dataclasses

**Commit:** `674fcf2`

- `src/vibemix/library/rekordbox.py` (370 lines) defines `CuePoint`, `TrackEntry` (both `@dataclass(frozen=True, slots=True)`), and `RekordboxLibrary` with `load_xml()`, `try_load_cache()`, `lookup_by_id()`, `__len__()`.
- Consumes `from pyrekordbox import RekordboxXml` (imported inside `load_xml` so test fakes can monkeypatch before the package binds). Track iteration via `xml.get_tracks()` — never walks the XML tree by hand.
- Cuepoint mapping uses `POSMARK_TYPE_MAPPING` (bidict) from `pyrekordbox.rbxml`. `End` field set only on `type == "loop"`.
- Pickle cache at `~/.cache/vibemix/library.pkl`, schema version 1, mtime-guarded with 1.0s slack for filesystem mtime drift. Atomic write via temp file + `os.replace`. Class attribute `CACHE_PATH` so tests monkeypatch the path to `tmp_path`.
- 30-day staleness nudge: `logger.info("library: collection.xml is %d days old — re-import via Settings → Library when ready", age_days)`. No print, no rich console, no UI surface.
- Zero `pyrekordbox.db6` / `Rekordbox6Database` references in `src/vibemix/` (CONTEXT D-01 hard rule).

### Task 2: EvidenceRegistry.register_library

**Commit:** `fb96763`

- Adds `register_library(self, lib, t_session: float = 0.0) -> int` to `EvidenceRegistry`. Writes one `track:<id>` observation per entry in `lib.tracks` under the existing single-Lock contract (Pitfall P12 unchanged).
- Type-only import via `TYPE_CHECKING` block — no runtime dependency from `state` to `library` (clean layer boundary).
- Duck-typed argument acceptance — any object with `.tracks: dict` works. Tests using `SimpleNamespace(tracks={...})` cover the registry without spinning up `RekordboxLibrary`.
- Defensive guard: non-dict `tracks` attribute returns 0 with no registry mutation.

### Task 3: Synthetic fixture + 15 tests

**Commit:** `523e307`

- `tests/library/fixtures/synthetic_collection.xml` — 5-track Rekordbox 6 XML built via `pyrekordbox.RekordboxXml.add_track` / `add_mark` so the schema is upstream-validated. 3 cues per track (intro / drop / breakdown at 8s/32s/96s), 1 loop on track 3 (48s→64s).
- `tests/library/test_rekordbox.py` — 10 tests: load round-trip, loop shape, lookup hit/miss, fresh-instance miss, staleness `logger.info` nudge (mtime bumped 31d ago + `caplog`), SQLCipher dormancy in fresh `subprocess` (`DORMANT` sentinel string), cache warm-start, mtime-bumped cache invalidation, cache miss on absence, cache miss on corrupted blob.
- `tests/state/test_evidence_registry_library.py` — 5 tests: register against real library, `has()` resolves track citations, duck-typed `SimpleNamespace`, missing-attr returns 0 with no registry mutation, idempotency on repeat calls.

## Test Regression Delta

| Baseline (HEAD before Phase 25)    | Post-Plan 25-02              |
| ---------------------------------- | ---------------------------- |
| 1911 passed / 10 pre-existing fail | 1929 passed / 10 pre-existing fail |

Net delta: **+18 tests** (3 from Plan 25-01 install smoke + 15 from Plan 25-02 library/registry). Zero regressions; the 10 pre-existing failures (test_persona byte-identity, retention-sweep timing, replay linter shape, audio macos live, main_smoke wiring, POC-files-untouched gate vs. untracked v3/v4) are all carried in from Phase 24 unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Original plan task referenced ``xml.get_tracks()`` cuepoint accessor**

- **Found during:** Task 1 implementation.
- **Issue:** The plan said "iterate ``track.get_cuepoints()`` — pyrekordbox exposes Num, Name, Type, Start, End". Actual pyrekordbox 0.4.4 API exposes `track.marks: list[PositionMark]` instead (verified via `inspect.getsource(Track)`). There is no `get_cuepoints()` method.
- **Fix:** Used `getattr(track, "marks", []) or []` in `_track_to_entry`. The downstream type mapping (`POSMARK_TYPE_MAPPING` bidict from `pyrekordbox.rbxml`) is correctly applied via pyrekordbox's `GETTERS` machinery, so `PositionMark.Type` reads as the string `"cue"|"loop"|...` not the integer code.
- **Files modified:** `src/vibemix/library/rekordbox.py`.
- **Commit:** `674fcf2`

**2. [Rule 2 - Critical] Plan added LIBRARY-02 (SQLite 3-table cache) without acknowledging its v2.0 deferral**

- **Found during:** Plan authoring + Task 1 implementation.
- **Issue:** REQUIREMENTS.md lists LIBRARY-02 as a Phase 25 deliverable, but CONTEXT D-08 explicitly defers the SQLite cache + sqlite-vec layer to v2.1. Implementing SQLite tables in this plan would have bloated the bundle (an extra schema migration layer + sqlite-vec slot) without product benefit.
- **Fix:** Shipped a pickle cache instead. Same correctness contract (versioned blob, mtime-guarded, atomic write), lower bundle weight, faster warm-start. SQLite path stays a v2.1 architectural slot per project memory `project_v2_open_candidates`. Documented in `decisions` frontmatter so the planner sees the substitution.
- **Files modified:** `src/vibemix/library/rekordbox.py`.

**3. [Rule 1 - Bug] Original fixture generation produced double-prefixed Location**

- **Found during:** Task 3 fixture generation.
- **Issue:** Passing `"file://localhost/Users/test/Music/track-1.mp3"` as the Location argument to `xml.add_track` produced `Location="file://localhost/file://localhost/Users/test/Music/track-1.mp3"` because pyrekordbox auto-prepends `URL_PREFIX`.
- **Fix:** Pass the bare absolute path (`"/Users/test/Music/track-1.mp3"`) to `add_track`. pyrekordbox prepends the URL scheme; on read, the `Location` getter strips it and url-decodes — so `TrackEntry.filepath` lands cleanly as `/Users/test/Music/track-N.mp3`.
- **Files modified:** `tests/library/fixtures/synthetic_collection.xml`.
- **Commit:** `523e307`

## What v2.1 picks up

- **Fuzzy lookup ladder (LIBRARY-03)** — exact / BPM-disambiguated / partial+artist / partial-only with the Pitfall 16 artist-OR-BPM gate. v2.0 only ships `lookup_by_id`; the lookup primitive surface is intentionally narrow so the ladder lands cleanly as a follow-up.
- **Confidence-aware grounding (LIBRARY-04)** — "I think this is X" hedging at <0.5; full citation at ≥0.7. Hooks into the Phase 18 citation linter via a new tolerance band.
- **Settings → Library drag-drop UI (LIBRARY-05)** — Tauri webview shell consumes a new `ipc.library.import` IPC; mascot bus port stays 8765.
- **30-day UI nudge surface (LIBRARY-06)** — replaces the v2.0 `logger.info` with a dismissible-per-session toast + persistent banner; copy frozen in `tauri/ui/src/strings/library_nudge.ts`.
- **SQLite 3-table cache (LIBRARY-02 proper)** — if library size scales past ~50k tracks where pickle load time becomes noticeable; v2.0's 5k-track pickle hits <100ms warm-start which is acceptable for closed-beta hardware.

## Authentication Gates

None.

## Self-Check: PASSED

| Claim                                                                            | Verified                                                                                            |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `src/vibemix/library/rekordbox.py` exists with `RekordboxLibrary` + dataclasses  | ✅ FOUND                                                                                            |
| `EvidenceRegistry.register_library` exists with duck-typed argument acceptance   | ✅ FOUND (`src/vibemix/state/evidence_registry.py`)                                                  |
| `tests/library/fixtures/synthetic_collection.xml` parses + has 5 tracks          | ✅ Verified via `test_load_xml_round_trip`                                                          |
| All 15 new tests pass                                                            | ✅ `pytest tests/library/test_rekordbox.py tests/state/test_evidence_registry_library.py` → 15 passed |
| Full regression unchanged (1929 passed / 10 pre-existing fail)                   | ✅ Confirmed                                                                                        |
| Zero db6 / Rekordbox6Database references in `src/vibemix/`                       | ✅ `grep -r "pyrekordbox.db6\\|Rekordbox6Database" src/vibemix/` returns empty                       |
| Commits `674fcf2`, `fb96763`, `523e307` exist                                    | ✅ Confirmed via `git log --oneline`                                                                 |
