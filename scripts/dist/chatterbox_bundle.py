# SPDX-License-Identifier: Apache-2.0
"""Helpers for bundling the local Chatterbox voice reference into sidecars.

The reference clip is release-owned/licensed content. It is intentionally not
vendored in git; release builders must place the approved 24 kHz mono WAV at
``~/.cache/vibemix/cohost_voice_ref.wav`` or set ``VIBEMIX_CHATTERBOX_REF``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CHATTERBOX_REF_ENV = "VIBEMIX_CHATTERBOX_REF"
CHATTERBOX_REF_NAME = "cohost_voice_ref.wav"
CHATTERBOX_BUNDLE_DEST = Path("models") / "chatterbox"


def default_chatterbox_ref_path() -> Path:
    cache = os.environ.get("VIBEMIX_CACHE_DIR") or os.path.join(Path.home(), ".cache", "vibemix")
    return Path(cache) / CHATTERBOX_REF_NAME


def source_chatterbox_ref_path() -> Path:
    override = os.environ.get(CHATTERBOX_REF_ENV)
    return Path(override).expanduser() if override else default_chatterbox_ref_path()


def collect_chatterbox_ref_datas() -> list[tuple[str, str]]:
    ref_path = source_chatterbox_ref_path()
    if not ref_path.is_file():
        print(
            "[chatterbox_bundle] Chatterbox ref not bundled: "
            f"{ref_path} not found",
            file=sys.stderr,
        )
        return []
    print(
        f"[chatterbox_bundle] bundled Chatterbox ref from {ref_path}",
        file=sys.stderr,
    )
    return [(str(ref_path), str(CHATTERBOX_BUNDLE_DEST))]
