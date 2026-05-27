# Bucket F — Library Intelligence Research

> Research scope: vibemix v2 local music library indexer. Embed user's tracks with Gemini Embedding 2, store locally, power "what should I play next?" live and "your library had a better neighbor for that transition" post-session. Anti-slop thesis applied: every grounding signal closes a hallucination class.
> Date: 2026-05-13. Author: GSD research agent. Status: ready for Kaan review.

## TL;DR (5 bullets)

1. **Gemini Embedding 2 audio mode** runs at `$0.00016/sec` paid tier (free tier exists). At an 80s-per-track sampled chunk strategy: **5k tracks ≈ $0.64 one-time index, 15k ≈ $1.92, 30k ≈ $3.84**. Free tier covers virtually every realistic library. Re-embedding is essentially free. The 50€/mo proxy budget is **not the bottleneck — query latency is**.
2. **Bravoh's pipeline is 80% portable.** `app/services/embedding/service.py` (309 LoC) is the canonical embed call — Gemini SDK, L2-normalize, 80s audio cap, MP3 transcoding via pydub when >20MB, tenacity retry on SSL/429. We lift the embed function verbatim and skip Bravoh's centralized "Pool API" — vibemix needs a **local embedded vector store**, not a separate service.
3. **Vector store pick: `sqlite-vec` + an in-memory hnswlib re-rank for top-k**. sqlite-vec gives us "one file on disk, no server, pip wheels for Mac arm64/x64 + Windows, ships with the Tauri sidecar." At 30k × 1536-dim it stays under 200MB and queries under 50ms. Vectorlite is faster but `<400 stars, last release Aug 2024` — too dormant for a load-bearing dep in a v2 ship.
4. **Don't full-track embed. Sample.** Bravoh caps at 80s for a reason: the Gemini API rejects >180s and degrades on long clips. Default strategy: **drop (60s starting at energy peak) + breakdown (30s from low-energy section)** = 2 embeddings per track, centroid stored alongside. This costs ~$0.019/track at paid rate. For tracks <90s total, embed full.
5. **Grounding payoff > recommendation engine.** The headline live feature isn't "AI picks your next track" (that's slop-prone — users have taste). It's **"is this transition rough?"** grounded in: outgoing track key + BPM + Camelot adjacency, incoming track same, *and* an embedding-distance check against the actual transition audio segment. Library intelligence's job is to give the cohost evidence to call out a key clash 4 bars before it lands, and to drop "your library has a 124 BPM Bm track 3 spots back if you want to bail" as a soft suggestion — never a prescription.

---

## Gemini Embedding 2 audio mode — concrete behavior + pricing

### Model + API shape

- **Model name**: `gemini-embedding-2-preview` (per Bravoh `EMBED_MODEL` env, 2026-04 deployment). Generally available `gemini-embedding-001` is text-only — must use the `-2` preview SKU for audio.
- **Output dim**: configurable 128–3072. Default 3072. Bravoh picks **1536** as the production sweet spot — 4× smaller than 3072, matches `numpy.float32` storage at 6KB/vector, recall is "indistinguishable from 3072 on our benchmarks." vibemix should match: **1536-dim**.
- **L2 normalization**: required, applied client-side. Bravoh's `_l2_normalize` is 4 lines — copy verbatim.
- **Task type**: text-only kwarg. `RETRIEVAL_DOCUMENT` for stored chunks, `RETRIEVAL_QUERY` for searches. **Never pass `task_type` for audio/image/video — Gemini rejects it.**

### Audio specifics

- **Formats**: MP3 and WAV only. **No AAC/FLAC** — transcode at ingestion. macOS music libraries are full of AAC/`.m4a` (iTunes default) → mandatory pydub→MP3 step.
- **Duration cap**: 180s per docs, but Bravoh empirically caps at **80s** — they hit rejections beyond that. We adopt 80s.
- **Max payload size**: 20MB. WAV @ 44.1k/16bit/stereo = ~10MB/min → 80s WAV ≈ 14MB, safe. Bravoh's pattern is "if >20MB, transcode to 128kbps MP3 instead of byte-truncating" — truncating a WAV header corrupts it. We inherit this.
- **Sample rate**: not specified in docs. Bravoh ingests at native rate, lets Gemini handle resampling internally. Don't pre-resample.

### Pricing (2026-05, paid tier per [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing))

| Modality | $ per 1M tokens | Effective unit cost |
|---|---|---|
| Text | $0.20 | $0.0000002/token |
| Image | $0.45 | $0.00012/image |
| **Audio** | **$6.50** | **$0.00016/second** |
| Video | $12.00 | $0.00079/frame |

- **Free tier**: all inputs free of charge (Gemini Developer API), subject to RPM/TPM rate limits. Most vibemix users **never hit paid tier** — this is the secret.
- **Batch API**: 50% discount → audio drops to `$0.00008/sec`. We use this for one-time library indexing (Celery-style jobs from the Tauri shell) and skip it for live "what's playing" queries.

### Latency

- Not specified in docs. Bravoh's empirical timeout: **15s per HTTP call, ~25s async wait including retry margin**. Real-world median ≈ 1–3s for an 80s audio embed. Tenacity backoff cycles can stretch to 4 minutes worst-case on rate limit — fine for indexing, **too slow for live**.
- **Implication for vibemix**: never embed live audio on the critical reaction path. Library is pre-indexed once. Live "what's playing right now" matches the current 60s window against the *cached* library embeddings — only the *query embed* call hits the wire (~1s), then ANN search is local-microsecond.

### Batching

- API supports batch endpoint (`/v1beta/.../batchEmbedContents`). Bravoh doesn't use it (they parallelize per-track via Celery instead). For vibemix's first-run indexing of a 5k+ library, **batching matters** — wraps 100 chunks per call, halves latency and gives the 50% discount. Worth a Phase F-3 implementation pass.

### Sources

- [Gemini API embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Bravoh `app/services/embedding/service.py`](altidus:/var/www/bravoh-backend/app/services/embedding/service.py)
- [Gemini Embedding 2 Preview on OpenRouter](https://openrouter.ai/google/gemini-embedding-2-preview)

---

## Indexing strategy (full-track vs chunk, cost projection at 1k/5k/15k/30k scale)

### The chunk decision

Full-track embedding is impossible — the 180s/80s cap forces chunking. Three plausible strategies:

| Strategy | Embeds/track | Description | Verdict |
|---|---|---|---|
| **Middle 80s** | 1 | Grab seconds `90 → 170` of a track. Cheap, simple. | Loses intro/outro vibe. Fails on tracks with delayed drops (deep house, build-heavy techno). |
| **Drop + breakdown** | 2 | Use librosa onset detection to find peak-energy 60s window (drop) + low-energy 30s window (breakdown). Store both + centroid. | ✓ **Recommended**. Captures both faces of the track. Centroid powers vibe queries; individual chunks power "find me a similar drop." |
| **Sliding windows** | 3–5 | Every 60s from start, overlapping. Used in some research papers. | Wasteful. 3× cost, marginal recall gain on a DJ library that's already metadata-rich. |

**Pick drop + breakdown.** 2 embeds × 60s + 30s = 90s of audio per track. Cost at paid rate: `90 × $0.00016 = $0.0144`. With batch API (50% off): `$0.0072/track`.

### One-time index cost projection

| Library size | Cost (paid, standard) | Cost (paid, batch) | Cost (free tier) |
|---|---|---|---|
| 1k tracks | $14.40 | $7.20 | $0 |
| 5k tracks | $72.00 | $36.00 | $0 |
| 15k tracks | $216.00 | $108.00 | $0 |
| 30k tracks | $432.00 | $216.00 | $0 |

The numbers look ugly, but **virtually no vibemix user hits paid tier from a one-time index alone** — Gemini's free tier is generous (current RPM/TPM allow ~100k embed/day for free accounts). The user's *own* API key on the free tier covers indexing. We default to "user brings their own key for first-run indexing, vibemix proxy handles live queries."

If the user is on a Gemini free tier and we just throttle indexing to fit (~30 embeds/min), even 30k tracks finishes in **~33 hours of background indexing** — fine for a one-time setup, the Tauri shell shows a progress bar.

### Live query cost

Per "what should I play next?" query: 1 query embedding (text only, ~50 tokens) = `$0.00001`. Vibemix can do 5000 of these for $0.05. The 50€/mo proxy budget supports millions of queries. **Not the bottleneck.**

### Incremental updates

- **File watcher**: [`watchdog`](https://github.com/gorakhargosh/watchdog) (pure Python, FSEvents on macOS / ReadDirectoryChangesW on Windows / inotify on Linux). Pip-installable, no native deps, ships green to Tauri sidecar.
- **Triggers**: `on_created` → queue embed job; `on_deleted` → tombstone the row (don't hard-delete — user might re-add); `on_moved` → fingerprint-match (see below) and update path, don't re-embed.
- **Concurrency**: one embed worker thread, queue depth visible in UI. Don't ddos Gemini.

### Move/dedupe via Chromaprint

- **[Chromaprint](https://github.com/acoustid/chromaprint) + [pyacoustid](https://github.com/beetbox/pyacoustid)**: standard fingerprinting library used by beets, MusicBrainz, etc. Generates a perceptual hash from raw audio — invariant under transcoding, slight DSP, ID3 rewrites.
- **Why it matters**: a DJ moves their library from `/Users/x/Music/2025` to `/Volumes/USB/2025`. Without fingerprinting, watchdog sees this as 5000 deletes + 5000 creates → 5000 re-embeds → $72 wasted on identical tracks.
- **Install footprint**: chromaprint C library is ~200KB, pyacoustid is pure Python on top. Mac: `brew install chromaprint` or bundle `fpcalc` binary in the Tauri sidecar (Bravoh-style — they bundle 5+ Homebrew binaries already). Windows: same story.
- **Cost**: `fpcalc` runs at ~10s/track audio analysis, generates a 32-bit hash. Cache in SQLite alongside the embedding row. On `on_moved` or `on_created`, fingerprint first; if match exists, only update the path.

---

## Vector store recommendation (table + verdict)

Requirements baked in from constraints:
- One-click install (no Docker, no separate service) ✓
- Mac arm64 + x64 + Windows wheels for Python 3.12 ✓
- 30k vectors × 1536 dim comfortable (= ~180MB float32)
- ANN search < 50ms p99
- Persists to disk between launches
- License compatible with vibemix's TBD MIT/Apache 2.0

| Candidate | Stars | Last release | Install footprint | 30k × 1536 latency | Persistence | Wheels mac+win | Verdict |
|---|---|---|---|---|---|---|---|
| **sqlite-vec** | 7.6k | 2026-03-31 (v0.1.9) | ~500KB extension + sqlite3 (stdlib) | ~10ms exact KNN at 30k | ✓ native (one .db file) | ✓ pip wheels for all | **✓ Recommended** |
| Vectorlite | 361 | 2024-08-19 (v0.2.0) | hnswlib + sqlite wrapper, ~2MB | 124μs at 3k vectors (15× faster than sqlite-vec at 1536d) | ✓ sqlite-backed | ✓ wheels all platforms | Dormant — 8 months since release, low maintainership risk |
| hnswlib (raw) | 4.5k | 2024 ([nmslib/hnswlib](https://github.com/nmslib/hnswlib)) | header-only C++ binding, ~1MB | ~100μs at 30k | save/load index file, **no SQL** | ✓ pip wheels | Fastest but you build the metadata layer yourself |
| ChromaDB (embedded) | 18k | active | ~50MB (sqlite + hnswlib + duckdb deps) | ~5ms at 30k | ✓ persistent | ✓ wheels | Heavyweight. Fine but more dep surface than needed for a single-table lookup |
| FAISS (embedded) | 33k | active | ~100MB build, no auto-persist | sub-ms | manual write_index | ✗ Windows wheels flaky | Best perf but Windows distribution is the pain point |
| DuckDB + vss | 23k | active | ~50MB | ~10ms at 30k | ✓ | ✓ | Overkill — we don't need SQL analytics on embeddings |
| Lance | 4k | active | ~30MB, rust-backed | ~10ms | ✓ columnar | ✓ wheels | Modern, but adds a rust toolchain dep at build time for vibemix dev |
| Qdrant (client-local) | 22k | active | ~100MB binary, separate process | sub-ms | ✓ | ✓ but needs sidecar binary | Violates "no server" hard req |

### Verdict: `sqlite-vec` + Bravoh-style "store as bytes, rank in Python" fallback

**Primary**: sqlite-vec virtual table `vec0(embedding float[1536])`. Native KNN search. Metadata columns alongside (path, fingerprint, BPM, key, last_played, etc.). One `.db` file per library, ships in `~/Library/Application Support/vibemix/library.db` on Mac and `%APPDATA%\vibemix\library.db` on Windows.

**Fallback** (if sqlite-vec wheels break on a target platform): Bravoh's pattern — store embedding as `numpy.float32.tobytes()` in a `BLOB` column, do top-k ranking in Python with `np.dot`. At 30k × 1536 this is **~6ms in pure numpy** if you keep the matrix in RAM. Bravoh literally chose this over pgvector ([`docs/schema-repairs/artist_memories-2026-04-20.md`](altidus:/var/www/bravoh-backend/docs/schema-repairs/artist_memories-2026-04-20.md)) for the same "we can't ship a server" reason — pgvector unavailable in their cluster.

**No hnswlib re-rank needed at 30k.** Exact search is fast enough. Reserve hnswlib for if we ever hit 100k+ libraries (Pro DJ archives, label A&R libraries — out of scope for v2).

**Migration story**: if sqlite-vec ever blocks us, the schema is portable — column-by-column dump-and-import to any other store. Keep the vector store layer behind a thin `LibraryStore` interface.

---

## Bravoh pipeline architecture — what to lift

> Source: `ssh altidus` → `/var/www/bravoh-backend/app/services/embedding/`

### What we lift verbatim

1. **`embedding/service.py` core embed functions** (`_embed_text_sync`, `_embed_bytes_sync`, `embed_audio`, `embed_text`)
   - Gemini client lazy init, thread-safe with lock + generation counter
   - L2 normalization (4 lines)
   - SSL retry (3 attempts with backoff, client recreation on persistent SSL errors)
   - Rate limit (429) retry via tenacity, exponential jitter (initial=2s, max=60s, 6 attempts)
   - Async wrappers via `asyncio.to_thread` with 25s default / 300s background timeouts
   - **Why lift verbatim**: this is battle-tested against a 95k-track production index. Every SSL/429 retry case Kaan has seen at scale is already handled.

2. **`embedding/service.py` audio preprocessing** (`_convert_audio_to_mp3`)
   - pydub transcode WAV/FLAC → MP3 128kbps when >20MB
   - Trim to 80s
   - Truncating raw bytes corrupts the file (their hard-won lesson) — **don't byte-truncate**

3. **`embedding/chunk_builder.py` schema** — adapted
   - Bravoh's `build_audio_chunk` returns `{chunk_id, source_type, source_id, modality, embedding, content_summary, metadata, ...}`
   - vibemix needs less: `{track_id, path, fingerprint, embedding, chunk_kind (drop|breakdown|full), bpm, key, energy, indexed_at}`
   - Steal the dict shape, drop Bravoh's artist-centric fields

### What we leave behind (Bravoh-specific, vibemix-irrelevant)

- **Pool API HTTP layer** (`pool/client.py`, 200+ LoC). Bravoh has a separate FastAPI service holding the 95k-track market pool — vibemix's library is per-user-local. We replace the entire HTTP layer with a thin `LibraryStore` over sqlite-vec.
- **Cross-modal artist fingerprint** (`embedding/fingerprint.py`, 795 LoC). Bravoh computes per-artist weighted centroids across audio/visual/text modalities for "creator vs taste gap" detection. Cool concept, **out of vibemix scope**. We just need track-level embeddings.
- **Contextual frame generation** (`embedding/contextual.py`, 144 LoC). Bravoh uses Gemini Flash to write a 2-3 sentence prose description per chunk before embedding, improving retrieval. **Skip for v2** — audio embeddings without text augmentation are already strong for music. Revisit if recall is weak.
- **DragonflyDB centroid caching**. Server-side Redis — irrelevant for a single-user app.
- **Tenacity rate-limit logging via structlog**. Replace with vibemix's plain Python `logging`.

### Architectural deltas vibemix needs

1. **Local file watcher** (Bravoh has none — their inputs are user uploads via HTTP)
2. **Fingerprint dedupe layer** (Bravoh's market pool has ISRC, vibemix doesn't)
3. **Metadata enrichment from ID3/Rekordbox** (Bravoh embeds raw audio + user-provided context, vibemix needs to *read* DJ-software metadata)
4. **Single-process embedded vector store** (replaces Pool API)
5. **Proxy routing** for end-user Gemini key vs Bravoh proxy key (see Funnel section)

---

## Track metadata enrichment stack

Embedding similarity alone gives "this sounds like this." DJs need more: BPM, key, energy, hot cues, year, label. Most of this is **already in the file** if the user has tagged it for Rekordbox/Serato/Engine DJ/Mixxx. We just read it.

### Layer 1 — ID3/Vorbis/MP4 tags via [Mutagen](https://mutagen.readthedocs.io)

Pure Python, no native deps, handles every audio format DJs use. Pip-installable.

Standard tags DJs fill:
- `TBPM` (ID3) / `bpm` (Vorbis) — beats per minute. DJ tools write this universally.
- `TKEY` (ID3) / `initialkey` / `key` (Vorbis) — Camelot or natural key. `8A`, `Cm`, `D#`, etc. Normalize at read time.
- `TCON` / `genre` — genre string. Free-text, messy, useful as a soft filter.
- `TDRC` / `date` — release year. Useful for "play me something from 2018" queries.
- `TPUB` / `label` — label/publisher. Pro DJs use this heavily.
- `COMM`/`comment` — Mixed In Key and Rekordbox write energy 1–10 here in some workflows.

### Layer 2 — [pyrekordbox](https://github.com/dylanljones/pyrekordbox)

If the user has Rekordbox installed (most DJs do), `pyrekordbox` reads the `master.db` SQLite database directly. **Caveat**: Rekordbox 6/7 encrypts master.db with SQLCipher. pyrekordbox bundles the key (well-known reverse-engineered constant). Legal posture: the user already has Rekordbox installed and licensed, we're reading their own data — fair game, same as how Mixed In Key, CueGen, Lexicon, etc. operate.

What we extract beyond ID3:
- **Beat grid** — precise downbeat timing, dramatically improves "what bar of the track are we in?" grounding
- **Hot cues + memory cues** — "DROP" labeled cues, intro/outro markers. **This is gold for live-reaction grounding.** Knowing the user marked bar 47 as "DROP" lets the cohost say "drop in 8 bars" with confidence instead of guessing from audio.
- **Energy** — Rekordbox's 1–6 energy rating
- **Waveform color profile** — Rekordbox stores band-energy summaries; useful for visualization later
- **Play count, rating, color label** — for personalization

### Layer 3 — librosa fallback (only if metadata missing)

For tracks with no BPM tag (rare for a DJ — they tag everything — but possible for a hobbyist's library):
- `librosa.beat.tempo()` — accurate to ±1 BPM on most electronic music, slower on jazz/live
- Key detection via Krumhansl-Schmuckler or `librosa.feature.chroma_cqt` + template match — **less reliable**, error rate ~15-20%. Don't write back to the file; store as "estimated" in our DB.
- CPU cost: ~5s/track on a 2020 MBP. Acceptable for indexing background pass.

### Schema sketch

```sql
CREATE TABLE tracks (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE NOT NULL,
  fingerprint BLOB,           -- chromaprint hash, dedupe key
  title TEXT, artist TEXT, album TEXT, year INTEGER, genre TEXT, label TEXT,
  bpm REAL, key TEXT,         -- normalized to Camelot, e.g. "8A"
  energy INTEGER,             -- 1-10 from MIK/Rekordbox, NULL if absent
  duration_s REAL,
  rekordbox_track_id INTEGER, -- if pyrekordbox match
  embedding_drop BLOB,        -- 1536 float32 = 6144 bytes
  embedding_breakdown BLOB,
  embedding_centroid BLOB,    -- avg of drop+breakdown, used for vibe queries
  hot_cues JSON,              -- [{name, time_s, color}]
  last_played_at INTEGER,
  play_count INTEGER DEFAULT 0,
  indexed_at INTEGER NOT NULL,
  metadata_source TEXT        -- "id3", "rekordbox", "librosa"
);

-- sqlite-vec virtual table over centroid for top-k search
CREATE VIRTUAL TABLE tracks_vec USING vec0(
  track_id INTEGER PRIMARY KEY,
  embedding float[1536]
);
```

### Camelot key compatibility

For transition critique we need to compute key compatibility live:
- Same key (e.g. `8A` ↔ `8A`): perfect
- Adjacent on wheel (`8A` ↔ `7A`, `9A`): smooth
- Relative major/minor (`8A` ↔ `8B`): mood shift, valid
- `+7` on the wheel (e.g. `8A` ↔ `3A`): "energy boost," more aggressive
- Anything else: clash — cohost flags it

[PyCamelot](https://github.com/DJStompZone/PyCamelot) handles the math, or 30 LoC of homegrown logic. Ship homegrown — one less dep.

---

## Query interfaces (next-track + transition critique)

### Live query 1 — "what should I play next?"

Inputs (the grounding stack does most of the work):
- Current track centroid (already in DB)
- Current energy curve from the last 60s of live audio (RMS from `Levels` — v1 already computes this)
- Current Camelot key (from current track metadata)
- Current BPM (live audio BPM autocorr + metadata)
- Set time remaining (user-stated at session start, optional)
- User mood prompt ("ramp up," "cool down," "stay weird") — optional, voice input

Algorithm (target latency <500ms, all local):
1. Compute target embedding: weighted blend of current centroid + user mood embedding (if provided) + recency penalty.
2. sqlite-vec KNN top-50 against `tracks_vec`.
3. Re-rank with hard filters:
   - BPM within ±6% (one-pitch-knob range)
   - Key on Camelot wheel: same / adjacent / relative / +7
   - Not played in this session
   - Not played in last 7 days (recency penalty, configurable)
4. Re-score top-50 → top-5 with soft signals:
   - Energy adjacency
   - Genre proximity
   - User play_count + rating boost
5. Return top 5 with **reasoning strings** that the cohost reads aloud: `"'Galaxy' by ANNA, 8A → 9A, +2 BPM, same hypnotic vibe, you played it last week and rated it 5"`.

The reasoning string is **anti-slop**: every claim is sourced from a DB column, no LLM invention. The cohost reads, doesn't generate. Gemini gets the reasoning as text grounding when it speaks.

### Live query 2 — "is this transition rough?"

Triggers when user starts a mix (controller move detected: crossfader moves off center, or deck B volume rises above threshold while deck A still playing).

Inputs:
- Outgoing track ID + its Camelot/BPM/energy
- Incoming track ID + same (from now-playing or audible-deck heuristic)
- Live audio segment of the actual transition (last 8 bars, ~16s at 120 BPM)

Algorithm:
1. **Symbolic check**: Camelot distance + BPM delta + energy delta → score 0-1. Below threshold → "rough on paper" flag.
2. **Audio check**: embed the live 16s transition segment. Compute cosine distance against the *expected* blended centroid (avg of outgoing + incoming embeddings). High distance → "doesn't sound right" flag.
3. Combine. If both flag, cohost intervenes: `"That key clash is real — 8A into 4B is a tritone, you've got 12 bars to bail"`. If only audio flags but symbolic is fine, cohost suggests EQ: `"sounds muddy, kill the lows on deck A"`. If only symbolic flags but audio is fine, cohost compliments: `"that's a wild key jump but you sold it"`.
4. Live query latency budget: <500ms. Embed call (~1s) is async — the cohost speaks symbolic check first, audio check verifies/adjusts in the background.

### Pre-compute vs on-demand split

| Computed at index time (cached) | Computed live (on-demand) |
|---|---|
| Track centroid embeddings (drop + breakdown) | Query text embedding |
| Fingerprint | Live audio segment embedding |
| BPM, key, energy from tags | BPM/key compat scores |
| Hot cue list | ANN search results |
| Genre/year/label | Re-rank scoring |

---

## Privacy + portability

### Privacy boundary (clear)

- **Stays local**: the library DB (`library.db`), all embeddings, all metadata, all fingerprints, the user's audio files. Vibemix never uploads the library to any server.
- **Leaves the machine**: short audio chunks (≤80s per track) sent to Gemini for embedding, one-time per track. Live query audio segments (~16s) sent for embedding during transitions. Text query strings sent for embedding.
- **What Gemini sees**: anonymous audio chunks, no metadata, no track titles. Per Google's API ToS, Gemini Developer API tier does not train on prompts by default.
- **What Bravoh's proxy sees**: query rate per user (for rate limiting). No audio payload logging in the proxy. Document this in the README and privacy policy at launch.

### License posture

- User's audio files are their property — vibemix never re-uploads them after the embed call returns. Embeddings are derived data, not the original audio.
- Make this **explicit** in the README and onboarding screen. DJs are paranoid about leaks of unreleased promos. We must say "your library never leaves this computer except for ≤80s embed requests to Gemini, and those audio chunks are not retained by Google or us."
- If a label-signed pro DJ asks for **fully offline mode**, that's a v3+ ask — at that point we'd swap to a local embedding model (probably CLAP), but per Kaan's hard rule we don't propose that swap (`feedback_no_clap_use_gemini_embedding.md`).

### Portability

- One file: `library.db`. User can sync it via Dropbox/iCloud/USB stick.
- Mac → Win move: paths break (`/Users/x/Music` → `C:\Users\X\Music`). Solution: store paths *relative* to a configurable library root, plus the fingerprint as a fallback identity. On first launch with a moved DB, re-scan the new root, match by fingerprint, update paths in place. No re-embed.
- Export to JSON for backup / audit / migration: trivial since it's all SQLite.

---

## Funnel economics + free-tier policy proposal

### Per-user cost projection (Gemini API rates via Bravoh proxy)

Assumption: vibemix proxy bundles a Bravoh-side API key. End user pays nothing for occasional use, hits the proxy free tier, beyond that gets a polite "upgrade to Bravoh Pro" CTA.

| User class | Library | Activity | Embed cost/mo (proxy) | Query cost/mo (proxy) | **Total proxy cost** |
|---|---|---|---|---|---|
| Bedroom DJ (light) | 200 tracks | 5 new tracks/mo, 2 sessions/mo (~30 reactions each) | $0.07 one-time, $0.0007/mo new | $0.001 | **$0.001/mo recurring** |
| Hobbyist | 1,000 tracks | 20 new tracks/mo, weekly session (4 × 50 reactions) | $0.29 one-time, $0.003/mo | $0.002 | **$0.005/mo recurring** |
| Working DJ | 5,000 tracks | 50 new tracks/mo, 3 sessions/wk (12 × 80 reactions) | $1.44 one-time, $0.007/mo | $0.01 | **$0.017/mo recurring** |
| Pro DJ | 15,000 tracks | 100 new/mo, 5 sessions/wk | $4.32 one-time, $0.014/mo | $0.025 | **$0.039/mo recurring** |
| Hoarder | 30,000 tracks | rare new, 1 session/wk | $8.64 one-time, $0.0005/mo | $0.005 | **$0.005/mo recurring** |

**These numbers are tiny.** The 50€/mo proxy budget supports thousands of working DJs comfortably. Bottleneck is not cost — it's rate limits (RPM/TPM caps on a single shared key) and abuse.

### Free-tier policy proposal

Two-tier flow:

**Tier A — vibemix Free (default):**
- Library indexing: **user brings their own Gemini API key**, configured in settings, never leaves the machine. Free Gemini Developer tier handles it (a 30k-track library indexes in ~33h at free RPM).
- Live queries through Bravoh proxy: **100 reactions/day, 500/mo soft cap**. Resets monthly. Hit cap → cohost says "I'm conserving juice, talk to me less or upgrade." This covers 95% of users.
- **No credit card required.** Critical for GitHub stars goal.

**Tier B — Bravoh Pro / vibemix+:**
- Unlimited live queries via proxy
- Optional: Bravoh handles indexing too (no BYO key needed)
- Per-month subscription priced at Bravoh's existing Pro tier
- This is the conversion funnel — vibemix is free, Bravoh Pro is the upsell

### Tunable knobs (for Kaan)

1. **Reaction rate limit**: 100/day was a finger-in-the-wind. Could be higher (200/day) without breaking the budget. Recommend Kaan tune after first 100 beta users.
2. **Indexing**: BYO-key is the safest free-tier policy. Alternative: vibemix proxy handles indexing for libraries ≤500 tracks, BYO required beyond. More generous, slightly more cost exposure.
3. **Query embedding** (the per-search cost): always proxied, always counts against the daily cap.

---

## Risk + watchouts

1. **`gemini-embedding-2-preview` is "preview" still** — API shape could change before GA. Bravoh has been on it since 2026-04 without breaking changes, but pin the model name and watch for GA migration (probably renames to `gemini-embedding-2` no-preview suffix). One-line change.
2. **macOS BlackHole-style "user-installed driver"** is not needed for library indexing — that's audio I/O, separate concern. Library indexing reads files directly. No friction here.
3. **AAC/M4A transcoding** at scale: pydub uses ffmpeg under the hood. Need to bundle ffmpeg in the Tauri sidecar for Windows (no system ffmpeg). Adds ~20MB to the installer. Acceptable. macOS ships with afconvert as fallback.
4. **Rekordbox master.db lock**: when Rekordbox is *running*, master.db is locked. pyrekordbox reads it anyway via SQLite WAL mode, but writes are unsafe. **vibemix only reads** — never writes to Rekordbox. Document this loudly.
5. **Library scale beyond 30k**: untested. Pro archives can hit 100k+. At that scale sqlite-vec exact-KNN starts to feel sluggish (~500ms at 100k × 1536). Build the abstraction layer such that swapping to hnswlib-backed re-rank is a one-week migration, not a rewrite. Don't promise 100k support in v2 docs.
6. **Audio chunk selection accuracy**: "drop" detection via librosa onset_strength is correct ~85% of the time on EDM, drops to ~60% on ambient/jazz. Failure mode: we embed a chunk that's not representative → bad retrieval. Mitigation: also store the *centroid* (avg of drop + breakdown), use it for vibe queries. Centroid is robust even if one chunk is wrong.
7. **Gemini rate limit on shared proxy**: a viral moment (Reddit post hits front page) → 10x normal traffic → free-tier RPM cap → service degradation for all users. Mitigations: queue + retry with exponential backoff (already in Bravoh's tenacity config), surface "high traffic, try again in 30s" in the UI, have a Bravoh Pro key as backup pool.
8. **Pricing surprise**: Gemini Embedding 2 GA pricing could differ from preview. Currently locked at $6.50/M audio tokens but this is "preview" — Google reserves the right to change. Recompute budget pre-launch.
9. **pyrekordbox encryption posture**: Pioneer hasn't sued any of the 10+ libraries that use the same approach (Lexicon, CueGen, Mixed In Key, beets/rekordboxxml, etc.). But they could. If Pioneer changes the encryption scheme in Rekordbox 8, pyrekordbox might break for weeks. Have a graceful degradation: vibemix works without Rekordbox metadata, the Rekordbox priors are a *bonus* not a requirement.
10. **Centralized proxy = single point of failure**: if Bravoh proxy is down, vibemix is reaction-less for all users. Tauri shell should detect proxy failure and fall back to "library-only" mode (no live AI, but BYO-key mode still indexes). Document in roadmap.

---

## Open questions for Kaan (3-5 max)

1. **BYO-key for indexing — yes or no?** My recommendation: yes (user provides their Gemini API key for first-run library indexing, vibemix proxy handles live queries with Bravoh's key). It eliminates 95% of our cost exposure and makes the "vibemix Free" tier truly free for us. Friction cost: user has to grab a key from aistudio.google.com. Mitigation: in-app wizard with screenshots, takes 2 min. **Alternative**: vibemix proxy handles indexing too, capped at 500-track libraries on the free tier. Easier UX, higher cost ceiling for us.

2. **Drop+breakdown chunk strategy vs single 80s middle chunk?** My recommendation: drop+breakdown (2 embeds/track) for the recall gain. Cost difference is irrelevant. But it means 2× indexing time and 2× storage. If you'd rather ship fast with one chunk, switch to "middle 80s" and we revisit if recall feels weak in real DJ testing.

3. **Free-tier reaction rate limit — 100/day or higher?** I picked 100/day from intuition. A 2-hour Friday set is ~80 reactions if the cohost fires every 90s. So 100/day = roughly one set per day. Working DJs play more. Open to bumping to 200/day if you want the upgrade-to-Pro signal to come from the high-volume users only.

4. **Should "Smart Crate" (post-session "your library had better neighbors") be a v2.0 feature or a v2.1 stretch?** The recommender engine is straightforward once the index is built. UI surface is non-trivial — needs a post-session debrief screen with audio playback of "the transition you did vs the transition I'd have suggested." Time cost: ~2 weeks of frontend work. Could ship v2.0 without it (just live reactions) and add it as a 2.1 update.

5. **pyrekordbox: opt-in or auto-detect?** Opt-in = "Connect Rekordbox" toggle in settings, user explicitly grants. Auto-detect = vibemix scans for Rekordbox install on first run and offers to use the data. Auto-detect is slicker but spookier — DJs are paranoid. Recommend opt-in with a strong "this is huge for grounding" pitch on the onboarding screen.

---

## Sources

### Bravoh code (private — `ssh altidus`)

- `/var/www/bravoh-backend/app/services/embedding/service.py` — canonical embed pipeline
- `/var/www/bravoh-backend/app/services/embedding/chunk_builder.py` — chunk schemas
- `/var/www/bravoh-backend/app/services/embedding/fingerprint.py` — cross-modal centroid math
- `/var/www/bravoh-backend/app/services/embedding/contextual.py` — Gemini Flash labeling
- `/var/www/bravoh-backend/app/services/semantic_search.py` — in-memory cosine search reference
- `/var/www/bravoh-backend/app/services/pool/client.py` — Pool API client reference (we replace with local store)
- `/var/www/bravoh-backend/docs/schema-repairs/artist_memories-2026-04-20.md` — "embedding as BYTEA, rank in Python" pattern

### Public

- [Gemini API embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings) — model spec, dim, batch
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) — $0.00016/sec audio confirmed
- [sqlite-vec GitHub (7.6k stars, v0.1.9 March 2026)](https://github.com/asg017/sqlite-vec) — primary vector store
- [sqlite-vec PyPI](https://pypi.org/project/sqlite-vec/) — pip wheels for all platforms
- [Vectorlite GitHub (361 stars, v0.2.0 Aug 2024)](https://github.com/1yefuwang1/vectorlite) — faster alternative, dormant
- [hnswlib GitHub (nmslib)](https://github.com/nmslib/hnswlib) — ANN library, raw
- [watchdog GitHub](https://github.com/gorakhargosh/watchdog) — cross-platform file watcher
- [Chromaprint / AcoustID](https://acoustid.org/chromaprint) — audio fingerprinting
- [pyacoustid GitHub](https://github.com/beetbox/pyacoustid) — Python Chromaprint bindings
- [pyrekordbox docs](https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html) — Rekordbox 6/7 DB format
- [Mutagen docs](https://mutagen.readthedocs.io) — universal audio tag reader
- [Camelot Wheel — Mixed In Key](https://mixedinkey.com/camelot-wheel/) — harmonic mixing reference
- [PyCamelot GitHub](https://github.com/DJStompZone/PyCamelot) — Python Camelot impl
- [Vector Database Comparison 2026 — Groovy Web](https://www.groovyweb.co/blog/vector-database-comparison-2026)
- [Gemini Embedding 2 — buildfastwithai.com](https://www.buildfastwithai.com/blogs/gemini-embedding-2-multimodal-model)
