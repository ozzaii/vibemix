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
IPC_SCHEMA_REL = Path("tauri/ui/src/ipc/messages.schema.json")
DEFAULT_MIN_BYTES = 4096
MOSS_MODEL_DIRNAME = "MOSS-TTS-Nano-100M-ONNX"
MOSS_MANIFEST = "browser_poc_manifest.json"
MOSS_ARCHIVE_URL_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_URL"
MOSS_ARCHIVE_SHA_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_SHA256"
MOSS_ARCHIVE_SIZE_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_SIZE"


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


def _bundled_ipc_schema(bundle_dir: Path) -> Path:
    return bundle_dir / "_internal" / IPC_SCHEMA_REL


def _source_ipc_schema(root: Path) -> Path:
    return root / IPC_SCHEMA_REL


def _moss_archive_pin_errors() -> list[str]:
    """Return release-source pin errors for the hosted MOSS model archive."""
    url = os.environ.get(MOSS_ARCHIVE_URL_ENV, "").strip()
    if not url:
        return [f"{MOSS_ARCHIVE_URL_ENV} is not set"]

    errors: list[str] = []
    if not url.startswith("https://"):
        errors.append(f"{MOSS_ARCHIVE_URL_ENV} must be an https:// URL")

    sha = os.environ.get(MOSS_ARCHIVE_SHA_ENV, "").strip().lower()
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        errors.append(f"{MOSS_ARCHIVE_SHA_ENV} must be a 64-character lowercase SHA-256")

    raw_size = os.environ.get(MOSS_ARCHIVE_SIZE_ENV, "").strip()
    try:
        size = int(raw_size)
    except ValueError:
        size = 0
    if size <= 0:
        errors.append(f"{MOSS_ARCHIVE_SIZE_ENV} must be a positive byte count")

    return errors


def _bundled_moss_model_status(bundle_dir: Path) -> tuple[bool, str]:
    """Return whether ``bundle_dir`` contains a complete MOSS model tree.

    The PyInstaller layout may choose a different destination for future bundled
    data, so search for the canonical model dir name instead of hardcoding one
    path under ``_internal``. Validation reuses the runtime's cheap manifest
    checker, keeping the release gate aligned with what MOSS actually loads.
    """
    manifests = sorted(bundle_dir.rglob(f"{MOSS_MODEL_DIRNAME}/{MOSS_MANIFEST}"))
    if not manifests:
        return (False, f"no bundled {MOSS_MODEL_DIRNAME}/{MOSS_MANIFEST}")

    from vibemix.agent.local_tts import MOSS_MODEL_DIR_ENV, model_status

    old = os.environ.get(MOSS_MODEL_DIR_ENV)
    had_old = MOSS_MODEL_DIR_ENV in os.environ
    details: list[str] = []
    try:
        for manifest in manifests:
            model_dir = manifest.parent
            os.environ[MOSS_MODEL_DIR_ENV] = str(model_dir)
            status = model_status()
            if bool(status["installed"]):
                return (True, f"bundled MOSS model ready: {model_dir}")
            missing = ", ".join(str(item) for item in status.get("missing", []))
            mismatched = ", ".join(str(item) for item in status.get("mismatched", []))
            detail = "; ".join(part for part in (missing, mismatched) if part)
            details.append(f"{model_dir}: {detail or 'not usable'}")
    finally:
        if had_old and old is not None:
            os.environ[MOSS_MODEL_DIR_ENV] = old
        else:
            os.environ.pop(MOSS_MODEL_DIR_ENV, None)

    return (False, "bundled MOSS model incomplete: " + " | ".join(details))


def _moss_release_source_ready(bundle_dir: Path) -> tuple[bool, str]:
    bundled_ok, bundled_detail = _bundled_moss_model_status(bundle_dir)
    if bundled_ok:
        return (True, bundled_detail)
    archive_errors = _moss_archive_pin_errors()
    if not archive_errors:
        return (True, f"MOSS archive pins configured via {MOSS_ARCHIVE_URL_ENV}")
    return (
        False,
        "MOSS-only release has no model source. "
        f"Bundle a complete {MOSS_MODEL_DIRNAME} tree or set "
        f"{MOSS_ARCHIVE_URL_ENV}/{MOSS_ARCHIVE_SHA_ENV}/{MOSS_ARCHIVE_SIZE_ENV}. "
        f"Bundled check: {bundled_detail}. Archive pins: {', '.join(archive_errors)}.",
    )


def check_sidecar_bundle_ready(
    *,
    root: Path = REPO_ROOT,
    triple: str | None = None,
    min_bytes: int = DEFAULT_MIN_BYTES,
    require_moss_source: bool = False,
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

    source_schema = _source_ipc_schema(root)
    if source_schema.is_file():
        bundled_schema = _bundled_ipc_schema(bundle_dir)
        if not bundled_schema.is_file():
            return SidecarBundleStatus(
                False,
                f"bundled IPC schema missing: {bundled_schema}. Run `{build_cmd}`.",
                binary,
            )
        if bundled_schema.read_bytes() != source_schema.read_bytes():
            return SidecarBundleStatus(
                False,
                f"bundled IPC schema is stale: {bundled_schema}. Run `{build_cmd}`.",
                binary,
            )

    if require_moss_source:
        moss_ok, moss_message = _moss_release_source_ready(bundle_dir)
        if not moss_ok:
            return SidecarBundleStatus(False, moss_message, binary)

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
    parser.add_argument(
        "--require-moss-source",
        action="store_true",
        help=(
            "release gate: require either a complete bundled MOSS model tree or "
            "verified VIBEMIX_MOSS_TTS_ARCHIVE_* pins"
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    try:
        status = check_sidecar_bundle_ready(
            root=args.root.resolve(),
            triple=args.triple,
            min_bytes=args.min_bytes,
            require_moss_source=args.require_moss_source,
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
