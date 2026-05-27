# SPDX-License-Identifier: Apache-2.0
"""Validate the bundled ``vibemix-core`` sidecar resource tree.

This is a local/package-readiness guard. Release CI builds the PyInstaller
sidecar before Tauri packaging, but direct ``cargo tauri build`` can otherwise
bundle the committed ``.placeholder`` directories and produce an app that opens
without a launchable Python sidecar.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BINARIES_REL = Path("tauri/src-tauri/binaries")
DEFAULT_MIN_BYTES = 4096


@dataclass(frozen=True)
class SidecarBundleStatus:
    ok: bool
    message: str
    binary: Path


def detect_host_triple() -> str:
    """Return the host Rust target triple from ``rustc -vV``."""
    try:
        out = subprocess.check_output(["rustc", "-vV"], text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "rustc not found; install Rust or pass --triple explicitly"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"rustc -vV failed: {exc}") from exc

    for line in out.splitlines():
        if line.startswith("host: "):
            triple = line.split("host: ", 1)[1].strip()
            if triple:
                return triple
            break
    raise RuntimeError(f"rustc -vV did not report a host triple:\n{out}")


def exe_suffix_for_triple(triple: str) -> str:
    return ".exe" if "windows" in triple else ""


def build_command_for_triple(triple: str) -> str:
    spec = "vibemix-core.windows.spec" if "windows" in triple else "vibemix-core.macos.spec"
    return f"uv run python scripts/build_sidecar.py --spec {spec}"


def expected_binary(root: Path, triple: str) -> Path:
    suffix = exe_suffix_for_triple(triple)
    return (
        root
        / BINARIES_REL
        / f"vibemix-core-{triple}"
        / f"vibemix-core-{triple}{suffix}"
    )


def check_sidecar_bundle_ready(
    *,
    root: Path = REPO_ROOT,
    triple: str | None = None,
    min_bytes: int = DEFAULT_MIN_BYTES,
) -> SidecarBundleStatus:
    """Check that the Tauri resource tree contains a real sidecar bundle."""
    target_triple = triple or detect_host_triple()
    binary = expected_binary(root, target_triple)
    bundle_dir = binary.parent
    build_cmd = build_command_for_triple(target_triple)

    if not bundle_dir.is_dir():
        return SidecarBundleStatus(
            False,
            f"sidecar bundle directory missing: {bundle_dir}. Run `{build_cmd}`.",
            binary,
        )

    placeholders = list(bundle_dir.glob(".placeholder*"))
    real_entries = [p for p in bundle_dir.iterdir() if not p.name.startswith(".placeholder")]
    if not real_entries and placeholders:
        return SidecarBundleStatus(
            False,
            f"sidecar bundle is placeholder-only at {bundle_dir}. Run `{build_cmd}`.",
            binary,
        )

    if not binary.is_file():
        return SidecarBundleStatus(
            False,
            f"bundled sidecar binary missing: {binary}. Run `{build_cmd}`.",
            binary,
        )

    size = binary.stat().st_size
    if size < min_bytes:
        return SidecarBundleStatus(
            False,
            f"bundled sidecar binary is too small ({size} bytes): {binary}. Run `{build_cmd}`.",
            binary,
        )

    if exe_suffix_for_triple(target_triple) == "" and not os.access(binary, os.X_OK):
        return SidecarBundleStatus(
            False,
            f"bundled sidecar binary is not executable: {binary}. Run `{build_cmd}`.",
            binary,
        )

    internal_dir = bundle_dir / "_internal"
    if not internal_dir.is_dir():
        return SidecarBundleStatus(
            False,
            f"PyInstaller _internal directory missing next to {binary}. Run `{build_cmd}`.",
            binary,
        )

    return SidecarBundleStatus(True, f"sidecar bundle ready: {binary}", binary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if the Tauri sidecar resource tree is missing or placeholder-only.",
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--triple", default=None, help="target triple; default detects host")
    parser.add_argument(
        "--min-bytes",
        type=int,
        default=DEFAULT_MIN_BYTES,
        help=f"minimum acceptable sidecar binary size (default: {DEFAULT_MIN_BYTES})",
    )
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    try:
        status = check_sidecar_bundle_ready(
            root=args.root.resolve(),
            triple=args.triple,
            min_bytes=args.min_bytes,
        )
    except RuntimeError as exc:
        print(f"[sidecar-bundle] FAIL: {exc}", file=sys.stderr)
        return 1

    if status.ok:
        if not args.quiet:
            print(f"[sidecar-bundle] OK: {status.message}")
        return 0

    print(f"[sidecar-bundle] FAIL: {status.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
