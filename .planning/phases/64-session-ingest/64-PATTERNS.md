# Phase 64: Session Ingest - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 5 (1 new module, 1 new test, 3 shipped gates verified/extended)
**Analogs found:** 5 / 5 (every primitive ships — zero net-new logic except the signature template + marker table + signature-keyed embed cache)

> All file:line refs below were re-verified against live `src/vibemix/` source on 2026-05-22 (not inherited from RESEARCH on trust). RESEARCH's three load-bearing findings hold: (1) `evidence_registry.json` absent on disk → citations are inline in `ai_text` text; (2) `embed_query` has NO content-hash cache (`embed.py:362-369`); (3) taxonomy = ONE kind `coach_line`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/memory/ingest.py` (NEW) | service (reader + builder + writer + sweep) | batch / file-I/O / transform | `debrief/session_loader.py` (reader) + `runtime/recordings_index.py` (sweep) + `library/embed.py` (cache) | role-match (composed from 3 analogs; no single 1:1 analog) |
| signature-keyed embed cache (inside `ingest.py`) | utility (content-hash cache) | transform | `library/embed.py` `embed_cache` table + `_cache_get`/`_cache_put` | exact (clone the table shape verbatim) |
| `memory_ingested` marker table (inside `ingest.py`) | model (sqlite schema) | CRUD | `memory/store.py` `moments` `CREATE TABLE` idiom | role-match |
| runtime wiring (`runtime/session_loop.py` seams — discretion) | controller (dispatch) | event-driven | `session_loop.py` `_fire_one_retention_sweep` `run_in_executor` dispatch (`:751`) | exact |
| `tests/memory/test_ingest.py` (NEW) | test | unit | `tests/memory/test_store.py` + `tests/memory/test_retention.py` | exact (shape clone) |
| `tests/memory/test_no_extraction.py` (SHIPPED — auto-covers) | test | static scan | itself (globs `memory/*.py`) | exact (no edit needed; verify it sees `ingest.py`) |
| `tests/memory/test_no_live_path_import.py` (SHIPPED — auto-covers) | test | static + subprocess | itself (globs `memory/*.py`) | exact (static auto-covers; **subprocess imports only `store` — see note**) |
| `tests/repo/test_model_literal_gate.py` (SHIPPED) | test | static scan | scans all `src/vibemix/` | exact (auto-covers; no edit) |

## Pattern Assignments

### `src/vibemix/memory/ingest.py` — Reader half (file-I/O)

**Analog:** `src/vibemix/debrief/session_loader.py`

**MIRROR the malformed-tolerant JSONL read** (`session_loader.py:74-88`) — re-implement, do NOT call `load_session` (it enforces a 5-min `SessionTooShort` floor and returns a debrief-shaped tuple; ingest must ingest short sessions too):
```python
# session_loader.py:74-88 — the ~12-line read to MIRROR (NOT inherit the 5-min floor at :140)
def _read_events(events_jsonl_path: Path) -> list[dict]:
    """Parse events.jsonl into a list of dicts; skip malformed lines."""
    events: list[dict] = []
    with events_jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError as e:
                logger.warning("[debrief] events.jsonl line %d malformed: %s", line_no, e)
    return events
```

**DO NOT inherit** (anti-pattern flagged by RESEARCH Pitfall / Open Q2):
- The 5-min `_MIN_SESSION_DURATION_S = 300.0` floor (`session_loader.py:31, :140-141`) — a debrief-UX rule, not an ingest rule.
- The `(events, evidence_snapshot, voice_meta)` tuple shape (`:115, :166`).
- Reading `evidence_registry.json` (`:143-156`) — **it does not exist on disk** (Finding 1); `load_session` returns `{}`. Citations live inline in `ai_text` text instead (see below).

**KEEP** the `InvalidSessionDir` / `is_dir()` guard idiom (`:130-136`) and the `events.jsonl` existence check (`:134-136`).

---

### `src/vibemix/memory/ingest.py` — Signature builder (transform, PURE — no model)

**Analog:** none in-repo (genuinely new logic) — but constrained by `EVIDENCE_CITATION_RE`.

**Citation grammar — COPY the constant** (do NOT import `evidence_registry`; RESEARCH §Off-Hot-Path recommends copy to keep import surface minimal/unambiguously gate-clean). Source-of-truth verified at `state/evidence_registry.py:117-135`:
```python
# state/evidence_registry.py:103-135 (VERIFIED) — 8 sources, locked EBNF grammar
EVIDENCE_SOURCES = frozenset({"ev", "aud", "midi", "track", "screen", "mix", "tend", "key"})
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend|key"
_INNER_ATOM = rf"(?:{_SOURCE_ALT}):[^\s,\]]+"
EVIDENCE_CITATION_RE = re.compile(rf"\[{_INNER_ATOM}(?:,{_INNER_ATOM})*\]")
```
When copied into `ingest.py`, add a comment pointing at `evidence_registry.py:133` (lock-step source-of-truth). The leading `[emotion]` TTS tag (`[chill]`/`[hype]`) is NOT a citation (no `source:` colon-form → won't match `EVIDENCE_CITATION_RE`) — strip with `^\[[a-z]+\]\s*`.

**Signature template** (deterministic; implement verbatim per RESEARCH §Signature Template Spec):
```
coach_line | track={track} | phase={phase} | deck={deck} | event={event_type} | cite={citation_tokens} | said: {reaction_text}
```
Determinism rules (load-bearing for cache hits): NO `t` in the embedded text (it goes to the `ts` column); citation tokens sorted; emotion-tag stripped deterministically. `SIG_TEMPLATE_VERSION = "v1-coach_line"`.

**Edge case (VERIFIED `dj_cohost.py:1054` emit vs `:1123` strip):** ingest ONLY `kind=="ai_text"` lines (heard); SKIP `citation_strip` (silenced — embedding it = confabulation). Per RESEARCH A3, `citation_bypass` is out-of-scope for v1.

---

### `src/vibemix/memory/ingest.py` — Embed call + signature-keyed cache (transform)

**Analog:** `src/vibemix/library/embed.py`

**The embed call** (`embed.py:362-369`, VERIFIED no cache):
```python
def embed_query(self, query: str) -> np.ndarray:
    """Embed a natural-language vibe-search query (text-only path).
    No content-hash cache here — Plan 28-03's 24h LRU sits on top of this..."""
    vec = self._call_gemini_text(query)
    return l2_normalize(vec)
```
This is the ONLY model call ingest may make — proxy-only, FLEX, 768-dim, L2-normalized. Model id source: `LibraryEmbedder._model` (probe-derived, `embed.py:301,308`) — NEVER a literal (the `test_model_literal_gate.py` canary scans `ingest.py`).

**Clone the cache table shape VERBATIM** (`embed.py:146-157`, VERIFIED):
```python
def _init_cache_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embed_cache (
            key TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            ts REAL NOT NULL
        )""")
    conn.commit()
```

**Clone the get/put round-trip** (`embed.py:605-623`, VERIFIED — the `(key, vector BLOB, ts)` proven round-trip):
```python
def _cache_get(self, key: str) -> np.ndarray | None:
    row = self._cache.execute("SELECT vector FROM embed_cache WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return np.frombuffer(row[0], dtype=np.float32).copy()

def _cache_put(self, key: str, vector: np.ndarray) -> None:
    import time as _time
    assert vector.dtype == np.float32 and vector.shape == (EMBEDDING_DIM,)
    self._cache.execute(
        "INSERT OR REPLACE INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
        (key, vector.tobytes(), _time.time()))
    self._cache.commit()
```

**Key derivation** (the Finding-2 fix; mirror `_track_hash` at `embed.py:583-601` but key on signature TEXT, not file bytes):
```python
# embed.py:597-601 — the (content || model || strategy_version) keying idiom to mirror
h.update(b"||"); h.update(self._model.encode())
h.update(b"||"); h.update(self._excerpt_strategy_version.encode())
# → ingest clones as: SHA256(signature || model_id || SIG_TEMPLATE_VERSION)
```
Shared `~/.cache/vibemix/embeddings.db` `embed_cache` table is safe (RESEARCH A2 — keys namespaced by distinct signature text) OR a sibling cache (planner discretion). `EMBED_CACHE_DB_PATH = Path.home()/".cache"/"vibemix"/"embeddings.db"` (`embed.py:99`).

---

### `src/vibemix/memory/ingest.py` — Write target (CRUD)

**Analog:** `src/vibemix/memory/store.py` `MemoryStore.add_record` (`store.py:271-310`, VERIFIED — Phase 63 contract, do NOT re-open the DB ad hoc):
```python
def add_record(self, record_id: str, session_id: str, ts: float,
               kind: str, signature: str, embedding: np.ndarray) -> None:
    _validate_session_id(session_id, self._db_path)   # path-traversal gate (T-63-07) BEFORE any write
    self._backend.add_batch([(record_id, embedding)]) # vector-first
    self._moments.execute(
        "INSERT OR REPLACE INTO moments (record_id, session_id, ts, kind, signature) "
        "VALUES (?, ?, ?, ?, ?)",
        (record_id, session_id, float(ts), kind, signature))
    self._moments.commit()
```
Per record: `record_id = f"{session_id}:{seq}"` (seq = 0-based index of emitted `ai_text` line; matches Phase-63 PK scheme), `session_id` = dir basename `YYYYMMDD-HHMMSS` (re-validated on write), `ts` = the line's `t`, `kind = "coach_line"`, `signature` = verbatim assembled string. NOT atomic across the two commits (`store.py:282-293` docstring) — ingest must not assume atomicity.

**`memory_ingested` marker schema** (NEW — mirror the `moments` `CREATE TABLE IF NOT EXISTS` idiom at `store.py:252-260`):
```sql
CREATE TABLE IF NOT EXISTS memory_ingested (
    session_id           TEXT PRIMARY KEY,
    ingested_at          REAL NOT NULL,
    sig_template_version TEXT NOT NULL
);
```
**A4 / Open-Q1 marker↔retention coupling (MEDIUM risk — flag for planner):** Phase-63 `delete_session` does NOT know about this table. Do NOT modify shipped `delete_session`. Prefer (b) gate idempotency on a cheap `COUNT(*) FROM moments WHERE session_id=?` OR (c) reconcile the marker against `moments` in the boot sweep (drop markers for sessions with 0 moments). Planner picks the one that leaves Phase-63 code untouched.

---

### `src/vibemix/memory/ingest.py` — Boot sweep (batch / file-I/O)

**Analog:** `src/vibemix/runtime/recordings_index.py` (MIRROR, do NOT import — it imports `vibemix.ui_bus.messages`; copying the FS-safety shapes matches Phase-63's established "copy, don't import" discipline).

**Session-dir regex** (`recordings_index.py:78`, VERIFIED):
```python
SESSION_DIR_RE: re.Pattern[str] = re.compile(r"^\d{8}-\d{6}$")
```

**Two-layer path-traversal gate** (`recordings_index.py:388-401`, VERIFIED — copy before reading any session dir, per Security V5/V12):
```python
if not isinstance(session_dir_name, str):           return ...   # reject
if not SESSION_DIR_RE.match(session_dir_name):      return ...   # layer 1: regex
target = (recordings_root / session_dir_name).resolve()
root_resolved = recordings_root.resolve()
if not target.is_relative_to(root_resolved):        return ...   # layer 2: containment
if target == root_resolved:                          return ...   # never the root itself
```

**Best-effort sweep shape** (`recordings_index.py:490-524` `run_retention_sweep`): `os.scandir` the root, filter `SESSION_DIR_RE`, skip marked sessions, `ingest_session` the rest; per-entry failures log + continue (never raise); never block boot. Add a sibling `run_ingest_sweep(recordings_root, store, embedder)` in `ingest.py`.

---

### Runtime wiring (controller, event-driven) — `runtime/session_loop.py` (planner discretion: ship here OR scope-note)

**Analog / seams:** `runtime/session_loop.py` (both seams already exist, both already use `run_in_executor`).

**Session-close seam** (`session_loop.py:709 on_session_close`, called from `__main__` close path AFTER `recorder.close()` finalizes `session.json`). The dispatch idiom to copy (`session_loop.py:747-756`, VERIFIED):
```python
if self.recordings_root is None:
    return
try:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        run_retention_sweep,           # ← ingest enqueues ingest_session(session_dir, store, embedder) the same way
        self.recordings_root,
        self.config_store.retention_days,
    )
```

**Boot seam** (`session_loop.py:685 run_boot_sweeps`, delegates to `_fire_one_retention_sweep("boot")`). Add a sibling `run_ingest_sweep` call via `run_in_executor` — either inside `run_boot_sweeps` or as a parallel boot step. Best-effort + never-raise (matches the existing contract).

**One-way arrow (the gate-safe wiring):** the runtime imports `memory.ingest`; `memory.ingest` NEVER imports `runtime.session_loop` / `state.coach` / `agent` / `prompts` / `ws_bus` / `MusicState`. This keeps `test_no_live_path_import.py` green.

---

### `tests/memory/test_ingest.py` (NEW) — test

**Shape analog:** `tests/memory/test_store.py` + `tests/memory/test_retention.py`.

Clone the deterministic-vector helper (`test_store.py:40-43`, VERIFIED):
```python
def _vec(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
```
Imports to mirror: `from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize`; `from vibemix.memory.store import MemoryStore`; `tmp_path` fixture; `prefer_sqlite_vec=False` for the numpy parity path (`test_store.py:53`). Tests required (RESEARCH Test Map): `test_signature_deterministic`, `test_ingest_emits_coach_lines` (+ skips `citation_strip`), `test_reingest_is_noop` (0 embeds / 0 new records), `test_records_tagged`, `test_embed_cache_hit`, `test_sweep_uses_executor`. Generate a synthetic `events.jsonl` fixture in-test (mirror real on-disk shapes: `event` lines w/ `type/track/phase/deck`, `ai_text` lines w/ `[emotion]`-prefixed text + optional `[aud:rms@…]`, plus a `citation_strip` line to assert it's skipped).

## Shared Patterns

### No-extraction gate (auto-covers `ingest.py` — NO EDIT NEEDED)
**Source:** `tests/memory/test_no_extraction.py:79-82` (VERIFIED globs `memory/*.py`)
**Apply to:** `ingest.py` automatically.
```python
MEM = REPO / "src" / "vibemix" / "memory"
def _memory_py_files() -> list[Path]:
    if not MEM.exists():
        return []
    return sorted(MEM.rglob("*.py"))   # ← picks up ingest.py the moment it lands
FORBIDDEN = ("generate_content", "generate_reply", ".chats.", "GenerateContentConfig")
```
`ingest.py`'s only model call must be `embedder.embed_query(...)`. **Add a focused positive test** in `test_ingest.py` (or extend this file) asserting `ingest.py` contains `embed_query`/`LibraryEmbedder` and none of the FORBIDDEN tokens.

### No-live-path import boundary (static auto-covers; subprocess does NOT yet)
**Source:** `tests/memory/test_no_live_path_import.py:51-54` (static, globs `memory/*.py`) + `:95-119` (subprocess).
**Apply to:** `ingest.py`.
- **Static AST gate (`:57-92`) auto-covers** `ingest.py` — forbids importing `vibemix.state.coach` / `vibemix.state.refresh` / `vibemix.agent` / `vibemix.prompts` / `vibemix.runtime.ws_bus` and the names `MusicState` / `EventDetector`.
- **GAP — the subprocess dormancy gate (`:107-119`) imports ONLY `vibemix.memory.store`**, not `ingest`. To get true runtime-dormancy coverage for `ingest.py`, the planner should ADD a parallel subprocess assertion that `import vibemix.memory.ingest` leaks no live-path module (clone the `:107-130` block, swap `store`→`ingest`). Not strictly required (static gate covers imports), but recommended for parity.

### Lazy runtime-config import (keeps the dormancy gate green)
**Source:** `memory/store.py:71-83` (VERIFIED) — `app_data_dir` imported function-local, NOT module-level.
**Apply to:** `ingest.py` if it needs `app_data_dir()` / any `vibemix.runtime.config_store` symbol for the cache/marker path. A module-level `from vibemix.runtime... import` risks pulling runtime into `sys.modules` and tripping the dormancy gate. Mirror store's lazy-import discipline.

### Off-hot-path dispatch
**Source:** `runtime/session_loop.py:750-756` (VERIFIED).
**Apply to:** both ingest triggers (session-close, boot sweep) — `loop.run_in_executor(None, fn, *args)`. Never inline on the reaction loop.

### Model-literal gate (auto-covers — NO EDIT)
**Source:** `tests/repo/test_model_literal_gate.py` (scans all of `src/vibemix/`).
**Apply to:** `ingest.py` — never hardcode `gemini-embedding-2`/`gemini-embedding-001`; resolve via `LibraryEmbedder._model` (it does `resolve("embedding")` internally).

## No Analog Found

| File / unit | Role | Data Flow | Reason |
|-------------|------|-----------|--------|
| `build_coach_line_signature(...)` (the template string) | utility | transform | Genuinely new — pure string assembly. NOT scope creep: it is the phase's core deliverable (INGEST-01/03), constrained by the COPIED `EVIDENCE_CITATION_RE` + the byte-reproducibility rule. No model in the path (no-extraction gate enforces). |
| `memory_ingested` marker table | model | CRUD | New schema; structurally clones the `store.py:252-260` `CREATE TABLE IF NOT EXISTS` idiom. Not off-pattern. |

**No off-pattern scope creep detected.** Every other unit composes a shipped primitive. Per RESEARCH/CONTEXT: do NOT touch Phase-63 `store.py` internals (compose `add_record`; the marker-coupling is solved without editing `delete_session`), and do NOT modify `library/embed.py` (the new embed cache is a CLONE living in the memory/ingest layer, not a library edit).

## Metadata

**Analog search scope:** `src/vibemix/memory/`, `src/vibemix/debrief/`, `src/vibemix/library/`, `src/vibemix/runtime/`, `src/vibemix/state/`, `tests/memory/`
**Files scanned:** 8 source files + 5 test files (verified the 11 RESEARCH-cited file:line anchors against live source)
**Pattern extraction date:** 2026-05-22
