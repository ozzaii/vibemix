# Vibe Mix Slice 0 — Rekordbox cue write-back spike verdict

> Scaffolded verdict. The automated round-trip (Tasks 1-5) proves the data path;
> the real-Rekordbox import + controller-trigger check is a Kaan-action discharge
> ("test together" bar from `.planning/notes/vibe-mix-concept-brief.md`).
> Until that runs, status stays `engineering-scaffolded`.

**Status:** engineering-scaffolded
**Run date:** _____
**Operator:** Kaan (+ Francesco for the real-set trigger check)
**Scaffold landed:** 2026-05-20

State machine:
`engineering-scaffolded` → `kaan-action-discharge` → `verdict-written`.

---

## API confirmed (Task 1 finding — installed pyrekordbox 0.4.4)

- `RekordboxXml.add_track(...)` → `add_track(location="file://...")` — **lowercase positional**, NOT `Location=`.
- `Track.add_mark(...)` → `add_mark(Name="DROP", Type="cue", Start=64.0, End=None, Num=3)` — **capitalized kwargs**.
- `xml.save(...)` → `xml.save(path="out.xml", indent=None, encoding="utf-8")`.
- Read-back: `track.marks` (attribute), `mark.Name` / `mark.Start` / `mark.Num`.
- Minimal `<TRACK>` attributes the production reader requires: **none beyond `location`** — `TrackID` auto-assigns ("1", "2", ...), and `vibemix.library.rekordbox.RekordboxLibrary.load_xml` reads the minimal track + its marks cleanly (verified in `test_roundtrip.py`).

- **macOS Location quirk (found while running the demo):** `pyrekordbox.rbxml.encode_path`
  emits `"file://localhost/" + quote(path)`. A POSIX absolute path (`/Users/...`) yields a
  DOUBLE slash (`file://localhost//Users/...`) that does NOT match Rekordbox's canonical
  `file://localhost/Users/...` — import would fail to attach cues to the real file.
  `cue_writer._rb_location` strips one leading slash on POSIX to compensate; guarded by
  `test_location_encoding.py`. This is exactly the class of write-back gotcha the spike exists to catch.

**Headline finding:** Direct `master.db` writes are NOT viable (no stable write API in 0.4.4; SQLCipher; ANLZ/PCOB sync; VBR offset bug — GitHub discussion #113). The **collection.xml round-trip is the safe, working path** and is non-destructive by construction.

## Automated proof — all green (`9 passed`)

- [x] Confidence gate drops sub-0.85 cues (`test_confidence_gate.py`, 3 tests)
- [x] Writer backs up before overwrite; never mutates source (`test_backup_nondestructive.py`, 3 tests)
- [x] Written cues read back correctly through production `RekordboxLibrary` (`test_roundtrip.py`, 1 test)
- [x] Installed-version write API pinned (`test_api_probe.py`, 1 test)
- [x] Location serializes to Rekordbox-canonical single-slash URI (`test_location_encoding.py`, 1 test)

## Demo artifact (run `python -m spikes.vibe_mix_slice0.demo`)

Writes `~/Desktop/vibemix-cues-demo.xml` for the two `~/Music/PioneerDJ/Demo Tracks`:
6 cues kept, 1 gated out (BREAK @ 0.55 confidence). Drag into Rekordbox to feel it.

## Kaan-together import test (manual — the real gate)

Procedure:
1. Pick 3 real tracks from your library. Hand-author a `CueCandidate` list with
   known positions (e.g. the actual drop in each, eyeballed in Rekordbox first).
2. `write_cues(cands, "vibemix-cues.xml")`.
3. In Rekordbox: File → Import Collection / drag the XML in. Import as a NEW
   playlist (do NOT merge into your main collection on the first run).
4. Open each track. Confirm:

- [ ] Cues appear on the correct tracks
- [ ] Cue positions are on the intended beat (within a few ms — note any drift)
- [ ] Hot-cue slot numbers (1-8) match what we wrote
- [ ] Cues trigger cleanly on the DDJ-FLX4 (no off-beat fire)
- [ ] Original collection is untouched until you explicitly accept the import
- [ ] VBR/ABR MP3s: any position drift vs CBR/FLAC? (research flagged VBR offset risk)

## Verdict

> **Are auto-cues in the Vibe Mix launch?**  YES / NO / NEEDS-WORK

Decision: __________
Rationale: __________
If NEEDS-WORK, the specific failure mode to fix before re-test: __________
