# REKORDBOX CUES/PHRASE vs CUE-DETR — does vibemix already consume the DJ's local structure?

**Date:** 2026-06-03 · **HEAD:** f3fc4964 · **Mode:** read-only analyst
**Question:** Does vibemix ALREADY consume the local cue + phrase/structure analysis Rekordbox/Serato/Traktor store on disk — making CUE-DETR a FALLBACK rather than a requirement?

---

## TL;DR VERDICT

vibemix **does** parse Rekordbox ANLZ **PSSI phrase/structure** (intro/build/breakdown/drop/outro) AND
hot/memory cues from `collection.xml`, AND has full Serato/Traktor/VirtualDJ/EngineDJ cue importers — and
the precedence is correctly **DJ cues → ANLZ phrase → CUE-DETR auto (last)**.

**Correction at current HEAD:** the original "labels are thrown away" conclusion below was stale. `library
ingest` now materializes matched ANLZ phrases into persisted `TrackEntry.cues` (`source="anlz"`) before
writing `library.pkl`, and `sections_for_entry()` maps those cached cues back to `source_detail="pssi"` for
live/drop/section consumers. CUE-DETR remains a fallback for cue-less tracks; the remaining owner-gated item is
the DROP-call voice/accuracy bar, not an ANLZ materialization build.

---

## 1. The Rekordbox import path — WHAT is parsed and stored

Two distinct Rekordbox readers exist, both real:

### (a) `collection.xml` cues — `library/rekordbox.py`
- `_mark_to_cue` (`rekordbox.py:574`) converts each `pyrekordbox.rbxml.PositionMark` → `CuePoint`
  (`rekordbox.py:130`), capturing `name`, `type` (cue/loop/fadein/fadeout/load), `start_s`, `end_s`,
  `number` (1..8 hot cues, -1 memory cues). So **hot cues + memory cues (POSITION_MARK) ARE parsed.**
- `TrackEntry` (`rekordbox.py:165`) stores `title/artist/album/bpm/key/duration/cues/filepath` plus
  `genre/label/rating/play_count/comments/camelot/beatgrid` (TEMPO nodes → `beatgrid:198`).
- **NOT in collection.xml:** PSSI phrase labels. The docstring is explicit — a bare position mark carries
  no build/breakdown semantics (`excerpt.py:165`, T-89-08), so `_label_for_cue` hedges hot-slot-0→intro,
  everything-else→drop.

### (b) ANLZ `.EXT`/`.DAT` — PSSI phrase + PQTZ beatgrid — `library/anlz_ingest.py`
This is the real phrase parser:
- `parse_anlz_bundle` (`anlz_ingest.py:106`) lazily imports `pyrekordbox.anlz.AnlzFile`, reads **PPTH**
  (path), **PSSI** (`anlz_ingest.py:126` — Pioneer phrase/structure), **PQTZ** (`:127` — beatgrid).
- `phrases_from_pssi_entries` (`anlz_ingest.py:250`) + `map_pssi_kind` (`:313`) map PSSI mood+kind →
  `AnlzPhrase` with a real `cue_label` ∈ intro/build/breakdown/drop/outro (test `:62-67` proves the
  mapping), `start_beat/end_beat`, `start_s/end_s` (via `beat_to_time` on the beatgrid), and `confidence`
  (mood-hedged — high mood 0.84, mid 0.56, low 0.42 → dropped below anchor floor).
- `AnlzBeatGrid` (`:44`) stores `times_s/bpms/beat_in_bar` — so **beatgrid IS parsed.**
- `build_anlz_index` (`:163`) → `match_track_to_anlz` (`:174`, basename then suffix) → `anchors_from_anlz`
  (`:194`) emits `CueAnchor`s with `source="anlz"`.

**So: beatgrid YES, hot/memory cues YES, PSSI phrase/structure YES — not "only title+BPM+key".**

## 2. Where the imported data FLOWS — and where it STOPS

Original read-only finding, now corrected by current-source verification:
```
__main__.py:7317  build_anlz_index()        # inside _cmd_library_ingest — OFFLINE CLI subcommand
        ↓ anlz_index=
library/ingest.py:644 / :829  anchors_for_track(track, anlz_index=...) / _match_anlz_for_cache
        ↓
library/ingest.py:831  _materialize_anlz_cues(track, anlz_meta)
        ↓
library/folder_ingest.py:_write_library_cache(...)
        ↓
library.pkl TrackEntry.cues source="anlz"
        ↓
library/section_builder.py:sections_for_entry(...)
```

`_embed_track_cue_anchored` still uses ANLZ anchors to choose ≤80s CLAP windows, but it is no longer the
only sink. `_materialize_anlz_cues()` persists the same structure into the cached `TrackEntry`; section
builders then recover source/detail/confidence from those cues. The remaining gap is not persistence. It is
live voice/product gating: DROP-call speech is still deliberately dormant, and any future spoken structural
line must remain citation-grounded.

## 3. Serato / Traktor / VirtualDJ / EngineDJ — import side EXISTS

`export_serato.py` is export, but there are full **import** sources under `library/sources/`:
- `traktor.py` — `collection.nml`, `_cue_from_node` reads `CUE_V2` (`:134`) → `CuePoint` (hotcue/loop).
- `serato.py` — `database V2` + `.crate` import (`SeratoSource`); cues via Markers2 path.
- `virtualdj.py` — `_cue_from_poi` (`:134`) reads POI cues.
- `sources/engine.py` — `EngineDJSource`, `_cues_by_track` (`:208`).
- `sources/rekordbox.py` — `RekordboxSource` wrapper.

All normalize to the **same `TrackEntry`/`CuePoint`** shape. That means ordinary DJ-authored cues
from Serato/Traktor/VirtualDJ/EngineDJ do not need `_materialize_anlz_cues`; they are already cached
as cue records and can be read by `sections_for_entry()` like Rekordbox XML cues. `_materialize_anlz_cues`
is specifically the Rekordbox ANLZ/PSSI phrase-sidecar bridge: it adds phrase structure only when the
track has no structural DJ cues. If another ecosystem has phrase sidecars beyond cue records, that is a
separate verified gap, not the stale "nothing reaches live" claim.

## 4. The precedence (decision logic) — CUE-DETR is correctly LAST

`excerpt.py::anchors_for_track` (`excerpt.py:71`) implements clean precedence:
1. **DJ cues first** (`:103`) — structural cue/loop marks from XML, `source="dj"`, conf 0.9.
2. **ANLZ phrase second** (`:133`) — `match_track_to_anlz` → `anchors_from_anlz`, `source="anlz"`,
   only when the caller injects an `anlz_index`.
3. **CUE-DETR auto last** (`:154`) — `cue_engine.detect_cues_auto`, `source="auto"`.

And `cue_engine.detect_cues_auto` (`cue_engine.py:164`) itself degrades: CUE-DETR ONNX → on
`CueProducerUnavailable` or empty → dep-free heuristic `cue_detect.detect_cues`.

**So within the library-embedding job, CUE-DETR is already the third-choice fallback — a Rekordbox DJ's
real cues/phrases win.**

---

## VERDICT & B4/O1 PRIORITY IMPLICATION

For a Rekordbox-using DJ, the structural cue intelligence is **available locally, parsed correctly, and
persisted into the shared `TrackEntry.cues` shape**. The old "imported but dark" verdict is false for the
library/cache and section-consumer path: ANLZ phrase anchors survive restart as `source="anlz"` cues and are
read by `sections_for_entry()`. The live co-host still must not auto-speak DROP calls until the owner-gated
accuracy bar lands, and the prompt-level "per-deck phrase grid" wording remains a separate live-framing gap.

**Implication:** B4/O1 (CUE-DETR) can safely **drop priority *for the library/embedding lane*** — a
Rekordbox DJ's own cues already beat it there, and the auto-engine even has a dep-free heuristic fallback
below it, so CUE-DETR is a "nice-to-have for non-Rekordbox / cue-less tracks", not a requirement. **Do not
build a second ANLZ→cue path.** The next live value is verification plus the owner-gated DROP-call accuracy
decision: prove cached ANLZ cues populate the live structure/evidence path, then keep `VIBEMIX_DROP_CALL` off
until Kaan signs the accuracy bar.
