# Phase 28: Library Intelligence v1 — Research

**Researched:** 2026-05-15
**Domain:** Multimodal audio embedding + local vector index + Tauri drag-drop UX + IPC schema extension
**Confidence:** HIGH (model API + sqlite-vec + Tauri seam all CITED), MEDIUM (Mac/Win parity test design + 24h cache key strategy — ASSUMED)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All implementation choices at Claude's discretion under `gsd-autonomous fully` mode, grounded in:

- ROADMAP Phase 28 success criteria
- REQUIREMENTS.md LIBRARY-10..17 + LIBRARY-05
- Pitfalls P48 (orphan), P54 (180s cap), P55 (Mac/Win divergence), P56 (cost runaway)
- v2.0 Phase 25 register_library slot + Rekordbox parser (already shipped)
- Memory `project_gemini_embedding_2` — Gemini Embedding 2 is THE embedding for vibemix
- Memory `feedback_no_clap_use_gemini_embedding` — no alt providers

**Embedding model:** `gemini-embedding-2` via `google-genai>=2.0.1` `client.models.embed_content`. Output dim = 768 (CONTEXT D-cost-balanced — 3072 is 4× storage). Audio cap = 180s hard limit, 3-excerpt averaging for longer tracks (intro 0–60s + mid 60–120s + outro -60s..end).

**Storage backend:**
- macOS primary: `sqlite-vec==0.1.9` (`~/.cache/vibemix/library.db`)
- Windows fallback: pure-numpy float32 matrix (`library_vectors.npy` + `library_ids.json`)
- Both backends MUST yield bit-identical top-K — shared `cosine_topk(query, vectors, k)` + stable argsort + secondary sort by `track_id ASC`.

**Content-hash dedupe:** track-key = `sha256(file_bytes_or_id + model_id + excerpt_strategy_version)`. Hit → skip embed call. 24h query-text cache for vibe-search: `sha256(query_text + library_snapshot_hash)`.

**"What's playing" grounding:** 3 excerpts/min sampled (NOT continuous), cosine top-K against library. Citation `[track:<id>]` emitted only when ≥ 0.7. 0.6–0.7 = "uncertain", no citation. Flows as audio Part anchor + text reference into Gemini prompt (memory `feedback_mic_audio_as_multimodal_part`).

**Vibe-search:** `vibemix library search "<NL query>"` → JSON top-K `{track_id, title, artist, bpm, confidence, snippet}`. CLI + IPC `ipc.library.search_result`. 24h cache.

**Drag-drop UX:** Tauri Settings → Library tab. React-ish vanilla TS component (project convention: vanilla TS in `tauri/ui/src/`, NOT React — verified `SettingsDrawer.ts`). Drag target + file-picker fallback. Import progress via `ipc.library.import_progress {total, done, current_track_name}`. Cancel button → `cancel_flag` consumed by importer worker.

**Staleness nudge (LIBRARY-15):** poll `library_import_timestamp` > 30 days → `ipc.library.staleness_nudge` → UI banner. Snooze 7d on dismiss; persistent in `~/.config/vibemix/state.json`.

**Track-to-track similarity (LIBRARY-14):** USER-ASKED only. CLI: `vibemix library similar <track_id>`. IPC: `ipc.library.similar_request` → `ipc.library.similar_result`. UI does NOT autosurface — only on explicit ask. Anti-feature watch.

**IPC schemas (LIBRARY-17):** 4 new schemas on existing ws_bus port 8765 (NOT a new port). `schema_version: "1"` field at top level. Definitions added to `tauri/ui/src/ipc/messages.schema.json` `oneOf` + per-message dataclass in `src/vibemix/ui_bus/schemas/library.py` (matches existing `citation.py` / `debrief.py` / `overlay.py` pattern).

**Visual direction:** CDJ Whisper — `mocks/vibemix-direction-final.html`. Import progress bar: thin 2px line, amber-1 background → amber-3 fill, no gradient flash. Match confidence: text-only badge "0.83" (no bar).

### Claude's Discretion

- 768-dim chosen over 3072 for cost + storage (∼4× win, MRL-validated). Phase-28 plan reserves `EMBEDDING_DIM` env override if benchmark shows recall loss.
- Excerpt averaging: per-track stored vector = `np.mean(stack, axis=0)` (3 excerpts → 1 stored row); per-excerpt vectors NOT separately persisted in v1. (Pitfall P54 mitigation note suggests "OR keep separate for 'find tracks that drop like this drop'" — deferred to v2.2.)
- Mid-excerpt = literal `track_duration / 2 ± 30s` (NOT RMS-peak detection — librosa peak adds CPU cost; mid-track is empirically the drop on most DJ tracks).
- BYO-key soft cap at 100 vibe-searches/day deferred — not needed for v1 (single-user local app, not multi-tenant SaaS).

### Deferred Ideas (OUT OF SCOPE)

- CLAP / LAION-CLAP / MERT / OpenL3 — memory-locked NO
- Audio fingerprinting (acoustid-style) — v2.2
- Bravoh-side embedding service — v2.2
- Stems separation — v2.2
- Track segment retrieval (within-track search) — v2.2
- Multi-user library merging/sharing — never
- Spotify / Apple Music API — never
- Per-excerpt separate persistence — v2.2
- Faiss / Qdrant / Chroma / Weaviate — server-bound, violates one-click-install
- BYO-key gate at 100 vibe-searches/day — single-user app, deferred
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIBRARY-10 | Gemini Embedding 2 client wrapper — `src/vibemix/library/embed.py` using `google-genai` 2.0.1 native `embed_content`. Caches embeddings keyed by track-hash + model-id (Pitfall P56). | [CITED: ai.google.dev/gemini-api/docs/models/gemini-embedding-2] — model ID `gemini-embedding-2`, `client.models.embed_content`, `types.EmbedContentConfig(output_dimensionality=768)`. SDK example uses `types.Part.from_bytes(data=audio_bytes, mime_type='audio/mpeg')`. |
| LIBRARY-11 | sqlite-vec index (Mac) + numpy fallback (Win); identical cosine + stable argsort + float32 (P55). | [CITED: alexgarcia.xyz/sqlite-vec/python.html] — `pip install sqlite-vec`, `sqlite_vec.load(db)`, `vec0` virtual table with `distance_metric=cosine`. [CITED: knn.html] — `MATCH :query and k = 10` syntax. |
| LIBRARY-12 | Vibe-search query interface — NL English → top-K with confidence. | [CITED: ai.google.dev] — text-only path also via `embed_content(contents="query string")`. |
| LIBRARY-13 | "What's playing" grounding — 3-excerpt strategy, citation at ≥ 0.7 (P54). | [CITED: ai.google.dev] — 180s hard cap, MP3/WAV. Memory `project_gemini_embedding_2`. |
| LIBRARY-14 | Track-to-track similarity — USER-ASKED only, anti-feature watch. | [ASSUMED] design pattern — surfaces only via explicit CLI/IPC command, not auto-emitted. |
| LIBRARY-05 | Drag-drop + file-picker UX in Settings → Library tab. | [CITED: tauri-apps/tauri discussions/4736 + Issue #14134] — Tauri v2 uses `tauri://drag-drop` event; `webview.onDragDropEvent()` API; `dragDropEnabled: true` is v2 default. Bug: events can fire twice — must dedupe by event ID. |
| LIBRARY-15 | 30-day staleness nudge UI prompt. | [VERIFIED: `src/vibemix/library/rekordbox.py:171-181`] — log-only nudge already shipped v2.0; Phase 28 surfaces it via IPC. |
| LIBRARY-16 | Embedding cost projection — 24h query cache + budget ≤ €50/month (P56). | [CITED: aicostcheck.com + tokencost.app 2026] — `$0.20/1M text tokens`, `$6.50/1M audio tokens`. 8192-token context. |
| LIBRARY-17 | 4 new IPC schemas on ws_bus port 8765 — `ipc.library.import_progress`, `ipc.library.search_result`, `ipc.library.confidence`, `ipc.library.staleness_nudge`. | [VERIFIED: `tauri/ui/src/ipc/messages.schema.json`] — Draft-07 schema with `oneOf` + per-payload `additionalProperties: false`; mirrored in `src/vibemix/ui_bus/schemas/*.py` dataclasses. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **GSD Workflow Enforcement:** before any Edit/Write, work must go through a GSD command. Phase 28 = `/gsd-execute-phase`.
- **Anti-slop bar:** "real DJ friend in your ear" — verification phase blocks release if reactions feel scripted/late/hallucinated. Citation gate (≥ 0.7) is the grounding contract.
- **POC files untouched:** `cohost*.py` + `mascot.html` are reference IP — `test_g5_poc_files_untouched.py` (extended in Phase 37 AUDIT-07) blocks edits. Phase 28 does NOT touch cohost variants.
- **Frontend-enforcement skill:** loaded automatically when touching `tauri/ui/`. CDJ Whisper visual direction is the bar.
- **Privacy rule:** NEVER read OZ/Hermes log paths (`~/hermes-rig/**`, `~/.hermes/sessions/**`, `~/.lmstudio/**`). Phase 28 does not touch these.
- **Bundle ≤ 350 MB / mascot ≤ 25 MB sub-budget:** sqlite-vec dylib is +600 KB; well under cap.
- **AIza-leak gate:** any new bundled asset (embedding caches, fixtures) must re-scan 0/N matches.
- **Vanilla TS, NOT React:** `tauri/ui/src/` is plain TypeScript. The CONTEXT mentions "React component" — incorrect terminology; verified `tauri/ui/src/settings/SettingsDrawer.ts` is vanilla TS class. Phase 28 plan must say "vanilla TS class" not "React component".

## Summary

Phase 28 is a three-seam build:

1. **Sidecar embedding pipeline** (`src/vibemix/library/{embed,index_sqlite_vec,index_numpy,store,search,staleness}.py`) — Gemini Embedding 2 SDK call → content-hash cache → backend-agnostic LibraryStore facade.
2. **IPC extension** (`src/vibemix/ui_bus/schemas/library.py` + 4 new entries in `tauri/ui/src/ipc/messages.schema.json` `oneOf`) — piggybacks on existing `ws_bus.py` port 8765, runs through the existing jsonschema Draft-07 validator pipeline.
3. **Renderer Settings → Library tab** (`tauri/ui/src/settings/components/library-panel.ts` vanilla-TS class) — drag-drop + file-picker + import-progress chip + staleness banner + amber accent.

The model API surface is **CITED HIGH** — `gemini-embedding-2` is the GA model ID (preview ID `gemini-embedding-2-preview` co-exists), 180s audio cap is documented, 768/1536/3072 MRL truncation is supported, audio via `types.Part.from_bytes`. The storage path is **CITED HIGH** — `sqlite-vec 0.1.9` ships Apache-2.0/MIT, `vec0` virtual table supports `distance_metric=cosine`, `MATCH :query and k = N` is the canonical KNN syntax.

The cross-platform parity contract (Pitfall P55) is **MEDIUM-confidence** — both backends use float32 + cosine, but exact bit-identity requires care: sqlite-vec uses its internal cosine path, numpy uses `np.dot(...) / (norm × norm)`. The fix is to use a **single shared Python function `cosine_topk()`** on both platforms, with sqlite-vec serving only as the *storage layer* in v1 (NOT the search layer). The Mac path queries via `SELECT vector FROM vec_library` into Python, then runs identical cosine math. This trades sqlite-vec's KNN speed for guaranteed parity — acceptable at personal-library scale (≤50k tracks × 768 dim × 4 bytes = ≤150 MB, brute-force ~10–50 ms).

**Primary recommendation:** Use sqlite-vec as the **persistence backend only** (write vectors as float32 blobs via vec0 virtual table for fast disk I/O + future-proofing); keep top-K math in Python so Mac and Win run literally identical code. This sidesteps P55 entirely and keeps the budget test reproducible.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gemini Embedding 2 SDK calls (audio + text) | Python sidecar | — | All AI calls flow through `google-genai` SDK on sidecar; renderer never sees Gemini directly (proxy-only path memory `project_one_click_install_hard_req`). |
| Embedding cache + content-hash dedupe | Python sidecar | — | Pure-Python on-disk SQLite — no cross-tier concerns. |
| sqlite-vec persistence | Python sidecar | — | Database stays on sidecar; renderer never touches `library.db`. |
| Top-K cosine math + tie-break | Python sidecar | — | Single source of truth; identical code Mac + Win. |
| Vibe-search NL query embedding | Python sidecar | — | Same Gemini Embedding 2 path. |
| Drag-drop file capture | Tauri webview (renderer) | Python sidecar (importer worker) | Webview captures `tauri://drag-drop` event → fires `ipc.library.import` over ws_bus → sidecar parses XML + embeds. |
| Import progress UI | Tauri webview (renderer) | Python sidecar (emits `ipc.library.import_progress` ticks) | Renderer subscribes to ws_bus stream; sidecar emits @ 1-tick-per-batch. |
| Citation rendering | Python sidecar (Gemini prompt builder + linter) | Tauri webview (Diagnostics drawer) | `[track:<id>]` ID resolution via `EvidenceRegistry` happens sidecar-side; renderer shows the linter pass/fail diagnostics. |
| Staleness banner | Tauri webview (renderer) | Python sidecar (boot-time poll) | Sidecar checks library mtime at boot → emits `ipc.library.staleness_nudge`; webview renders banner. |
| Track similarity (USER-ASKED) | Python sidecar | Tauri webview (renderer triggers via CLI-like IPC) | UI surfaces explicit "find similar" button only on selected track — NEVER autosurfaces. |

## Standard Stack

### Core (already locked in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | `>=2.0.1` (locked) | Gemini Embedding 2 client | [CITED: ai.google.dev] — the official Google Python SDK; `client.models.embed_content` is the documented call surface. SDK ≥ 1.73.0 required for latest embedding behavior — 2.0.1 satisfies. |
| `sqlite-vec` | `==0.1.9` (locked STATE.md) | Vector storage on disk | [CITED: PyPI / alexgarcia.xyz] — released 2026-03-31; Apache-2.0/MIT dual; ~600 KB dylib on Mac, ~400 KB DLL on Win. Architectural slot reserved in v2.0 pyproject. |
| `numpy` | `>=2.4.4` (locked) | Cosine math + array ops | [VERIFIED: pyproject.toml] — already shipped; `np.dot` / `np.argpartition` / `np.argsort(kind='stable')`. |
| `pyrekordbox` | `==0.4.4` (locked) | Rekordbox XML parser | [VERIFIED: `src/vibemix/library/rekordbox.py`] — already shipped Phase 25; Phase 28 only *consumes* its output. |
| `jsonschema` | `>=4.23,<5` (locked) | IPC payload validation | [VERIFIED: `src/vibemix/ui_bus/messages.py:30,53`] — Draft-07 validator already wired. |
| `websockets` | `>=11` (locked) | ws_bus transport | [VERIFIED: `src/vibemix/runtime/ws_bus.py`] — port 8765 already live. |
| `hashlib` (stdlib) | — | SHA256 content hashing | stdlib; no install. |

### Supporting (new for Phase 28)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **No new runtime deps** | — | — | All Phase 28 functionality fits within the locked v2.1 stack. Dev-only: optional `pydantic-to-typescript` rejected — vibemix uses dataclasses + jsonschema, not pydantic (per `src/vibemix/ui_bus/messages.py:8-13` project convention; **TS types are generated by `npm run check:ipc` codegen from `messages.schema.json`**, not from pydantic). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `gemini-embedding-2` 768-dim | 3072-dim default | 4× storage cost (3072 × 4 bytes × 50k tracks = 600 MB vs 150 MB); MRL-truncation to 768 is documented + recommended; recall loss is small (per Google blog). |
| sqlite-vec KNN (vec0 `MATCH`) | Brute-force Python cosine on raw float32 blobs | sqlite-vec KNN is faster (~5× at 50k rows) but P55 mandates Mac/Win bit-identity. Using sqlite-vec ONLY as blob storage + brute-force Python on both backends → guaranteed parity at ≤ 50 ms/query (acceptable for personal libraries). |
| Audio-only embedding | Text-title + audio-excerpt cross-modal embedding | Text-only is fast (no audio I/O) but loses "tracks that *sound* like this" semantic; audio-only handles unknown titles. v1: **audio when local file available, text fallback for streaming-only entries**. |
| Per-excerpt persistence (3 vectors/track) | Averaged 1-vector/track | Per-excerpt enables "tracks that drop like this drop" but 3× storage + 3× query cost. v1 = average; v2.2 stretch = per-excerpt. |

**Installation:** No new packages — everything is already in `pyproject.toml`. Verify at plan-time:
```bash
python -c "import google.genai, sqlite_vec, numpy, jsonschema, websockets; print('ok')"
```

**Version verification (run at plan-start):**
```bash
pip show google-genai sqlite-vec | grep -E "Name|Version"
```

## Architecture Patterns

### System Architecture Diagram

```
                ┌─────────────────────────────────────────┐
                │  Tauri Webview (renderer)               │
                │  tauri/ui/src/settings/components/      │
                │                                          │
                │  library-panel.ts                       │
                │   ├─ drag target (tauri://drag-drop)   │
                │   ├─ file-picker fallback              │
                │   ├─ progress bar (amber-1→amber-3)    │
                │   ├─ staleness banner (snooze 7d)      │
                │   └─ "Find similar" button (per-track) │
                └────────────┬────────────────────────────┘
                             │  ws://127.0.0.1:8765
                             │  (existing ws_bus)
                             │
                             │  4 new schemas in messages.schema.json oneOf:
                             │  - ipc.library.import_progress  (sidecar → shell)
                             │  - ipc.library.search_result    (sidecar → shell)
                             │  - ipc.library.confidence       (sidecar → shell)
                             │  - ipc.library.staleness_nudge  (sidecar → shell)
                             │  (+ inbound: ipc.library.import / search / similar_request)
                             ▼
                ┌─────────────────────────────────────────┐
                │  Python sidecar (existing src/vibemix/) │
                │                                          │
                │  runtime/ws_bus.py                       │
                │   └─ handler() dispatch to library/      │
                │                                          │
                │  library/                                │
                │   ├─ rekordbox.py  (shipped v2.0)       │
                │   │   └─ RekordboxLibrary.load_xml()    │
                │   │       → ~/.cache/vibemix/library.pkl│
                │   │                                      │
                │   ├─ embed.py    NEW                    │
                │   │   ├─ LibraryEmbedder                │
                │   │   ├─ embed_track(track) → vec[768]  │
                │   │   │   ├─ audio file? → 3-excerpt    │
                │   │   │   │   (intro 0-60 + mid + outro)│
                │   │   │   │   → average → 768-dim       │
                │   │   │   ├─ no audio? → text-only      │
                │   │   │   │   (title + artist + bpm)   │
                │   │   │   └─ content-hash cache hit?    │
                │   │   │       → skip API call          │
                │   │   └─ embed_query(text) → vec[768]   │
                │   │       └─ sha256(query) cache 24h    │
                │   │                                      │
                │   ├─ index_sqlite_vec.py  NEW           │
                │   │   ├─ vec0 virtual table             │
                │   │   ├─ distance_metric=cosine         │
                │   │   └─ float32 blob storage           │
                │   │                                      │
                │   ├─ index_numpy.py  NEW                │
                │   │   ├─ load → (N, 768) ndarray       │
                │   │   └─ float32 enforced              │
                │   │                                      │
                │   ├─ store.py  NEW                      │
                │   │   ├─ LibraryStore facade            │
                │   │   ├─ cosine_topk(query, k=10)       │
                │   │   │   = np.dot + stable argsort     │
                │   │   │     + secondary track_id ASC    │
                │   │   ├─ add_batch(track_id, vector)    │
                │   │   └─ save() / load()                │
                │   │                                      │
                │   ├─ search.py  NEW                     │
                │   │   └─ vibe_search(query, k) → list   │
                │   │                                      │
                │   ├─ grounding.py  NEW                  │
                │   │   └─ identify_playing(audio_ms)     │
                │   │       → top-K, citation if ≥ 0.7    │
                │   │                                      │
                │   ├─ staleness.py  NEW                  │
                │   │   └─ is_stale(threshold=30d)        │
                │   │                                      │
                │   └─ budget.py  NEW                     │
                │       ├─ cost projection table          │
                │       └─ assert ≤ €50/month             │
                │                                          │
                │  state/evidence_registry.py             │
                │   └─ register_library() (shipped v2.0,  │
                │      wired Phase 27 — verified)         │
                │                                          │
                │  __main__.py:672-682                    │
                │   └─ Phase 27-05 wiring (verified)      │
                └────────────┬────────────────────────────┘
                             │
                             │  Outbound HTTPS to Bravoh proxy:
                             │  POST /v1beta/models/gemini-embedding-2:embedContent
                             ▼
                ┌─────────────────────────────────────────┐
                │  Bravoh proxy (api.altidus.world)       │
                │  Per-client rate limit + AIza-key hide  │
                └─────────────────────────────────────────┘
```

### Recommended Project Structure

```
src/vibemix/library/
├── __init__.py              # re-export public API
├── rekordbox.py             # (shipped v2.0 — DO NOT TOUCH)
├── embed.py                 # NEW — LibraryEmbedder + content-hash cache
├── store.py                 # NEW — LibraryStore facade (picks backend)
├── index_sqlite_vec.py      # NEW — sqlite-vec persistence (Mac primary)
├── index_numpy.py           # NEW — pure-numpy persistence (Win fallback)
├── search.py                # NEW — vibe_search(query, k)
├── grounding.py             # NEW — identify_playing(audio_ms) → citation
├── staleness.py             # NEW — is_stale(threshold_days=30)
├── budget.py                # NEW — cost projection + telemetry
└── _cosine.py               # NEW — cosine_topk(query, vectors, k) shared math

src/vibemix/ui_bus/schemas/
└── library.py               # NEW — 4 payload dataclasses

tauri/ui/src/ipc/
└── messages.schema.json     # EXTEND oneOf with 4 new entries

tauri/ui/src/settings/components/
└── library-panel.ts         # NEW — vanilla-TS class (NOT React)

tests/library/               # already exists from Phase 25
├── test_rekordbox.py        # (shipped v2.0)
├── test_embed.py            # NEW — content-hash + cache + 3-excerpt
├── test_store_parity.py     # NEW — Mac vs Win top-K bit-identity
├── test_grounding.py        # NEW — citation gate at 0.7
├── test_search.py           # NEW — vibe-search + 24h cache
├── test_staleness.py        # NEW — 30-day boundary
├── test_budget.py           # NEW — ≤ €50/month assertion
└── fixtures/
    ├── synthetic_collection.xml   # (shipped v2.0)
    ├── synthetic_embeddings.npy   # NEW — 1000-vec parity corpus
    └── synthetic_queries.json     # NEW — 50 query embeddings
```

### Pattern 1: 3-excerpt Embedding (Pitfall P54 mitigation)

**What:** Tracks longer than 180s are sliced into intro (0–60s) + middle (duration/2 ± 30s) + outro (-60..end), each embedded separately, then averaged into a single 768-dim vector.

**When to use:** Any `TrackEntry.duration_s > 180`. Tracks ≤ 180s are embedded as a single call.

**Example:**
```python
# Source: ai.google.dev/gemini-api/docs/embeddings + Pitfall P54
# src/vibemix/library/embed.py
import numpy as np
from google import genai
from google.genai import types

def _excerpts(audio_path: Path, duration_s: float) -> list[bytes]:
    """Returns [intro_60s, mid_60s, outro_60s] as MP3 bytes."""
    if duration_s <= 180:
        return [audio_path.read_bytes()]  # single call path
    # ffmpeg-extracted excerpts (cached on disk by content-hash)
    return [
        _extract_mp3(audio_path, start=0, dur=60),
        _extract_mp3(audio_path, start=duration_s/2 - 30, dur=60),
        _extract_mp3(audio_path, start=max(0, duration_s-60), dur=60),
    ]

def embed_track(client: genai.Client, audio_path: Path, duration_s: float) -> np.ndarray:
    parts = [
        types.Part.from_bytes(data=clip, mime_type='audio/mpeg')
        for clip in _excerpts(audio_path, duration_s)
    ]
    vectors: list[np.ndarray] = []
    for part in parts:
        result = client.models.embed_content(
            model='gemini-embedding-2',
            contents=[part],
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
        vec = np.asarray(result.embeddings[0].values, dtype=np.float32)
        vectors.append(vec)
    return np.mean(np.stack(vectors), axis=0).astype(np.float32)
```

### Pattern 2: Identical Cosine Top-K Across Backends (Pitfall P55 mitigation)

**What:** Both Mac (sqlite-vec persistence) and Win (numpy persistence) call the SAME Python function for top-K math. sqlite-vec is used purely as a storage layer in v1.

**When to use:** Every search call (vibe-search, grounding, similar-track).

**Example:**
```python
# Source: alexgarcia.xyz/sqlite-vec/benchmarks (argpartition pattern) + P55
# src/vibemix/library/_cosine.py
import numpy as np

def cosine_topk(
    query: np.ndarray,        # shape (768,), float32, L2-normalized
    vectors: np.ndarray,      # shape (N, 768), float32, L2-normalized
    track_ids: list[str],     # length N
    k: int = 10,
) -> list[tuple[str, float]]:
    """Returns top-K (track_id, similarity) sorted DESC by similarity,
    then ASC by track_id for stable tie-break across platforms."""
    assert query.dtype == np.float32, "query must be float32"
    assert vectors.dtype == np.float32, "vectors must be float32"
    sims = vectors @ query                                # (N,) dot product
    # argpartition for O(N + k log k); then stable sort within top-K
    if len(sims) <= k:
        top_idx = np.arange(len(sims))
    else:
        top_idx = np.argpartition(-sims, k)[:k]
    # Two-key stable sort: primary = -similarity DESC, secondary = track_id ASC
    pairs = [(track_ids[i], float(sims[i]), i) for i in top_idx]
    pairs.sort(key=lambda p: (-p[1], p[0]))                # bit-identical Mac+Win
    return [(tid, sim) for tid, sim, _ in pairs[:k]]
```

**Note on `np.argpartition` determinism:** `argpartition` is not stable, but we re-sort the K-element partition explicitly with Python's `sort(key=...)` (stable, deterministic, Timsort), so ties are broken by `track_id` ASC. Bit-identical Mac/Win/Linux output is the guarantee.

### Pattern 3: Content-Hash Embedding Cache (Pitfall P56 mitigation)

**What:** Every embedding is keyed by `sha256(file_bytes + model_id + excerpt_version)`. Re-import of the same XML → 0 API calls. Same library on two installs → second install pays 0 (if files are byte-identical).

**When to use:** Every `embed_track()` call.

**Example:**
```python
# Source: Pitfall P56 + Memory project_gemini_embedding_2
# src/vibemix/library/embed.py
import hashlib
import sqlite3

EXCERPT_STRATEGY_VERSION = "v1-3excerpt-mean"

def _track_hash(audio_path: Path, model_id: str) -> str:
    """SHA256 of (file_bytes || model_id || excerpt_strategy_version).
    Streaming-only entries (no local file) use track_id as proxy hash."""
    h = hashlib.sha256()
    if audio_path.exists():
        with open(audio_path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 16), b''):
                h.update(chunk)
    else:
        h.update(b'<no-local-file>')
    h.update(model_id.encode())
    h.update(EXCERPT_STRATEGY_VERSION.encode())
    return h.hexdigest()

def embed_track_cached(self, track: TrackEntry) -> np.ndarray:
    key = _track_hash(Path(track.filepath), 'gemini-embedding-2')
    cached = self.cache_db.execute(
        "SELECT vector FROM embed_cache WHERE key = ?", (key,)
    ).fetchone()
    if cached:
        return np.frombuffer(cached[0], dtype=np.float32)
    vec = embed_track(self.client, Path(track.filepath), track.duration_s)
    self.cache_db.execute(
        "INSERT INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
        (key, vec.tobytes(), time.time()),
    )
    return vec
```

### Pattern 4: 24h Query Cache (Pitfall P56 mitigation)

```python
# src/vibemix/library/search.py
def vibe_search(self, query: str, k: int = 10) -> list[TrackEntry]:
    library_snapshot = self.store.snapshot_hash()  # sha256 of sorted track_ids
    cache_key = hashlib.sha256(
        f"{query}|{library_snapshot}".encode()
    ).hexdigest()
    ttl_24h = 86400
    hit = self.cache_db.execute(
        "SELECT result_json, ts FROM query_cache WHERE key = ?", (cache_key,)
    ).fetchone()
    if hit and (time.time() - hit[1]) < ttl_24h:
        return [TrackEntry.from_dict(d) for d in json.loads(hit[0])]
    qvec = embed_query(query)
    top = self.store.cosine_topk(qvec, k=k)
    self.cache_db.execute(
        "INSERT OR REPLACE INTO query_cache (key, result_json, ts) VALUES (?, ?, ?)",
        (cache_key, json.dumps([t.to_dict() for t in top]), time.time()),
    )
    return top
```

### Pattern 5: Tauri 2 Drag-Drop (LIBRARY-05)

**What:** Webview captures `tauri://drag-drop` event, posts file paths over ws_bus to sidecar.

**When to use:** Settings → Library tab drop zone.

**Example:**
```typescript
// Source: github.com/tauri-apps/tauri discussions/4736 + Issue #14134
// tauri/ui/src/settings/components/library-panel.ts
import { getCurrentWebview } from '@tauri-apps/api/webview';

class LibraryPanel {
  private seenEventIds = new Set<number>();  // dedupe Issue #14134

  async mount() {
    const webview = getCurrentWebview();
    await webview.onDragDropEvent((event) => {
      // Bug: Tauri v2 fires twice with different IDs; dedupe by event.id.
      if (this.seenEventIds.has(event.id)) return;
      this.seenEventIds.add(event.id);

      if (event.payload.type === 'drop') {
        const paths = event.payload.paths;
        const xml = paths.find(p => p.endsWith('.xml'));
        if (xml) this.beginImport(xml);
      }
    });
  }

  private beginImport(path: string) {
    this.wsBus.send({
      type: 'ipc.library.import',
      schema_version: '1',
      path,
      ts: new Date().toISOString(),
    });
  }
}
```

**Tauri config note:** `dragDropEnabled` is `true` by default in Tauri v2; no `tauri.conf.json5` change needed. Verified: no `dragDrop` key in `tauri/src-tauri/tauri.conf.json5`.

### Anti-Patterns to Avoid

- **❌ Continuous embedding of "what's playing" audio.** Pitfall P56 — embeds every 5s in a 1h session = ~720 calls/session × 1000 DAU = budget blown. **✅ Sample 3 excerpts/min (one every 20s, ~180/hr).**
- **❌ Different cosine implementations per backend.** P55 — sqlite-vec `vec_distance_cosine` is fast but differs from `np.dot/norm` in float32 rounding. **✅ Single `cosine_topk()` function; sqlite-vec used only for storage.**
- **❌ Auto-emit "next track" suggestions.** Memory anti-feature watch — slop risk + LIBRARY-14 explicit. **✅ Surface only on user-explicit CLI/IPC ask.**
- **❌ Pydantic anywhere in `src/vibemix/`.** Project convention (`messages.py:8-13`). **✅ Hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07.**
- **❌ React component in `tauri/ui/`.** CLAUDE.md decision lock — vanilla TS. **✅ Vanilla-TS class extending the `SettingsDrawer` registration pattern.**
- **❌ Embedding the full track inline.** 180s cap → silent truncation or cryptic error. **✅ 3-excerpt strategy explicit; ffmpeg-cached excerpts.**
- **❌ Storing track titles in the long-term DJ profile (Phase 32).** Pitfall P51 — profile allowlist forbids it. Phase 28 ships the embeddings + index; profile reads aggregate-only stats.
- **❌ Inventing a new ws_bus port.** STATE.md decision lock — port 8765 stays; everything piggybacks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio embedding | Custom CLAP wrapper / MERT extractor | `google-genai` `embed_content` with `gemini-embedding-2` | Memory-locked; CLAP requires 200 MB+ model bundle. |
| Vector storage | Custom flat-file format | `sqlite-vec 0.1.9` vec0 virtual table | Apache-2.0/MIT, +600 KB, runs everywhere SQLite runs. |
| Cosine math | Reimplemented dot product | `numpy.dot` + `numpy.linalg.norm` | Already shipped, BLAS-accelerated. |
| Top-K | Hand-rolled heap | `np.argpartition` + Python sorted() | argpartition is O(N + k log k); sorted() is stable Timsort for tie-break. |
| Rekordbox XML parse | Custom XML walker | `pyrekordbox==0.4.4` (already shipped) | Phase 25 Plan 25-01 spike-locked. |
| IPC schema validation | Custom validator | `jsonschema.Draft7Validator` (already shipped) | Phase 11 Wave 0 — single source schema at `tauri/ui/src/ipc/messages.schema.json`. |
| File drag-drop in webview | Custom mouse-event listener | Tauri v2 `webview.onDragDropEvent()` | Native OS hooks; both Webview2 + WKWebView. |
| Audio excerpt extraction | Custom WAV slicer | `ffmpeg` subprocess (already on Mac+Win one-click install) | Handles MP3/AAC/FLAC inputs; preserves codec for upload. |
| Content hashing | Custom file-content hasher | `hashlib.sha256` (stdlib) | streaming-safe, cross-platform. |

**Key insight:** Phase 28 introduces ZERO new runtime deps. Every primitive is already in the locked stack.

## Runtime State Inventory

Not a rename/refactor/migration phase — N/A. All new artifacts are additive (new files, new IPC schema entries, new disk paths `~/.cache/vibemix/library.db` and `~/.cache/vibemix/embeddings.db`). No existing keys/IDs/strings being renamed.

## Common Pitfalls

### Pitfall P48: register_library Orphaned Re-Ship (Critical)

**What goes wrong:** Phase 27 wired `register_library` at `__main__.py:672-682`. Phase 28 builds on top — but if any refactor accidentally moves or guards the call site behind a feature flag, the v2.0 orphan re-emerges and `[track:<id>]` citations never resolve.

**Why it happens:** "Test exists for the method" ≠ "method is called in shipping binary path." Easy to satisfy `import register_library` smoke test without ever invoking it.

**How to avoid:**
- `tests/integration/test_library_wired_into_main.py::test_main_calls_register_library_when_library_loaded` — boots `__main__.py` init path with synthetic `library.pkl`, asserts `evidence_registry.register_library` is invoked via mock/spy.
- `tests/integration/test_track_citation_validates_end_to_end.py::test_drag_drop_xml_then_live_track_citation_validates` — full E2E: import XML via drag-drop IPC → fire synthetic track-aware event → assert `[track:<id>]` citation passes linter.
- CI grep gate: `grep -q "evidence_registry.register_library" src/vibemix/__main__.py`.

**Warning signs:** Grep returns 0 matches; integration audit says "defined" without verifying "invoked"; events.jsonl shows no track citations after import.

[VERIFIED: `src/vibemix/__main__.py:672-682` — wiring present + comment "Plan 27-05 final-mile wiring (closes v2.0 register_library orphan, P48)".]

### Pitfall P54: Gemini Embedding 2 180s Audio Cap (High)

**What goes wrong:** Naive `embed(audio_bytes)` call with a 6-min track either rejects with cryptic error OR silently truncates to first 180s (intro-biased embedding) OR returns 4xx the dev swallows.

**How to avoid:**
- 3-excerpt strategy (Pattern 1 above) when `duration_s > 180`.
- Explicit `try/except` on the API call — `"audio too long"` → fall back to excerpt path + log.
- Test fixture: synthetic 8-min track → assert 3 API calls + 1 stored 768-vector.

**Tests:** `test_long_track_split_into_3_excerpts`, `test_audio_cap_error_handled`.

[CITED: ai.google.dev/gemini-api/docs/models/gemini-embedding-2 — "maximum duration of 180 seconds" for audio modality.]

### Pitfall P55: Mac/Win Top-K Divergence (High)

**What goes wrong:** sqlite-vec uses internal cosine math + heap ordering; numpy uses `np.dot/norm` + argsort. At float32 precision, these can produce different rank orders for similarity ties. User on Mac sees track A → friend on Win sees track B for identical query.

**How to avoid (the v1 approach):**
- sqlite-vec is **persistence only** in v1. Top-K math runs in Python on both platforms via shared `cosine_topk()` (Pattern 2 above).
- Float32 enforced via `assert vec.dtype == np.float32`.
- Tie-break: primary = -similarity DESC, secondary = track_id ASC. Python's `sort(key=lambda p: (-p[1], p[0]))` is bit-identical across platforms (Timsort, no float NaN handling differences for finite cosine sims).
- Parity test: `tests/library/test_store_parity.py::test_topk_identical_mac_win` — same fixture corpus + queries → both backends return IDENTICAL ordered lists.

**Tests:** `test_topk_identical_mac_win`, `test_numpy_fallback_uses_stable_argsort`, `test_float32_contract_enforced`.

[CITED: alexgarcia.xyz/sqlite-vec/features/knn.html + benchmark code — argpartition + sort pattern.]

### Pitfall P56: Embedding Cost Runaway (High)

**What goes wrong:** At 100 queries/day × 1000 DAU + per-event grounding (5–10 events/hr) + transition critiques + session retrievals, budget hits $300/month = 6× the €50 cap.

**How to avoid:**
- Per-feature cost projection table (see `## Budget Telemetry` below). Sum must fit ≤ €50/month.
- 24h query cache (Pattern 4): same NL query within 24h → 0 API calls.
- Content-hash embedding cache (Pattern 3): re-import XML → 0 API calls.
- Sampled grounding: 3 excerpts/min, NOT per-event (= 180 calls/hr session vs 720).
- Session retrieval embeddings: computed at session END, cached locally → retrieval is FREE local cosine.
- BYO-key soft cap deferred (single-user local app; not needed for v1 — Bravoh proxy enforces per-client rate-limit).

**Tests:** `test_budget_projection_under_50_euro`, `test_query_cache_24h_ttl`, `test_content_hash_skip_on_reimport`.

[CITED: aicostcheck.com — $0.20/1M text tokens, $6.50/1M audio tokens for `gemini-embedding-2-preview` 2026 pricing.]

### Pitfall: Tauri v2 Drag-Drop Duplicate Events (Medium)

**What goes wrong:** Tauri v2 fires `webview.onDragDropEvent` twice with different event IDs for a single drop (Issue #14134). Naive handler imports the same XML twice → 2× embed cost or worse — duplicate `register_library` registrations.

**How to avoid:** Dedupe by `event.id` in a `Set<number>` (Pattern 5 above). Clear set on component unmount.

**Tests:** `tests/ui/library-panel.spec.ts::test_drop_event_dedupe`.

[CITED: github.com/tauri-apps/tauri/issues/14134.]

### Pitfall: Streaming-Only Tracks (no local file)

**What goes wrong:** Tracks that exist only as nowplaying-cli metadata (Spotify, Apple Music streaming) have no local file → audio embed call fails. If not handled, importer crashes mid-batch.

**How to avoid:** Embedder branches on `Path(track.filepath).exists()`:
- Has file → 3-excerpt audio embed.
- No file → text-only embed via `embed_content(contents=f"{title} by {artist} | {bpm} BPM | key {key}")`.

**Tests:** `test_streaming_track_text_only_path`.

### Pitfall: ffmpeg not available

**What goes wrong:** Excerpt extraction requires `ffmpeg`. If absent, importer fails.

**How to avoid:** `shutil.which("ffmpeg")` check at boot. Phase 33 INSTALL wizard already bundles ffmpeg per CLAUDE.md tech stack. Sidecar fail-loud at import-start, NOT mid-batch.

**Tests:** `test_embed_missing_ffmpeg_fails_loud`.

## Code Examples

### Boot-time staleness check

```python
# Source: src/vibemix/library/rekordbox.py:171-181 + LIBRARY-15
# src/vibemix/library/staleness.py
import os
import time
from pathlib import Path

STALE_AGE_SECONDS = 30 * 86400  # 30 days

def is_stale(library_pkl: Path = None) -> tuple[bool, int]:
    """Returns (stale_flag, age_days). False/0 if no library loaded."""
    library_pkl = library_pkl or Path.home() / ".cache" / "vibemix" / "library.pkl"
    if not library_pkl.exists():
        return False, 0
    try:
        mtime = os.path.getmtime(library_pkl)
    except OSError:
        return False, 0
    age = time.time() - mtime
    return age > STALE_AGE_SECONDS, int(age // 86400)
```

### IPC schema dataclass

```python
# Source: src/vibemix/ui_bus/schemas/citation.py pattern
# src/vibemix/ui_bus/schemas/library.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class LibraryImportProgressPayload:
    """Payload for ipc.library.import_progress (sidecar → shell)."""
    total: int                    # total tracks to embed
    done: int                     # tracks embedded so far
    current_track_name: str       # e.g., "Aphex Twin — Xtal"
    cache_hits: int               # tracks skipped via content-hash
    schema_version: str = "1"

@dataclass(frozen=True, slots=True)
class LibrarySearchResultPayload:
    """Payload for ipc.library.search_result."""
    query: str
    matches: tuple[dict, ...]     # [{track_id, title, artist, bpm, confidence, snippet}, ...]
    cache_hit: bool
    schema_version: str = "1"

@dataclass(frozen=True, slots=True)
class LibraryConfidencePayload:
    """Payload for ipc.library.confidence — citation telemetry diagnostics."""
    track_id: str                 # the cited track
    cosine: float                 # [0.0, 1.0]
    decision: str                 # "cited" | "uncertain" | "below_threshold"
    schema_version: str = "1"

@dataclass(frozen=True, slots=True)
class LibraryStalenessNudgePayload:
    """Payload for ipc.library.staleness_nudge."""
    age_days: int
    snoozed_until_ts: float | None
    schema_version: str = "1"
```

### sqlite-vec persistence layer

```python
# Source: alexgarcia.xyz/sqlite-vec/python.html + features/knn.html
# src/vibemix/library/index_sqlite_vec.py
import sqlite3
import sqlite_vec
import numpy as np
from pathlib import Path

DB_PATH = Path.home() / ".cache" / "vibemix" / "library.db"
EMBEDDING_DIM = 768

class SqliteVecStore:
    def __init__(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(DB_PATH))
        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)
        self.db.enable_load_extension(False)
        self.db.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_library USING vec0("
            f"track_id TEXT PRIMARY KEY, "
            f"embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine"
            f")"
        )

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        for tid, vec in items:
            assert vec.dtype == np.float32 and vec.shape == (EMBEDDING_DIM,)
            self.db.execute(
                "INSERT OR REPLACE INTO vec_library (track_id, embedding) VALUES (?, ?)",
                (tid, vec.tobytes()),
            )
        self.db.commit()

    def load_all(self) -> tuple[list[str], np.ndarray]:
        """Returns (track_ids, vectors_NxD) for in-Python top-K math (P55 parity)."""
        rows = self.db.execute(
            "SELECT track_id, embedding FROM vec_library ORDER BY track_id ASC"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        ids = [r[0] for r in rows]
        mat = np.stack([
            np.frombuffer(r[1], dtype=np.float32) for r in rows
        ])
        return ids, mat
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLAP / LAION-CLAP audio embedding | Gemini Embedding 2 (multimodal single space) | March 2026 (GA) | 200-500 MB model weights replaced by API call; bundle stays under 350 MB cap. |
| Faiss / Qdrant / Chroma vector DBs | sqlite-vec (~600 KB extension) | 2024-2026 (sqlite-vec v0.1.0 stable → 0.1.9 in March 2026) | No new processes, no MKL deps, runs anywhere SQLite runs. |
| Token-based embeddings (text-only) | Native multimodal (audio + text + image in one space) | Gemini Embedding 2 GA | Cross-modal queries like "tracks that sound like this audio clip" work without separate encoders. |
| `task_type` config parameter | Inline task instructions in prompt text | `gemini-embedding-2` (the previous `embedding-001` used task_type) | `task_type` is NOT used with `gemini-embedding-2`. [CITED: ai.google.dev — "you cannot use the `task_type` field for the `gemini-embedding-2` model"]. |

**Deprecated/outdated:**
- `gemini-embedding-001` task_type field — not applicable to v2 model
- `embedding-001` model ID — replaced by `gemini-embedding-2` and `gemini-embedding-2-preview`
- 2048-token context limit — `gemini-embedding-2` extends to 8192 tokens

**CORRECTION to CONTEXT.md:** CONTEXT.md says model ID = `gemini-embedding-001`. **VERIFIED INCORRECT** against [CITED: ai.google.dev/gemini-api/docs/models/gemini-embedding-2]. The actual GA model ID is `gemini-embedding-2`. STACK.md and the Gemini Embedding 2 product page agree. Plan-phase MUST use `gemini-embedding-2` — `embedding-001` is the predecessor (text-only, 768-dim, task_type-required).

## Budget Telemetry

**Cost projection table** (must commit to `.planning/phases/28-library-intelligence-v1/COST-PROJECTION.md` as part of LIBRARY-16):

| Feature | Cost-per-call | Calls per user/month | Monthly cost @1000 DAU | Notes |
|---------|---------------|----------------------|------------------------|-------|
| One-time library indexing (30k tracks × 3 excerpts) | ~$0.0002 × 3 = $0.0006/track | First import only | ~$18 one-time per 1000-track library × 1000 users | Amortized; protected by content-hash cache. |
| Vibe-search NL query | ~$0.0001 (text-only, 50 tokens × $0.20/1M) | 5 queries/day × 30 = 150 | $0.015/user/month × 1000 = $15 | 24h cache cuts to ~$5 effective. |
| "What's playing" grounding (3 excerpts/min sampled) | ~$0.0006 (60s audio × $6.50/1M tokens approximation) | 180 calls/hr × 1hr/day × 30d = 5400 | $3.24/user/month × 1000 = $3240 ❌ | **CRITICAL — this line alone blows budget. Must reduce to 1 excerpt/min OR gate on event-detection.** |
| Track-to-track similarity (USER-ASKED) | ~$0.0006 (audio embed) | ~3 asks/session × 5 sessions = 15/mo | $0.009/user × 1000 = $9 | Cached per track-hash. |
| Session retrieval embedding | ~$0.0006 (one per session-end) | 5 sessions/mo | $0.003/user × 1000 = $3 | Computed once at session-end. |
| **TOTAL @ 1000 DAU (uncached grounding)** | — | — | **~$3285/month = ~3000 €** ❌ | Budget blown 60×. |
| **TOTAL @ 1000 DAU (event-gated grounding, 10/session)** | — | — | **~$60/month = ~55 €** ✅ | Within budget. |

**Critical decision needed in plan-phase:** Grounding sampling rate.

- **Option A (CONTEXT spec, 3/min):** Blows budget at scale. Acceptable only at single-user-Mac scale (~10-20 active users) where €50 is rarely touched.
- **Option B (event-gated, embed only on EvidenceRegistry event fire):** ~10 events/session × 5 sessions/mo = 50 calls/user/month = ~$0.03/user × 1000 = **$30/month ≈ €27**. Within budget. **RECOMMENDED.**
- **Option C (hybrid):** Background sampling at 1/min + event-burst on detection. Compromise. ~60/session = $36/month at 1000 DAU.

**Plan-phase MUST decide** between A/B/C and lock in the budget assertion test. Recommendation: **Option B** (event-gated) for v1; revisit in v2.2 if telemetry shows under-grounding.

**Telemetry surface:**
- CLI: `vibemix library budget` → prints monthly projection + actual call counts.
- IPC: `ipc.library.confidence` payload includes `cosine` per citation; renderer can roll up to "grounding rate" display in Diagnostics drawer.
- CI assertion: `tests/library/test_budget.py::test_monthly_projection_under_50_eur` — runs cost projection function with default config, asserts ≤ €50/month at 1000 DAU.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (verified in `tests/` layout) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (assumed — verify in plan-phase) |
| Quick run command | `pytest tests/library/ -x` |
| Full suite command | `pytest tests/library/ tests/integration/ tests/ipc/` |
| Phase gate | Full suite green before `/gsd-verify-work` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIBRARY-10 | Embedding client wraps Gemini API with content-hash cache | unit | `pytest tests/library/test_embed.py -x` | ❌ Wave 0 |
| LIBRARY-10 | 3-excerpt path triggered when duration > 180s | unit | `pytest tests/library/test_embed.py::test_long_track_split_into_3_excerpts -x` | ❌ Wave 0 |
| LIBRARY-10 | Audio-cap error explicitly caught and falls back | unit | `pytest tests/library/test_embed.py::test_audio_cap_error_handled -x` | ❌ Wave 0 |
| LIBRARY-10 | Streaming-only tracks use text-only path | unit | `pytest tests/library/test_embed.py::test_streaming_track_text_only_path -x` | ❌ Wave 0 |
| LIBRARY-10 | Content-hash cache skips re-embed | unit | `pytest tests/library/test_embed.py::test_content_hash_skip_on_reimport -x` | ❌ Wave 0 |
| LIBRARY-11 | sqlite-vec store on Mac, numpy on Win | unit | `pytest tests/library/test_store.py -x` | ❌ Wave 0 |
| LIBRARY-11 | Mac/Win top-K bit-identical | integration | `pytest tests/library/test_store_parity.py::test_topk_identical_mac_win -x` | ❌ Wave 0 |
| LIBRARY-11 | Float32 contract enforced | unit | `pytest tests/library/test_store_parity.py::test_float32_contract_enforced -x` | ❌ Wave 0 |
| LIBRARY-11 | Stable argsort + secondary track_id ASC | unit | `pytest tests/library/test_store_parity.py::test_tie_break_track_id_asc -x` | ❌ Wave 0 |
| LIBRARY-12 | Vibe-search end-to-end NL → tracks | integration | `pytest tests/library/test_search.py::test_vibe_search_returns_top_k -x` | ❌ Wave 0 |
| LIBRARY-12 | 24h query cache hits | unit | `pytest tests/library/test_search.py::test_query_cache_24h_ttl -x` | ❌ Wave 0 |
| LIBRARY-13 | Citation emitted at ≥ 0.7 | integration | `pytest tests/library/test_grounding.py::test_citation_at_threshold -x` | ❌ Wave 0 |
| LIBRARY-13 | "Uncertain" zone 0.6-0.7 no citation | unit | `pytest tests/library/test_grounding.py::test_uncertain_no_citation -x` | ❌ Wave 0 |
| LIBRARY-13 | Citation flows into Gemini prompt as Part | integration | `pytest tests/library/test_grounding.py::test_citation_to_prompt_part -x` | ❌ Wave 0 |
| LIBRARY-13 + P48 | register_library invoked from __main__ | integration | `pytest tests/integration/test_library_wired_into_main.py -x` | ❌ Wave 0 |
| LIBRARY-13 + P48 | E2E drag-drop XML → live track citation | integration | `pytest tests/integration/test_track_citation_validates_end_to_end.py -x` | ❌ Wave 0 |
| LIBRARY-14 | Similar-track surfaces only on user ask | unit | `pytest tests/library/test_similar.py::test_no_autosurface -x` | ❌ Wave 0 |
| LIBRARY-14 | CLI `vibemix library similar <id>` returns top-K | integration | `pytest tests/scripts/test_cli_similar.py -x` | ❌ Wave 0 |
| LIBRARY-05 | Drag-drop event captured + deduplicated | e2e | `npm run test -- library-panel.spec.ts` | ❌ Wave 0 |
| LIBRARY-05 | File-picker fallback works | e2e | `npm run test -- library-panel.spec.ts::test_file_picker` | ❌ Wave 0 |
| LIBRARY-15 | 30-day staleness boundary | unit | `pytest tests/library/test_staleness.py::test_30_day_boundary -x` | ❌ Wave 0 |
| LIBRARY-15 | Snooze 7d on dismiss | unit | `pytest tests/library/test_staleness.py::test_snooze_persists -x` | ❌ Wave 0 |
| LIBRARY-16 | Budget projection ≤ €50/month at 1000 DAU | unit | `pytest tests/library/test_budget.py::test_monthly_projection_under_50_eur -x` | ❌ Wave 0 |
| LIBRARY-17 | 4 new IPC schemas validate against existing pipeline | unit | `pytest tests/ipc/test_library_schemas.py -x` | ❌ Wave 0 |
| LIBRARY-17 | schema_version="1" on every payload | unit | `pytest tests/ipc/test_library_schemas.py::test_schema_version_field -x` | ❌ Wave 0 |
| LIBRARY-17 | Count parity Python ↔ TS | integration | `python scripts/check_ipc_schema.py && cd tauri/ui && npm run check:ipc` | ✅ scripts exist |

### Sampling Rate

- **Per task commit:** `pytest tests/library/ -x`
- **Per wave merge:** `pytest tests/library/ tests/integration/ tests/ipc/`
- **Phase gate:** Full suite + Mac/Win parity matrix in `.github/workflows/library-parity.yml` (NEW) green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/library/test_embed.py` — covers LIBRARY-10
- [ ] `tests/library/test_store.py` — covers LIBRARY-11
- [ ] `tests/library/test_store_parity.py` — Mac/Win parity, P55
- [ ] `tests/library/test_search.py` — LIBRARY-12 + 24h cache
- [ ] `tests/library/test_grounding.py` — LIBRARY-13 + 0.7 threshold
- [ ] `tests/library/test_similar.py` — LIBRARY-14 anti-feature
- [ ] `tests/library/test_staleness.py` — LIBRARY-15
- [ ] `tests/library/test_budget.py` — LIBRARY-16
- [ ] `tests/integration/test_library_wired_into_main.py` — P48 invocation test
- [ ] `tests/integration/test_track_citation_validates_end_to_end.py` — P48 E2E
- [ ] `tests/ipc/test_library_schemas.py` — LIBRARY-17
- [ ] `tests/ui/library-panel.spec.ts` — LIBRARY-05 drag-drop + file-picker (vitest)
- [ ] `tests/library/fixtures/synthetic_embeddings.npy` — 1000-vec parity corpus
- [ ] `tests/library/fixtures/synthetic_queries.json` — 50 query embeddings
- [ ] `.github/workflows/library-parity.yml` — Mac + Win matrix gate

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Gemini calls flow through Bravoh proxy with proxy-side auth; no user-supplied keys. |
| V3 Session Management | no | Local app, no sessions. |
| V4 Access Control | partial | sqlite-vec DB at `~/.cache/vibemix/library.db` is user-owned; standard POSIX perms 0644 sufficient. Tauri capability allowlist (Phase 34 SEC-09) gates `fs.read` to specific scopes. |
| V5 Input Validation | yes | jsonschema Draft-07 with `additionalProperties: false` on every payload (existing convention). XML parse via pyrekordbox already exception-handled. |
| V6 Cryptography | yes | `hashlib.sha256` for content-hash + query-cache keys; SHA256 is collision-resistant — no rolling-our-own. |

### Known Threat Patterns for vibemix Phase 28

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed Rekordbox XML crashes parser | Denial of Service | pyrekordbox raises; renderer surfaces error toast via `ipc.error`. Test: `tests/library/test_rekordbox.py` (shipped) covers. |
| Embedding cache poisoning (attacker writes bad vector blob) | Tampering | Cache files in user's own `~/.cache/vibemix/` — local trust boundary. SHA256 key collision would be required (computationally infeasible). |
| Path traversal via dropped file path | Tampering | Tauri v2 auto-scopes drag-drop paths to drop-time scope; renderer validates `.xml` extension before forwarding to sidecar. Sidecar uses `Path(...).resolve()` + `.is_file()` check. |
| API key extraction from embedded binary | Information Disclosure | NEVER ship Gemini key — all calls flow through `api.altidus.world` proxy (memory `project_one_click_install_hard_req`). Phase 28 plan must NOT introduce any direct-to-Gemini code path. |
| Cost-amplification attack (attacker tricks app into re-embedding) | DoS / financial | Content-hash dedupe + 24h query cache + Bravoh proxy per-client rate limit (existing Phase 9 surface). |
| PII leak via NL query | Information Disclosure | Vibe-search queries are sent verbatim to Gemini Embedding 2. CLAUDE.md telemetry consent is opt-in default-OFF (Phase 34 SEC-08); users should be aware their query text leaves the machine for embedding. Plan-phase: surface in Settings → Privacy disclosure. |

## Open Questions

> Resolved with grounded recommendations per `gsd-autonomous fully` — each marked `[RESOLVED]` with chosen path.

1. **Grounding sampling rate (3/min vs event-gated) — budget vs coverage tradeoff [RESOLVED]**
   - What we know: 3/min × 1hr × 1000 DAU = $3000+/mo at audio token pricing. Event-gated (~10/session) fits €50.
   - What's unclear: Will event-gated grounding miss enough "what's playing" moments to break the citation gate?
   - **Recommendation:** Option B (event-gated). Embed only on EvidenceRegistry event fire. If telemetry shows under-grounding in v2.2 (citation rate < 0.5 of fired events), revisit. Lock in `tests/library/test_budget.py::test_monthly_projection_under_50_eur` with Option B numbers.

2. **Excerpt averaging vs per-excerpt storage [RESOLVED]**
   - What we know: Average loses the "drop-only" semantic; per-excerpt preserves it at 3× storage.
   - What's unclear: Does the user-facing query "tracks that drop like this" justify 3× storage in v1?
   - **Recommendation:** Average in v1 (150 MB for 50k tracks); per-excerpt deferred to v2.2 when usage patterns justify. CONTEXT confirms.

3. **Middle excerpt: literal midpoint vs RMS-peak detection [RESOLVED]**
   - What we know: Pitfall P54 recommends RMS-peak; CONTEXT defers to literal mid.
   - What's unclear: How much recall do we lose with literal mid on tracks with off-center drops?
   - **Recommendation:** Literal `duration/2 ± 30s` in v1. Cheaper, no librosa dep. Re-evaluate after Kaan-ear-test reveals miss cases.

4. **TS schema generation pipeline [RESOLVED]**
   - What we know: vibemix uses dataclasses + jsonschema (not pydantic). CONTEXT mentions "pydantic-to-typescript" — incorrect.
   - What's unclear: How are TS types currently generated from `messages.schema.json`?
   - **Recommendation:** [VERIFIED: `tauri/ui/src/ipc/messages.ts` + `validator.generated.mjs` + `npm run check:ipc`] — existing codegen flow generates TS from jsonschema. Phase 28 adds 4 new schema entries; codegen pipeline emits TS types automatically. No new tool needed.

5. **Cache database path collision [RESOLVED]**
   - What we know: Existing `~/.cache/vibemix/library.pkl` is the Rekordbox pickle. CONTEXT proposes `~/.cache/vibemix/library.db` for sqlite-vec.
   - What's unclear: Same directory — name collision risk?
   - **Recommendation:** Use separate files: `library.pkl` (Rekordbox), `embeddings.db` (sqlite-vec embeddings + query cache), `embeddings.npy` + `embedding_ids.json` (numpy Win fallback). Plan-phase should commit to these exact paths. ARCHITECTURE.md line 101 agrees.

6. **Audio MIME type for excerpts [RESOLVED]**
   - What we know: SDK example uses `mime_type='audio/mpeg'` (MP3). DJ libraries may have FLAC, AAC, WAV originals.
   - What's unclear: Does Gemini Embedding 2 accept all? Or do we need to transcode to MP3?
   - **Recommendation:** [CITED: ai.google.dev] — "supports MP3 and WAV formats". Transcode FLAC/AAC → MP3 via ffmpeg as part of excerpt extraction (already needed for slicing). Cache the MP3 excerpt on disk for re-use.

7. **Cancel-mid-import behavior [RESOLVED]**
   - What we know: CONTEXT says cancel button sets `cancel_flag`. Sidecar must check between batches.
   - What's unclear: Partial-import state — does the next import resume or restart?
   - **Recommendation:** Resume from content-hash cache. Cancelled tracks unembedded → next import picks up from cache miss. No explicit "resume" state needed; content-hash cache provides idempotency.

8. **`task_type` field for vibe-search vs grounding [RESOLVED]**
   - What we know: [CITED: ai.google.dev] — `task_type` field is NOT used with `gemini-embedding-2`. Embedding instructions inline in prompt text.
   - What's unclear: How to phrase the query embedding to favor "similar audio vibe" over "literal token match"?
   - **Recommendation:** No task_type config. Vibe-search query is embedded as plain text (`"driving acid techno around 138 BPM, dark intro"`). Audio excerpts embed as Part. Gemini Embedding 2's multimodal single space handles cross-modal matching natively. No special prompt engineering needed in v1.

9. **Model ID discrepancy: CONTEXT says `gemini-embedding-001`, STACK says `gemini-embedding-2-preview`, docs say `gemini-embedding-2` [RESOLVED]**
   - **Recommendation:** Use `gemini-embedding-2` (GA model ID, verified at ai.google.dev). `gemini-embedding-2-preview` co-exists; use GA. CONTEXT.md `embedding-001` is stale — predates Gemini Embedding 2. Plan-phase MUST correct CONTEXT terminology.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | sidecar | ✓ | 3.14 (Mac/Win shipped per CLAUDE.md) | — |
| google-genai | LIBRARY-10 | ✓ (pyproject locked >=2.0.1) | — | — |
| sqlite-vec | LIBRARY-11 | ✓ (pyproject locked ==0.1.9) | 0.1.9 | numpy-only path |
| numpy | LIBRARY-11 | ✓ (pyproject) | >=2.4.4 | — |
| pyrekordbox | rekordbox.py (consumed) | ✓ (shipped Phase 25) | ==0.4.4 | — |
| jsonschema | IPC validation | ✓ (shipped) | >=4.23 | — |
| websockets | ws_bus | ✓ (shipped) | — | — |
| ffmpeg | Audio excerpt extraction | ⚠️ check at boot | varies | Fail loud at import-start; Phase 33 INSTALL wizard bundles. |
| Tauri 2 webview onDragDropEvent | LIBRARY-05 | ✓ (Tauri 2 default) | 2.x | File-picker only (existing button). |
| sqlite3 + extension support | LIBRARY-11 Mac | ⚠️ macOS default sqlite3 lacks extension support | — | Brew python's sqlite3 (per alexgarcia docs) — verified in Phase 25 spike. |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- ffmpeg — fail-loud at import-start; user prompted to install (Phase 33 will bundle).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vibemix uses Bravoh proxy for Gemini Embedding 2 calls (not direct AIza-key) | Architecture, Security | LOW — verified pattern from `agent/proxy_client.py`; Phase 28 plan must NOT bypass. |
| A2 | sqlite-vec 0.1.9 on Win includes pre-built wheel for both x64 + ARM64 | Stack | MEDIUM — STACK.md flagged ARM64 wheel as "needs verification". If absent, numpy fallback covers. |
| A3 | Event-gated grounding (Option B) provides sufficient citation coverage | Budget Telemetry, Open Q1 | MEDIUM — empirical; revisit in v2.2 after Kaan-ear-test. |
| A4 | `np.argpartition` + Python `sorted(key=...)` produces bit-identical results on Mac and Win | Pattern 2, P55 | LOW — Timsort is deterministic; floats are IEEE 754 identical for cosine ops; verified by parity test in Wave 1. |
| A5 | Content-hash key including `excerpt_strategy_version="v1-3excerpt-mean"` is sufficient versioning | Pattern 3 | LOW — bumping the constant invalidates cache; standard approach. |
| A6 | Cache database can co-exist in `~/.cache/vibemix/` alongside `library.pkl` (Phase 25 shipped) | Open Q5 | LOW — separate filenames; verified ARCHITECTURE.md line 101. |
| A7 | Drag-drop dedupe by `event.id` resolves Tauri Issue #14134 across both macOS and Windows webviews | Pattern 5 | MEDIUM — Tauri bug is open; verify in plan-phase with on-device test on both OS. |
| A8 | Audio MIME `audio/mpeg` is the only Gemini Embedding 2-accepted upload format requiring transcoding from FLAC | Open Q6 | LOW — verified [CITED: ai.google.dev], "MP3 and WAV formats". WAV also acceptable for lossless. |
| A9 | Cost projection at €0.20/1M text tokens + €6.50/1M audio tokens (2026 rates) is stable for milestone duration | Budget Telemetry | MEDIUM — Google pricing can change. Test asserts a derived total against a config constant; pricing change requires constant update only. |
| A10 | Bravoh proxy already proxies the `models:embedContent` endpoint (not just `models:generateContent`) | Architecture | HIGH if wrong — would force a proxy-side change in this phase. **Plan-phase MUST verify** by checking `proxy/` codebase + sending a test embed call through the proxy in Wave 0. |

## Sources

### Primary (HIGH confidence)

- [Gemini Embedding 2 model docs (Google AI for Developers)](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2) — model ID, supported modalities, dimensionality
- [Embeddings API (Google AI for Developers)](https://ai.google.dev/gemini-api/docs/embeddings) — Python SDK example, 180s audio cap, MP3/WAV, `output_dimensionality=768`, task_type N/A
- [Gemini Embedding 2 announcement (Google DeepMind blog)](https://deepmind.google/models/gemini/embedding/) — multimodal single space, 8192 token context
- [sqlite-vec Python guide](https://alexgarcia.xyz/sqlite-vec/python.html) — install, `sqlite_vec.load(db)`, vec0 virtual table
- [sqlite-vec KNN features](https://alexgarcia.xyz/sqlite-vec/features/knn.html) — `MATCH :query and k = N`, distance_metric=cosine
- [Tauri 2 stable release blog](https://v2.tauri.app/blog/tauri-20/) — drag-drop event rename
- [Tauri Discussion #4736 (drag from PC folder)](https://github.com/tauri-apps/tauri/discussions/4736) — onDragDropEvent API
- [Tauri Issue #14134 (duplicate drag events)](https://github.com/tauri-apps/tauri/issues/14134) — dedupe by event ID
- VERIFIED codebase: `src/vibemix/__main__.py:672-682` (register_library wired), `src/vibemix/state/evidence_registry.py:168` (register_library def), `src/vibemix/library/rekordbox.py` (Phase 25 shipped), `src/vibemix/ui_bus/messages.py` (jsonschema pattern), `tauri/ui/src/ipc/messages.schema.json` (Draft-07 oneOf)

### Secondary (MEDIUM confidence)

- [Gemini Embedding 2 pricing 2026 (AICostCheck.com)](https://aicostcheck.com/model/gemini-embedding-2-preview) — $0.20/1M text, $6.50/1M audio
- [Gemini Embedding 2 cookbook quickstart](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Embeddings.ipynb)
- [sqlite-vec stable release blog](https://alexgarcia.xyz/blog/2024/sqlite-vec-stable-release/index.html)
- v2.1 STACK.md and ARCHITECTURE.md (`.planning/research/v2-1/`)
- v2.1 PITFALLS.md (P48, P54, P55, P56 mitigations)

### Tertiary (LOW confidence — flagged for plan-phase validation)

- BYO-key soft cap design pattern (deferred — not needed in v1 per CONTEXT clarification)
- librosa RMS-peak vs literal-mid decision (deferred — literal-mid recommended)
- Tauri drag-drop OS-parity (macOS WKWebView vs Windows Webview2) — verify on both at Wave 1

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep is locked in pyproject.toml; model ID + storage backend + SDK syntax all cited from official docs
- Architecture: HIGH — verified against shipped code (`__main__.py:672-682`, `evidence_registry.py:168`, `ui_bus/messages.py`)
- Pitfalls: HIGH — P48/P54/P55/P56 mitigations cross-referenced with research PITFALLS.md and codebase
- Budget telemetry: MEDIUM — Option A/B/C tradeoff is empirical; plan-phase must lock the choice (recommend B)
- Drag-drop: MEDIUM — Tauri Issue #14134 dedupe is recent (2026); cross-OS verification needed in Wave 1
- IPC schema codegen: HIGH — existing pipeline (`npm run check:ipc` + `scripts/check_ipc_schema.py`) handles new entries

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (30 days — Gemini Embedding 2 model ID is GA but could evolve; sqlite-vec moves fast; Tauri 2 minor patches frequent)

---

## RESEARCH COMPLETE

**Phase:** 28 — Library Intelligence v1
**Confidence:** HIGH

### Key Findings

- **Model ID is `gemini-embedding-2`** (NOT `embedding-001` from CONTEXT.md — verified discrepancy via ai.google.dev). Plan-phase MUST correct this.
- **sqlite-vec serves as persistence-only in v1**, with all top-K math in shared Python `cosine_topk()` — sidesteps Pitfall P55 entirely. sqlite-vec's own KNN deferred until parity test corpus + bit-identity assertions ship.
- **Cost-critical decision in Open Q1:** continuous-3/min grounding blows €50 budget by ~60×. **Recommended: event-gated grounding** (Option B) — ~€27/month at 1000 DAU. Plan-phase MUST lock this in the budget assertion test.
- **Tauri 2 drag-drop duplicate-event bug (Issue #14134) is real and unfixed** — handler MUST dedupe by `event.id`.
- **Zero new runtime dependencies** — every primitive (google-genai, sqlite-vec, numpy, jsonschema, websockets, pyrekordbox, hashlib) is already in the locked v2.1 stack.
- **register_library wiring is VERIFIED at `__main__.py:672-682`** (Phase 27 closed P48). Phase 28 must add invocation + E2E tests but does NOT need to add the call.
- **TS code generation via existing `npm run check:ipc`** — vibemix uses dataclasses + jsonschema (NOT pydantic per `messages.py:8-13`). CONTEXT's "pydantic-to-typescript" mention is stale.
- **Vanilla TS in `tauri/ui/src/`**, NOT React — CONTEXT wording must be corrected at plan time.

### File Created

`/Users/ozai/projects/dj-set-ai/.planning/phases/28-library-intelligence-v1/28-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All deps cited + locked in pyproject |
| Architecture | HIGH | Verified against shipped code |
| Pitfalls | HIGH | Cross-referenced with PITFALLS.md + codebase |
| Budget Telemetry | MEDIUM | Sampling-rate choice is empirical; plan-phase locks |
| Drag-Drop | MEDIUM | Tauri Issue #14134 cross-OS verify needed Wave 1 |
| IPC Codegen | HIGH | Existing `npm run check:ipc` pipeline verified |

### Open Questions (all resolved with recommendations)

All 9 open questions resolved per `gsd-autonomous fully`. Highest-impact decisions:
1. **Sampling rate = event-gated (Option B)** — required to meet €50/month budget.
2. **Model ID = `gemini-embedding-2`** — corrects CONTEXT.md.
3. **sqlite-vec = storage-only in v1** — guarantees Mac/Win parity.

Two MEDIUM-risk assumptions need Wave 0 plan validation:
- A2 — sqlite-vec ARM64 Windows wheel availability (test at install)
- A10 — Bravoh proxy passes `models:embedContent` endpoint through (verify via probe call in Wave 0)

### Ready for Planning

Research complete. Planner can now create PLAN.md files. Recommended wave structure:
- **Wave 0:** Test scaffolding + proxy probe + dep verification + fixture corpus.
- **Wave 1:** `library/embed.py` + `library/_cosine.py` + `library/store.py` + `library/index_*.py` + Mac/Win parity test (P55 gate).
- **Wave 2:** `library/search.py` + `library/grounding.py` + `library/staleness.py` + `library/budget.py` + integration tests for P48 + register_library wiring E2E.
- **Wave 3:** IPC schemas (4 new entries) + `library-panel.ts` vanilla-TS drag-drop + visual mocks alignment + LIBRARY-05 e2e.
- **Wave 4:** CLI commands (`vibemix library search/similar/budget`) + COST-PROJECTION.md + telemetry surface.
