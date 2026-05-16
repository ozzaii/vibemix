---
phase: 15-recording-session-capture-finalization
plan: 02
subsystem: recording
tags: [session-metadata, atomic-write, tauri-asset-protocol, csp, crash-detect, recorder]

# Dependency graph
requires:
  - phase: 02-audio-core-port-ring-buffer-fix
    provides: VoiceRecorder per-session WAV/JSONL writer
  - phase: 12-live-session-ui
    provides: ConfigStore + _app_data_dir() OS-aware path resolution
  - phase: 11-tauri-shell-sidecar-wizard
    provides: tauri.conf.json5 app.security shape + capabilities/default.json convention
provides:
  - session.json two-write writer (placeholder at __init__ + finalizer at close)
  - sweep_crashed_sessions boot-time crashed-session detector
  - Production recordings root resolved via app_data_dir() / "recordings"
  - Tauri assetProtocol enabled with scope $APPDATA/vibemix/recordings/** + $APPLOCALDATA/vibemix/recordings/**
  - CSP media-src 'self' asset: http://asset.localhost
  - Tauri Cargo features include protocol-asset (required by build script when assetProtocol.enable=true)
affects: [15-03 (RecordingsIndex consumes session.json), 15-04 (browser UI loads via asset://), 15-06 (verification gates these flows)]

# Tech tracking
tech-stack:
  added: []  # zero new pip / npm deps — built on stdlib (json, os, datetime, pathlib) + existing Tauri 2.x capability
  patterns:
    - "Two-write metadata: placeholder at session start, finalize at close → crash detection without sentinel files"
    - "Atomic JSON write recipe (tmp + os.replace) — copy of runtime/config_store.py:229-234"
    - "Public alias for private resolver (app_data_dir → _app_data_dir) when crossing module boundaries"
    - "Boot-only sweep: walk recordings/*/session.json, mark crashed=True on (ended_at_iso=None AND mtime>30s)"

key-files:
  created:
    - tests/recording/__init__.py
    - tests/recording/conftest.py
    - tests/recording/test_session_metadata.py
    - tests/recording/test_app_data_root_wiring.py
    - .planning/phases/15-recording-session-capture-finalization/deferred-items.md
  modified:
    - src/vibemix/audio/recorder.py
    - src/vibemix/__main__.py
    - src/vibemix/runtime/config_store.py
    - tauri/src-tauri/tauri.conf.json5
    - tauri/src-tauri/capabilities/default.json
    - tauri/src-tauri/Cargo.toml
    - tauri/src-tauri/Cargo.lock

key-decisions:
  - "session.json schema version pinned to 1.0 as first field (autonomous resolution #5)"
  - "Two-write pattern (placeholder + finalizer) over single-write-at-close — only way to surface crashed sessions without a sentinel file"
  - "Atomic write via tmp + os.replace mirroring ConfigStore.save() at config_store.py:229-234"
  - "Crashed-session sweep is boot-only (autonomous resolution #4); mid-session sweeps would race the active session"
  - "Sweep predicate is (ended_at_iso=None AND mtime older than 30s) — both required so the active session is left alone"
  - "Public app_data_dir() alias added to config_store.py rather than crossing the underscore boundary with noqa"
  - "VoiceRecorder constructor default unchanged (Path.cwd()/recordings) — cohost_v4.py POC compat rule"
  - "Asset protocol scope locks BOTH $APPDATA and $APPLOCALDATA variants — defensive Windows coverage per RESEARCH Pitfall 2"
  - "CSP media-src directive appended; no existing directive modified — preserves every Phase 11+13 invariant"
  - "Tauri Cargo features += protocol-asset — required by build script when assetProtocol.enable=true (Rule 3 deviation; auto-fixed)"
  - "Capability allowlist description amended (load-bearing comment per Phase 11 W4) — no new permission identifier; asset protocol is plugin-less in Tauri 2"

patterns-established:
  - "Pattern 1: Two-write session.json — placeholder at __init__, finalize at close. Crash-detect emerges from absence of ended_at_iso + stale mtime."
  - "Pattern 2: _atomic_write_json module-level helper at vibemix/audio/recorder.py:43 — re-usable across the recorder family without taking a dependency on runtime/config_store.py"
  - "Pattern 3: sweep_crashed_sessions(root, mtime_age_s=30) — idempotent best-effort walker; skips legacy + busted-JSON dirs; returns list of dirs marked"
  - "Pattern 4: _resolve_recordings_root() helper in __main__.py — test-able wire-site for the production recordings root; pure forwarder over app_data_dir()"

requirements-completed:
  - REC-01
  - REC-04

# Metrics
duration: 25min
completed: 2026-05-13
---

# Phase 15 Plan 02: Recording metadata + Tauri asset protocol Summary

**Two-write session.json with crash-detect, production recordings root wired to OS-aware app_data_dir, and Tauri assetProtocol exposed under $APPDATA/$APPLOCALDATA/vibemix/recordings/** with CSP media-src updated for <audio src="asset://...">.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-13T13:51 UTC
- **Completed:** 2026-05-13T14:16 UTC
- **Tasks:** 2
- **Files created:** 5
- **Files modified:** 7

## Accomplishments

- `VoiceRecorder.__init__` now writes a 16-field placeholder session.json (session_json_version="1.0" first, vibemix_version, started_at_iso/_unix, ended_at_iso=None, ended_at_unix=None, duration_s=None, voice/mode/genre/user_level, event_count=0, three *_bytes at 0, crashed=False) — atomic write via tmp + os.replace.
- `VoiceRecorder.close()` now calls `_finalize_session_meta` which rewrites session.json atomically with the real ended_at, duration_s, byte counts (post-handle-close so wave.close()'s RIFF length patch is reflected), and JSONL line count minus the session_start marker line.
- New module-level `sweep_crashed_sessions(recordings_root, mtime_age_s=30)` walks `recordings/*/session.json` and marks crashed=True on dirs whose ended_at_iso is None AND mtime older than 30s. Idempotent (already-marked sessions have ended_at_iso set and don't re-match). Skips legacy dirs and busted JSON.
- `vibemix.__main__._resolve_recordings_root()` resolves to `app_data_dir() / "recordings"` (the new public alias in config_store.py forwards to the existing `_app_data_dir()` resolver). Production `python -m vibemix` now constructs `VoiceRecorder(root=recordings_root)` explicitly AND runs `sweep_crashed_sessions(recordings_root)` at boot.
- `tauri.conf.json5` `app.security` gains a `media-src 'self' asset: http://asset.localhost` directive in the CSP plus a new `assetProtocol` block with `enable=true` and scope `["$APPDATA/vibemix/recordings/**", "$APPLOCALDATA/vibemix/recordings/**"]`.
- `tauri/src-tauri/Cargo.toml` `tauri` features += `protocol-asset` (Rule 3 deviation — Tauri 2's build script requires this matching feature flag when `assetProtocol.enable=true`).
- `tauri/src-tauri/capabilities/default.json` description string amended with the assetProtocol surface note (load-bearing comment per Phase 11 W4 convention; no new permission identifier needed — asset protocol is plugin-less in Tauri 2).
- POC compat preserved: `VoiceRecorder()` no-args still defaults to `Path.cwd() / "recordings"` so `cohost_v4.py` continues to work unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: VoiceRecorder gains session.json write + crashed-session boot sweep** — `e6ccf2a` (feat) — 4 files, 657 insertions
2. **Task 2: Wire production recordings root + Tauri assetProtocol + CSP** — `95a6672` (feat) — 8 files, 143 insertions

## Files Created/Modified

### Created

- `tests/recording/__init__.py` — empty package marker.
- `tests/recording/conftest.py` — `tmp_recordings_dir` + `make_fake_session` fixtures; the factory writes synthetic session.json with controllable shape + mtime so sweep tests can simulate (active vs stale) × (ended vs unended) × (crashed vs clean) without spinning up a real VoiceRecorder.
- `tests/recording/test_session_metadata.py` — 6 tests covering: init shape (all 16 fields, session_json_version="1.0" first), close finalize (ended_at + duration + byte counts), atomic-write survives mid-rewrite OSError, sweep marks stale unended only (active + clean left untouched), sweep idempotent, sweep skips legacy + busted JSON dirs.
- `tests/recording/test_app_data_root_wiring.py` — 2 tests pinning `_resolve_recordings_root() == app_data_dir() / "recordings"` AND the helper does no mkdir (VoiceRecorder owns the create with mode=0o700).
- `.planning/phases/15-recording-session-capture-finalization/deferred-items.md` — pre-existing cargo-check blocker (missing PyInstaller sidecar binary; out of scope for Plan 15-02).

### Modified

- `src/vibemix/audio/recorder.py` — `SESSION_JSON_VERSION="1.0"` module constant, `_atomic_write_json` module-level helper (mirrors config_store.py:229-234), `sweep_crashed_sessions` module-level walker, `VoiceRecorder.__init__` extended with 4 optional kwargs (voice_id/mode/genre/user_level) + placeholder session.json write, `VoiceRecorder.log_event` mirrors event_count under the lock (no disk-write amplification), `VoiceRecorder._finalize_session_meta` rewrites session.json atomically from `close()` AFTER handles close so st_size returns final flushed sizes.
- `src/vibemix/__main__.py` — added `_resolve_recordings_root()` helper, imports `sweep_crashed_sessions` + `app_data_dir`, main() now calls the sweep at boot + constructs `VoiceRecorder(root=recordings_root)`.
- `src/vibemix/runtime/config_store.py` — added public `app_data_dir()` alias forwarding to `_app_data_dir()`. Pure forwarder; no behavior change.
- `tauri/src-tauri/tauri.conf.json5` — `app.security.csp` appended `media-src 'self' asset: http://asset.localhost`. `app.security.assetProtocol` added with `enable=true` + dual `$APPDATA`/`$APPLOCALDATA` scope.
- `tauri/src-tauri/capabilities/default.json` — description string amended with assetProtocol surface note.
- `tauri/src-tauri/Cargo.toml` — `tauri` features += `protocol-asset` (build-script-required matching feature flag).
- `tauri/src-tauri/Cargo.lock` — regenerated by `cargo check` after the feature add.

## Decisions Made

All decisions were locked by the plan + autonomous resolutions; no new decisions taken during execution. Notable lock-ins applied:

- session.json includes `session_json_version: "1.0"` as first field (autonomous resolution #5).
- Crashed-session sweep is boot-only (autonomous resolution #4) — mid-session sweeps would race the active session.
- `_finalize_session_meta` re-counts events.jsonl lines (minus session_start) for authoritative event_count; the in-memory counter is a fallback.
- Sweep skips legacy dirs (no session.json — RESEARCH Pitfall 9) and JSON-parse-failure dirs (best-effort, no raise).
- Sweep is idempotent by construction: marked sessions have ended_at_iso set, so they no longer match the (ended_at_iso=None) predicate on the next pass.
- Public `app_data_dir()` alias added to config_store.py — cleaner than a noqa-tagged underscore import at the call site.
- Capability allowlist description-string amendment (not a new permission) per Phase 11 W4 convention.
- The asset:// scheme uses Tauri's built-in protocol (autonomous resolution #1 — superseded CONTEXT.md's `recording://` custom scheme). No Rust URI handler needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tauri build script required `protocol-asset` Cargo feature flag**

- **Found during:** Task 2 cargo-check sanity gate.
- **Issue:** Setting `assetProtocol.enable = true` in `tauri.conf.json5` triggers the Tauri 2 build script to assert the Cargo-side feature allowlist matches. Without `protocol-asset` in the `tauri` features list, `cargo check` errors with: `The tauri dependency features on the Cargo.toml file does not match the allowlist defined under tauri.conf.json. Please run tauri dev or tauri build or add the protocol-asset feature.`
- **Fix:** Added `protocol-asset` to `tauri/src-tauri/Cargo.toml` `tauri` features list. Cargo.lock auto-regenerated by the next `cargo check`. Documented in the Cargo.toml comment line with the Phase 15 Plan 02 rationale.
- **Files modified:** `tauri/src-tauri/Cargo.toml`, `tauri/src-tauri/Cargo.lock`.
- **Verification:** `cargo check` now passes the feature allowlist gate (the only remaining error is the pre-existing missing-sidecar-binary check; logged in deferred-items.md).
- **Committed in:** `95a6672` (Task 2 commit).

---

**Total deviations:** 1 auto-fixed (1 Rule 3 blocking).
**Impact on plan:** Single auto-fix essential for the assetProtocol surface to compile. No scope creep — `protocol-asset` is the canonical Tauri-2 feature flag matching the runtime assetProtocol config.

## Issues Encountered

- **Worktree branch divergence:** The worktree branch (`worktree-agent-a2475047ee876369c`) was at Phase 6 commit (`6e6dd9f`), 5 commits behind `main` (`3e16b6e`). Rebased onto `main` (strict ancestor, fast-forward equivalent) to bring all Phase 15 planning artifacts + Phase 7-14 source into the worktree. No conflicts.
- **PYTHONPATH override needed:** The venv at `/Users/ozai/projects/dj-set-ai/.venv` has `vibemix` installed editable against the main repo's `src/`. To make pytest import from the worktree's `src/` (where Plan 15-02 edits land), all test runs used `PYTHONPATH=src` to take precedence over the editable install path.
- **`tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` fails in worktree:** Test expects `cohost_v4.py` to exist at repo root; the POC file is untracked in git and therefore not present in this worktree. Pre-existing environmental artifact unrelated to Plan 15-02. Out of scope per execute-plan.md scope-boundary rule.

## Threat Surface

No new security-relevant surface introduced beyond what the `<threat_model>` already covered. The assetProtocol scope is scope-limited and Tauri resolves real paths (no symlink escape per T-15-02-02 mitigation). CSP media-src directive added; no other directives modified.

## Next Phase Readiness

Plan 15-02 provides:

- **Plan 15-03 (RecordingsIndex)** can now read `session.json` to surface crashed sessions in the browser UI list (the LED dot status) and to compute disk usage without re-scanning every WAV header.
- **Plan 15-04 (browser UI)** can drop `<audio src={convertFileSrc(absPath)} controls />` into recording rows — the assetProtocol + CSP media-src make the URL resolve and play.
- **Plan 15-06 (verification)** can pin the session.json schema fields + the asset:// playback path against the soak test.

No blockers passed forward. The pre-existing `cargo check` missing-sidecar-binary error is a Phase 11 W1 workflow gate (run `scripts/build_sidecar.py` first); not a Plan 15-02 concern.

## Self-Check

Verified all claims against disk before writing this section.

### Files exist

```
FOUND: src/vibemix/audio/recorder.py
FOUND: src/vibemix/__main__.py
FOUND: src/vibemix/runtime/config_store.py
FOUND: tauri/src-tauri/tauri.conf.json5
FOUND: tauri/src-tauri/capabilities/default.json
FOUND: tauri/src-tauri/Cargo.toml
FOUND: tauri/src-tauri/Cargo.lock
FOUND: tests/recording/__init__.py
FOUND: tests/recording/conftest.py
FOUND: tests/recording/test_session_metadata.py
FOUND: tests/recording/test_app_data_root_wiring.py
FOUND: .planning/phases/15-recording-session-capture-finalization/deferred-items.md
```

### Commits exist

```
FOUND: e6ccf2a (Task 1 — VoiceRecorder gains session.json write + crashed-session boot sweep)
FOUND: 95a6672 (Task 2 — Wire production recordings root + Tauri assetProtocol + CSP)
```

### Done criteria

```
PASS: grep -c "session_json_version" src/vibemix/audio/recorder.py = 2 (≥2)
PASS: grep -c "sweep_crashed_sessions" src/vibemix/audio/recorder.py = 2 (≥1)
PASS: grep -c "assetProtocol" tauri/src-tauri/capabilities/default.json = 1 (≥1)
PASS: tauri.conf.json5 parses + has media-src + asset: in CSP + both scope variants
PASS: 6 tests in test_session_metadata.py pass
PASS: 2 tests in test_app_data_root_wiring.py pass
PASS: 8 existing recorder tests in tests/audio/test_recorder.py still pass
PASS: POC compat — VoiceRecorder() no-args still defaults to cwd/recordings
PASS: full plan suite (audio + ui_bus + runtime + recording) — 210 passes
PASS: IPC schema baseline unchanged at 27 (this plan did not touch IPC families)
```

## Self-Check: PASSED

---
*Phase: 15-recording-session-capture-finalization*
*Plan: 02*
*Completed: 2026-05-13*
