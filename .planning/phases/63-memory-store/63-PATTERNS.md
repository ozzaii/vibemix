# Phase 63: Memory Store - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 9 new (3 src + 6 test) + 1 conditional modify
**Analogs found:** 9 / 9 (every file has a strong existing analog — this is a pure reuse phase)

This is a **REUSE phase**. Every new `memory/` file copies a shipped `library/` or `runtime/` analog. The single load-bearing rule: the ranking math (`cosine_topk`) is **imported verbatim, never copied or forked**. The ~120 storage lines of `index_sqlite_vec.py` ARE copied (table rename `vec_library` → `vec_memory`) because that is storage, not ranking. No analog == off-pattern scope creep → flag it (none found here).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/memory/store.py` | store/facade | CRUD | `src/vibemix/library/store.py` | exact (compose, not subclass) |
| `src/vibemix/memory/index_sqlite_vec_memory.py` | model/backend | file-I/O (sqlite) | `src/vibemix/library/index_sqlite_vec.py` | exact (copy + `vec_memory` rename + `moments` table) |
| `src/vibemix/memory/__init__.py` | config/barrel | n/a | `src/vibemix/library/__init__.py` | exact (re-export surface) |
| `tests/memory/test_store_parity.py` | test | CRUD | `tests/library/test_store_parity.py` | exact clone (`@pytest.mark.parity`) |
| `tests/memory/test_store.py` | test | CRUD | `tests/library/test_store_parity.py` (round-trip shape) | role-match |
| `tests/memory/test_retention.py` | test | batch | `recordings_index.run_retention_sweep` behavior | role-match (no test analog; mirror sweep semantics) |
| `tests/memory/test_no_live_path_import.py` | test (gate) | static+subprocess | `tests/repo/test_repo_scrub.py::test_deck_path_sqlcipher_dormant` | exact pattern |
| `tests/memory/test_no_extraction.py` | test (gate) | static (tokenize) | `tests/repo/test_repo_scrub.py::_strip_comments_and_docstrings` | exact pattern |
| `tests/memory/__init__.py` | config | n/a | `tests/library/__init__.py` | exact (marker) |
| `src/vibemix/runtime/recordings_index.py` (CONDITIONAL — cascade call-site wiring only) | service | event-driven | self (existing `delete`) | modify-in-place (see Open Q2 below) |

**NumpyStore reuse note:** `src/vibemix/library/index_numpy.py` is **reused as-is via import** (its constructor already accepts `vectors_path`/`ids_path` — pass `memory_vectors.npy`/`memory_ids.json`). No `index_numpy_memory.py` file is needed; if a plan proposes one, that is off-pattern — flag it.

## Pattern Assignments

### `src/vibemix/memory/store.py` (store/facade, CRUD)

**Analog:** `src/vibemix/library/store.py` — but **compose, do NOT subclass** (`LibraryStore` is the facade shape; `MemoryStore` owns its own `moments` sqlite connection because `NumpyStore` has no sqlite file).

**Imports pattern** — copy the chokepoint import verbatim (`library/store.py:21-30`):
```python
from __future__ import annotations
import logging, sys, sqlite3
from pathlib import Path
import numpy as np
from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk   # VERBATIM — never fork
from vibemix.library.index_numpy import NumpyStore                # reuse as-is
from vibemix.runtime.config_store import app_data_dir
```

**`open_memory_store()` probe** — clone of `library/store.py:78-114` (`open_store`), pointed at `memory.db`. Keep the exact try/except + structured-log + numpy fall-through shape:
```python
# library/store.py:85-114 — the probe-and-fall-through to mirror verbatim
if prefer_sqlite_vec:
    try:
        from vibemix.library.index_sqlite_vec import SqliteVecStore
        backend: _Backend = SqliteVecStore()
        print(f"-> library store: backend=SqliteVecStore reason=ok", file=sys.stdout, flush=True)
        return LibraryStore(backend)
    except Exception as e:
        logger.warning("library backend probe failed: backend_probe_failed=sqlite_vec reason=%s — falling back to NumpyStore", e)
        print(f"-> library store: backend=NumpyStore reason=sqlite_vec_unavailable ({e})", file=sys.stdout, flush=True)
backend = NumpyStore()
```
For memory: swap `SqliteVecStore()` → `SqliteVecMemoryStore(db_path=MEMORY_DB_PATH)`, swap the numpy default paths to `app_data_dir()/"memory_vectors.npy"` + `"memory_ids.json"`, and change the log prefix to `-> memory store:`.

**Single ranking chokepoint** — copy `library/store.py:56-61` (`LibraryStore.search`) and generalize to `query_topk`. NEVER `ORDER BY distance` / `MATCH ... AND k=`:
```python
def search(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
    ids, vectors = self._backend.load_all()
    return cosine_topk(query_vector, vectors, ids, k)   # the ONLY top-K path (P55)
```
Memory variant adds the locked `exclude_session=None` param (ship the seam now; Phase 65 *uses* it) then JOINs `moments` on returned `record_id`s. See RESEARCH Pattern 3 (63-RESEARCH.md:247-263).

**Delete-cascade** — RESEARCH Pattern 4 (63-RESEARCH.md:265-280); both deletes + one commit. The backend `delete()` it calls is `index_sqlite_vec.py:99-107` / `index_numpy.py:130-140` (both already verified to take `list[str]`).

**`moments` schema** — sibling plain table in the same `memory.db` (sqlite-vec path) or a sibling `memory_moments.db` (numpy path), per RESEARCH Pattern 2 (63-RESEARCH.md:228-245):
```sql
CREATE TABLE IF NOT EXISTS moments (
    record_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
    ts REAL NOT NULL, kind TEXT NOT NULL, signature TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_moments_session ON moments(session_id);
```

---

### `src/vibemix/memory/index_sqlite_vec_memory.py` (model/backend, file-I/O)

**Analog:** `src/vibemix/library/index_sqlite_vec.py` — **copy the ~120-line class**, two changes only: (1) rename the hardcoded `vec_library` table to `vec_memory` in all SQL strings; (2) add the `moments` table on the same `self.db` connection so `add_record` commits vec0 + metadata atomically.

**Why copy, not parameterize:** the table name `vec_library` is baked into 5 SQL strings (`index_sqlite_vec.py:51, 77, 81, 89, 103, 110`). Parameterizing it touches shipped library code and would force a library regression run (RESEARCH Open Q1, 63-RESEARCH.md:468-471). Copying is the lower-risk reading of "don't fork the chokepoint" — the chokepoint is `cosine_topk`, which is *imported*, not copied.

**Init pattern** — copy `index_sqlite_vec.py:41-56`. Note `db_path` is already a constructor arg (`def __init__(self, db_path: Path = DB_PATH)`), and the `sqlite_vec.load(self.db)` line re-raises on a host with no extension → `open_memory_store` catches → numpy fallback:
```python
self.db = sqlite3.connect(str(self._db_path))
self.db.enable_load_extension(True)
sqlite_vec.load(self.db)                       # re-raises on Win-ARM64 → numpy fallback
self.db.enable_load_extension(False)
self.db.execute(
    f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_memory USING vec0("   # RENAMED from vec_library
    f"track_id TEXT PRIMARY KEY, embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine)")
# NEW: the moments sibling table on the SAME connection (atomic add_record)
self.db.execute("CREATE TABLE IF NOT EXISTS moments (...)")
self.db.commit()
```

**add_batch / load_all / delete / snapshot_hash / close** — copy `index_sqlite_vec.py:58-120` with the `vec_library` → `vec_memory` substitution. Keep the float32 + `(EMBEDDING_DIM,)` asserts verbatim (`index_sqlite_vec.py:63-70`) — they are the dimension-drift guard (Pitfall 5). Keep the delete-then-insert replace idiom (`:72-84`) and `ORDER BY track_id ASC` (`:89`).

> Backend interface contract (must match `NumpyStore` exactly — see `library/store.py:35-40`): `add_batch / load_all -> (list[str], np.ndarray) / delete / snapshot_hash / close`.

---

### `src/vibemix/memory/__init__.py` (barrel)

**Analog:** `src/vibemix/library/__init__.py` (the clean re-export surface). Export `MemoryStore`, `open_memory_store`, and a minimal typed `MemoryRecord`/`Record` (only if `query_topk` needs a typed return — RESEARCH structure note 63-RESEARCH.md:188-189; keep raw, no signature builders, those are Phase 64). Mirror `library/store.py:117-122` `__all__` style.

---

### `tests/memory/test_store_parity.py` (test, CRUD) — STORE-01 gate

**Analog:** `tests/library/test_store_parity.py` — direct clone.

**Backend-availability probe** — copy `test_store_parity.py:32-45` verbatim (`_sqlite_vec_available()` + `SQLITE_VEC_AVAILABLE` module flag):
```python
def _sqlite_vec_available() -> bool:
    try:
        import sqlite_vec
        db = sqlite3.connect(":memory:"); db.enable_load_extension(True)
        sqlite_vec.load(db); db.close(); return True
    except Exception:
        return False
SQLITE_VEC_AVAILABLE = _sqlite_vec_available()
```

**Parity assertion** — copy the shape of `test_store_parity.py:100-138` (`test_sqlite_vec_topk_matches_numpy`): two stores over `tmp_path`, one `prefer_sqlite_vec=True`, one `False`; add the same records; assert identical `record_id` rank order. Use `@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, ...)` on the sqlite-vec leg. RESEARCH ships a ready clone at 63-RESEARCH.md:342-380.

**In-test fixture, not a fixture file** — unlike the library test (which loads `fixtures/synthetic_embeddings.npy`, `test_store_parity.py:49-53`), generate synthetic 768-dim vectors with `np.random.default_rng(seed)` in-test (keeps the repo lean; RESEARCH Wave-0 note 63-RESEARCH.md:530). Reuse `l2_normalize` + `EMBEDDING_DIM` from `library._cosine`.

**Also clone:** `test_tie_break_track_id_asc` (`:141-155`) and `test_float32_round_trip_bit_identical` (`:158-170`) — the determinism + byte-exactness guards.

---

### `tests/memory/test_store.py` (test, CRUD) — STORE-01/02/03 units

**Analog:** the round-trip / add-batch shape in `tests/library/test_store_parity.py`. Cover: `test_add_query_roundtrip` (raw signature returned verbatim — STORE-02), `test_numpy_fallback` (force `prefer_sqlite_vec=False`, store still functional — STORE-01), `test_delete_cascade` (no orphaned vectors after `delete_session` — STORE-03), `test_session_id_path_traversal` (crafted `session_id` rejected — STORE-03 security). The path-traversal test mirrors `recordings_index` gate behavior (see Shared Patterns below).

---

### `tests/memory/test_retention.py` (test, batch) — STORE-03

**Analog:** behavioral mirror of `recordings_index.run_retention_sweep` (`recordings_index.py:490-528`). No direct test analog exists; assert oldest-session-first, whole-session eviction (never partial). Mirror the `∞` sentinel short-circuit semantics (`recordings_index.py:523-524`) if the memory sweep adopts a similar "infinite retention" stop.

---

### `tests/memory/test_no_live_path_import.py` (test gate, static + subprocess)

**Analog:** `tests/repo/test_repo_scrub.py::test_deck_path_sqlcipher_dormant` (`test_repo_scrub.py:406-435`) — the subprocess `sys.modules` dormancy idiom, copied exactly:
```python
# test_repo_scrub.py:416-432 — the dormancy idiom to clone for the live-path gate
script = (
    "import sys\n"
    "import vibemix.memory.store  # noqa: F401\n"
    "leaks = sorted(m for m in sys.modules if m.startswith('vibemix.state.coach') "
    "or m.startswith('vibemix.agent') or 'ws_bus' in m)\n"
    "print('LEAKED:' + ','.join(leaks) if leaks else 'CLEAN')\n")
result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
    check=True, cwd=REPO_ROOT, env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT/"src")})
assert result.stdout.strip() == "CLEAN", ...
```
Plus a static AST scan of `src/vibemix/memory/*.py` for forbidden imports (`vibemix.state.coach`, `vibemix.state.refresh`, `vibemix.agent`, `vibemix.prompts`, `vibemix.runtime.ws_bus`) and forbidden names (`MusicState`, `EventDetector`). RESEARCH ships the clone at 63-RESEARCH.md:382-418.

---

### `tests/memory/test_no_extraction.py` (test gate, static tokenize)

**Analog:** `tests/repo/test_repo_scrub.py::_strip_comments_and_docstrings` (`test_repo_scrub.py:272-310`) — the tokenize-based COMMENT+STRING stripper, so docstrings that *document* the ban don't self-trip the gate. Copy this exact stripper shape:
```python
# test_repo_scrub.py:290-304 — tokenize stripper to reuse
kept = []
for tok in tokenize.generate_tokens(io.StringIO(src_text).readline):
    if tok.type in (tokenize.COMMENT, tokenize.STRING):
        if tok.type == tokenize.STRING:
            kept.append(tok._replace(string='""'))   # collapse string, keep token positions
        continue
    kept.append(tok)
return tokenize.untokenize(kept)
```
Then scan stripped `memory/*.py` for generation surfaces: `generate_content`, `generate_reply`, `.chats.`, `GenerateContentConfig` — assert none present (only `embed_content` may reach Gemini). RESEARCH ships the clone at 63-RESEARCH.md:420-443.

---

## Shared Patterns

### Embedding seam (STORE-04 — reuse, nothing to re-wire)
**Source:** `src/vibemix/library/embed.py` + `src/vibemix/llm/model_router.py::resolve`
**Apply to:** `memory/store.py` (the only model call the store makes, structurally)

The model id is resolved once at module import (`embed.py:71`), never hardcoded:
```python
# library/embed.py:58, 71 — the ONLY sanctioned resolution; CI-gated against literals
from vibemix.llm.model_router import resolve
GEMINI_EMBEDDING_MODEL = resolve("embedding")[0]   # -> ("gemini-embedding-2", ServiceTier.FLEX)
```
`_router_config.py:40` maps `"embedding" → ("gemini-embedding-2", ServiceTier.FLEX)` — FLEX cost lane is already wired. Reuse `LibraryEmbedder.embed_query(text)` (`embed.py:362-369`) for the text→768-dim L2-normalized path. The content-hash cache lives on `embed_track` (`embed.py:328-360`); for idempotent re-embeds of identical signatures, the planner reuses that cache machinery rather than re-solving it. **Phase 63 store tests use synthetic float32 vectors — no live API call** (Environment Availability, 63-RESEARCH.md:488).

### Path-traversal defense (STORE-03 security, V5/V12)
**Source:** `src/vibemix/runtime/recordings_index.py`
**Apply to:** any `session_id`/`record_id` that reaches the filesystem in `memory/`

Two-layer gate, copied exactly:
```python
# recordings_index.py:78 — the regex (DJ-session-dir shape)
SESSION_DIR_RE: re.Pattern[str] = re.compile(r"^\d{8}-\d{6}$")
# recordings_index.py:388-401 — the symlink-escape-proof gate
if not SESSION_DIR_RE.match(name):  return (False, "path_traversal_rejected")
target = (root / name).resolve(); root_resolved = root.resolve()
if not target.is_relative_to(root_resolved):  return (False, "path_traversal_rejected")
if target == root_resolved:  return (False, "path_traversal_rejected")  # refuse root itself
```

### Cache-dir resolution (STORE-03 location)
**Source:** `src/vibemix/runtime/config_store.py:136` (`app_data_dir()`)
**Apply to:** `MEMORY_DB_PATH = app_data_dir() / "memory.db"` — durable user data, NOT `~/.cache`.
```python
# config_store.py:136-142 — OS-aware, monkeypatch-friendly (tests redirect HOME/APPDATA)
def app_data_dir() -> Path:  # darwin: ~/Library/Application Support/vibemix ; win32: $APPDATA/vibemix
    return _app_data_dir()
```
> NOTE on a research drift: `library/index_sqlite_vec.py:27` and `index_numpy.py:27` default to `~/.cache/vibemix/library.db`. Memory MUST override the path to `app_data_dir()` (the durable tier), per the anti-pattern in 63-RESEARCH.md:290. Do NOT inherit the `~/.cache` default.

### Retention / eviction sweep (STORE-03)
**Source:** `src/vibemix/runtime/recordings_index.py:490-528` (`run_retention_sweep` + `RetentionSweepResult`)
**Apply to:** the memory retention sweep — mirror best-effort per-entry deletion, the `RetentionSweepResult(deleted_names, bytes_pruned)` return shape, and the `∞` sentinel short-circuit. Memory evicts **whole sessions, oldest-first** (never partial-session) via `delete_session`.

### Determinism / dimension contract (STORE-01)
**Source:** `src/vibemix/library/_cosine.py` — `EMBEDDING_DIM = 768` (`:51`), `cosine_topk` (`:74`), `l2_normalize` (`:54`)
**Apply to:** every vector path in `memory/`. Reuse `EMBEDDING_DIM` (no new dim, no per-store dim config). The float32 + `(768,)` asserts in `cosine_topk` (`:107-129`) and the Timsort tie-break (`:143`, primary DESC sim / secondary ASC id) are the parity contract — never re-truncate or re-normalize in `memory/`.

## No Analog Found

None. Every file maps to a shipped analog. **This is the success condition for a reuse phase** — any plan that proposes a file without an analog here (e.g. a bespoke KNN, a memory-specific embedder, a new `index_numpy_memory.py`, or a new socket/port) is off-pattern and should be rejected per the anti-patterns list (63-RESEARCH.md:282-290).

## Open Items for the Planner (from RESEARCH Open Questions)

1. **Cascade call-site wiring (Open Q2, 63-RESEARCH.md:473-476):** `RecordingsIndex.delete` (`recordings_index.py:370`) is the cascade site. Ship `MemoryStore.delete_session` + its unit test in Phase 63 (the store contract). Wiring the actual call `recordings_index.delete → MemoryStore.delete_session` is in-scope ONLY IF it imports no live coach path (`recordings_index.py` is a runtime utility, not the reaction loop). If it risks scope creep, defer the call-site to the recordings-UI-delete phase and keep Phase 63 to store contract + test. **This is the only candidate modification to shipped code — gate it through the import boundary test.**
2. **Single connection to `memory.db` (Open Q3, 63-RESEARCH.md:478-480):** reuse the backend's `self.db` for the `moments` table (one writer, one connection, atomic add_record). Document the single-writer invariant in the module docstring (mirrors `MusicState`/`EvidenceRegistry` house style).
3. **`moments` placement on numpy path (RESEARCH Pattern 2 + Pitfall 3):** order writes vector-first, `moments`-second so a crash leaves at worst a reconcilable orphan vector (never a metadata row pointing at a missing vector). The boot orphan-reconciliation sweep is the backstop.

## Metadata

**Analog search scope:** `src/vibemix/library/` (store, index_sqlite_vec, index_numpy, _cosine, embed), `src/vibemix/runtime/` (recordings_index, config_store), `src/vibemix/llm/` (model_router, _router_config), `tests/library/`, `tests/repo/`
**Files scanned:** 11 source/test files read end-to-end or in targeted ranges; all RESEARCH file:line citations verified against live source 2026-05-22
**Pattern extraction date:** 2026-05-22
