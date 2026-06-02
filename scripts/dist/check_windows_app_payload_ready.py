# SPDX-License-Identifier: Apache-2.0
"""Validate the staged Windows app payload before signing or installer build."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.dist.check_sidecar_bundle_ready import (  # noqa: E402
    DEFAULT_MIN_BYTES,
    moss_release_source_ready,
)

DEFAULT_TRIPLE = "x86_64-pc-windows-msvc"


@dataclass
class WindowsAppPayloadStatus:
    payload: str
    triple: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    app_binary: str = ""
    sidecar_binary: str = ""
    moss_source: str = ""
    smoke_stdout: str = ""

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _is_probable_pe(path: Path, *, min_bytes: int) -> bool:
    if not path.is_file() or path.stat().st_size < min_bytes:
        return False
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"MZ"
    except OSError:
        return False


def _run_smoke(binary: Path, smoke: str, timeout_s: float, status: WindowsAppPayloadStatus) -> None:
    if smoke == "none":
        return
    if smoke == "version":
        cmd = [str(binary), "--version"]
    elif smoke == "library-stats":
        cmd = [str(binary), "library", "stats", "--json"]
    else:  # pragma: no cover - argparse prevents this.
        raise ValueError(f"unknown smoke mode: {smoke}")

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        status.fail(f"Windows sidecar smoke failed to launch: {exc}")
        return

    status.smoke_stdout = result.stdout.strip()
    if result.returncode != 0:
        status.fail(
            f"Windows sidecar smoke exited {result.returncode}: stderr={result.stderr.strip()!r}"
        )


def check_windows_app_payload_ready(
    payload: Path,
    *,
    triple: str = DEFAULT_TRIPLE,
    min_bytes: int = DEFAULT_MIN_BYTES,
    require_moss_source: bool = False,
    smoke: str = "none",
    smoke_timeout_s: float = 20.0,
) -> WindowsAppPayloadStatus:
    """Check that ``dist/windows-app`` contains the app exe and sidecar tree."""
    status = WindowsAppPayloadStatus(payload=str(payload), triple=triple)

    if "windows" not in triple:
        status.fail(f"expected a Windows target triple, got {triple!r}")
        return status

    if not payload.is_dir():
        status.fail(f"Windows app payload directory missing: {payload}")
        return status

    app_binary = payload / "vibemix.exe"
    status.app_binary = str(app_binary)
    if not _is_probable_pe(app_binary, min_bytes=min_bytes):
        status.fail(f"app binary missing, tiny, or not a PE executable: {app_binary}")

    sidecar_dir = payload / "binaries" / f"vibemix-core-{triple}"
    sidecar_binary = sidecar_dir / f"vibemix-core-{triple}.exe"
    status.sidecar_binary = str(sidecar_binary)

    if not sidecar_dir.is_dir():
        status.fail(f"Windows sidecar directory missing: {sidecar_dir}")
        return status

    placeholders = list(sidecar_dir.glob(".placeholder*"))
    real_entries = [
        path for path in sidecar_dir.iterdir() if not path.name.startswith(".placeholder")
    ]
    if not real_entries and placeholders:
        status.fail(f"Windows sidecar directory is placeholder-only: {sidecar_dir}")
        return status

    if not _is_probable_pe(sidecar_binary, min_bytes=min_bytes):
        status.fail(
            f"Windows sidecar binary missing, tiny, or not a PE executable: {sidecar_binary}"
        )
        return status

    internal = sidecar_dir / "_internal"
    if not internal.is_dir():
        status.fail(f"Windows sidecar _internal directory missing: {internal}")
        return status

    if require_moss_source:
        moss_ok, moss_message = moss_release_source_ready(sidecar_dir)
        status.moss_source = moss_message
        if not moss_ok:
            status.fail(moss_message)

    if status.ok:
        _run_smoke(sidecar_binary, smoke, smoke_timeout_s, status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if a staged Windows app payload is missing its runnable sidecar."
    )
    parser.add_argument("payload", type=Path, help="path to dist/windows-app")
    parser.add_argument("--triple", default=DEFAULT_TRIPLE)
    parser.add_argument(
        "--min-bytes",
        type=int,
        default=DEFAULT_MIN_BYTES,
        help=f"minimum acceptable executable size (default: {DEFAULT_MIN_BYTES})",
    )
    parser.add_argument(
        "--smoke",
        choices=("version", "library-stats", "none"),
        default="none",
        help="sidecar command to run after structural checks",
    )
    parser.add_argument(
        "--require-moss-source",
        action="store_true",
        help=(
            "release gate: require either a complete bundled MOSS model tree or "
            "verified VIBEMIX_MOSS_TTS_ARCHIVE_* pins"
        ),
    )
    parser.add_argument("--smoke-timeout-s", type=float, default=20.0)
    parser.add_argument("--json", action="store_true", help="print machine-readable status")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    status = check_windows_app_payload_ready(
        args.payload,
        triple=args.triple,
        min_bytes=args.min_bytes,
        require_moss_source=args.require_moss_source,
        smoke=args.smoke,
        smoke_timeout_s=args.smoke_timeout_s,
    )

    if args.json:
        print(json.dumps(asdict(status), sort_keys=True))
    elif status.ok:
        if not args.quiet:
            print(f"[windows-app-payload] OK: {status.sidecar_binary}")
    else:
        for error in status.errors:
            print(f"[windows-app-payload] FAIL: {error}", file=sys.stderr)
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
