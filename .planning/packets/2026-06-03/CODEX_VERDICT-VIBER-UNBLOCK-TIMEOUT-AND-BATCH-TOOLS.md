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

## Follow-Up — Batch Budget Fix (`a17d905b`)

- Item: Viber batch candidate inspection still had the old tiny per-tool budget.
- SHA: `a17d905b fix(viber): let batch inspection finish`
- User value: a Pro/Studio user can let Viber inspect a whole candidate pool without the fused call being killed like a one-track lookup.

### By-Eye Artifact

Real current-source build-set run:

```bash
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library build-set \
  "fast hardgroove opener, 6 tracks, 128-134 bpm" \
  --curve opener --n-slots 6 --export rekordbox --backend codex --json
```

Observed tool tape:

```text
[viber-tool] discover_pool ok fast hardgroove opener; bpm=128.0-134.0; k=15; 15 tracks; bpm_unknown=15/15
[viber-tool] sequence_set ok opener; 15 tracks; slots=6; 3 candidates
[viber-tool] export_set ok Fast Hardgroove Opener; 6 tracks
```

Result: `stop_reason="exported"`, exported XML at `/Users/ozai/.cache/vibemix/sets/fast-hardgroove-opener.xml`.

Real current-source chat run forcing candidate inspection:

```bash
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat \
  "Find a handful of fast hardgroove candidates from my library and inspect their BPM, key, sections, and energy before you answer. Keep it concise." \
  --backend codex --json
```

Observed tool tape:

```text
[viber-tool] discover_pool ok fast hardgroove techno percussive driving 128-138 BPM; bpm=128.0-138.0; k=6; 6 tracks; bpm_unknown=6/6
[viber-tool] inspect_candidates ok 6 tracks; 6 candidate inspections
```

Result: `stop_reason="model_done"`, two tool iterations, and no serial `get_track_features` / `get_track_sections` / `get_track_energy` loop.

Real app proof:

- Relaunched Tauri dev against current source with `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
- `ws://127.0.0.1:8765` reachable; status tick showed `gemini=ok`, `livekit=ok`, `midi=1`.
- UI/session logs showed music meter moving and voice meter at/near zero after the live reaction; no current speech loop.

### Gates

- `uv run pytest -q tests/library/test_setprep_tools.py::test_dispatch_gives_batched_candidate_inspection_a_larger_timeout tests/library/test_setprep_tools.py::test_inspect_candidates_parallelizes_rows tests/library/test_setprep_tools.py::test_inspect_candidates_batches_features_sections_and_energy tests/library/test_codex_curate.py::test_chat_timeout_is_interactive tests/library/test_codex_curate.py::test_codex_mcp_tool_timeout_allows_batched_candidate_inspection` -> 5 passed.
- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_codex_curate.py` -> 125 passed.
- `uv run pytest -q tests/library` -> 1040 passed.
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py tests/library/test_codex_curate.py` -> pass.
- `git diff --check` -> pass.

### Notes

- Current source chat/build-set wall-clock is 180s, not 90s.
- This follow-up raises the Codex MCP tool timeout from 60s to 120s and gives `inspect_candidates` a matching `BATCH_TOOL_CALL_TIMEOUT_S=120.0`; tiny tools keep the 30s dispatch budget.
- No signed/package rebuild was performed in this loop; package status remains a separate release lane.
