---
phase: 89-dj-library-ingest
plan: 01
subsystem: library
tags: [rekordbox, clap, ingest, embeddings, sqlite-vec, protocol, cli]

# Dependency graph
requires:
  - phase: 28-library
    provides: "LibraryStore (open_store/add_batch/vector_dim/recreate_table), RekordboxLibrary parser, folder_ingest IngestReport + resumable/honest loop shape"
  - phase: 89-clap-stage
    provides: "ClapEngine staged on-device 512-dim embedder (lazy-import contract)"
provides:
  - "LibrarySource @runtime_checkable Protocol (detect/default_paths/iter_tracks) — the firewall between DJ-app catalogs and the OS-agnostic ingest orchestrator"
  - "RekordboxSource — collection.xml auto-detect (macOS+Windows defaults, OS-tolerant) + iter_tracks over the existing RekordboxLibrary, XML-only (no SQLCipher)"
  - "ingest_source orchestrator — detect→iter→CLAP-embed→store, resumable via a CLAP-namespaced content-hash cache, honest per-file failure, dim-posture-locked"
  - "vibemix library ingest [path] [--json] CLI — keyless on-device embed, one-tap auto-detect"
affects: [89-02-metadata-enrichment, 89-03-cue-anchored-embed, clap-wiring-session, serato-source, traktor-source]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Source-as-Protocol: ingest depends on LibrarySource structural contract, never a concrete source — Serato/Traktor drop in with zero ingest.py edits (open/closed)"
    - "CLAP-namespaced content-hash cache (clap_embeddings.db) distinct from Gemini embeddings.db — a 512-d CLAP vector never collides with a 1536-d Gemini row keyed by the same file"
    - "Dim-posture-locked ingest: store whatever clap_engine returns (512); recreate empty-mismatch store, fail-loud on non-empty mismatch — never silently mix dims"

key-files:
  created:
    - src/vibemix/library/sources/__init__.py
    - src/vibemix/library/sources/base.py
    - src/vibemix/library/sources/rekordbox.py
    - src/vibemix/library/ingest.py
    - tests/library/test_sources_rekordbox.py
    - tests/library/test_ingest.py
  modified:
    - src/vibemix/__main__.py

key-decisions:
  - "LibrarySource is a @runtime_checkable Protocol (structural), not an ABC — test fakes stay trivial and concrete sources never inherit"
  - "Content-hash cache key = sha256(file-bytes) || clap-backend-tag || INGEST_STRATEGY_VERSION('v1-clap-wholetrack') so the Plan-03 cue-anchored swap invalidates v1 vectors cleanly"
  - "ingest is KEYLESS (ClapEngine on-device) — unlike embed-folder which needs a Gemini API key; audio never leaves the machine"
  - "Whole-track embed for the skeleton; cue-anchoring is deferred to Plan 03 per the version-tagged cache"

patterns-established:
  - "Pattern: LibrarySource Protocol firewall — per-DJ-app catalog readers behind one structural contract"
  - "Pattern: resumable+honest ingest loop mirrored from folder_ingest (broad-except per file → failed+continue, never a faked vector)"

requirements-completed: []

# Metrics
duration: 14min
completed: 2026-05-26
---

# Phase 89 Plan 01: DJ-Library Ingest (Rekordbox MVP slice) Summary

**One-tap `vibemix library ingest` auto-detects the Rekordbox collection.xml, parses each track via the existing RekordboxLibrary, embeds it on-device via keyless CLAP (512-dim), and stores the vectors resumably + honestly — the detect→parse→embed→store walking skeleton.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-05-26T13:08:09Z
- **Completed:** 2026-05-26T13:22:54Z
- **Tasks:** 2 (TDD: RED committed prior session, GREEN this session)
- **Files modified:** 7 (5 created, 1 modified, plus deferred-items note)

## Accomplishments
- `LibrarySource` `@runtime_checkable` Protocol — the source firewall: ingest depends on the contract, so Serato/Traktor sources slot in with zero ingest.py edits.
- `RekordboxSource` — auto-detects `collection.xml` at standard macOS + Windows export locations (OS-tolerant expanduser), records the resolved path, and iterates `TrackEntry` rows over the existing `RekordboxLibrary` (cache-warm then `load_xml`). XML-only — SQLCipher `master.db` never opened.
- `ingest_source` orchestrator — resumable (CLAP-namespaced content-hash cache → ~0 re-embeds on re-run), honest (missing/unreadable file or embed raise → `failed`+continue, never a faked vector), dim-posture-locked (recreate empty-mismatch store; fail-loud RuntimeError on a non-empty dim mismatch, naming the CLAP-wiring session as the dim-reconciliation owner). Writes `library.pkl` so `search`/`similar` resolve ingested titles.
- `vibemix library ingest [path] [--json]` CLI — keyless `ClapEngine`, actionable "no collection.xml found" message + exit 1 when undetected.

## Task Commits

1. **Task 1: Wave-0 failing e2e ingest test + sources package skeleton** - `6aa9686` (test — RED, committed in a prior session)
2. **Task 2: RekordboxSource + ingest_source orchestrator + CLI** - `927a4e6` (feat — GREEN: removed strict-xfail, landed impl + CLI + two Rule-1 fixes)

_TDD: RED (test) → GREEN (feat). No refactor commit needed._

## Files Created/Modified
- `src/vibemix/library/sources/base.py` - `LibrarySource` `@runtime_checkable` Protocol; lazy-import-clean (typing+pathlib only).
- `src/vibemix/library/sources/__init__.py` - re-exports `LibrarySource`; import-safe (no heavy dep).
- `src/vibemix/library/sources/rekordbox.py` - `RekordboxSource` detect/default_paths/iter_tracks over `RekordboxLibrary`.
- `src/vibemix/library/ingest.py` - `ingest_source` orchestrator + content-hash cache + dim reconciliation + `_resolve_local_path`.
- `src/vibemix/__main__.py` - `library ingest` subparser + `_cmd_library_ingest` handler (keyless ClapEngine).
- `tests/library/test_sources_rekordbox.py` - Protocol pin (real-green) + RekordboxSource detect/iter coverage.
- `tests/library/test_ingest.py` - e2e / resumability / honest-failure tests with a deterministic `FakeClapEmbedder` (no torch, no network).

## Decisions Made
- See `key-decisions` frontmatter. Notably: keyless on-device ingest (CLAP, not Gemini), version-tagged content-hash cache for clean Plan-03 invalidation, and a fail-loud dim posture that defers the 512↔1536 reconciliation to the CLAP-wiring session.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `default_paths()` raised `RuntimeError` on wrong-OS `~\\...` defaults**
- **Found during:** Task 2 (running the RekordboxSource detect tests under `--runxfail`)
- **Issue:** The Windows defaults (e.g. `~\Documents\rekordbox\collection.xml`) are a single POSIX path component starting with `~`; `Path(...).expanduser()` on macOS raises `RuntimeError: Could not determine home directory` for that "~user" form, aborting the whole `detect()` probe.
- **Fix:** Per-candidate try/except in `default_paths()` — fall back to the un-expanded `Path(c)` on `RuntimeError`/`OSError` so a wrong-OS default simply fails the later `.exists()` check instead of crashing.
- **Files modified:** `src/vibemix/library/sources/rekordbox.py`
- **Verification:** All 5 RekordboxSource tests + 3 ingest tests green.
- **Committed in:** `927a4e6`

**2. [Rule 1 - Bug] `_resolve_local_path` missed pyrekordbox's slash-stripped Location form**
- **Found during:** Task 2 (ingest e2e/resumable/honest tests reported every file as "local audio file missing")
- **Issue:** pyrekordbox 0.4.4 normalizes `file://localhost/private/var/...` by stripping the scheme + authority INCLUDING the leading slash, so `TrackEntry.filepath` arrives as a host-relative `private/var/...`. `_resolve_local_path` only stripped a `file://` prefix and then `Path("private/var/...").is_file()` was False — meaning whole-track ingest would find ZERO files in production, not just in tests.
- **Fix:** Build a candidate list — try the path as-is, then a slash-restored `/`+path when it's neither root-anchored nor a Windows drive path (`X:`). Return the first that resolves to a real file; honest None otherwise.
- **Files modified:** `src/vibemix/library/ingest.py`
- **Verification:** All 3 ingest tests green (embedded==5, resumable skipped_cached==5, honest failed==1).
- **Committed in:** `927a4e6`

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs). Bug #2 was a production-blocking defect — without it `library ingest` would silently embed nothing on a real Mac.
**Impact on plan:** Both fixes necessary for correctness. No scope creep; no scope-fenced file touched.

## Issues Encountered
- Initial test run used a stray homebrew Python 3.14 (`ServiceTier` import error). Resolved by running under the project's `.venv` (3.12.12) per CLAUDE.md — `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest`.

## Threat surface
No new threat surface beyond the plan's `<threat_model>`. SQLCipher stays dormant (XML-only); per-file broad-except honors Invariant #3 (never a faked vector); the dim-mismatch Runtimeable path is fail-loud (T-89-04). The two AST-aware repo-scrub mentions of `Rekordbox6Database`/`pyrekordbox.db6` in `sources/rekordbox.py` are docstring-only (documenting the ban) — `tests/repo/test_repo_scrub.py` is import-AST-based and passes.

## Known Stubs
None. The whole-track embed is intentional for the skeleton; Plan 03 refines it to cue-anchored (cache version-tagged `v1-clap-wholetrack` so the swap invalidates cleanly). The `onnx` CLAP backend remains a documented `NotImplementedError` stub owned by the CLAP parity gate — not this plan's surface.

## Next Phase Readiness
- 89-02 (metadata enrichment) and 89-03 (cue-anchored embed) build on this skeleton; both consume the same `LibrarySource`/`ingest_source` seam.
- The 512↔1536 dim reconciliation is deferred to the CLAP-wiring session (ingest fails loud on a non-empty mismatch rather than guessing). `open_store()` returns the live 1536-d store today; CLAP ingest against a populated 1536-d store will fail-loud by design until that session migrates the store.
- Out-of-scope pre-existing failure logged in `deferred-items.md`: `tests/security/test_no_api_key_surface.py` flags `tauri/ui/src/library/index.ts:217` ("Add a Gemini key…", committed Phase 88) — frontend, untouched by this plan.

## Self-Check: PASSED

All 6 created files exist on disk; both task commits (`6aa9686` RED, `927a4e6` GREEN) resolve in git log.

---
*Phase: 89-dj-library-ingest*
*Completed: 2026-05-26*
