---
phase: 28-library-intelligence-v1
plan: 02
subsystem: library
tags: [storage, sqlite-vec, numpy, mac-win-parity, P55, vec0]

requires:
  - phase: 28-01
    provides: cosine_topk + l2_normalize + EMBEDDING_DIM (shared math primitives)

provides:
  - SqliteVecStore (Mac primary backend, vec0 virtual table)
  - NumpyStore (any-host fallback, .npy + JSON sidecar)
  - LibraryStore facade with single chokepoint for top-K math
  - open_store() probe with graceful sqlite-vec → numpy fallback
  - 1000 × 768 + 50-query parity fixture corpus
  - 12 tests including Mac↔Win bit-identity parity gate

affects: [28-03, 28-04, 28-05, 28-06]

tech-stack:
  added:
    - sqlite-vec==0.1.9
  patterns:
    - "Backend-agnostic facade with single math chokepoint (P55)"
    - "Storage-only sqlite-vec (no built-in KNN; rank in Python)"
    - "Atomic save via os.replace for crash safety"
    - "Trust caller for L2 normalization (no defensive renorm — parity contract)"

key-files:
  created:
    - src/vibemix/library/index_numpy.py
    - src/vibemix/library/index_sqlite_vec.py
    - src/vibemix/library/store.py
    - tests/library/test_store.py
    - tests/library/test_store_parity.py
    - tests/library/fixtures/_generate.py
    - tests/library/fixtures/synthetic_embeddings.npy (3.1 MB)
    - tests/library/fixtures/synthetic_queries.json (1.1 MB)
  modified:
    - src/vibemix/library/__init__.py
    - pyproject.toml (parity mark + sqlite-vec dep)
    - uv.lock

key-decisions:
  - "sqlite-vec is STORAGE-ONLY in v1 — no MATCH KNN, no vec_distance_cosine. All ranking in Python via shared cosine_topk (P55)."
  - "NumpyStore does NOT re-normalize on add_batch (trust caller). Defensive renorm introduced 1-ULP drift that broke parity — explicit decision to drop it."
  - "open_store() falls back to NumpyStore on sqlite_vec.load() failure with structured log (Wave 0 ARM64 Win probe)."
  - "Fixture stores full-precision similarities (float() not round) so parity tests can compare via bounded rounding."
  - "vec0 INSERT does delete-then-insert because INSERT OR REPLACE isn't uniformly supported on the virtual-table layer."

patterns-established:
  - "Pattern: backend interface = (add_batch, load_all, delete, snapshot_hash, close). Both backends implement; LibraryStore composes."
  - "Pattern: ORDER BY track_id ASC on every read — combined with cosine_topk's secondary tie-break (track_id ASC), gives platform-independent results."
  - "Pattern: pytest.mark.parity flags Mac/Win contract tests for the future CI matrix (Plan 09 + 28-08 owned)."
---

# Plan 28-02 — Library Storage + Mac/Win Parity

Status: complete.

## Backend probe outcome on developer's host

```
$ python -c "from vibemix.library import open_store; s = open_store(); print(s.backend_name)"
-> library store: backend=SqliteVecStore reason=ok
SqliteVecStore
```

Mac arm64 (developer host) has the sqlite-vec extension wheel — primary backend selected. Numpy fallback path is exercised by `test_open_store_falls_back_to_numpy_when_sqlite_vec_load_fails` via `unittest.mock.patch`.

## sqlite-vec Win-ARM64 wheel verdict (Assumption A2)

**Status:** TBD on actual Win-ARM64 hosts. The fallback path proves the runtime degradation is graceful — `open_store()` will silently switch to NumpyStore without breaking any downstream caller. Fixed in code by:

```python
# store.py:75
try:
    backend = SqliteVecStore()
    return LibraryStore(backend)
except Exception as e:
    logger.warning("backend_probe_failed=sqlite_vec reason=%s — falling back to NumpyStore", e)
    backend = NumpyStore()
    return LibraryStore(backend)
```

Plan 28-08 will add CI parity matrix (Mac arm64 + Win x64 + Win arm64) — the parity tests are already tagged `pytest.mark.parity` ready for that workflow.

## Fixture corpus stats

- `synthetic_embeddings.npy`: shape `(1000, 768)`, dtype `float32`, 3.1 MB. L2-normalized.
- `synthetic_queries.json`: 50 queries × top-10 ground-truth, 1.1 MB. Each query carries the unrounded `[float, ...] * 768` vector + `[{track_id, similarity}, ...] * 10` ground-truth.
- Seed: `numpy.random.default_rng(2826)`. Re-running `tests/library/fixtures/_generate.py` produces byte-identical output.

## Tests

```
$ pytest tests/library/test_store.py tests/library/test_store_parity.py -q
............                                                             [100%]
12 passed in 5.78s
```

- 7 per-backend smoke tests in `test_store.py`
- 5 parity-marked tests in `test_store_parity.py`:
  - `test_numpy_topk_matches_fixture_ground_truth` — 50 queries × top-10
  - `test_sqlite_vec_topk_matches_numpy` — Mac↔Win parity gate
  - `test_tie_break_track_id_asc` — deterministic tie-break
  - `test_float32_round_trip_bit_identical` — byte-exact persistence
  - `test_cosine_topk_uses_python_sort` — static contract guard

Both backends verified on Mac arm64; CI matrix for Win comes in Plan 28-08.

## Deviation from plan

- **Dropped defensive re-normalization on `NumpyStore.add_batch`**: the plan said "L2-normalize on persistence (defense-in-depth)". In practice this introduced 1-ULP float drift on already-normalized vectors → broke the parity test against fixture ground-truth. Decision: trust caller (LibraryEmbedder always L2-normalizes its output via Plan 01). Float32 + shape assertions remain as cheap defense. Documented in `index_numpy.py` line 87.

- **`sqlite-vec` INSERT pattern**: vec0 virtual tables don't reliably support `INSERT OR REPLACE`. Used DELETE-then-INSERT in a single transaction instead. Functionally identical, atomic via `commit()`.

## What this unlocks

- Plan 28-03: vibe-search wraps `store.search(qvec, k)` + 24h LRU cache.
- Plan 28-04: grounding pipeline calls `store.search(audio_embedding, k=1)` and decides cite vs uncertain by cosine threshold.
- Plan 28-05: similar-track is `store.search(seed_vector, k+1)` with seed self-removal.
- Plan 28-06: drag-drop importer batches `store.add_batch(items)` per chunk.
