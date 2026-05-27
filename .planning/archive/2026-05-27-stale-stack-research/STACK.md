# Stack Research — v6.0 "The Memory Turn" (session-memory / embedding-retrieval layer)

**Domain:** Local embedded vector memory for a Gemini-only live DJ co-host (Python 3.12, uv, Tauri sidecar, one-click install Mac+Win)
**Researched:** 2026-05-22
**Confidence:** HIGH (both core deps are already declared + installed in the repo; live ecosystem versions verified against PyPI + official Gemini docs + Context7)

---

## TL;DR for the roadmap

**The memory layer is almost entirely a REUSE play, not a net-new stack.** vibemix already shipped a production sqlite-vec + Gemini Embedding 2 + deterministic `cosine_topk` subsystem in **v2.1 Phase 28** and hardened it in **v3.0 Phase 41** (MRL-768, GA-rename probe, Mac/Win parity, proxy-only client). The memory layer's job is to add a **second store** (`sessions.db`) and a **~50-line wrapper** on top of the *exact same primitives* — not to introduce new technology.

- **Net-new dependencies: ZERO.** `sqlite-vec>=0.1.9` is already in `pyproject.toml` (line 118). `google-genai`, `numpy`, `scipy` are already core deps. The wrapper is pure-Python on top of the stdlib `sqlite3` + existing modules.
- **The one correction to surface:** the LOCKED model literal "`gemini-embedding-001`" is the **text-only GA** model. The milestone's actual intent (multimodal: text + audio Parts, 180s cap) is served by **`gemini-embedding-2`** (preview, native 3072-dim). The codebase *already routes to this* via `EMBEDDING_GA_CANDIDATES = ("gemini-embedding-002", "gemini-embedding-2")` with a runtime GA-rename probe. See [Model ID Resolution](#model-id-resolution--read-this).
- **One-click install: GREEN.** sqlite-vec ships prebuilt per-OS wheels with a tiny (~160 KB) bundled extension binary. No compiler, no system SQLite dependency. The one platform gap (Windows ARM64 has no wheel) is *already handled* by the existing `open_store()` numpy-fallback probe. No new signing/notarization snag for the Tauri sidecar.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **sqlite-vec** | `0.1.9` (current latest; already pinned `>=0.1.9`) | `vec0` virtual-table vector store for the session-memory DB | Pure-C SQLite extension, ~160 KB prebuilt binary, zero server, single `sqlite_vec.load(conn)` call. **Already a declared + installed dep.** Same backend as the library index — reuse all of `_cosine.py`, the `open_store()` probe, and the Mac/Win parity discipline. |
| **google-genai** | installed `2.0.1` (latest `2.5.0`) | `embed_content` calls for `gemini-embedding-2` | Already the sole AI SDK in the repo. Embedding path already implemented in `src/vibemix/library/embed.py` (audio Parts + text, MRL-768, cache-keyed). Memory layer reuses `LibraryEmbedder` / the same `embed_content` shape verbatim. |
| **gemini-embedding-2** | model SKU (preview; native 3072-dim) | The embedding model — natively multimodal (text + image + audio + video + PDF in one space) | The milestone's "Gemini Embedding 002 / natively multimodal" decision. Audio cap 180 s, MRL truncation to 768 (already locked in `_cosine.EMBEDDING_DIM`), auto-normalizes truncated dims. Routed via `model_router.resolve("embedding")` — never hardcoded. |
| **numpy** | `2.4.4` (already core) | float32 vector math, L2-normalize, `cosine_topk` ranking | Already core. The memory store is **storage-only** in sqlite-vec (P55 parity rule); ranking happens in `cosine_topk()` on numpy arrays, identical to the library backend. |
| **stdlib `sqlite3`** | bundled (CPython 3.12, libsqlite **3.50.4** on dev box) | DB connection, schema, blob I/O, metadata columns | No new dep. `vec0` loads as an extension on top of stdlib `sqlite3`. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **scipy** | `1.17.1` (already core) | Resampling if any audio excerpt prep is reused | Only if the memory layer ever embeds *audio* records (vs. structured/text records). For v1, structured-text records likely dominate (see Architecture/Pitfalls research). Reuse `library/embed.py`'s ffmpeg 3-excerpt-mean path for any >180 s audio — do **not** reinvent. |
| **ffmpeg** (system binary, not pip) | any | 60 s excerpt extraction for >180 s audio embeds | Only on the audio-record path. Already a documented prereq (`brew install ffmpeg` / `winget install Gyan.FFmpeg`) and fail-loud-checked in `library/embed.py:_require_ffmpeg()`. Prefer text/structured records to avoid this dependency entirely for v1 memory. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` + `pytest-mock` (already dev deps) | wrapper unit tests + Mac/Win parity gate | Reuse the `parity` marker convention (`pytest -m parity`) already defined in `pyproject.toml` for the library backend. The memory store gets the same bit-identical-top-K gate. |
| `vcrpy` + `pytest-recording` (already dev deps) | cache `embed_content` calls so CI runs at $0 | Already wired for the eval suite. Memory-layer embed tests should use the same cassette discipline — no live Gemini in PR CI. |
| `uv` | resolver + lockfile | No `pyproject.toml` change needed for sqlite-vec (already present). If bumping `google-genai`, do it as a separate hermetic `uv lock` regen (see Version Compatibility). |

---

## Installation

**No `pip install` / `uv add` is required for the memory layer** — every dependency is already in `pyproject.toml`. Confirmation only:

```bash
# Already present in pyproject.toml dependencies:
#   "sqlite-vec>=0.1.9"
#   "google-genai>=2.0.1"
#   "numpy>=2.4.4"
#   "scipy>=1.17.1"

# Verify the sqlite-vec extension loads on the host (this is what open_store() probes):
uv run python -c "import sqlite3, sqlite_vec; \
db=sqlite3.connect(':memory:'); db.enable_load_extension(True); \
sqlite_vec.load(db); print(db.execute('select vec_version()').fetchone())"
# -> ('v0.1.9',)
```

### sqlite-vec one-click-install impact (the HARD requirement)

**Verdict: GREEN — already proven by the shipping library index.**

| Concern | Finding | Source / Evidence |
|---------|---------|-------------------|
| Prebuilt wheels? | **Yes.** sqlite-vec 0.1.9 publishes `py3-none-` wheels per OS/arch: `macosx_11_0_arm64`, `macosx_10_6_x86_64`, `win_amd64`, `manylinux x86_64`, `manylinux aarch64`. | PyPI `sqlite-vec/json` (verified 2026-05-22) |
| What gets bundled? | A single tiny shared library named **`vec0`** with an OS suffix: `vec0.dylib` (Mac, 162 KB Mach-O arm64 on dev box), `vec0.dll` (Win), `vec0.so` (Linux). No C compiler, no system SQLite version dependency, no headers. | `.venv/.../sqlite_vec/vec0.dylib` inspected; `sqlite_vec.loadable_path()` returns the suffix-less stem, `load()` appends the OS suffix. |
| How it loads | `sqlite_vec.load(conn)` → `conn.load_extension(loadable_path())`. Requires `conn.enable_load_extension(True)` first (CPython's stdlib `sqlite3` supports this on Mac + Windows official builds). | Existing `index_sqlite_vec.py:44-49`; Context7 `/asg017/sqlite-vec`. |
| Windows ARM64 | **No wheel exists** (only `win_amd64`). | PyPI verified. **Already mitigated:** `open_store(prefer_sqlite_vec=True)` catches the `sqlite_vec.load()` failure and falls through to `NumpyStore`. The memory store MUST reuse this exact probe — do not assume sqlite-vec is always present. |
| Tauri sidecar signing/notarization snag? | **None new.** The `.dylib`/`.dll` is bundled by PyInstaller into the `--onedir` sidecar (already the case for the library index in shipped v2.1/v3.x builds). Apple notarization of the sidecar already covers nested dylibs; SignPath covers the Windows binary. The memory DB is a *new data file* (`~/.cache/vibemix/sessions.db`), not a new binary — zero signing surface. | Inferred from v3.0/v3.1 install chain (Phases 33/38/49) which already ships `vec0.dylib`/`vec0.dll` inside the signed sidecar; the existing `library.db` proves the path. |
| CPython `sqlite3` extension-loading disabled? | Not on the official CPython builds vibemix ships (PyInstaller bundles the standard `_sqlite3` which has `enable_load_extension`). Only some distro/Homebrew Pythons disable it — irrelevant since the sidecar bundles its own interpreter. | Dev-box probe succeeded; `enable_load_extension(True)` works. |

**Bottom line:** the memory store inherits a one-click-install path that already cleared Apple + SignPath in the shipping build. The only new artifact is a data file. No green/yellow/red regression.

---

## The ~50-line wrapper — recommended API surface

The wrapper is a **second store instance**, not new infrastructure. It mirrors `LibraryStore` but stores *session moments* keyed by time, with metadata columns living in the `vec0` table itself (sqlite-vec supports typed metadata columns + `+`-prefixed auxiliary columns — so the raw record text rides *inside* the same row, no JSON sidecar needed).

**Recommended `vec0` schema** (verified syntax, Context7 `/asg017/sqlite-vec`):

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS vec_sessions USING vec0(
    record_id    TEXT PRIMARY KEY,
    embedding    FLOAT[768] distance_metric=cosine,  -- EMBEDDING_DIM (MRL-truncated)
    session_id   TEXT,        -- metadata column (filterable in KNN)
    event_type   TEXT,        -- metadata column (e.g. TRACK_CHANGE, MIX_MOVE)
    ts           FLOAT,       -- unix epoch; drives the optional time-weight
    +raw         TEXT         -- auxiliary column: the raw record text (NO LLM extraction)
);
```

**Recommended wrapper API** (mirrors `store.py` so downstream coach-grounding code is symmetric):

```python
class SessionMemory:
    def add_record(record_id: str, vector: np.ndarray, *,
                   session_id: str, event_type: str, ts: float, raw: str) -> None: ...
        # float32 (768,) assert; delete-then-insert for deterministic replace
        # (vec0 has no uniform INSERT OR REPLACE on the virtual layer — same
        #  pattern as SqliteVecStore.add_batch)

    def query_topk(query_vec: np.ndarray, k: int = 8, *,
                   time_weight: float | None = None,
                   now: float | None = None) -> list[Record]: ...
        # STORAGE-ONLY load + shared cosine_topk (P55 parity rule), THEN
        # optional time-decay re-rank:  score = cosine * exp(-lambda * age_days)
        # Keep ranking in Python/numpy so Mac (sqlite-vec) and Win (numpy
        # fallback) return bit-identical orders. Do NOT use vec0 MATCH/k= for
        # ranking — it can diverge on tied similarities (Pitfall P55).
```

**Two viable ranking paths — recommend the storage-only one for v1:**

1. **Storage-only + Python `cosine_topk` (RECOMMEND).** Reuse `library/_cosine.py` verbatim. Guarantees Mac/Win parity, makes the time-weight blend trivial (it's just a numpy multiply after cosine), and matches the shipped library discipline. The KNN happens over the in-process numpy array.
2. **Native `vec0` KNN** (`WHERE embedding MATCH ? AND k = ?`, or `ORDER BY distance LIMIT ?`). Faster at large N and supports metadata pre-filtering (`AND session_id = ?`) — but it (a) only exists on the sqlite-vec backend (Windows ARM64 falls back to numpy and *must* match), and (b) can diverge on tied distances. Only consider this if session corpora grow large enough that loading all vectors per query becomes a latency problem on the live coach path — unlikely for a single DJ's session history.

The time-weight blend is the one genuinely new bit of logic. Everything else is a thin re-skin of the library store.

---

## Model ID Resolution — READ THIS

The locked decision text says **`gemini-embedding-001`**, but that literal is the **text-only GA** model (2,048-token cap, no audio Parts). The milestone's stated intent — *"natively multimodal text+image+audio… ~180 s audio cap"* — is the **`gemini-embedding-2`** model (preview as of 2026-05; native 3072-dim, 180 s audio, 8,192 text tokens, auto-normalizes truncated dims). These are the facts to confirm with Kaan, not re-litigate:

| Capability | `gemini-embedding-001` (text GA) | `gemini-embedding-2` (multimodal) |
|------------|----------------------------------|-----------------------------------|
| Modalities | text only | text + image + audio + video + PDF, one space |
| Audio Parts | ✗ | ✓ (180 s cap) |
| Native dim | 3072 | 3072 |
| MRL `output_dimensionality` | 128–3072 (manual normalize if <3072) | 128–3072 (**auto-normalizes** truncated) |
| Text token cap | 2,048 | 8,192 |
| Paid price (input) | $0.15 / 1M tok | $0.20 / 1M text · $6.50 / 1M audio |

**Action:** the codebase already does the right thing — `_router_config.EMBEDDING_GA_CANDIDATES = ("gemini-embedding-002", "gemini-embedding-2")` plus the runtime `_probe_ga_model_id()` GA-rename probe lands on whatever ID is live. The memory layer must call **`model_router.resolve("embedding")`** (or reuse `LibraryEmbedder`), never hardcode a literal — the CI grep gate (`check_no_hardcoded_model.sh`) enforces this. If Kaan truly wants text-only-001 (cheaper, no audio), that's a one-line `_router_config.py` change; otherwise default to the multimodal `gemini-embedding-2` the milestone describes.

### embed_content call shape (verified, google-genai)

```python
from google import genai
from google.genai import types

# TEXT record (note: contents is a bare string, NOT a list — SDK 2.0.1 contract)
result = client.models.embed_content(
    model=model_id,                       # from model_router.resolve("embedding")
    contents="TRACK_CHANGE | Amelie Lens - In My Mind | 138 BPM | key 4A | phase=drop",
    config=types.EmbedContentConfig(output_dimensionality=768),
)
vec = np.asarray(result.embeddings[0].values, dtype=np.float32)

# AUDIO record (only if embedding raw audio moments; >180 s → 3-excerpt mean)
result = client.models.embed_content(
    model=model_id,
    contents=[types.Part.from_bytes(data=clip_bytes, mime_type="audio/mpeg")],
    config=types.EmbedContentConfig(output_dimensionality=768),
)
```

### Batching / rate / cost notes

- **Batch limit:** `embed_content` accepts a list of `contents` in one call; the multimodal model documents per-call limits of 8,192 text tokens / 6 images / 120 s video / **180 s audio** / 6 PDF pages. For many *separate* records, loop or use the Batch API (50% cheaper, async) on the ingest path — never on the live coach path.
- **Rate limits** (these bind the **Bravoh proxy's** paid key, not per-end-user — the proxy holds the key per the locked security model): embeddings free tier ≈ 100 RPM / 1,000 RPD; paid Tier 1 ≈ 150–300 RPM, scaling with spend. Ingest is a batch/offline path → route it through `ServiceTier.FLEX` (already the `embedding` route's tier in `_router_config.py`), which the repo already uses for the 50% cost lane.
- **Cost reality at vibemix scale:** a session's structured records are tiny (a few hundred short text strings ≈ well under 1M tokens). At $0.20/1M text tokens, embedding a full session is fractions of a cent. Audio records ($6.50/1M audio tok) are the expensive path — another reason to favor structured-text records for v1 and gate audio embedding behind the acid test.
- **Cache it:** reuse `library/embed.py`'s SHA256(`content || model_id || strategy_version`) cache (`~/.cache/vibemix/embeddings.db`) so re-ingest = 0 API calls. The memory ingest pipeline should key the same way.

---

## Reused vs. Net-New (explicit, per the quality gate)

| Component | Status | Source |
|-----------|--------|--------|
| `sqlite-vec` dependency | **REUSE** — already declared `>=0.1.9`, already installed, already bundled in signed sidecar | `pyproject.toml:118` |
| `vec0` store pattern (load + create + add_batch + load_all) | **REUSE** — copy `index_sqlite_vec.py` shape, add metadata + `+raw` columns | `src/vibemix/library/index_sqlite_vec.py` |
| `open_store()` numpy-fallback probe (Win ARM64) | **REUSE verbatim** — memory store needs the identical fallback | `src/vibemix/library/store.py:78` |
| `cosine_topk` + `l2_normalize` + `EMBEDDING_DIM=768` | **REUSE verbatim** — Mac/Win parity (P55) | `src/vibemix/library/_cosine.py` |
| `embed_content` call shape (text + audio Part) | **REUSE** — `LibraryEmbedder` already implements both | `src/vibemix/library/embed.py` |
| Model routing (`resolve("embedding")` + GA-rename probe) | **REUSE** — never hardcode the literal | `src/vibemix/llm/_router_config.py`, `model_router.py` |
| SHA256 embed cache | **REUSE** — same cache discipline for ingest | `src/vibemix/library/embed.py` (`embeddings.db`) |
| Proxy-only Gemini client (no raw key) | **REUSE** — security invariant | `build_proxy_genai_client` (per `embed.py` docstring) |
| `google-genai`, `numpy`, `scipy` | **REUSE** — already core deps | `pyproject.toml:28-38` |
| **`sessions.db` (`vec_sessions` table)** | **NET-NEW** — a new data file at `~/.cache/vibemix/sessions.db`, distinct from `library.db` / `embeddings.db` / `library.pkl` | new |
| **`SessionMemory` ~50-line wrapper** | **NET-NEW** — `add_record` / `query_topk(+time_weight)` | new |
| **Ingest pipeline** (events.jsonl → typed embeddable records) | **NET-NEW** — raw-in/raw-out, no LLM extraction | new |
| **Time-weight re-rank** (`cosine * exp(-λ·age)`) | **NET-NEW** — the only genuinely new math | new |

**No new third-party packages.** The entire memory layer is a wrapper + a data file on top of the already-shipped library subsystem.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| sqlite-vec `vec0` storage-only + Python `cosine_topk` | sqlite-vec native KNN (`MATCH ... AND k =`) | Only if a single DJ's session corpus grows large enough that loading all vectors per live-coach query becomes a measurable latency cost — and even then only with the Win-ARM64 numpy-fallback parity risk understood. Unlikely at vibemix scale. |
| sqlite-vec | `sqlite-vector` (sqliteai), `sqlite-vss`, FAISS, chromadb, lancedb | Never for vibemix. sqlite-vec is already locked, already shipped, has the smallest install footprint, and `sqlite-vss` is its deprecated predecessor. FAISS/chroma/lance add heavy native deps that break the one-click-install budget. |
| `gemini-embedding-2` (multimodal) | `gemini-embedding-001` (text GA) | If Kaan decides memory records are *always* text (no raw-audio embedding), 001 is cheaper ($0.15 vs $0.20/1M) and has a smaller blast radius. One-line `_router_config.py` swap. Default stays multimodal per milestone intent. |
| MRL 768 (`EMBEDDING_DIM`) | 1536 / 3072 | If retrieval recall on session moments measurably regresses vs. the 768 library baseline. Rollback path already documented in `_cosine.py` (bump dim → bump cache version → re-embed). Costs +33% storage at 1024, +100% at 1536. |
| Storage-only ranking in numpy | sqlite-vec metadata pre-filter in SQL (`AND session_id = ?`) | Useful for scoping retrieval to one session or one event_type *before* KNN — but only on the sqlite-vec backend. If used, the numpy fallback must replicate the filter in Python to preserve parity. Acceptable for ingest-side analytics; risky on the parity-critical live path. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Mem0 / Letta / Zep / Cognee** (any managed memory framework) | LOCKED rejection. Mem0 audit: ~97.8% junk + hard `openai` dependency (would re-introduce a forbidden provider). All add LLM-extraction layers (= confabulation surface = anti-slop violation) and a server/runtime that breaks one-click install. | `sqlite-vec` + the ~50-line `SessionMemory` wrapper. |
| **An LLM-extraction step between session and embedding** | LOCKED. "Summarize this session into facts" is exactly the hallucination surface the anti-slop thesis forbids. Raw events/transcripts/metadata embed directly. | Embed the raw typed record text (or audio Part) as-is. The `+raw` auxiliary column stores it verbatim for citation. |
| **CLAP / LAION-CLAP / MERT / OpenL3 / sentence-transformers / torch** | LOCKED Gemini-only rule. Any of these pulls torch (~2 GB), murders the install budget, and violates the single-provider thesis. | `gemini-embedding-2` multimodal embeddings via google-genai. |
| **A raw embedded API key in the binary** | LOCKED security model. | Bravoh proxy with per-client rate limit — reuse `build_proxy_genai_client`; the embed module *cannot* read an AIza var directly by design. |
| **vec0 native KNN as the v1 default ranker** | Diverges on tied similarities across Mac (sqlite-vec) vs Win-ARM64 (numpy fallback) → breaks the parity gate (Pitfall P55). | `cosine_topk()` on numpy arrays (storage-only pattern), exactly as the library index does. |
| **A separate JSON sidecar for record metadata** | Unnecessary — `vec0` stores typed metadata columns + `+`-prefixed auxiliary text columns in the same row. | Put `session_id` / `event_type` / `ts` as metadata columns and `+raw` as an auxiliary column. |
| **Bumping numpy/scipy/sqlite3 for this feature** | No memory-layer requirement needs it; bumps risk the locked library-parity tests. | Keep `numpy 2.4.4` / `scipy 1.17.1` / pinned `sqlite-vec 0.1.9`. |
| **sqlite-vec `0.1.10aN` pre-releases** | 0.1.10 is alpha-only (a1–a4, latest a4 2026-05-18); 0.1.9 is the stable line. | Stay on the pinned stable `0.1.9` that already cleared the install chain. |

---

## Stack Patterns by Variant

**If a memory record is structured/text (TRACK_CHANGE, MIX_MOVE, transcript line, track metadata):**
- Embed via `embed_content(contents="<raw record string>", config=output_dimensionality=768)`.
- Cheapest path ($0.20/1M tok), no ffmpeg, no 180 s cap concern. **Recommend this as the v1 default record type.**

**If a memory record is raw audio (a 30 s phrase window, a transition moment):**
- Embed via an audio `Part`; if the clip is >180 s, reuse `LibraryEmbedder`'s 3-excerpt-mean ffmpeg path. Costs $6.50/1M audio tokens.
- Gate behind the acid test ("does retrieving this close a hallucination class or unlock a copilot move?") before adding — audio records are the expensive, dependency-heavy path.

**If running on Windows ARM64 (no sqlite-vec wheel):**
- `open_store()`/the memory equivalent catches the `sqlite_vec.load()` failure → `NumpyStore`-style backend. The `cosine_topk` ranking is identical, so retrieval results are bit-for-bit the same as Mac. No code-path special-casing in the coach grounding seam.

**If the live coach path needs sub-budget retrieval latency:**
- Storage-only load + numpy `cosine_topk` is O(N·D); at one DJ's session-history scale (thousands of records × 768 dims) this is sub-millisecond. Only if N explodes, consider native `vec0` KNN with the parity caveat — but profile first.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `sqlite-vec 0.1.9` | CPython 3.12, stdlib `sqlite3` (libsqlite 3.50.4) | `py3-none-` ABI-stable wheels; loads via `enable_load_extension`. Mac arm64/x86_64 + win_amd64 + manylinux wheels exist. **No win_arm64 wheel** → numpy fallback required (already built). |
| `google-genai 2.0.1` (installed) | `gemini-embedding-2` / `-001` `embed_content` + `EmbedContentConfig(output_dimensionality=...)` + `Part.from_bytes` | Current call shape works as-is (already used in `library/embed.py`). Latest SDK is `2.5.0`; **bumping is optional and out of scope for the memory feature** — if done, run it as a separate hermetic `uv lock` regen + re-run the library parity tests, since the SDK is shared with the live coach path. |
| `gemini-embedding-2` (multimodal) | `output_dimensionality=768` | Auto-normalizes truncated dims (no manual L2 needed for the model output) — but keep the explicit `l2_normalize()` in the wrapper anyway for parity with the library store and to be model-swap-safe (001 does *not* auto-normalize). |
| `numpy 2.4.4` / `scipy 1.17.1` | `cosine_topk`, `l2_normalize`, audio resample | Already the locked library-subsystem versions. Do not bump for this feature. |

---

## Sources

- `pyproject.toml:118` — `sqlite-vec>=0.1.9` already declared (architectural slot from v2.0, exercised v2.1); `google-genai>=2.0.1`, `numpy>=2.4.4`, `scipy>=1.17.1` already core — **HIGH** (repo ground truth)
- `src/vibemix/library/{index_sqlite_vec,embed,_cosine,store}.py` — shipped sqlite-vec + Gemini Embedding 2 + cosine_topk subsystem; the reuse target — **HIGH** (repo ground truth)
- `src/vibemix/llm/_router_config.py` — `embedding` route + `EMBEDDING_GA_CANDIDATES` + `ServiceTier.FLEX` — **HIGH** (repo ground truth)
- Live dev-box probe: `sqlite_vec 0.1.9`, `vec_version()='v0.1.9'`, `vec0.dylib` Mach-O arm64 162 KB, `google-genai 2.0.1`, `sqlite3 3.50.4` — **HIGH** (executed)
- PyPI `sqlite-vec/json` (verified 2026-05-22): latest stable 0.1.9; wheels = macosx arm64/x86_64, win_amd64, manylinux x86_64/aarch64; **no win_arm64**; 0.1.10 alpha-only — **HIGH**
- PyPI `google-genai/json`: latest 2.5.0 (installed 2.0.1) — **HIGH**
- Context7 `/asg017/sqlite-vec` — `vec0` schema (metadata + partition-key + `+`auxiliary columns), `distance_metric=cosine`, `MATCH ... AND k =` / `ORDER BY distance LIMIT` KNN syntax, `sqlite_vec.load()` + `serialize_float32` Python path — **HIGH**
- [Gemini API — Embeddings](https://ai.google.dev/gemini-api/docs/embeddings) — `gemini-embedding-2` multimodal vs `gemini-embedding-001` text-only; native 3072-dim; MRL 128–3072; 180 s audio cap; `embed_content` text + audio-`Part` shape; gemini-embedding-2 auto-normalizes truncated dims — **HIGH**
- [Building with Gemini Embedding 2](https://developers.googleblog.com/building-with-gemini-embedding-2/) — per-call limits (8,192 text tok / 6 img / 120 s video / 180 s audio / 6 PDF); recommends 768/1536; Batch API = 50% price — **HIGH**
- [Gemini API — Pricing](https://ai.google.dev/gemini-api/docs/pricing) — embedding-2 paid $0.20/1M text · $6.50/1M audio · $12/1M video; embedding-001 $0.15/1M; free tier free — **MEDIUM** (preview pricing may shift)
- [Gemini API — Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) + 2026 tier guides — embeddings free ≈100 RPM/1,000 RPD; paid Tier 1 ≈150–300 RPM — **MEDIUM** (single-vendor-doc + secondary aggregators; bind the proxy key, not end-users)

---
*Stack research for: v6.0 "The Memory Turn" — session-memory / embedding-retrieval layer*
*Researched: 2026-05-22*
