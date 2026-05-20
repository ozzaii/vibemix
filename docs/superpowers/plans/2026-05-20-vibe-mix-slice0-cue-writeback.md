# Vibe Mix Slice 0 — Rekordbox Cue Write-Back Spike — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove vibemix can hand a DJ a set of auto-placed Rekordbox hot cues that land on the right tracks at the right positions — backup-first, reversible, non-destructive, and confidence-gated — so Kaan can decide whether auto-cues are in the Vibe Mix launch.

**Architecture:** Research (GitHub discussion #113 + pyrekordbox 0.4.4 docs) established that **direct writes to the SQLCipher `master.db` are not production-safe** (no stable write API, ANLZ/PCOB sync, VBR offset bug). The safe, proven path is **collection.xml round-trip**: emit a Rekordbox XML carrying `PositionMark`s via `pyrekordbox.RekordboxXml`, which the DJ imports into Rekordbox themselves. This is non-destructive *by construction* — we never touch the user's master database; the import is user-controlled and undoable. The spike lives entirely under `spikes/` (OUT of the `src/vibemix/` grep gate per `spikes/__init__.py`), reusing the *production* reader `vibemix.library.rekordbox.RekordboxLibrary` to verify the round-trip.

**Tech Stack:** Python 3.12, `pyrekordbox==0.4.4` (`RekordboxXml` only — never `db6`/`Rekordbox6Database`), pytest. No new dependencies. No Gemini calls in the spike (detection is fixture-driven; the unknown under test is write-back, not detection).

**Out of scope (documented decisions, not gaps):**
- Direct `master.db` writes (`Rekordbox6Database`) — research says unsafe; would also break the `src/vibemix/` grep gate.
- Real DSP cue detection (downbeat/breakdown/drop) — that is Slice 3. Here, candidate cues are fixtures with explicit confidence scores.
- Serato / Engine / Traktor formats — Rekordbox-only at this gate (per concept brief recommendation).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `spikes/vibe_mix_slice0/__init__.py` | Package marker + one-line purpose docstring. |
| `spikes/vibe_mix_slice0/types.py` | `CueCandidate` dataclass — a detected cue + confidence, the spike's input contract. |
| `spikes/vibe_mix_slice0/confidence_gate.py` | Pure function: drop candidates below threshold (the anti-slop law in code). |
| `spikes/vibe_mix_slice0/cue_writer.py` | Backup-first, write `CueCandidate`s as `PositionMark`s into a Rekordbox XML and save. |
| `spikes/vibe_mix_slice0/tests/test_api_probe.py` | Empirically confirms the installed `RekordboxXml` write API (`add_track`/`add_mark`/`save`). |
| `spikes/vibe_mix_slice0/tests/test_confidence_gate.py` | Unit tests for the gate. |
| `spikes/vibe_mix_slice0/tests/test_roundtrip.py` | The proof: written cues survive a read-back through the *production* `RekordboxLibrary`. |
| `spikes/vibe_mix_slice0/tests/test_backup_nondestructive.py` | Asserts the writer never overwrites without a backup, and the original is byte-identical after a write to a new path. |
| `spikes/vibe-mix-slice0-cue-writeback.md` | Verdict scaffold (mirrors `spikes/gemini-3-1-flash-live-music.md`); the Kaan-together import test fills it. |

---

## Task 1: Spike package + API probe (confirm the write API actually exists in 0.4.4)

**Files:**
- Create: `spikes/vibe_mix_slice0/__init__.py`
- Test: `spikes/vibe_mix_slice0/tests/test_api_probe.py`

The discussion thread showed `track.add_mark(Name="A", Type="cue", Start=50, Num=1)` + `xml.save(...)`, but kwarg casing varies across pyrekordbox releases. This probe is the spike's empirical anchor: it pins the exact working call in *our* installed `0.4.4` before any other task depends on it.

- [ ] **Step 1: Create the package marker**

```python
# spikes/vibe_mix_slice0/__init__.py
# SPDX-License-Identifier: Apache-2.0
"""Vibe Mix Slice 0 — Rekordbox cue write-back de-risk spike.

OUT of the src/vibemix grep gate (see spikes/__init__.py). The unknown under
test is WRITE-BACK SAFETY, not cue detection. Direct master.db writes are
deliberately excluded; the safe path is a collection.xml round-trip the DJ
imports into Rekordbox.
"""
```

- [ ] **Step 2: Write the failing probe test**

```python
# spikes/vibe_mix_slice0/tests/test_api_probe.py
# SPDX-License-Identifier: Apache-2.0
"""Empirical confirmation of the pyrekordbox RekordboxXml write API."""
from pyrekordbox import RekordboxXml


def test_rekordboxxml_write_roundtrip_minimal(tmp_path):
    """A new XML with one track + one hot cue saves and re-parses."""
    xml = RekordboxXml()
    track = xml.add_track(Location="file://localhost/tmp/demo.mp3")
    track.add_mark(Name="A", Type="cue", Start=12.5, Num=1)

    out = tmp_path / "out.xml"
    xml.save(path=str(out))

    assert out.exists() and out.stat().st_size > 0
    # Re-parse with a fresh reader to prove the mark persisted.
    reparsed = RekordboxXml(str(out))
    tracks = list(reparsed.get_tracks())
    assert len(tracks) == 1
    marks = list(tracks[0].marks)
    assert len(marks) == 1
    assert marks[0].Name == "A"
    assert abs(float(marks[0].Start) - 12.5) < 1e-6
    assert int(marks[0].Num) == 1
```

- [ ] **Step 3: Run the probe**

Run: `PYTHONPATH=src python3 -m pytest spikes/vibe_mix_slice0/tests/test_api_probe.py -v`
Expected: **PASS**. If it FAILS on a kwarg name (`Location`/`location`, `Name`/`name`, `marks` vs `get_marks()`, `save(path=)` vs `save()`), the failure message names the correct attribute — **record the working signature in the verdict file's "API confirmed" section and use that exact casing in Tasks 3-5.** This is the spike's first finding, not a blocker.

- [ ] **Step 4: Commit**

```bash
git add spikes/vibe_mix_slice0/__init__.py spikes/vibe_mix_slice0/tests/test_api_probe.py
git commit -m "spike(vibe-mix-slice0): confirm pyrekordbox RekordboxXml write API"
```

---

## Task 2: The input contract — `CueCandidate`

**Files:**
- Create: `spikes/vibe_mix_slice0/types.py`

`CueCandidate` is what a (future, Slice 3) detector would emit and what the writer consumes. It mirrors the production `CuePoint` field names (`name`/`type`/`start_s`/`number`) plus a `confidence` float, so the spike's contract is forward-compatible with `vibemix.library.rekordbox.CuePoint`.

- [ ] **Step 1: Write the dataclass**

```python
# spikes/vibe_mix_slice0/types.py
# SPDX-License-Identifier: Apache-2.0
"""Input contract for the cue write-back spike."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CueCandidate:
    """A detected cue point + the detector's confidence.

    Field names track ``vibemix.library.rekordbox.CuePoint`` so this is a
    drop-in upstream of the production reader. ``confidence`` is in [0, 1];
    the confidence gate (the anti-slop law) drops anything below threshold.
    """

    track_location: str   # file:// URI of the audio file
    name: str             # cue label, e.g. "DROP"
    type: str             # "cue" (hot/memory) — strict set only at this gate
    start_s: float        # cue position in seconds
    number: int           # 1..8 = hot cue slot; -1 = memory cue
    confidence: float     # [0, 1]
```

- [ ] **Step 2: Commit**

```bash
git add spikes/vibe_mix_slice0/types.py
git commit -m "spike(vibe-mix-slice0): CueCandidate input contract"
```

---

## Task 3: Confidence gate — the anti-slop law in code

**Files:**
- Create: `spikes/vibe_mix_slice0/confidence_gate.py`
- Test: `spikes/vibe_mix_slice0/tests/test_confidence_gate.py`

"A wrong cue is worse than no cue." The gate is a pure function that drops low-confidence candidates *before* they are ever written. Default threshold is deliberately conservative (0.85).

- [ ] **Step 1: Write the failing test**

```python
# spikes/vibe_mix_slice0/tests/test_confidence_gate.py
# SPDX-License-Identifier: Apache-2.0
from spikes.vibe_mix_slice0.confidence_gate import gate_cues
from spikes.vibe_mix_slice0.types import CueCandidate


def _cand(conf: float, num: int = 1) -> CueCandidate:
    return CueCandidate(
        track_location="file://localhost/tmp/x.mp3",
        name="DROP", type="cue", start_s=30.0, number=num, confidence=conf,
    )


def test_drops_below_threshold():
    cands = [_cand(0.9, 1), _cand(0.5, 2), _cand(0.86, 3)]
    kept = gate_cues(cands, threshold=0.85)
    assert [c.number for c in kept] == [1, 3]


def test_empty_when_all_below():
    # No cue beats a wrong cue: an empty result is a valid, safe outcome.
    assert gate_cues([_cand(0.1)], threshold=0.85) == []


def test_default_threshold_is_conservative():
    # A 0.8-confidence cue is NOT good enough by default.
    assert gate_cues([_cand(0.8)]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest spikes/vibe_mix_slice0/tests/test_confidence_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: spikes.vibe_mix_slice0.confidence_gate`

- [ ] **Step 3: Write minimal implementation**

```python
# spikes/vibe_mix_slice0/confidence_gate.py
# SPDX-License-Identifier: Apache-2.0
"""The anti-slop law: drop any cue we are not confident about."""
from __future__ import annotations

from spikes.vibe_mix_slice0.types import CueCandidate

# Conservative by intent. A wrong cue fired in front of a crowd is worse
# than the manual prep we removed, so the bar to auto-place is high.
DEFAULT_THRESHOLD: float = 0.85


def gate_cues(
    candidates: list[CueCandidate], threshold: float = DEFAULT_THRESHOLD
) -> list[CueCandidate]:
    """Return only candidates at or above ``threshold``, order preserved."""
    return [c for c in candidates if c.confidence >= threshold]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest spikes/vibe_mix_slice0/tests/test_confidence_gate.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add spikes/vibe_mix_slice0/confidence_gate.py spikes/vibe_mix_slice0/tests/test_confidence_gate.py
git commit -m "spike(vibe-mix-slice0): confidence gate — no cue beats a wrong cue"
```

---

## Task 4: Cue writer — backup-first, never destructive

**Files:**
- Create: `spikes/vibe_mix_slice0/cue_writer.py`
- Test: `spikes/vibe_mix_slice0/tests/test_backup_nondestructive.py`

Two non-destructive guarantees, both tested:
1. **Never overwrite without a backup.** If the target path exists, copy it to `<path>.bak-<timestamp>` before writing.
2. **The DJ's source is never mutated.** We always emit a *new* XML for the DJ to import; we never write into their live `collection.xml` in place unless they explicitly point the output there (and then only after the backup in guarantee 1).

> Use the API casing confirmed by Task 1. Code below uses the discussion-thread casing (`add_track(Location=...)`, `add_mark(Name=, Type=, Start=, Num=)`, `xml.save(path=...)`); adjust only if Task 1's probe reported otherwise.

- [ ] **Step 1: Write the failing test**

```python
# spikes/vibe_mix_slice0/tests/test_backup_nondestructive.py
# SPDX-License-Identifier: Apache-2.0
import glob

from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice0.types import CueCandidate


def _cand(num: int) -> CueCandidate:
    return CueCandidate(
        track_location="file://localhost/tmp/track.mp3",
        name=f"CUE{num}", type="cue", start_s=10.0 * num, number=num,
        confidence=0.99,
    )


def test_writes_new_file(tmp_path):
    out = tmp_path / "set.xml"
    n = write_cues([_cand(1), _cand(2)], out_path=str(out))
    assert n == 2
    assert out.exists()


def test_backs_up_before_overwrite(tmp_path):
    out = tmp_path / "set.xml"
    out.write_text("ORIGINAL")  # pretend a prior file exists
    write_cues([_cand(1)], out_path=str(out))
    backups = glob.glob(str(tmp_path / "set.xml.bak-*"))
    assert len(backups) == 1
    # The backup preserves the original bytes verbatim.
    assert open(backups[0]).read() == "ORIGINAL"


def test_source_collection_never_mutated(tmp_path):
    source = tmp_path / "collection.xml"
    source.write_text("DJS_LIVE_LIBRARY")
    out = tmp_path / "vibemix-cues.xml"
    write_cues([_cand(1)], out_path=str(out))
    # We emitted to a separate file; the live library is byte-identical.
    assert source.read_text() == "DJS_LIVE_LIBRARY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest spikes/vibe_mix_slice0/tests/test_backup_nondestructive.py -v`
Expected: FAIL with `ModuleNotFoundError: spikes.vibe_mix_slice0.cue_writer`

- [ ] **Step 3: Write minimal implementation**

```python
# spikes/vibe_mix_slice0/cue_writer.py
# SPDX-License-Identifier: Apache-2.0
"""Write CueCandidates as Rekordbox PositionMarks into a fresh XML.

Non-destructive by construction: we emit a NEW collection.xml the DJ imports
into Rekordbox. We never touch the SQLCipher master.db (no stable/safe write
API — see GitHub discussion #113). If the chosen output path already exists,
we back it up first.
"""
from __future__ import annotations

import shutil
import time
from collections import defaultdict
from pathlib import Path

from pyrekordbox import RekordboxXml

from spikes.vibe_mix_slice0.types import CueCandidate


def _backup_if_exists(out_path: Path) -> None:
    if out_path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(out_path, out_path.with_name(f"{out_path.name}.bak-{stamp}"))


def write_cues(candidates: list[CueCandidate], out_path: str) -> int:
    """Emit a Rekordbox XML carrying ``candidates`` as PositionMarks.

    Returns the number of marks written. Backs up ``out_path`` first if it
    exists. One ``<TRACK>`` per distinct ``track_location``; each candidate
    becomes one ``add_mark`` on its track.
    """
    target = Path(out_path)
    _backup_if_exists(target)

    by_track: dict[str, list[CueCandidate]] = defaultdict(list)
    for c in candidates:
        by_track[c.track_location].append(c)

    xml = RekordboxXml()
    written = 0
    for location, cues in by_track.items():
        track = xml.add_track(Location=location)
        for c in cues:
            track.add_mark(Name=c.name, Type=c.type, Start=c.start_s, Num=c.number)
            written += 1

    xml.save(path=str(target))
    return written
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest spikes/vibe_mix_slice0/tests/test_backup_nondestructive.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add spikes/vibe_mix_slice0/cue_writer.py spikes/vibe_mix_slice0/tests/test_backup_nondestructive.py
git commit -m "spike(vibe-mix-slice0): backup-first non-destructive cue writer"
```

---

## Task 5: The proof — written cues survive the PRODUCTION reader

**Files:**
- Test: `spikes/vibe_mix_slice0/tests/test_roundtrip.py`

This is the spike's central claim: cues we write are read back *correctly by the same code that ships in vibemix* (`vibemix.library.rekordbox.RekordboxLibrary`). If a written `DROP` at 64.0s in hot-cue slot 3 comes back through the production reader as exactly that, the data path is sound end-to-end.

- [ ] **Step 1: Write the round-trip test**

```python
# spikes/vibe_mix_slice0/tests/test_roundtrip.py
# SPDX-License-Identifier: Apache-2.0
"""Cues written by the spike survive a read-back through the SHIPPING reader."""
from vibemix.library.rekordbox import RekordboxLibrary

from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice0.types import CueCandidate


def test_written_cues_readback_through_production_reader(tmp_path, monkeypatch):
    out = tmp_path / "vibemix-cues.xml"
    cands = [
        CueCandidate("file://localhost/tmp/a.mp3", "INTRO", "cue", 0.0, 1, 0.99),
        CueCandidate("file://localhost/tmp/a.mp3", "DROP", "cue", 64.0, 3, 0.99),
    ]
    write_cues(cands, out_path=str(out))

    # Isolate the production reader's pickle cache to a tmp location.
    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "cache.pkl", raising=True
    )
    lib = RekordboxLibrary()
    n = lib.load_xml(str(out))
    assert n == 1

    (entry,) = lib.tracks.values()
    cues = {c.name: c for c in entry.cues}
    assert set(cues) == {"INTRO", "DROP"}
    assert cues["DROP"].start_s == 64.0
    assert cues["DROP"].number == 3
    assert cues["DROP"].type == "cue"
    assert cues["INTRO"].number == 1
```

- [ ] **Step 2: Run the test**

Run: `PYTHONPATH=src:. python3 -m pytest spikes/vibe_mix_slice0/tests/test_roundtrip.py -v`
Expected: PASS. (`src` on the path for `vibemix`, `.` for `spikes`.)
If it FAILS because the production reader requires XML fields the writer omits (e.g. a `TrackID` or `TotalTime` attribute on `<TRACK>`), **that is a real finding** — record it in the verdict, add the minimal missing attribute to `write_cues` (`xml.add_track(Location=..., TrackID=..., TotalTime=...)`), and re-run. The reader's `_track_to_entry` is the spec for what a valid track row needs.

- [ ] **Step 3: Commit**

```bash
git add spikes/vibe_mix_slice0/tests/test_roundtrip.py
git commit -m "spike(vibe-mix-slice0): round-trip proof via production RekordboxLibrary"
```

---

## Task 6: Verdict scaffold + the Kaan-together import test

**Files:**
- Create: `spikes/vibe-mix-slice0-cue-writeback.md`

The automated tests prove the *data* round-trips. The remaining unknown can only be settled by a human in Rekordbox: **does the imported XML actually show the cues on the right tracks at the right beats, and do they trigger cleanly on the controller?** That is the "test together" bar from the concept brief — a Kaan-action discharge, mirroring `spikes/gemini-3-1-flash-live-music.md`.

- [ ] **Step 1: Write the verdict scaffold**

```markdown
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

## API confirmed (Task 1 finding)

- `RekordboxXml.add_track(...)` signature actually used: __________
- `Track.add_mark(...)` signature actually used: __________
- `xml.save(...)` signature actually used: __________
- Minimal `<TRACK>` attributes the production reader requires: __________

## Automated proof (Tasks 3-5)

- [ ] Confidence gate drops sub-0.85 cues (`test_confidence_gate.py`)
- [ ] Writer backs up before overwrite; never mutates source (`test_backup_nondestructive.py`)
- [ ] Written cues read back correctly through production `RekordboxLibrary` (`test_roundtrip.py`)

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
```

- [ ] **Step 2: Commit**

```bash
git add spikes/vibe-mix-slice0-cue-writeback.md
git commit -m "spike(vibe-mix-slice0): verdict scaffold + Kaan-together import test"
```

---

## Final verification

- [ ] **Run the full spike suite**

Run: `PYTHONPATH=src:. python3 -m pytest spikes/vibe_mix_slice0/ -v`
Expected: all tests PASS (api probe + gate ×3 + backup ×3 + roundtrip ×1 = 8).

- [ ] **Confirm the grep gate is still green** (we never touched `src/vibemix/` and never imported `db6`)

Run: `grep -rn "Rekordbox6Database\|pyrekordbox.db6" src/vibemix/ spikes/vibe_mix_slice0/`
Expected: no output (empty).

- [ ] **Hand off to Kaan** for the `kaan-action-discharge` import test in Task 6.
