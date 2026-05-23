#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Discover attached MIDI input port names — Step 1 of add-a-controller.md.

Usage:
    python3 scripts/discover_midi_port.py

Prints one port name per line (sorted). Exits 0 with the list, 1 if no ports,
2 if mido is not installed. Cross-platform: macOS (CoreMIDI) + Windows (WinMM).

No imports from src/vibemix/ — runs with just `pip install mido python-rtmidi`.
Coexists with scripts/sniff_controller.py (the heavier JSONL session capture);
this script is the lightweight "what is my port called?" first step.
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import mido  # noqa: F401  (imported to confirm install before use)
    except ImportError:
        print("mido is not installed. Run: pip install mido python-rtmidi", file=sys.stderr)
        return 2
    names = sorted(mido.get_input_names())
    if not names:
        print("No MIDI input ports detected. Connect your controller via USB and re-run.", file=sys.stderr)
        return 1
    print("Attached MIDI input ports:")
    for n in names:
        print(f"  - {n}")
    print("\nCopy the substring that uniquely identifies your controller into the")
    print("'port_name_hints' field of your new profile JSON (see docs/contributing/_template.json).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
