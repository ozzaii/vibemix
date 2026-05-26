# Rekordbox Metadata Unlock — What We Get For Free

**Question:** Does the DJ's Rekordbox library already contain clean, human-curated key + BPM + beatgrid + cue points so vibemix doesn't have to DSP them itself? And can those cues anchor our CLAP embedding excerpts?

**Headline answer: YES (partial) — via `collection.xml` export, no SQLCipher needed.**
We get clean key, BPM, beatgrid, and labeled hot/memory cues for free. The catch: it's all _user-effort-gated_ (the DJ has to have actually analyzed + cued the tracks in Rekordbox), and the data is a one-time **export snapshot**, not live. vibemix already parses the spine (title/artist/bpm/key/duration/cues) but **leaves real metadata on the table** — genre, label, rating, comments, color, playcount, and the **beatgrid (TEMPO nodes)** are all in the XML and currently unread.

---

## 1. `collection.xml` export — every field, per node

Source: Pioneer's official XML spec (`xml_format_list.pdf`) + `pyrekordbox.rbxml` `ATTRIBS` lists (the exact attributes the parser exposes). Numbers are locale-independent (dot decimal, no thousands separators).

### TRACK element — full attribute set (`Track.ATTRIBS`)

| Attribute | Type | Unit / Format | Notes |
|---|---|---|---|
| `TrackID` | utf-8 | — | Rekordbox internal id; our dict key |
| `Name` | utf-8 | — | Track title |
| `Artist` | utf-8 | — | Performer |
| `Composer` | utf-8 | — | Composer / producer |
| `Album` | utf-8 | — | Album title |
| `Grouping` | utf-8 | — | Free group field |
| `Genre` | utf-8 | — | **Human/auto genre tag** |
| `Kind` | utf-8 | — | File type, e.g. `"WAV File"`, `"MP3 File"` |
| `Size` | sint64 | bytes | File size |
| `TotalTime` | float64 | seconds | Duration (integer seconds, no decimals) |
| `DiscNumber` | sint32 | — | |
| `TrackNumber` | sint32 | — | |
| `Year` | sint32 | — | Release year |
| `AverageBpm` | float64 | BPM | **The BPM**, with decimals (e.g. `128.00`, `174.01`) |
| `DateModified` | utf-8 | yyyy-mm-dd | |
| `DateAdded` | utf-8 | yyyy-mm-dd | When added to library |
| `BitRate` | sint32 | kbps | |
| `SampleRate` | float64 | Hz | e.g. `44100` |
| `Comments` | utf-8 | — | **Free-text DJ notes** (often holds energy ratings / Camelot / "intro 16 bars") |
| `PlayCount` | sint32 | — | Times played |
| `LastPlayed` | utf-8 | date | |
| `Rating` | sint32 | 0/51/102/153/204/255 | **Star rating** mapped 0–5 stars → those byte values |
| `Location` | utf-8 URI | `file://localhost/...` URL-encoded | File path (we `urllib.parse.unquote` it) |
| `Remixer` | utf-8 | — | |
| `Tonality` | utf-8 | **musical key** | See key-notation note below |
| `Label` | utf-8 | — | Record label |
| `Mix` | utf-8 | — | Mix variant name |
| `Colour` / `Color` | utf-8 | RGB hex-ish (`0xRRGGBB`) | **Track color tag** (the colored dot in the browser) |

> **MyTag / energy:** there is **no dedicated `MyTag` or `Energy` attribute** in the XML schema. Rekordbox "My Tags" and the energy/comment field are **flattened into `Comments`** on export (DJs commonly store `/* 7A - Energy 8 */`-style strings there). So MyTag/energy = parse `Comments`, not a clean field.

### Key notation (`Tonality`) — IMPORTANT

`Tonality` is a **utf-8 string in CLASSIC musical notation** by default: `Am`, `F#m`, `C`, `Abm`, `Ebm`, `Gm`, etc. (minor = lowercase `m` suffix). It is **NOT Camelot/Open-Key in the XML** even if the DJ's Rekordbox UI is set to display Alphanumeric/Camelot — the display format (Preferences → View → Key display) is a UI skin; the stored/exported value stays classical. So:

- We get classical key for free.
- **vibemix must convert classical → Camelot itself** (deterministic 24-entry lookup table — `Am=8A`, `C=8B`, `Cm=5A`, …). This matches the CLAUDE.md invariant "Camelot = deterministic table, LLM never computes keys." Our `harmonics.py` already owns Camelot.

### TEMPO node (beatgrid) — `Tempo.ATTRIBS`

One or more `<TEMPO>` children per track. A single node = constant-tempo grid; multiple = variable-tempo grid (live/unquantized tracks).

| Attribute | Type | Unit | Notes |
|---|---|---|---|
| `Inizio` | float64 | seconds | Position of this grid anchor (first beat / where the grid marker sits) |
| `Bpm` | float64 | BPM | BPM at this grid point (lets us detect tempo changes) |
| `Metro` | utf-8 | — | Time signature, e.g. `"4/4"`, `"3/4"` |
| `Battito` | sint32 | — | Beat number within the bar (1–4 for 4/4) — tells us which beat `Inizio` lands on, i.e. **downbeat phase** |

This is the **full beatgrid for free**: first-downbeat offset (`Inizio` + `Battito`), tempo, and meter. We currently **do not read TEMPO at all.**

### POSITION_MARK node (cues) — `PositionMark.ATTRIBS`

| Attribute | Type | Unit | Notes |
|---|---|---|---|
| `Name` | utf-8 | — | Cue label (often empty; DJs sometimes name them "DROP", "BREAK") |
| `Type` | sint32 | — | `0`=Cue, `1`=Fade-In, `2`=Fade-Out, `3`=Load, `4`=Loop |
| `Start` | float64 | seconds | Cue position |
| `End` | float64 | seconds | Only present for `Type=4` (Loop) |
| `Num` | sint32 | — | **`-1` = memory cue; `0..7` = hot cue slot (A–H)** |

> **Cue COLOR is NOT exposed by pyrekordbox 0.4.4.** Pioneer's newer XML does emit per-mark `Red`/`Green`/`Blue` color attributes, but `PositionMark.ATTRIBS` in the pinned 0.4.4 parser is only `["Name","Type","Start","End","Num"]` — so we **cannot read cue color with the current pin** without upgrading pyrekordbox or post-parsing the raw XML ourselves. (Track-level `Colour` IS available; cue-level color is the gap.)

---

## 2. `master.db` (SQLCipher) via pyrekordbox — what it adds, and why we don't use it

**What the DB has that XML does NOT:**
- **Live, always-current state** — XML is a manual `File → Export Collection`; the DB is the source of truth Rekordbox writes continuously. XML goes stale the moment the DJ re-analyzes or re-cues.
- **Cue colors + richer cue metadata**, My Tags as first-class relational rows (not flattened into Comments), playlists-as-tree with ordering, history sessions, related-tracks, beatgrid stored at full ANLZ fidelity.
- **ANLZ binaries** (`.DAT`/`.EXT`/`.2EX`) — the waveform, full beat grid, and per-cue color/comment that the DB references.

**Why vibemix deliberately does NOT touch it (from `pyproject.toml` + `rekordbox.py` docstring):**
1. **SQLCipher key friction + binary blob.** pyrekordbox 0.4.4 hard-lists `sqlcipher3-wheels` (a 3.2 MB compiled C-extension) as `install_requires`. To open `master.db` you must extract Rekordbox's SQLCipher key (historically scraped from the app binary / cached on disk) and feed it to `Rekordbox6Database.unlock()`. That key-extraction is **version-coupled and fragile** — Pioneer rotates it across Rekordbox 6/7 point releases, and it's a cat-and-mouse the project refuses to maintain.
2. **Bundle + attack-surface cost.** The 3.2 MB SQLCipher binary is excluded from the PyInstaller bundle on purpose (Phase 21 gate). vibemix installs pyrekordbox `--no-deps` and re-declares only the transitives it actually needs; `sqlcipher3-wheels` is overridden with a never-matching platform marker so `uv` keeps it in the resolved graph but never installs it.
3. **Enforced dormancy.** A CI grep gate keeps `Rekordbox6Database` / `pyrekordbox.db6` out of `src/vibemix/`; `tests/library/test_pyrekordbox_install.py` asserts the SQLCipher module stays dormant in `sys.modules`. The C-extension import in `pyrekordbox/db6/database.py:28-34` is wrapped in try/except so the package still imports under the stdlib `sqlite3` fallback even with the binary absent.

**Is XML strictly sufficient?** For vibemix's grounding spine — **yes.** Key, BPM, full beatgrid, hot+memory cue positions, genre, rating, comments, color, playcount, file location all come through XML. The only DB-exclusive wins are (a) cue colors, (b) My Tags as clean fields, (c) live freshness. None are worth re-opening the SQLCipher can. **Recommendation: stay XML-only.** If cue color ever becomes load-bearing, post-parse the raw XML for `Red/Green/Blue` rather than activating the DB.

---

## 3. Reliability — human-curated vs auto-analyzed vs missing

| Field | Trust class | Notes |
|---|---|---|
| `AverageBpm` / TEMPO `Bpm` | **Auto, very reliable** | Rekordbox BPM detection is excellent for 4/4 dance music. Can half/double-time on some genres; DJs usually correct. |
| TEMPO grid (`Inizio`/`Battito`) | **Auto, reliable IF analyzed; DJs hand-correct** | Grid is auto on analysis; serious DJs manually fix the first downbeat. Multiple TEMPO nodes = variable grid (live/older tracks) — handle, don't assume single. |
| `Tonality` (key) | **Auto, ~85–90% reliable** | Rekordbox key detect is decent but not perfect (relative-major/minor swaps, some EDM ambiguity). Treat as a strong prior, not gospel. |
| Hot cues (`Num` 0–7) | **HUMAN-curated — highest trust** | Hand-placed by the DJ at the parts they actually mix on. This is the gold. |
| Memory cues (`Num`=-1) | **Human-curated** | Also hand-placed; often phrase/section markers. |
| `Rating`, `Colour`, `Comments`, `Grouping`, `Mix` | **Human** | DJ's own taxonomy; high signal but idiosyncratic. |
| `Genre`, `Label`, `Year` | **Mixed** | From file tags / online lookup; reliable-ish, varies by how the DJ tags. |
| `PlayCount`, `DateAdded`, `LastPlayed` | **Auto, reliable** | Behavioral signal — what the DJ actually plays. |

**Can be empty/missing in a real library (must default-coerce — vibemix already does):**
- `Tonality`, `AverageBpm` → empty/0 if the track was **never analyzed** (just imported). Very common.
- **Cues + TEMPO → ZERO nodes** if not analyzed or not cued. Many "dump folder" tracks have no cues at all.
- `Genre`/`Label`/`Comments`/`Rating`/`Colour` → routinely blank.
- `Location` → can point at a **moved/missing file** (XML is a snapshot).

**Bottom line on reliability:** BPM + key + beatgrid are auto but good; **cues are the genuinely human, high-trust layer.** The hard truth is _coverage_: a field is only "free" if the DJ analyzed + cued that track. We must gracefully fall back to our own DSP (`cue_detect.py`, live detectors) when a track has no cues/grid.

---

## 4. Cues as embedding anchors — viable?

**Yes — hot/memory cues are the best possible anchors for our ≤80s CLAP excerpts, when present.**

How DJs actually place cues (the convention we can lean on):
- Standard structure (very common, ~5 hot cues): **A=intro/mix-in, B=breakdown, C=first drop, D=second drop, (E=outro/mix-out)**.
- Hot cues mark the **mixable moments** — exactly the regions we want CLAP to embed (intro for mix-in matching, drop for energy matching, breakdown for blend-out).
- Memory cues often mark phrase boundaries / section starts.

**Embedding strategy implication:**
- When a track has cues: anchor each ≤80s excerpt **at a cue `Start`** (and for the intro, run to the next cue or +80s) → embeddings represent the parts the DJ mixes on, not arbitrary intro/mid/outro slices. This directly enables "enter on hot cue 2" type suggestions.
- `Type`/`Num` tell us the role: `Num`=0 (hot A) ≈ intro/mix-in; later hot cues ≈ drops; `Type=4` loops give an explicit start+end mixable region.
- **Reliability caveat:** cue _semantics_ aren't guaranteed (a DJ might cue idiosyncratically), but cue _positions_ are reliable as "musically significant moment" markers — enough to anchor excerpts even without trusting the label.
- **Fallback:** tracks without cues → `cue_detect.py` (our offline DSP breakdown/re-entry/phrase detector) generates anchors. So the pipeline is: **Rekordbox cues first (free, human), DSP cues second (computed).** vibemix already has both halves built — they just need to be wired so the importer prefers XML cues and falls back to `detect_cues()`.

---

## 5. What vibemix ALREADY parses vs leaves on the table

### Already parsed (`src/vibemix/library/rekordbox.py` → `TrackEntry` / `CuePoint`)
- **TrackEntry:** `TrackID`, `Name`, `Artist`, `Album`, `AverageBpm`→`bpm`, `Tonality`→`key` (raw classical, **not yet Camelot-normalized at parse time**), `TotalTime`→`duration_s`, `Location`→`filepath` (URL-decoded), and `marks`→`cues`.
- **CuePoint:** `Name`, `Type` (kept as raw string — note: pyrekordbox returns it; vibemix stores `"cue"` default), `Start`→`start_s`, `End`→`end_s` (loop only), `Num`→`number` (`-1` memory, else hot slot).
- Caching: pickle warm-start (`library.pkl`), 30-day staleness nudge, mtime invalidation. SQLCipher path correctly never touched.

### On the table (in the XML, currently UNREAD)
- **`Genre`** — high-value for the technics filter (genre ∩ Camelot ∩ BPM). _Missing._
- **`Label`, `Year`, `Remixer`, `Composer`, `Grouping`, `Mix`** — metadata richness for curate/Viber. _Missing._
- **`Comments`** — holds DJ's free-text energy/MyTag/Camelot scribbles. _Missing._ (Worth mining for energy.)
- **`Rating`** (0–5 stars) + **`PlayCount`** + **`DateAdded`/`LastPlayed`** — behavioral "what the DJ loves/plays" signal for ranking. _Missing._
- **`Colour`** (track color tag) — DJ's own visual taxonomy. _Missing._
- **`BitRate`/`SampleRate`/`Kind`/`Size`** — file quality. _Missing (minor)._
- **TEMPO nodes (entire beatgrid: `Inizio`/`Bpm`/`Metro`/`Battito`)** — **the biggest miss.** We get the **first-downbeat offset + meter + tempo-change map for free** and currently recompute downbeat phase live (`_phrase_dsp.lock_downbeat_phase`). Reading TEMPO would give us a grounded grid for free and let `cue_detect`/live detectors trust it. _pyrekordbox exposes `track.tempos` / TEMPO elements; vibemix never reads them._
- **Cue `Type` fidelity** — code defaults `Type` to `"cue"`; the real `Type` int (0/1/2/3/4 → cue/fadein/fadeout/load/loop) is available and would let us distinguish loops/fades. Partially on the table.
- **Cue COLOR** — _not_ available in the 0.4.4 parser (would need an upgrade or raw-XML post-parse). Note it as a known gap, not low-hanging fruit.

---

## Single biggest risk

**Coverage, not correctness.** Every "free" field is gated on the DJ having *analyzed and cued* the track in Rekordbox. A real-world library is a mix of fully-cued bangers and never-analyzed dump-folder tracks with **zero cues, no key, no grid**. If we ground the co-host / embeddings on "Rekordbox gave us cues" without a robust DSP fallback for uncued tracks, half the library silently has no anchors. The architecture must be **XML-first, DSP-fallback** per track — which we have the parts for (`cue_detect.py`) but haven't wired into the importer.

Secondary risk: the XML is a **stale one-time snapshot** (manual export) — `Location` can point at moved files, and re-cued tracks won't update until re-export. The 30-day staleness nudge exists; surface it in the UI.

---

## Concrete "what we get for free" checklist

**Clean, ready to use:**
- ✅ BPM (`AverageBpm`, with decimals)
- ✅ Musical key (`Tonality`, classical notation — we convert to Camelot ourselves, deterministic)
- ✅ Full beatgrid (TEMPO: first-downbeat `Inizio` + `Battito` phase, `Bpm`, `Metro` meter) — **in XML, not yet read**
- ✅ Hot cues (positions, slot A–H via `Num` 0–7) — human-placed, high trust
- ✅ Memory cues (`Num`=-1) — human-placed
- ✅ Cue type (cue/fadein/fadeout/load/loop via `Type` int) — in XML, partially read
- ✅ Duration, file location, format/bitrate/samplerate
- ✅ Genre, Label, Year, Remixer, Composer, Mix, Grouping
- ✅ Rating (0–5 stars), PlayCount, DateAdded/LastPlayed (behavioral signal)
- ✅ Track color tag (`Colour`), Comments (free-text MyTag/energy)

**NOT available (gaps):**
- ❌ Cue **color** (pyrekordbox 0.4.4 `PositionMark` omits Red/Green/Blue — needs upgrade or raw-XML post-parse)
- ❌ Clean **MyTag / Energy** fields (flattened into `Comments` on export — must parse free-text)
- ❌ Anything **live/current** (XML is a manual snapshot; live state lives only in `master.db`, which we deliberately don't open)

## Sources
- [pyrekordbox XML format docs](https://pyrekordbox.readthedocs.io/en/latest/formats/xml.html)
- [Pioneer official rekordbox XML format spec (PDF)](https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf)
- [pyrekordbox GitHub (rbxml ATTRIBS)](https://github.com/dylanljones/pyrekordbox)
- [AlphaTheta: key display format (Classic vs Alphanumeric)](https://support.pioneerdj.com/hc/en-us/articles/8943219092761-Can-I-change-the-display-format-for-keys)
- [Rekordbox cue setup / hot vs memory cue placement](https://blog.mixviberecords.com/2026/02/rekordbox-cue-setup-that-makes-djing.html)
- [DeeJay Plaza: hot cue & memory cue tutorial](https://www.deejayplaza.com/en/articles/rekordbox-memory-cue-point-hot-cue)
- vibemix code: `src/vibemix/library/rekordbox.py`, `src/vibemix/library/importer.py`, `src/vibemix/library/cue_detect.py`, `pyproject.toml` (lines 41–72, 139–148)
