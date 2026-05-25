# Library embedding — vibe search over your own tracks

vibemix can embed a folder of your audio files into a local vector index, then
let you search it by *vibe* ("dark rolling techno") or by *similarity to a seed
track*. Everything is stored locally; only the audio sent for embedding leaves
your machine (to Gemini, via your own key).

This is an **opt-in, isolated** subsystem. It never runs during a live session
and never touches the reaction loop — it's a CLI you invoke when you want to
build or query your library.

## What it does

```
your folder of tracks ──▶ embed-folder ──▶ ~/.cache/vibemix/library.db   (1536-d vectors, sqlite-vec)
                                       └─▶ ~/.cache/vibemix/library.pkl  (titles for search/similar)

            search "<vibe>"  ─┐
            similar <id>     ─┴──▶ top-K nearest tracks (filename + score)
```

- **Model:** Gemini Embedding 2 (`gemini-embedding-2`) — natively multimodal,
  embeds audio directly (no transcription, no text-tagging step).
- **Dimensions:** 1536 (a Matryoshka cut-point of the model's native 3072),
  L2-normalized before storage.
- **Long tracks:** the model takes short audio windows, so tracks are sampled
  as three 60s excerpts (intro / mid / outro) and averaged into one vector.
  Tracks ≤ 80s are embedded in a single call.
- **Backend:** `sqlite-vec` on macOS / Windows-x64, with a NumPy fallback
  (bit-identical top-K).

## Prerequisites

1. **An API key.** Either:
   - `GEMINI_API_KEY` in your `.env` (direct — the same key the live co-host
     uses), or
   - `VIBEMIX_PROXY_JWT` (+ optional `VIBEMIX_PROXY_BASE_URL`) for the Bravoh
     proxy path.
   `embed-folder` prefers the direct key when `GEMINI_API_KEY` is set.
2. **ffmpeg / ffprobe** on your `PATH` (already required by vibemix — used to
   read track duration and slice excerpts).

See [`byo-key.md`](./byo-key.md) for getting a key.

## Build your library

```bash
uv run python -m vibemix library embed-folder "/path/to/your/music"
```

It walks the folder recursively, embeds every supported file
(`.mp3 .m4a .wav .flac .aac`), and prints per-track progress with a running
cost estimate:

```
-> embed-folder: client=direct (GEMINI_API_KEY)
-> library store: backend=SqliteVecStore reason=ok
[1/128] ok   10_10.mp3                    ~€0.0017
[2/128] ok   2AT x Nixss - Nonstop.mp3    ~€0.0033
[3/128] err  corrupt_file.mp3             ~€0.0033   (logged, skipped)
...
```

It is:

- **Resumable** — already-embedded files are content-hash cached, so re-running
  the same folder costs ~€0 and just tops up what's missing. Safe to Ctrl-C and
  resume (handy on a slow connection).
- **Fault-tolerant** — a corrupt / unprobeable / over-long file is logged and
  skipped; it never aborts the run and never stores a faked embedding.
- **Cost-aware** — the running `~€` estimate lets you abort if a huge folder
  spikes. Embedding is cheap (≈ €0.002 / track), but it scales with library
  size.

**Tip:** start with one representative subfolder (a single genre, or a folder
with cross-genre variety) before committing a multi-thousand-track library —
you validate quality, cost, and upload speed first.

`--json` emits the final report (and per-track `track_id`s) as JSON instead of
the human progress stream.

## Query it

**By vibe (free text):**

```bash
uv run python -m vibemix library search "dark rolling hypnotic techno"
uv run python -m vibemix library search "euphoric melodic build" --k 15
```

**By similarity to a seed track:**

```bash
# get a track_id (run embed-folder --json, or note one from the index)
uv run python -m vibemix library embed-folder "/path/to/music" --json
uv run python -m vibemix library similar folder:ab12cd34ef56 --k 10
```

Folder-ingested track ids are namespaced `folder:<hash>` (a stable hash of the
absolute file path), distinct from Rekordbox-imported ids.

## Notes & limitations

- **Mean-of-excerpts** gives a single coarse "overall vibe" vector per track. It
  samples up to 180s of a track and averages, so it can blur tracks with strong
  internal contrast (ambient intro → peak drop). For transition-style matching
  (outro-of-A → intro-of-B) a per-section / multi-vector strategy is more
  faithful — that's an open design axis, not yet a shipped knob.
- **Cost** is per input token and independent of the 1536 output dimension.
- **Privacy:** vectors and the index stay on your machine. Audio excerpts are
  uploaded to Gemini for embedding under your key; nothing else is sent.
- Changing `EMBEDDING_DIM` invalidates an existing index — delete
  `~/.cache/vibemix/library.db` and re-embed (an empty stale-dim table is
  auto-recreated; a populated one fails loud to protect your data).
