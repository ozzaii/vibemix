# MIXXX ARSENAL — what 20 years of GPL DJ engineering hands vibemix

> READ-ONLY analyst packet. Role = MIXXX ARSENAL. HEAD ed081570 (charter says ce909a87 elsewhere — both pre-this-session). Every claim is file:line in our tree, a Mixxx source path, a license fact with source, or an explicit NOT-FOUND. Kaan: "if we can snort even further from Mixxx we can go GPL too, who cares?"
>
> **THE HEADLINE, STATED PLAINLY:** the bigger prize is the **library-format READERS**, not the DSP. The DSP is already mostly covered by prior clean-room packets (c297207c, d9ddbeed) and is gated behind genuine multi-week spikes (beat-tracker, WSOLA, key-DSP). The readers are a *different category of win*: they're the **onboarding/discovery wedge** — "import your whole library + cues + crates + play-history from ANY DJ app in one click" — they are mostly **NOT even GPL** (the cleanest ones are MIT/MPL/already-shipped), and the format is a *fact* you reimplement from a published spec, not authored expression you copy. Today vibemix can ingest exactly ONE ecosystem (Rekordbox) and is blind to Serato/Traktor/Engine/VirtualDJ users — that's a majority of the addressable DJ market locked out at the front door.

---

## 0. THE LICENSE TRUTH (correct Kaan's framing before he commits)

"Go GPL too" is the wrong frame for the readers — it's *more* permissive than that, and the DSP is where the GPL question actually bites.

| Asset | Real license | What that means for us |
|---|---|---|
| **Mixxx app source** | **GPL-3.0+** (upgraded from GPL-2.0+ when it adopted libKeyFinder) — [LICENSE](https://github.com/mixxxdj/mixxx/blob/main/LICENSE), [PR #3476](https://github.com/mixxxdj/mixxx/pull/3476) | If we *vendor Mixxx C++ verbatim*, the linked vibemix client becomes GPL-3.0. That is the only place the "go GPL" decision is real. We never need to. |
| **triseratops** (Serato parser, by Holzhaus = the Mixxx dev who wrote Mixxx's Serato code) | **MPL-2.0** — [repo](https://github.com/Holzhaus/triseratops) | File-level copyleft. Rust. We don't even vendor it — we reimplement from its + Mixxx's **public wiki format spec**. |
| **crate-digger** Kaitai `.ksy` PDB/ANLZ specs (Deep-Symmetry) | spec files, EPL/public — [crate-digger](https://github.com/Deep-Symmetry/crate-digger), [rekordbox_anlz.ksy](https://github.com/Deep-Symmetry/crate-digger/blob/main/src/main/kaitai/rekordbox_anlz.ksy) | A machine-readable format *grammar*. Reimplementing a documented binary grammar is the textbook clean-room case. |
| **pyrekordbox** (we ALREADY depend on it, `==0.4.4 --no-deps`) | **MIT** — [repo](https://github.com/dylanljones/pyrekordbox) | Reads collection.xml + **master.db (SQLCipher v6/v7)** + **ANLZ .DAT/.EXT/.2EX** + **PDB** + MySettings + Device Library Plus. We use ~10% of it. |
| **libdjinterop** (Engine DJ reader Mixxx links) | **LGPL-3.0+** — [repo](https://github.com/xsco/libdjinterop) | LGPL = dynamic-link OK in a proprietary product. But it's C++; the Engine DB is plain SQLite anyway (read it directly, no lib needed). |
| **libKeyFinder** (Mixxx's key detector) | **GPL-3.0** — [repo](https://github.com/mixxxdj/libkeyfinder) | This is the one true GPL trap. Vendoring it = GPL client. The *algorithm* (Sha'ath chromagram + key-profile correlation) is a published MSc thesis = reimplementable. |
| **qm-dsp** (beat/tempo + old key core; now vendored in Mixxx `lib/qm-dsp`) | **GPL-2.0+** — [qm-dsp](https://github.com/c4dm/qm-dsp) | GPL trap. Algorithm is published (complex-spectral-difference DF + DP beat-tracker). Reimplement, or use MIT ONNX Beat-This. |
| **SoundTouch** (Mixxx's timestretch/keylock) | **LGPL-2.1** — surina.net | LGPL dynamic-link OK. But it's the keylock spike (deferred). |

**Bottom line on license:** for the *readers*, "go GPL" is mostly moot — the cleanest path is **clean-room from the public Mixxx-wiki spec + reuse the MIT/MPL Python ports as cross-checks**, exactly the line our standing ports already cross (`state/transition_clock.py`, `learn/beatmatch_judge.py` — both "ported clean-room, no GPL"). The GPL decision *only* becomes live if we want to vendor **libKeyFinder** or **qm-dsp** C++ verbatim instead of reimplementing them. So the honest framing for Kaan: **we don't need to go GPL to get the readers; we'd only consider it to shortcut the key/beat DSP, and even there a reimplement keeps us Apache.**

---

# PART I — THE LIBRARY-FORMAT READERS (★ THE KILLER FIND)

## I.0 — What vibemix can read/write TODAY (the precise gap)

**Verified in tree:**
- READ Rekordbox `collection.xml` — `src/vibemix/library/sources/rekordbox.py` (drives `library/rekordbox.py::RekordboxLibrary`), **XML-ONLY by explicit design**, refuses to open master.db (`sources/rekordbox.py:13-19` "this source NEVER opens the SQLCipher master.db").
- READ Rekordbox **ANLZ** `.DAT/.EXT` — `library/anlz_ingest.py:86-163` (`iter_anlz_ext_files`, `parse_anlz_bundle`, PQTZ beatgrid + PSSI phrase + PCOB/PCO2 cues via pyrekordbox). **This already exists and is gold — it's the proof the binary-format path is viable in our stack.**
- WRITE Rekordbox XML — `library/export_rekordbox.py`.
- WRITE Serato Markers2 (the "UNIVERSAL carrier") — `library/export_serato.py`, `library/cue_folder.py`.
- WRITE M3U / Serato crate — `library/cue_export.py`, `library/cue_folder.py`.
- The source registry `library/sources/__init__.py:6-8` literally says *"Rekordbox collection.xml today; Serato / Traktor later"* — **the seam was designed for this and never filled.**

**The gap (NOT-FOUND, confirmed by grep across `library/`):**
- NO Serato library READER (crates + DB V2 + GEOB cue/beatgrid). We *write* Serato Markers2 but *cannot read a Serato user's existing library.*
- NO Traktor `collection.nml` reader.
- NO Engine DJ / Denon `m.db` reader.
- NO VirtualDJ `database.xml` reader.
- NO iTunes / Apple Music XML reader.
- We *depend on pyrekordbox* (MIT) which can read master.db + PDB, but we **deliberately use only its XML path** — leaving the encrypted v6 DB and USB device exports on the table.

**Why this is the wedge, not a nice-to-have:** every reader is a *one-click onboarding flow that drops the user's entire library + taste + cue work into vibemix's CLAP engine + Earned skill-tree.* The discovery-wedge memory (`project_vibe_mix_discovery_wedge.md`) says the hero is "DJs forget tracks in their own library" — that hero is **dead on arrival for any non-Rekordbox DJ** until these readers exist. Cross-ref FEATURE-STATE: library ingest is real but single-ecosystem.

---

## I.1 — SERATO READER ★★★★★ (highest leverage reader; biggest installed base after Rekordbox)

**On-disk format (3 layers):**
1. **Crates** — `_Serato_/Subcrates/<Name>.crate` (and `Subcrates` per drive). Flat binary: 4-byte ASCII tag + 4-byte big-endian length + payload, recursively. Track refs are relative paths. *Smart crates* = `_Serato_/SmartCrates/*.scrate`.
2. **Database V2** — `_Serato_/database V2`: the master track table, same tag/length TLV encoding. Holds file paths, BPM, key text, added-date, play count.
3. **GEOB metadata tags** *inside each audio file* (ID3v2.3 `GEOB`, or MP4/FLAC equivalents): `Serato Markers_` (first 5 hotcues + 9 loops + track color), `Serato Markers2` (base64-wrapped TLV — full cue/loop/flip set + color), `Serato BeatGrid` (anchor + non-terminal/terminal markers), `Serato Overview` (waveform), `Serato Autotags` (BPM/gain/key), `Serato Offsets_`.

**Mixxx source path:** `src/track/serato/markers.cpp`, `markers2.cpp`, `beatgrid.cpp`, `tags.cpp`; library feature `src/library/serato/seratofeature.cpp` (DB V2 + crates). PRs [#2480](https://github.com/mixxxdj/mixxx/pull/2480) (library feature), [#2495](https://github.com/mixxxdj/mixxx/pull/2495) (Markers_ GEOB), [#3421](https://github.com/mixxxdj/mixxx/pull/3421) (beatgrid). **Format wiki (the clean-room spec):** [Serato Database Format](https://github.com/mixxxdj/mixxx/wiki/Serato-Database-Format) + [Serato Metadata Format](https://github.com/mixxxdj/mixxx/wiki/Serato-Metadata-Format).

**License / build choice:**
- Mixxx C++ = GPL-3.0 (don't vendor).
- **triseratops** (Holzhaus, the same author) = **MPL-2.0** Rust, "all formats reverse-engineered, parsing from scratch" — a reference, not a copy target.
- **Python ports already exist, permissive:** `serato-tools` ([repo](https://github.com/bvandrc/serato-tools)) reads/writes crates + smart crates + DB + GEOB cues/beatgrid; `python-serato-crates` ([repo](https://github.com/stephanlensky/python-serato-crates), 3.10+) read/write crates; `Serato-lib` (jesseward) documents the binary format.
- **HONEST BUILD CHOICE: keyless clean-room Python reimplement.** The format is a trivial TLV — the crate + DB V2 parser is **~150 lines of `struct.unpack` from the Mixxx wiki spec, zero deps, stays Apache.** GEOB cue/beatgrid extraction reuses our existing ID3 path (we already write Markers2 in `export_serato.py`, so we own the encoder — the decoder is its inverse). **Effort delta vs vendoring:** vendoring triseratops means a Rust dependency + FFI into the Python sidecar = *more* work and an MPL obligation, for a format simple enough to hand-write. **Clean-room WINS outright here.**
- **Effort:** crates+DB reader ~1 day; GEOB Markers2/BeatGrid decoder ~1 day (inverse of code we already have). Total **~2 days, Apache-clean, zero new dep.**

**Gap it fills:** Serato DJs (huge in hip-hop/scratch/open-format) get one-click library + cue + crate import. Their beatgrids and hotcues land as `CueAnchor`s feeding `cue_agreement.py` ground-truth and the Earned cueing competency. Cross-ref GOLD-WIRING: gives the cue/beatmatch graders a *real* grid source for non-Rekordbox users.

---

## I.2 — REKORDBOX PDB + master.db READER ★★★★ (we already 80% own this — finish it)

**On-disk format:**
- **`export.pdb`** — the DeviceSQL binary on every USB Rekordbox prepares (`/PIONEER/rekordbox/export.pdb`). Page-based B-tree of tables (tracks, artists, albums, playlists, artwork, color, history). Reversed by Deep-Symmetry's crate-digger; **public Kaitai grammar** `crate-pdb.ksy`.
- **`master.db`** — Rekordbox 6/7 SQLCipher-encrypted SQLite (the live desktop library, far richer than the XML export; has play history, My Tag, intelligent playlists, cue colors). Key is derivable (publicly documented).
- **ANLZ `.DAT/.EXT/.2EX`** — per-track analysis (beatgrid PQTZ, cues PCOB/PCO2, phrases PSSI, waveforms). **We already parse these** (`anlz_ingest.py`).

**Mixxx source path:** `src/library/rekordbox/rekordboxfeature.cpp` + Kaitai-generated `rekordbox_pdb.cpp`/`rekordbox_anlz.cpp`. Mixxx ships a copy of crate-digger's `.ksy`. PRs [#2119](https://github.com/mixxxdj/mixxx/pull/2119), [#13293](https://github.com/mixxxdj/mixxx/pull/13293) (kaitai update).

**License / build choice:**
- **pyrekordbox is MIT and ALREADY a dependency** (`pyproject.toml`, installed `--no-deps`). It reads PDB + master.db (via bundled `sqlcipher3-wheels`) + ANLZ. **We are leaving the two richest sources unused by a one-line policy choice** (`sources/rekordbox.py` refuses master.db; CLAUDE.md notes "SQLCipher path explicitly unused").
- **HONEST BUILD CHOICE: not even a build — a policy flip + ~1 day of wiring.** The "explicitly unused" stance was a *de-risking* call (avoid SQLCipher native dep complexity in the installer), not a technical block. Two sub-options:
  - **(a) master.db** — flip the policy, add a `RekordboxDbSource` that calls `pyrekordbox.Rekordbox6Database`. Cost = accept the `sqlcipher3-wheels` native dep in the `[ai-local]`/installer path. Unlocks play history + My Tag + the *live* library (no manual XML export step — the #1 onboarding friction today, since DJs must remember File→Export Collection).
  - **(b) PDB** — add a `RekordboxUsbSource` reading `export.pdb` from a mounted USB via pyrekordbox or a ~200-line clean-room Kaitai-spec parser. Unlocks "plug in your CDJ USB, vibemix reads it."
- **Effort delta clean-room vs pyrekordbox:** pyrekordbox already does it — **using the dep is the lower-effort path** (it's MIT, already pinned). Only reimplement if the SQLCipher native dep is unacceptable for the signed bundle (it may be — verify against the notarization flow). **~1 day (use dep) vs ~3 days (clean-room PDB).**

**Gap it fills:** kills the manual-XML-export onboarding step (memory: `project_phase89_dj_library_ingest_shipped.md` notes detection of collection.xml — but a DJ who never exported XML has nothing to detect). master.db = zero-friction ingest for the largest DJ base.

---

## I.3 — TRAKTOR `collection.nml` READER ★★★ (pure XML — cheapest reader to build)

**On-disk format:** single XML file `collection.nml` (`~/Documents/Native Instruments/Traktor X.X.X/collection.nml`). `<ENTRY>` per track with `<LOCATION>`, `<TEMPO BPM=...>`, `<MUSICAL_KEY VALUE=...>` (0–23 integer → our Camelot table), `<CUE_V2>` elements (hotcues/loads/grids/loops with `START`/`LEN`/`TYPE`). Traktor 2.x and 3.x variants.

**Mixxx source path:** `src/library/traktor/traktorfeature.cpp` — [main](https://github.com/mixxxdj/mixxx/blob/main/src/library/traktor/traktorfeature.cpp). Locates the file by appending `/collection.nml`; n-level tree for crates/playlists.

**License / build choice:**
- Mixxx C++ = GPL-3.0. **`traktor-nml-utils`** (Python, [repo](https://github.com/wolkenarchitekt/traktor-nml-utils)) parses + modifies NML for 2.x/3.x — permissive.
- **HONEST BUILD CHOICE: clean-room Python, trivial.** It's XML — `xml.etree` + a Camelot map for the 0–23 key codes + CUE_V2 → `CueAnchor`. **~half a day, zero dep, Apache.** This is structurally identical to our *existing* `RekordboxLibrary.load_xml` — copy that source's shape, swap the schema. Lowest-effort reader on the board.

**Gap it fills:** Traktor's installed base (techno/house Europe — *exactly Francesco's DJ network*). The CUE_V2 grid + key lands directly in our Camelot/harmonic stack (`state/harmonics.py`).

---

## I.4 — ENGINE DJ / DENON `m.db` READER ★★★ (plain SQLite — no decryption)

**On-disk format:** `Engine Library/Database2/m.db` (+ `p.db`) — **unencrypted SQLite**. `Track` table = paths/BPM/key/length; `PerformanceData` (or `AnalysisData`) blobs = beatgrid + hot cues + loops + waveform. Schema is semver'd (the export-version mismatch is the main gotcha). Standalone SC5000/Prime hardware uses the identical format.

**Mixxx source path:** uses **libdjinterop** (`src/library/` Engine feature). Format wiki: [Engine Library Format](https://github.com/mixxxdj/mixxx/wiki/Engine-Library-Format).

**License / build choice:**
- libdjinterop = **LGPL-3.0+** (C++). LGPL dynamic-link is product-safe, but it's C++ → FFI pain in the Python sidecar.
- **HONEST BUILD CHOICE: clean-room Python via stdlib `sqlite3` — no decryption, no native dep, no lib.** Open `m.db`, `SELECT` the Track table, parse the `PerformanceData` blob per the documented schema. The only real work is the binary blob layout (beatgrid/cues), version-gated. **~1.5 days** (the blob is the cost; the relational part is an afternoon). **Clean-room WINS** — libdjinterop's whole value is the blob decoding, which the wiki documents.

**Gap it fills:** the entire Denon Prime / standalone-hardware DJ segment (growing fast, club-installed). Plug-in-USB ingest with full cue/grid.

---

## I.5 — VirtualDJ `database.xml` + iTunes/Apple Music XML ★★ (low effort, long-tail base)

**VirtualDJ:** one `database.xml` (per drive; `~/Documents/VirtualDJ/database.xml` on Mac). `<Song>` with `<Infos>`, `<Tags>` (BPM/key), `<Poi>` cue points (the [VirtualDJ Cue Storage Format](https://github.com/mixxxdj/mixxx/wiki/Virtual-Dj-Cue-Storage-Format) wiki). Mixxx has in-progress importers for "modern" and "v6" schemas.

**iTunes/Apple Music:** `iTunes Music Library.xml` plist — Mixxx `src/library/itunes/itunesfeature.cpp`. **Caveat:** Apple is killing XML export (off-by-default in Music.app) → declining value; only useful for users with legacy libraries.

**HONEST BUILD CHOICE for both: clean-room XML/plist, ~half a day each.** VirtualDJ is worth it (active product, no cue source otherwise). iTunes is marginal (dying format) — build only if a user asks. Apache, `xml.etree` / `plistlib`, zero dep.

---

## I.6 — READER VERDICT TABLE (leverage / port-cost)

| Reader | Installed base | License path | Build choice | Effort | Leverage/cost |
|---|---|---|---|---|---|
| **Serato** (crates+DB V2+GEOB) | ★★★★★ | clean-room (wiki spec); MPL/MIT ports as ref | clean-room Python, reuse our Markers2 encoder inverted | ~2d | **HIGHEST** |
| **Rekordbox master.db** | ★★★★★ | **MIT dep already shipped** | flip policy + wire pyrekordbox | ~1d | **HIGHEST** (kills XML-export friction) |
| **Traktor .nml** | ★★★★ | clean-room (XML) | mirror our `load_xml` | ~0.5d | **HIGHEST** (cheapest, Francesco's base) |
| **Engine m.db** | ★★★ | clean-room (plain SQLite) | stdlib sqlite3 | ~1.5d | HIGH |
| **Rekordbox PDB (USB)** | ★★★ | MIT dep or clean-room Kaitai | pyrekordbox or ~200-line parser | ~1d | MEDIUM-HIGH |
| **VirtualDJ .xml** | ★★ | clean-room (XML) | xml.etree | ~0.5d | MEDIUM |
| **iTunes/Apple XML** | ★ (dying) | clean-room (plist) | plistlib | ~0.5d | LOW |

**A "Universal Ingest" milestone = Serato + Traktor + Engine + master.db ≈ 5 focused days, all Apache-clean, mostly XML/SQLite/TLV, zero GPL exposure.** That is the single highest-ROI library move available and it is almost entirely *parsing*, not DSP or ML. It directly serves the discovery wedge and the Earned skill-tree (cues/grids from any app feed the competency graders).

---

# PART II — THE DSP & PERFORMANCE ARSENAL

> Most of this is already specced clean-room in the recovered packets (`wf_c297207c` goldmine map: beatgrid/sync/cue/autodj/key; `wf_d9ddbeed` round-2: EQ-filter DSP, crossfader math, loop/beatjump, waveform RGB, controller catalog). I rank by leverage/port-cost and flag exactly which of OUR current clean-room re-derivations become a straight copy if we vendored GPL.

## II.1 — EQ / FILTER / ISOLATOR DSP ★★★★★ (the R-SLOP keystone — this is THE prize after the readers)

**Mixxx path:** `engine/filters/enginefilteriir.h` (biquad processSample), `enginefilterbiquad1.cpp` (fidlib spec strings = which RBJ filter), `effects/backends/builtin/biquadfullkilleqeffect.cpp:10-46` (ALL constants: corners 246/2484/1100 Hz, Q boost 0.3 / kill 0.9 / shelf 0.4, `kKillGain=-23`, bessel ratio 0.25), `lvmixeqbase.h:71-187` (Bessel-4 isolator band-split = the true full-kill), `enginefilterbessel4.cpp` (group-delay table), `filtereffect.cpp` (the deck LP/HP filter sweep, Butterworth Q=0.707, corners 13–22050 Hz). **License: Mixxx GPL-2.0+, BUT the coefficient math is the public RBJ Audio-EQ-Cookbook — Mixxx itself calls external fidlib, doesn't hand-derive it.**

**Vibemix gap (= R-SLOP):** `intel/eq_move_model.py` exists (8KB, present in tree as of this session) — it's the **named keystone** (`apply_live_claim_guard:2342`) that converts the live guard from REFUSE-all-causal to a *licensed* "your low-kill cratered the sub by 18 dB" verdict, and works on the master-only rig (no controller). Cross-ref GOLD-WIRING CARD 1 (the keystone) + RED-TEAM (narrator→coach).

**The straight-copy question, answered precisely:** our `eq_move_model.py` RBJ coefficients are **NOT a Mixxx copy and going GPL would NOT change that** — Mixxx delegates to fidlib (separate GPL lib) and the RBJ cookbook formulas are **public-domain math** (Robert Bristow-Johnson's cookbook is explicitly public). So "go GPL to copy the RBJ coeffs" buys nothing — the coeffs were never Mixxx's to give. **What going-GPL *would* let us straight-copy:** the **Bessel-4 isolator delay-ratio table** (`enginefilterbessel4.cpp:23-65`, the hardcoded `kDelayFactor1/2` + `delayRatioTable[]` integer-group-delay quantization) — that's authored constants, not cookbook. But we don't need the isolator for *grounding* (we only need the magnitude response `|H|²` to predict band deltas, per the d9ddbeed spec §3 — no real-time filtering). **Verdict: this is the highest-leverage DSP item and it needs ZERO GPL — the cookbook is public.** Build/finish `eq_move_model.py`, no license change.

## II.2 — KEY DETECTION (libKeyFinder) ★★★★ (the real GPL decision point)

**Mixxx path:** Mixxx now uses **libKeyFinder** ([repo](https://github.com/mixxxdj/libkeyfinder), **GPL-3.0**, by Ibrahim Sha'ath, maintained by Mixxx since 2.3 — *better than the old qm-dsp key analyzer*). Old path = `analyzerqueenmarykey.cpp` (qm-dsp `GetKeyMode`, GPL-2.0+, in `lib/qm-dsp`).

**Vibemix gap:** NO audio→key producer — the entire Camelot/harmonic stack (`state/harmonics.py`, the well-wired intelligence join per GOLD-WIRING §2) **dies on tag-less libraries.** A user who imports untagged audio (or via a reader that has no key field) gets zero harmonic coaching.

**The straight-copy question:** libKeyFinder is the **one asset where "go GPL" is a genuine shortcut.** Its chromagram + spectral-analysis + key-profile-correlation pipeline is C++ we could *vendor* (GPL-3.0 → our client becomes GPL-3.0) OR *reimplement* (Sha'ath's method is a published MSc thesis; Krumhansl-Schmuckler profiles are public). The c297207c packet §3.6 already specs the reimplement (decimate-8 → 36-bin/oct CQ chroma → 24-profile correlate → duration-weighted histogram argmax) and flags the risk: a confidently-wrong key detector poisons every harmonic suggestion → **SPIKE the DSP core on 20 known-key tracks first.**
- **GPL path (vendor libKeyFinder):** ~2 days integration, *proven accuracy* (top-3 in 2020 comparisons), **but flips the client to GPL-3.0** — a real product decision (Kaan: "fuck gpl we use it" per memory, but that was about a *runtime dep* mutagen, not vendoring DSP source into the client).
- **Apache path (reimplement):** ~1 week + spike risk, stays Apache, accuracy unproven.
- **VERDICT:** This is the ONE place to actually ask Kaan the GPL question. If he means "go GPL" → vendoring libKeyFinder is the fastest proven key detector and the cleanest expression of the decision. If staying Apache → spike the reimplement first. *Recommend: vendor libKeyFinder behind the optional `[ai-local]` extra IF the GPL-on-client tradeoff is accepted, because accuracy here is safety-critical (wrong key = harmonic slop = release blocker).*

## II.3 — BEATGRID / BPM ANALYZER ★★★★ (split: metadata=free, audio=hard)

**Mixxx path:** `track/beatutils.cpp:51-429` (the readable Stage-D grid fitter: const-region detection, BPM rounding ladder, adjustPhase) + `analyzer/plugins/analyzerqueenmarybeats.cpp` → **qm-dsp `TempoTrackV2`** (GPL-2.0+, in `lib/qm-dsp`, [c4dm/qm-dsp](https://github.com/c4dm/qm-dsp)).

**Vibemix gap:** `audio/grid.py::BeatGrid` type exists; **NO producer** (GOLD-WIRING g14). `from_anlz()` (H2, ~15 lines) gives Rekordbox/Serato/Traktor/Engine users an *exact* grid from the readers above **for free** — this is where the readers and DSP converge: *the reader IS the beatgrid producer for the majority case.*

**Straight-copy question:** the `beatutils.cpp` Stage-D fitter is fully-readable GPL C++ — going GPL lets us copy it directly (~430 lines). But it's short numeric algorithm (math, not authored expression) → already clean-room-specced in c297207c §3.1 with the divide-by-zero guard Mixxx omits. The **beat *tracker* (qm-dsp) is NOT worth GPL** — reimplement from complex-spectral-difference literature OR drop in the **MIT Beat-This ONNX** (fits our `cue_detr.py` pattern, stays torch-free). **VERDICT: ship `from_anlz()` + reader-fed grids now (free via Part I); spike audio detection separately; no GPL needed.**

## II.4 — SYNC / PHASE ENGINE ★★★ (half already ported)

**Mixxx path:** `engine/controls/bpmcontrol.cpp:479/572/756/1134` (`calcSyncAdjustment` banded corrector: 0.01 lock / 0.2 trainwreck / 0.7 gain / ±0.02 slew / ±0.05 cap; `getNearestPositionInPhase`), `synccontrol.cpp:290` (octave fold). GPL-2.0+ but pure short numeric algorithm.

**Vibemix status:** static-comparison half **DONE** (`learn/beatmatch_judge.py::_phase_error`, `_octave_fold_multiplier` — already clean-room ported). Gap = the *corrective* controller (the "nudge +0.7%" coach line, H4) + live producer. **Octave fold also fixes a real live bug:** `next_suggestion.py:163` BPM filter has no fold → rejects valid 174↔87 pairings. **VERDICT: clean-room the corrector (~30 lines numpy), no GPL — the bands are documented thresholds.**

## II.5 — AUTODJ + KEY-AWARE MIXING ★★★ (planner DONE, driver missing)

**Mixxx path:** `library/autodj/autodjprocessor.cpp:1251/1363/~860-882` (transition planner + the ramp law) + `enginexfader.cpp:66-77` (equal-power crossfader curve). GPL-2.0+, scalar arithmetic.

**Vibemix status:** planner + curve **DONE** (`state/transition_clock.py:192`, `audio/xfade.py` — "faithful clean-room ports"). Gap = the real-time crossfader-ramp *driver* ("Ghost Line") that makes `MiniDeck` genuinely auto-mix + the transition-timing grader (H6). **VERDICT: clean-room arithmetic, no GPL. This is the "own practice player" vision's auto-mix half.**

## II.6 — CROSSFADER CURVE MATH ★★ (already ported; recovered ALT3)

`enginexfader.cpp:66` scaling math — already in `audio/xfade.py`. The d9ddbeed ALT3 packet specs the full curve family (constant-power, additive, scratch). Low marginal leverage (we have the curve we use). No GPL needed.

## II.7 — WAVEFORM / SPECTRAL ANALYSIS (RGB band split) ★★ (recovered ALT5)

**Mixxx path:** `analyzer/analyzerwaveform.cpp` + the RGB filtered-overview (low/mid/high band energy → R/G/B per pixel column). GPL-2.0+.

**Vibemix relevance:** we already do band-energy via `audio/band_features.py::band_energy_ratios` (sub/low/mid/high rfft). The RGB *overview* is a UI feature (the "Deck Speaks" amber rule could ignite per-band color) — **NOT a coaching primitive.** The *analysis* (3-band split) we already own. **VERDICT: low priority; it's a visual nicety, not intelligence. The band-split math is ours already; no GPL.**

## II.8 — LOOP / BEATJUMP PERFORMANCE ENGINE ★ (recovered ALT4)

`engine/controls/loopingcontrol.cpp` — beat-quantized loop in/out, beatjump, loop-roll. Relevant ONLY to the "own practice player" (MiniDeck) vision; needs `MiniDeck.seek()` (private cursors, no write path today — GOLD-WIRING notes this). Defer until the practice-deck loop (H1) is built. No GPL needed (quantize = `closest_beat` math we have).

## II.9 — CONTROLLER-MAPPING JS ENGINE + DEVICE CATALOG ★★★ (recovered ALT2 — underrated)

**Mixxx path:** `src/controllers/` + the `QJSEngine` mapping runtime ([New controller system wiki](https://github.com/mixxxdj/mixxx/wiki/New-controller-system)) + **the `res/controllers/` mapping catalog = hundreds of community-maintained device maps** (`<controller>.midi.xml` + `<controller>.js`). GPL-2.0+ for the engine; the **mapping XML/JS files are individually contributed** (mixed licenses, mostly permissive-intent community maps).

**Vibemix gap:** we ship ~10 hand-mapped controllers (`midi/profiles/`, CLAUDE.md "10-controller catalog"). Mixxx has **hundreds.** The *mappings* are the asset — each `.midi.xml` documents exactly which CC/note each knob/fader/jog emits for a real device. **VERDICT: don't port the JS *engine* (GPL, and our MIDI decode is `mido`-based + simpler). MINE the mapping *catalog* — each Mixxx device map is a free, tested spec for translating that controller's MIDI into our move vocabulary** (`killed/_low:/_filter:/xfader`). This is a *data* harvest, not a code port: read Mixxx's `<control>` → `<status>/<midino>` mappings, transcribe the CC layout into our profile format. Per-device ~30 min of transcription. **Effort: catalog-expansion is linear in devices we care about; the d9ddbeed ALT2 packet has the extraction recipe.** This directly fills the "~10 controllers" → "the controller everyone actually owns" gap, and richer MIDI maps feed the `recent_moves` evidence that the EQ keystone (II.1) grounds.

---

## III — THE RANKING (whole arsenal by leverage / port-cost)

| Rank | Item | Class | Effort | GPL needed? | Why |
|---|---|---|---|---|---|
| **1** | **Serato reader** (crates+DB+GEOB) | READER | ~2d | NO (clean-room) | Onboarding wedge, huge base, inverts code we own |
| **2** | **Rekordbox master.db** (flip policy) | READER | ~1d | NO (MIT dep shipped) | Kills XML-export friction, largest base |
| **3** | **Traktor .nml reader** | READER | ~0.5d | NO (XML) | Cheapest reader; Francesco's base |
| **4** | **EQ-move keystone** `eq_move_model.py` | DSP | ~1d | NO (RBJ public) | The R-SLOP narrator→coach unlock |
| **5** | **Engine m.db reader** | READER | ~1.5d | NO (plain SQLite) | Denon/standalone segment |
| **6** | **`BeatGrid.from_anlz()`** + reader-fed grids | DSP | ~0.5d | NO | Free exact grid for ALL reader users; closes g14 |
| **7** | **Controller-map catalog harvest** | DATA | linear | NO (data, not code) | 10→hundreds of devices; feeds move evidence |
| **8** | **Key detection (libKeyFinder)** | DSP | 2d vendor / 1wk reimpl | **YES if vendor** | Tag-less harmonic; THE genuine GPL decision |
| **9** | **Sync corrector** (`calcSyncAdjustment`) | DSP | ~0.5d | NO | "nudge +0.7%" coach + octave-fold bugfix |
| **10** | **AutoDJ ghost-line driver** | DSP | ~1d | NO | Practice-player auto-mix + blend grade |
| 11 | Rekordbox PDB/USB reader | READER | ~1d | NO | Plug-in-USB ingest |
| 12 | VirtualDJ reader | READER | ~0.5d | NO | Long-tail base |
| 13 | Waveform RGB split | UI | ~1d | NO | Visual nicety, not intelligence |
| 14 | Loop/beatjump engine | DSP | ~1d | NO | Needs MiniDeck.seek first; defer |
| 15 | iTunes XML reader | READER | ~0.5d | NO | Dying format; on-demand only |

---

## IV — THE STRAIGHT ANSWER (readers vs DSP — which is the bigger prize)

**The library-format READERS are the bigger prize, and it's not close — for four reasons:**

1. **Market gating.** vibemix today serves *one* DJ ecosystem at the door (Rekordbox-XML, and only if the user manually exported). Serato + Traktor + Engine + live-master.db opens the front door to the *majority* of DJs. The DSP makes the co-host smarter for users we already have; the readers *get us users.* That's the discovery/onboarding wedge the strategy memos call the hero.

2. **License posture.** The readers are almost entirely **Apache-clean** — XML, plain SQLite, and a trivial TLV, reimplemented from public Mixxx-wiki specs, with MIT/MPL Python ports only as cross-checks. The "go GPL" question barely applies to them. The DSP is where GPL actually bites (libKeyFinder, qm-dsp) — and the highest-leverage DSP item (the EQ keystone) needs no GPL anyway because RBJ is public-domain math.

3. **Effort/risk profile.** A "Universal Ingest" milestone (Serato + Traktor + Engine + master.db) is ~5 focused days of *parsing* — low-risk, no ML, no spike, no DSP accuracy gamble. The deepest DSP wins (key detection, audio beatgrid) carry genuine multi-week spike risk where a confidently-wrong output *poisons* the anti-slop moat.

4. **Synergy.** Every reader *also* delivers beatgrids + cues + keys — so the readers are simultaneously the cheapest **beatgrid producer** (II.3), **key source** (sidestepping II.2's GPL question for tagged libraries), and **cue ground-truth** (`cue_agreement.py`) for the Earned skill-tree. One parsing milestone feeds three DSP gaps for free.

**The one caveat that keeps the DSP relevant:** the **EQ-move keystone (II.1)** is the single thing that converts the live co-host from *narrator* to *coach* (per GOLD-WIRING/RED-TEAM), and it's cheap (~1d) and GPL-free. So the honest sequencing is: **build the EQ keystone (it's the product's core-value unlock) AND start the Universal Ingest milestone (it's the growth unlock) in parallel — they don't collide** (one is `intel/`, the other is `library/sources/`). Then make the **libKeyFinder GPL decision** as a deliberate, isolated call when tag-less ingest becomes the bottleneck.

---

### Sources
- Mixxx LICENSE (GPL-3.0+): https://github.com/mixxxdj/mixxx/blob/main/LICENSE · https://github.com/mixxxdj/mixxx/pull/3476
- Serato format wikis: https://github.com/mixxxdj/mixxx/wiki/Serato-Database-Format · https://github.com/mixxxdj/mixxx/wiki/Serato-Metadata-Format · PRs https://github.com/mixxxdj/mixxx/pull/2480 https://github.com/mixxxdj/mixxx/pull/2495 https://github.com/mixxxdj/mixxx/pull/3421
- triseratops (MPL-2.0): https://github.com/Holzhaus/triseratops · serato-tools: https://github.com/bvandrc/serato-tools · python-serato-crates: https://github.com/stephanlensky/python-serato-crates
- Rekordbox: crate-digger https://github.com/Deep-Symmetry/crate-digger · rekordbox_anlz.ksy https://github.com/Deep-Symmetry/crate-digger/blob/main/src/main/kaitai/rekordbox_anlz.ksy · pyrekordbox (MIT) https://github.com/dylanljones/pyrekordbox · rekordcrate https://github.com/Holzhaus/rekordcrate · Mixxx PRs https://github.com/mixxxdj/mixxx/pull/2119 https://github.com/mixxxdj/mixxx/pull/13293
- Traktor: traktorfeature.cpp https://github.com/mixxxdj/mixxx/blob/main/src/library/traktor/traktorfeature.cpp · traktor-nml-utils https://github.com/wolkenarchitekt/traktor-nml-utils
- Engine DJ: wiki https://github.com/mixxxdj/mixxx/wiki/Engine-Library-Format · libdjinterop (LGPL-3.0+) https://github.com/xsco/libdjinterop
- VirtualDJ: https://github.com/mixxxdj/mixxx/wiki/Virtual-Dj-Cue-Storage-Format
- libKeyFinder (GPL-3.0): https://github.com/mixxxdj/libkeyfinder
- qm-dsp (GPL-2.0+): https://github.com/c4dm/qm-dsp
- Controller system: https://github.com/mixxxdj/mixxx/wiki/New-controller-system
