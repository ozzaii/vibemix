# SPDX-License-Identifier: Apache-2.0
"""Helpers for bundling the local MOSS TTS model into PyInstaller sidecars."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MOSS_MODEL_DIR_ENV = "VIBEMIX_MOSS_TTS_DIR"
MOSS_MODEL_DIRNAME = "MOSS-TTS-Nano-100M-ONNX"
MOSS_CODEC_DIRNAME = "MOSS-Audio-Tokenizer-Nano-ONNX"
MOSS_MANIFEST = "browser_poc_manifest.json"
MOSS_BUNDLE_DEST = Path("models") / "moss-tts-onnx"


def default_moss_model_dir() -> Path:
    cache = os.environ.get("VIBEMIX_CACHE_DIR") or os.path.join(Path.home(), ".cache", "vibemix")
    return Path(cache) / "moss-tts-onnx" / MOSS_MODEL_DIRNAME


def source_moss_model_dir() -> Path:
    override = os.environ.get(MOSS_MODEL_DIR_ENV)
    return Path(override).expanduser() if override else default_moss_model_dir()


def _data_files_for_dir(src_dir: Path, *, root: Path) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        rel_parent = rel.parent
        files.append((str(path), str(MOSS_BUNDLE_DEST / rel_parent)))
    return files


def collect_moss_model_datas() -> list[tuple[str, str]]:
    """Return PyInstaller data tuples for the cached/configured MOSS model tree.

    The runtime and release verifier expect the bundled layout:
    ``_internal/models/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX`` plus its sibling
    tokenizer directory. If the model is absent, return an empty list; release
    builds that require local MOSS will fail later in the sidecar readiness gate
    instead of silently producing a mute app.
    """
    model_dir = source_moss_model_dir()
    if not (model_dir / MOSS_MANIFEST).is_file():
        print(
            "[moss_bundle] MOSS model not bundled: "
            f"{model_dir / MOSS_MANIFEST} not found",
            file=sys.stderr,
        )
        return []

    root = model_dir.parent
    source_dirs = [model_dir]
    codec_dir = root / MOSS_CODEC_DIRNAME
    if codec_dir.is_dir():
        source_dirs.append(codec_dir)
    else:
        print(
            "[moss_bundle] WARNING: MOSS codec sibling not found; "
            f"bundle may fail readiness: {codec_dir}",
            file=sys.stderr,
        )

    datas: list[tuple[str, str]] = []
    for source_dir in source_dirs:
        datas.extend(_data_files_for_dir(source_dir, root=root))
    print(
        f"[moss_bundle] bundled {len(datas)} MOSS model file(s) from {root}",
        file=sys.stderr,
    )
    return datas
