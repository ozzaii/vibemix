# CODEX_VERDICT-VIBER-BATCH-TOOLS

Item: Viber build-set timeout / one-by-one candidate inspection

SHA: `aa9a8e3e`

User value: A Pro/Studio user on Viber set prep now gets the fast grounded tool path instead of burning the live UI window on candidate-by-candidate inspection.

What changed:
- `inspect_candidates` now parallelizes per-candidate deterministic reads while preserving row order and grounding.
- `LibraryToolset` now locks the lazy genre lookup and section registry writes used by the parallel batch path.
- The set-prep Codex prompt now names the expected tape: `discover_pool -> sequence_set -> export_set`, choose the first/best `sequence_set` candidate, and avoid one-by-one candidate inspection.

By-eye artifact:
- Command: `VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library build-set "fast hardgroove opener, 6 tracks, 128-134 bpm" --curve opener --n-slots 6 --export rekordbox --backend codex --json`
- Observed tape: `discover_pool ok ... 15 tracks` -> `sequence_set ok opener; 15 tracks; slots=6; 2 candidates` -> `export_set ok Fast Hardgroove Opener; 6 tracks`.
- Result: `stop_reason="exported"` with Rekordbox XML at `/Users/ozai/.cache/vibemix/sets/fast-hardgroove-opener.xml`.
- Honest receipt: Viber noted BPM metadata was missing across the discovered pool and did not claim the requested `128-134 bpm` range was verified.

Verification:
- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_codex_curate.py tests/library/test_codex_curate_stop_reason.py tests/library/test_cli_exit_codes.py` -> `148 passed`
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py tests/library/test_codex_curate.py` -> passed
- `git diff --check -- src/vibemix/library/toolset.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py tests/library/test_codex_curate.py` -> passed

Notes:
- This does not invent a deterministic replacement for Viber. Codex still chooses and writes the final set; the deterministic tools provide the grounded facts and fast batch execution.
- The Tauri bridge has no separate 90s UI timer in source; current Python build-set timeout is 180s. The observed 90s problem is consistent with slow/serial candidate checking or stale UI copy, not a Rust/webview cutoff.
