# Phase 63: Memory Store - Research

**Researched:** 2026-05-22
**Domain:** Local per-install vector store (`memory.db`) built by REUSING the shipped `src/vibemix/library/` primitives — zero net-new dependency
**Confidence:** HIGH (every claim below verified by reading live `src/vibemix/` source, not training data)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — Store composition & schema (reuse, don't fork)**
- **Compose, don't subclass.** `MemoryStore` is a thin wrapper holding a `LibraryStore`-style backend pointed at a separate `memory.db` path (NOT the library's track DB). It reuses `library/index_sqlite_vec.py::SqliteVecStore` (vec0 storage-only) + `library/index_numpy.py` fallback, selected the same way `library/store.py::open_store(prefer_sqlite_vec=True)` does. `library/_cosine.py::cosine_topk` stays the **single ranking chokepoint** — no forked KNN, no SQL `ORDER BY distance`.
- **Record id scheme:** deterministic `f"{session_id}:{seq}"` (stable, human-debuggable; enables session-scoped delete + current-session self-exclusion downstream). Embedding keyed by this `record_id` in vec0.
- **Metadata lives in a sibling SQLite table in the same `memory.db`**: `moments(record_id PRIMARY KEY, session_id TEXT, ts REAL, kind TEXT, signature TEXT)`. vec0 holds only `(record_id → embedding)`. `add_record` writes both atomically; `query_topk` returns `record_id`s from `cosine_topk` then joins the sibling table for metadata.
- **Embedding dimension:** reuse `_cosine.EMBEDDING_DIM` (768). No new dim, no per-store dim config.

**Area 2 — Retention, privacy, delete-cascade**
- **Delete granularity = per session.** `delete_session(session_id)` removes every one of that session's vectors (vec0) **and** its `moments` rows in one transaction → no orphaned vectors. Cascade hook the existing recordings-delete path (`runtime/recordings_index.py`) calls.
- **Retention budget:** per-install cap that evicts **oldest-session-first**. Default generous + configurable via the existing config store: cap on moment count (recommend ~10,000) AND/OR age (recommend ~180 days), whichever trips first. Eviction is whole-session (never partial).
- **Location:** the app cache dir, same base resolution as `recordings_index`, per-install, local-only, user-deletable. Path-traversal-defended exactly like the shipped recordings/library path handling — no caller-supplied raw paths reach the filesystem.
- **Orphan reconciliation:** boot-time sweep reconciles vec0 record_ids against `moments` (and where cheap against the recordings index) and drops danglers — defensive, transactional.

**Area 3 — Embedding routing & cost**
- **Model resolution: `model_router.resolve("embedding")` ONLY** — never a hardcoded embedding-model literal. Reuse `library/embed.py`'s already-router-resolved client. CI grep gate asserts no hardcoded literal exists in `memory/`.
- **Cost lane: `ServiceTier.FLEX`** through the Bravoh proxy (memory embedding is off-hot-path by construction).
- **Idempotent embeds:** reuse `library/embed.py`'s content-hash embed cache so re-embedding identical signatures costs 0 API calls.
- **Raw-in, raw-out:** a record carries the raw text signature only + its embedding + (session_id, ts, kind). **Never** an LLM-extracted "insight". `MemoryStore` has no path that calls a chat/generation model — embedding is the only model call, structurally.

### Claude's Discretion
- Exact wrapper line-count ("~50 lines" is a north-star, not a hard limit), the precise default retention numbers (within the recommended ranges), and whether the boot-sweep lives in `MemoryStore` or a sibling helper — all at the planner's discretion, guided by the shipped `library/`/`recordings_index` conventions.

### Deferred Ideas (OUT OF SCOPE)
- **Ingest pipeline** (artifacts → signatures → `add_record`) → Phase 64.
- **Retrieval seam / `recall` evidence source / coach grounding** → Phase 65 (anti-slop release gate).
- **Visible copilot moves** → Phase 66.
- **Cosine-vs-time-weight blend + decay half-life tuning** → Phase 65 (in-phase, on Kaan's real corpus).
- **Audio-moment (multimodal) embedding** → future milestone (text-signature-only in v6.0).
- **NO live reaction-path touch whatsoever.** A grep/import gate proves `memory/` does not import the coach loop or `MusicState`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORE-01 | Per-install `memory.db` (sqlite-vec) stores embedded moments + metadata, reusing `SqliteVecStore` + storage-only vec0 + `cosine_topk` + content-hash embed cache; falls back to `NumpyStore` when the extension can't load (Mac/Win parity, `pytest -m parity`). | §Exact MemoryStore Composition (Q1) + §Fallback & Parity (Q2). The `open_store()` probe at `library/store.py:78-114` and the `cosine_topk` chokepoint at `_cosine.py:74` are reused verbatim; the `parity` marker is registered (`pyproject.toml:204`) with an existing test template at `tests/library/test_store_parity.py`. |
| STORE-02 | ~50-line `MemoryStore` exposes `add_record` + `query_topk`; each record carries `session_id` + timestamp + raw text signature + embedding — never an LLM-extracted insight (raw-in/raw-out). | §Exact MemoryStore Composition (Q1) + §No-LLM-Extraction (Q5). The wrapper imports only `embed.py` (no `agent`/`prompts`/`state` generation surface); a static import gate (Q6) proves it. |
| STORE-03 | Retention + privacy: deleting a session's recordings cascades to its memory embeddings (no orphaned vectors); per-install size/retention budget caps growth; everything local-only + user-deletable (extends `recordings_index` retention/delete + path-traversal defense). | §Retention + Cascade + Paths (Q4). `delete_session` is the cascade hook; `app_data_dir()` (`config_store.py:136`) is the cache-dir base; `SESSION_DIR_RE` + `is_relative_to` (`recordings_index.py:78,397`) is the path-traversal pattern; `run_retention_sweep` (`recordings_index.py:490`) is the eviction template. |
| STORE-04 | Embedding model resolved via `model_router.resolve("embedding")` (never hardcode); embeds route through the Bravoh proxy on `ServiceTier.FLEX`. | §Embedding Seam (Q3). `_router_config.py:40` already maps `"embedding" → ("gemini-embedding-2", ServiceTier.FLEX)`; `embed.py:71` resolves it; the model-literal CI gate (`tests/repo/test_model_literal_gate.py`) already enforces no literals in `src/vibemix/`. **Nothing to re-wire — reuse `LibraryEmbedder`.** |
</phase_requirements>

## Summary

Phase 63 is a **pure wiring/reuse phase with zero net-new dependency**. Every primitive the memory store needs already ships, hardened, in `src/vibemix/library/`: the storage-only sqlite-vec backend (`SqliteVecStore`), the numpy fallback (`NumpyStore`), the `open_store()` probe-and-fall-through facade, the single deterministic ranking chokepoint (`cosine_topk`), the proxy-only Gemini embedder with a content-hash cache (`LibraryEmbedder`), and the model router (`resolve("embedding")` → `gemini-embedding-2` on `ServiceTier.FLEX`, already wired at `_router_config.py:40`). The retention/delete/path-traversal machinery ships in `runtime/recordings_index.py`, and the OS-aware cache base resolver ships in `runtime/config_store.py::app_data_dir()`. The job is to instantiate a **second** store over a separate `memory.db`, add one sibling metadata table, and expose three methods — `add_record`, `query_topk`, `delete_session` — plus a parity test, an import-boundary gate, and a no-extraction gate.

The single hardest design decision (Q1) resolves cleanly: **`MemoryStore` owns its own `sqlite3` connection for the `moments` sibling table AND composes a `library`-style backend (`SqliteVecStore` / `NumpyStore`) over the same `memory.db` path** — it does not subclass `LibraryStore` or `SqliteVecStore`. This is forced by two facts read from source: (a) `SqliteVecStore.__init__` only creates the `vec_library` vec0 virtual table — it exposes no API to add a sibling table, but it does hold a normal `sqlite3.Connection` (`self.db`) over the file, so a second `CREATE TABLE moments` against the *same file path* (via `MemoryStore`'s own connection, or the backend's) is a plain sqlite operation; and (b) the `NumpyStore` fallback stores vectors in `.npy`/`.json` sidecars, NOT in a sqlite file at all — so the `moments` table cannot live "inside the backend" generically. `MemoryStore` owning the metadata connection is the only composition that works identically across both backends.

**Primary recommendation:** Create `src/vibemix/memory/` as a sibling of `library/`. Write `memory/store.py` with a `MemoryStore` class that (1) calls a memory-flavored `open_memory_store()` (clone of `open_store`, pointed at `app_data_dir()/"memory.db"`) for the vec0/numpy backend, (2) owns a private `sqlite3` connection to `app_data_dir()/"memory.db"` (sqlite-vec backend) or a sibling `moments.db`/JSON (numpy backend) for the `moments` table, and (3) exposes `add_record` / `query_topk` / `delete_session` that route ranking through `cosine_topk` and embedding through the injected `LibraryEmbedder`. Ship `tests/memory/test_store_parity.py` (clone of `test_store_parity.py`, `@pytest.mark.parity`), `tests/memory/test_no_live_path_import.py` (static + subprocess import gate), and `tests/memory/test_no_extraction.py` (static gate: `memory/` calls only `embed_content`, never a generation model). DO NOT fork `cosine_topk`, DO NOT add a dependency, DO NOT touch the live reaction path.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vector storage (`record_id → embedding`) | Local storage (sqlite-vec vec0 / numpy fallback) | — | Reuse `SqliteVecStore`/`NumpyStore`; per-install, single-writer, no server. |
| Metadata storage (`record_id → session_id, ts, kind, signature`) | Local storage (sibling sqlite table in `memory.db`) | — | Mirrors library's id/vector separation; joined after `cosine_topk` returns ids. |
| Top-k ranking | CPU/numpy (`cosine_topk`) | — | The single chokepoint (P55); deterministic, Mac/Win bit-identical. Never SQL `ORDER BY distance`. |
| Embedding a text signature | External API (Gemini Embedding 2 via Bravoh proxy, FLEX tier) | Content-hash cache (`embeddings.db`) | Reuse `LibraryEmbedder`; off-hot-path by construction; cache makes re-embed free. |
| Backend selection (sqlite-vec vs numpy) | Local probe at open time | — | Reuse `open_store()` shape; Win ARM64 has no wheel → numpy fallback, parity-identical. |
| Cache-dir resolution | OS-aware resolver (`app_data_dir()`) | — | Same base as `recordings/`; durable user data, not `~/.cache`. |
| Retention / eviction | Local sweep (oldest-session-first) | — | Mirror `run_retention_sweep` pattern; whole-session eviction. |
| Delete-cascade | Local transaction (`delete_session`) | — | Hook the `recordings_index.delete` path calls; removes vectors + `moments` rows atomically. |
| Path-traversal defense | Local validation (`SESSION_DIR_RE` + `is_relative_to`) | — | Copy the two-layer gate from `recordings_index.py`. |

> **No external network tier beyond the embedding call.** No new socket, no new port (one-socket invariant). No UI tier (this phase is headless storage — frontend skill confirmed N/A below).

## Standard Stack

**Net-new third-party dependencies: ZERO.** Everything below is already declared in `pyproject.toml`, installed, and (for `vec0.*`) bundled in the signed sidecar.

### Core (all REUSED, not installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite-vec` | `0.1.9` (pinned `>=0.1.9`, `pyproject.toml:118`) `[VERIFIED: pyproject.toml + dev-box probe per STACK.md]` | vec0 virtual-table storage for `memory.db` | Same backend as the shipped library index; storage-only; ~160 KB prebuilt extension, no compiler. |
| `google-genai` | `2.0.1` installed `[VERIFIED: STACK.md dev-box probe]` | `embed_content` for the text signature | Sole AI SDK; embedding path already implemented in `library/embed.py`. |
| `numpy` | `2.4.4` (`pyproject.toml`) `[CITED: STACK.md]` | float32 vector math, `cosine_topk`, `l2_normalize` | Already core; the ranking chokepoint runs on numpy arrays. |
| stdlib `sqlite3` | bundled (CPython 3.12) `[VERIFIED: CLAUDE.md Python 3.12]` | DB connection, `moments` sibling table, vec0 host | No new dep. |

### Supporting (REUSED in-repo modules — these are the actual "stack" of this phase)
| Module | Path | Reuse |
|--------|------|-------|
| `cosine_topk`, `l2_normalize`, `EMBEDDING_DIM` | `src/vibemix/library/_cosine.py` | **Verbatim.** The single ranking chokepoint. `_cosine.py:74` / `:54` / `:51`. |
| `SqliteVecStore` | `src/vibemix/library/index_sqlite_vec.py` | Clone the class (or instantiate with a `db_path=memory.db`, `table=vec_memory`). It is already path-parameterized: `def __init__(self, db_path: Path = DB_PATH)` (`index_sqlite_vec.py:41`). The table name `vec_library` is hardcoded in the SQL strings, so a memory variant needs a parameterized/renamed table. |
| `NumpyStore` | `src/vibemix/library/index_numpy.py` | Clone with memory-flavored sidecar paths (`memory_vectors.npy` / `memory_ids.json`); the class hardcodes `library_vectors.npy`/`library_ids.json` as defaults but accepts `vectors_path`/`ids_path` constructor args (`index_numpy.py:42-46`). |
| `open_store(prefer_sqlite_vec=True)` | `src/vibemix/library/store.py:78` | Clone as `open_memory_store()` — same probe + structured-log + fall-through to numpy. |
| `LibraryEmbedder` | `src/vibemix/library/embed.py:254` | **Reuse as-is** for embedding the text signature. `embed_query(text)` (`embed.py:362`) is the text→768-dim-L2-normalized path with no content-hash cache; `embed_track` has the cache. See Q3 for the cache decision. |
| `resolve("embedding")` | `src/vibemix/llm/model_router.py:44` → `_router_config.py:40` | The only sanctioned way to get the model id; already returns `("gemini-embedding-2", ServiceTier.FLEX)`. |
| `app_data_dir()` | `src/vibemix/runtime/config_store.py:136` | OS-aware cache base; `memory.db` lives at `app_data_dir()/"memory.db"`. |
| `RecordingsIndex` / `run_retention_sweep` / `SESSION_DIR_RE` | `src/vibemix/runtime/recordings_index.py` | Delete-cascade hook, retention sweep template, path-traversal regex + `is_relative_to` gate. |

### Alternatives Considered (all rejected — locked or off-pattern)
| Instead of | Could Use | Tradeoff / Verdict |
|------------|-----------|--------------------|
| Compose `SqliteVecStore` over `memory.db` | Subclass `LibraryStore` | REJECTED. Subclassing forces the `moments` sibling table into the backend, which the numpy fallback can't host (it has no sqlite file). Composition is the only cross-backend-uniform shape. |
| Python `cosine_topk` (storage-only) | sqlite-vec native `MATCH ... AND k=` KNN | REJECTED. Diverges on tied similarities across sqlite-vec (Mac) vs numpy (Win ARM64) → breaks the `parity` gate (P55). The shipped library proves storage-only is correct + fast enough. |
| Reuse `LibraryEmbedder` | A new memory embedder | REJECTED. Re-solves the proxy-only + cache + 768-dim + GA-rename-probe seams that already ship. |
| `sqlite-vec 0.1.9` | `0.1.10aN` pre-release / `sqlite-vss` / FAISS / chroma | REJECTED. 0.1.10 is alpha-only; the rest add native deps that break one-click install. Locked. |
| `gemini-embedding-2` (router-resolved) | hardcoded `gemini-embedding-001` literal | REJECTED — and CI-blocked. The model-literal gate (`tests/repo/test_model_literal_gate.py:110`) explicitly canaries `gemini-embedding-001`. |

**Installation:** none. Confirm only:
```bash
uv run python -c "import sqlite3, sqlite_vec; \
db=sqlite3.connect(':memory:'); db.enable_load_extension(True); \
sqlite_vec.load(db); print(db.execute('select vec_version()').fetchone())"
# -> ('v0.1.9',)   [VERIFIED: STACK.md dev-box probe 2026-05-22]
```

## Package Legitimacy Audit

> No external packages are installed by this phase. All four core libraries are already declared in `pyproject.toml`, already installed, and (for `sqlite-vec`'s `vec0.*` binary) already bundled in the signed sidecar from v2.1/v3.x. slopcheck is **not applicable** — there is no install step.

| Package | Registry | Status | Source Repo | Disposition |
|---------|----------|--------|-------------|-------------|
| `sqlite-vec` | PyPI | already declared `>=0.1.9` (`pyproject.toml:118`); dev-box probe `v0.1.9` | github.com/asg017/sqlite-vec | Reuse — no install |
| `google-genai` | PyPI | already core; installed `2.0.1` | github.com/googleapis/python-genai | Reuse — no install |
| `numpy` | PyPI | already core `2.4.4` | github.com/numpy/numpy | Reuse — no install |
| `sqlite3` | stdlib | bundled CPython 3.12 | — | Reuse — no install |

**Packages removed due to slopcheck [SLOP] verdict:** none (no install step).
**Packages flagged [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram (Phase 63 scope — STORAGE SPINE ONLY)

```
   PHASE 64 (ingest, OUT OF SCOPE)          PHASE 65 (retrieve, OUT OF SCOPE)
   add_record(record_id, session_id,        query_topk(query_embedding, k,
     ts, kind, signature, embedding)           *, exclude_session=None)
            │                                        │
            ▼                                        ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ MemoryStore  (src/vibemix/memory/store.py)  — THIS PHASE          │
   │                                                                    │
   │  add_record ──┬─► backend.add_batch([(record_id, embedding)])      │
   │               │      (vec0 / numpy — storage only)                 │
   │               └─► moments INSERT (record_id, session_id, ts,       │
   │                      kind, signature)   ── same txn ──             │
   │                                                                    │
   │  query_topk ──► backend.load_all() ─► cosine_topk(q, V, ids, k)    │
   │                   │  (THE single ranking chokepoint — P55)         │
   │                   └─► [optional] filter exclude_session via moments │
   │                   └─► JOIN moments on returned record_ids → Record │
   │                                                                    │
   │  delete_session(session_id) ──┬─► backend.delete(record_ids)       │
   │                               └─► DELETE FROM moments WHERE        │
   │                                     session_id = ?   ── same txn ──│
   └──────────────────────────────┬──────────────────┬────────────────┘
                                   │                  │
              backend (open_memory_store probe)   own sqlite3 conn
                                   │                  │ (moments table)
                ┌──────────────────┴───────┐          │
                ▼                          ▼          ▼
        SqliteVecStore(memory.db)   NumpyStore(memory_*.{npy,json})
        vec0 table: vec_memory                          moments table
                                                        lives in memory.db
                                                        (sqlite-vec path) or
                                                        a sibling sqlite file
                                                        (numpy path)
                                   ▲
                                   │ embeds the signature (off-hot-path)
              LibraryEmbedder (REUSED) ─► resolve("embedding")
                ─► gemini-embedding-2 @ ServiceTier.FLEX via Bravoh proxy
                ─► content-hash cache in embeddings.db (re-embed = 0 calls)

   DELETE CASCADE (wired by Phase 63, called by recordings_index):
   recordings_index.delete(session) ──► MemoryStore.delete_session(session)

   ❌ NO arrow to: coach loop / MusicState / ws_bus / EventDetector / agent.
      Import-boundary gate (tests/memory/test_no_live_path_import.py) enforces this.
```

### Recommended Project Structure
```
src/vibemix/memory/                 # NEW package — sibling of library/, NOT inside it
├── __init__.py                     # exports MemoryStore, open_memory_store, MemoryRecord
├── store.py                        # MemoryStore + open_memory_store() (clone of library/store.py)
└── (records.py is Phase 64's; Phase 63 may ship a minimal MemoryRecord/Record dataclass here
     if query_topk needs a typed return — keep it raw, no signature builders, those are P64)
```
Rationale (from ARCHITECTURE.md): `library/` is the user's track collection; `memory/` is the user's past sessions — different DB, different writer, different lifecycle. `memory/` *imports from* `library/` (`_cosine`, `index_sqlite_vec`, `index_numpy`, `embed`) rather than forking, so cosine-parity + embed-cache guarantees are shared.

### Pattern 1: Compose-not-subclass — `MemoryStore` owns the metadata connection
**What:** `MemoryStore` holds (a) a `library`-style backend for vectors via `open_memory_store()`, and (b) its own `sqlite3.Connection` for the `moments` table.
**When to use:** Always for this phase — it is the only shape uniform across the sqlite-vec and numpy backends.
**Why:** `SqliteVecStore` exposes no sibling-table API and `NumpyStore` has no sqlite file at all. The metadata table must be owned at the `MemoryStore` layer.

```python
# src/vibemix/memory/store.py  — SHAPE (planner refines; ~50-line north-star)
# Source pattern: library/store.py:78 (open_store) + library/index_sqlite_vec.py:41
from __future__ import annotations
import sqlite3
from pathlib import Path
import numpy as np
from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk, l2_normalize
from vibemix.library.index_numpy import NumpyStore
from vibemix.runtime.config_store import app_data_dir

MEMORY_DB_PATH = app_data_dir() / "memory.db"   # durable user data, NOT ~/.cache

def open_memory_store(prefer_sqlite_vec: bool = True):
    """Clone of library/store.py::open_store, pointed at memory.db.
    Probe sqlite-vec; on ANY sqlite_vec.load failure, fall through to numpy.
    Returns a (backend, db_path_for_moments) — see note on moments placement."""
    if prefer_sqlite_vec:
        try:
            from vibemix.memory.index_sqlite_vec_memory import SqliteVecMemoryStore
            return SqliteVecMemoryStore(db_path=MEMORY_DB_PATH)  # vec0 table = vec_memory
        except Exception as e:
            # structured log identical to library/store.py:97-106
            ...
    return NumpyStore(  # memory-flavored sidecars
        vectors_path=app_data_dir() / "memory_vectors.npy",
        ids_path=app_data_dir() / "memory_ids.json",
    )
```

### Pattern 2: `moments` sibling table placement (the load-bearing schema decision)
**What:** Where the `moments(record_id PK, session_id, ts, kind, signature)` table physically lives.
**Recommendation (planner-confirmable):**
- **sqlite-vec backend:** put `moments` in the **same `memory.db` file**. The `vec0` virtual table and a plain table coexist in one sqlite file. `MemoryStore` can either (a) reuse the backend's existing `sqlite3.Connection` (`SqliteVecMemoryStore.db`) by exposing it, or (b) open its own second connection to the same path. Recommend (a) — one connection per file avoids sqlite locking surprises and keeps `add_record` atomic across vec0 + `moments` in one transaction/commit.
- **numpy backend:** `moments` cannot live in the `.npy` sidecars. Put it in a sibling `app_data_dir()/"memory_moments.db"` (a plain stdlib sqlite file). `MemoryStore` owns this connection directly.
**Why this is safe:** `add_record` writes the vector via the backend AND the `moments` row, then a single commit. On the sqlite-vec path both writes are in one connection → one transaction. On the numpy path the vector write is an atomic `os.replace` (`index_numpy.py:88`) and the `moments` write is a sqlite commit — order them vector-first so a crash leaves at worst a vector with no metadata row (reconcilable by the boot sweep), never a metadata row pointing at a missing vector.

```python
# moments schema (verified plain-sqlite — no vec0 syntax needed)
CREATE TABLE IF NOT EXISTS moments (
    record_id  TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    ts         REAL NOT NULL,
    kind       TEXT NOT NULL,
    signature  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_moments_session ON moments(session_id);  -- delete-cascade + exclude
```

### Pattern 3: Ranking is ALWAYS `cosine_topk` (the single chokepoint, P55)
**What:** `query_topk` loads all vectors from the backend, calls `cosine_topk(query, vectors, ids, k)`, then joins `moments` on the returned ids.
**When:** Every query. Never `ORDER BY distance`, never `vec_distance_cosine`, never `MATCH ... AND k=`.
**Why:** Bit-identical Mac/Win rank order. `cosine_topk` asserts float32 + shape `(768,)` and resolves ties by `track_id ASC` via Timsort (`_cosine.py:107-144`).
```python
# Source: library/store.py:56-61 (search) generalized to memory
def query_topk(self, query_embedding, k=8, *, exclude_session=None):
    ids, vectors = self._backend.load_all()
    if exclude_session is not None:               # Phase 65 will use this; harmless to ship now
        keep = [i for i, rid in enumerate(ids)
                if self._moments_session_of(rid) != exclude_session]
        ids = [ids[i] for i in keep]
        vectors = vectors[keep] if keep else vectors[:0]
    hits = cosine_topk(query_embedding, vectors, ids, k)   # [(record_id, cosine), ...]
    return [self._join_moment(rid, cos) for rid, cos in hits]
```
> NOTE: `exclude_session` is in the locked `query_topk` signature. Ship the parameter and a correct implementation; the *use* of it (current-session exclusion) is Phase 65's concern, but the seam belongs here so P65 needs no signature change.

### Pattern 4: Delete-cascade in one transaction (no orphaned vectors)
**What:** `delete_session(session_id)` looks up that session's `record_id`s in `moments`, deletes them from the vec0/numpy backend, deletes the `moments` rows, commits once.
**When:** Called by `recordings_index`'s session-delete path (the cascade hook). Also called by the retention sweep (whole-session eviction).
```python
def delete_session(self, session_id: str) -> int:
    rows = self._moments.execute(
        "SELECT record_id FROM moments WHERE session_id = ?", (session_id,)
    ).fetchall()
    record_ids = [r[0] for r in rows]
    if not record_ids:
        return 0
    self._backend.delete(record_ids)              # library backend delete() — index_sqlite_vec.py:99 / index_numpy.py:130
    self._moments.execute("DELETE FROM moments WHERE session_id = ?", (session_id,))
    self._moments.commit()
    return len(record_ids)
```

### Anti-Patterns to Avoid
- **Subclassing `LibraryStore`/`SqliteVecStore`** to "get the table for free" — breaks numpy-fallback uniformity (numpy has no sqlite file). Compose instead.
- **Forking `cosine_topk`** or adding a memory-specific KNN — instant P55 parity break; HARD NO per the objective.
- **Native vec0 KNN (`MATCH`/`ORDER BY distance`)** for ranking — diverges from numpy on ties.
- **Adding any dependency** — HARD NO. Everything needed is already declared.
- **Hardcoding `gemini-embedding-001`/`gemini-embedding-2`** in `memory/` — CI gate blocks it; use `resolve("embedding")` / `LibraryEmbedder`.
- **Importing `state.coach` / `MusicState` / `ws_bus` / `agent` / `EventDetector` from `memory/`** — violates the no-live-path-touch invariant; the import gate fails the build.
- **A new socket/port** for memory — one-socket invariant. Memory is in-process file I/O only.
- **Writing to `~/.cache`** for `memory.db` — wrong durability tier. Memory is durable user data; use `app_data_dir()` (same base as `recordings/`), per ARCHITECTURE.md.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Top-k cosine ranking | A bespoke KNN / SQL `ORDER BY distance` | `library/_cosine.py::cosine_topk` (verbatim) | P55 Mac/Win bit-identity; float32 + shape asserts; deterministic tie-break already solved. |
| sqlite-vec vs numpy selection | A custom probe | Clone `library/store.py::open_store` | Probe-and-fall-through, structured logging, Win-ARM64 handling all shipped. |
| Embedding a text signature | A new genai client | `library/embed.py::LibraryEmbedder` | Proxy-only, FLEX-tier, 768-dim, content-hash cache, GA-rename probe — all shipped. |
| Model id resolution | A literal or a new resolver | `model_router.resolve("embedding")` | Already returns `("gemini-embedding-2", ServiceTier.FLEX)`; CI gate forbids literals. |
| Cache-dir resolution | `os.path` juggling | `runtime/config_store.py::app_data_dir()` | OS-aware (mac/win/linux), monkeypatch-friendly for tests. |
| Path-traversal defense on session_id | Ad-hoc validation | `recordings_index.py` regex `^\d{8}-\d{6}$` + `is_relative_to(root.resolve())` | Two-layer gate, symlink-escape-proof, already threat-modeled (T-15-03-01/05/08). |
| Retention / eviction | A new sweep | Mirror `recordings_index.py::run_retention_sweep` | ∞ sentinel, best-effort per-entry, byte accounting, Windows file-in-use handling shipped. |
| float32 round-trip / L2-normalize | Manual numpy | `library/_cosine.py::l2_normalize` + the backend blob round-trip | Byte-exact, parity-tested (`test_store_parity.py:159`). |

**Key insight:** This phase has essentially **no novel logic**. The only genuinely new code is the `moments` sibling table + the three-method wrapper that stitches the existing primitives together. If a plan proposes building any of the above, it is off-pattern — reject it.

## Runtime State Inventory

> This is a greenfield-storage phase (a NEW `memory.db` that does not yet exist), NOT a rename/refactor of existing runtime state. The standard Runtime State Inventory (stored data / live service config / OS-registered state / secrets / build artifacts) does not apply — there is no pre-existing `memory.db` to migrate, no service to reconfigure, no OS registration, no secret rename, no stale build artifact. **Verified:** `ls src/vibemix/memory/` → no package exists yet; `grep memory.db` → no current writer. The one forward-looking note is the install/signing item, captured in §sqlite-vec Install/Signing Landmine below.

## Common Pitfalls

### Pitfall 1: sqlite-vec one-click-install fragility (the KAAN-ACTION item)
**What goes wrong:** `vec0.dylib`/`vec0.dll` fails to load on a clean target (missing wheel on Win ARM64, unsigned binary tripping Gatekeeper/SmartScreen, PyInstaller not collecting the binary, "specified module not found" on Windows). Works in dev, crashes on first memory use on a fresh VM.
**Why it happens:** Extension loading is runtime + host-dependent; native binaries in a frozen bundle are a PyInstaller blind spot.
**How to avoid (Phase 63 engineering side):** Inherit the `open_store()` probe-and-fall-through verbatim (`open_memory_store()`). On ANY `sqlite_vec.load` failure → `NumpyStore`, which produces bit-identical results via the shared `cosine_topk`. There is **no correctness penalty** to the fallback, only perf at large N. The store layer is therefore install-fragility-proof by construction.
**How to avoid (downstream / KAAN-ACTION side):** The `vec0.*` binary is **already signed in shipping builds** (it ships for the library index). The new artifact is **only a data file (`memory.db`) — zero new signing surface.** The proof item is a clean-VM (incl. Windows ARM64) memory write→read round-trip in the e2e matrix, riding the existing Apple-notarization + SignPath external clock. **Surface this as KAAN-ACTION, NOT an engineering blocker for Phase 63.** (Verbatim ROADMAP framing in §sqlite-vec Install/Signing Landmine.)
**Warning signs:** logs show `backend=NumpyStore reason=sqlite_vec_unavailable` on a host that *should* support the extension (signing/packaging gap, not a true unsupported host).

### Pitfall 2: Orphaned vectors after delete (cascade gap)
**What goes wrong:** Deleting a session removes `moments` rows but leaves vectors in vec0 (or vice-versa) → dangling vectors retrieved with no metadata.
**Why it happens:** Two stores (vec0 + `moments`) with a non-atomic delete.
**How to avoid:** `delete_session` does both deletes then a single commit (Pattern 4). The boot-time orphan-reconciliation sweep is the defensive backstop: walk vec0 record_ids, drop any with no `moments` row (and, where cheap, any whose `session_id` no longer exists in the recordings index).
**Warning signs:** `query_topk` returns a `record_id` whose `moments` join is empty.

### Pitfall 3: The `moments` write half-succeeding on the numpy path
**What goes wrong:** Vector written to `.npy` but `moments` sqlite commit fails (or vice-versa) → split-brain across two files.
**Why it happens:** numpy fallback can't share a transaction with the `moments` sqlite file.
**How to avoid:** Order writes vector-first, `moments`-second; the boot sweep reconciles a vector with no `moments` row (drop it) — that direction is recoverable. Never write `moments` before the vector.

### Pitfall 4: Accidentally embedding via a generation model (no-extraction violation)
**What goes wrong:** A plan imports or calls a chat/generation model in the store path, opening the confabulation surface the whole milestone forbids.
**Why it happens:** "Let me summarize the signature first" temptation.
**How to avoid:** `MemoryStore` calls **only `LibraryEmbedder.embed_query`/the `embed_content` path** — never `client.models.generate_content`. Ship the static gate (Q5/Q6) that fails if `memory/` references any generation-model surface. Note: `memory/` should NOT import `vibemix.agent.*`, `vibemix.prompts.*`, or `vibemix.state.coach` at all.

### Pitfall 5: Dimension drift
**What goes wrong:** A 3072-dim vector reaches the store; `cosine_topk` asserts shape `(768,)` and fails (or worse, silently corrupts if asserts are stripped).
**How to avoid:** Reuse `EMBEDDING_DIM = 768` everywhere; `LibraryEmbedder` already returns 768-dim L2-normalized float32. Never re-truncate or re-normalize in `memory/`.

## Code Examples

### Example: clone of the parity test for `memory.db` (the STORE-01 gate)
```python
# tests/memory/test_store_parity.py  — clone of tests/library/test_store_parity.py
# Source: tests/library/test_store_parity.py:100-138 (the Mac↔Win backend parity test)
import sqlite3, numpy as np, pytest
from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize, cosine_topk
from vibemix.library.index_numpy import NumpyStore
from vibemix.memory.store import MemoryStore  # composes backend + moments

def _sqlite_vec_available() -> bool:
    try:
        import sqlite_vec
        db = sqlite3.connect(":memory:"); db.enable_load_extension(True)
        sqlite_vec.load(db); db.close(); return True
    except Exception:
        return False

SQLITE_VEC_AVAILABLE = _sqlite_vec_available()

@pytest.mark.parity
@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec extension unavailable")
def test_memory_sqlite_vec_topk_matches_numpy(tmp_path):
    """STORE-01 gate: sqlite-vec and numpy produce bit-identical top-k on memory.db."""
    rng = np.random.default_rng(7)
    records = []
    for i in range(100):
        v = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
        records.append((f"s1:{i}", "s1", float(i), "moment", f"sig {i}", v))
    # Two MemoryStore instances over tmp paths, one forced numpy, one sqlite-vec.
    sq = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=True)
    np_ = MemoryStore(db_path=tmp_path / "memory_np", prefer_sqlite_vec=False)
    for rid, sid, ts, kind, sig, vec in records:
        sq.add_record(rid, sid, ts, kind, sig, vec)
        np_.add_record(rid, sid, ts, kind, sig, vec)
    q = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
    a = [r.record_id for r in sq.query_topk(q, k=10)]
    b = [r.record_id for r in np_.query_topk(q, k=10)]
    assert a == b, "Mac↔Win parity broken on memory.db"
```

### Example: the no-live-path import gate (STORE-02 / no-live-path invariant)
```python
# tests/memory/test_no_live_path_import.py
# Precedent: tests/repo/test_repo_scrub.py:406 (subprocess sys.modules dormancy)
#          + tests/repo/test_model_literal_gate.py (static src scan)
import subprocess, sys, ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MEM = REPO / "src" / "vibemix" / "memory"
FORBIDDEN_IMPORTS = (  # the live reaction path + state surfaces memory must never import
    "vibemix.state.coach", "vibemix.state.refresh", "vibemix.agent",
    "vibemix.prompts", "vibemix.runtime.ws_bus",
)
FORBIDDEN_NAMES = ("MusicState", "EventDetector")

def test_memory_does_not_import_live_path_statically():
    for py in MEM.rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = [a.name for a in node.names]
                assert not any(mod.startswith(f) for f in FORBIDDEN_IMPORTS), (py, mod)
                assert not any(n in FORBIDDEN_NAMES for n in names), (py, names)

def test_importing_memory_loads_no_coach_loop():
    script = (
        "import sys, vibemix.memory.store\n"
        "leak = [m for m in sys.modules if m.startswith('vibemix.state.coach') "
        "or m.startswith('vibemix.agent') or 'ws_bus' in m]\n"
        "print('LEAKED:'+','.join(leak) if leak else 'CLEAN')\n"
    )
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                         cwd=REPO, env={**__import__('os').environ, 'PYTHONPATH': str(REPO/'src')})
    assert out.stdout.strip() == "CLEAN", out.stdout
```

### Example: the no-extraction gate (STORE-02 raw-in/raw-out)
```python
# tests/memory/test_no_extraction.py
# Precedent: tests/repo/test_repo_scrub.py:_strip_comments_and_docstrings (tokenize-stripped scan)
from pathlib import Path
import tokenize, io
REPO = Path(__file__).resolve().parents[2]
MEM = REPO / "src" / "vibemix" / "memory"
# Only embed_content may reach Gemini from memory/. generate_content == extraction.
FORBIDDEN = ("generate_content", "generate_reply", ".chats.", "GenerateContentConfig")
def _strip(src):  # reuse the tokenize stripper shape from test_repo_scrub.py
    kept = []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type in (tokenize.COMMENT, tokenize.STRING):
            if t.type == tokenize.STRING: kept.append(t._replace(string='""'))
            continue
        kept.append(t)
    return tokenize.untokenize(kept)
def test_memory_calls_only_embed_content():
    for py in MEM.rglob("*.py"):
        stripped = _strip(py.read_text())
        hits = [p for p in FORBIDDEN if p in stripped]
        assert not hits, f"{py} references a generation surface (extraction): {hits}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Managed memory framework (Mem0/Letta/Zep/Cognee) | DIY sqlite-vec + Gemini Embedding + `cosine_topk` | LOCKED (2026-05-18, mem0-rejected audit: 97.8% junk + hard `openai` dep) | No new dep, no extraction surface, no server. |
| LLM-extracted "insights" embedded | Raw text signature embedded verbatim (raw-in/raw-out) | LOCKED milestone thesis | Confabulation surface structurally removed. |
| Hardcoded embedding model literal | `model_router.resolve("embedding")` | Phase 41 (v3.0) | GA-rename-safe; CI gate forbids literals. |
| Native vec0 KNN for ranking | Storage-only vec0 + Python `cosine_topk` | Phase 28 (v2.1, P55) | Mac/Win bit-identical rank order. |

**Deprecated/outdated:**
- `gemini-embedding-001` (text-only GA) — the milestone intent is the multimodal `gemini-embedding-2`, already the router default. Never hardcode either; the literal is a CI canary.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Default retention numbers (~10,000 moments / ~180 days) are sensible per-install caps. | User Constraints / Pitfalls | LOW — these are explicitly Claude's-discretion in CONTEXT (within recommended ranges); tunable; whole-session eviction keeps retrieval coherent regardless of exact number. |
| A2 | `SqliteVecStore`'s `self.db` connection can host a second plain `moments` table in the same `memory.db` file, and `add_record` can commit vec0 + `moments` in one transaction on that connection. | Pattern 2 | LOW — this is standard sqlite (a vec0 virtual table and a normal table coexist in one DB file); the only nuance is whether to reuse the backend's connection or open a second one. Verify during planning by instantiating a memory `SqliteVecStore` and `CREATE TABLE moments` on `self.db`. |
| A3 | The cosine-vs-time-weight blend stays OUT of Phase 63 (`query_topk` ships plain cosine). | User Constraints | NONE — explicitly deferred to Phase 65 in CONTEXT + ROADMAP. |
| A4 | `gemini-embedding-2` returns 768-dim float32 L2-normalized via `LibraryEmbedder` with no per-call surprises for short text signatures. | Embedding Seam | LOW — the library embedder ships this path (`embed.py:362,535`); short text is the cheapest, most-tested path; STACK.md confirms gemini-embedding-2 auto-normalizes truncated dims and `LibraryEmbedder` L2-normalizes anyway. |

## Open Questions

1. **Reuse vs. fresh `SqliteVecMemoryStore` class.**
   - What we know: `SqliteVecStore` is path-parameterized (`db_path=`) but hardcodes the table name `vec_library` in its SQL strings (`index_sqlite_vec.py:51,77,81,89,103,110`).
   - What's unclear: whether to (a) parameterize the table name on the existing class (touches shipped library code — riskier, needs library regression run) or (b) ship a thin `memory/index_sqlite_vec_memory.py` that copies the ~120-line class with `vec_memory` + a `moments` table on the same connection.
   - Recommendation: **(b) — a small dedicated memory backend module.** Avoids touching shipped library code, keeps the `library/` parity tests untouched, and is the lower-risk reading of "compose, don't fork the chokepoint" (the *chokepoint* is `cosine_topk`, which is still imported, not copied). The ~120 duplicated storage lines are acceptable; the line that must NOT be duplicated is the ranking math.

2. **Where the `recordings_index` cascade hook gets wired.**
   - What we know: `RecordingsIndex.delete` (`recordings_index.py:370`) and `run_retention_sweep` (`:490`) are the deletion sites; `__main__.py` calls the sweep at boot (`:522`) and at session-close (`:1098`).
   - What's unclear: whether Phase 63 wires the actual call from `recordings_index.delete → MemoryStore.delete_session`, or whether it ships `delete_session` + a parity/cascade unit test and the *call-site wiring* lands with Phase 64/installer work.
   - Recommendation: ship `delete_session` + its unit test in Phase 63 (it's the store's contract). Wire the call from `recordings_index`/`__main__` in Phase 63 too **only if** it can be done without importing the live coach path — `recordings_index.py` is a runtime utility, not the reaction loop, so a `MemoryStore.delete_session` call from the delete path is safe and in-scope. Confirm with the planner; if it risks scope creep, defer the *call-site* to the phase that owns the recordings UI delete flow and keep Phase 63 to the store contract + test.

3. **Single connection vs. two connections to `memory.db` (sqlite-vec path).**
   - What we know: sqlite allows multiple connections to one file but with locking semantics; one connection avoids "database is locked" under the single-writer model.
   - Recommendation: one connection (reuse the backend's `self.db`) since memory has exactly one writer (ingest, off-loop) and Phase 63 is single-threaded unit-testable. Document the single-writer invariant in the module docstring (mirrors `MusicState`/`EvidenceRegistry` house style).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `sqlite-vec` extension (`vec0`) | vector storage backend | ✓ (dev box) / ✗ (Win ARM64) | `0.1.9` | `NumpyStore` via `open_memory_store()` probe — bit-identical results |
| stdlib `sqlite3` w/ `enable_load_extension` | vec0 host + `moments` table | ✓ | CPython 3.12 bundled | numpy fallback (no extension needed) |
| `google-genai` + Bravoh proxy | embedding the signature | ✓ | `2.0.1` | none needed at store layer — embedding is supplied by the caller (Phase 64); Phase 63 store tests use synthetic vectors, no live API |
| `ffmpeg` | NOT required (text-signature only; no audio embedding in v1) | n/a | — | n/a |

**Missing dependencies with no fallback:** none — the store layer needs no live API (tests use synthetic float32 vectors).
**Missing dependencies with fallback:** sqlite-vec on Win ARM64 → numpy backend (parity-identical, zero correctness cost).

## Validation Architecture

> `workflow.nyquist_validation` is not set to false (key absent in `.planning/config.json` per project convention) → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.x + `pytest-mock` (already dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`:196`); `--strict-markers`; `parity` marker registered (`:204`) |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory` |
| Full suite command | `uv run pytest -q` (or `PYTHONPATH=src python3 -m pytest -q`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STORE-01 | sqlite-vec ↔ numpy bit-identical top-k on `memory.db` | parity | `pytest -m parity tests/memory/test_store_parity.py -x` | ❌ Wave 0 |
| STORE-01 | numpy fallback engaged when extension unavailable; store still functional | unit | `pytest tests/memory/test_store.py::test_numpy_fallback -x` | ❌ Wave 0 |
| STORE-02 | `add_record`/`query_topk` round-trip; raw signature returned verbatim | unit | `pytest tests/memory/test_store.py::test_add_query_roundtrip -x` | ❌ Wave 0 |
| STORE-02 | `memory/` imports no live-path module; no extraction surface | unit (static + subprocess) | `pytest tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py -x` | ❌ Wave 0 |
| STORE-03 | `delete_session` removes vectors + `moments` atomically (no orphans) | unit | `pytest tests/memory/test_store.py::test_delete_cascade -x` | ❌ Wave 0 |
| STORE-03 | retention sweep evicts oldest-session-first, whole-session | unit | `pytest tests/memory/test_retention.py -x` | ❌ Wave 0 |
| STORE-03 | path-traversal: crafted session_id rejected | unit (security) | `pytest tests/memory/test_store.py::test_session_id_path_traversal -x` | ❌ Wave 0 |
| STORE-04 | embedding routes via `resolve("embedding")`; no model literal in `memory/` | unit (static, already-shipped gate covers it) | `pytest tests/repo/test_model_literal_gate.py -x` | ✅ (existing gate auto-covers new `memory/` files) |

### Sampling Rate
- **Per task commit:** `PYTHONPATH=src python3 -m pytest -q tests/memory` (the new package's tests; sub-second).
- **Per wave merge:** `pytest -m parity` + `tests/repo/test_model_literal_gate.py` (parity + literal gate).
- **Phase gate:** full suite green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/memory/__init__.py` — package marker.
- [ ] `tests/memory/test_store.py` — round-trip, numpy-fallback, delete-cascade, path-traversal (STORE-01/02/03).
- [ ] `tests/memory/test_store_parity.py` — `@pytest.mark.parity` Mac↔Win bit-identity (STORE-01).
- [ ] `tests/memory/test_no_live_path_import.py` — static + subprocess import-boundary gate (no-live-path invariant).
- [ ] `tests/memory/test_no_extraction.py` — tokenize-stripped scan: only `embed_content`, never generation (STORE-02 raw-in/raw-out).
- [ ] `tests/memory/test_retention.py` — oldest-session-first whole-session eviction (STORE-03).
- [ ] Reusable parity fixture: clone `tests/library/fixtures/` generation or generate synthetic 768-dim vectors in-test (the parity test above uses an in-test rng to avoid a new fixture file — preferred, keeps the repo lean).
- Framework install: none — pytest + parity marker already present.

## Security Domain

> `security_enforcement` not set to false → included. This is a local-only storage phase (no network surface beyond the proxied embedding call the caller supplies, no auth, no sessions, no web tier).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local single-user store. |
| V3 Session Management | no | "session" here = DJ-set session id, not a web session. |
| V4 Access Control | no | Single-user per-install; no multi-tenant boundary (documented out-of-scope per PITFALLS.md Pitfall 7). |
| V5 Input Validation | **yes** | `session_id` / `record_id` path-traversal defense: reuse `SESSION_DIR_RE` (`^\d{8}-\d{6}$`) + `Path.is_relative_to(root.resolve())` from `recordings_index.py` for any id that reaches the filesystem. Vector shape/dtype validated by `cosine_topk` asserts. |
| V6 Cryptography | no | No crypto in this layer; no key handling (the proxy holds the API key; `LibraryEmbedder` cannot read a raw key by design). |
| V12 File / Resource | **yes** | Confine all writes to `app_data_dir()`; never to the off-limits Hermes/LM-Studio privacy paths. Local-only, no exfiltration. |

### Known Threat Patterns for {local sqlite storage + embedding}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via crafted `session_id`/`record_id` (delete/read) | Tampering / EoP | Two-layer gate: regex shape + `is_relative_to` after `resolve()` (copy `recordings_index.py:390-401`). |
| Orphaned vectors after delete (data integrity) | Tampering | Atomic `delete_session` (Pattern 4) + boot orphan-reconciliation sweep. |
| Memory writes leaking outside the sanctioned cache dir | Information disclosure | All paths derive from `app_data_dir()`; extend the e2e privacy fixture (downstream) to assert no writes to `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/`. |
| Embeddings treated as "anonymous" / exempt from retention | Information disclosure | Subject embeddings to the same delete + retention contract as raw artifacts (delete cascades to vectors). |
| Unsigned `vec0.*` native extension | Tampering / supply-chain | Already signed in shipping builds; clean-VM round-trip is the proof item (KAAN-ACTION, not a Phase 63 engineering task). |
| Confabulation via a generation-model call in the store path | Spoofing (fabricated "facts") | No-extraction static gate (`test_no_extraction.py`): `memory/` calls only `embed_content`. |

## sqlite-vec Install/Signing Landmine (KAAN-ACTION — state crisply, do NOT treat as an engineering blocker)

Verbatim ROADMAP framing (`.planning/ROADMAP.md:58`):

> **Research/KAAN-ACTION flag**: sqlite-vec one-click-install fragility — the `vec0.dylib`/`vec0.dll` native binaries must be signed/notarized and a clean-VM (incl. Windows ARM64) memory round-trip proven in the e2e matrix. This rides the Apple notarization + SignPath external clock already on the critical path — surface it early so it parallelizes against the in-flight approvals. (The *binary* was already signed in shipping builds; the new artifact is only a data file with zero new signing surface, but the clean-VM round-trip is the proof item.)

**Crisp planner takeaway:**
- **Engineering surface for Phase 63 = ZERO new signing.** The new artifact is a *data file* (`memory.db`). The `vec0.*` binary is already in the signed sidecar (it ships for the library index). Phase 63 adds no binary.
- **The only forward item is a verification, on the external clock:** a clean-VM (Mac + Win, incl. Windows ARM64) `memory.db` write→read round-trip in the e2e install matrix. This is a KAAN-ACTION proof item that rides the already-pending Apple-notarization + SignPath approvals — it does NOT block Phase 63 engineering close under `gsd-autonomous fully`.
- **Plan accordingly:** Phase 63 ships the store + parity + gates and surfaces the clean-VM round-trip as a KAAN-ACTION line (mirroring how v4.0/v5.0 surface their live-confirm items). Do not insert an engineering "sign the binary" task — there is nothing new to sign.

## Project Constraints (from CLAUDE.md / memory)

- **Gemini-only.** No other LLM provider. Embedding = `gemini-embedding-2` via the router; no CLAP/MERT/OpenL3/torch/sentence-transformers (locked).
- **No managed memory frameworks.** Mem0/Letta/Zep/Cognee rejected — DIY sqlite-vec + Gemini Embedding wrapper only.
- **No-LLM-extraction.** Raw-in/raw-out; the store's only model call is the embed call.
- **Four cardinal invariants preserved by construction:** single-writer (memory's writer = ingest, off-loop; never writes `MusicState`), citation-grounding (downstream P65), trust-the-audio (memory never overrides live ears), one-socket (no new port — in-process file I/O only).
- **Strict per-file staging.** Commit memory store, tests, and any wiring as separate, scoped commits.
- **GSD workflow enforcement.** Phase work goes through the GSD command path; planning artifacts under `.planning/phases/63-memory-store/`.
- **Frontend skill:** N/A. Phase 63 is headless backend storage — no UI, no HTML/CSS/JS, no design contract. The `frontend-enforcement` skill does not apply; do not force frontend concerns into this phase. (The pill/mascot UI surfaces are Phase 65/66 territory, and even there only as additive citation chips.)

## Sources

### Primary (HIGH confidence — read from live source 2026-05-22)
- `src/vibemix/library/store.py` (`open_store` probe + `LibraryStore.search` chokepoint) — Q1/Q2
- `src/vibemix/library/index_sqlite_vec.py` (`SqliteVecStore`, path-parameterized, `vec_library` table) — Q1
- `src/vibemix/library/index_numpy.py` (`NumpyStore` fallback, atomic `os.replace`) — Q2
- `src/vibemix/library/_cosine.py` (`cosine_topk`, `l2_normalize`, `EMBEDDING_DIM=768`, determinism contract) — Q2
- `src/vibemix/library/embed.py` (`LibraryEmbedder`, `embed_query`, content-hash cache, `GEMINI_EMBEDDING_MODEL = resolve("embedding")[0]`) — Q3
- `src/vibemix/library/__init__.py` (clean re-export surface for `cosine_topk`/`NumpyStore`/`open_store`/`LibraryEmbedder`) — import seam
- `src/vibemix/llm/model_router.py` + `src/vibemix/llm/_router_config.py:40` (`"embedding" → ("gemini-embedding-2", ServiceTier.FLEX)`) — Q3/STORE-04
- `src/vibemix/runtime/recordings_index.py` (`SESSION_DIR_RE`, `is_relative_to` delete gate, `run_retention_sweep`, `compute_usage`) — Q4
- `src/vibemix/runtime/config_store.py:108,136` (`_app_data_dir`/`app_data_dir`) — Q4 cache base
- `src/vibemix/__main__.py:123,502-531,1088-1110` (recordings_root resolution, boot sweep, session-close sweep — wiring precedent) — Q4
- `tests/library/test_store_parity.py` (the parity test template + `@pytest.mark.parity`) — Q2
- `tests/repo/test_model_literal_gate.py` (model-literal CI gate — auto-covers new `memory/` files) — Q5/STORE-04
- `tests/repo/test_repo_scrub.py` (tokenize-stripped static scan + subprocess `sys.modules` dormancy — the import-boundary gate precedent) — Q6
- `pyproject.toml:118,196-208` (`sqlite-vec>=0.1.9`; `parity` marker registered) — stack + validation
- `.planning/ROADMAP.md:41,48-58` (Phase 63 framing + KAAN-ACTION sqlite-vec note verbatim) — KAAN-ACTION

### Secondary (HIGH — milestone research, corroborated by source above)
- `.planning/research/{SUMMARY,ARCHITECTURE,STACK,PITFALLS}.md` (the 4-agent reuse thesis; every integration point cross-checked against live source)
- `.planning/phases/63-memory-store/63-CONTEXT.md` (locked decisions — copied verbatim into User Constraints)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep already declared/installed; `_router_config.py:40` FLEX wiring confirmed in source.
- Architecture (compose-not-subclass, `moments` placement, cascade): HIGH — forced by reading `SqliteVecStore`/`NumpyStore` interfaces directly; the one nuance (A2: second table on the backend connection) is standard sqlite, flagged for a 1-line planning verification.
- Pitfalls: HIGH — all map to patterns vibemix already shipped (P55 parity, recordings_index path-traversal, open_store fallback) + the locked no-extraction rule.
- Validation/security: HIGH — parity marker + model-literal gate + repo-scrub static-gate precedent all exist and were read.

**Research date:** 2026-05-22
**Valid until:** ~2026-06-21 (stable — built on shipped in-repo primitives; only drifts if `library/` is refactored or sqlite-vec is bumped)
