#!/usr/bin/env python3
"""Phase 47 / MASCOT-03 — Manifest ↔ on-disk GLB parity gate.

Asserts:
  1. Every GLB in tauri/ui/assets/mascot/animations/ that matches a
     Phase 47 family prefix (base_/emotion_/prep_/react_) has a
     corresponding row in assets/mascot/source/MANIFEST.yaml.
  2. Every MANIFEST.yaml row with status='retargeted' has a GLB
     at the expected slot path.

Placeholder rows (status='placeholder') are tolerated — they exist
precisely to surface incomplete §VIS-04 discharge without breaking CI.

Exit codes:
  0 — manifest matches inventory
  1 — drift detected
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: pyyaml not installed; run `uv add pyyaml` in dev shell",
        file=sys.stderr,
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "assets" / "mascot" / "source" / "MANIFEST.yaml"
ANIM_DIR = REPO_ROOT / "tauri" / "ui" / "assets" / "mascot" / "animations"
FAMILY_PREFIXES = ("base_", "emotion_", "prep_", "react_")


def main() -> int:
    if not MANIFEST.is_file():
        print(f"ERROR: missing {MANIFEST}", file=sys.stderr)
        return 1
    if not ANIM_DIR.is_dir():
        print(f"ERROR: missing {ANIM_DIR}", file=sys.stderr)
        return 1

    data = yaml.safe_load(MANIFEST.read_text())
    rows = data.get("slots", [])
    rows_by_slot = {r["slot"]: r for r in rows}

    on_disk = {
        p.stem
        for p in ANIM_DIR.glob("*.glb")
        if any(p.name.startswith(prefix) for prefix in FAMILY_PREFIXES)
    }

    errors: list[str] = []

    for slot in sorted(on_disk):
        if slot not in rows_by_slot:
            errors.append(
                f"  ON-DISK NOT IN MANIFEST: {slot}.glb has no MANIFEST.yaml row"
            )

    for slot, row in rows_by_slot.items():
        if row.get("status") == "retargeted" and slot not in on_disk:
            errors.append(
                f"  RETARGETED ROW WITHOUT GLB: {slot} marked retargeted but {slot}.glb missing on disk"
            )

    if errors:
        print("Manifest <-> inventory drift detected:")
        for e in errors:
            print(e)
        return 1

    print(
        f"OK: {len(rows_by_slot)} manifest rows, {len(on_disk)} on-disk Phase-47-family GLBs, in sync"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
