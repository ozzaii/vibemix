# Phase 63: Memory Store - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous `fully` — grey areas auto-resolved with recommended answers; no human pause)

<domain>
## Phase Boundary

A local, per-install vector store for embedded session "moments" that is **proven correct in isolation** — built entirely on the shipped `src/vibemix/library/` primitives with **zero net-new dependency** (`sqlite-vec>=0.1.9` already declared/installed/signed-in-sidecar). This phase delivers ONLY the storage spine: a `memory.db` + a ~50-line `MemoryStore` wrapper exposing `add_record` + `query_topk`, with Mac/Win rank-identical retrieval, sqlite-vec→numpy fallback, retention + delete-cascade, and model-router-resolved embedding on the FLEX cost lane.

**Hard out-of-scope for this phase** (downstream phases own these):
- NO ingest job / artifact→signature conversion (Phase 64 writes to this store).
- NO retrieval seam / coach-prompt grounding / `recall` evidence source (Phase 65 reads this store).
- NO copilot move (Phase 66).
- **NO live reaction-path touch whatsoever** — this phase is unit-testable against `memory.db` with the co-host never running. A grep/import gate proves `memory/` does not import the coach loop or `MusicState`.
- NO audio embedding, NO LLM-extraction, NO time-weight/decay tuning (the cosine-vs-time blend is Phase 65's in-phase tuning; Phase 63 ships plain cosine `query_topk`).

</domain>

<decisions>
## Implementation Decisions

### Area 1 — Store composition & schema (reuse, don't fork)
- **Compose, don't subclass.** `MemoryStore` is a thin wrapper that holds a `LibraryStore`-style backend pointed at a separate `memory.db` path (NOT the library's track DB). It reuses `library/index_sqlite_vec.py::SqliteVecStore` (vec0 storage-only) + `library/index_numpy.py` fallback selected the same way `library/store.py::open_store(prefer_sqlite_vec=True)` does. The deterministic `library/_cosine.py::cosine_topk` stays the **single ranking chokepoint** — no forked KNN, no SQL `ORDER BY distance`.
- **Record id scheme:** deterministic `f"{session_id}:{seq}"` (stable, human-debuggable; enables session-scoped delete + current-session self-exclusion downstream). The embedding is keyed by this `record_id` in vec0.
- **Metadata lives in a sibling SQLite table in the same `memory.db`**, mirroring how the library separates ids from vectors: `moments(record_id PRIMARY KEY, session_id TEXT, ts REAL, kind TEXT, signature TEXT)`. vec0 holds only `(record_id → embedding)`. `add_record` writes both atomically; `query_topk` returns `record_id`s from `cosine_topk` then joins the sibling table for metadata.
- **Embedding dimension:** reuse the shipped `_cosine.EMBEDDING_DIM` constant — gemini-embedding-2's dim. No new dim, no per-store dim config.

### Area 2 — Retention, privacy, delete-cascade
- **Delete granularity = per session.** `delete_session(session_id)` removes every one of that session's vectors (vec0) **and** its `moments` rows in one transaction → no orphaned vectors. This is the cascade hook the existing recordings-delete path (`runtime/recordings_index.py`) calls when a session's recordings are deleted.
- **Retention budget:** a per-install cap that evicts **oldest-session-first**. Default generous + configurable via the existing config store: cap on moment count (recommend ~10,000 moments) AND/OR age (recommend ~180 days), whichever trips first. Eviction is whole-session (never partial-session) to keep retrieval coherent.
- **Location:** the app cache dir, same base resolution as `recordings_index` (per-install, local-only, user-deletable). Path-traversal-defended exactly like the shipped recordings/library path handling — no caller-supplied raw paths reach the filesystem.
- **Orphan reconciliation:** a boot-time sweep reconciles vec0 record_ids against the `moments` table (and, where cheap, against the recordings index) and drops danglers — defensive, transactional.

### Area 3 — Embedding routing & cost
- **Model resolution: `model_router.resolve("embedding")` ONLY** — never a hardcoded `gemini-embedding-001`/`gemini-embedding-2` literal. Reuse `library/embed.py`'s already-router-resolved client (`GEMINI_EMBEDDING_MODEL = resolve("embedding")[0]`). A CI grep gate asserts no hardcoded embedding-model literal exists in `memory/`.
- **Cost lane: `ServiceTier.FLEX`** through the Bravoh proxy (memory embedding is never latency-critical — it's off-hot-path by construction).
- **Idempotent embeds:** reuse `library/embed.py`'s content-hash embed cache so re-embedding identical signatures costs 0 API calls (load-bearing for Phase 64's re-ingest idempotency and the €50/mo budget).
- **Raw-in, raw-out:** a record carries the **raw text signature only** + its embedding + (session_id, ts, kind). **Never** an LLM-extracted "insight"/"tendency". `MemoryStore` has no path that calls a chat/generation model — embedding is the only model call, structurally.

### Claude's Discretion
- Exact wrapper line-count ("~50 lines" is a north-star, not a hard limit), the precise default retention numbers (within the recommended ranges above), and whether the boot-sweep lives in `MemoryStore` or a sibling helper — all at the planner's discretion, guided by the shipped `library/`/`recordings_index` conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (the whole point of this phase)
- `library/store.py` — `LibraryStore` wraps a `_Backend` Protocol (`add_batch`/`load_all`/`delete`/`snapshot_hash`/`close`) and `open_store(prefer_sqlite_vec=True)` does the sqlite-vec→numpy selection. The `MemoryStore` mirrors this composition against a `memory.db` path.
- `library/index_sqlite_vec.py` — `SqliteVecStore(db_path=...)` is already path-parameterized → point it at `memory.db`. vec0 storage-only.
- `library/index_numpy.py` — the numpy fallback backend (parity target).
- `library/_cosine.py` — `cosine_topk(query, vectors, track_ids, k)` (float32, shape-checked, `EMBEDDING_DIM`) + `l2_normalize`. THE deterministic ranking chokepoint reused verbatim → Mac/Win bit-identical rank order.
- `library/embed.py` — `GEMINI_EMBEDDING_MODEL = resolve("embedding")[0]`, content-hash cache, FLEX-tier client. Reuse for moment embedding.
- `llm/model_router.py::resolve("embedding")` — the router probe; the only sanctioned way to get the embedding model id.
- `runtime/recordings_index.py` — the shipped retention/delete machinery + path-traversal defense + per-install cache-dir resolution to mirror and hook the cascade into.

### Established Patterns
- Backend-behind-Protocol + a thin store wrapper; sqlite-vec primary with numpy fallback chosen at open time.
- `cosine_topk` as the single ranking path → `pytest -m parity` proves Mac/Win + sqlite-vec/numpy rank identity.
- Content-hash embed cache for idempotent, budget-safe embedding.
- Per-install cache-dir, local-only, path-traversal-defended storage.

### Integration Points
- WRITE side: Phase 64 ingest calls `MemoryStore.add_record(...)`.
- READ side: Phase 65 retrieval calls `MemoryStore.query_topk(...)`.
- DELETE side: `runtime/recordings_index` session-delete calls `MemoryStore.delete_session(session_id)` (cascade).
- This phase wires NONE of those consumers — it only ships + unit-proves the store.

</code_context>

<specifics>
## Specific Ideas

- Reuse over rewrite is the explicit milestone thesis (`.planning/research/SUMMARY.md`, 4 convergent agents): the embed→`cosine_topk`→cited-evidence machine already ships; `MemoryStore` is its second instance pointed at `memory.db`.
- The new artifact is a **data file only** (`memory.db`) — zero new signing surface vs the already-signed `vec0.dylib`/`vec0.dll`. The KAAN-ACTION proof item is a clean-VM (incl. Windows ARM64) memory round-trip in the e2e matrix, riding the existing Apple-notarization + SignPath external clock.
- Four cardinal invariants preserved by construction: memory never writes `MusicState` (single-writer), never opens a new socket (one-socket), never overrides live ears (trust-the-audio), and downstream retrieval is citation-grounded (Phase 65).

</specifics>

<deferred>
## Deferred Ideas

- **Ingest pipeline** (artifacts → signatures → `add_record`) → Phase 64.
- **Retrieval seam / `recall` evidence source / coach grounding** → Phase 65 (anti-slop release gate).
- **Visible copilot moves** → Phase 66.
- **Cosine-vs-time-weight blend + decay half-life tuning** → Phase 65 (in-phase, on Kaan's real corpus).
- **Audio-moment (multimodal) embedding** → future milestone (text-signature-only in v6.0).

</deferred>
