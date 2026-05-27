# VERIFY — DJ library-parser claims (Serato / Engine DJ / Traktor)

> Fact-check of load-bearing claims in [`serato-engine-traktor-metadata.md`](./serato-engine-traktor-metadata.md).
> Method: GitHub repo pages + project docs + WebSearch (context7 unavailable in this env; not in deferred-tool list). Date: 2026-05-26.
> Focus: does each lib **exist**, is it **maintained**, and does it actually do the **read vs write** claimed.

## Verdict table

| Library / Claim | Verdict | Evidence |
|---|---|---|
| **`libdjinterop` is a real C++ Engine DJ lib** | **CONFIRMED** | `github.com/xsco/libdjinterop` — C++ (98.6%), ~77 stars, 273 commits, 37 tags/releases. Real, the canonical Engine lib. |
| `libdjinterop` LGPL-3.0 | **CONFIRMED** | Repo license = LGPL-3.0. |
| `libdjinterop` reads **AND writes** Engine Database2 (track meta, beat grids, hot cues, loops, waveforms, crates, playlists) | **CONFIRMED** | README feature list = "Track metadata, Beat grids, Hot cues, Loops, Waveforms, Crates, Playlists." Mixxx uses it for **Export to Engine Prime** (write path) — PR mixxxdj/mixxx#2753, and ongoing updates PR #14172. So write is real, proven in production by Mixxx. |
| `libdjinterop` supports OS 1.0.3–4.3.3 / Desktop 1.0.1–4.3.0; actively tracks new schema versions | **CONFIRMED (with nuance)** | Repo README states that exact version range. Actively developed in 2025 (issues Jan–Apr 2025; v0.26.1 added Engine v3-era support; Mixxx pin 0.24.3 = Engine 4.1/4.2). The headline range is the repo's own claim, not hallucinated. **Nuance:** README also self-describes as "early beta… not all features implemented" — maturity is real but not 1.0. |
| `libdjinterop` has **no Python binding** | **CONFIRMED** | No PyPI package, no bindings dir; pure C++ (distro packages are libdjinterop-dev / .so only). Integration needs FFI/pybind11 or a port. Matches doc. |
| **`serato-tools` (bvandercar-vt) exists, Python 3.12+** | **CONFIRMED** | `github.com/bvandercar-vt/serato-tools` — Python, "designed for Python 3.12+", ~25 stars, 298 commits, on PyPI (`pip install serato-tools`). Real and on PyPI as claimed. |
| `serato-tools` **writes** GEOB "Serato Markers2" (cues/loops), beatgrid, crates, DatabaseV2 | **CONFIRMED** | README documents read+write of Serato Markers2 (hotcues/loops), Serato BeatGrid (incl. dynamic analysis + snap-to-beat), Serato Autotags, crates + smart-crate rules. Read+write toolkit, as claimed. |
| `serato-tools` README backup warning | **CONFIRMED (verbatim)** | README: "Recommended to make a backup of the database file elsewhere, before modifying via this package, in case an unforeseen bug appears." Doc quotes it correctly. |
| `serato-tools` maturity / actively committed | **CONFIRMED** | 298 commits, on PyPI, Py3.12 target. README notes the *upstream* `serato-tags` "appears to be no longer maintained" — this fork is the live one. Modest stars but active. |
| **`piratengine` (ssabug) — pure-Python Engine `m.db` reader** | **CONFIRMED, with correction** | `github.com/ssabug/piratengine` exists. **Correction to doc:** not strictly pure-Python (96% Python + PowerShell/Shell helpers) and it does more than read — reads track/playlist, **edits/adds tracks, manages playlists**, + StageLinQ network. ~19 stars, 67 commits, last release **Aug 2024**. "Provided as is, no warranty." Doc's "early/low maturity" is accurate. |
| **Engine DJ: `Database2/{m.db,p.db}` SQLite; PerformanceData BLOBs = Qt qCompress (4-byte BE uncompressed-len + zlib); loops column uncompressed; cue positions in samples** | **CONFIRMED** | Mixxx wiki "Engine-Library-Format" confirms ALL of: m.db/p.db SQLite, the 32-bit-uncompressed-length-prefix + zlib = `QByteArray::qCompress/qUncompress` framing, `loops` is NOT compressed (explicit note), positions "usually measured in samples rather than elapsed time," and per-column layout (quickCues/beatData/loops). Byte-level claims match the authoritative reverse-eng spec. |
| **Traktor `collection.nml` XML; real NML parser lib `traktor-nml-utils`** | **CONFIRMED** | `github.com/wolkenarchitekt/traktor-nml-utils` — Python, xsdata-generated dataclasses, reads **and** writes NML (Traktor 2.x/3.x), ~58 stars, 107 commits, active (GH Actions). Confirms doc. |
| `traktor-nml-utils` is low-maintenance / chokes on newer attrs | **CONFIRMED (consistent)** | Maintainer's own caveats: XSD "created from my own Traktor files… might not fit all collection/history files" + "writing NML hasn't been tested thoroughly enough yet, always keep a copy." Matches doc's "low-maintenance, hand-rolled `xml.etree` more robust for write" guidance. |
| **Serato GEOB tag names: Serato Markers2 / BeatGrid / Autotags / Overview; base64 + binary cue (RGB color, ms position)** | **CONFIRMED** | Holzhaus reverse-eng writeup (ruhr-uni-bochum.de) + `github.com/Holzhaus/serato-tags` (MIT code / CC-BY-SA docs, ~91 stars, 138 commits) confirm all four tag names, that Markers2 payload is **base64-encoded**, cue **position = 4-byte LE int in milliseconds**, **color = 3 RGB bytes**, names = null-terminated UTF-8. Format claims accurate. |
| Mixxx "Serato cue round-trip loses data" risk (issue #11530) | **CONFIRMED** | mixxxdj/mixxx#11530 is a real issue: importing file metadata replaces Mixxx cues with Serato cues; Serato schema differs (numbering, no loop color) → lossless round-trip impossible. Supports the doc's "preserve unknown bytes" write-safety argument. |
| Denon official 3rd-party write-contract (schema-edit prohibition, ATTACH side-db, don't write while running) | **NOT INDEPENDENTLY RE-FETCHED** | Cited KB URLs (support.denondj.com / enginedj.com article 69000834165) are plausible and consistent with the format docs, but I did not fetch them this pass. **UNCERTAIN-but-low-risk** — the technical write-rules they imply are corroborated by the Mixxx format wiki and Engine corruption KBs. |

## Hallucination check
**No hallucinated libraries.** All five named code libs are real and resolve to live GitHub repos with the claimed capabilities:
- `xsco/libdjinterop` (C++, LGPL-3.0, read+write Engine)
- `bvandercar-vt/serato-tools` (Python 3.12+, PyPI, read+write Serato)
- `ssabug/piratengine` (Python, early, Engine m.db)
- `wolkenarchitekt/traktor-nml-utils` (Python, read+write NML)
- `Holzhaus/serato-tags` (GEOB format spec + Python examples)

Plus the two authoritative format specs (Mixxx Engine-Library-Format wiki, Holzhaus GEOB writeup) check out.

## Corrections / flags for the source doc
1. **`piratengine` is not "pure-Python" and is more than an m.db reader** — it also edits/adds tracks, manages playlists, and does StageLinQ networking (96% Python + shell helpers). Doc undersells it slightly; "early/low maturity" rating is fair.
2. **`libdjinterop` self-describes as "early beta, not all features implemented"** — doc calls it "best-maintained / canonical" (true) but should note the beta caveat; its write path is nonetheless production-validated via Mixxx's Engine export.
3. **The Holzhaus repo is `Holzhaus/serato-tags`** (the format-spec repo) — distinct from `bvandercar-vt/serato-tools` (the write toolkit). Doc cites both correctly; just don't conflate the near-identical names.
4. **Denon KB write-contract URLs were not re-verified this pass** (UNCERTAIN) — only flag where independent confirmation is missing; technical claims are corroborated by other sources.
