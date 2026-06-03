# CODEX VERDICT — B15 VERIFY ANLZ CUES LIVE

- Item: B15 verify-only ANLZ cue persistence / stale doc correction.
- User value: a Studio / Pro DJ using Rekordbox can trust that their own phrase structure survives import and reaches section consumers; CUE-DETR remains a fallback, not the first source of truth.
- SHAs:
  - `c1486520` — `test(library): prove ANLZ cues survive cache reload`
  - `91aa5e80` — `docs(packets): correct b15 ANLZ scope`

## What Landed

- Added a real Rekordbox-source ingest regression that loads the persisted `library.pkl` through `RekordboxLibrary().try_load_cache()` and asserts cached cues include `source="anlz"` with the expected `INTRO` / `DROP` labels.
- Corrected the stale packet claim that ANLZ labels were thrown away. Current source materializes Rekordbox ANLZ/PSSI anchors into `TrackEntry.cues source="anlz"` before cache persistence, and `sections_for_entry()` maps those cues back to `source_detail="pssi"`.
- Clarified coverage: `_materialize_anlz_cues` is Rekordbox ANLZ/PSSI-specific. Serato, Traktor, VirtualDJ, and EngineDJ import ordinary DJ-authored cues directly into the shared `TrackEntry.cues` shape; phrase sidecars beyond cue records would be a separate follow-up.

## Proof

- `uv run pytest -q tests/library/test_ingest.py::test_rekordbox_ingest_persists_anlz_cues_in_loadable_library_cache tests/library/test_ingest.py::test_anlz_index_drives_windows_and_has_separate_cache tests/library/test_anlz_ingest.py tests/library/test_excerpt.py::test_materialized_anlz_cues_keep_source_confidence_and_label` -> 18 passed.
- `uv run pytest -q tests/library/test_sources_rekordbox.py tests/library/test_sources_serato.py tests/library/test_sources_traktor.py tests/library/test_sources_virtualdj.py tests/library/test_sources_engine.py` -> 33 passed.
- `uv run ruff check tests/library/test_ingest.py` -> pass.
- Current live cache check: `cache_ok=True tracks=187 path=/Users/ozai/.cache/vibemix/library.pkl`, `anlz_cue_count=0 source_counts={}`. This machine currently has a folder cache with no ANLZ cues, so a true live ANLZ drop/section observation is not available from this cache.

## Verdict

B15's build premise is closed as false: the ANLZ-to-cached-cue wire already exists, and the regression now pins restart/load persistence. The live DROP-call / spoken structure path remains intentionally owner-gated; do not flip `VIBEMIX_DROP_CALL` until an actual ANLZ-keyed Rekordbox import is run on Kaan's rig and the drop accuracy bar is ear-approved.
