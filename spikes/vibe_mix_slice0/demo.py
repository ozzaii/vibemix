# SPDX-License-Identifier: Apache-2.0
"""Demo runner — emit a real importable Rekordbox XML for the PioneerDJ demo
tracks with AUTO-DETECTED cues (Slice 3), gated by confidence (anti-slop),
written via the safe XML round-trip (Slice 0).

    PYTHONPATH=src:. .venv/bin/python3 -m spikes.vibe_mix_slice0.demo
"""
from __future__ import annotations

from pathlib import Path

from spikes.vibe_mix_slice0.confidence_gate import gate_cues
from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice3.detect import detect_cues

DEMO_DIR = Path.home() / "Music" / "PioneerDJ" / "Demo Tracks"
OUT = Path.home() / "Desktop" / "vibemix-cues-demo.xml"


def main() -> None:
    tracks = [DEMO_DIR / "Demo Track 1.mp3", DEMO_DIR / "Demo Track 2.mp3"]
    for t in tracks:
        if not t.exists():
            raise SystemExit(f"missing demo track: {t}")

    all_detected = []
    for t in tracks:
        detected = detect_cues(str(t), track_location=str(t))
        kept = gate_cues(detected)
        all_detected.extend(kept)
        print(f"-> {t.name}")
        for c in sorted(detected, key=lambda c: c.start_s):
            mark = "KEEP" if c in kept else "drop"
            print(f"     [{mark}] {c.name:9s} @ {c.start_s:6.1f}s  conf {c.confidence:.2f}")

    n = write_cues(all_detected, out_path=str(OUT))
    print(f"\n-> wrote {n} confidence-gated cues to {OUT}")
    print("Import into Rekordbox (rekordbox xml node) -> check cues land + trigger.")
    print("Verdict: spikes/vibe-mix-slice0-cue-writeback.md")


if __name__ == "__main__":
    main()
