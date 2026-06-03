# CODEX VERDICT — VIBER-UNBLOCK-TIMEOUT-AND-BATCH-TOOLS

- Item: Viber set-prep timeout + batch candidate inspection.
- Code SHAs:
  - `63cecda1 feat(viber): batch candidate inspection`
  - `762462a0 fix(viber): give chat the set-prep timeout budget`
  - `fafe5c37 fix(viber): surface unverified bpm metadata`
- User value: a Pro/Studio user asking Viber for set prep now sees Viber inspect a whole candidate pool in one grounded tool call instead of crawling track-by-track, and chat turns get the same 180s wall-clock budget as build-set while the live tool tape shows progress.

## By-Eye Artifact

Real CLI run:

```bash
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library build-set \
  "dark warehouse pressure, 3 tracks, include candidate receipts before choosing" \
  --curve peak_time --n-slots 3 --export rekordbox --name "Batch Inspect Proof" --json
```

Observed tool tape:

```text
[viber-tool] discover_pool ok dark warehouse pressure peak-time techno set, focused and mixable; k=15; 15 tracks
[viber-tool] inspect_candidates ok 15 tracks; 15 candidate inspections
[viber-tool] sequence_set ok peak_time; 15 tracks; slots=3; 4 candidates
[viber-tool] export_set ok Batch Inspect Proof; 3 tracks
```

Result: `stop_reason="exported"`, exported XML exists at `/Users/ozai/.cache/vibemix/sets/batch-inspect-proof.xml`.

Real chat run after raising the chat wall-clock:

```bash
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat \
  "Build me a tight 3-track peak-time set from my library. Inspect the candidate pool once before choosing, include the candidate receipts, and return the chosen track IDs." \
  --json
```

Observed tool tape:

```text
[viber-tool] discover_pool ok tight 3-track peak-time set driving club energy 128-138 bpm; bpm=128.0-138.0; k=12; 12 tracks
[viber-tool] inspect_candidates ok 12 tracks; 12 candidate inspections
[viber-tool] sequence_set ok peak_time; 12 tracks; slots=3; 4 candidates
[viber-tool] create_playlist ok Viber Peak-Time 3; 3 tracks; 3 tracks
```

Result: `stop_reason="created"`, four tool iterations, playlist artifact `/Users/ozai/.cache/vibemix/playlists/viber-peak-time-3-1780489511.m3u8`.

Real chat run for the BPM metadata honesty follow-up:

```bash
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat \
  "Build me a tight 3-track peak-time 128-138 BPM set from my library. Inspect candidates once and be honest if BPM metadata is missing." \
  --json
```

Observed tool tape:

```text
[viber-tool] discover_pool ok peak-time driving club energy tight 3-track set; bpm=128.0-138.0; k=12; 12 tracks; bpm_unknown=12/12
[viber-tool] inspect_candidates ok 12 tracks; 12 candidate inspections
[viber-tool] sequence_set ok peak_time; 12 tracks; slots=3; 4 candidates
[viber-tool] create_playlist ok Peak-time 128-138 BPM metadata-check draft; 3 tracks; 3 tracks
```

Observed Viber reply included the honest line: the library metadata is missing BPM/key for the candidate pool, so Viber cannot verify the `128-138 BPM` requirement or harmonic lane; it sequenced by inspected energy and playable length instead. Result: `stop_reason="created"`, playlist artifact `/Users/ozai/.cache/vibemix/playlists/peak-time-128-138-bpm-metadata-check-draft-1780489917.m3u8`.

## Gates

- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_mcp_server_clarification.py tests/library/test_codex_curate.py::test_build_set_prompt_has_set_prep_workflow` → 43 passed.
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py tests/library/test_mcp_server_clarification.py tests/library/test_codex_curate.py` → pass.
- `uv run pytest -q tests/library` → 1036 passed.
- `uv run pytest -q tests/library/test_codex_curate.py::test_chat_timeout_is_interactive` → 1 passed.
- `uv run pytest -q tests/library/test_codex_curate.py` → 89 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py` → pass.
- `uv run pytest -q tests/library/test_setprep_tools.py::test_discover_pool_marks_unverified_bpm_filter tests/library/test_codex_curate.py::test_build_set_prompt_has_set_prep_workflow tests/library/test_codex_curate.py::test_chat_prompt_threads_history_and_rules` → 3 passed.
- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_codex_curate.py` → 122 passed.
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py tests/library/test_codex_curate.py` → pass.
- `git diff --check` → pass.

## Notes

- HEAD already had build-set outer timeout at 180s and Codex MCP tool timeout at 60s. Chat now uses `BUILD_SET_TIMEOUT_S` too.
- Parallelizing individual MCP calls would not help this path because FastMCP/dispatch execution is serialized; the shipped fix collapses repeated candidate probes into one `inspect_candidates(track_ids=[...])` call while preserving the `seen` grounding guard.
- The proof run also showed these local cache rows have `bpm: null` / `camelot: null`; that is a separate metadata/cache lane, not a timeout or batch-inspection failure.
