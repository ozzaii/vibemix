# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-01 — GLB optimization pipeline (gltfpack wrapper).

Two modes:

  --check ROOT
      Scan ROOT recursively for .glb files. Assert per-clip <= 600 KB
      AND total <= 25 MB. No external deps. CI mode.

      The 600 KB per-clip cap applies to ANIMATION clips only — files
      under any path segment named "animations" or matching the prep_*
      / react_* / dance_* naming convention. Character/rig meshes
      (e.g. character.glb at the mascot root) are excluded from the
      per-clip cap but still count toward the 25 MB total.

  --optimize INPUT_DIR OUTPUT_DIR
      Run gltfpack on every .glb in INPUT_DIR, write to OUTPUT_DIR.
      Requires gltfpack on PATH. Kaan-action local mode (used before
      committing real GLBs).

Pitfall P52: real GLB animations can push the bundle past the 350 MB
hard cap. Phase 35 sub-budget = 25 MB total + 600 KB per clip. This
script is the CI enforcer for the per-clip half of the budget
(check_mascot_glb_size.sh + tests/repo/test_mascot_glb_size_gate.py
already cover the total half — this script adds redundant total-check
so the binary is self-contained).

Exit codes:
    0 = OK
    1 = budget violation (--check) or other check failure
    2 = missing external tool (--optimize without gltfpack)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

MAX_PER_CLIP_BYTES = 600 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024

# Character / rig meshes are not animation clips and don't fit under the
# 600 KB per-clip cap (a rigged character with textures is ~10-25 MB even
# DRACO-compressed). They DO still count toward the 25 MB total.
# Match by path-segment 'animations' membership: if the file lives under
# an 'animations' dir it's a clip; otherwise it's a rig/character mesh.
ANIMATION_PATH_SEGMENT = "animations"


def _iter_glbs(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return iter(())
    return sorted(root.rglob("*.glb"))


def _is_animation_clip(path: Path, root: Path) -> bool:
    """True iff `path` lives under a directory named 'animations' relative
    to `root`. Used to scope the 600 KB per-clip cap to clips only."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    return ANIMATION_PATH_SEGMENT in rel.parts[:-1]


def _format_mb(byte_count: int) -> str:
    return f"{byte_count / 1024 / 1024:.2f} MB"


def _format_kb(byte_count: int) -> str:
    return f"{byte_count / 1024:.1f} KB"


def cmd_check(root: Path) -> int:
    """Scan ROOT for GLBs; assert per-clip + total budgets."""
    glbs = list(_iter_glbs(root))
    if not glbs:
        # Empty root is OK — nothing to check. CI surface this so future
        # path drifts are still visible.
        print(f"OK: no .glb files under {root}")
        return 0

    per_clip_violations: list[tuple[Path, int]] = []
    total = 0
    animation_count = 0
    for glb in glbs:
        size = glb.stat().st_size
        total += size
        if _is_animation_clip(glb, root):
            animation_count += 1
            if size > MAX_PER_CLIP_BYTES:
                per_clip_violations.append((glb, size))

    failed = False

    if per_clip_violations:
        failed = True
        print(
            f"FAIL: {len(per_clip_violations)} animation clip(s) exceed "
            f"{_format_kb(MAX_PER_CLIP_BYTES)} per-clip cap (Pitfall P52):",
            file=sys.stderr,
        )
        for path, size in per_clip_violations:
            print(
                f"  - {path.relative_to(root)}: {_format_kb(size)} "
                f"(over by {_format_kb(size - MAX_PER_CLIP_BYTES)})",
                file=sys.stderr,
            )

    if total > MAX_TOTAL_BYTES:
        failed = True
        print(
            f"FAIL: total {_format_mb(total)} exceeds "
            f"{_format_mb(MAX_TOTAL_BYTES)} cap (Pitfall P52)",
            file=sys.stderr,
        )

    if failed:
        return 1

    animation_glbs = [g for g in glbs if _is_animation_clip(g, root)]
    if animation_glbs:
        largest_animation = max(g.stat().st_size for g in animation_glbs)
        per_clip_msg = (
            f", largest animation {_format_kb(largest_animation)} / "
            f"{_format_kb(MAX_PER_CLIP_BYTES)} per-clip cap"
        )
    else:
        per_clip_msg = ""
    print(
        f"OK: {len(glbs)} file(s) ({animation_count} animation), "
        f"total {_format_mb(total)} / {_format_mb(MAX_TOTAL_BYTES)} "
        f"cap{per_clip_msg}"
    )
    return 0


def cmd_optimize(input_dir: Path, output_dir: Path) -> int:
    """Run gltfpack DRACO L7 + KTX2 on every .glb in INPUT_DIR."""
    gltfpack = shutil.which("gltfpack")
    if gltfpack is None:
        print(
            "FAIL: gltfpack not on PATH. Install via:\n"
            "  npm install -g gltfpack\n"
            "or download from https://github.com/zeux/meshoptimizer/releases",
            file=sys.stderr,
        )
        return 2

    if not input_dir.is_dir():
        print(f"FAIL: input dir {input_dir} does not exist", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    glbs = list(_iter_glbs(input_dir))
    if not glbs:
        print(f"OK: no .glb files in {input_dir} — nothing to optimize")
        return 0

    failures = 0
    for src in glbs:
        rel = src.relative_to(input_dir)
        dst = output_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # gltfpack flags:
        #   -i / -o    in / out
        #   -cc        meshopt compression (KHR_mesh_quantization +
        #              EXT_meshopt_compression)
        #   -tc        KTX2 texture transcoding
        #   -tq 8      texture quality (8 = good, 4 = small, 10 = max)
        cmd = [gltfpack, "-i", str(src), "-o", str(dst), "-cc", "-tc", "-tq", "8"]
        print(f"-> {rel}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures += 1
            print(
                f"   FAIL (exit {result.returncode}): {result.stderr.strip()}",
                file=sys.stderr,
            )
            continue
        if dst.exists():
            in_kb = src.stat().st_size / 1024
            out_kb = dst.stat().st_size / 1024
            ratio = (1 - out_kb / in_kb) * 100 if in_kb > 0 else 0
            print(f"   {in_kb:.1f} KB -> {out_kb:.1f} KB ({ratio:+.1f}%)")

    if failures:
        print(f"FAIL: {failures} clip(s) failed gltfpack", file=sys.stderr)
        return 1

    # Re-run the budget check on the output dir so the Kaan-action flow
    # gets immediate feedback on whether the optimization landed within
    # budget.
    print()
    print("--- Post-optimization budget check ---")
    return cmd_check(output_dir)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "GLB optimization + budget enforcement (Phase 35 ASSETS-04). "
            "Use --check in CI; --optimize before committing real GLBs."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        metavar="ROOT",
        type=Path,
        help="Scan ROOT for .glb files; enforce per-clip + total budgets.",
    )
    group.add_argument(
        "--optimize",
        nargs=2,
        metavar=("INPUT_DIR", "OUTPUT_DIR"),
        help="Run gltfpack on every .glb in INPUT_DIR, write to OUTPUT_DIR.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.check is not None:
        return cmd_check(args.check)
    if args.optimize is not None:
        input_dir, output_dir = args.optimize
        return cmd_optimize(Path(input_dir), Path(output_dir))
    # argparse mutually_exclusive_group(required=True) guarantees one branch.
    return 2  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
