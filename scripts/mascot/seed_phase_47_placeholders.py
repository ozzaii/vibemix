#!/usr/bin/env python3
"""Phase 47 / MASCOT-01 — Seed 23 placeholder GLBs at the new slot paths.

Aliases existing prep_settle.glb content into 23 Phase 47 family slots
(3 base_ / 5 emotion_ / 5 prep_kick-family / 10 react_) so the
asset-loader doesn't 404 in dev before Kaan §VIS-04 discharge.

Idempotent: running twice produces zero diff. Skips any slot that
already has a non-placeholder-sized GLB (>= floor of its family band)
— that's a sign Kaan already discharged that slot via the retarget CLI.

Real retargets via `retarget_to_neon_rebel.py --slot <slot> --really`
overwrite the placeholder with the actual Mixamo clip data.

Run from repo root: uv run python scripts/mascot/seed_phase_47_placeholders.py
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANIM_DIR = REPO_ROOT / "tauri" / "ui" / "assets" / "mascot" / "animations"
SOURCE = ANIM_DIR / "prep_settle.glb"

PHASE_47_SLOTS: dict[str, tuple[int, int]] = {
    # slot: (min_kb floor, max_kb ceiling)
    # Base family (200-600 KB)
    "base_idle": (200, 600),
    "base_breathe": (200, 600),
    "base_sway": (200, 600),
    # Emotion family (300-900 KB)
    "emotion_joy": (300, 900),
    "emotion_trust": (300, 900),
    "emotion_surprise": (300, 900),
    "emotion_anticipation": (300, 900),
    "emotion_focus": (300, 900),
    # Anticipation family — NEW prep_kick et al (400-1200 KB, distinct from legacy_prep)
    "prep_kick": (400, 1200),
    "prep_breakdown": (400, 1200),
    "prep_drop": (400, 1200),
    "prep_layer": (400, 1200),
    "prep_mix": (400, 1200),
    # Reaction family (400-1200 KB)
    "react_kick_swap": (400, 1200),
    "react_sub_layer": (400, 1200),
    "react_breakdown": (400, 1200),
    "react_reentry": (400, 1200),
    "react_phrase_boundary": (400, 1200),
    "react_distortion_climb": (400, 1200),
    "react_acid_line": (400, 1200),
    "react_mix_in": (400, 1200),
    "react_mix_out": (400, 1200),
    "react_hype_peak": (400, 1200),
}


def main() -> int:
    if not SOURCE.is_file():
        print(f"ERROR: missing seed source {SOURCE}", file=sys.stderr)
        return 1

    source_bytes = SOURCE.stat().st_size
    if source_bytes < 1024:
        print(
            f"ERROR: seed source {SOURCE} suspiciously small ({source_bytes} bytes)",
            file=sys.stderr,
        )
        return 1

    seeded = 0
    skipped_discharged = 0
    unchanged = 0

    for slot, (min_kb, _max_kb) in sorted(PHASE_47_SLOTS.items()):
        dest = ANIM_DIR / f"{slot}.glb"
        min_bytes = min_kb * 1024

        if dest.is_file() and dest.stat().st_size >= min_bytes:
            # Already discharged — preserve real retarget
            skipped_discharged += 1
            print(
                f"  SKIP  {slot}.glb ({dest.stat().st_size} bytes; >= {min_bytes} floor — real asset)"
            )
            continue

        if dest.is_file() and dest.stat().st_size == source_bytes:
            # Already seeded with the same source — idempotent no-op
            unchanged += 1
            continue

        shutil.copyfile(SOURCE, dest)
        seeded += 1
        print(
            f"  SEED  {slot}.glb ({source_bytes} bytes, aliased to prep_settle.glb)"
        )

    print(
        f"\nDone: {seeded} seeded, {unchanged} unchanged, {skipped_discharged} skipped (already discharged)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
