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
import wave
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

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
from vibemix.library.model_assets import (  # noqa: E402
    CHATTERBOX_MODEL_REPO,
    CHATTERBOX_MODEL_REVISION,
    CHATTERBOX_REQUIRED_FILES,
)

BINARIES_REL = Path("tauri/src-tauri/binaries")
IPC_SCHEMA_REL = Path("tauri/ui/src/ipc/messages.schema.json")
DEFAULT_MIN_BYTES = 4096
CHATTERBOX_REF_NAME = "cohost_voice_ref.wav"
CHATTERBOX_REF_REL = Path("_internal") / "models" / "chatterbox" / CHATTERBOX_REF_NAME
CHATTERBOX_REF_CHANNELS = 1
CHATTERBOX_REF_SAMPLE_WIDTH = 2
CHATTERBOX_REF_SAMPLE_RATE = 24_000
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


def learn_exemplar_audio_ready(bundle_dir: Path) -> tuple[bool, str]:
    """Return whether the frozen sidecar carries the packaged Learn audio bank."""
    internal = bundle_dir / "_internal"
    missing = [rel for rel in LEARN_EXEMPLAR_WAVS if not (internal / rel).is_file()]
    if missing:
        preview = ", ".join(str(path) for path in missing[:4])
        extra = "" if len(missing) <= 4 else f" (+{len(missing) - 4} more)"
        return (False, f"Learn exemplar WAV bank missing from sidecar: {preview}{extra}")
    return (True, f"Learn exemplar WAV bank ready: {len(LEARN_EXEMPLAR_WAVS)} file(s)")


def _chatterbox_ref_wave_status(path: Path) -> tuple[bool, str]:
    try:
        with wave.open(str(path), "rb") as ref:
            channels = ref.getnchannels()
            sample_width = ref.getsampwidth()
            sample_rate = ref.getframerate()
            frames = ref.getnframes()
    except (OSError, EOFError, wave.Error) as exc:
        return (False, f"unreadable WAV: {path}: {exc}")

    if channels != CHATTERBOX_REF_CHANNELS:
        return (False, f"expected mono Chatterbox ref, got {channels} channel(s): {path}")
    if sample_width != CHATTERBOX_REF_SAMPLE_WIDTH:
        bits = sample_width * 8
        return (False, f"expected 16-bit PCM Chatterbox ref, got {bits}-bit: {path}")
    if sample_rate != CHATTERBOX_REF_SAMPLE_RATE:
        return (False, f"expected 24000 Hz Chatterbox ref, got {sample_rate} Hz: {path}")
    if frames <= 0:
        return (False, f"Chatterbox ref has no audio frames: {path}")
    return (True, f"bundled Chatterbox ref ready: {path}")


def chatterbox_release_ref_ready(bundle_dir: Path) -> tuple[bool, str]:
    """Return whether a sidecar bundle carries the production Chatterbox reference."""
    ref_path = bundle_dir / CHATTERBOX_REF_REL
    if not ref_path.is_file():
        return (
            False,
            f"Chatterbox release has no bundled voice reference. "
            f"Bundle {CHATTERBOX_REF_REL} from the approved production WAV.",
        )
    return _chatterbox_ref_wave_status(ref_path)


def chatterbox_release_source_ready() -> tuple[bool, str]:
    """Return whether the pinned public Chatterbox HF source still resolves."""
    repo = CHATTERBOX_MODEL_REPO
    revision = CHATTERBOX_MODEL_REVISION
    url = (
        "https://huggingface.co/api/models/"
        f"{quote(repo, safe='/')}/revision/{quote(revision, safe='')}?blobs=true"
    )
    try:
        req = Request(url, headers={"User-Agent": "vibemix-release-gate/1"})
        with urlopen(req, timeout=30) as response:  # nosec B310 - fixed HTTPS HF API
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return (
            False,
            "Chatterbox HF source check failed. Connect to the internet and verify "
            f"{repo}@{revision}: {exc}",
        )

    actual_sha = str(payload.get("sha") or "")
    if actual_sha != revision:
        return (
            False,
            f"Chatterbox HF revision mismatch: {repo}@{revision} resolved to {actual_sha!r}",
        )

    siblings = payload.get("siblings")
    if not isinstance(siblings, list):
        return (False, f"Chatterbox HF source response has no sibling file list: {repo}")
    sizes: dict[str, int] = {}
    for item in siblings:
        if not isinstance(item, dict):
            continue
        name = str(item.get("rfilename") or "")
        try:
            size = int(item.get("size") or item.get("lfs", {}).get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if name:
            sizes[name] = size

    missing = [rel for rel in CHATTERBOX_REQUIRED_FILES if rel not in sizes]
    wrong_size = [
        f"{rel}={sizes.get(rel)} expected {expected}"
        for rel, expected in CHATTERBOX_REQUIRED_FILES.items()
        if rel in sizes and sizes[rel] != expected
    ]
    if missing or wrong_size:
        detail = "; ".join(
            part
            for part in (
                f"missing {', '.join(missing)}" if missing else "",
                f"size mismatch {', '.join(wrong_size)}" if wrong_size else "",
            )
            if part
        )
        return (False, f"Chatterbox HF source is not the pinned release snapshot: {detail}")

    return (
        True,
        f"Chatterbox HF source ready: {repo}@{revision} "
        f"({len(CHATTERBOX_REQUIRED_FILES)} file(s))",
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
    require_chatterbox_ref: bool = False,
    require_chatterbox_source: bool = False,
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

    if require_chatterbox_ref:
        ref_ok, ref_message = chatterbox_release_ref_ready(bundle_dir)
        if not ref_ok:
            return SidecarBundleStatus(False, ref_message, binary)
    if require_chatterbox_source:
        source_ok, source_message = chatterbox_release_source_ready()
        if not source_ok:
            return SidecarBundleStatus(False, source_message, binary)

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
        "--require-chatterbox-ref",
        action="store_true",
        help=(
            f"release gate: require bundled {CHATTERBOX_REF_REL} as mono "
            "16-bit 24000 Hz WAV"
        ),
    )
    parser.add_argument(
        "--require-chatterbox-source",
        action="store_true",
        help=(
            "release gate: require the public Chatterbox HF repo and pinned "
            "revision to resolve"
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    try:
        status = check_sidecar_bundle_ready(
            root=args.root.resolve(),
            triple=args.triple,
            min_bytes=args.min_bytes,
            require_chatterbox_ref=args.require_chatterbox_ref,
            require_chatterbox_source=args.require_chatterbox_source,
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
