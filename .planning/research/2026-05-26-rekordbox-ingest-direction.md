# Direction: rekordbox local data ingest → ground-truth structure floor

**Date:** 2026-05-26 · **Status:** pre-roadmap research (feeds a future milestone) ·
**Spikes:** `.planning/spikes/001-003` · **Memory:** `project_local_deck_ingest_spike_findings`

## Problem

The live co-host *infers* what the DJ does (MIDI moves + now-playing title + 6 s
audio-autocorrelation BPM). That inference ceiling is why feedback is shallow. Goal:
read **ground-truth** instead of guessing. Kaan dropped the screen-vision path; we mine
rekordbox's local data exhaust.

## What's viable (measured on Kaan's rig — rekordbox 7.2.9, Apple Silicon, 487 analyzed tracks)

| Source | Viable? | Evidence |
|--------|---------|----------|
| **ANLZ files** (beatgrid PQTZ, cues PCOB/PCO2, **phrase PSSI**) | ✅ **YES, now** | plain/unencrypted, `pyrekordbox.anlz`, **92% of library has PSSI**, 0 parse errors |
| master.db (library + play history) | ⚠️ later | SQLCipher static key (`download-key`); **no live transport table** (history only); `sqlcipher3` has no py3.14 wheel → needs `brew install sqlcipher` |
| **rkbx_link** (live per-deck beat-phase) | ❌ **dead on 7.2.9 macOS** | free offsets = 7.2.8 only; licensed skips 7.2.9 (Windows-oriented); needs root/`task_for_pid` entitlement |
| Ableton Link | ⚠️ weak | one global tempo, only if DJ Link-locks a deck |
| PRO DJ LINK | ❌ laptop-only / ✅ with hardware | 0/173k packets laptop-only; full per-deck **with CDJs on LAN** (club segment) |

**Conclusion:** no clean *live beat-phase* path on Kaan's setup. The realistic architecture
is an **offline per-track structure floor** (ANLZ) joined to **live track-identity** (which
we already resolve). Live beat-phase ground truth is a hardware-DJ (PRO DJ LINK) feature, parked.

## The data: rekordbox phrase structure (PSSI)

Per-track song structure, beat-indexed, ~19 segments median. `mood` field sets the label
vocabulary; **Kaan's library is 77% high-mood (346), 22% mid (101), 2 low** — most tracks
get the clean EDM vocab that maps directly to our cue labels:

| PSSI (high mood) | → vibemix `CueLabel` |
|------------------|----------------------|
| Intro 1/2 | `intro` |
| **Up 1/2/3** (k1/k2 flags on kind=2) | `build` |
| **Down** (kind=3) | `breakdown` |
| **Chorus 1/2** (kind=5) | `drop` |
| Outro 1/2 (kind=6) | `outro` |

Mid-mood (kind 1=Intro, 2-7=Verse, 8=Bridge, 9=Chorus, 10=Outro) is pop-vocab — boundaries
still real, labels approximate (Bridge≈breakdown, Chorus≈drop). Low mood (2 tracks) ignore.

**Note:** Kaan sets **no hot cues** (0 PCO2 across the library) — so phrases ARE the data,
not DJ cues. The DSP cue heuristic (`cue_detect.py`) that failed on hardtechno is replaced
by this, not augmented.

## Architecture map (insertion points — shape, lines may drift post-debloat)

- **`cue_types.py` (`CueAnchor`)** — the contract: `label/start_s/end_s/confidence/source`.
  Add `source="anlz"`. PSSI → CueAnchor is a direct mapping.
- **NEW `library/anlz_ingest.py`** — `find_anlz(file) → dir`, `parse → AnlzMeta(beatgrid,
  cues, phrases)`, `phrases_to_anchors(meta, dur) → list[CueAnchor]`. Lazy-imported.
- **`library/excerpt.py::anchors_for_track`** — insert **ANLZ tier** between DJ-cue and
  auto-DSP: DJ cues → **ANLZ phrases** → heuristic fallback. (For Kaan, DJ tier is empty →
  ANLZ is primary.)
- **`library/ingest.py` / `embed.py`** — unchanged; cue-anchored embeddings just get real
  phrase-boundary windows instead of DSP-guessed ones.
- **`library/cue_detect.py`** — demoted to fallback when no ANLZ.
- **`state/deck_poller.py` + `event_detector.py`** — loaded-track → cache its phrase map on
  `DeckTrack` → emit `PHRASE_APPROACHING` ("breakdown in 16 bars") for anticipatory coaching.
- **Path resolution (DB-free):** walk `USBANLZ/**/ANLZ0000.EXT`, read `PPTH` (UTF-16-BE;
  on local libs it's `?/<basename>`), join to `collection.xml` tracks by **basename**
  (handle collisions). Use ANLZ `.EXT` specifically for PSSI (phrases are not in the XML).

## Phased plan (build AFTER tonight's codebase debloat)

- **Phase A — ANLZ structure ingest (offline, library).** `anlz_ingest.py` + PSSI→CueAnchor
  mapping + USBANLZ/PPTH index + excerpt.py ANLZ tier. Replaces DSP cue heuristic; feeds
  cue-anchored embeddings with real boundaries. **Highest value, lowest risk, no live deps.**
  Unlocks the auto-cue moat shortcut + better library/set-builder.
- **Phase B — live phrase anticipation.** loaded-track → ANLZ phrase map on `DeckTrack` →
  `PHRASE_APPROACHING` events. Needs track-identity (have it) + a position/beat estimate for
  the countdown (now-playing position, or Ableton Link clock if Link-locked).
- **Phase C — hardware ground truth (deferred, club segment).** PRO DJ LINK ingest (spike-001
  probe built) when CDJs are on the LAN. Not for laptop-only.

## Open questions / risks

1. **Ear-check (the gate):** do PSSI phrase boundaries match Kaan's *felt* intro/build/
   breakdown/drop on real tracks? Audition: pick a track, jump to the boundary timestamps.
   77% high-mood is encouraging but unverified by ear.
2. High-mood label mapping (Up→build, Chorus→drop, Down→breakdown) needs ear validation —
   "Chorus" may be the main section, not always the drop.
3. Mid-mood 22% — accept approximate labels or fall back to DSP for those?
4. PSSI XOR-masking exists in some rekordbox exports; Kaan's parses clean (0 errors) but other
   users' versions may need de-masking — gate gracefully.
5. PPTH basename-only matching on local libraries → duplicate-filename collisions.
6. master.db live history poll (Phase B+ nicety) blocked on `sqlcipher3`/py3.14 — defer.
