---
spike: 003
name: rekordbox-data-exhaust
type: standard
validates: "Given a laptop-only rekordbox install, when we read its local files/DB, then we recover per-track structure (beatgrid/cues/phrases) + library + track-change events without hardware or screen vision"
verdict: PARTIAL→VALIDATED (static rich data works now; live transport needs a fragile memory-reader)
related: [001, 002]
tags: [ingest, rekordbox, anlz, master-db, rkbx-link, phrase-analysis, auto-cue]
---

# Spike 003: rekordbox local data exhaust (no hardware, no vision)

Kaan's directive: drop the screen-vision path; find where rekordbox *writes/exposes*
data locally and read that. Probed his rig + researched the methods.

## What This Validates

Given laptop-only rekordbox (Kaan's rig: rekordbox **7.2.9**, Apple Silicon), what
ground-truth can we read from local files/DB, no Pioneer hardware, no screen scrape?

## Findings — the data-exhaust map

| Source | Encrypted? | Live? | Content | Status |
|--------|-----------|-------|---------|--------|
| **ANLZ files** (`USBANLZ/**/ANLZ*.DAT/.EXT/.2EX`) | no | static (per analyze) | **beatgrid (PQTZ/PQT2), cues (PCOB/PCO2), phrase structure (PSSI)**, waveforms | **WORKS NOW** via `pyrekordbox.anlz` |
| **master.db** | SQLCipher (static shared key) | WAL writes live | full library + **play history** (`djmdSongHistory`) + cues; **no live transport table** | blocked: `sqlcipher3` has no py3.14 wheel (needs `brew install sqlcipher` + source build) |
| networkRecommend.db / networkAnalyze6.db | no | static | analyze manifest (`manage_tbl`: SongID→ANLZ path, phrase/key/bpm flags) | readable now (stdlib sqlite3) |
| **rkbx_link → OSC** | n/a | **live per-deck** | BPM(current+orig), beat/bar phase, position, track, **phrase/current** | not built; fragile (see below) |
| Ableton Link (spike 002) | n/a | live, weak | one global tempo/phase | PARTIAL |
| PRO DJ LINK (spike 001) | n/a | hardware-only | full per-deck | INVALIDATED laptop-only |

### Key facts from research (agent ac325863)
- **master.db has NO "now playing"/transport table** — live deck state lives only in
  rekordbox RAM. The live-ish signal is polling `djmdSongHistory` (read-only): gives
  **TRACK_CHANGE + track identity** (join `ContentID`→`djmdContent` for bpm/key/genre)
  at ~seconds latency. No beat/position/pitch/deck. Robust, survives RB updates.
  SQLCipher key is a single static shared passphrase → `python -m pyrekordbox download-key`.
- **rkbx_link** reads rekordbox **process memory** via Cheat-Engine-derived per-version
  offsets, re-broadcasts over OSC. Richest live source (per-deck bpm/beat/phase/position/
  **phrase labels**) BUT **fragile per RB version**; macOS free build offsets = **RB 7.2.8
  Apple-Silicon only** (Kaan is **7.2.9** → likely needs licensed offsets or re-derive),
  and macOS process-memory read needs elevated `task_for_pid` entitlements.
- Skip: rekordboxAgent IPC (no stable schema), MIDI-LED decode (sparse), OS2L/ShowKontrol/
  SoundSwitch (Pro-DJ-Link/hardware-gated).

## Live evidence captured

ANLZ read of a 180-BPM hardtechno track ("Nexus Infiltration - MA_Warhead"):
- Beatgrid: 180.00 BPM, 789 beats.
- **PSSI phrase structure: 23 segments**, mood=2 (mid), boundaries at e.g. intro@0s,
  chorus@91s, bridge@133.7s, chorus@143s, outro@255s. Labels use rekordbox's pop
  vocab (intro/verse1-6/bridge/chorus/outro) — semantically off for techno, but the
  **segment boundaries are real and non-trivial**. Whether they align with the DJ's
  felt intro/build/breakdown/drop is an **ear-check** (open).
- Cues: none on this track (Kaan's own production, no cues set) — cue richness depends
  on the user having set cues; phrase analysis is automatic and always present.

## Recommended architecture (layered, graceful degradation)

1. **Floor (robust, ship-safe):** track identity (we already have via now-playing +
   MIDI deck inference; optionally upgrade with `djmdSongHistory` poll) → **look up that
   track's ANLZ** for full beatgrid + cues + phrase structure. The co-host then knows
   the *entire structure of the loaded track* and can anticipate ("breakdown in 16 bars").
   Survives RB updates, laptop-only, no hardware.
2. **Rich live layer (best-effort):** `rkbx_link` OSC for live per-deck beat-phase/position
   → true beat-relative feedback ("you cut off-beat"). **Hard-gate on RB version**; degrade
   to floor + Ableton Link clock when offsets are missing/broken (they will break on RB updates).

## Unlocks

- **Auto-cue moat shortcut:** rekordbox already computed phrase structure (PSSI) for every
  track — could short-circuit the planned server-side CUE-DETR engine *if* accurate on
  hardtechno (ear-check). See `project_auto_cue_engine`.
- **Cue-anchored embeddings (Phase 89):** anchor on *real* rekordbox cues/phrases instead
  of DSP-guessed excerpts.
- **TRACK_CHANGE ground truth** + full metadata, no now-playing-title guessing.
- **Beat-relative feedback + anticipation** (with the rich layer).

## Open / next
- **Ear-check:** do PSSI phrase boundaries match Kaan's felt structure on hardtechno?
- master.db live read: needs `brew install sqlcipher` + source-built `sqlcipher3` (py3.14).
- rkbx_link on RB 7.2.9 macOS: offset availability unknown (free = 7.2.8).
