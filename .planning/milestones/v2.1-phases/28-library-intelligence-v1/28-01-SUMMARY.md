---
phase: 28-library-intelligence-v1
plan: 01
subsystem: library
tags: [gemini-embedding, embedding-2, content-hash-cache, ffmpeg, sqlite, proxy-only, mac-win-parity]

requires:
  - phase: 25-pyrekordbox-xml-import-debrief-architectural-slot
    provides: TrackEntry / RekordboxLibrary dataclasses
  - phase: 05-fastapi-proxy-install-uuid-jwt
    provides: build_proxy_genai_client (Bravoh proxy genai.Client builder)

provides:
  - LibraryEmbedder class with embed_track(track) + embed_query(text)
  - 3-excerpt strategy (intro/mid/outro 60s mp3 via ffmpeg, mean-pool)
  - Content-hash SHA256 cache → ~/.cache/vibemix/embeddings.db
  - Streaming-only text-only fallback
  - Audio-cap error fallback path
  - Shared cosine_topk + l2_normalize (Mac/Win parity primitive)

affects: [28-02, 28-03, 28-04, 28-05, 28-06]

tech-stack:
  added: []
  patterns:
    - "Proxy-only contract: no AIza env vars read by library modules"
    - "Three-excerpt mean-pool for tracks > 180s"
    - "Content-hash cache with strategy_version + model_id in key"
    - "Float32-asserted shared math primitive across backends"

key-files:
  created:
    - src/vibemix/library/_cosine.py
    - src/vibemix/library/embed.py
    - tests/library/test_embed.py
    - tests/library/fixtures/__init__.py
  modified:
    - src/vibemix/library/__init__.py

key-decisions:
  - "Model ID locked to gemini-embedding-2 (Open Q9 — overrides stale CONTEXT)"
  - "EMBEDDING_DIM = 768 (MRL truncation from native 3072; CONTEXT D-cost-balanced)"
  - "Cache DB path = ~/.cache/vibemix/embeddings.db (distinct from Plan 02 library.db and Phase 25 library.pkl)"
  - "ffmpeg required at import-time for the 3-excerpt path (fail-loud RuntimeError)"
  - "Single-call cap-error fallback ALWAYS produces 3 excerpts via force=True (test_audio_cap_error_handled gate)"
  - "Tie-break in cosine_topk: primary DESC similarity, secondary ASC track_id (Timsort cross-platform stable)"

patterns-established:
  - "Pattern: ALL library/* modules accept genai.Client via constructor — never build their own client. Proxy-only by construction."
  - "Pattern: shared _cosine.py for math primitives. P55 mitigation — both backends in Plan 02 will import + use the identical function."
  - "Pattern: cache key = SHA256(file_bytes || model_id || strategy_version). Bumping EXCERPT_STRATEGY_VERSION invalidates ALL caches without manual cleanup."
---

# Plan 28-01 — LibraryEmbedder + Shared Cosine Math

Status: complete.

## What landed

### `src/vibemix/library/_cosine.py`

Single source of math used by BOTH storage backends in Plan 28-02. Two functions:

- `l2_normalize(vec: np.ndarray) -> np.ndarray` — float32-asserted, divide-by-zero-safe.
- `cosine_topk(query, vectors, track_ids, k=10) -> list[tuple[str, float]]` — pre-normalized inputs, `argpartition` + Timsort deterministic sort (primary DESC similarity, secondary ASC track_id).

Module-level constant `EMBEDDING_DIM = 768`. Float32 assertions on every input as the Mac/Win parity contract (Pitfall P55).

### `src/vibemix/library/embed.py`

`LibraryEmbedder` class with two public methods:

- `embed_track(track)` → 768-dim float32 L2-normalized vector. Decision tree:
  1. Content-hash cache hit → return cached.
  2. Local file exists → audio path. If `duration_s > 180` go straight to 3-excerpt; if `<= 180`, try single call first.
  3. Single-call audio cap-error → fallback to 3-excerpt with `force=True`.
  4. No local file → text-only embed of `"title by artist | BPM | key"`.
- `embed_query(text)` → 768-dim float32 L2-normalized vector (text-mode embed_content).

Locked constants:
- `GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"`
- `EXCERPT_STRATEGY_VERSION = "v1-3excerpt-mean"`
- `AUDIO_CAP_SECONDS = 180`
- `EXCERPT_DURATION = 60`
- `EMBED_CACHE_DB_PATH = ~/.cache/vibemix/embeddings.db`

### Cache DB schema

```sql
CREATE TABLE IF NOT EXISTS embed_cache (
    key TEXT PRIMARY KEY,
    vector BLOB NOT NULL,
    ts REAL NOT NULL
);
```

Cache key = `SHA256(file_bytes || model_id || strategy_version)`. Streaming-only tracks substitute `f"<streaming>{track.track_id}".encode()` for the file portion. Re-importing the same byte-identical file → 0 API calls.

### ffmpeg invocation

```text
ffmpeg -y -loglevel error -ss <start> -i <input> -t 60 \
       -acodec libmp3lame -b:a 128k <tempfile>
```

Per excerpt timeout: 30s (defends against malformed audio). Tempfiles cleaned up after `read_bytes`.

### Tests (`tests/library/test_embed.py`)

8 tests, all passing in 0.4s, zero network calls (every `client.models.embed_content` mocked):

1. `test_short_track_single_call`
2. `test_long_track_split_into_3_excerpts`
3. `test_audio_cap_error_handled`
4. `test_streaming_track_text_only_path`
5. `test_content_hash_skip_on_reimport`
6. `test_text_query_embed`
7. `test_model_id_locked` (regression guard against `embedding-001` drift)
8. `test_no_task_type_param` (Open Q8 — Embedding 2 doesn't take it)

## Deviations

- **Force-fallback flag on `_extract_excerpts`**: the plan's `test_audio_cap_error_handled` requires that a short track misjudged as < 180s still gets the 3-excerpt fallback after the API rejects the single call. Added `force=True` kwarg so the cap-error fallback bypasses the short-track guard and always produces 3 excerpts.

- **TrackEntry field shape**: Phase 25's actual `TrackEntry` has `bpm: float` and `key: str` (not Optional), plus `album: str` and `cues: tuple[CuePoint, ...]` fields that the plan didn't mention. Test fixtures and `_text_signature` adjusted accordingly. No behavioral change.

## What this unlocks

- Plan 28-02 (storage layer) imports `EMBEDDING_DIM`, `cosine_topk`, `l2_normalize` from `_cosine` — bit-identical math across sqlite-vec (Mac) and numpy (Win).
- Plan 28-03 (vibe-search CLI) wraps `embed_query` with a 24h query cache.
- Plan 28-04 (grounding) calls `embed_track` on live audio snapshots from the BlackHole buffer.
- Plan 28-05 (similar) calls `embed_track` for the seed and reuses Plan 02's `top_k` against the stored library vectors.
- Plan 28-06 (drag-drop importer) batches `embed_track` over a Rekordbox XML.
