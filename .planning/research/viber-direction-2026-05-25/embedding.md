# vibemix library vibe-search — embedding/search grounding audit

Repo: /Users/ozai/projects/dj-set-ai · branch live-tuning-or-brain · HEAD ~930f53e
Scope: READ-ONLY. centering.py, search.py, similar.py, store.py, _cosine.py, embed.py, grounding.py, folder_ingest.py, index_*.py

---

## VERDICT

**Grounded & correct: YES, with ONE latent corruption risk (cache dim coupling) that is currently masked by a fail-loud assertion, not eliminated.**

- The math (mean-centering) is correct.
- The grounding invariant holds: a result can NEVER be a non-existent track — stale store rowids are skipped with a warning, never fabricated.
- Dim consistency is clean in code (no live stray 768/3072; all paths resolve EMBEDDING_DIM).
- The 80s cap routing is correct.
- The ONE real gap: the content-hash cache key (embeddings.db) does **not** include EMBEDDING_DIM. A 768→1536 dim bump did not bump the strategy version either, so a stale 768-dim cached vector could be returned by `_cache_get`. It does not silently corrupt the store (add_batch asserts shape), but it is a fail-loud crash waiting on a stale cache rather than a clean invalidation. See BUG-1.

---

## MATH CORRECTNESS (centering.py)

Verified against the spec — all correct:

- **Centroid = mean of stored unit vectors** — `compute_centroid` (centering.py:64-67): `vectors.mean(axis=0).astype(float32)` then `l2_normalize`. Stored vectors are already L2-unit (embed.py always returns `l2_normalize(...)`), so this is the mean of unit vectors, re-normalized. Correct.
- **Subtract from BOTH query and candidates, re-L2-normalize, rank by cosine** — store.py `search_centered` (store.py:63-90): `center_and_renorm(query)` + `center_and_renorm(vectors)` with the SAME centroid, then the shared `cosine_topk`. Correct and P55-parity-preserving (only inputs change; the dot-product chokepoint is untouched).
- **(a) Centroid cached by snapshot_hash, recomputed on store change** — `load_or_compute_centroid` (centering.py:90-143): fast path reads `library_centroid.npy` + `.meta.json`, returns cached only if `meta.snapshot_hash == store.snapshot_hash()` AND dtype==float32 AND shape==(EMBEDDING_DIM,). On mismatch/corrupt/missing it recomputes and atomically rewrites (tmp .npy → replace). When the track set changes the snapshot hash changes → recompute. Correct. Also note the cached-array shape guard at centering.py:118 means a stale centroid at the OLD dim is rejected and recomputed — this is the one place dim is actually validated on read.
- **(b) N<2 degenerate guard → None → raw-cosine fallback** — `compute_centroid` returns None for `ndim != 2 or shape[0] < 2` (centering.py:64). `search_centered` falls back to plain `cosine_topk` when centroid is None (store.py:86-87). No crash, no NaN. Correct.
- **(c) QUERY-SIDE only** — persisted vectors are never rewritten; centering happens on freshly loaded copies inside `search_centered`. Correct.
- **NaN / zero-norm safety** — `center_and_renorm` (centering.py:81-87): single-vector path delegates to `l2_normalize` (returns input unchanged if norm<1e-12 — no div-by-zero); batch path uses `np.where(norms < 1e-12, 1.0, norms)` so a row at the exact corpus mean becomes the zero vector (cosine 0, ranks last) — documented and correct. No NaN path.
- **dtype** — all float32 throughout; `load_all` returns float32 in both backends (sqlite-vec frombuffer float32; numpy store asserts float32 on load). frombuffer arrays are read-only but every centering op produces a new array, so no in-place write error.

No numerical bug found in centering.

---

## GROUNDING INVARIANT (can it ever return a non-existent track?)

**DEFINITIVE: NO. A vibe-search / similar result is emitted ONLY if its track_id resolves to a real TrackEntry in the in-memory library index.**

- `vibe_search` (search.py:135-157): builds `index = {t.track_id: t for t in tracks}` from `library.tracks`, then for each `(tid, sim)` from `store.search_centered`, does `t = index.get(tid)`; if `t is None` it **logs a warning and `continue`s** (search.py:139-146) — the stale store row (vector whose track_id is no longer in the library) is SKIPPED, never fabricated. The emitted `VibeSearchResult` is built from the real TrackEntry's title/artist/bpm. Confirmed.
- `similar_to` (similar.py:89-94): same pattern — `t = index.get(tid)`; `if t is None: continue`. Stale rows skipped. Seed excluded. Confirmed.
- `identify_playing` grounding (grounding.py:149-166): returns top-1 `track_id` from `store.search(...)`. NOTE: this path returns the store's track_id WITHOUT re-resolving it against the library (it has no library handle — it's the live audio path). The downstream agent injects `[track:<id>]` only when `decision == "cited"` (cosine >= 0.7). This is a different surface than vibe-search; the citation grounding gate against EvidenceRegistry lives in the agent layer, not here. Within library scope this is consistent: it returns a real stored track_id (never invented). The threshold gate prevents low-confidence cites. Acceptable for this audit's scope.

**dict-shape fix confirmed correct** at both call sites:
- search.py:101-102 `raw = library.tracks; tracks = list(raw.values()) if isinstance(raw, dict) else list(raw)`
- similar.py:62-63 identical.
Both handle the canonical dict `{track_id: TrackEntry}` and tolerate a bare list. Correct — `.values()` yields TrackEntry objects (`t.track_id` works), and a list yields the same. No regression.

---

## DIM CONSISTENCY (stray 768 / 3072)

**Code is clean. No LIVE hardcoded dim. All embed/search/store paths resolve `_cosine.EMBEDDING_DIM` (=1536).**

grep of `src/vibemix/library/` for 768/3072/output_dimensionality:
- All `768` hits are in COMMENTS / docstrings / fail-loud error message strings (store.py:98, folder_ingest.py:30/206/219/252, index_sqlite_vec.py:114/140, _cosine.py:34-55). Not executable dim literals.
- `output_dimensionality` appears 4× (embed.py:257, embed.py:722, embed.py:743, grounding.py:126) — **every one passes `EMBEDDING_DIM`**, none hardcoded. grounding.py:126 confirmed FIXED from the prior 768 literal (commit b16ec8a).
- `3072` hits are all comments (the rollback note in _cosine.py).
- ONE stale COSMETIC docstring: index_numpy.py:92 `"""...Vectors must be float32 (768,)."""` — the actual assertion two lines down uses `(EMBEDDING_DIM,)`, so this is wrong text only, no behavioral impact. (NIT-1)

`l2_normalize` and `cosine_topk` assert `query.shape == (EMBEDDING_DIM,)` and `vectors.shape[1] == EMBEDDING_DIM` (_cosine.py:123-130), so any dim mismatch reaching the math is a fail-loud AssertionError, not silent garbage.

Store-side dim guard is robust: `_assert_store_dim_compatible` (folder_ingest.py:200-255) catches a stale-but-empty 768 vec0 table (parses `FLOAT[N]` DDL), auto-recreates ONLY when row_count==0, else fails loud; plus a zero-query probe. Solid.

---

## 80s CAP HANDLING (embed.py)

**Correct. Tracks >80s never send a single >80s embed_content call.**

- `AUDIO_SINGLE_CALL_MAX_SECONDS = 80` (embed.py:140) — the real routing threshold. `AUDIO_CAP_SECONDS = 180` (embed.py:131) is used ONLY by the `_is_audio_cap_error` heuristic, not routing.
- `_embed_audio` (embed.py:457-488): `if duration_s <= 80` → single call, and on a cap-error it sets `force_excerpts=True` and falls to the 3-excerpt path (defense-in-depth). `> 80` skips the single-call gamble entirely and goes straight to 3 excerpts (intro/mid/outro, 60s each via ffmpeg `-t 60`). Each excerpt is its own single embed call, then mean → `l2_normalize`. So no call ever carries >80s of audio. Confirmed.
- `_extract_excerpts` (embed.py:644-706): each clip is `EXCERPT_DURATION=60`s, well under cap. Starts at 0 / midpoint / (dur-60). Tempfiles cleaned in finally. Correct.
- Cue-anchored path (embed.py:490-569): `CUE_WINDOW_SECONDS` kept <= 80 by contract (embed.py:112-114), each cue window is a single call, mean+normalize. Falls back to `_embed_audio` on no-cues. Correct.
- **Sub-3072 L2-normalization**: every return path normalizes — embed_track (line 428), embed_query (440), _embed_audio (468, 488), cue-anchored (569), grounding (138). Google does not auto-normalize MRL-truncated dims; vibemix always does. Confirmed.

---

## CACHE CORRECTNESS (embeddings.db content-hash cache)

`_track_hash` (embed.py:765-804) hashes: file_bytes (64KB-chunked) OR `<streaming>{track_id}` marker, `|| self._model || self._excerpt_strategy_version`, and (cue_anchored only) `|| CUE_ANCHORED_STRATEGY_VERSION`.

What is GOOD:
- Cache hit returns the exact stored bytes for that key — `_cache_get` (embed.py:808-815) `np.frombuffer(blob, float32).copy()`. SHA256 key, no realistic collision risk.
- Strategy version IS in the key, and model id IS in the key — a model rename or strategy change invalidates. cue_anchored vs mean_excerpt namespaces are disjoint (won't cross-contaminate).
- `_cache_put` asserts `dtype==float32 and shape==(EMBEDDING_DIM,)` (embed.py:820) — a wrong-dim vector can never be WRITTEN under the current dim.

What is the GAP — see BUG-1:
- **EMBEDDING_DIM is NOT a component of the cache key.** The 768→1536 bump (commit b16ec8a) changed EMBEDDING_DIM but did NOT bump `EXCERPT_STRATEGY_VERSION` (still `"v1-3excerpt-mean"`, embed.py:86) and did NOT add a dim field to `_track_hash`. So for the same file + same model id + same strategy version, the cache key is byte-identical at 768 and at 1536. A pre-bump embeddings.db row holds a 768-dim blob; post-bump `_cache_get` will `frombuffer` it as a 768-element float32 array and `embed_track` returns it WITHOUT any shape check (`_cache_get` validates nothing; `embed_track` line 404-410 returns the cached array directly).

---

## BUGS

### BUG-1 (MEDIUM — latent corruption, currently fail-loud-masked): content-hash cache key omits EMBEDDING_DIM
- Files: src/vibemix/library/embed.py:86 (`EXCERPT_STRATEGY_VERSION = "v1-3excerpt-mean"`), embed.py:765-804 (`_track_hash` — no dim), embed.py:808-815 (`_cache_get` — no shape validation).
- A stale 768-dim cached vector survives a dim bump and is returned by `embed_track`. It does NOT silently enter the store (NumpyStore.add_batch:100 / SqliteVecStore.add_batch and folder_ingest both ultimately assert/probe `(EMBEDDING_DIM,)`, so ingest CRASHES fail-loud). And `similar_to` checks `seed_vec.shape != (EMBEDDING_DIM,)` (similar.py:77) and returns `[]`. So today the outcome is a crash / empty-result on a stale cache, NOT silent garbage ranking — the invariant is intact. BUT the documented intent ("a dim/strategy change invalidates the cache") is NOT met: the only thing that saves it is downstream assertions, and a fresh user who bumped dim without clearing `~/.cache/vibemix/embeddings.db` hits a hard error instead of a clean lazy re-embed.
- Fix options (pick one): (a) add `h.update(str(EMBEDDING_DIM).encode())` to `_track_hash`; or (b) bump `EXCERPT_STRATEGY_VERSION` to `"v2-3excerpt-mean-1536"` on every dim change (the in-code comment at embed.py:85 already says "Bump to invalidate ALL cached embeddings" — it just wasn't bumped for the gz2 dim change); or (c) add a shape guard in `_cache_get` that drops a wrong-dim row and returns None (treats as miss). (a) or (c) is the durable fix; (b) is the manual discipline that was missed this time.

### NIT-1 (cosmetic): stale docstring
- src/vibemix/library/index_numpy.py:92 — docstring says `float32 (768,)`; the live assertion is `(EMBEDDING_DIM,)`. Text only.

### NIT-2 (cosmetic): stale docstring
- src/vibemix/library/embed.py:399 (`embed_track` decision-tree docstring) and grounding.py:119 still reference "180s" as the single-call cap; the real routing threshold is 80s (`AUDIO_SINGLE_CALL_MAX_SECONDS`). The CODE is correct (uses the 80 constant); the comments mislead. grounding.py audio is short (≤30s) so behaviorally irrelevant, but the docstring should say 80s.
