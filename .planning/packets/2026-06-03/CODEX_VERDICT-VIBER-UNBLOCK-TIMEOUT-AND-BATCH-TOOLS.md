# CODEX VERDICT — VIBER-UNBLOCK-TIMEOUT-AND-BATCH-TOOLS

- Item: Viber set-prep timeout + batch candidate inspection.
- Code SHA: `63cecda1 feat(viber): batch candidate inspection`.
- User value: a Pro/Studio user asking Viber for set prep now sees Viber inspect a whole candidate pool in one grounded tool call instead of crawling track-by-track.

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

## Gates

- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_mcp_server_clarification.py tests/library/test_codex_curate.py::test_build_set_prompt_has_set_prep_workflow` → 43 passed.
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py tests/library/test_mcp_server_clarification.py tests/library/test_codex_curate.py` → pass.
- `uv run pytest -q tests/library` → 1036 passed.
- `git diff --check` → pass.

## Notes

- HEAD already had build-set outer timeout at 180s and Codex MCP tool timeout at 60s. `CHAT_TIMEOUT_S` remains 90s.
- Parallelizing individual MCP calls would not help this path because FastMCP/dispatch execution is serialized; the shipped fix collapses repeated candidate probes into one `inspect_candidates(track_ids=[...])` call while preserving the `seen` grounding guard.
