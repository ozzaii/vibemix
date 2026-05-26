# DJ Ecosystem Metadata — Offline Ingest Survey (non-Rekordbox)

> Research for vibemix's "DJ-library-first" ingest. The DJ's software already holds hand-curated key/BPM/beatgrid/cues — we read that as the grounding spine plus cue-anchored excerpts for CLAP. Rekordbox is researched separately; this covers **Serato DJ, Traktor Pro, djay Pro**. macOS paths.
> Date: 2026-05-26.

---

## TL;DR ranked table

| Ecosystem | Where stored | Key + BPM + Cues available? | Parse difficulty | Python lib | v1 verdict |
|-----------|--------------|------------------------------|------------------|------------|------------|
| **Serato DJ** | GEOB ID3 tags *inside the audio file* (MP3/AIFF), Vorbis comments (FLAC/Ogg), MP4 `----` atoms (M4A); crates in `~/Music/_Serato_/` | Yes (all 3) — cues+loops+beatgrid+BPM+gain in `Serato Markers2`/`BeatGrid`/`Autotags`; **key not in GEOB** (read from standard `TKEY` ID3 frame) | Medium — binary blobs, but **fully reverse-engineered + documented** | `serato-tools` (PyPI, **actively maintained, v4.0.1 Feb 2026, Py3.12+**) + `Holzhaus/serato-tags` docs | **SUPPORT (do 2nd, after Rekordbox)** |
| **Traktor Pro** | Single XML `collection.nml` (NOT in audio files) | Yes (all 3) — `MUSICAL_KEY`, `TEMPO BPM`, `CUE_V2` (grid+cue+loop) | **Easy** — clean XML, fully open | `traktor-nml-utils` (PyPI) **OR just stdlib `xml.etree`** | **SUPPORT (do 3rd) — or trivially even 2nd given XML ease** |
| **djay Pro** | Proprietary SQLite "djay Media Library" in `~/Music/djay/` + analysis in Group Container; **cues/loops NOT in audio files** | Yes internally, but schema **undocumented/closed**; key+BPM only sometimes written to file tags | **Hard** — closed SQLite schema, no reverse-eng docs, version-churn risk | None | **SKIP for v1** (revisit via OneLibrary export) |

### Headline recommendation
**Coverage order: Rekordbox → Serato → Traktor → (defer djay).**
Serato is second because it is the #1 DJ platform by market share AND has a mature, actively-maintained Python parsing library — best market×reliability product. Traktor is third only by smaller share; technically it is the *easiest* parse of all three (plain XML), so it is cheap to add and a strong "round out the big 3" follow-on. djay is skipped for v1: its library is a closed, undocumented SQLite DB with no parsing library and high schema-churn risk; the cleaner future path is its **OneLibrary** export (a standardized DJ-library format djay co-developed with AlphaTheta/Pioneer) rather than poking the private DB.

---

## 1. Serato DJ (Pro / Lite)

### Where stored
Serato writes its data **into the audio files themselves** (so a copied file carries its cues), with format-specific containers:

| File format | Container | Example field name |
|-------------|-----------|--------------------|
| MP3, AIFF | ID3v2.4 **GEOB** (General Encapsulated Object) frames | `Serato Markers2`, `Serato BeatGrid`, `Serato Autotags`, `Serato Overview`, `Serato Analysis` |
| FLAC, Ogg | `VORBIS_COMMENT` block, base64 (no padding, LF every 72 chars) | `SERATO_MARKERS_V2`, `SERATO_BEATGRID` (Ogg lowercase: `serato_markers2`) |
| MP4 / M4A / AAC | custom MP4 `----` atom, mean `com.serato.dj`, base64 | `----:com.serato.dj:markersv2` |

Library/crate state also lives on disk:
- `~/Music/_Serato_/` — crate files (`.crate`), `database V2` (the library DB), `Subcrates/`, smart crates.
- Each drive with Serato-managed tracks also gets its own `_Serato_` folder at the volume root.

### Fields available
- **Hot cues + saved loops** → `Serato Markers2` (and legacy `Serato Markers_`): per-cue **position (ms), color (RGB), name, type, index**. Loops add start+end. — human-set.
- **Beatgrid** → `Serato BeatGrid`: anchor markers + BPM segments. — auto-analyzed (editable).
- **BPM + autogain** → `Serato Autotags`. — auto (BPM editable).
- **Waveform overview** → `Serato Overview` (not needed for us).
- **Version stamp** → `Serato Analysis`.
- **Musical key** → NOT a Serato GEOB tag. Serato reads/writes the **standard `TKEY` ID3 frame** (and equivalents). Read via mutagen directly. — auto-analyzed or Mixed-In-Key-set.
- **Track color, comments, rating, play count, genre** → standard ID3/Vorbis/MP4 tags (mutagen), plus Serato's own color via tags.

### Parseability (Python)
- **Best-documented of the three.** Jan Holthuis (`Holzhaus/serato-tags`) reverse-engineered and publicly documented every major GEOB tag (`docs/fileformats.md`, `docs/`); Mixxx adopted the same format docs in its wiki.
- **`serato-tools` (PyPI)** — actively maintained, **v4.0.1 released 2026-02-27, Python 3.12+ (matches our runtime), MIT**. Reads/writes cues, beatgrid, BPM, key, track color, autogain; also crates, smart crates, and the library `database V2`. Deps: `mutagen` (tag I/O), optional `numpy`/`librosa`/`pillow`. This is the one to use.
- Other options: `Holzhaus/serato-tags` (reference + `scripts/tagdump.py`), `juicy-serato`, `bvandercar-vt/serato-tools`.
- **Risk:** the markers are binary blobs (medium effort if hand-parsing), but the maintained library + docs absorb that. Low risk in practice.

### Cue points as embedding anchors
**Yes — reliable.** Hot-cue positions are exact sample/ms offsets the DJ deliberately set (drop, breakdown, intro). Ideal CLAP excerpt anchors. Plus beatgrid gives downbeat alignment.

---

## 2. Traktor Pro (Native Instruments)

### Where stored
Single XML file (**not** in the audio files):
- macOS: `~/Documents/Native Instruments/Traktor <version>/collection.nml`
- History sets: `~/Documents/Native Instruments/Traktor <version>/History/history_<date>.nml`

### Fields available (exact NML schema)
Per-track `<ENTRY>` (verified against real fixture):

```xml
<ENTRY MODIFIED_DATE="2019/10/19" TITLE="Dubstep 1" ARTIST="Loopmasters" AUDIO_ID="...">
  <LOCATION DIR="/:path/:to/:" FILE="track.mp3" VOLUME="osx" VOLUMEID="osx"/>
  <INFO BITRATE="189720" GENRE="Dubstep" COMMENT="..." KEY="10m"
        PLAYTIME="193" PLAYTIME_FLOAT="192.078369" FILESIZE="5040" .../>
  <TEMPO BPM="139.999924" BPM_QUALITY="100.000000"/>
  <MUSICAL_KEY VALUE="12"/>
  <CUE_V2 NAME="AutoGrid" TYPE="4" START="52.315876" LEN="0.000000" REPEATS="-1" HOTCUE="0"/>
</ENTRY>
```

- **Musical key** — two encodings, both present:
  - `INFO@KEY="10m"` = **Open Key notation** (human-displayed; Open Key = Camelot with letters swapped: `m`=minor, `d`=major; one-to-one with Camelot, e.g. OpenKey `1m`↔Camelot `8A`). May be human/Mixed-In-Key set.
  - `MUSICAL_KEY@VALUE` = integer **0–23 chromatic** (Traktor's auto key-detect; 12 pitches × major/minor). Deterministic to map → Camelot.
- **BPM** → `TEMPO@BPM` (float) + `BPM_QUALITY`. Auto, editable.
- **Beatgrid + cues + loops** → `CUE_V2` elements (multiple). Attributes: `NAME`, `DISPL_ORDER`, `TYPE`, `START`, `LEN`, `REPEATS`, `HOTCUE`.
  - `TYPE`: `4` = grid/AutoGrid anchor, `0` = cue point, `5` = loop, `1`/`2`/`3` = fade-in/fade-out/load (cue subtypes).
  - **`START` is in SECONDS as a float** (e.g. `"52.315876"`) — NOT milliseconds. `LEN` likewise (loop length; `0` for point cues).
  - `HOTCUE` = slot index (`-1`/`0`..`7`); `-1`/unassigned = grid/anchor not bound to a pad.
- **Rating** → `INFO@RANKING` (0–255 scale, maps to 0–5 stars), **Comment** → `INFO@COMMENT`/`COMMENT2`, **Play count** → `INFO@PLAYCOUNT`, **Color** → `INFO@COLOR` (when set; absent in minimal fixtures). Human-set.
- **Playlists** → `<PLAYLIST>`/`<NODE>` tree referencing entries by `LOCATION` key.

### Parseability (Python)
- **Easiest of the three — clean, fully open XML.** Can parse with stdlib `xml.etree.ElementTree` directly; no reverse-engineering needed.
- `traktor-nml-utils` (PyPI, `wolkenarchitekt`) — autogenerated dataclasses (xsdata), read+write, Py3.7+. Tested vs Traktor 3.3.0 and parses 2.x. **Caveat: low maintenance (no PyPI release in ~12mo); a known issue chokes on newer attrs like `NML:INDEXING`** — so for vibemix's read-only needs, hand-rolling `xml.etree` against the small ENTRY schema above is more robust than depending on it.
- **Risk:** very low. Worst case is new optional attributes in future Traktor versions, which lenient `xml.etree` parsing ignores gracefully.

### Cue points as embedding anchors
**Yes — reliable.** `CUE_V2 START` (seconds float) gives exact, DJ-set hot-cue/loop positions. Just remember seconds (not ms) and filter `TYPE=4` grid anchors from real performance cues.

---

## 3. djay Pro (Algoriddim)

### Where stored
- `~/Music/djay/` — the **"djay Media Library"** (playlists, history, queue, and **per-song cue points + loop regions**). Format is a **proprietary SQLite database** ("djay Media Library database" — confirmed by Algoriddim's own corruption/error docs referencing the DB).
- `~/Library/Group Containers/VJXTL73S8G.com.algoriddim.userdata/Library/Application Support/Algoriddim/` — per-song analysis (waveforms, beatgrids). (Sandboxed alt path: `~/Library/Containers/com.algoriddim.djay-pro-mac/Data/...` for MAS installs.)
- **Cue points and loops are NOT embedded in the audio files** — they live only in djay's DB. BPM and key are sometimes written back to standard file tags when edited, but not reliably.

### Fields available
Internally djay holds key, BPM, beatgrid, cue points, loop regions, playlists, history — including AI-derived analysis (djay Pro AI uses on-device Core ML for stem/analysis, audio-driven not metadata-driven). But the **schema is closed and undocumented**.

### Parseability (Python)
- **No public schema, no reverse-engineering docs, no Python parsing library.** You can open the SQLite file with stdlib `sqlite3`, but table/column meaning, cue encoding (likely a serialized blob/plist per track), and beatgrid format are all unknown and would need from-scratch reverse engineering.
- **High brittleness:** closed proprietary format with frequent app updates (djay Pro AI ships fast) → schema can change under us with no notice. Worst risk/reward of the three.
- **Cleaner future path:** **OneLibrary** — a standardized cross-app DJ-library format Algoriddim co-developed **with AlphaTheta (Pioneer/Rekordbox's parent)** that exports playlists, cue points, loops, and beatgrids to a USB drive in a documented-ish standard. If djay support is ever wanted, ingest the OneLibrary export, not the private DB.

### Cue points as embedding anchors
Technically yes (djay stores precise cues), but **not accessible reliably offline** without reverse-engineering the closed DB. Not usable for v1.

---

## Decision rationale (market × parseability)

- **Market share (DJ pro/prosumer, approx):** Serato ≈ #1 (esp. controllerists/turntablists/hip-hop/open-format), Rekordbox ≈ #1–2 (club-standard CDJs), Traktor ≈ #3 (declined but loyal base), djay ≈ growing on iPad/Mac + casual/Apple-Music users but smaller pro footprint.
- **Parse reliability:** Traktor (clean XML) > Serato (binary but maintained lib + full docs) >> djay (closed SQLite, no lib).
- **Product (share × reliability):** Serato wins the #2 slot — huge base AND a current Python 3.12 library that reads exactly the cues/beatgrid/BPM we need. Traktor is a cheap #3 (small lib effort, XML). djay is deferred — low pro share relative to the reverse-engineering cost and ongoing churn risk.

**Final order: Rekordbox → Serato → Traktor → (defer djay via OneLibrary).**

---

## Sources
- Serato GEOB reverse-engineering + format docs: https://github.com/Holzhaus/serato-tags , https://github.com/Holzhaus/serato-tags/blob/main/docs/fileformats.md , https://homepage.ruhr-uni-bochum.de/jan.holthuis/reversing-seratos-geob-tags.html , https://github.com/mixxxdj/mixxx/wiki/Serato-Metadata-Format
- Serato Python lib: https://pypi.org/project/serato-tools/ , https://github.com/bvandercar-vt/serato-tools , https://pypi.org/project/juicy-serato/
- Traktor NML lib + fixture: https://pypi.org/project/traktor-nml-utils/ , https://github.com/wolkenarchitekt/traktor-nml-utils , https://github.com/wolkenarchitekt/traktor-nml-utils/blob/master/tests/fixtures/collection.nml , https://github.com/wolkenarchitekt/traktor-nml-utils/issues/7
- Traktor NML→Rekordbox converter: https://github.com/Segolene-Albouy/Traktor-NML-to-Rekordbox-XML
- Traktor key notation: https://djtechtools.com/amp/2013/09/11/traktor-script-convert-open-key-to-camelot-scale/ , https://github.com/rosstroha/traktor-key-converter
- djay storage: https://help.algoriddim.com/hc/en-us/articles/360014912211-Where-does-djay-Pro-store-playlists-cue-points-and-other-data-on-my-Mac , https://help.algoriddim.com/hc/en-us/articles/360014912131-Where-does-djay-Pro-store-cue-points-and-other-metadata , https://www.algoriddim.com/onelibrary
- Cross-ecosystem overview: https://www.digitaldjtips.com/dj-software-secrets/
