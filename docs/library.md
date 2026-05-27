# Library embedding — vibe search over your own tracks

vibemix can embed a folder of your audio files into a local vector index, then
let you search it by *vibe* ("dark rolling techno") or by *similarity to a seed
track*. Everything is stored locally; audio embedding runs on-device with CLAP
ONNX, so your tracks do not leave the machine for library indexing.

This is an **opt-in, isolated** subsystem. It never runs during a live session
and never touches the reaction loop — it's a CLI you invoke when you want to
build or query your library.

## What it does

```
your folder of tracks ──▶ embed-folder ──▶ ~/.cache/vibemix/library-clap.db   (512-d vectors, sqlite-vec)
                                       └─▶ ~/.cache/vibemix/library.pkl  (titles for search/similar)

            search "<vibe>"  ─┐
            similar <id>     ─┴──▶ top-K nearest tracks (filename + score)
```

- **Model:** CLAP ONNX (`Xenova/larger_clap_music_and_speech`) — local
  audio/text embeddings in one shared space.
- **Dimensions:** 512, L2-normalized before storage.
- **Long tracks:** audio is chunked into deterministic 10s windows and
  mean-pooled into one track vector.
- **Backend:** `sqlite-vec` on macOS / Windows-x64, with a NumPy fallback
  (bit-identical top-K).

## Prerequisites

Install local AI runtime dependencies when setting up a full app/dev
environment:

```bash
uv sync --extra ai-local
```

Use `--extra clap` for embedding-only CI/dev jobs, or `--extra cue` for
cue-engine-only checks.

1. **CLAP ONNX model files** under `~/.cache/vibemix/clap-onnx/` or
   `VIBEMIX_CLAP_ONNX_DIR`.
2. Optional for cue-anchored ingest: **CUE-DETR ONNX** at
   `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx` or
   `VIBEMIX_CUE_ONNX_PATH`. If missing, cue detection falls back to the local
   heuristic.
3. **ffmpeg / ffprobe** on your `PATH` (already required by vibemix — used to
   read track duration and slice excerpts).

Check local model status before indexing:

```bash
uv run python -m vibemix library models --json
```

This is an offline setup probe. It reports install state, cache paths, missing
files, and env overrides for both CLAP and CUE-DETR.

Install or verify the supported downloadable assets:

```bash
uv run python -m vibemix library models --install required --json
```

`--install required` is the app's first-run path: it downloads the required
CLAP files from the `Xenova/larger_clap_music_and_speech` Hugging Face model
repo into the vibemix cache and verifies size + SHA-256. Existing verified
files are skipped. `--install clap` performs the same CLAP-only install.
`--install cue` reports/verifies the CUE-DETR target and exits non-zero until
the ONNX file is present. It can download CUE-DETR only when a release/ops
build provides a hosted fp32 ONNX artifact through all three env pins:
`VIBEMIX_CUE_ONNX_URL`, `VIBEMIX_CUE_ONNX_SHA256`, and
`VIBEMIX_CUE_ONNX_SIZE`. `--install all` remains strict and requires both
targets to be ready. Without those pins, CUE remains an honest manual target.

## Build your library

```bash
uv run python -m vibemix library embed-folder "/path/to/your/music"
```

It walks the folder recursively, embeds every supported file
(`.mp3 .m4a .wav .flac .aac`), and prints per-track progress with a running
cost estimate:

```
-> embed-folder: embedder=CLAP ONNX (local, keyless)
-> library store: backend=SqliteVecStore reason=ok
[1/128] ok   10_10.mp3                    ~€0.0000
[2/128] ok   2AT x Nixss - Nonstop.mp3    ~€0.0000
[3/128] err  corrupt_file.mp3             ~€0.0000   (logged, skipped)
...
```

It is:

- **Resumable** — already-embedded files are content-hash cached, so re-running
  the same folder just tops up what's missing. Safe to Ctrl-C and resume.
- **Fault-tolerant** — a corrupt / unprobeable / over-long file is logged and
  skipped; it never aborts the run and never stores a faked embedding.
- **Keyless** — the running `~€` estimate stays at zero for local CLAP
  embeddings.

**Tip:** start with one representative subfolder (a single genre, or a folder
with cross-genre variety) before committing a multi-thousand-track library —
you validate quality and local model speed first.

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
- **Cost:** local CLAP embeddings do not use the Gemini embedding API.
- **Privacy:** vectors, index, and audio stay on your machine for embedding.
- **Setup:** `library models --json` is the installer/app seam for showing
  whether local model assets are ready before a user starts indexing.
  `library models --install required --json` installs the pinned
  full-precision CLAP ONNX snapshot and repairs mismatched required caches.
  Add `--progress` to keep stdout as final JSON while emitting
  `VIBEMIX_MODEL_PROGRESS {...}` frames on stderr for the desktop setup row.
  `library models --install cue --json` verifies CUE and can install it from a
  hosted artifact only when URL, byte size, and SHA-256 are configured.
- **Agent preflight:** `library stats --json` also reports the local Codex
  Viber backend plus `agent_ready`, `agent_status`, and `agent_hint`. This is an
  offline check for obvious Codex setup gaps; the actual chat/build run still
  returns the authoritative result.
- **Dependencies:** the full app/installer path should include the
  `ai-local` extra; narrower `clap` and `cue` extras exist for focused jobs.
- Changing `EMBEDDING_DIM` invalidates an existing index — delete
  `~/.cache/vibemix/library-clap.db` and re-embed (an empty stale-dim table is
  auto-recreated; a populated one fails loud to protect your data).
