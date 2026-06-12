# Hand-of-God ingest digest + Gig Check V1 ship note

Date: 2026-06-12. Source: the 8-file research pack Viber WA produced 2026-06-11
(Kaan dropped them from `~/Downloads`; canonical JSON lives at
`/home/ozai/projects/bravoh-ai/data/vibemix/research/2026-06-11-vibemix-hand-of-god-adversarial-ingest.json`).
Corpus: 513 ranked Reddit posts, 18 full thread reads, 51 source links, 35
machine-readable golds, raw exports under the pack's `raw_corpus/`.

## The strategy in three sentences

DJs do not trust their library under pressure. The open lane is a preflight
verdict (will this crate, USB, and cue map survive tonight?), not another
organizer, not "AI DJ". Public noun: **Gig Check** — a competitor already owns
"Music Library Doctor", and our own `library doctor` command is the environment
self-check.

## The five breakthroughs (hand-of-god ranked)

1. **Gig Check beats Library Doctor** — name collision with musiclibrarydoctor.com;
   own the moment before the gig instead of the cleanup category.
2. **USB "Will It Show Up?" is the safest read-only wedge** — AlphaTheta's dual
   OneLibrary/Device-Library formats + the pulled Rekordbox 7.2.12 export bug
   made booth survival a live public panic.
3. **Cue Notary beats cue generation** — MIK/Lexicon already generate dots; the
   open lane is reason/confidence/risk/alternate per cue. Our `smart_cues.py`
   already implements this shape (review-first, source-ranked, never invents).
4. **Back up meaning, not music** — crates, cues, path graph, tags, device DBs.
   "Crate Ark" = read-only snapshot manifest of what is and is not protected.
5. **Distribution = public panic utilities** — DJs search "rekordbox usb tracks
   not loading", not category names. One indexable free tool harvests intent.

Red lines from the pack, all kept: no DB mutation in V1, no destructive
deletes, no opaque cue without a reason, no fake scarcity, V1 earns trust by
refusing dangerous fixes.

## What the repo already had (gap analysis)

| Pack concept | Repo state before today |
|---|---|
| Cue Notary | `library/smart_cues.py` + cue stack — already built, review-first |
| Tonight/auto crate | `library/auto_crate.py` — deterministic, keyless |
| Env self-check | `library/doctor.py` — capability probes (name "doctor" occupied internally) |
| Rekordbox parse | `library/rekordbox.py` — tracks + cues + beatgrid, no playlists |
| **Preflight verdict** | **did not exist** ← the gap, now closed |
| USB Export Guard | does not exist (next candidate) |
| Crate Ark | does not exist |

## Shipped today: `vibemix library gig-check`

`src/vibemix/library/gig_check.py` + `tests/library/test_gig_check.py` (18
tests) + CLI wiring in `__main__.py`.

```
uv run python -m vibemix library gig-check <collection.xml> [--json]
```

Read-only audit ending in one verdict — `take_it` / `fix_first` /
`do_not_take` — with receipts:

- **missing files** (rides `ingest._resolve_local_path`, handles the
  pyrekordbox stripped-leading-slash form)
- **cue debt** per track: `no_hot_cues` (red; only `source=="dj"` cues count
  as prep — anlz/auto suggestions never silence the naked-track signal),
  `unlabeled_cues`, `no_mix_out_anchor` (no cue in the last 30%),
  `no_beatgrid` (yellows)
- **duplicate suspects** (normalized title+artist collisions)
- **crate bloat** (playlists over `--bloat-threshold`, default 80; playlist
  layer parsed read-only via pyrekordbox, stdlib `xml` banned by the semgrep
  gate on untrusted input)
- **Tonight crate**: the ready subset ranked by rating, capped `--tonight-cap`
  (default 40)

Verdict ladder: empty library or >30% blocked → `do_not_take`; any blocked or
>25% warn → `fix_first`; else `take_it`. Exit code IS the verdict (0/1/2), so
a prep script can gate on it.

Suite state: 18/18 new tests green; `tests/library` + `tests/repo` green except
two inherited reds (persona-seam expectation vs HEAD's debrief persona, and the
2026-06-10 `debrief-mock-after.png` >1MB LFS scrub) — both pre-date this work.

## Shipped 2026-06-12 (second wedge): `vibemix library export-guard`

`src/vibemix/library/export_guard.py` + `tests/library/test_export_guard.py`
(25 tests) + CLI wiring in `__main__.py`.

```
uv run python -m vibemix library export-guard <usb_path> --rig cdj-3000x [--json] [--filesystem fat32]
```

Read-only walk of a mounted USB ending in the same verdict ladder as
gig-check (exit code = verdict). What it audits, every hardware fact
verified against official AlphaTheta notices/manuals by a 4-agent research
workflow (wf_c61ce5aa-807; 23/24 claims survived adversarial verification):

- **The dual-format trap**: classic Device Library
  (`PIONEER/rekordbox/export.pdb`) vs OneLibrary
  (`PIONEER/rekordbox/exportLibrary.db`). CDJ-3000X/OPUS-QUAD read
  OneLibrary; CDJ-3000/XDJ-XZ/RX3/NXS2 and older read Device Library.
  Wrong-format-only stick = do_not_take with the re-export instruction
  (rekordbox 7.2.11+ writes both). This is the XDJ-AZ horror story and the
  withdrawn CDJ-3000 fw 3.30, predicted in the kitchen.
- **Filesystem vs rig**: NTFS/APFS = blocked everywhere; exFAT blocked on
  NXS2 (manual: FAT16/FAT32/HFS+ only), warn on CDJ-3000/XDJ-XZ
  (firmware-added), native on RX3/3000X/OPUS-QUAD. Unknown fs = honest
  absence, never a penalty.
- **Audio formats vs rig**: FLAC/ALAC start at NXS2; XZ/RX3 list no ALAC;
  pre-NXS2 = MP3 universal, AAC/WAV/AIFF patchy (warn). `.m4a` ambiguity
  (AAC or ALAC) warns instead of guessing.
- **Missing USBANLZ** (no waveforms/beatgrids), Engine-stick-on-Pioneer-rig,
  raw-files-no-export, Serato `_Serato_` presence, empty stick.

9 rig profiles: cdj-3000x, cdj-3000, cdj-2000nxs2, cdj-2000nxs (pre-NXS2),
xdj-xz, xdj-rx3, opus-quad, engine-os, serato-laptop. Engine OS format/fs
matrices deliberately not audited (no verified fact base yet).

## Queue (in pack-priority order)

1. ~~**Export Guard / USB Will-It-Show**~~ — SHIPPED 2026-06-12 (above).
2. **Serato input** — partially pre-existing: `library/sources/serato.py`
   (binary crate + Markers2 cue decoder) already implements the parse layer
   (Phase 89). Remaining: route SeratoSource through gig-check's audit.
3. **Public panic utility** — `/dj/gig-check` web page emitting shareable
   receipts; SEO on panic phrases ("serato crates no music", "cue points
   disappeared").
4. **Crate Ark** — backup-meaning manifest (audio vs crates vs cues vs DBs).
5. **Recall trainer** — KRATEO-style track-recall drill from the user's own
   library; strong Reddit signal (19↑/29 comments).
6. Copy bank for launch lives in the pack's `many_golds` (g01–g05): "You did
   not need more music. You needed fewer lies." etc. Avoid: "AI DJ",
   "seamless", "magic".

## Where the raw data lives

- `~/Downloads/2026-06-11-vibemix-hand-of-god-adversarial-ingest{-pack.zip,.json}`
  (pack zip = 8.3M unpacked: ranked posts, 18 reddit reads, last30days runs,
  YouTube TSVs, GitHub repo scans)
- `~/Downloads/2026-06-11-vibemix-library-doctor-insane-data{.json,-pack.zip}`
- `~/Downloads/vibemix-dj-pain-scan.md` (the 8-pain stack + beachheads)
- `~/Downloads/vibemix-library-automation-cue-crafter.zip` (cue blueprint:
  8-slot A–H system, per-DJ-software read paths, week-by-week attack order)
- `~/Downloads/gold-radar-dj-library-surgery-2026-06-11.md`
