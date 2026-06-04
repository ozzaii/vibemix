# SPDX-License-Identifier: Apache-2.0
"""Validate the bundled ``vibemix-core`` sidecar resource tree.

This is a local/package-readiness guard. Release CI builds the PyInstaller
sidecar before Tauri packaging, but direct ``cargo tauri build`` can otherwise
bundle the committed ``.placeholder`` directories and produce an app that opens
without a launchable Python sidecar.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.build_sidecar import (  # noqa: E402
    BUILD_MANIFEST_NAME,
    BUILD_MANIFEST_SCHEMA,
    git_head,
    source_dirty_paths,
    source_fingerprint,
)

BINARIES_REL = Path("tauri/src-tauri/binaries")
IPC_SCHEMA_REL = Path("tauri/ui/src/ipc/messages.schema.json")
DEFAULT_MIN_BYTES = 4096
MOSS_MODEL_DIRNAME = "MOSS-TTS-Nano-100M-ONNX"
MOSS_MANIFEST = "browser_poc_manifest.json"
MOSS_ARCHIVE_URL_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_URL"
MOSS_ARCHIVE_SHA_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_SHA256"
MOSS_ARCHIVE_SIZE_ENV = "VIBEMIX_MOSS_TTS_ARCHIVE_SIZE"
LEARN_EXEMPLAR_WAVS: tuple[Path, ...] = (
    Path("vibemix/learn/assets/band_exemplars/high/vibemix_internal_high_hat_air.wav"),
    Path("vibemix/learn/assets/band_exemplars/low/vibemix_internal_low_bass_gate.wav"),
    Path("vibemix/learn/assets/band_exemplars/mid/vibemix_internal_mid_chord_body.wav"),
    Path("vibemix/learn/assets/band_exemplars/sub/vibemix_internal_sub_pulse.wav"),
)


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


def _is_test_fixture_path(path: Path) -> bool:
    parts = path.parts
    for index, part in enumerate(parts):
        if part == "tests" and "fixtures" in parts[index + 1 :]:
            return True
    return False


def _bundled_test_fixture_paths(bundle_dir: Path) -> list[Path]:
    return sorted(
        path.relative_to(bundle_dir)
        for path in bundle_dir.rglob("*")
        if _is_test_fixture_path(path.relative_to(bundle_dir))
    )


def _resolve_manifest_path(base: Path, rel_path: str) -> Path:
    path = Path(rel_path)
    return path if path.is_absolute() else (base / path).resolve(strict=False)


def _display_model_path(path: Path, model_dir: Path) -> str:
    for root in (model_dir, model_dir.parent):
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def _read_moss_json_file(
    path: Path,
    *,
    mismatched: list[str],
    model_dir: Path,
) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        mismatched.append(_display_model_path(path, model_dir))
        return None


def _add_moss_meta_files(
    *,
    meta_path: Path,
    required: set[Path],
    missing: list[str],
    mismatched: list[str],
    model_dir: Path,
) -> None:
    """Add ONNX/data files referenced by a MOSS meta file to ``required``."""
    if not meta_path.is_file():
        missing.append(_display_model_path(meta_path, model_dir))
        return
    meta = _read_moss_json_file(meta_path, mismatched=mismatched, model_dir=model_dir)
    if not meta:
        return
    base = meta_path.parent
    files = meta.get("files")
    if isinstance(files, dict):
        for rel_path in files.values():
            if isinstance(rel_path, str):
                required.add(_resolve_manifest_path(base, rel_path))
    external = meta.get("external_data_files")
    if isinstance(external, dict):
        for rel_paths in external.values():
            if isinstance(rel_paths, list):
                for rel_path in rel_paths:
                    if isinstance(rel_path, str):
                        required.add(_resolve_manifest_path(base, rel_path))


def _moss_model_tree_status(model_dir: Path) -> tuple[bool, str]:
    """Return whether ``model_dir`` has the MOSS files needed before ORT load.

    Keep this release verifier stdlib-only. Importing ``vibemix.agent.local_tts``
    would also import LiveKit, so a machine that can inspect a DMG could fail the
    artifact gate before it even checks the packaged files.
    """
    manifest_path = model_dir / MOSS_MANIFEST
    missing: list[str] = []
    mismatched: list[str] = []
    required: set[Path] = {manifest_path}

    if not manifest_path.is_file():
        missing.append(MOSS_MANIFEST)
    else:
        manifest = _read_moss_json_file(
            manifest_path,
            mismatched=mismatched,
            model_dir=model_dir,
        )
        if manifest:
            model_files = manifest.get("model_files")
            if isinstance(model_files, dict):
                for key, rel_path in model_files.items():
                    if not isinstance(rel_path, str):
                        continue
                    path = _resolve_manifest_path(model_dir, rel_path)
                    required.add(path)
                    if key in {"tts_meta", "codec_meta"}:
                        _add_moss_meta_files(
                            meta_path=path,
                            required=required,
                            missing=missing,
                            mismatched=mismatched,
                            model_dir=model_dir,
                        )

    for path in sorted(required, key=lambda item: str(item)):
        if not path.is_file():
            display = _display_model_path(path, model_dir)
            if display not in missing:
                missing.append(display)

    if not missing and not mismatched:
        return (True, f"bundled MOSS model ready: {model_dir}")
    detail = "; ".join(
        part
        for part in (
            "missing " + ", ".join(missing) if missing else "",
            "mismatched " + ", ".join(mismatched) if mismatched else "",
        )
        if part
    )
    return (False, f"{model_dir}: {detail or 'not usable'}")


def learn_exemplar_audio_ready(bundle_dir: Path) -> tuple[bool, str]:
    """Return whether the frozen sidecar carries the packaged Learn audio bank."""
    internal = bundle_dir / "_internal"
    missing = [rel for rel in LEARN_EXEMPLAR_WAVS if not (internal / rel).is_file()]
    if missing:
        preview = ", ".join(str(path) for path in missing[:4])
        extra = "" if len(missing) <= 4 else f" (+{len(missing) - 4} more)"
        return (False, f"Learn exemplar WAV bank missing from sidecar: {preview}{extra}")
    return (True, f"Learn exemplar WAV bank ready: {len(LEARN_EXEMPLAR_WAVS)} file(s)")


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
    path under ``_internal``.
    """
    manifests = sorted(bundle_dir.rglob(f"{MOSS_MODEL_DIRNAME}/{MOSS_MANIFEST}"))
    if not manifests:
        return (False, f"no bundled {MOSS_MODEL_DIRNAME}/{MOSS_MANIFEST}")

    details: list[str] = []
    for manifest in manifests:
        model_dir = manifest.parent
        ok, detail = _moss_model_tree_status(model_dir)
        if ok:
            return (True, detail)
        details.append(detail)

    return (False, "bundled MOSS model incomplete: " + " | ".join(details))


def moss_release_source_ready(bundle_dir: Path) -> tuple[bool, str]:
    """Return whether a sidecar bundle has a release-usable MOSS model source."""
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


def _preview_paths(paths: list[str], *, limit: int = 5) -> str:
    preview = ", ".join(paths[:limit])
    extra = "" if len(paths) <= limit else f" (+{len(paths) - limit} more)"
    return preview + extra


def sidecar_build_manifest_ready(
    bundle_dir: Path,
    *,
    root: Path = REPO_ROOT,
    expected_triple: str | None = None,
) -> tuple[bool, str]:
    """Return whether the frozen sidecar was built from the current source bytes."""
    manifest_path = bundle_dir / BUILD_MANIFEST_NAME
    build_cmd = build_command_for_triple(expected_triple or detect_host_triple())

    if not manifest_path.is_file():
        return (
            False,
            f"sidecar source manifest missing: {manifest_path}. Run `{build_cmd}`.",
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return (
            False,
            f"sidecar source manifest unreadable: {manifest_path}: {exc}. Run `{build_cmd}`.",
        )

    if manifest.get("schema") != BUILD_MANIFEST_SCHEMA:
        return (
            False,
            f"sidecar source manifest schema is stale: {manifest_path}. Run `{build_cmd}`.",
        )

    if expected_triple and manifest.get("triple") != expected_triple:
        return (
            False,
            "sidecar source manifest triple mismatch: "
            f"{manifest.get('triple')!r} != {expected_triple!r}. Run `{build_cmd}`.",
        )

    recorded_dirty = manifest.get("source_dirty")
    if recorded_dirty:
        dirty = recorded_dirty if isinstance(recorded_dirty, list) else [str(recorded_dirty)]
        return (
            False,
            "sidecar was built from dirty runtime-package source: "
            f"{_preview_paths([str(path) for path in dirty])}. Commit/rebuild via `{build_cmd}`.",
        )

    try:
        current_dirty = source_dirty_paths(root=root)
        current_head = git_head(root=root)
        current_fingerprint = source_fingerprint(root=root)
    except Exception as exc:
        return (
            False,
            f"could not compute current sidecar source fingerprint: {exc}. Run `{build_cmd}`.",
        )

    if current_dirty:
        return (
            False,
            "runtime-package source is dirty after the sidecar was frozen: "
            f"{_preview_paths(current_dirty)}. Commit/rebuild via `{build_cmd}`.",
        )

    if manifest.get("git_head") != current_head:
        return (
            False,
            "sidecar source manifest git_head is stale: "
            f"{manifest.get('git_head')!r} != {current_head!r}. Run `{build_cmd}`.",
        )

    if manifest.get("source_fingerprint") != current_fingerprint:
        return (
            False,
            f"sidecar source manifest fingerprint is stale: {manifest_path}. Run `{build_cmd}`.",
        )

    return (True, f"sidecar source manifest ready: {manifest_path}")


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

    fixture_hits = _bundled_test_fixture_paths(bundle_dir)
    if fixture_hits:
        preview = ", ".join(str(path) for path in fixture_hits[:5])
        extra = "" if len(fixture_hits) <= 5 else f" (+{len(fixture_hits) - 5} more)"
        return SidecarBundleStatus(
            False,
            f"test fixture payloads bundled in sidecar: {preview}{extra}. Run `{build_cmd}`.",
            binary,
        )

    exemplar_ok, exemplar_message = learn_exemplar_audio_ready(bundle_dir)
    if not exemplar_ok:
        return SidecarBundleStatus(False, f"{exemplar_message}. Run `{build_cmd}`.", binary)

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

    manifest_ok, manifest_message = sidecar_build_manifest_ready(
        bundle_dir,
        root=root,
        expected_triple=target_triple,
    )
    if not manifest_ok:
        return SidecarBundleStatus(False, manifest_message, binary)

    if require_moss_source:
        moss_ok, moss_message = moss_release_source_ready(bundle_dir)
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
