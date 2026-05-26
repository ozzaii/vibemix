# Phase 89 — Deferred / Out-of-Scope Items

Logged by the 89-02 executor (scope fence: `library/rekordbox.py` + its tests/fixture only).
These failures surfaced in the full offline suite but are NOT caused by Plan 89-02's changes
and lie outside its scope fence — left untouched per the executor scope boundary.

## Out-of-scope test failures observed during 89-02 full-suite run (2026-05-26)

- `tests/library/test_sources_rekordbox.py` — 4 failing tests
  (`test_rekordbox_source_detect_missing_returns_false`,
  `test_rekordbox_source_iter_tracks_yields_entries`,
  `test_rekordbox_source_satisfies_protocol`,
  `test_rekordbox_source_no_sqlcipher_import`).
  Owned by **Plan 89-01** (the `library/sources/` + `ingest.py` LibrarySource Protocol slice).
  These are the 89-01 RED tests (committed at `6aa9686`); their implementation has not landed
  yet. Expected-RED for the parallel plan — will flip green when 89-01 lands its source impl.

- `tests/security/test_no_api_key_surface.py::test_no_api_key_label_text_anywhere_in_ui` — 1 failing.
  UI/security guard unrelated to the Python Rekordbox parser. No 89-02 file touches the UI.
  Pre-existing in the working tree; outside 89-02 scope fence.

89-02's own surface (`tests/library/test_rekordbox.py`) is fully green: 18 passed.

## Update from 89-01 executor (2026-05-26)

- The four `tests/library/test_sources_rekordbox.py` tests above are now GREEN — 89-01
  landed `RekordboxSource` + `ingest_source` and removed the strict-xfail markers.
- `tests/security/test_no_api_key_surface.py::test_no_api_key_label_text_anywhere_in_ui`
  STILL fails: offender is `tauri/ui/src/library/index.ts:217` ("Add a Gemini key…"),
  committed in Phase 88 (`ea9ceff`), unmodified by 89-01, frontend, outside the 89-01
  Python scope fence. Left untouched per the executor scope boundary — a frontend/Phase-88
  owner must reword that empty-state string.

## Update from 89-03 executor (2026-05-26)

Full offline suite at 89-03 completion: **4751 passed, 2 failed, 27 skipped, 1 xfailed, 4 xpassed**.
Both failures are OUT of 89-03's scope fence (`excerpt.py` + `ingest.py` + their tests):

- `tests/security/test_no_api_key_surface.py::test_no_api_key_label_text_anywhere_in_ui`
  STILL fails — same Phase-88 frontend offender as above. No 89-03 file touches the UI.
- `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline`
  fails with ONE new orphan: `build_set_prompt` in `src/vibemix/library/codex_curate.py`
  (a **Set-Builder concurrent session** file — NOT a 89-03 file). 89-03's own new symbols
  (`anchors_for_track` / `cut_windows` in `excerpt.py`) are consumed by `ingest.py` and are
  NOT flagged as orphans. Refreshing `.planning/codebase/orphans.csv` is explicitly forbidden
  for this session (concurrent sessions own the baseline), so this gate is left red for the
  baseline-owner to refresh after the concurrent work lands.
