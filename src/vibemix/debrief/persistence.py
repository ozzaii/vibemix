# SPDX-License-Identifier: Apache-2.0
"""Persistence layer — atomic write+read of session_debrief.json + tldr.mp3.

Cache key is the SHA-256 of the MP3 bytes recorded in
``session_debrief.json``. On read, if the recorded sha256 doesn't match the
MP3 bytes on disk (e.g. user moved/edited it), :func:`read_debrief` returns
``None`` so the orchestrator re-generates.

Atomic write pattern: temp file beside target → ``os.replace`` for atomic
swap. Crash mid-write leaves either the old file or no file at all.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "SCHEMA_VERSION",
    "TLDR_MP3_FILENAME",
    "DEBRIEF_JSON_FILENAME",
    "read_debrief",
    "write_debrief",
]

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "v1"
DEBRIEF_JSON_FILENAME = "session_debrief.json"
TLDR_MP3_FILENAME = "debrief_tldr.mp3"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomic file write — temp + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def write_debrief(
    session_dir: Path,
    debrief_dict: dict[str, Any],
    tldr_mp3: bytes,
) -> tuple[Path, Path]:
    """Atomically write the debrief JSON and TLDR MP3 to ``session_dir``.

    Adds ``schema_version`` + ``tldr_sha256`` + ``tldr_path`` +
    ``generated_at`` keys to ``debrief_dict`` if they aren't already set.

    Returns: ``(json_path, mp3_path)``.
    """
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = session_dir / TLDR_MP3_FILENAME
    json_path = session_dir / DEBRIEF_JSON_FILENAME

    # Compute cache key + metadata before persisting.
    tldr_sha256 = _sha256_bytes(tldr_mp3)
    debrief_to_write = dict(debrief_dict)
    debrief_to_write.setdefault("schema_version", SCHEMA_VERSION)
    debrief_to_write["tldr_sha256"] = tldr_sha256
    debrief_to_write["tldr_path"] = TLDR_MP3_FILENAME
    debrief_to_write.setdefault(
        "generated_at", datetime.now(UTC).isoformat()
    )

    # Write MP3 first so a partial state can't be "json says cache hit but
    # mp3 missing". On a crash between the two writes we have an mp3 +
    # no json (orchestrator will regen).
    _atomic_write_bytes(mp3_path, tldr_mp3)

    json_payload = json.dumps(debrief_to_write, ensure_ascii=False, indent=2)
    _atomic_write_bytes(json_path, json_payload.encode("utf-8"))

    logger.info("[debrief] wrote %s (%d bytes mp3)", session_dir, len(tldr_mp3))
    return (json_path, mp3_path)


def read_debrief(session_dir: Path) -> dict[str, Any] | None:
    """Read a previously persisted debrief.

    Returns ``None`` if:

    - ``session_debrief.json`` is missing
    - ``debrief_tldr.mp3`` is missing
    - the recorded ``tldr_sha256`` does not match the MP3 bytes on disk
      (cache-invalidation)
    - the JSON is malformed
    """
    session_dir = Path(session_dir)
    json_path = session_dir / DEBRIEF_JSON_FILENAME
    mp3_path = session_dir / TLDR_MP3_FILENAME

    if not json_path.exists() or not mp3_path.exists():
        return None

    try:
        debrief = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("[debrief] read_debrief malformed json: %s", e)
        return None

    recorded_sha = debrief.get("tldr_sha256")
    if not recorded_sha:
        return None

    actual_sha = _sha256_bytes(mp3_path.read_bytes())
    if recorded_sha != actual_sha:
        logger.info(
            "[debrief] cache miss — tldr_sha256 drift in %s", session_dir
        )
        return None

    return debrief
