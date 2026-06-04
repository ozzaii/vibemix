# SPDX-License-Identifier: Apache-2.0
"""Mount and validate a macOS first-install DMG artifact."""

from __future__ import annotations

import argparse
import json
import plistlib
import shutil
import subprocess
import sys
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
class MacOSDmgArtifactStatus:
    artifact: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    mounted_app: str = ""
    installed_app: str = ""
    app_status: MacOSAppBundleStatus | None = None

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _attach_dmg(artifact: Path) -> tuple[list[str], list[Path]]:
    result = subprocess.run(
        ["hdiutil", "attach", str(artifact), "-readonly", "-nobrowse", "-plist"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())

    data = plistlib.loads(result.stdout)
    devices: list[str] = []
    mounts: list[Path] = []
    for entity in data.get("system-entities", []):
        if dev := entity.get("dev-entry"):
            devices.append(str(dev))
        if mount := entity.get("mount-point"):
            mounts.append(Path(str(mount)))
    if not mounts:
        raise RuntimeError("hdiutil attach did not report a mount-point")
    return devices, mounts


def _detach(devices: list[str], mounts: list[Path]) -> None:
    targets = devices or [str(mount) for mount in mounts]
    for target in reversed(targets):
        subprocess.run(["hdiutil", "detach", target, "-quiet"], check=False)


def _find_app(mounts: list[Path], app_name: str | None) -> Path:
    candidates: list[Path] = []
    for mount in mounts:
        if app_name:
            candidate = mount / app_name
            if candidate.is_dir():
                candidates.append(candidate)
        else:
            candidates.extend(sorted(mount.glob("*.app")))
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one .app in mounted DMG, found {[str(path) for path in candidates]}"
        )
    return candidates[0]


def check_macos_dmg_artifact_ready(
    artifact: Path,
    *,
    triple: str | None = None,
    install_dir: Path | None = None,
    app_name: str | None = "vibemix.app",
    require_chatterbox_ref: bool = False,
    require_chatterbox_source: bool = False,
    require_developer_id: bool = False,
    developer_team_id: str | None = None,
    smoke: str = "version",
    smoke_timeout_s: float = 20.0,
) -> MacOSDmgArtifactStatus:
    """Mount a DMG, copy out the app, and validate the copied install."""
    status = MacOSDmgArtifactStatus(artifact=str(artifact))
    if not artifact.is_file() or artifact.suffix.lower() != ".dmg":
        status.fail(f"first-install artifact must be a .dmg file: {artifact}")
        return status

    temp_ctx: tempfile.TemporaryDirectory[str] | None = None
    devices: list[str] = []
    mounts: list[Path] = []
    try:
        devices, mounts = _attach_dmg(artifact)
        mounted_app = _find_app(mounts, app_name)
        status.mounted_app = str(mounted_app)

        if install_dir is None:
            temp_ctx = tempfile.TemporaryDirectory(prefix="vibemix-dmg-install.")
            base_dir = Path(temp_ctx.name)
        else:
            base_dir = install_dir
            if base_dir.exists() and any(base_dir.iterdir()):
                raise RuntimeError(f"install directory is not empty: {base_dir}")
            base_dir.mkdir(parents=True, exist_ok=True)

        installed_app = base_dir / mounted_app.name
        shutil.copytree(mounted_app, installed_app, symlinks=True)
        status.installed_app = str(installed_app)
    except (OSError, RuntimeError, subprocess.SubprocessError, plistlib.InvalidFileException) as exc:
        status.fail(str(exc))
    finally:
        if mounts or devices:
            _detach(devices, mounts)

    if status.ok:
        app_status = check_macos_app_bundle_ready(
            Path(status.installed_app),
            triple=triple,
            require_chatterbox_ref=require_chatterbox_ref,
            require_chatterbox_source=require_chatterbox_source,
            require_developer_id=require_developer_id,
            developer_team_id=developer_team_id,
            smoke=smoke,
            smoke_timeout_s=smoke_timeout_s,
        )
        status.app_status = app_status
        if not app_status.ok:
            status.fail("installed app bundle failed readiness checks")
            status.errors.extend(app_status.errors)

    if temp_ctx is not None:
        temp_ctx.cleanup()
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if a macOS first-install DMG does not drag-install to a ready app."
    )
    parser.add_argument("artifact", type=Path, help="path to vibemix-<version>-<arch>.dmg")
    parser.add_argument("--triple", default=None, help="target triple; default detects host")
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=None,
        help="optional clean directory to leave the copied app in for inspection",
    )
    parser.add_argument("--app-name", default="vibemix.app")
    parser.add_argument(
        "--require-chatterbox-ref",
        action="store_true",
        help="release gate: require the bundled Chatterbox production reference WAV",
    )
    parser.add_argument(
        "--require-chatterbox-source",
        action="store_true",
        help="release gate: require the public Chatterbox HF repo/revision to resolve",
    )
    parser.add_argument(
        "--require-developer-id",
        action="store_true",
        help=(
            "release gate: require a strict Developer ID Application signature "
            "after drag-install"
        ),
    )
    parser.add_argument(
        "--developer-team-id",
        default=None,
        help="optional Apple team id expected in the Developer ID signature",
    )
    parser.add_argument(
        "--smoke",
        choices=("version", "library-stats", "none"),
        default="version",
        help="sidecar command to run after copying the app from the DMG",
    )
    parser.add_argument("--smoke-timeout-s", type=float, default=20.0)
    parser.add_argument("--json", action="store_true", help="print machine-readable status")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    status = check_macos_dmg_artifact_ready(
        args.artifact,
        triple=args.triple,
        install_dir=args.install_dir,
        app_name=args.app_name,
        require_chatterbox_ref=args.require_chatterbox_ref,
        require_chatterbox_source=args.require_chatterbox_source,
        require_developer_id=args.require_developer_id,
        developer_team_id=args.developer_team_id,
        smoke=args.smoke,
        smoke_timeout_s=args.smoke_timeout_s,
    )

    if args.json:
        print(json.dumps(asdict(status), sort_keys=True))
    elif status.ok:
        if not args.quiet:
            print(f"[macos-dmg-artifact] OK: {status.installed_app}")
    else:
        for error in status.errors:
            print(f"[macos-dmg-artifact] FAIL: {error}", file=sys.stderr)
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
