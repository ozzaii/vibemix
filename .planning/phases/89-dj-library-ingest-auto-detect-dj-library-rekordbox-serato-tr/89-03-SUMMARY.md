---
phase: 89-dj-library-ingest
plan: 03
subsystem: library
tags: [cue-anchored, excerpt, ingest, clap, embeddings, mean-pool, rekordbox]

# Dependency graph
requires:
  - phase: 89-01-dj-library-ingest
    provides: "ingest_source orchestrator + CLAP-namespaced content-hash cache + resumable/honest loop (the path this slice rewires)"
  - phase: 89-02-dj-library-ingest
    provides: "Rekordbox CuePoint.type fidelity (cue/loop/load/fadein/fadeout) — the dj-anchor mapping needs the real Type label"
  - phase: 89-clap-stage
    provides: "ClapEngine.embed_audio_bytes (window) + embed_audio_file (whole-track) seam"
  - phase: auto-cue
    provides: "cue_types.CueAnchor frozen contract + cue_detect.detect_cues offline auto engine (consumed READ-ONLY)"
provides:
  - "excerpt.anchors_for_track — dj-first (cue/loop, hot-0=intro else drop) → detect_cues auto fallback → [] honest; never anchor-less, never a faked anchor"
  - "excerpt.cut_windows — clamp anchors to [0,duration] 1..80s mixable windows, drop degenerate spans"
  - "ingest_source rewired to cue-anchored window embedding (mean-pool the per-window CLAP vectors); INGEST_CUE_STRATEGY_VERSION namespaces the cache key"
affects: [clap-wiring-session, set-builder, live-cohost-enter-on-hot-cue, serato-source, traktor-source]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cue-anchored mean-pool: per-window embed_audio_bytes → np.mean → l2_normalize → one vector (mirrors embed.py _embed_audio_cue_anchored, CLAP not Gemini)"
    - "Triple-degrade coverage: dj cues → detect_cues auto → whole-track embed_audio_file; a track is NEVER left anchor-less and NEVER gets a faked vector (T-89-09/T-89-11)"
    - "Strategy-version cache namespacing: INGEST_CUE_STRATEGY_VERSION in the content-hash key so a cue-anchored vector never collides with the whole-track vector for the same file (T-89-10)"
    - "Import-light mapping module: excerpt.py top level = stdlib + cue_types + rekordbox; cue_detect (DSP) lazy-imported inside the fallback branch — torch-free import"

key-files:
  created:
    - src/vibemix/library/excerpt.py
    - tests/library/test_excerpt.py
  modified:
    - src/vibemix/library/ingest.py
    - tests/library/test_ingest.py

key-decisions:
  - "Labels best-effort, positions authoritative: hot cue slot 0 → intro, every other cue → drop; we do NOT fabricate build/breakdown from a bare position mark (T-89-08, trust the audio)"
  - "load/fadein/fadeout marks are NOT structural anchors — only type in {cue,loop} (hot or memory) map to dj anchors; the rest fall through to the auto path"
  - "detect_cues failure (it shells ffmpeg to decode) degrades to the whole-track embed, NOT a track abort — mirrors embed.py's fallback posture and honors T-89-09"
  - "Slicer resolved at call time from the module global (_default_slicer), not bound as a default arg — so tests can monkeypatch it and the suite stays ffmpeg-free"
  - "excerpt.py re-declares CUE_WINDOW_SECONDS/MAX_CUES_PER_TRACK locally (mirroring embed.py's values) rather than importing embed — keeps the module genai-free + import-light"

# Metrics
metrics:
  duration: "~25 min"
  completed: 2026-05-26
  tasks: 2
  files-created: 2
  files-modified: 2
---

# Phase 89 Plan 03: Cue-Anchored Excerpt Embedding Summary

Cue-anchored ≤80s mixable-window embedding for DJ-library ingest: a track's
DJ-placed hot/memory cues become `source="dj"` `CueAnchor`s (positions
authoritative, labels best-effort), un-cued tracks fall back to the offline
`detect_cues()` auto engine (`source="auto"`), and a no-structure track degrades
to a whole-track embed — so no track is ever anchor-less and never gets a faked
vector. `ingest_source` now mean-pools the per-window CLAP vectors instead of
embedding the whole file, with a strategy-version-namespaced content-hash cache.

## What Was Built

### Task 1 — `excerpt.py` (RED a3fe8cd → GREEN e6ca124)
- `anchors_for_track(track, *, max_cues=4, window_s=80.0) -> list[CueAnchor]`:
  filters the track's CuePoints to the structural set (`type in {cue,loop}`,
  hot or memory), sorts by `start_s`, caps at `max_cues`, maps each to a
  `source="dj"` anchor (hot-0 → `intro`, else `drop`, confidence 0.9), with
  `end_s = min(start + 80s, next_cue.start_s, duration_s)` and degenerate spans
  dropped. No usable cue → lazy-imports and delegates to `detect_cues` (auto);
  empty detect_cues → `[]` honestly.
- `cut_windows(anchors, duration_s) -> list[(start_s, end_s)]`: clamps to
  `[0, duration]`, keeps 1..80s spans, drops degenerate.
- Import-light: top level is stdlib + `cue_types` + `rekordbox`; torch-free.

### Task 2 — `ingest.py` rewire (RED 6cb6a77 → GREEN a7e4da9)
- `_embed_track_cue_anchored(track, local, embedder, *, slicer=None)`:
  `anchors_for_track` → `cut_windows` → per-window `_default_slicer` (ffmpeg
  `-ss/-t libmp3lame 128k`, mirrors `embed.LibraryEmbedder._slice_window`) →
  `embedder.embed_audio_bytes(clip, "audio/mpeg")` (per-window try/except skip)
  → `np.mean` + `l2_normalize`. Empty/all-failed/detect_cues-failure → whole-track
  `embed_audio_file` fallback (a real re-embed, never a faked vector).
- `INGEST_CUE_STRATEGY_VERSION = "v1-clap-cueanchored"` folded into the
  content-hash cache key (distinct from `INGEST_STRATEGY_VERSION` whole-track).
- `_Embedder` Protocol now requires `embed_audio_bytes` + `embed_audio_file`.
- Loop, resumable cache, `library.pkl` write, `IngestReport`, and dim
  reconciliation all preserved; `embed_strategy` now reports the cue tag.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Slicer monkeypatch was a no-op via default-arg binding**
- **Found during:** Task 2 GREEN
- **Issue:** `slicer: Callable = _default_slicer` bound the function at def time,
  so `monkeypatch.setattr(ingest, "_default_slicer", ...)` had no effect and the
  window tests shelled real ffmpeg (exit 183 on fake bytes).
- **Fix:** Changed the param to `slicer=None` and resolve `_default_slicer` from
  the module global at call time inside `_embed_track_cue_anchored`.
- **Files modified:** src/vibemix/library/ingest.py
- **Commit:** a7e4da9

**2. [Rule 2 - Missing critical functionality] detect_cues failure must degrade, not abort**
- **Found during:** Task 2 GREEN (Plan-01 e2e tests on fake-byte mp3s)
- **Issue:** `anchors_for_track`'s auto fallback shells `detect_cues`, which
  decodes audio via ffmpeg and raises `CalledProcessError` on a non-decodable
  file. Unwrapped, this aborted the whole track — violating T-89-09 (never
  anchor-less / never skip a track for lack of cues).
- **Fix:** Wrapped the `anchors_for_track` call in `_embed_track_cue_anchored`
  in try/except → `anchors = []` on failure → whole-track fallback. Mirrors
  `embed.py`'s `_embed_audio_cue_anchored` posture.
- **Files modified:** src/vibemix/library/ingest.py
- **Commit:** a7e4da9

**3. [Rule 3 - Test hygiene] autouse detect_cues stub keeps the suite ffmpeg-free**
- **Found during:** Task 2 GREEN
- **Issue:** Plan-01's e2e/resumability/failure tracks carry no DJ cues, so the
  auto fallback would shell real ffmpeg in the offline suite (honest-green
  contract: no ffmpeg).
- **Fix:** Added an autouse fixture stubbing `cue_detect.detect_cues` to `[]`
  (no-structure → whole-track), overridable by tests that need a specific auto
  result. Drives the Plan-01 whole-track fallback path cleanly, offline.
- **Files modified:** tests/library/test_ingest.py
- **Commit:** a7e4da9

## Verification

- `tests/library/test_excerpt.py` — 12 passed.
- `tests/library/test_ingest.py` — 8 passed (3 Plan-01 e2e/resumability/honest-
  failure still green + 5 new cue-anchored window-path tests).
- Import purity: `excerpt.py` and `ingest.py` import with `torch` NOT in
  `sys.modules` (CI-relevant guard).
- SQLCipher dormancy grep gate stays empty over `ingest.py` + `excerpt.py`.
- Full offline suite: **4751 passed, 27 skipped, 1 xfailed, 4 xpassed, 2 failed**
  (no network, no torch, no GEMINI_API_KEY, no real ffmpeg).

## Deferred Issues (out of 89-03 scope fence)

Both full-suite failures are owned by other sessions and were left untouched
(logged to `deferred-items.md`):

1. `tests/security/test_no_api_key_surface.py::test_no_api_key_label_text_anywhere_in_ui`
   — pre-existing Phase-88 frontend string (`tauri/ui/src/library/index.ts`), no
   89-03 file touches the UI.
2. `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline`
   — one NEW orphan, `build_set_prompt` in `src/vibemix/library/codex_curate.py`
   (a Set-Builder concurrent-session file, NOT a 89-03 file). 89-03's own new
   symbols are consumed by `ingest.py` and are not orphans. Refreshing
   `.planning/codebase/orphans.csv` is forbidden for this session (concurrent
   sessions own the baseline).

## TDD Gate Compliance

Both tasks followed RED → GREEN with atomic per-gate commits:
- Task 1: test a3fe8cd (RED) → feat e6ca124 (GREEN)
- Task 2: test 6cb6a77 (RED) → feat a7e4da9 (GREEN)

(Concurrent-session commit `58e1293` landed in the shared tree between gates; it
is unrelated to 89-03 and does not break the gate sequence.)

## Self-Check: PASSED

All created files exist (excerpt.py, test_excerpt.py, 89-03-SUMMARY.md) and all four
per-task commits (a3fe8cd, e6ca124, 6cb6a77, a7e4da9) are present in git history.
