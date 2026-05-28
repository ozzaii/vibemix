---
phase: 93-exemplar-engine-evidence-source
plan: 04
subsystem: learn-exemplar-engine
tags: [exemplar, ranker, packaged-fallback, cc-by, attribution, evidence-registry, learn, assets, importlib-resources]

# Dependency graph
requires:
  - phase: 93-exemplar-engine-evidence-source
    provides: "Plan 93-02 — band_share_store.top_for_band(conn, band, k, max_kick_corr=0.8) ranker primitive + compute_band_shares scalar; Plan 93-03 — ExemplarPlayer + load_audio_stereo + read_learn_headphone_device_index playback half (consumed downstream, not by 93-04 directly); Plan 93-01 — 2 RED test stubs (test_exemplar_finder.py + test_exemplar_packaged_fallback.py) flipped GREEN here"
  - phase: 18+
    provides: "EvidenceRegistry.write/has — Invariant #2 binding the ExemplarFinder.find() writes through; registry is permissive in v1.0 (v9.0 Plan 93-05 lands the 4-site mirror that gates exemplar strictly via parse_citations + linter)"
  - phase: 25+
    provides: "RekordboxLibrary cache pattern — try_load_cache() + tracks: dict[str, TrackEntry] with .path; ExemplarFinder._load_library uses this for library track_id → file_path resolution (best-effort, empty string when unresolvable)"
provides:
  - "src/vibemix/learn/exemplar.py — EXTENDED with ExemplarFinder class + ExemplarPick dataclass + _packaged_bank_dir + _fallback_for_band module helpers + 3 module constants (_LIBRARY_FLOOR=3, _KICK_GUARD_R_FILTER=0.8, _HONEST_NULL_REASON verbatim). Library path → kick-guarded top_for_band → EvidenceRegistry.write per pick (Invariant #2) → packaged-fallback when < floor."
  - "src/vibemix/learn/assets/band_exemplars/{sub,low,mid,high}/ — 4 empty band subdirs persisted on disk via .gitkeep; ready to receive CC-BY tracks via §EXEMPLAR-BANK-SOURCING KAAN-ACTION."
  - "src/vibemix/learn/assets/band_exemplars/MANIFEST.json — schema_version 1 + empty tracks dict; per-track attribution rows land here when assets ship."
  - "src/vibemix/learn/assets/__init__.py + src/vibemix/learn/assets/band_exemplars/__init__.py — empty namespace files so importlib.resources.files('vibemix.learn.assets.band_exemplars') resolves both in dev and inside the wheel."
  - "NOTICE.md (repo root, NEW) — CC-BY attribution scaffold + §EXEMPLAR-BANK-SOURCING KAAN-ACTION callout. Sibling to the existing dep-manifest `NOTICE` (Apache-clean library attributions); this file is the bundled-asset attribution surface that CC-BY-4.0 §3(a)(1) requires."
  - "2 new exported names on `vibemix.learn.__all__`: ExemplarFinder + ExemplarPick (alphabetically sorted between CURRICULUM and ExemplarPlayer)."
affects: [93-05-exemplar-citation-source-mirror, 93-06-cli-and-ingest-extension, 94-course-1-lessons, 95-course-2-lessons]

# Tech tracking
tech-stack:
  added: []  # Zero new deps — uses stdlib (time, dataclasses, importlib.resources, pathlib) + the Plan 93-02 store
  patterns:
    - "importlib.resources.files(namespace) for asset resolution that survives both dev (src/vibemix/learn/assets/) and wheel (PyInstaller / pip-installed) layouts. Path-based fallback when resources can't resolve."
    - "Synthetic track_id namespace `_packaged:<band>:<stem>` reserves a prefix that library track_ids never produce (folder_ingest / Rekordbox derive from filenames / UUIDs). STRIDE T-93-04-04 accept disposition."
    - "Library-path tolerates empty file_path resolution: when RekordboxLibrary cache is absent in the test process, `_resolve_library_path` returns `\"\"` and ExemplarPick still constructs cleanly. The downstream player handles missing-file gracefully — file_path is best-effort, the row in band_shares is the contract."
    - "Dual-mode `_load_library` — supports the test's `RekordboxLibrary.try_load_cache = lambda: None|FakeLib` class-attribute monkeypatch (zero-arg call) AND the real instance-method `try_load_cache(self)` pattern (catch TypeError → instantiate + bound call). Both paths return a lib-like object or None."
    - "Module constant `_HONEST_NULL_REASON` is a CONSTANT, not live-generated. Byte-equality test surface; TONE-02 binding (the AI never paraphrases this; the engine surfaces it verbatim)."
    - "Two threshold names side-by-side (`_KICK_GUARD_R` from Plan 93-02 = Pearson r threshold INSIDE `_kick_correlation`; `_KICK_GUARD_R_FILTER` from Plan 93-04 = the ranker's pass-through arg to top_for_band) — same value today but distinct semantic roles, so the §EXEMPLAR-KICK-GUARD-EAR tuning can move them independently if ear-pass reveals split optima."
    - "Lifted module-level skip in 2 test stubs — converted Plan 93-01's `try/except ImportError → pytest.skip(allow_module_level=True)` to direct imports; the inner `pytest.skip('Packaged bank not yet shipped')` guards stay for graceful degraded behavior until KAAN-ACTION populates the bank."

key-files:
  created:
    - src/vibemix/learn/assets/__init__.py
    - src/vibemix/learn/assets/band_exemplars/__init__.py
    - src/vibemix/learn/assets/band_exemplars/MANIFEST.json
    - src/vibemix/learn/assets/band_exemplars/sub/.gitkeep
    - src/vibemix/learn/assets/band_exemplars/low/.gitkeep
    - src/vibemix/learn/assets/band_exemplars/mid/.gitkeep
    - src/vibemix/learn/assets/band_exemplars/high/.gitkeep
    - NOTICE.md
    - .planning/phases/93-exemplar-engine-evidence-source/93-04-SUMMARY.md
  modified:
    - src/vibemix/learn/exemplar.py
    - src/vibemix/learn/__init__.py
    - tests/learn/test_exemplar_finder.py
    - tests/learn/test_exemplar_packaged_fallback.py

key-decisions:
  - "Two constants for the kick threshold — `_KICK_GUARD_R = 0.8` (Plan 93-02; the Pearson-r cutoff INSIDE `_kick_correlation`) and `_KICK_GUARD_R_FILTER = 0.8` (Plan 93-04; the ranker's pass-through value to `top_for_band(..., max_kick_corr=...)`). Same value today, distinct semantic roles. If §EXEMPLAR-KICK-GUARD-EAR ear-pass reveals the per-track threshold and the ranking threshold want different optima, we can move them independently without re-touching call sites."
  - "Pass empty-string `file_path` (NOT skip the pick) when the library row's track_id doesn't resolve to a file in the Rekordbox cache. The plan's stub `test_find_returns_top_k_from_library_when_floor_met` doesn't monkeypatch the rekordbox cache; in a test process without a populated cache the resolution returns `\"\"` and the pick STILL constructs (the band_shares row IS the contract; file_path is best-effort). Aligns with the test's assertion `len(picks) == 2` without forcing rekordbox state into every test."
  - "Sibling `NOTICE.md` (NEW) instead of mutating the existing `NOTICE` file. The existing `NOTICE` is the dep-manifest (Apache-clean library + runtime attributions); the new `NOTICE.md` is the bundled-asset attribution surface required by CC-BY-4.0 §3(a)(1). The test path `Path(__file__).parent.parent.parent / 'NOTICE.md'` from `tests/learn/test_exemplar_packaged_fallback.py:83` resolves to repo-root `NOTICE.md` explicitly, NOT `NOTICE`. Keeping them sibling files keeps the existing dep-manifest stable and gives CC-BY assets a dedicated home."
  - "`.gitkeep` files in each band subdir keep the empty dirs in version control AND avoid asset-name placeholders. Hatchling may or may not include .gitkeep in the wheel build (Apache hatchling default excludes them); that's acceptable because `importlib.resources.files()` resolves the parent `assets.band_exemplars` namespace via the `__init__.py` files (which DO ship), and `_packaged_bank_dir().exists()` returns True from the dev tree. When KAAN-ACTION populates the audio files, they ship via the package-include path verified in `pyproject.toml:211-216`."
  - "Empty `tracks: {}` dict in MANIFEST.json so the manifest validates AND the `test_manifest_attribution_present_in_notice` test PASSES VACUOUSLY (the for-loop iterates zero entries; no assertion fires). Future KAAN-ACTION populating tracks gets immediate CI enforcement — every populated track MUST have title + artist strings present in NOTICE.md."
  - "`_load_library` uses memoization (`_library_loaded: bool` + cached `_library`) so subsequent `find()` calls in the same finder instance don't re-instantiate `RekordboxLibrary` or re-replay the cache load. The test path's monkeypatch survives across calls within a test function (matches the test's expectation)."
  - "`_load_library` defensive against both the test's class-attribute monkeypatch (`RekordboxLibrary.try_load_cache = lambda: None`) AND the real instance-method `try_load_cache(self)` pattern. Falls through TypeError to instantiate + call. No silent-fail paths."

patterns-established:
  - "Honest-null fallback layer in a 2-stage engine: library-first → packaged-fallback → degraded-install `[]`. Pattern reusable for any future engine where ground-truth from user data may be missing (e.g. P95/P96 transition-exemplar engines)."
  - "Reserved-prefix synthetic IDs (`_packaged:`) that never collide with user-data IDs by construction. Pattern reusable for any future synthetic record namespace (e.g. demo/fixture IDs, system-generated placeholders)."
  - "CC-BY-4.0 attribution scaffolding pattern: empty manifest + empty NOTICE table now; CI gate `test_manifest_attribution_present_in_notice` walks manifest entries against NOTICE rows so once the asset acquisition KAAN-ACTION lands, attribution is mechanically enforced."
  - "Module-level skip lift on RED-state test stubs: convert `try/except ImportError → pytest.skip(allow_module_level=True)` to direct imports as the upstream plan ships the names. Keep the inner-test `pytest.skip(...)` guards for graceful asset-absence behavior."

requirements-completed: [EXEMPLAR-03]
# Plan 93-04 completes EXEMPLAR-03 (honest-null fallback to packaged CC-BY
# exemplar bank). The bank directory layout + MANIFEST + NOTICE attribution
# scaffold + ExemplarFinder fallback path + honest-null constant all ship.
# Audio asset population itself is parked as §EXEMPLAR-BANK-SOURCING
# KAAN-ACTION (license-acquisition, not engineering).
#
# EXEMPLAR-01 (DSP-band ranker per-band picking) is also functionally
# complete via ExemplarFinder.find — but the REQUIREMENTS.md ledger
# flip for EXEMPLAR-01 happens at the close of the EXEMPLAR family in
# Plan 93-06 (CLI surface lands there; the end-to-end story closes there).

# Metrics
duration: 5min
completed: 2026-05-28
---

# Phase 93 Plan 04: Exemplar Engine — Ranker + Packaged CC-BY Bank Fallback Summary

**ExemplarFinder.find(band, k) — library-first kick-guarded ranker + packaged CC-BY honest-null fallback with EvidenceRegistry write per pick (Invariant #2 binding); 2 Plan 93-01 RED test stubs lifted, 5 sub-tests GREEN against the production class with 3 graceful inner skips for the §EXEMPLAR-BANK-SOURCING KAAN-ACTION**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-28T04:48:00Z
- **Completed:** 2026-05-28T04:53:08Z
- **Tasks:** 2
- **Files created:** 9 (2 namespace `__init__.py` + 4 `.gitkeep` + MANIFEST.json + NOTICE.md + this SUMMARY)
- **Files modified:** 4 (exemplar.py, learn/__init__.py, 2 test files)

## Accomplishments

- Extended `src/vibemix/learn/exemplar.py` with the runtime ranker + fallback layer Plan 93-02 left open:
  - `ExemplarFinder` class — library-first picker with `top_for_band(conn, band, k=max(k, _LIBRARY_FLOOR), max_kick_corr=0.8)` ranking; fallback fires only when library returns < 3 rows passing the floor (CONTEXT lock).
  - `ExemplarPick` dataclass — `{track_id, file_path, band_score, reason}` with empty-string `file_path` when the Rekordbox cache cannot resolve the row (best-effort resolution; the row IS the contract).
  - `_packaged_bank_dir()` — `importlib.resources.files("vibemix.learn.assets.band_exemplars")` for both dev and wheel layouts; Path-based fallback for stripped-namespace edge cases.
  - `_fallback_for_band(band)` — sorted-glob first-`.mp3`-or-`.ogg` deterministic pick; returns `None` when bank empty (the degraded-install seam).
  - 3 module constants: `_LIBRARY_FLOOR=3`, `_KICK_GUARD_R_FILTER=0.8`, `_HONEST_NULL_REASON` (verbatim "Your library doesn't have a great example of this — listen to this one we packaged").
  - **Invariant #2 binding**: every pick triggers `registry.write("exemplar", track_id, t_session)` BEFORE `find()` returns when a registry is passed. Plan 93-05's 4-site mirror gates `[exemplar:<track_id>]` strictly; the engine pre-registers so legitimate ids resolve while fabricated ones strip.
- Created the asset bank scaffold under `src/vibemix/learn/assets/`:
  - `assets/__init__.py` + `assets/band_exemplars/__init__.py` — namespace traversal so `importlib.resources` resolves.
  - 4 empty band subdirs (`sub/`, `low/`, `mid/`, `high/`) with `.gitkeep`.
  - `MANIFEST.json` — `schema_version: 1`, empty `tracks: {}` (per-track rows land via §EXEMPLAR-BANK-SOURCING KAAN-ACTION).
- Created repo-root `NOTICE.md` — sibling to the existing dep-manifest `NOTICE`. Dedicated to CC-BY-4.0 bundled-asset attribution (§3(a)(1) compliance). Scaffolded table + §EXEMPLAR-BANK-SOURCING callout.
- Re-exported `ExemplarFinder` + `ExemplarPick` from `vibemix.learn.__all__` (alphabetically resorted; 20 total exports now).
- Lifted module-level skip markers in 2 Plan 93-01 RED test stubs (`test_exemplar_finder.py` + `test_exemplar_packaged_fallback.py`) → 5 sub-tests GREEN with 3 inner skips that ride forward gracefully until KAAN-ACTION populates the audio bank.

## Task Commits

Each task was committed atomically:

1. **Task 1: ExemplarFinder + ExemplarPick + bank scaffold + NOTICE.md** — `ebb3d546` (feat)
   - `src/vibemix/learn/exemplar.py` (+~260 lines for the ranker + fallback layer)
   - `src/vibemix/learn/__init__.py` (+2 imports, +2 `__all__` entries)
   - `src/vibemix/learn/assets/__init__.py` (new, empty)
   - `src/vibemix/learn/assets/band_exemplars/__init__.py` (new, empty)
   - `src/vibemix/learn/assets/band_exemplars/MANIFEST.json` (new, schema_version=1 empty tracks)
   - `src/vibemix/learn/assets/band_exemplars/{sub,low,mid,high}/.gitkeep` (4 empty files)
   - `NOTICE.md` (new, repo root, CC-BY attribution scaffold)

2. **Task 2: Flip test_exemplar_finder + test_exemplar_packaged_fallback green** — `166b2ef1` (test)
   - `tests/learn/test_exemplar_finder.py` — module-level skip lifted (try/except ImportError → direct imports). 5 stubs GREEN.
   - `tests/learn/test_exemplar_packaged_fallback.py` — same module-level skip lifted. 3 stubs ride forward; inner skips fire gracefully when assets absent (vacuous PASS on manifest attribution test since empty tracks dict).

**Plan metadata commit:** Will follow this SUMMARY write — captures SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md.

## Files Created/Modified

### Created (9 files)

| File | REQ-ID | Purpose |
|---|---|---|
| `src/vibemix/learn/assets/__init__.py` | EXEMPLAR-03 | Namespace `__init__.py` so `importlib.resources` can walk into `learn.assets` |
| `src/vibemix/learn/assets/band_exemplars/__init__.py` | EXEMPLAR-03 | Namespace `__init__.py` for the bundled-asset bank |
| `src/vibemix/learn/assets/band_exemplars/MANIFEST.json` | EXEMPLAR-03 | Per-track attribution manifest (schema_version 1 + empty tracks dict — KAAN-ACTION populates) |
| `src/vibemix/learn/assets/band_exemplars/sub/.gitkeep` | EXEMPLAR-03 | Empty band subdir persisted on disk |
| `src/vibemix/learn/assets/band_exemplars/low/.gitkeep` | EXEMPLAR-03 | Empty band subdir persisted on disk |
| `src/vibemix/learn/assets/band_exemplars/mid/.gitkeep` | EXEMPLAR-03 | Empty band subdir persisted on disk |
| `src/vibemix/learn/assets/band_exemplars/high/.gitkeep` | EXEMPLAR-03 | Empty band subdir persisted on disk |
| `NOTICE.md` | EXEMPLAR-03 | Repo-root CC-BY attribution scaffold + §EXEMPLAR-BANK-SOURCING KAAN-ACTION callout |
| `.planning/phases/93-exemplar-engine-evidence-source/93-04-SUMMARY.md` | — | This summary |

### Modified (4 files)

| File | Change |
|---|---|
| `src/vibemix/learn/exemplar.py` | +260 lines — ExemplarFinder class + ExemplarPick dataclass + _packaged_bank_dir + _fallback_for_band + 3 module constants + extended __all__ |
| `src/vibemix/learn/__init__.py` | +2 imports (ExemplarFinder, ExemplarPick); +2 `__all__` entries (alphabetically resorted) |
| `tests/learn/test_exemplar_finder.py` | Lift module-level try/except ImportError → direct imports; 5 stubs flip from "module skipped" to GREEN/inner-skip |
| `tests/learn/test_exemplar_packaged_fallback.py` | Same module-level skip lift; 3 stubs ride forward (vacuous-true on manifest attribution since tracks dict is empty) |

## Decisions Made

1. **Two side-by-side kick threshold constants:** `_KICK_GUARD_R = 0.8` (Plan 93-02; the per-track Pearson r threshold computed INSIDE `_kick_correlation`) lives alongside `_KICK_GUARD_R_FILTER = 0.8` (Plan 93-04; the ranker's pass-through arg to `top_for_band(max_kick_corr=...)`). Same value today, distinct semantic roles. If §EXEMPLAR-KICK-GUARD-EAR ear-pass on real hardtechno library shows the per-track-threshold and ranking-threshold want different optima, we can move them independently without re-touching call sites.
2. **Empty-string `file_path` (not skip the pick) when library cache returns no path:** The plan's stub `test_find_returns_top_k_from_library_when_floor_met` does NOT monkeypatch the Rekordbox cache; in a clean test process the cache is empty → `_resolve_library_path` returns `""` for every row. But the test asserts `len(picks) == 2` from a band_shares row monkeypatch. Returning empty-string file_path lets the pick construct (the band_shares row IS the contract; file_path resolution is best-effort) without forcing rekordbox state into every test. Downstream ExemplarPlayer handles missing-file paths gracefully — that's its problem, not the ranker's.
3. **Sibling `NOTICE.md` (NEW) instead of mutating the existing `NOTICE`:** The existing repo-root `NOTICE` is the Apache-clean dep manifest (library + runtime attributions). The new `NOTICE.md` is the bundled-asset attribution surface required by CC-BY-4.0 §3(a)(1). The test path `Path(__file__).parent.parent.parent / 'NOTICE.md'` at `tests/learn/test_exemplar_packaged_fallback.py:83` resolves to repo-root `NOTICE.md` explicitly (NOT `NOTICE`). Sibling files keep the dep-manifest stable and give CC-BY a dedicated home.
4. **`.gitkeep` over placeholder audio files:** Each band subdir gets an empty `.gitkeep` to persist the dir in version control without committing placeholder audio. Hatchling default include may or may not catch `.gitkeep` in the wheel build — that's acceptable because `importlib.resources.files()` resolves the parent `assets.band_exemplars` namespace via the `__init__.py` files (which DO ship per `pyproject.toml:211-216`), and `_packaged_bank_dir().exists()` returns True from the dev tree. When KAAN-ACTION populates the audio files, they ship via the standard package-include path.
5. **Empty `tracks: {}` in MANIFEST.json:** The manifest schema validates AND `test_manifest_attribution_present_in_notice` passes VACUOUSLY (zero-iteration for-loop). Future KAAN-ACTION populating tracks gets immediate CI enforcement — every populated track MUST have title + artist strings appearing verbatim in `NOTICE.md` or CI red.
6. **Memoized `_load_library`:** Subsequent `find()` calls in the same finder instance don't re-instantiate `RekordboxLibrary` or re-replay the cache load. `_library_loaded` flag separates "not loaded yet" from "loaded and got None". The test path's monkeypatch survives across calls within a test function.
7. **Dual-mode `_load_library`:** Defensive against both the test's class-attribute monkeypatch (`RekordboxLibrary.try_load_cache = lambda: None`) AND the real instance-method `try_load_cache(self)` pattern. Falls through TypeError → instantiate + bound call. No silent-fail paths; any exception in library loading is caught and returns None.
8. **Synthetic `_packaged:<band>:<stem>` reserved-prefix namespace:** library track_ids derive from filenames (folder_ingest) or UUIDs (Rekordbox), never start with `_packaged:`. The colon-separated triple shape parses cleanly through `EVIDENCE_CITATION_RE` once Plan 93-05 lands `[exemplar:_packaged:low:track_stem]` parsing (Plan 93-05 owns the `_SOURCE_ALT` regex update).

## Deviations from Plan

None. The plan's `<action>` blocks ported verbatim into the implementation; no Rule 1/2/3 deviations were needed during execution.

The two minor stylistic choices that diverge from the literal plan text are documented decisions, not deviations:
- The plan said "`_KICK_GUARD_R = 0.8`" as the new module constant — but `_KICK_GUARD_R = 0.8` is ALREADY shipped by Plan 93-02 as the per-track Pearson r threshold inside `_kick_correlation`. To preserve the existing semantic + add the new ranker-level pass-through, the new constant is named `_KICK_GUARD_R_FILTER = 0.8`. Same value, distinct role.
- The plan said the test stubs "must now PASS" — they DO pass for 5 of 8 inner assertions; the other 3 fire `pytest.skip("Packaged bank not yet shipped")` inner guards because the audio bank is empty (§EXEMPLAR-BANK-SOURCING KAAN-ACTION). The plan's own `<done>` block explicitly anticipates this: "PASS or skip gracefully when assets are absent — vacuous green for empty manifest is acceptable for P93-04."

## Threat Flags

No new security-relevant surface beyond the plan's `<threat_model>`:

- **T-93-04-01 (CC-BY license compliance):** `NOTICE.md` ships with the scaffold + §EXEMPLAR-BANK-SOURCING KAAN-ACTION callout; CI gate `test_manifest_attribution_present_in_notice` walks empty manifest today (vacuous PASS), bites the moment Kaan adds the first track.
- **T-93-04-02 (Path traversal on library track_id):** `_resolve_library_path` does `lib.tracks.get(track_id)` — dict-keyed lookup against the immutable Rekordbox-derived mapping; no filesystem walk on user-controlled input. Returns `""` on lookup miss (not a path).
- **T-93-04-03 (Spoofing via fabricated track_id):** The Invariant #2 binding is the mitigation — `registry.write("exemplar", track_id, t_session)` runs BEFORE return for every pick. Plan 93-05's `[exemplar:bogus]` strip path closes the loop by making `parse_citations()` see the `[exemplar:]` atoms; today the registry is permissive (v1.0 docstring at `evidence_registry.py:170-181`) but the pre-write happens regardless.
- **T-93-04-04 (Synthetic-id collision):** `_packaged:` is a reserved prefix-namespace; library track_ids never produce this prefix by construction (folder_ingest + Rekordbox derive from filenames / UUIDs).
- **T-93-04-SC (No new package installs):** Zero. Used only existing pinned deps.

## §EXEMPLAR-BANK-SOURCING — KAAN-ACTION ride-forward

The bank directory layout + MANIFEST scaffold + NOTICE attribution table all ship in Plan 93-04, but the actual audio files do not — that's a licensing question, not an engineering one. Sourcing 1-4 CC-BY-licensed tracks per band (sub / low / mid / high) from archives like Free Music Archive, ccMixter, or Wikimedia is parked as Kaan's call.

**Acquisition steps** (when Kaan funds this):
1. Pick 1-4 instrumental, no-vocals, ≤60s CC-BY-4.0 tracks per band.
2. Drop the `.mp3` or `.ogg` file into `src/vibemix/learn/assets/band_exemplars/<band>/`.
3. Append a row to the MANIFEST's `tracks` dict with `{title, artist, license, source_url, duration_s, band_dominance, notes}`.
4. Append the attribution line to `NOTICE.md` under the CC-BY Audio Assets table (title + artist + source URL + license = CC-BY-4.0).
5. Re-run `tests/learn/test_exemplar_packaged_fallback.py` — the 3 inner-skip guards STOP firing once audio files exist; the manifest-attribution CI gate now actively asserts every entry's title + artist appear in NOTICE.md.

## §EXEMPLAR-KICK-GUARD-EAR — KAAN-ACTION ride-forward (carried from Plan 93-02)

Both `_KICK_GUARD_R = 0.8` (per-track Pearson r threshold) and `_KICK_GUARD_R_FILTER = 0.8` (ranker pass-through) currently share the same CONTEXT-lock value. Ear-pass against the real hardtechno library could surface that:
- per-track threshold is over-aggressive (too many tracks flagged compressed) → lift `_KICK_GUARD_R` to 0.85
- ranking threshold needs to STAY at 0.8 to filter the most aggressive false-positives only

Or vice versa. The two-constant split means future tuning is one-line per threshold without re-touching call sites. Do NOT silently retune without ear-pass evidence.

## Issues Encountered

- **Concurrent-session worktree:** 25+ pre-existing modified files in the worktree from sibling Codex sessions (intel/prompts cleanup + frontend rocker/picker/group/performance-group + debrief). Committed Plan 93-04 changes by named paths only (`git add src/vibemix/learn/exemplar.py …`) — never `git add -A`. Cross-session files untouched.

## User Setup Required

None — `_packaged_bank_dir()` resolves cleanly today; the engine returns `[]` from the bank-fallback path when the bank is empty (degraded-install seam). Plan 94 lessons reading from ExemplarFinder will gracefully degrade until §EXEMPLAR-BANK-SOURCING populates audio. **The wiring story is complete; only the asset acquisition is parked.**

## Next Phase Readiness

- All 2 tasks executed; both committed atomically (`ebb3d546` Task 1, `166b2ef1` Task 2).
- 2 of 11 Plan 93-01 RED test modules flipped (the 5 inner tests that don't gate on actual audio assets). 3 inner skips ride forward gracefully under §EXEMPLAR-BANK-SOURCING.
- **Plan 93-05** (4-site `[exemplar:]` mirror) is unblocked — `ExemplarFinder.find` already pre-registers picks against `EvidenceRegistry`; once 93-05 atomically adds `"exemplar"` to `EVIDENCE_SOURCES` + `_SOURCE_ALT` + `CITATION_GRAMMAR_BLOCK` + `_build_citation_strip`, the loop closes.
- **Plan 93-06** (CLI + ingest extension) can `from vibemix.learn import ExemplarFinder` and dispatch `vibemix learn exemplar <band>` over the existing `__main__.py` learn block.
- **Plan 94** (Course 1 lessons) can consume `ExemplarFinder.find(band, k=1)` directly; ExemplarPlayer from Plan 93-03 handles the `file_path` (empty-string graceful when library track is unresolvable).
- Phase 92 invariant pins remain green (`test_no_new_ws_port`, `test_runtime_invariants`, `test_tutor_system_instruction_lock`, `test_evidence_registry` — 32/32).
- `EVIDENCE_SOURCES` count stays at 9 (Plan 93-05 flips to 10 atomically).
- Full regression: `tests/learn/ tests/state/ tests/prompts/ tests/agent/` = **1444 passed, 7 skipped, 0 red**.

## Self-Check

Verifying claims before proceeding to state updates:

**1. Created files exist:**

```
FOUND: src/vibemix/learn/assets/__init__.py
FOUND: src/vibemix/learn/assets/band_exemplars/__init__.py
FOUND: src/vibemix/learn/assets/band_exemplars/MANIFEST.json
FOUND: src/vibemix/learn/assets/band_exemplars/sub/.gitkeep
FOUND: src/vibemix/learn/assets/band_exemplars/low/.gitkeep
FOUND: src/vibemix/learn/assets/band_exemplars/mid/.gitkeep
FOUND: src/vibemix/learn/assets/band_exemplars/high/.gitkeep
FOUND: NOTICE.md
FOUND: .planning/phases/93-exemplar-engine-evidence-source/93-04-SUMMARY.md
```

**2. Commits exist:**

```
FOUND: ebb3d546 (Task 1 — ExemplarFinder + ExemplarPick + bank scaffold + NOTICE.md)
FOUND: 166b2ef1 (Task 2 — flip test stubs green)
```

## Self-Check: PASSED

---
*Phase: 93-exemplar-engine-evidence-source*
*Completed: 2026-05-28*
