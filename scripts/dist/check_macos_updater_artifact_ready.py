# SPDX-License-Identifier: Apache-2.0
"""Extract and validate a macOS Tauri updater ``.app.tar.gz`` artifact."""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.dist.check_macos_app_bundle_ready import (  # noqa: E402
    MacOSAppBundleStatus,
    check_macos_app_bundle_ready,
)


@dataclass
class MacOSUpdaterArtifactStatus:
    artifact: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    app: str = ""
    app_status: MacOSAppBundleStatus | None = None

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _safe_members(archive: tarfile.TarFile) -> tuple[list[tarfile.TarInfo], str]:
    members = archive.getmembers()
    safe_members: list[tarfile.TarInfo] = []
    top_levels: set[str] = set()
    for member in members:
        path = Path(member.name)
        if member.name.startswith("/") or ".." in path.parts:
            raise RuntimeError(f"unsafe tar member path: {member.name}")
        if not path.parts:
            raise RuntimeError("empty tar member path")
        if path.parts[0] == "__MACOSX" or any(part.startswith("._") for part in path.parts):
            continue
        top_levels.add(path.parts[0])
        if member.issym() or member.islnk():
            link = Path(member.linkname)
            if member.linkname.startswith("/") or ".." in link.parts:
                raise RuntimeError(
                    f"unsafe tar link target for {member.name}: {member.linkname}"
                )
        safe_members.append(member)

    if len(top_levels) != 1:
        raise RuntimeError(f"expected one top-level app entry, found {sorted(top_levels)}")
    top = next(iter(top_levels))
    if not top.endswith(".app"):
        raise RuntimeError(f"top-level entry is not a .app bundle: {top}")
    return safe_members, top


def check_macos_updater_artifact_ready(
    artifact: Path,
    *,
    triple: str | None = None,
    install_dir: Path | None = None,
    require_moss_source: bool = False,
    smoke: str = "version",
    smoke_timeout_s: float = 20.0,
) -> MacOSUpdaterArtifactStatus:
    """Extract a macOS updater archive and validate the contained app bundle."""
    status = MacOSUpdaterArtifactStatus(artifact=str(artifact))
    if not artifact.is_file() or artifact.suffixes[-3:] != [".app", ".tar", ".gz"]:
        status.fail(f"updater artifact must be a .app.tar.gz file: {artifact}")
        return status

    temp_ctx: tempfile.TemporaryDirectory[str] | None = None
    try:
        if install_dir is None:
            temp_ctx = tempfile.TemporaryDirectory(prefix="vibemix-updater-check.")
            base_dir = Path(temp_ctx.name)
        else:
            base_dir = install_dir
            if base_dir.exists() and any(base_dir.iterdir()):
                raise RuntimeError(f"install directory is not empty: {base_dir}")
            base_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(artifact, "r:gz") as archive:
            members, top = _safe_members(archive)
            archive.extractall(base_dir, members=members, filter="data")

        app = base_dir / top
        status.app = str(app)
        app_status = check_macos_app_bundle_ready(
            app,
            triple=triple,
            require_moss_source=require_moss_source,
            smoke=smoke,
            smoke_timeout_s=smoke_timeout_s,
        )
        status.app_status = app_status
        if not app_status.ok:
            status.fail("extracted app bundle failed readiness checks")
            status.errors.extend(app_status.errors)
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        status.fail(str(exc))
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if a macOS updater .app.tar.gz cannot extract to a ready app."
    )
    parser.add_argument("artifact", type=Path, help="path to vibemix-<version>-<arch>.app.tar.gz")
    parser.add_argument("--triple", default=None, help="target triple; default detects host")
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=None,
        help="optional clean extraction directory to leave behind for inspection",
    )
    parser.add_argument(
        "--smoke",
        choices=("version", "library-stats", "none"),
        default="version",
        help="sidecar command to run after extracting the app",
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

    status = check_macos_updater_artifact_ready(
        args.artifact,
        triple=args.triple,
        install_dir=args.install_dir,
        require_moss_source=args.require_moss_source,
        smoke=args.smoke,
        smoke_timeout_s=args.smoke_timeout_s,
    )

    if args.json:
        print(json.dumps(asdict(status), sort_keys=True))
    elif status.ok:
        if not args.quiet:
            print(f"[macos-updater-artifact] OK: {status.app}")
    else:
        for error in status.errors:
            print(f"[macos-updater-artifact] FAIL: {error}", file=sys.stderr)
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
