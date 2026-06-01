# CODEX_READY: Runtime Memory CLAP Readiness

Date: 2026-06-01
Verifier: Codex
Package: 12 - Runtime Memory CLAP Readiness
Suggested commit: `fix(memory): reconcile stale sqlite-vec embedding dimensions`
Decision: LAND, as runtime memory and CLAP readiness hardening only

## Scope

Include:

- `src/vibemix/memory/index_sqlite_vec_memory.py`
- `src/vibemix/runtime/session_loop.py`
- `tests/memory/test_ingest_wiring.py`
- `tests/memory/test_store_parity.py`

Keep out:

- Library-folder ingest dimension reconciliation.
- Mix/audio hold-lane files.
- Final Tauri/DDJ live acceptance.

Shared-file caution:

- `src/vibemix/runtime/session_loop.py` also carries non-Package-12 hunks for
  drop prediction and legacy timestamp normalization. Stage by hunk if this
  package lands independently.

## What Is Proven

Runtime memory now handles sqlite-vec dimension drift without silently mixing
CLAP embeddings:

- `SqliteVecMemoryStore.__init__` loads sqlite-vec, creates the current
  `FLOAT[EMBEDDING_DIM]` table, ensures the sibling `moments` schema, and then
  reconciles the declared vector dimension before the store is accepted
  (`src/vibemix/memory/index_sqlite_vec_memory.py:74-108`).
- Empty stale vec tables are recreated at the current embedding dimension, and
  unbacked `moments` rows are cleared (`index_sqlite_vec_memory.py:139-153`,
  `index_sqlite_vec_memory.py:217-223`).
- Populated stale vec tables are refused with a hard RuntimeError so
  `MemoryStore` falls back instead of wiping user memory or mixing dimensions
  (`index_sqlite_vec_memory.py:155-160`).
- Store inspection helpers expose `vector_dim()`, `row_count()`, and
  `recreate_table()` for tests and future migrations
  (`index_sqlite_vec_memory.py:203-223`).

Runtime session ingest is best-effort and off the hot path:

- `_build_ingest_embedder()` constructs the local CLAP embedder lazily
  (`src/vibemix/runtime/session_loop.py:868-877`).
- `_fire_ingest()` skips when disabled or rootless, imports `memory.ingest`
  inside the worker, dispatches via `loop.run_in_executor`, closes the store,
  and swallows/logs failures instead of crashing boot or close
  (`session_loop.py:879-954`).
- Diagnostic `run_session()` constructs `SessionLoop(memory_ingest_enabled=False)`,
  so sidecar health checks do not launch CLAP memory indexing
  (`session_loop.py:1460-1468`).

Tests cover both correctness and the operational boundary:

- Empty stale 768-dim sqlite-vec tables self-heal before a current 512-dim insert
  (`tests/memory/test_store_parity.py:123-148`).
- Populated stale sqlite-vec tables fall back to `NumpyStore` instead of being
  wiped (`tests/memory/test_store_parity.py:151-169`).
- Source-text and behavioral gates prove the runtime imports `memory.ingest`
  only through the off-loop worker, dispatches boot/close through
  `run_in_executor`, skips rootless and disabled loops, swallows failures, keeps
  main-path ingest behind `recall_enabled`, and disables ingest for diagnostic
  `--session` (`tests/memory/test_ingest_wiring.py:89-112`,
  `tests/memory/test_ingest_wiring.py:149-219`,
  `tests/memory/test_ingest_wiring.py:295-325`).

## Verification

Model readiness:

```text
uv run python -m vibemix library models --json
```

Result:

- CLAP ONNX installed: true
- CUE-DETR installed: true
- `required_ready: true`
- `all_ready: true`

Focused tests:

```text
uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py
```

Result:

```text
34 passed in 0.35s
```

Lint:

```text
uv run ruff check src/vibemix/runtime/session_loop.py src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py
```

Result:

```text
All checks passed!
```

Diagnostic live bus proof:

```text
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session
```

Observed:

- session bus reached `127.0.0.1:8765`
- MCP `sidecar_status` reported `ws_reachable: true`
- MCP `ws_observe(seconds=2, type_filter="ipc.session.snapshot")` captured 56
  session snapshot frames
- Ctrl-C exited cleanly with `memory ingest (boot) skipped: disabled for this
  session loop` and `memory ingest (close) skipped: disabled for this session
  loop`
- A follow-up MCP `sidecar_status` reported `ws_reachable: false`, confirming the
  diagnostic runtime was stopped

Whitespace:

```text
git diff --check -- src/vibemix/memory/index_sqlite_vec_memory.py src/vibemix/runtime/session_loop.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py
```

Result: clean.

## Boundaries

This packet does not claim:

- packaged Tauri app proof
- DDJ/FLX4 hardware proof
- live co-host memory recall quality proof
- library-folder ingest dimension reconciliation
- that all memory/search product surfaces are ready

It proves the runtime memory/CLAP readiness slice is safe to land and no longer
silently mixes stale sqlite-vec dimensions or launches CLAP indexing during the
diagnostic `--session` probe.
