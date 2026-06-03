# SPDX-License-Identifier: Apache-2.0
"""Validate the flat GitHub Release upload directory before publish."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.dist.check_updater_manifest_ready import (  # noqa: E402
    check_updater_manifest_ready,
)


@dataclass
class ReleaseUploadDirStatus:
    upload_dir: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _require_file(path: Path, status: ReleaseUploadDirStatus, label: str) -> None:
    if not path.is_file():
        status.fail(f"missing {label}: {path.name}")


def _glob_one(upload_dir: Path, pattern: str, status: ReleaseUploadDirStatus, label: str) -> None:
    hits = sorted(path for path in upload_dir.glob(pattern) if path.is_file())
    if len(hits) != 1:
        status.fail(f"expected exactly one {label} matching {pattern!r}, found {len(hits)}")


def _check_verify_report(path: Path, status: ReleaseUploadDirStatus) -> None:
    if not path.is_file():
        status.fail(f"missing verify report: {path.name}")
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        status.fail(f"{path.name}: verify report is not readable JSON: {exc}")
        return
    if payload.get("status") != "clean":
        status.fail(f"{path.name}: verify report status is not clean")
    hits = payload.get("hits")
    if hits not in ([], None):
        status.fail(f"{path.name}: verify report contains hits")


def check_release_upload_dir_ready(
    upload_dir: Path,
    *,
    tag: str | None = None,
) -> ReleaseUploadDirStatus:
    status = ReleaseUploadDirStatus(upload_dir=str(upload_dir))
    if not upload_dir.is_dir():
        status.fail(f"upload directory not found: {upload_dir}")
        return status

    files = sorted(path.name for path in upload_dir.iterdir() if path.is_file())
    status.files = files

    if tag:
        _require_file(upload_dir / f"vibemix-{tag}-arm64.dmg", status, "macOS arm64 DMG")
        _require_file(
            upload_dir / f"vibemix-{tag}-x86_64.dmg",
            status,
            "macOS x86_64 DMG",
        )
    else:
        _glob_one(upload_dir, "vibemix-*-arm64.dmg", status, "macOS arm64 DMG")
        _glob_one(upload_dir, "vibemix-*-x86_64.dmg", status, "macOS x86_64 DMG")

    _require_file(upload_dir / "vibemix-installer.exe", status, "Windows first installer")
    _require_file(upload_dir / "latest.json", status, "signed updater manifest")
    _require_file(
        upload_dir / "verify-report-macos-arm64.json",
        status,
        "macOS arm64 verify report",
    )
    _require_file(
        upload_dir / "verify-report-macos-x86_64.json",
        status,
        "macOS x86_64 verify report",
    )
    _require_file(upload_dir / "verify-report-windows.json", status, "Windows verify report")

    _glob_one(upload_dir, "*arm64.app.tar.gz", status, "macOS arm64 updater archive")
    _glob_one(upload_dir, "*x86_64.app.tar.gz", status, "macOS x86_64 updater archive")
    windows_updaters = [
        path
        for path in upload_dir.glob("*setup*.exe")
        if path.is_file() and path.name != "vibemix-installer.exe"
    ]
    if len(windows_updaters) != 1:
        status.fail(
            "expected exactly one Windows updater NSIS setup EXE, "
            f"found {len(windows_updaters)}"
        )

    forbidden = [
        name
        for name in files
        if name.endswith(".msi")
        or name.endswith(".pkg")
        or name.endswith(".app")
        or name == "vibemix-0.0.1.dmg"
    ]
    if forbidden:
        status.fail(f"forbidden upload asset(s): {', '.join(forbidden)}")

    manifest_status = check_updater_manifest_ready(upload_dir / "latest.json")
    if not manifest_status.ok:
        status.fail("latest.json failed updater manifest readiness")
        status.errors.extend(manifest_status.errors)

    for report_name in (
        "verify-report-macos-arm64.json",
        "verify-report-macos-x86_64.json",
        "verify-report-windows.json",
    ):
        _check_verify_report(upload_dir / report_name, status)

    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if release-artifacts/upload is incomplete or unsafe."
    )
    parser.add_argument("upload_dir", type=Path, help="flat upload directory")
    parser.add_argument("--tag", default=None, help="optional Git tag/ref name, e.g. v0.1.0")
    parser.add_argument("--json", action="store_true", help="print machine-readable status")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    status = check_release_upload_dir_ready(args.upload_dir, tag=args.tag)
    if args.json:
        print(json.dumps(asdict(status), sort_keys=True))
    elif status.ok:
        if not args.quiet:
            print(f"[release-upload] OK: {len(status.files)} file(s)")
    else:
        for error in status.errors:
            print(f"[release-upload] FAIL: {error}", file=sys.stderr)
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
