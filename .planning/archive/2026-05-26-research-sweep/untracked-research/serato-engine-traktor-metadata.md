# Serato / Engine DJ / Traktor — READ + WRITE Feasibility for the Viber Agent

> **Goal:** can vibemix's Viber agent **read** (grounding spine: key/BPM/beatgrid/cues) and, where safe, **write back** (e.g. agent-set hot cues, agent-built crates/playlists) across the three non-Rekordbox ecosystems?
> **Scope note:** the READ survey for Serato + Traktor already exists in [`dj-ecosystem-metadata.md`](./dj-ecosystem-metadata.md) (covers GEOB/NML field maps, key notation, cue-anchor reliability). **This doc does NOT repeat that** — it adds (a) **Engine DJ** in full (missing entirely from that doc), (b) a deep **WRITE feasibility + corruption-risk** treatment for all three, and (c) a **cross-ecosystem abstraction model** the agent can target. Read both together.
> Date: 2026-05-26. macOS paths.

---

## TL;DR — read/write verdict per ecosystem

| Ecosystem | Storage | READ | WRITE feasibility | WRITE risk | Best lib | Agent verdict |
|---|---|---|---|---|---|---|
| **Serato** | GEOB ID3 in-file + `_Serato_/` crates | mature | **YES, real** (cues/grid/color/crates) | **Medium** — in-file edit; mutagen-safe but no atomic txn; backup mandatory | `serato-tools` / `bvandercar-vt/serato-tools` (Py3.12) | **R/W candidate** — crates first (low risk), cues later |
| **Engine DJ** | `Database2/{m,p}.db` SQLite (+ zlib-Qt BLOBs) | medium (BLOB parse) | **YES but hard** — Denon *prohibits schema edits*, blesses row writes + ATTACH side-db | **High** — must respect schema version, never run while Engine open, p.db BLOB encoding is brittle | `libdjinterop` (C++, no PyPI), `piratengine` (Py, early) | **READ-first; WRITE via libdjinterop only, or write crates/playlists rows + ATTACH our own side-db** |
| **Traktor** | single `collection.nml` XML (+ writes to file tags) | trivial (XML) | **YES, easy** (rewrite XML; Traktor auto-backs-up) | **Low** — plain XML, atomic file replace; Traktor keeps dated backups | stdlib `xml.etree` (preferred) / `traktor-nml-utils` | **R/W candidate — cheapest write path of the three** |

**Headline:** Write order by risk/reward = **Traktor (easy) → Serato (medium) → Engine (hard, gated)**. For v1, ship **READ everywhere** + **WRITE only the low-risk surfaces**: build/append **crates (Serato), playlists (Engine via blessed rows), playlist NODES (Traktor)** rather than touching per-track cue BLOBs. Per-track cue *writing* is feasible everywhere but is the corruption-prone path — gate it behind explicit user opt-in + mandatory backup.

---

## 1. Engine DJ (Denon / inMusic — SC/Prime hardware + Engine DJ Desktop)

> The gap-filler. Engine is the standalone-CDJ ecosystem (Denon SC5000/SC6000, Prime 4) — a real chunk of the non-laptop club/mobile market, and the one with the *most explicit official 3rd-party-tool guidance* (which doubles as a write-rulebook).

### 1.1 Where it lives
- Root: `<drive>/Engine Library/Database2/` (on the computer **and** on each USB/SSD prepared for the players — the players read the on-drive copy directly).
- **`m.db`** — *metadata* DB: `Track`, `Crate`, `Playlist`, `PlaylistEntity`, `Historylist`, `AlbumArt`, `Information`. Holds title/artist/album/genre/bpm/key/path/rating + library structure.
- **`p.db`** — *performance* DB: `PerformanceData` table = the analysis (beatgrid, hot cues, loops, waveforms). **The `id` ties back to `m.db.Track.id`, but the DB UUIDs differ** (each .db has its own UUID in `Information`).
- Companion `*.db-journal` / `-wal` rollback files. Pre-2.0 used a flat `Engine Library/m.db`; **2.0+ moved everything under `Database2/`** and the migration is the famous "library is corrupt after 2.0 upgrade" support thread.
- **`Information` table** in *both* DBs carries `schemaVersionMajor/Minor/Patch` — **you MUST read this and refuse to write if it's a version you don't recognise** (see §1.4).

### 1.2 Per-track data formats (the hard part)
`PerformanceData` columns are **BLOBs in Qt `qCompress` framing**: a **4-byte big-endian uint32 uncompressed-length prefix, then a zlib stream** (this is exactly `QByteArray` `qCompress`/`qUncompress`). **Exception: the `loops` column is uncompressed.** Decode = read 4-byte length, `zlib.decompress(rest)`, sanity-check length.

- **`beatData`** — sample rate (f64), track length in samples (f64), a "set" flag byte, then **default** + **adjusted** beatgrids. Each beatgrid is a list of markers: `sampleOffset (f64 LE)`, `beatIndex (i64 LE)`, `beatsToNextMarker (u32 LE)`, `unknown (u32 LE)`. First marker is conventionally "beat -4", last "beat N+1". BPM derivable: `SR * 60 * (lastBeatIdx - firstBeatIdx) / (lastOffset - firstOffset)`.
- **`quickCues`** — 8 hot-cue repeating frames: `labelLen (u8; 0 = unset)`, `label (chars)`, `position (f64, in SAMPLES)`, `color (ARGB bytes)`. Plus a trailing main-cue position (f64) + override flag + default position.
- **`loops`** (uncompressed) — `numLoops (u8 = 8)`, 7 pad bytes, then 8 frames: `labelLen`, `label`, `startSample (f64 LE)`, `endSample (f64 LE)`, `startSetFlag (u8)`, `endSetFlag (u8)`, `color (ARGB)`.
- **`trackData`** — sample rate (f64), length (u64 samples), avg loudness (f64 0–1), analyzed key (u32).
- **Waveforms** (`highResolutionWaveFormData` / `overviewWaveFormData`) — not needed for us; ignore.
- **Cue positions are in SAMPLES** here (Rekordbox/Traktor use ms or seconds) — divide by sample rate to get seconds before they become CLAP excerpt anchors.

### 1.3 Parsers / libraries
- **`libdjinterop`** (`xsco/libdjinterop`, **LGPL-3.0, C++**) — *the* canonical, best-maintained Engine library. **Reads AND writes** track metadata, beat grids, hot cues, loops, waveforms, crates, playlists. Covers **Engine DJ OS 1.0.3 → 4.3.3** and **Engine Desktop 1.0.1 → 4.3.0** (actively tracks new schema versions — this is the killer feature, it abstracts the version churn for you). Used by **Mixxx** for its "Export to Engine Prime" feature. Not-yet-implemented: album art, play history. **No Python binding ships** — integration = FFI/pybind11 wrapper, or shell to a tiny C++ helper, or port the read logic (Engine read is well-documented enough to reimplement in pure Python for our READ-only needs).
- **`piratengine`** (`ssabug/piratengine`, Python) — open-source Denon-hardware tooling; first goal is "simple tools to interact with `m.db`". **Early/low maturity**, but it's a pure-Python starting point for `m.db` (metadata) reads.
- **Mixxx wiki "Engine Library Format"** — the authoritative *reverse-engineering doc* (schema + BLOB byte layouts above come from it). This is your spec if you reimplement in Python.
- **Lexicon** (commercial DJ-library manager) reads/writes Engine — proves bidirectional sync is viable in practice, not a parser we can use.

### 1.4 WRITE feasibility + risk — **the gated one**
Denon published explicit 3rd-party-tool guidance (Engine DJ v3.0 KB). It is effectively a write-contract:
- **READ is allowed.** **WRITE is "not officially supported"** but tolerated under rules.
- **HARD RULE: never edit the schema** of any `Database2/*.db`. "Doing so will cause Engine DJ to refuse to load the database." → We may `INSERT`/`UPDATE` rows in existing tables (e.g. add a `Crate`, a `Playlist`, `PlaylistEntity` rows) but **must not add/drop/alter columns or tables**.
- **For our own extra data, Denon's blessed pattern is: create a SEPARATE SQLite db in a subfolder of `Database2/` and `ATTACH DATABASE` Engine's files at runtime** — never mutate theirs in place for custom fields. (Bind tracks by `Track.{originId, originDatabaseUuid}`; bind playlists by playlist path as the natural key.)
- **Never write while Engine DJ is running** — simultaneous access = corruption (their own corruption-prevention KB). Detect the app / lock; operate only on a quiesced library or a copy.
- **Engine "reserves the right to drop any data that doesn't conform to its schema"** on upgrade — so anything we write into their tables is best-effort, not durable across their migrations.
- **p.db BLOB writes (cues/grid) = highest risk:** the Qt-zlib framing + exact byte layout must be reproduced perfectly or the player silently drops or mis-renders the analysis. **Do NOT hand-roll p.db BLOB writes** — if we ever write Engine cues, do it **through `libdjinterop`** (it owns the version-correct encoder) and **never** our own struct-packer.
- **Risk rating: HIGH.** Mitigations: version-gate on `Information.schemaVersion*`; operate on a copied library or with Engine closed; metadata/crate/playlist row writes only for our own code; cue/grid writes only via `libdjinterop`; mandatory backup of the whole `Database2/` folder first.

**Agent verdict:** READ via pure-Python reimpl of the Mixxx-documented format (m.db rows + p.db BLOB decode) OR `piratengine` for m.db. WRITE limited to **building a playlist/crate** (blessed row inserts) for v1; defer per-track cue writes to a `libdjinterop`-backed path behind explicit opt-in.

---

## 2. Serato — WRITE deep-dive

> READ field map (GEOB tags `Serato Markers2`/`BeatGrid`/`Autotags`/`Overview`, FLAC/Ogg Vorbis-comment + MP4 `----` variants, `TKEY` for key, `~/Music/_Serato_/` crates) is fully covered in `dj-ecosystem-metadata.md` §1. Not repeated.

### 2.1 What we can WRITE — yes, this is real
`serato-tools` / `bvandercar-vt/serato-tools` (Python 3.12+, actively committed, `mutagen`-backed) is a genuine **read+write** toolkit:
- **Hot cues + loops** → `TrackCuesV2` (`track_cues_v2.py`): add/edit cue position, name, color; `set_track_color()`.
- **Beatgrid** → `track_beatgrid.py`: even does **dynamic beatgrid analysis** and writes it to the `Serato BeatGrid` tag; can **snap cues to the nearest beat** (1/16, 1/8, 1/4 tolerance).
- **BPM/gain** → `track_autotags.py` (`Serato Autotags`).
- **Crates / smart crates** → `Crate` class (add/remove tracks, create crates), smart-crate rule editing.
- **Library `database V2`** → `DatabaseV2` (rename files, update metadata).
- File formats: MP3, FLAC, M4A, AIFF (via mutagen).

### 2.2 Risk profile — **MEDIUM** (in-file, not a side-DB)
- **Serato data lives INSIDE the audio file** (GEOB ID3 / Vorbis / MP4 atom). A write = rewriting the file's tag chunk via mutagen. That is well-trodden (mutagen is battle-tested) but:
  - **No transaction / atomicity** at the Serato-format level — a crash mid-write or a format-edge-case (odd ID3 version, AIFF chunk quirks, FLAC base64-LF-every-72-chars rule) can leave a track Serato can't read → cues vanish for that track.
  - The library's own README explicitly says: **"Recommended to make a backup of the database file elsewhere, before modifying via this package, in case an unforeseen bug appears."** Treat that as mandatory and extend it to the *audio files* we touch.
  - Mixxx has a tracked issue ("Serato cue import: risk of losing data") about round-tripping Serato cues — confirms the marker format has lossy edge cases. Our writer must **preserve unknown/passthrough bytes** rather than re-emitting only fields we understand.
- **Crate writes are LOW risk** — `.crate` files in `_Serato_/` are separate sidecar files; creating/appending a crate doesn't touch audio files and is easy to back up/delete. **This is the safe write surface to ship first.**
- Two writers to the same file = corruption: **never write while Serato DJ is open** on that library.

**Agent verdict:** **Crate-building first** (low risk, high value — "agent built you a crate"). **Per-track cue/color writes** are feasible and the lib supports them, but ship behind explicit opt-in + auto-backup of each file (copy original tag blob first) + unknown-byte passthrough.

---

## 3. Traktor — WRITE deep-dive

> READ field map (`collection.nml` ENTRY/INFO/TEMPO/MUSICAL_KEY/CUE_V2, Open-Key vs chromatic key, `START` in SECONDS, TYPE 4=grid) is fully covered in `dj-ecosystem-metadata.md` §2. Not repeated.

### 3.1 What we can WRITE — easiest of the three
- **It's one plain XML file.** Writing = parse → mutate DOM → serialize → **atomic replace** (write temp, `os.replace`). No binary, no compression, no in-file tag surgery.
- Add a `<PLAYLIST>`/`<NODE>` subtree (agent-built playlist referencing existing entries by their `LOCATION` key) — clean, append-only, trivially reversible.
- Add/edit `CUE_V2` elements on an `<ENTRY>` (cue/loop/grid) — also straightforward XML; remember `START`/`LEN` are **seconds (float)**, `HOTCUE` is the pad slot.
- `traktor-nml-utils` exists (xsdata dataclasses, read+write) but is **low-maintenance and chokes on newer attrs** (`NML:INDEXING` etc.) — for writing, **hand-rolled `xml.etree` is more robust** because it ignores/preserves attributes it doesn't model instead of dropping them.

### 3.2 Risk profile — **LOW**
- **Traktor keeps automatic, dated backups** of the collection (`Collection<YYYY>y<MM>m<DD>d_<HH>h<MM>m_<SS>s.nml`) — there's a known restore path, so a bad write is recoverable by the user out of the box. We should *also* snapshot before writing.
- **Caveat — preserve, don't regenerate:** Traktor also writes most performance data **into the file tags themselves**, and re-serializing the whole NML with a naive parser risks dropping attributes/elements you didn't model (genre, ranking, AUDIO_ID, color). **Use a surgical DOM edit (mutate only target nodes, keep everything else byte-for-byte where possible), never a "round-trip through my dataclasses" rewrite.** Validate the entry count + a checksum of untouched nodes before/after.
- `AUDIO_ID` is Traktor's content fingerprint used to dedupe/propagate cues across duplicate files — **don't fabricate or alter it**; only reference it.
- **Never write while Traktor is open.**

**Agent verdict:** **R/W candidate — cheapest write path.** Ship **playlist NODE creation** + (opt-in) `CUE_V2` cue insertion, both via surgical `xml.etree` edit with snapshot-before-write.

---

## 4. Cross-ecosystem abstraction — the model the agent targets

The agent should never branch on ecosystem in its logic. Put a **per-ecosystem adapter** behind one neutral model (mirrors how the Rekordbox path already feeds the `library/` spine + cue-anchored CLAP excerpts).

### 4.1 Common data model (read side)
```python
# library/ecosystem/model.py  (sketch — NOT written, repo is read-only here)
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class Ecosystem(str, Enum):
    REKORDBOX = "rekordbox"; SERATO = "serato"; ENGINE = "engine"; TRAKTOR = "traktor"

class CueKind(str, Enum):
    HOT = "hot"; MEMORY = "memory"; LOOP = "loop"; GRID_ANCHOR = "grid_anchor"; LOAD = "load"

@dataclass
class Cue:
    pos_s: float                 # NORMALIZED to SECONDS (Engine=samples/SR, Traktor=already s, Serato/RB=ms/1000)
    kind: CueKind
    index: int | None = None     # pad slot (-1/None = unbound grid anchor)
    name: str | None = None
    color_rgb: tuple[int,int,int] | None = None   # strip alpha; ARGB->RGB for Engine/Serato
    length_s: float | None = None                 # loops only

@dataclass
class BeatGridMarker:
    pos_s: float
    bpm: float | None = None     # segment BPM from this anchor

@dataclass
class TrackMetadata:
    source: Ecosystem
    source_id: str               # RB TrackID / Serato file path / Engine Track.id / Traktor LOCATION key
    path: str | None             # resolved absolute file path
    title: str | None; artist: str | None
    bpm: float | None            # prefer analyzed/adjusted over file-tag bpm
    key_camelot: str | None      # ALL notations normalized -> Camelot (Open-Key/chromatic/TKEY map deterministically)
    duration_s: float | None
    genre: str | None = None; label: str | None = None
    rating_0_5: int | None = None; color_rgb: tuple[int,int,int] | None = None
    comment: str | None = None; play_count: int | None = None
    cues: list[Cue] = field(default_factory=list)
    grid: list[BeatGridMarker] = field(default_factory=list)
    raw: dict = field(default_factory=dict)   # passthrough of unparsed/unknown fields -> CRITICAL for safe write-back
```

### 4.2 Adapter protocol (read + guarded write)
```python
class LibraryAdapter(Protocol):
    ecosystem: Ecosystem
    def detect(self) -> bool: ...                          # is this library present on this machine?
    def is_app_running(self) -> bool: ...                  # MUST be False before any write
    def read_tracks(self) -> Iterable[TrackMetadata]: ...
    # WRITE is split by risk tier so the agent picks the safe surface by default:
    def write_playlist(self, name, track_ids) -> WriteResult: ...   # LOW risk everywhere (crate/playlist/NODE)
    def write_cues(self, track_id, cues: list[Cue]) -> WriteResult: ...  # GATED: opt-in + backup + unknown-byte passthrough
    def backup(self) -> Path: ...                          # snapshot before any write; returns restore handle
```

### 4.3 Normalization rules (the load-bearing details)
- **Time → seconds, always.** Engine cue/loop positions are **samples** (÷ SR); Traktor `CUE_V2 START` is **seconds**; Serato/Rekordbox are **ms** (÷1000). The model stores seconds; CLAP excerpt anchoring consumes seconds.
- **Key → Camelot, always.** Traktor Open-Key (`10m`) ↔ Camelot is a fixed table; Traktor `MUSICAL_KEY VALUE` 0–23 chromatic → Camelot deterministic; Serato/RB `TKEY` strings → Camelot table. LLM never computes keys (cardinal rule already in CLAUDE.md).
- **Color → RGB, strip alpha.** Engine + Serato store **ARGB**; drop the alpha byte. Rekordbox `0xRRGGBB`; Traktor `INFO@COLOR` index.
- **Cue-kind filter for embedding anchors:** drop `GRID_ANCHOR`/`LOAD` (auto, not musical); keep `HOT`/`MEMORY`/`LOOP` — those are the DJ's deliberate intro/breakdown/drop markers that make good CLAP excerpt centers.
- **`raw` passthrough is the write-safety keystone.** On read, stash every byte/attr we didn't model into `raw`; on write-back, re-emit `raw` untouched. This is what prevents the "Serato cue round-trip loses data" / "naive NML rewrite drops attributes" failure class.

### 4.4 Universal write-safety checklist (applies to all four ecosystems)
1. **Refuse if the DJ app is running** (lock/process check) — concurrent access is the #1 corruption cause everywhere.
2. **Backup before write** — copy the file/DB/crate; return a one-click restore handle. (Traktor & Engine self-backup too, but don't rely on it.)
3. **Version-gate** — Engine: check `Information.schemaVersion*`; Serato: tolerate ID3 version variance; refuse unknown majors.
4. **Never edit schema** (Engine hard rule) / **never re-encode unknown bytes** (Serato/Engine BLOBs) / **surgical DOM edit only** (Traktor).
5. **Prefer the side-channel** — Engine: ATTACH our own db for custom data; Serato: write `.crate` sidecars not audio files when possible; Traktor: append NODE not rewrite ENTRY when possible.
6. **Default the agent to LOW-risk writes** (playlists/crates). Cue/grid writes are opt-in, per-track, backed-up, and (Engine) routed through `libdjinterop`, never a hand-rolled BLOB packer.

---

## Sources
- Engine Library format (schema + BLOB byte layouts): https://github.com/mixxxdj/mixxx/wiki/Engine-Library-Format
- Denon official 3rd-party DB tool guidance (write-contract, schema-edit prohibition, ATTACH pattern): https://support.denondj.com/en/support/solutions/articles/69000834165-engine-dj-v3-0-support-for-third-party-database-tools , https://enginedj.com/kb/solutions/69000834165/engine-dj-v3-0-support-for-third-party-database-tools
- Engine corruption-prevention KB: https://support.denondj.com/en/support/solutions/articles/69000815206-engine-dj-fixing-and-preventing-engine-library-corruption
- `libdjinterop` (canonical Engine read/write C++ lib, OS 1.0.3–4.3.3 / Desktop 1.0.1–4.3.0, LGPL-3.0): https://github.com/xsco/libdjinterop
- `piratengine` (Python Denon m.db tooling, early): https://github.com/ssabug/piratengine
- Mixxx ↔ libdjinterop "export to Engine Prime": https://github.com/mixxxdj/mixxx/pull/2753
- Serato write lib (`bvandercar-vt/serato-tools`, Py3.12, cues/grid/crates/db, backup warning): https://github.com/bvandercar-vt/serato-tools , https://pypi.org/project/serato-tools/
- Serato GEOB format docs (Holzhaus): https://github.com/Holzhaus/serato-tags , https://homepage.ruhr-uni-bochum.de/jan.holthuis/reversing-seratos-geob-tags.html
- Serato cue round-trip data-loss risk (Mixxx): https://github.com/mixxxdj/mixxx/issues/11530
- Traktor NML write tooling + AUDIO_ID cue propagation + backup advice: https://github.com/pestrela/music/blob/master/traktor/tools_traktor/README.md
- Traktor collection backup/restore (NI official): https://support.native-instruments.com/hc/en-us/articles/209590729-How-to-Restore-the-TRAKTOR-Track-Collection-from-a-Backup
- Traktor NML parser lib + fixture: https://github.com/wolkenarchitekt/traktor-nml-utils , https://github.com/wolkenarchitekt/traktor-nml-utils/blob/master/tests/fixtures/collection.nml
- Cross-ecosystem storage overview: https://www.digitaldjtips.com/dj-software-secrets/
