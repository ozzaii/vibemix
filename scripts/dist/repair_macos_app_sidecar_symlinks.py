#!/usr/bin/env python3
"""Restore PyInstaller sidecar dylib symlinks flattened by Tauri bundling."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

DYLIB_DIRS = ("av/.dylibs", "PIL/.dylibs")


@dataclass
class RepairSummary:
    app: str
    scanned_internal_dirs: int = 0
    already_linked: int = 0
    relinked: int = 0
    missing_top_level: int = 0
    mismatches: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.mismatches


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_contents(left: Path, right: Path) -> bool:
    left_stat = left.stat()
    right_stat = right.stat()
    return left_stat.st_size == right_stat.st_size and _sha256(left) == _sha256(right)


def _internal_dirs(app: Path) -> list[Path]:
    binaries = app / "Contents" / "Resources" / "binaries"
    if not binaries.is_dir():
        return []
    return sorted(
        path
        for path in binaries.glob("vibemix-core-*/_internal")
        if path.is_dir() and "apple-darwin" in str(path.parent)
    )


def _repair_link(internal: Path, dylib_dir: str, target: Path, summary: RepairSummary) -> None:
    top_level = internal / target.name
    desired = f"{dylib_dir}/{target.name}"

    if not top_level.exists() and not top_level.is_symlink():
        summary.missing_top_level += 1
        return

    if top_level.is_symlink():
        current = os.readlink(top_level)
        if current == desired:
            summary.already_linked += 1
            return
        if (top_level.parent / current).resolve(strict=False) == target.resolve(strict=False):
            top_level.unlink()
            os.symlink(desired, top_level)
            summary.relinked += 1
            return
        summary.mismatches.append(f"{top_level}: points to {current!r}, expected {desired!r}")
        return

    if not top_level.is_file():
        summary.mismatches.append(f"{top_level}: expected file or symlink")
        return

    if not _same_contents(top_level, target):
        summary.mismatches.append(f"{top_level}: content differs from {target}")
        return

    top_level.unlink()
    os.symlink(desired, top_level)
    summary.relinked += 1


def repair_bundle(app: Path) -> RepairSummary:
    """Repair flattened sidecar links inside a macOS ``.app`` bundle."""
    app = app.resolve()
    summary = RepairSummary(app=str(app))

    for internal in _internal_dirs(app):
        summary.scanned_internal_dirs += 1
        for dylib_dir in DYLIB_DIRS:
            target_dir = internal / dylib_dir
            if not target_dir.is_dir():
                continue
            for target in sorted(path for path in target_dir.iterdir() if path.is_file()):
                _repair_link(internal, dylib_dir, target, summary)

    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore PyInstaller sidecar dylib symlinks in a Tauri macOS .app."
    )
    parser.add_argument("app", type=Path, help="Path to vibemix.app")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.app.is_dir():
        parser.error(f"app bundle not found: {args.app}")

    summary = repair_bundle(args.app)
    if args.json:
        print(json.dumps(asdict(summary), sort_keys=True))
    else:
        print(
            "[repair_macos_app_sidecar_symlinks] "
            f"scanned={summary.scanned_internal_dirs} "
            f"relinked={summary.relinked} "
            f"already_linked={summary.already_linked} "
            f"missing_top_level={summary.missing_top_level}"
        )
        for mismatch in summary.mismatches:
            print(f"[repair_macos_app_sidecar_symlinks] mismatch: {mismatch}", file=sys.stderr)

    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
