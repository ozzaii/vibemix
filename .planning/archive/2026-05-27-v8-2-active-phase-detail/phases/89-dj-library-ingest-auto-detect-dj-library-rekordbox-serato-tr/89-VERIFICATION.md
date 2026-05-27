---
phase: 89-dj-library-ingest
verified: 2026-05-26T00:00:00Z
status: passed
mode: mvp
score: 4/4 user-flow steps verified (MVP) · 13/13 plan truths verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
---

# Phase 89: DJ-Library Ingest (Rekordbox MVP slice) Verification Report

**Phase Goal (User Story):** As a DJ, I want to have vibemix auto-detect my Rekordbox library and embed my tracks on-device, so that my library is searchable and ready in minutes.
**Mode:** mvp
**Verified:** 2026-05-26
**Status:** passed
**Re-verification:** No — initial verification

User Story format: VALID (`user-story.validate` → `valid: true`; role=DJ, capability="have vibemix auto-detect my Rekordbox library and embed my tracks on-device", outcome="my library is searchable and ready in minutes").

---

## User Flow Coverage (MVP)

The success condition is the `[outcome]` clause: a DJ's library is **searchable and ready** after a one-tap ingest. Each step of the capability is traced to codebase evidence.

| # | User-story step | Expected | Evidence in codebase | Status |
|---|------------------|----------|----------------------|--------|
| 1 | DJ runs `vibemix library ingest` (no args) → auto-detect Rekordbox | `collection.xml` found at a standard export location; actionable error + exit 1 if not | `RekordboxSource.detect()` probes 3 macOS + 2 Windows defaults (`sources/rekordbox.py:36-99`), records `resolved_path`; CLI `_cmd_library_ingest` (`__main__.py:2570-2599`) gates on `detect()`, prints "no Rekordbox collection.xml found … Export via File → Export Collection" + `return 1`. CLI `--help` exits 0 listing `path` + `--json` (ran). `detect()` on the synthetic fixture returned `True` (ran). | ✓ VERIFIED |
| 2 | Each track parsed with clean metadata (key→Camelot, BPM, beatgrid, cues, genre/rating/comments) | `TrackEntry` carries enriched fields; Camelot computed deterministically at parse; missing fields honestly empty | Live parse of synthetic fixture (ran): track0 = `genre='Techno' rating=4 camelot='8A' key='Am' play_count=42 beatgrid_nodes=2 cues=4`, cue types `['cue','cue','cue','load']`. `rekordbox.py:42` imports `to_camelot`; `_track_to_beatgrid` (`:381`), `_rating_to_stars` (`:403`), `_resolve_cue_type` (`:460`) all defensive/honest. `SCHEMA_VERSION=2` (`:165`) invalidates stale v1 caches. | ✓ VERIFIED |
| 3 | Tracks embedded on-device (cue-anchored ≤80s windows, CLAP 512-dim) | DJ cues → `source="dj"` anchors; un-cued → `detect_cues` auto; no structure → whole-track; mean-pooled; keyless on-device | `excerpt.anchors_for_track`/`cut_windows` (`excerpt.py:66,145`) map structural cue/loop marks (load/fade dropped), ≤80s clamp; `ingest._embed_track_cue_anchored` (`ingest.py:311-379`) slices windows → `embed_audio_bytes` → `np.mean` → `l2_normalize`, whole-track `embed_audio_file` fallback, never a faked vector. CLI builds keyless `ClapEngine()` (`__main__.py:2608`). Tests `test_dj_cued_track_uses_window_path_and_mean_pools`, `test_no_structure_track_falls_back_to_whole_track`, `test_all_windows_failed_falls_back_to_whole_track`, `test_one_bad_window_is_non_fatal` all pass (46/46). | ✓ VERIFIED |
| 4 | Library searchable & ready (vectors stored, resumable, library.pkl) | Vectors in sqlite-vec store; re-run ~0 re-embeds; per-file failures skipped; titles resolve via library.pkl | `ingest_source` (`ingest.py:387-504`) stores via `store.add_batch`, content-hash cache (`clap_embeddings.db`, CLAP-namespaced) → resumable, writes `library.pkl` via `_write_library_cache`. Tests prove `embedded==5 / row_count==5` (e2e), `skipped_cached==5 / embedded==0` (resumable), `failed==1 / embedded==4 / row_count==4` no faked vector (honest). | ✓ VERIFIED |

**User-flow score: 4/4 verified.** The end-to-end vertical (detect → parse → excerpt → embed → store) is wired and proven on the synthetic fixture + the 46-test offline suite.

---

## Goal Achievement — Plan Truths

All 13 truths declared across the 3 plan frontmatters, verified against code.

| # | Truth (plan) | Status | Evidence |
|---|--------------|--------|----------|
| 1 | One-tap auto-detect of collection.xml (89-01) | ✓ VERIFIED | `RekordboxSource.detect()` + CLI gate; ran `detect()→True` |
| 2 | Each track CLAP-embedded on-device, vector stored (89-01) | ✓ VERIFIED | `ingest_source` → `embed_audio_*` → `store.add_batch`; e2e test embedded==5/row_count==5 |
| 3 | Resumable + honest partial failure (89-01) | ✓ VERIFIED | content-hash cache; resumable test skipped_cached==5/embedded==0; honest test failed==1, no faked vector |
| 4 | search/similar resolve titles (library.pkl written) (89-01) | ✓ VERIFIED | `_write_library_cache(handled, marker)` at `ingest.py:500`; `persist_library=True` default |
| 5 | TrackEntry carries genre/label/rating/play_count/comments (89-02) | ✓ VERIFIED | live parse: genre='Techno', rating=4, play_count=42; fields at `rekordbox.py:134-138` |
| 6 | Camelot at parse via deterministic table; raw key preserved (89-02) | ✓ VERIFIED | `camelot='8A'` from `key='Am'` (ran); `to_camelot(key)` at `:358`, raw key untouched |
| 7 | Beatgrid (TEMPO nodes) parsed when present, () when absent (89-02) | ✓ VERIFIED | `beatgrid_nodes=2` on fixture track0 (ran); `_track_to_beatgrid` returns `()` honestly |
| 8 | Cue carries real Type label, not flat 'cue' (89-02) | ✓ VERIFIED | fixture track0 cue types `['cue','cue','cue','load']` (ran); `_resolve_cue_type` |
| 9 | Missing fields honestly empty; SCHEMA_VERSION bump (89-02) | ✓ VERIFIED | typed-empty defaults; `SCHEMA_VERSION: int = 2` (`:165`), version guard at `:256` |
| 10 | dj-first CueAnchors, detect_cues fallback, never anchor-less (89-03) | ✓ VERIFIED | `excerpt.anchors_for_track` dj→auto→[]; ingest triple-degrade to whole-track |
| 11 | ≤80s mixable windows clamped to duration (89-03) | ✓ VERIFIED | `cut_windows` clamps [0,dur], 1..80s, drops degenerate (`excerpt.py:145-167`) |
| 12 | Cue-anchored mean-pool embed; cache-namespaced (89-03) | ✓ VERIFIED | `_embed_track_cue_anchored` mean-pool; `INGEST_CUE_STRATEGY_VERSION` in hash key; `test_cue_strategy_version_namespaces_cache` passes |
| 13 | Honest cue mapping; never a faked vector (89-03) | ✓ VERIFIED | load/fade marks dropped; whole-track fallback re-embeds real file; Invariant #3 |

**Plan-truth score: 13/13 verified.**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `library/sources/base.py` | LibrarySource @runtime_checkable Protocol | ✓ VERIFIED | 68L, `class LibrarySource(Protocol)` detect/default_paths/iter_tracks; import-clean |
| `library/sources/rekordbox.py` | RekordboxSource detect + iter | ✓ VERIFIED | 127L, `class RekordboxSource`, XML-only, OS-tolerant default_paths |
| `library/ingest.py` | ingest_source orchestrator | ✓ VERIFIED | 526L, `def ingest_source`, cache + dim-reconcile + honest loop |
| `library/excerpt.py` | anchors_for_track + cut_windows | ✓ VERIFIED | 167L, both functions present, pure mapping, import-light |
| `library/rekordbox.py` (enriched) | TempoNode + enriched TrackEntry + cue Type | ✓ VERIFIED | 488L, `class TempoNode`, `to_camelot`, SCHEMA_VERSION=2 |
| `__main__.py` (CLI) | `library ingest` subcommand | ✓ VERIFIED | `_cmd_library_ingest` at `:2570`; subparser at `:1740`; `--help` exits 0 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| ingest.py | clap_engine.py | `ClapEngine().embed_audio_*` (on-device) | ✓ WIRED | CLI builds `ClapEngine()` (`:2608`); helper calls `embed_audio_bytes`/`embed_audio_file` |
| ingest.py | store.py | `store.add_batch([(id, vec)])` | ✓ WIRED | `ingest.py:458,483`; CLI `open_store()` + try/finally close |
| sources/rekordbox.py | rekordbox.py | `RekordboxLibrary().load_xml/try_load_cache` | ✓ WIRED | `iter_tracks` cache-warms then `load_xml`, yields TrackEntry |
| rekordbox.py | state/harmonics.py | `to_camelot(raw)` at parse | ✓ WIRED | import `:42`, call `:358`; produced `8A` from `Am` (ran) |
| excerpt.py | cue_types.py | emits `CueAnchor` | ✓ WIRED | import `:41`, constructed `:111` |
| excerpt.py | cue_detect.py | `detect_cues` fallback | ✓ WIRED | lazy import inside fallback branch `:126` |
| ingest.py | excerpt.py | `anchors_for_track` + `cut_windows` | ✓ WIRED | import `:49`, called `:345,354` |

### Data-Flow Trace (Level 4)

Pipeline produces real data — not hardcoded/empty:
- Detect → real filesystem `.is_file()` probe (no static return).
- Parse → real `pyrekordbox` XML read; verified on fixture: genre/rating/camelot/beatgrid/cue-types all populated from XML attributes, not defaults (live run).
- Excerpt → real cue→window geometry from parsed CuePoints.
- Embed → real `ClapEngine.embed_audio_*` forward pass (keyless, on-device); tests use a deterministic non-faked fake; never stores a zero/faked vector on failure (honest-failure test asserts `row_count==4` after `failed==1`).
- Store → real `add_batch`; e2e asserts `row_count==5`.

Status: ✓ FLOWING. No hollow props, no static returns, no faked vectors.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI subcommand exists | `python -m vibemix library ingest --help` | exit 0, lists `path` + `--json` | ✓ PASS |
| Detect on fixture | `RekordboxSource(xml_path=FIX).detect()` | `True`, resolved path set | ✓ PASS |
| Parse enrichment | `iter_tracks()` track0 | genre=Techno rating=4 camelot=8A key=Am play_count=42 beatgrid=2 cues=4 | ✓ PASS |
| Honest-failure on no-audio fixture | `ingest_source(...)` over fixture (paths absent) | `failed=5, embedded=0, store rows=0` — no faked vectors | ✓ PASS |
| Phase-89 offline suite | `pytest test_ingest/test_excerpt/test_sources_rekordbox/test_rekordbox` | 46 passed | ✓ PASS |
| Embed→store leg (real temp audio) | e2e/resumable/honest tests in test_ingest.py | embedded==5/skipped==5/failed==1 with row counts | ✓ PASS |

### Import Purity

`import vibemix.library.{sources.base, sources.rekordbox, ingest, excerpt, rekordbox}` → `torch`/`laion_clap` NOT in `sys.modules` → printed `IMPORT_CLEAN`. CLAP heavy deps stay lazy. ✓ VERIFIED.

### SQLCipher Dormancy Gate

`grep "Rekordbox6Database\|pyrekordbox.db6"` over the Phase-89 files matches only docstrings documenting the ban (3 lines, all comment/docstring). The repo-scrub test (`test_repo_scrub.py`) is AST-import-based and passes. No real `master.db` import/call. ✓ VERIFIED.

### Anti-Patterns Found

None in Phase-89 files. No debt markers (TBD/FIXME/XXX), no `return null`/empty-stub renders, no console-only handlers. The `pragma: no cover` markers on Protocol classes are intentional structural-typing stubs, not implementation stubs. The "whole-track fallback" path is a real re-embed, not a faked vector.

---

## Full-Suite Result & Failure Triage

Full offline suite: **4749 passed, 8 failed, 25 skipped, 1 xfailed, 4 xpassed** (356s, no network/torch/GEMINI_API_KEY).

All 8 failures investigated; **none are Phase-89 artifacts:**

| Failure | Owner | Evidence it is NOT Phase 89 |
|---------|-------|------------------------------|
| `test_no_api_key_surface::test_no_api_key_label_text_anywhere_in_ui` | Phase 88 (frontend) | Offender `tauri/ui/src/library/index.ts:217` "Add a Gemini key…" — committed Phase 88, no 89 file touches UI (matches prompt's known-acceptable list) |
| `test_orphan_inventory::test_orphan_diff_clean_against_committed_baseline` | Set-Builder session | New orphan = `build_set_prompt` in `codex_curate.py` (concurrent session), not a 89 symbol; 89's symbols are consumed (matches prompt's known-acceptable list) |
| `test_grounding.py` (5 tests) + `test_track_citation_validates_end_to_end` (1) | **Phase 90 (CLAP-wiring, in-flight)** | Commit `a6dc6659` "feat(90): CLAP embedding-swap wiring" modified `grounding.py` to call `embedder.embed_audio_bytes` + assert `shape==(EMBEDDING_DIM=1536,)`, and changed `test_grounding.py`. Run in isolation `test_grounding.py` is **13/13 green**; the integration test fails **even run alone** (intrinsic to P90's mid-flight grounding migration). **Zero Phase-89 commits touched grounding/citation files** (verified via `git show --stat` over all 8 P89 commits → empty). Error: `grounding embed failed: … expected (1536,)` — the 1536 dim is explicitly the **Phase 90 lane** per the phase scope fence ("the 1536→512 flip is owned by the CLAP-wiring session"). |

**Conclusion:** The 6 grounding/citation failures are collateral from Phase 90's CLAP-wiring landing in the shared `live-tuning-or-brain` working tree (the documented concurrent-sessions-on-one-tree hazard). They belong to Phase 90's completion, are out of Phase 89's scope fence, and do not invalidate Phase 89's goal — whose own surface (46 tests) is fully green.

---

## Deferred Items (later-phase ownership, not actionable Phase-89 gaps)

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | EMBEDDING_DIM 1536→512 flip / grounding embed_audio_bytes test migration | Phase 90 | ROADMAP Phase 90 goal: "library … embeds on-device via CLAP (… 512-dim) instead of Gemini"; grounding failures trace to P90 commit `a6dc6659` |
| 2 | Serato + Traktor source adapters | Phase 90 | CONTEXT `<deferred>`: "Serato adapter → Phase 90; Traktor adapter → Phase 90" |
| 3 | Real file watcher (auto re-embed on change) | Phase 91 | CONTEXT `<deferred>`: "Real file watcher → Phase 91" |

---

## Gaps Summary

No Phase-89 gaps. The detect → parse → excerpt → embed → store vertical is implemented, wired, and proven end-to-end on the synthetic fixture and the 46-test offline suite. Metadata enrichment (Camelot/beatgrid/cue-Type/genre/rating) verified live. Import purity, SQLCipher dormancy, resumability, and honest partial-failure (never a faked vector — Invariant #3) all hold. Dim posture is correctly deferred to Phase 90 (store-whatever-CLAP-returns, fail-loud on non-empty mismatch). The 8 full-suite failures are all non-Phase-89 (2 known-acceptable + 6 owned by the in-flight Phase 90 CLAP-wiring session sharing the working tree).

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
