# Phase 89: DJ-Library Ingest (Rekordbox MVP slice) — Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Source:** Design spec (`docs/superpowers/specs/2026-05-26-dj-library-ingest-design.md`) + this-session research

<domain>
## Phase Boundary

**MVP slice = Rekordbox-only, end-to-end walking skeleton.** Prove the full ingest
vertical on ONE source: detect the user's Rekordbox library → parse clean metadata
from `collection.xml` → cut cue-anchored ≤80s excerpts → embed on-device via the
staged `clap_engine` → store in the existing sqlite-vec library store.

**Explicitly deferred to follow-up phases (90, 91):** Serato + Traktor source
adapters; the real file watcher (auto re-embed on library change).
</domain>

<decisions>
## Implementation Decisions (LOCKED)

### Discovery
- DJ-library-first: detect a Rekordbox `collection.xml` (the standard File → Export
  Collection in xml format). Do NOT open the SQLCipher `master.db` (CI grep-gated as
  unused; XML is strictly sufficient — confirmed in research).
- No full-disk scan, no manual folder-picking in this slice.

### Metadata parse (extend existing `library/rekordbox.py`)
- Read per track: title, artist, album, BPM (`AverageBpm`), musical key (`Tonality`,
  classical notation `Am`/`F#m`) → convert to Camelot via the existing deterministic
  table in `state/harmonics.py` (the LLM never computes keys), duration, file path,
  hot cues (`Num` 0–7) + memory cues (`Num`=-1).
- ALSO add the currently-unread high-value fields surfaced by research: TEMPO
  beatgrid nodes, Genre, Label, Rating, PlayCount, Comments. (Cue color is NOT
  available via pyrekordbox 0.4.4 — out of scope.)
- Coverage is the risk, not correctness: un-analyzed/un-cued tracks have no
  key/grid/cue. XML-first, DSP-fallback per track. Never silently leave a track
  anchor-less. Missing fields stay honestly missing (Invariant #3 "trust the audio").

### Excerpt cutting (`library/excerpt.py` — NEW)
- Consume `library/cue_types.py::CueAnchor` (shipped by the cue-engine session).
- DJ cues → `source="dj"` anchors; un-cued tracks fall back to `detect_cues()`
  (`source="auto"`). `excerpt.py` turns anchors into ≤80s mixable audio windows.

### Embedding (on-device, via staged `clap_engine`)
- Call the staged `library/clap_engine.py` (laion_clap 630k-fusion, 512-dim,
  deterministic). Mean-centering is mandatory downstream (CLAP is anisotropic).
- Embedder runs locally — no server upload, no RPC.

### Storage
- Store vectors in the existing sqlite-vec library store + content-hash cache
  (resumable, per-file errors logged + skipped, never fatal — same posture as the
  current `embed-folder` path).

### CLI
- A `library ingest` (or extend the existing embed-folder entry) command that runs
  the Rekordbox detect → parse → excerpt → embed → store pipeline.

## Claude's Discretion
- Module layout under `library/sources/` (base protocol + rekordbox source), exact
  CLI subcommand naming, progress reporting shape.
</decisions>

<canonical_refs>
## Canonical References — read before planning/implementing

### Design + research (this session)
- `docs/superpowers/specs/2026-05-26-dj-library-ingest-design.md` — the full design.
- `.planning/research/rekordbox-metadata-unlock.md` — EXACTLY what `collection.xml`
  exposes, what `rekordbox.py` already parses vs leaves on the table.
- `.planning/research/clap-engine-deep-dive.md` — CLAP engine decisions.
- `docs/clap-engine.md` — the staged engine contract (READ-ONLY — another session owns it).

### Code seams
- `src/vibemix/library/rekordbox.py` — existing parser to EXTEND.
- `src/vibemix/library/clap_engine.py` — embed seam (READ-ONLY — do not modify).
- `src/vibemix/library/cue_types.py` — `CueAnchor` (READ-ONLY — cue-engine session).
- `src/vibemix/library/embed.py` — existing `LibraryEmbedder`/`embed-folder` flow + content-hash cache to mirror.
- `src/vibemix/state/harmonics.py` — deterministic Camelot table.
</canonical_refs>

<scope_fence>
## DO NOT TOUCH (concurrent sessions own these)
- `library/clap_engine.py`, `docs/clap-engine.md` (CLAP ship session)
- `library/cue_types.py`, `library/cue_detect.py` (cue-engine session)
- `library/discovery.py`, `library/energy.py`, `library/sequencer.py`,
  `library/export_rekordbox.py` (Set-Builder session)
- The `EMBEDDING_DIM` flip (1536→512) — owned by the CLAP wiring session. Store
  whatever `clap_engine` returns; do NOT flip the dim from this phase.
- Do NOT refresh `.planning/codebase/orphans.csv` unless the integration audit demands it.

## Invariants (test-enforced)
Single-writer (#1), citation grounding (#2), trust-the-audio (#3), one socket (#4) —
all hold by zero-touch; this phase adds NEW library-side files + extends `rekordbox.py`.
</scope_fence>

<deferred>
## Deferred Ideas
- Serato adapter (serato-tools GEOB + mutagen TKEY) → Phase 90.
- Traktor adapter (collection.nml, stdlib xml.etree; CUE_V2 START in SECONDS) → Phase 90.
- Real file watcher (watchdog on index files → diff → re-embed delta) → Phase 91.
- djay Pro — out (closed DB, no parser).
</deferred>

---

*Phase: 89-dj-library-ingest · Context gathered 2026-05-26 (MVP Rekordbox slice)*
