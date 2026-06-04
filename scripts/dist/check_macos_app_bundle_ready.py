# SPDX-License-Identifier: Apache-2.0
"""Validate a macOS Tauri ``.app`` bundle before signing or upload."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.dist.check_sidecar_bundle_ready import (  # noqa: E402
    DEFAULT_MIN_BYTES,
    chatterbox_release_ref_ready,
    chatterbox_release_source_ready,
    detect_host_triple,
    exe_suffix_for_triple,
    learn_exemplar_audio_ready,
    sidecar_build_manifest_ready,
)
from scripts.dist.repair_macos_app_sidecar_symlinks import DYLIB_DIRS  # noqa: E402


@dataclass
class MacOSAppBundleStatus:
    app: str
    triple: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    developer_id: str = ""
    sidecar_binary: str = ""
    chatterbox_ref: str = ""
    chatterbox_source: str = ""
    smoke_stdout: str = ""

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _is_executable_file(path: Path, *, min_bytes: int = DEFAULT_MIN_BYTES) -> bool:
    return path.is_file() and path.stat().st_size >= min_bytes and os.access(path, os.X_OK)


def _check_repaired_dylib_links(internal: Path, status: MacOSAppBundleStatus) -> None:
    for dylib_dir in DYLIB_DIRS:
        target_dir = internal / dylib_dir
        if not target_dir.is_dir():
            continue
        for target in sorted(path for path in target_dir.iterdir() if path.is_file()):
            top_level = internal / target.name
            desired = f"{dylib_dir}/{target.name}"
            if not top_level.exists() and not top_level.is_symlink():
                status.fail(f"missing repaired top-level dylib link: {top_level}")
                continue
            if not top_level.is_symlink():
                status.fail(
                    f"flattened dylib copy still needs repair: {top_level} -> {desired}"
                )
                continue
            current = os.readlink(top_level)
            if current != desired:
                status.fail(
                    f"wrong dylib symlink target for {top_level}: {current!r}, expected {desired!r}"
                )


def _is_test_fixture_path(path: Path) -> bool:
    parts = path.parts
    for index, part in enumerate(parts):
        if part == "tests" and "fixtures" in parts[index + 1 :]:
            return True
    return False


def _check_no_test_fixtures(app: Path, status: MacOSAppBundleStatus) -> None:
    hits = [
        path.relative_to(app)
        for path in app.rglob("*")
        if _is_test_fixture_path(path.relative_to(app))
    ]
    if hits:
        preview = ", ".join(str(path) for path in sorted(hits)[:5])
        extra = "" if len(hits) <= 5 else f" (+{len(hits) - 5} more)"
        status.fail(f"test fixture payloads bundled: {preview}{extra}")


def _run_smoke(binary: Path, smoke: str, timeout_s: float, status: MacOSAppBundleStatus) -> None:
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
        status.fail(f"sidecar smoke failed to launch: {exc}")
        return

    status.smoke_stdout = result.stdout.strip()
    if result.returncode != 0:
        status.fail(
            f"sidecar smoke exited {result.returncode}: stderr={result.stderr.strip()!r}"
        )


def _run_codesign(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["codesign", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, str(exc)
    output = "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part.strip()
    )
    return result.returncode == 0, output


def _developer_id_signature_ready(
    app: Path,
    *,
    team_id: str | None = None,
) -> tuple[bool, str]:
    """Return whether ``app`` has a Developer ID signature with a resource seal."""
    seal = app / "Contents" / "_CodeSignature" / "CodeResources"
    if not seal.is_file():
        return False, f"Developer ID resource seal missing: {seal}"

    verify_ok, verify_output = _run_codesign(
        ["--verify", "--strict", "--verbose=4", str(app)]
    )
    if not verify_ok:
        return False, f"codesign verification failed: {verify_output}"

    details_ok, details = _run_codesign(["-dv", "--verbose=4", str(app)])
    if not details_ok:
        return False, f"codesign details failed: {details}"

    if "Authority=Developer ID Application:" not in details:
        return False, "signature is not a Developer ID Application signature"

    if "Sealed Resources version=" not in details:
        return False, "Developer ID signature has no sealed resources"

    actual_team_id = ""
    for line in details.splitlines():
        if line.startswith("TeamIdentifier="):
            actual_team_id = line.split("=", 1)[1].strip()
            break

    if team_id:
        if actual_team_id != team_id:
            return False, (
                f"Developer ID TeamIdentifier mismatch: got {actual_team_id!r}, "
                f"expected {team_id!r}"
            )
    elif not actual_team_id or actual_team_id.lower() == "not set":
        return False, "Developer ID TeamIdentifier is missing"

    return True, f"Developer ID signature ready: TeamIdentifier={actual_team_id}"


def check_macos_app_bundle_ready(
    app: Path,
    *,
    triple: str | None = None,
    min_bytes: int = DEFAULT_MIN_BYTES,
    require_chatterbox_ref: bool = False,
    require_chatterbox_source: bool = False,
    require_developer_id: bool = False,
    developer_team_id: str | None = None,
    smoke: str = "version",
    smoke_timeout_s: float = 20.0,
) -> MacOSAppBundleStatus:
    """Check that a macOS app bundle contains a repaired, runnable sidecar."""
    target_triple = triple or detect_host_triple()
    status = MacOSAppBundleStatus(app=str(app), triple=target_triple)

    if "apple-darwin" not in target_triple:
        status.fail(f"expected an apple-darwin triple, got {target_triple!r}")
        return status

    if not app.is_dir() or app.suffix != ".app":
        status.fail(f"app bundle not found or not a .app directory: {app}")
        return status

    info_plist = app / "Contents" / "Info.plist"
    if not info_plist.is_file():
        status.fail(f"missing Info.plist: {info_plist}")

    main_binary = app / "Contents" / "MacOS" / "vibemix"
    if not _is_executable_file(main_binary, min_bytes=min_bytes):
        status.fail(f"main app binary missing, tiny, or not executable: {main_binary}")

    if require_developer_id:
        signature_ok, signature_message = _developer_id_signature_ready(
            app,
            team_id=developer_team_id or os.environ.get("APPLE_TEAM_ID"),
        )
        status.developer_id = signature_message
        if not signature_ok:
            status.fail(signature_message)

    bundle_dir = (
        app / "Contents" / "Resources" / "binaries" / f"vibemix-core-{target_triple}"
    )
    sidecar = bundle_dir / f"vibemix-core-{target_triple}{exe_suffix_for_triple(target_triple)}"
    status.sidecar_binary = str(sidecar)
    if not _is_executable_file(sidecar, min_bytes=min_bytes):
        status.fail(f"sidecar binary missing, tiny, or not executable: {sidecar}")
        return status

    internal = bundle_dir / "_internal"
    if not internal.is_dir():
        status.fail(f"sidecar _internal directory missing: {internal}")
        return status

    _check_no_test_fixtures(app, status)
    _check_repaired_dylib_links(internal, status)
    exemplar_ok, exemplar_message = learn_exemplar_audio_ready(bundle_dir)
    if not exemplar_ok:
        status.fail(exemplar_message)
    manifest_ok, manifest_message = sidecar_build_manifest_ready(
        bundle_dir,
        root=_PROJECT_ROOT,
        expected_triple=target_triple,
    )
    if not manifest_ok:
        status.fail(manifest_message)
    if require_chatterbox_ref:
        ref_ok, ref_message = chatterbox_release_ref_ready(bundle_dir)
        status.chatterbox_ref = ref_message
        if not ref_ok:
            status.fail(ref_message)
    if require_chatterbox_source:
        source_ok, source_message = chatterbox_release_source_ready()
        status.chatterbox_source = source_message
        if not source_ok:
            status.fail(source_message)
    if status.ok:
        _run_smoke(sidecar, smoke, smoke_timeout_s, status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if a macOS .app is missing its repaired PyInstaller sidecar."
    )
    parser.add_argument("app", type=Path, help="path to vibemix.app")
    parser.add_argument("--triple", default=None, help="target triple; default detects host")
    parser.add_argument(
        "--min-bytes",
        type=int,
        default=DEFAULT_MIN_BYTES,
        help=f"minimum acceptable executable size (default: {DEFAULT_MIN_BYTES})",
    )
    parser.add_argument(
        "--smoke",
        choices=("version", "library-stats", "none"),
        default="version",
        help="sidecar command to run after structural checks",
    )
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
            "with a sealed resource manifest"
        ),
    )
    parser.add_argument(
        "--developer-team-id",
        default=None,
        help="optional Apple team id expected in the Developer ID signature",
    )
    parser.add_argument("--smoke-timeout-s", type=float, default=20.0)
    parser.add_argument("--json", action="store_true", help="print machine-readable status")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    try:
        status = check_macos_app_bundle_ready(
            args.app,
            triple=args.triple,
            min_bytes=args.min_bytes,
            require_chatterbox_ref=args.require_chatterbox_ref,
            require_chatterbox_source=args.require_chatterbox_source,
            require_developer_id=args.require_developer_id,
            developer_team_id=args.developer_team_id,
            smoke=args.smoke,
            smoke_timeout_s=args.smoke_timeout_s,
        )
    except RuntimeError as exc:
        print(f"[macos-app-bundle] FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(asdict(status), sort_keys=True))
    elif status.ok:
        if not args.quiet:
            print(f"[macos-app-bundle] OK: {status.sidecar_binary}")
    else:
        for error in status.errors:
            print(f"[macos-app-bundle] FAIL: {error}", file=sys.stderr)
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
