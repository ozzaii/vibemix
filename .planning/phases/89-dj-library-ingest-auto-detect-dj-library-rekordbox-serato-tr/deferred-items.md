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
