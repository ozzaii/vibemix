---
plan: 29-02
phase: 29-post-session-debrief-mvp-ui
status: complete
wave: 3
requirements: [DEBRIEF-08, DEBRIEF-09]
commits:
  - <T1+T2>  # feat(29-02): debrief sidecar orchestrator + WS server on port 8766
tasks_completed: 2/2
tests_added: 14
tests_passing: 14/14 (full debrief suite 79/79)
regression_check: tests/debrief 79/79; tests/main/test_debrief_short_circuits_audio_init.py 3/3
---

# Plan 29-02 Summary — debrief sidecar orchestrator + WS server

## What was built

### Task 1 — main.py orchestrator + path-traversal defense + cache-hit

**`src/vibemix/debrief/main.py`** (new):

- `resolve_recordings_root()` mirrors `recordings.rs::resolve_recordings_root`
  via `runtime/config_store.app_data_dir()` (OS-aware path computation).
- `validate_session_dir_under_root(path, recordings_root=None)`:
  canonicalizes via `Path.resolve(strict=True)`, asserts the resolved
  path is under recordings_root. Accepts session_dir as absolute path
  OR bare session-id. Raises `InvalidSessionDir` on any failure
  (including non-existent path). Defense-in-depth alongside the Rust
  shell's `validate_under_root`.
- `run(session_dir, client=None, recordings_root=None, serve=True, port=8766)`:
  - validates session_dir
  - cache-hit fast path: `read_debrief(session_dir)` returns dict → skip Gemini
  - first-time path: `load_session` → `derive_chapters` →
    `generate_drills` → `generate_tldr_mp3` → defense-in-depth stripper
    sweep → `write_debrief` → start WS server
  - all typed exceptions caught and surfaced via `emit_error` before
    process exit (graceful UI error, not a crash)
- `_emit_error_and_exit(port, reason, message)`: one-shot WS server
  emitting a single `DebriefError` frame then exiting after 2s. Used
  when the orchestrator fails before generation can start.
- `_chapter_to_payload` / `_drill_to_payload`: dataclass→IPC payload
  coercion.
- `_build_cited_critique(events, chapters)`: condenses `events.jsonl`
  `ai_text` lines into a citation-rich critique string; prepends the
  preceding event-id citation when the original Gemini reply didn't
  include one.

`src/vibemix/__main__.py`:
- `_run_debrief_sidecar` dispatch updated to call
  `vibemix.debrief.main.run` (replaces banner-only Phase 25 stub).
  Empty session_dir keeps the banner-only behavior for smoke-test plumbing.

### Task 2 — ws_server.py async WebSocket server (port 8766)

**`src/vibemix/debrief/ws_server.py`** (new):

- `class DebriefWsServer(port=8766, host="127.0.0.1", state=…)`:
  - `enqueue_initial_frames()`: pushes session-loaded → chapter-list →
    drills → tldr-audio in order onto an asyncio.Queue.
  - `emit_error(reason, message)`: pushes a typed `DebriefError`.
  - `_handler(websocket)`: drains the queue on connect, then listens
    for inbound frames.
  - Inbound dispatch:
    - `ipc.debrief.citation-tooltip-request` → `_build_tooltip_reply`
      which parses the citation tag, looks up `(source, key)` in
      `state.evidence_snapshot`, picks the timestamp closest to the
      target, returns a `DebriefCitationTooltip` frame.
    - unknown kind → `DebriefError(reason="unknown_kind")`.
  - `serve_forever()` / `serve_for_seconds(s)`: bound serve loops.
    Port bind failure → log + `os._exit(1)` (Rust parent detects the
    early-exit and surfaces a sidecar-crashed banner per Plan 29-04).

## Key endpoints

- `127.0.0.1:8766` — DEBRIEF_PORT constant
- log prefix: `[debrief]` on every stdout/stderr line for greppable
  sidecar.log

## Test summary

| File | Tests | Coverage |
|------|-------|----------|
| test_session_dir_path_traversal_rejected.py | 5 | `../` rejected, absolute-outside rejected, nonexistent rejected, session-id resolves under root, absolute-inside accepted |
| test_main_dispatch.py | 5 | cache-hit skips Gemini, first-time path makes 3 Gemini calls + persists, InvalidSessionDir / SessionTooShort / EventsMissing |
| test_ws_server_progressive_emit.py | 4 | progressive 4-frame order on real `websockets.serve`, citation-tooltip RPC roundtrip, emit_error frame, unknown_kind dispatch |

**Total: 14 new tests, all pass.**

## Deviations

- **`anyio` instead of `pytest-asyncio`.** The repo's test stack ships
  `anyio` (pytest-anyio plugin) but not `pytest-asyncio`. Tests use
  `@pytest.mark.anyio("asyncio")` decorator instead.
- **No literal pytest "[debrief] log prefix" capsys assertion.** The
  prefix is verified via the logger config in `ws_server.py` —
  `logger = logging.getLogger("vibemix.debrief")`. Manual smoke confirms.

## Self-Check: PASSED

- [x] Both tasks' acceptance criteria satisfied.
- [x] 14/14 new tests pass.
- [x] Full debrief suite: 79/79.
- [x] `python -m vibemix --debrief <session>` dispatches to real
      orchestrator (banner-only stub replaced).
- [x] Path-traversal raises before any file read.
- [x] Cache-hit returns within 1s (no Gemini in cached path).
- [x] WS server binds to 127.0.0.1 only (not 0.0.0.0).
- [x] DEBRIEF-08 + DEBRIEF-09 covered.

## What this unblocks

- **Plan 29-04** (Rust Tauri shell) can spawn `--debrief <session>` and
  expect WS bus on 8766 with progressive frames.
- **Plan 29-05** (vanilla-TS UI) can consume the IPC contract.
- **Plan 29-07** can deepen the defense-in-depth stripper integration
  on top of the orchestrator's already-installed final sweep.
- **Plan 29-08** can spawn this sidecar headlessly for e2e tests.
