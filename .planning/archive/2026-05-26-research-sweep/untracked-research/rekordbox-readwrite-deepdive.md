# Rekordbox READ + WRITE Deep Dive — AI-placed hot cues back into Rekordbox

**Question:** vibemix's Viber agent already READS a local DJ library. We now want it to deeply read AND **write** Rekordbox metadata — specifically **AI-placed hot cues written back into Rekordbox so the DJ sees them on their CDJs/controller**. What's the safest write path, what can pyrekordbox actually do, and what survives a Rekordbox re-import?

**Date:** 2026-05-26. Companion to (and does NOT duplicate):
- `rekordbox-metadata-unlock.md` — the **READ spine** (collection.xml schema: every `TRACK`/`POSITION_MARK`/`TEMPO` attribute, key notation, reliability classes, cue-as-embedding-anchor strategy, the "XML-first / DSP-fallback" coverage problem). **Treat that file as authoritative on the read side; this file does not re-list the XML attribute tables.**
- `dj-ecosystem-metadata.md` — Serato/Traktor/djay (non-Rekordbox) ingest survey.

This file is the **WRITE side** + the parts of READ that bear on writing (DB tables, the SQLCipher key, ANLZ).

---

## TL;DR — the recommended write strategy

**Ship AI hot cues via a generated `rekordbox.xml` that the DJ imports — NOT by writing `master.db` directly. In v1.**

| | XML round-trip (RECOMMENDED v1) | Direct `master.db` write (defer / Pro-only) |
|---|---|---|
| **What we emit** | A `*.xml` (Pioneer DJ XML) with `<TRACK>` rows carrying our `<POSITION_MARK>` hot cues (+ optional `<TEMPO>` grid). DJ imports it. | Decrypt `master.db` (SQLCipher), `INSERT` rows into `DjmdCue`, bump USN, commit. |
| **Reversibility / safety** | **Non-destructive.** Lands in a *separate* "rekordbox xml" sidebar tree; the DJ chooses which tracks to "Import to Collection". Their live DB is never touched by us. | **Mutates the live source-of-truth DB.** Backup-or-bust. A bad write/USN desync can corrupt the collection or trigger a full re-sync. |
| **Rekordbox running?** | Fine — XML is just a file; DJ imports on their own time. | **Must be CLOSED.** pyrekordbox refuses to commit while Rekordbox runs (anti-corruption guard). |
| **Cue color** | Writeable (newer XML carries per-mark `Red`/`Green`/`Blue`) — but our pinned 0.4.4 parser doesn't *read* it, and we'd hand-emit it. | Writeable via `DjmdCue.ColorTableID`/`Color`. |
| **Hot cue → pad visible on CDJ** | Yes, after the DJ imports + (re)exports to USB. | Yes, after Rekordbox re-exports ANLZ to USB. |
| **pyrekordbox support TODAY (0.4.4)** | **Fully supported** — `pyrekordbox.rbxml` builds + writes XML, including `add_mark()`. | **Cue writing is NOT in the released package.** It lives in an unmerged "cues" branch and is *stuck* on the VBR/ABR `InMpegAbs` problem. Releasing it ourselves = maintaining reverse-engineered byte-offset math. |
| **Install/bundle cost** | Zero — XML path needs no SQLCipher binary (matches our existing `--no-deps` posture). | Re-introduces the 3.2 MB `sqlcipher3-wheels` C-extension we deliberately excluded (Phase 21 gate) + the key-extraction fragility. |

**Bottom line:** the XML round-trip is the safe, shippable, "DJ stays in control" path and it is the one pyrekordbox actually supports for writing today. Direct-DB is the power-user upgrade once we (a) need live/instant cues without a manual import, (b) can stomach the SQLCipher dependency, and (c) are willing to own USN + ANLZ correctness. Recommend XML for v1; gate direct-DB behind a Pro flag + explicit "close Rekordbox, we backed up your DB" UX.

---

## 1. collection.xml READ — what's reliably readable (delta only)

The full per-attribute schema is in **`rekordbox-metadata-unlock.md` §1** (TRACK attrs, `POSITION_MARK` Type/Num/Start, `TEMPO` Inizio/Bpm/Metro/Battito, key-notation gotcha). Not repeated here. Reliable-read summary that file already establishes:

- **Free + clean:** BPM (`AverageBpm`), key (`Tonality`, *classical* notation — convert to Camelot ourselves), full beatgrid (`TEMPO` nodes), hot cues (`Num` 0–7) + memory cues (`Num=-1`), duration, location, genre/label/year/rating/playcount/colour/comments.
- **Gaps on read with pinned 0.4.4:** **cue color** (`PositionMark.ATTRIBS` omits Red/Green/Blue), clean **My Tag/Energy** (flattened into `Comments` on export), and anything **live** (XML is a manual snapshot).
- **The coverage truth:** every field is gated on the DJ having analyzed + cued that track → **XML-first, DSP-fallback per track** (we own `cue_detect.py`).

**New read note relevant to writing:** the XML uses `file://localhost/...` URL-encoded `Location` as the practical join key on import (see §3 — Rekordbox matches by file path, not by our `TrackID`). So whatever we *write* back must carry the **exact same `Location`** as the DJ's real file or the cues won't attach.

---

## 2. `master.db` (SQLCipher) — read AND write feasibility

### 2.1 The key situation — it's a single hardcoded constant (this is the big unlock/risk)

- Rekordbox **6 and 7** store the collection in `master.db`, a **SQLCipher 4**-encrypted SQLite file. Default macOS path: `~/Library/Pioneer/rekordbox/master.db` (Win: `%APPDATA%\Pioneer\rekordbox\master.db`).
- **The encryption key is the same hardcoded value for every install of RB6 and RB7.** Community-documented (liamcottle, pyrekordbox): SQLCipher key `402fd482c38817c35ffa8ffb8c7d93143b749e7d315df7a81732a1ff43608497`, applied as a raw key:
  ```sql
  PRAGMA key = "x'402fd482c38817c35ffa8ffb8c7d93143b749e7d315df7a81732a1ff43608497'";
  -- SQLCipher 4 defaults: cipher_page_size=4096, kdf_iter=256000, HMAC-SHA512, PBKDF2-HMAC-SHA512.
  -- (raw-key form skips KDF; pyrekordbox passes the key directly.)
  ```
  It is **obfuscation, not real security** — "Pioneer prefer no one outside Pioneer touches it."
- **How pyrekordbox gets the key:**
  1. **`python -m pyrekordbox download-key`** — fetches the known key into the local pyrekordbox cache (`~/.local/share/pyrekordbox` / appdirs). After this, `Rekordbox6Database()` opens with no args.
  2. **Manual:** `Rekordbox6Database(key="402fd482...")`.
  3. **Frida runtime dump** (legacy, version-proof): hook `sqlite3_key()` while Rekordbox launches. Only needed if the constant ever rotates.
- **The 6.6.5 breakage (historical, now moot for us):** RB ≥6.6.5 compiled `app.asar` to `.jsc` bytecode, killing the old *regex-scrape-the-app* auto-extraction. That only matters if you insist on *deriving* the key from the binary. Since the key is a **known published constant**, `download-key` / manual sidesteps the whole 6.6.5 saga. pyrekordbox 0.4.4 is **tested against `5.8.6 | 6.7.7 | 7.0.9`** — RB7 confirmed working.

> **Implication for vibemix:** opening `master.db` read/write is *technically trivial* (known key). The friction is the **3.2 MB `sqlcipher3-wheels` C-extension** we currently exclude from the bundle + the CI dormancy gate (`tests/library/test_pyrekordbox_install.py` asserts `Rekordbox6Database`/`pyrekordbox.db6` stay out of `src/vibemix/`). Activating DB writes means reversing that deliberate Phase-21 posture.

### 2.2 The USN problem — the silent corruption trap

Every syncable row in `master.db` carries `rb_local_usn` (update sequence number); a global counter lives in `agentRegistry`/`localUsn`. **Rekordbox uses USN to detect what changed since last sync (cloud/USB).** If you `INSERT`/`UPDATE` a row **without bumping the USN correctly**, Rekordbox can: ignore your change, mark the collection inconsistent, or trigger a full re-sync that **overwrites or drops your edit**. This is the #1 way naive direct-DB writes silently fail or corrupt.

- pyrekordbox exposes USN helpers (e.g. `get_local_usn()` / `increment_local_usn()` / an autoincrement path) and bumps USN on its supported writes. **You cannot just raw-`sqlite3` INSERT a cue and walk away** — you must set the new row's `rb_local_usn` to a freshly incremented global USN, in pyrekordbox's transaction, then `db.commit()`.
- **pyrekordbox refuses to `commit()` while Rekordbox is running** — explicit anti-corruption guard ("raises an error if you want to commit while Rekordbox is running"). Reading is allowed with RB open; **writing is not.**

### 2.3 What the DB has that XML doesn't (write-relevant)

- `DjmdCue` rows = first-class cues with **`Color`/`ColorTableID`** (per-cue color — the thing XML 0.4.4 can't read), `ActiveLoop`, `Comment` (label), `Kind`.
- My Tags as relational rows (`DjmdMyTag`/`DjmdSongMyTag`) instead of `Comments` mush.
- **ANLZ binaries** (`.DAT`/`.EXT`/`.2EX`, referenced by `DjmdContent.AnalysisDataPath`) hold the waveform + the cue/grid copy that **CDJs actually read off USB**. pyrekordbox can **parse** ANLZ (DAT/EXT/2EX; unsupported tags PWV6/PWV7/PWVC) but **cannot write/create them yet** ("planned"). On USB export, **Rekordbox regenerates ANLZ from the DB** — so writing `DjmdCue` + leaving ANLZ to Rekordbox is the pragmatic path (this is exactly what `djcues` does: "Cues are written to `master.db` only; rekordbox handles ANLZ sync on USB export").

### 2.4 pyrekordbox WRITE limits (0.4.4) — concrete

- **Supported writes:** edit existing fields on ORM objects (`content.Title = ...`, color/rating/comment/genre), and **add/delete on a small whitelist of tables:** `DjmdContent`, `DjmdPlaylist`, `DjmdSongPlaylist`, `DjmdAlbum`, `DjmdArtist`, `DjmdGenre`, `DjmdLabel`. Then `db.commit()`.
- **Cue WRITING is NOT in the released package.** Reading cues works (`content.Cues`); creating them lives in an **unmerged "cues" branch** and is **blocked on VBR/ABR MP3s** — it can't compute the required `InMpegFrame`/`InMpegAbs` byte offsets for variable-bitrate files, so it `raise NotImplementedError`. Fixed-bitrate MP3/constant formats are the only ones the branch handles. **This is why third-party tools (CueGen) bypass pyrekordbox for the cue INSERT and hit the DB themselves.**
- **Cue color gap (0.4.4):** confirmed on the *read* side in `rekordbox-metadata-unlock.md`; on the *write* side, the unreleased cue branch + the DB's `DjmdCue.ColorTableID` are where color lives. XML path: emit `<POSITION_MARK Red= Green= Blue=>` ourselves.

### 2.5 Risks of writing the live DB

1. **USN desync → dropped/overwritten cues or full re-sync** (§2.2). Highest-probability silent failure.
2. **Write-while-running corruption** — mitigated by pyrekordbox's guard, but only if you go through pyrekordbox (raw sqlite3 has no guard).
3. **ANLZ staleness** — DB cue exists but the `.EXT` the CDJ reads doesn't, until Rekordbox re-exports. Cue invisible on hardware until then.
4. **VBR `InMpegAbs`** — wrong byte offset = cue lands at the wrong audio position (or NotImplementedError). Most DJ libraries are full of VBR MP3s.
5. **Schema drift** RB6→7 and across point releases (column adds, new sync fields). pyrekordbox tracks it but lags Pioneer.
6. **Bundle + attack surface** — re-adding `sqlcipher3-wheels` reverses our deliberate exclusion and grows the one-click installer.

---

## 3. SAFEST write path for AI-placed hot cues — what survives a re-import

### 3.1 The XML round-trip mechanism (how Rekordbox actually ingests it)

1. We generate a Pioneer DJ XML file (`pyrekordbox.rbxml`) containing `<TRACK>` entries — each with our AI `<POSITION_MARK>` hot cues (and optionally `<TEMPO>` if we're confident about grid). **`Location` must exactly match the DJ's real file URI.**
2. DJ points **Preferences → Advanced → Database → rekordbox xml** at our file, enables the **"rekordbox xml"** view (Preferences → View).
3. The file appears as a **separate sidebar tree** ("rekordbox xml"), NOT merged. The DJ selects tracks → **right-click → "Import to Collection."** *They* choose what lands. **Match is by file path/`Location`, not our `TrackID`** — same file = cues attach to their existing analyzed track.

### 3.2 What survives the re-import (and what doesn't)

- **Hot cues + memory cues (`POSITION_MARK`) — survive.** This is the load-bearing win: AI hot cues show up on the DJ's pads (and CDJs after USB export).
- **Beatgrid (`TEMPO`) — survives** but with two real caveats:
  - **Hotcue↔grid misalignment** is a known XML-import artifact (cues drift relative to the imported grid). Safer to **NOT write our own grid** and let the AI cues snap onto the DJ's *existing* grid — i.e. emit only `POSITION_MARK`, reuse their `TEMPO`. (We can snap our cue `Start` to the nearest downbeat from their grid before emitting — same idea as CueGen's `--snap`.)
  - **Rekordbox auto-analysis can overwrite an imported grid/cues.** Mitigation the DJ must do once: **turn OFF auto-analysis** (Preferences → Analysis), or analyze with **Phrase only** (adds waveform without clobbering grid). We should surface this as a one-line instruction in the import UX.
- **Tags / rating / color / comments — survive** if present in the XML.
- **Does NOT transfer cleanly:** cue **color** unless we hand-emit `Red/Green/Blue`; My Tags as structured tags (XML flattens to `Comments`); anything the DJ doesn't explicitly "Import to Collection."

### 3.3 Why XML beats direct-DB *for cues specifically*

- **Non-destructive + DJ-in-control** (separate tree, opt-in import) — matches vibemix's "never break the flow / DJ trusts it" bar.
- **No SQLCipher, no USN math, no ANLZ math, no VBR offset problem** — the four hardest failure modes of direct-DB writes all evaporate; Rekordbox does the DB insert + ANLZ regen itself, correctly, on its own engine.
- **It's the path pyrekordbox actually ships for writing.** `rbxml` write is released; cue-DB write is not.
- **Tradeoff we accept:** it's a *manual import step* and a *snapshot*, not instant/live. For "AI proposes hot cues, DJ reviews + imports," that's the right amount of friction (it doubles as the review gate). Direct-DB is only worth it for a future "auto-applied, zero-click" Pro mode.

---

## 4. pyrekordbox API specifics — read & write snippets

### 4.1 XML write path (RECOMMENDED) — emit AI hot cues

```python
from pyrekordbox.rbxml import RekordboxXml

xml = RekordboxXml()  # or RekordboxXml(path="existing.xml") to extend the DJ's export

# Add a track keyed on the DJ's REAL file location (Location must match exactly).
track = xml.add_track(
    location="/Users/dj/Music/HardTechno/banger.wav",  # written as file://localhost/... URI
    Name="Banger", Artist="ArtistX",
    AverageBpm=174.0, Tonality="Am", TotalTime=360,
)

# AI-placed HOT CUE: Num 0..7 = hot pad A..H ; Num=-1 = memory cue.
# Type: 0=cue 1=fade-in 2=fade-out 3=load 4=loop. Start/End in SECONDS.
track.add_mark(Name="DROP",     Type="cue", Start=92.0, Num=0)   # hot cue A
track.add_mark(Name="BREAK",    Type="cue", Start=156.5, Num=1)  # hot cue B
track.add_mark(Name="MIX-OUT",  Type="cue", Start=300.0, Num=2)  # hot cue C
# Cue COLOR: newer XML accepts Red/Green/Blue on the mark; emit explicitly if wanted:
# track.add_mark(..., Red=204, Green=0, Blue=204)

# Reuse the DJ's grid rather than writing our own (avoid hotcue/grid drift):
# track.add_tempo(Inizio=0.123, Bpm=174.0, Metro="4/4", Battito=1)

xml.save(path="/Users/dj/Desktop/vibemix_cues.xml")
# DJ: Preferences→Advanced→Database→rekordbox xml → point here → import the tracks they want.
```

### 4.2 READ path (what we already do / should extend) — XML

```python
from pyrekordbox.rbxml import RekordboxXml
xml = RekordboxXml(path="collection.xml")
for t in xml.get_tracks():
    bpm, key = t["AverageBpm"], t["Tonality"]   # classical key -> our Camelot table
    for m in t.marks:                            # POSITION_MARK
        # m.Type, m.Start (s), m.Num (-1 memory / 0..7 hot), m.End (loops)
        ...
    for tempo in t.tempos:                        # TEMPO beatgrid (currently UNREAD in vibemix)
        # tempo.Inizio, tempo.Bpm, tempo.Metro, tempo.Battito
        ...
```

### 4.3 Direct-DB read (allowed with Rekordbox OPEN) — db6

```python
from pyrekordbox import Rekordbox6Database
db = Rekordbox6Database()                 # uses cached key from `download-key`
# or Rekordbox6Database(key="402fd482...")  # explicit known key

for c in db.get_content():
    print(c.Title, c.Artist.Name, c.BPM, c.Rating, c.ColorID)
    for cue in c.Cues:                    # DjmdCue rows
        print(cue.InMsec, cue.Kind, cue.Color, cue.Comment)
```

### 4.4 Direct-DB WRITE — the supported fields (NOT cues), with the USN + close-RB rules

```python
# PRECONDITIONS: Rekordbox CLOSED. master.db backed up (datetime-suffixed copy) — like CueGen/djcues do.
from pyrekordbox import Rekordbox6Database
db = Rekordbox6Database()

c = db.get_content()[0]
c.Rating  = 255          # 0/51/102/153/204/255 -> 0..5 stars
c.Commnt  = "vibemix: peak-time"   # note column spelling varies; comment field
c.ColorID = ...          # track color tag
# My Tag: via DjmdMyTag / DjmdSongMyTag relation (add the song-tag link row).

db.commit()              # pyrekordbox handles USN bump for its supported writes;
                         # commit() RAISES if Rekordbox is running.
```

### 4.5 Direct-DB WRITE of CUES — NOT available in 0.4.4

```python
# There is NO released `add_cue()` / cue-create in pyrekordbox 0.4.4.
# It exists only on the unmerged "cues" branch and raises NotImplementedError on VBR/ABR MP3
# because it can't compute InMpegFrame/InMpegAbs byte offsets.
#
# If we ever MUST write cues to the DB (Pro/auto-apply mode), the proven reference is
# CueGen (C#): it INSERTs into DjmdCue directly, snaps to the bar (--snap), assigns
# Color/ColorTableID from a palette, backs up master.db first, requires Rekordbox CLOSED,
# and lets Rekordbox regenerate ANLZ on USB export. We would own: USN increment, the
# InMsec/InFrame fields, color table mapping, and VBR offset correctness.
#
# RECOMMENDATION: do NOT build this for v1. Use §4.1 XML instead.
```

### 4.6 ANLZ (`.DAT`/`.EXT`/`.2EX`)

```python
from pyrekordbox.anlz import AnlzFile
anlz = AnlzFile.parse_file(".../ANLZ0000.DAT")   # READ ONLY (beatgrid, cues, waveform)
# Writing/creating ANLZ is "planned", NOT implemented. PWV6/PWV7/PWVC tags unsupported.
# So: write DB cues -> let Rekordbox rebuild ANLZ on export. Never hand-write ANLZ for cues.
```

---

## 5. Version differences (RB5 vs 6 vs 7) that affect read/write

| | Rekordbox 5 | Rekordbox 6 | Rekordbox 7 |
|---|---|---|---|
| **Collection store** | `datafile.edb` (Firebird-ish, different format) | `master.db` (SQLCipher SQLite) | `master.db` (same SQLCipher SQLite + cloud/sync layer) |
| **SQLCipher key** | n/a (no SQLCipher) | one **hardcoded** key (`402fd482...`) | **same** hardcoded key; 7.0.9 confirmed working with pyrekordbox 0.4.4 |
| **collection.xml export** | Yes (same Pioneer XML schema across 5/6/7) | Yes | Yes — **the XML schema is the stable cross-version interface** → another reason XML is the safe write path |
| **USN/sync** | minimal | `rb_local_usn` + `localUsn`; must bump on write | same + heavier cloud sync (Dropbox/AlphaTheta Cloud) → USN/sync mistakes are *more* consequential (can propagate a bad state to other devices) |
| **Key extraction** | n/a | regex-scrape worked pre-6.6.5; `download-key`/manual after | obfuscated app; `download-key`/manual/Frida only |
| **pyrekordbox coverage** | `.edb` read partial | full db6 read + limited write | tested (7.0.9), same db6 path |

**Net:** RB6 and RB7 are the same DB/key/XML story for our purposes — write code targets both. RB5 is legacy (different store) but its **XML export is identical**, so the XML write path covers RB5 users for free; direct-DB does not apply to RB5. **The XML schema being stable across 5/6/7 is itself a strong argument for the XML write path.**

---

## 6. Recommendation for vibemix (concrete)

1. **v1 — ship AI hot cues via XML round-trip.** Extend the importer's sibling: a `cue_export.py` that takes Viber/`cue_detect.py` cue anchors → `pyrekordbox.rbxml` `add_mark()` → save `vibemix_cues.xml`. Reuse the DJ's existing `Location` + `TEMPO` grid; snap cue `Start` to the nearest downbeat from their grid; emit `Red/Green/Blue` per cue if we want vibemix-branded colors. Ship a 3-line UX: "point RB at this XML → import these tracks → (turn off auto-analysis so it sticks)."
2. **Keep the SQLCipher / direct-DB path DORMANT** (don't reverse Phase-21). The known key makes it *possible* anytime, so document it as the **Pro/auto-apply** upgrade with: backup master.db (datetime suffix) → require Rekordbox closed → pyrekordbox commit (USN-safe) → user re-exports to USB. Do **not** hand-write ANLZ; let Rekordbox regenerate.
3. **Do NOT attempt DB cue-INSERT until either** (a) pyrekordbox merges + releases the cues branch with VBR support, or (b) we port CueGen's DjmdCue/USN/color logic ourselves and accept ownership of VBR `InMpegAbs` correctness. Neither is v1.
4. **Read upgrades (cheap, do alongside):** read `TEMPO` (currently unread — grounded grid for free) and the full `Comments` for energy/MyTag mining, per `rekordbox-metadata-unlock.md §5`. For cue *color on read*, post-parse raw XML `Red/Green/Blue` rather than activating db6.

---

## Risks summary (write side)

- **XML path:** (a) DJ must do a manual import — surface it clearly; (b) **auto-analysis can clobber imported grid/cues** → instruct "turn off auto-analysis / Phrase-only analyze"; (c) hotcue↔grid drift → reuse DJ's grid + snap to downbeat, don't write our own `TEMPO`; (d) `Location` mismatch (moved/renamed files) = cues don't attach → match the exact file URI; (e) it's a snapshot, not live.
- **Direct-DB path:** USN desync (dropped/overwritten cues, or bad state propagated via RB7 cloud sync), write-while-running corruption, stale ANLZ until export, VBR `InMpegAbs` mis-placement, schema drift, and reversing our bundle/CI dormancy posture. All avoidable in v1 by choosing XML.

---

## Sources

- pyrekordbox — repo, db6 API, XML format, ANLZ, tested versions (5.8.6/6.7.7/7.0.9): https://github.com/dylanljones/pyrekordbox , https://pyrekordbox.readthedocs.io/en/latest/quickstart.html , https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html , https://pypi.org/project/pyrekordbox/
- Cue WRITE status (cues branch, VBR/ABR `InMpegAbs` NotImplementedError, DjmdCue table): https://github.com/dylanljones/pyrekordbox/discussions/113
- SQLCipher key extraction RB6.6.5+ / app.asar `.jsc` breakage / download-key / Frida: https://github.com/dylanljones/pyrekordbox/discussions/97 , https://github.com/dylanljones/pyrekordbox
- Hardcoded master.db key (single constant, RB6/7, obfuscation-not-security): https://github.com/liamcottle/pioneer-rekordbox-database-encryption , https://github.com/liamcottle/pioneer-rekordbox-database-encryption/blob/master/README.md
- Direct-DB cue writer reference (CueGen — DjmdCue, --snap, color palette, backup, RB-must-be-closed, ANLZ on USB export): https://github.com/mganss/CueGen/blob/master/README.md
- djcues (pyrekordbox-based, "cues written to master.db only, RB handles ANLZ on USB export", apply won't write while RB running, auto-backup): https://github.com/mcroydon/djcues
- "write while Rekordbox running raises an error" (My Tag write discussion): https://github.com/dylanljones/pyrekordbox/discussions/122
- XML import workflow / what survives / auto-analysis overwrite / Phrase-only: https://djfile.com/how-import-beatgrids-cue-points-and-tags-using-rekordbox-xml , https://www.lexicondj.com/manual/sync-rekordbox-xml , https://mixedinkey.com/rekordbox-cue-points/
- Pioneer official XML format spec: https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf
- Companion read research (NOT duplicated here): `.planning/research/rekordbox-metadata-unlock.md`, `.planning/research/dj-ecosystem-metadata.md`
