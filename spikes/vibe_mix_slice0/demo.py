# SPDX-License-Identifier: Apache-2.0
"""Demo runner — emit a real importable Rekordbox XML for the two PioneerDJ
demo tracks, so the cue write-back can be felt in Rekordbox + on a controller.

Cue POSITIONS here are hand-placed demo values (real DSP detection is Slice 3);
what this exercises is the WRITE-BACK + import path. Run:

    PYTHONPATH=src:. .venv/bin/python3 -m spikes.vibe_mix_slice0.demo
"""
from __future__ import annotations

from pathlib import Path

from spikes.vibe_mix_slice0.confidence_gate import gate_cues
from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice0.types import CueCandidate

DEMO_DIR = Path.home() / "Music" / "PioneerDJ" / "Demo Tracks"
OUT = Path.home() / "Desktop" / "vibemix-cues-demo.xml"


def _cues_for(track: Path, plan: list[tuple[str, float, int, float]]) -> list[CueCandidate]:
    loc = str(track)  # plain absolute path; the writer builds the Rekordbox URI
    return [
        CueCandidate(track_location=loc, name=n, type="cue", start_s=s,
                     number=num, confidence=conf)
        for (n, s, num, conf) in plan
    ]


def main() -> None:
    t1 = DEMO_DIR / "Demo Track 1.mp3"  # ~172s
    t2 = DEMO_DIR / "Demo Track 2.mp3"  # ~128s
    for t in (t1, t2):
        if not t.exists():
            raise SystemExit(f"missing demo track: {t}")

    # (label, start_s, hot-cue slot, confidence). One sub-0.85 entry on purpose
    # to show the anti-slop gate dropping it before anything is written.
    candidates = (
        _cues_for(t1, [
            ("INTRO", 0.0, 1, 0.99),
            ("CUE",   32.0, 2, 0.91),
            ("DROP",  64.0, 3, 0.95),
            ("BREAK", 128.0, 4, 0.55),   # low confidence -> gated out
        ])
        + _cues_for(t2, [
            ("INTRO", 0.0, 1, 0.99),
            ("BUILD", 32.0, 2, 0.88),
            ("DROP",  64.0, 3, 0.96),
        ])
    )

    kept = gate_cues(candidates)
    dropped = len(candidates) - len(kept)
    n = write_cues(kept, out_path=str(OUT))

    print(f"-> confidence gate: {len(candidates)} candidates, {dropped} dropped, {len(kept)} kept")
    print(f"-> wrote {n} cues to {OUT}")
    print()
    print("Import into Rekordbox:")
    print("  1. Rekordbox -> File -> Import Collection (or drag the XML into the tree)")
    print("  2. Import as a NEW playlist (do NOT merge into your main collection)")
    print("  3. Load Demo Track 1 / 2, check cues land + trigger on the DDJ-FLX4")
    print(f"  4. Fill the verdict: spikes/vibe-mix-slice0-cue-writeback.md")


if __name__ == "__main__":
    main()
