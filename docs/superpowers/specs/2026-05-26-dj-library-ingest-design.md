# DJ-Library Ingest — Current Product Spec

**Date:** 2026-05-26
**Status:** current Rekordbox MVP source truth after Phase 89.

DJ-library ingest turns a user's local DJ library export into local CLAP vectors
for search, similarity, set building, and Viber tools. The product path is
`uv run python -m vibemix library ingest`.

## Current Scope

Shipped MVP:

- Source: Rekordbox `collection.xml` only.
- Metadata: title, artist, album, BPM, key, Camelot, genre, label, rating,
  play count, comments, cues/loops/fades/load marks, and TEMPO beatgrid nodes.
- Embeddings: local CLAP ONNX, 512 dimensions, keyless.
- Excerpts: cue-anchored <=80s windows. DJ cues are preferred; uncued tracks
  fall back to `cue_engine.detect_cues_auto()` and then to whole-track embedding
  if no usable cue window exists.
- Storage: active local library store plus `library.pkl` for title resolution.
- Cache: CLAP-namespaced content-hash cache in
  `~/.cache/vibemix/clap_embeddings.db`, separated from legacy Gemini rows and
  from whole-track embedding strategy rows.

Deferred:

- Serato and Traktor sources.
- Real file watcher / delta queue.
- djay Pro closed database support.
- Public catalog discovery and server-side embedding.

## Current Pipeline

```
Rekordbox collection.xml
  -> RekordboxLibrary.load_xml()
  -> TrackEntry rows with typed metadata and cues
  -> ingest_source()
  -> anchors_for_track()         # DJ cue first, auto-cue fallback
  -> cut_windows()               # <=80s mixable windows
  -> ClapEmbedder / ClapEngine   # local 512D vector
  -> sqlite-vec or NumPy store
  -> library.pkl title cache
```

## Honesty And Safety Rules

- Missing or unreadable audio files are logged and counted as failures; no fake
  vector is stored.
- A cue failure degrades to whole-track embedding; a bad cue window is skipped.
- Existing non-empty stores with the wrong vector dimension fail loudly instead
  of mixing incompatible vectors.
- Rekordbox SQLCipher database paths remain out of scope. The product reads the
  exported XML path only.

## Verification Surface

Focused checks:

```bash
uv run pytest -q tests/library/test_ingest.py tests/library/test_excerpt.py
uv run pytest -q tests/library/test_stats_cli.py tests/library/test_models_cli.py
```

Setup/status checks:

```bash
uv run python -m vibemix library models --json
uv run python -m vibemix library ingest --help
```

The active implementation map is
`.planning/research/CODEX-full-product-sweep-map.md`.
