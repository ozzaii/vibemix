# CODEX_READY — Serato Library Reader (the last Universal-Ingest island, B1b)

> Universal Ingest is ~80% done — Codex landed `traktor.py`, `engine.py`, `virtualdj.py` (verified at HEAD `e49b2f63`). **Serato is the only major ecosystem still un-readable** (`library/sources/serato.py` NOT-FOUND) — and it's the **biggest installed base** of the lot. "One-click import your Serato crates + cues into vibemix" is the highest-reach onboarding wedge left. License doc confirms: **Apache-clean, no GPL needed** (Serato format is documented; `triseratops` reference is MPL-2.0 = facts, not code we copy).
> **Owner: Codex A.** Claude read-only. Re-verified at HEAD `e49b2f63`. CRITIQUE L4, LICENSE arsenal row 1, FUTURE B1b.

## Why this one is cheap (half of it is already owned)
The hot-cue half is **free** — we already decode Serato Markers2: `library/export_serato.py:95` `decode_markers2(data)` → `[SeratoCue]`, `:121` `_parse_cue`, `:177` the ID3-GEOB container read. The new work is only the **crate list + track metadata** parse; cues come straight from the file tags we can already read. The collision-free island pattern is proven by the three readers that just landed.

## The pattern to mirror (do NOT re-invent the seam)
`library/sources/base.py:36` `LibrarySource` Protocol — three methods, structural typing (no inheritance needed): `detect() -> bool` (`:48`), `default_paths() -> list[Path]` (`:57`), `iter_tracks() -> Iterable[TrackEntry]` (`:61`). The orchestrator `library/ingest.py::ingest_source` depends only on the Protocol. `sources/__init__.py:11-12` lists concrete sources, imported on demand (never eagerly). **Closest analog: `sources/traktor.py:37` `TraktorSource`** — copy its shape (`__init__(path|None)`, `default_paths`, `detect`, `iter_tracks`, the `_track_from_entry`/`_cue_from_node`/`_location_path` helper decomposition, `TrackEntry`/`CuePoint` construction).

## 1. New module — `library/sources/serato.py` → `SeratoSource`
Serato's on-disk library (documented format, clean-room from the public spec — never copy `triseratops` source):
- **Location:** `~/Music/_Serato_/` (+ per-drive `<volume>/_Serato_/`). `default_paths()` returns these; `detect()` = the dir + a `database V2` file exists.
- **Crates:** `_Serato_/Subcrates/*.crate` — a flat binary of tagged chunks (`otrk` track entries, `ptrk` file-path payloads). Parse the chunk stream (4-byte ASCII tag + 4-byte big-endian length + body) to recover each crate's ordered track file list. Crate name = the filename (sanitized).
- **Track metadata:** the `database V2` file (same tagged-chunk format: `otrk` → `ttyp/pfil/tsng/tart/tbpm/tkey/…`) gives path/title/artist/bpm/key/duration. Where a field is absent, fall back to reading the audio file's tags (you already have a decode path).
- **Cues:** for each track file, read the Serato Markers2 GEOB via the **owned** `export_serato.decode_markers2` (`:95`) → map `SeratoCue` → `CuePoint` (mirror `traktor.py:134 _cue_from_node` shape). Free reuse — do not write a second Markers2 parser.
- Yield `TrackEntry` (numpy-free dataclass, `base.py:21`) exactly as the other readers do, so the whole CLAP/Viber/pill/Earned stack lights up unchanged.
- Per-file/per-crate parse errors are **logged + skipped, never fatal** (match the resumable-ingest discipline in the existing readers).

## 2. Register + CLI
- Add `serato` to the on-demand source list (`sources/__init__.py:11`, same lazy pattern — no eager import).
- Wire into `library ingest` auto-detect (mirror however `engine`/`traktor` were wired in `__main__.py` + `library/ingest.py`; the engine-dj setup path `e49b2f63` is the freshest analog).

## 3. Guardrails
- **Clean-room only:** implement from the documented Serato binary layout; the `triseratops`/`serato-tags` projects are reference *facts*, never copied source (LICENSE doc: this is Apache-clean, no GPL flip needed — keep it that way).
- Reuse `decode_markers2` — do not duplicate cue parsing.
- No new third-party dep (stdlib `struct` + the owned mutagen path already in the `serato` extra). No change to `MusicState`, the embedder, or the citation grammar.
- The library/rekordbox-test rule applies: any test that touches the cache MUST monkeypatch the cache path to a tmp dir (CLAUDE.md gotcha) — never overwrite the real `library.pkl`.

## Acceptance
**SRC (Codex):** `tests/library/sources/test_serato.py` — a tiny synthetic `_Serato_/` fixture (one `database V2` + one `.crate` + one tagged mp3 with a Markers2 GEOB) → `iter_tracks()` yields the right `TrackEntry` set with cues recovered via `decode_markers2`; `detect()` true only with the dir present; malformed chunk → skipped not raised. Round-trip sanity: `encode_markers2`→`decode_markers2` already covered; reuse it. `clean-checkout`/import gate green; ruff clean.
**LIVE (optional, Claude):** point `library ingest` at a real `~/Music/_Serato_/` → crates + cues land, vibe-search returns Serato tracks.
**Proof tiers:** SRC is sufficient to land (parser is deterministic); LIVE is a bonus on a real Serato library.

## Gate
**`clean-checkout` / import gate** (new module must import on a fresh clone — commit with its `sources/__init__.py` + CLI wiring). No grounding-review (doesn't touch what the co-host SAYS). Effort ~2d (crate + database V2 parse; cues are free).
