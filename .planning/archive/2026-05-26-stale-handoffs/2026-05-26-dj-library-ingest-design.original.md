# DJ-Library Ingest — design spec

> **Status: design, approved 2026-05-26.** Build routes through GSD (per CLAUDE.md).
> The CLAP embedder + curator wiring is a SEPARATE session's lane — this spec does
> NOT touch `clap_engine.py`, `docs/clap-engine.md`, or the Viber/curator code.

## User story

"I install vibemix, tap once, it finds my DJ library, and a few minutes later my
tracks are ready — embedded and searchable — with no folder-picking and no manual
analysis."

## Scope

**In (v1):**
- Auto-detect the user's DJ library (Rekordbox first; Serato + Traktor next).
- Parse clean, human-curated metadata: musical key, BPM, beatgrid, hot/memory cues,
  genre, rating, comments.
- Cut **cue-anchored ≤80s excerpts** per track (anchored on the DJ's real cues;
  fall back to the auto-cue engine's `CueAnchor`s when a track is un-cued).
- Embed each track **on-device** via the staged `clap_engine` (512-dim) — no upload,
  no server RPC. Store in the existing sqlite-vec library store.
- A **real file watcher**: watch the library index files, diff on change, re-embed
  new/changed tracks.

**Out (deferred):**
- djay Pro (closed DB), public-catalog/Beatport discovery, server-side embedding
  (on-device won — the upload problem the old plan worried about is moot).

## Architecture (new, disjoint modules)

```
library/
  sources/
    base.py        # LibrarySource protocol: detect() -> bool; iter_tracks() -> Iterable[TrackEntry]
    rekordbox.py   # EXTEND existing library/rekordbox.py: add beatgrid/genre/rating/cue-type reads
    serato.py      # NEW — serato-tools (GEOB markers) + mutagen TKEY for key
    traktor.py     # NEW — collection.nml (stdlib xml.etree); CUE_V2 START is in SECONDS, filter TYPE="4" grid
  excerpt.py       # NEW — TrackEntry + cues -> list of ≤80s mixable audio excerpts
  ingest.py        # NEW — orchestrator: detect source -> iter tracks -> excerpt -> clap_engine embed -> store
  watcher.py       # NEW — watchdog Observer on index files -> diff -> enqueue changed tracks
```

## The CueAnchor seam (shared — already shipped)

Excerpt anchoring consumes `library/cue_types.py::CueAnchor` (from the shipped
auto-cue engine). DJ-library sources emit `source="dj"` anchors from the parsed
cues; un-cued tracks fall back to `detect_cues()` (`source="auto"`). `excerpt.py`
is the single consumer that turns anchors into audio windows. **Do not modify
`cue_types.py` or `cue_detect.py`** — they are the cue-engine session's artifacts.

## Data flow

```
one-tap → detect installed DJ app (path probe)
        → LibrarySource.iter_tracks()  (clean metadata, key→Camelot via deterministic table)
        → per track: CueAnchors (dj | auto) → excerpt.py cuts ≤80s windows
        → clap_engine.embed_audio_file/bytes → 512-dim L2 vector
        → store in library.db (sqlite-vec) + content-hash cache
        → watcher: index file changes → diff → re-embed delta
```

## Reliability / honesty rules

- **Coverage, not correctness, is the risk:** un-analyzed tracks have no key/grid/cue
  → XML/tag-first, DSP-fallback per track. Never silently leave a track anchor-less.
- **Rekordbox watcher is semi-live:** `collection.xml` is a manual export; watch the
  export file + nudge the user to re-export. Serato/Traktor are live.
- **Trust the audio (Invariant #3):** never fabricate metadata; missing fields stay
  missing, surfaced honestly.

## Cross-session collision boundaries

- **Owned by other sessions — DO NOT TOUCH:** `clap_engine.py`, `docs/clap-engine.md`
  (CLAP ship session); `discovery.py`, `energy.py`, `sequencer.py`,
  `export_rekordbox.py` (Set-Builder session); `cue_types.py`, `cue_detect.py`
  (cue-engine session).
- **Shared read-only seams:** `clap_engine` (embed call), `cue_types.CueAnchor`,
  `TrackEntry`.
- Check `git status` + existing files before creating anything.

## Open dependency

- **Store dim (1536→512):** the CLAP session owns the `EMBEDDING_DIM` flip + cache
  rebuild. Ingest stores whatever `clap_engine` returns; the dim change lands when
  the CLAP wiring phase ships. Coordinate — do not flip the dim from this lane.

## Build path

Routes through GSD (`/gsd-plan-phase` or `/gsd-mvp-phase`) — this doc is the WHAT;
GSD produces the HOW (PLAN.md, atomic commits). No code is written by this spec.
