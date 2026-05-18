"""Mixamo → Neon Rebel retarget pipeline (Phase 43, Plan 43-05 / VIS-04).

Inputs: a Mixamo-downloaded source GLB (single clip, default rig).
Output: a draco-compressed single-clip GLB retargeted onto the Neon
Rebel rig at ``tauri/ui/assets/mascot/character.glb``, sized in the
400KB-1.2MB band (CONTEXT §VIS-04).

This script is **engineering scaffolding**. The actual Mixamo account
login + 5 clip downloads + per-clip retarget run is Kaan-discharge per
``KAAN-ACTION-LEGAL.md §VIS-04``. Engineering CI uses this scaffold to
validate:

  * CLI surface (slot mapping, rig path, output dir)
  * dry-run plan inventory (5 slots)
  * per-clip size-band predicate (400KB-1.2MB)
  * file-existence guard on the source argument

…without committing any real Mixamo bytes. The real ``retarget()``
implementation (pygltflib skeleton remap or blender headless shell-out)
is filled in at §VIS-04 discharge time — see the runbook in
``KAAN-ACTION-LEGAL.md`` for both implementation paths.

Pipeline (real run):
  1. Load source GLB (pygltflib).
  2. Remap skeleton joints onto Neon Rebel rig.
  3. Export as single-clip GLB.
  4. Draco-compress via ``npx gltf-pipeline -i <in> -o <out> -d``.
  5. Assert output size lands in 400KB-1.2MB band.

Slot mapping (CONTEXT §VIS-04):
  Idle        → prep_settle.glb
  Talk_short  → prep_head_turn_left.glb
  Talk_long   → prep_head_turn_right.glb
  Celebrate   → prep_lean_in_hyped.glb
  Headbob     → prep_lean_in_neutral.glb
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Repo-root resolution: this file lives at <repo>/scripts/mascot/retarget_to_neon_rebel.py
# so parents[2] is the repo root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEON_REBEL_RIG_PATH = (
    _PROJECT_ROOT / "tauri" / "ui" / "assets" / "mascot" / "character.glb"
)
_OUTPUT_DIR_DEFAULT = (
    _PROJECT_ROOT / "tauri" / "ui" / "assets" / "mascot" / "animations"
)

# Per-clip size band per CONTEXT §VIS-04: 400KB-1.2MB after draco compression.
_MIN_BYTES = 400 * 1024
_MAX_BYTES = 1200 * 1024


@dataclass(frozen=True)
class SlotMapping:
    """One Mixamo source label → vibemix slot output mapping.

    ``mixamo_label`` matches CONTEXT §VIS-04 verbatim (Idle / Talk_short /
    Talk_long / Celebrate / Headbob). ``output_slot`` is the filename stem
    used inside ``tauri/ui/assets/mascot/animations/``.
    """

    mixamo_label: str
    output_slot: str
    purpose: str


SLOT_MAPPINGS: tuple[SlotMapping, ...] = (
    SlotMapping("Idle", "prep_settle", "baseline idle pose"),
    SlotMapping("Talk_short", "prep_head_turn_left", "short talk loop"),
    SlotMapping("Talk_long", "prep_head_turn_right", "long talk loop"),
    SlotMapping("Celebrate", "prep_lean_in_hyped", "Hype-man celebrate (Pioneer CDJ headbob feel)"),
    SlotMapping("Headbob", "prep_lean_in_neutral", "Pioneer-CDJ headbob baseline"),
)

# Phase 47 / MASCOT-02 — Slot family taxonomy (28 total = 5 legacy_prep + 23 new
# family slots). Per memory `project_mascot_as_vtuber_personality_surface`: single
# VTuber Neon Rebel rig; `/hatch` user-gen is v2.x stretch. Per-family size bands
# carry forward into scripts/mascot/check_bundle_size.sh Tier 2 prefix routing.
SLOT_FAMILIES: dict[str, dict] = {
    "legacy_prep": {
        "slots": [
            "prep_settle",
            "prep_head_turn_left",
            "prep_head_turn_right",
            "prep_lean_in_hyped",
            "prep_lean_in_neutral",
        ],
        "size_band_kb": (400, 1200),
    },
    "base": {
        "slots": ["base_idle", "base_breathe", "base_sway"],
        "size_band_kb": (200, 600),
    },
    "emotion": {
        "slots": [
            "emotion_joy",
            "emotion_trust",
            "emotion_surprise",
            "emotion_anticipation",
            "emotion_focus",
        ],
        "size_band_kb": (300, 900),
    },
    "anticipation": {
        # NEW Phase 47 prep_* event-class slots — distinct from legacy_prep.
        "slots": ["prep_kick", "prep_breakdown", "prep_drop", "prep_layer", "prep_mix"],
        "size_band_kb": (400, 1200),
    },
    "reaction": {
        "slots": [
            "react_kick_swap",
            "react_sub_layer",
            "react_breakdown",
            "react_reentry",
            "react_phrase_boundary",
            "react_distortion_climb",
            "react_acid_line",
            "react_mix_in",
            "react_mix_out",
            "react_hype_peak",
        ],
        "size_band_kb": (400, 1200),
    },
}

# Slot → family reverse map (28 entries total).
VALID_SLOTS: dict[str, str] = {
    s: family for family, info in SLOT_FAMILIES.items() for s in info["slots"]
}


def verify_size_band(file_size_bytes: int) -> bool:
    """Return True iff ``file_size_bytes`` lies in the legacy 400KB-1.2MB band.

    Per CONTEXT §VIS-04 a draco-compressed retarget output must land in
    this band. Below 400KB suggests the clip is degenerate (no
    animation data or over-compressed); above 1.2MB suggests draco
    compression is undertuned and bundle size will overshoot the 25MB
    total cap once all 5 slots populate.
    """
    return _MIN_BYTES <= file_size_bytes <= _MAX_BYTES


def verify_size_band_for_slot(slot: str, file_size_bytes: int) -> bool:
    """Phase 47 / MASCOT-02 per-family size band check.

    Looks up the slot's family and asserts ``file_size_bytes`` is in that
    family's band. Falls back to the legacy 400-1200 KB band if the slot
    is not declared in SLOT_FAMILIES (which is itself an error condition —
    every shipped slot should appear in SLOT_FAMILIES).
    """
    family = VALID_SLOTS.get(slot)
    if family is None:
        return verify_size_band(file_size_bytes)
    min_kb, max_kb = SLOT_FAMILIES[family]["size_band_kb"]
    return (min_kb * 1024) <= file_size_bytes <= (max_kb * 1024)


def compress_draco(input_glb: Path, output_glb: Path) -> None:
    """Run gltf-pipeline draco compression.

    Shell-out to ``npx --yes gltf-pipeline``. Raises CalledProcessError
    on non-zero exit. Requires npm + gltf-pipeline on PATH.
    """
    cmd = [
        "npx",
        "--yes",
        "gltf-pipeline",
        "-i",
        str(input_glb),
        "-o",
        str(output_glb),
        "-d",
    ]
    subprocess.run(cmd, check=True)


def retarget(source: Path, rig: Path, slot: str, output_dir: Path) -> Path:
    """Skeleton-remap ``source`` onto ``rig``; emit ``<output_dir>/<slot>.glb``.

    Scaffold-only mode in Plan 43-05: this function validates input
    paths exist and reserves the output slot, then raises
    ``NotImplementedError`` to surface that the real skeleton-remap
    implementation lives in the §VIS-04 Kaan-discharge runbook
    (KAAN-ACTION-LEGAL.md). Two implementation paths are documented
    there:

    * **pygltflib path** — Python-native skeleton remap; preferred for
      simple skinned-mesh inputs.
    * **blender headless path** — ``blender --background --python``
      invocation; fallback when pygltflib can't handle blend-weight
      transfer cleanly.

    Both paths produce a single-clip GLB at ``<output_dir>/<slot>.glb``
    which then runs through ``compress_draco()`` and ``verify_size_band()``.
    """
    if not source.exists():
        raise FileNotFoundError(f"source GLB missing: {source}")
    if not rig.exists():
        raise FileNotFoundError(f"rig GLB missing: {rig}")
    output_dir.mkdir(parents=True, exist_ok=True)
    raise NotImplementedError(
        "Skeleton remap implementation is filled in at §VIS-04 Kaan-discharge. "
        "Scaffold-only mode: use --dry-run to inspect the planned retargets. "
        "See KAAN-ACTION-LEGAL.md §VIS-04 for the pygltflib / blender paths."
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code.

    ``--dry-run`` (default) prints the 5 planned retargets and exits 0.
    ``--really`` requires ``--source`` and ``--slot``; engages the (not
    yet implemented) retarget + draco + size-band pipeline.
    """
    parser = argparse.ArgumentParser(
        prog="retarget_to_neon_rebel",
        description=(
            "Mixamo → Neon Rebel retarget pipeline (Plan 43-05 / VIS-04). "
            "Engineering scaffold — real retargets run during §VIS-04 "
            "Kaan-discharge per KAAN-ACTION-LEGAL.md."
        ),
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Mixamo source GLB (single clip, Mixamo default rig)",
    )
    parser.add_argument(
        "--slot",
        choices=sorted(VALID_SLOTS.keys()),
        help="Target slot file in the mascot animations dir (28 slots across 5 families)",
    )
    parser.add_argument(
        "--slot-family",
        choices=sorted(SLOT_FAMILIES.keys()),
        help=(
            "Phase 47 — batch mode: run retarget against every slot in the family "
            "(assumes ~/Downloads/mixamo_<slot>.glb naming convention per slot)."
        ),
    )
    parser.add_argument(
        "--rig",
        type=Path,
        default=NEON_REBEL_RIG_PATH,
        help="Skeleton-target rig (default: Neon Rebel — tauri/ui/assets/mascot/character.glb)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_OUTPUT_DIR_DEFAULT,
        help="Output directory (default: tauri/ui/assets/mascot/animations)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print planned retargets without invoking any tools (default)",
    )
    parser.add_argument(
        "--really",
        dest="dry_run",
        action="store_false",
        help="Engage the real retarget + draco pipeline (requires --source + --slot)",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        print("VIS-04 retarget plan (Plan 43-05):")
        for m in SLOT_MAPPINGS:
            print(
                f"  {m.mixamo_label:<12} -> {m.output_slot}.glb  ({m.purpose})"
            )
        print(f"  Rig: {args.rig}")
        print(f"  Output dir: {args.output_dir}")
        print(
            f"  Per-clip size band: {_MIN_BYTES}..{_MAX_BYTES} bytes "
            f"(400KB-1200KB / 0.4MB-1.2MB after draco compression)"
        )
        print(
            "  NOTE: scaffold-only — real retargets run at §VIS-04 "
            "Kaan-discharge (KAAN-ACTION-LEGAL.md)."
        )
        return 0

    if args.source is None or args.slot is None:
        print(
            "ERROR: --really requires both --source and --slot",
            file=sys.stderr,
        )
        return 2

    try:
        out = retarget(args.source, args.rig, args.slot, args.output_dir)
        compress_draco(out, out)
        size = out.stat().st_size
        if not verify_size_band(size):
            print(
                f"ERROR: output {out} size {size} bytes outside the "
                f"{_MIN_BYTES}..{_MAX_BYTES} band; tune the gltf-pipeline "
                f"draco flag (--draco.compressionLevel 1..10, default 7) "
                f"and re-run.",
                file=sys.stderr,
            )
            return 1
        print(f"OK: retargeted {args.source.name} -> {out} ({size} bytes)")
        return 0
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except NotImplementedError as e:
        # Exit 3 = scaffold-only mode; §VIS-04 discharge fills the implementation.
        print(f"NOT-YET-IMPLEMENTED: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
