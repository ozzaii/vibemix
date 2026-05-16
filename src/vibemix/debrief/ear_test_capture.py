# SPDX-License-Identifier: Apache-2.0
"""Ear-test capture writer for the v3.0 hybrid hallucination gate.

Plan 42-03 (GATE-05 + GATE-07). When the Phase 29 debrief window's
"Rate this session for release-gate" toggle is opted in, the form
payload crosses the Tauri IPC (or, in dev mode, the debrief WS client
on 127.0.0.1:8766) into this module. We:

1. Validate the payload against ``eval/ear-test-logs/schema.json``
   (JSON Schema draft 2020-12).
2. Reject path-traversal attempts in ``session_id`` (defense in depth
   on top of the schema's regex — same pattern as Phase 29
   ``test_session_dir_path_traversal_rejected.py``).
3. Atomically write ``<base_dir>/<session_id>.json`` via temp file +
   ``os.replace`` (mirrors ``vibemix.debrief.persistence``).

The output is consumed by ``scripts/release/check_ear_test.sh`` (the
14-day window math + ≥ 2 genres + zero-slop-flag gate).

See ``eval/EAR-TEST-PROTOCOL.md`` for the protocol that produced this
shape.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "EAR_TEST_LOG_DIR",
    "SCHEMA_PATH",
    "SLOP_FLAG_KEYS",
    "GENRE_ENUM",
    "EarTestPayload",
    "validate_payload",
    "write_ear_test_log",
]

logger = logging.getLogger(__name__)

# Default landing directory. Tests override via the ``base_dir`` argument.
EAR_TEST_LOG_DIR = Path("eval/ear-test-logs")

# Schema path is relative to repo root; tests resolve it explicitly to keep
# the writer importable in CI environments that don't share cwd with repo.
SCHEMA_PATH = Path("eval/ear-test-logs/schema.json")

# Slop-flag taxonomy (Plan 42-03 D-GATE-05). Order is documentation-only;
# the dict is unordered at runtime.
SLOP_FLAG_KEYS: tuple[str, ...] = (
    "felt_slop",
    "felt_scripted",
    "felt_late",
    "felt_generic",
)

# Genre enum mirrors the schema. Imports keep both definitions in sync via
# the ``test_payload_rejects_*`` suite.
GENRE_ENUM: tuple[str, ...] = (
    "hard_tek",
    "techno",
    "house",
    "hip_hop",
    "dnb",
    "dubstep",
    "other",
)

# Pinned to the JSON Schema pattern. Validated server-side regardless of
# what the UI sends.
_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Free-form textarea cap mirrors the schema's maxLength.
_FREE_FORM_MAX_LEN = 4000

# Minimum session duration (seconds) — schema-level 30-min rule.
_DURATION_MIN_S = 1800


class EarTestValidationError(ValueError):
    """Raised when an ear-test payload fails schema or invariant checks.

    Subclass of :class:`ValueError` so existing
    ``except ValueError`` blocks (e.g. in the Tauri IPC dispatch path)
    treat us as a generic input-validation failure.
    """


@dataclass(frozen=True)
class EarTestPayload:
    """Frozen, schema-aligned payload from the debrief UI."""

    session_id: str
    started_at: str
    duration_s: int
    genre: str
    slop_flags: dict[str, bool] = field(default_factory=dict)
    free_form: str = ""
    signed_by: str = "kaan"
    signed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict matching the schema shape."""
        # ``asdict`` deep-copies nested dicts so callers can mutate the
        # result without affecting the frozen payload.
        d = asdict(self)
        return d


def _load_schema(schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or SCHEMA_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def _has_jsonschema() -> bool:
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        return False
    return True


def _validate_dict(payload_dict: dict[str, Any]) -> None:
    """Fallback manual validator if ``jsonschema`` is unavailable.

    Pins the same invariants the JSON Schema enforces. Used as a
    safety net in environments where the dep isn't installed (we still
    fail closed on every contract bit).
    """

    required_keys = {
        "session_id",
        "started_at",
        "duration_s",
        "genre",
        "slop_flags",
        "free_form",
        "signed_by",
        "signed_at",
    }
    missing = required_keys - payload_dict.keys()
    if missing:
        raise EarTestValidationError(
            f"missing required keys: {sorted(missing)}"
        )

    extra = set(payload_dict.keys()) - required_keys
    if extra:
        raise EarTestValidationError(
            f"unknown keys (additionalProperties=false): {sorted(extra)}"
        )

    session_id = payload_dict["session_id"]
    if not isinstance(session_id, str) or not _SESSION_ID_PATTERN.match(
        session_id
    ):
        raise EarTestValidationError(
            f"session_id does not match pattern: {session_id!r}"
        )

    if not isinstance(payload_dict["started_at"], str):
        raise EarTestValidationError("started_at must be string")

    duration_s = payload_dict["duration_s"]
    if (
        not isinstance(duration_s, int)
        or isinstance(duration_s, bool)
        or duration_s < _DURATION_MIN_S
    ):
        raise EarTestValidationError(
            f"duration_s must be int >= {_DURATION_MIN_S}, got {duration_s!r}"
        )

    genre = payload_dict["genre"]
    if genre not in GENRE_ENUM:
        raise EarTestValidationError(
            f"genre not in enum {GENRE_ENUM}: {genre!r}"
        )

    slop_flags = payload_dict["slop_flags"]
    if not isinstance(slop_flags, dict):
        raise EarTestValidationError("slop_flags must be object")
    slop_required = set(SLOP_FLAG_KEYS)
    sf_missing = slop_required - slop_flags.keys()
    if sf_missing:
        raise EarTestValidationError(
            f"slop_flags missing keys: {sorted(sf_missing)}"
        )
    sf_extra = set(slop_flags.keys()) - slop_required
    if sf_extra:
        raise EarTestValidationError(
            f"slop_flags has unknown keys: {sorted(sf_extra)}"
        )
    for k, v in slop_flags.items():
        if not isinstance(v, bool):
            raise EarTestValidationError(
                f"slop_flags.{k} must be bool, got {v!r}"
            )

    free_form = payload_dict["free_form"]
    if not isinstance(free_form, str):
        raise EarTestValidationError("free_form must be string")
    if len(free_form) > _FREE_FORM_MAX_LEN:
        raise EarTestValidationError(
            f"free_form too long: {len(free_form)} > {_FREE_FORM_MAX_LEN}"
        )

    if payload_dict["signed_by"] != "kaan":
        raise EarTestValidationError(
            f"signed_by must be 'kaan' (v3.0 single-DJ): "
            f"{payload_dict['signed_by']!r}"
        )

    if not isinstance(payload_dict["signed_at"], str):
        raise EarTestValidationError("signed_at must be string")


def validate_payload(
    payload: EarTestPayload | dict[str, Any],
    schema_path: Path | None = None,
) -> None:
    """Validate a payload against the JSON Schema.

    Uses ``jsonschema.Draft202012Validator`` when available; falls back
    to a manual validator that pins the same invariants when the dep
    is absent (we fail closed regardless).

    Raises :class:`EarTestValidationError` on any contract violation.
    """

    payload_dict = (
        payload.to_dict() if isinstance(payload, EarTestPayload) else payload
    )

    if _has_jsonschema():
        import jsonschema

        schema = _load_schema(schema_path)
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(payload_dict), key=lambda e: e.path)
        if errors:
            # Coalesce errors into a single readable message (keeps the
            # exception surface a simple string for the IPC layer).
            messages = [f"{list(e.path)}: {e.message}" for e in errors]
            raise EarTestValidationError(
                "; ".join(messages)
            )
        return

    # Fallback path — keep contract identical.
    _validate_dict(payload_dict)


def _reject_path_traversal(session_id: str) -> None:
    """Defense in depth on top of the schema regex.

    The regex already excludes ``/``, ``\\``, and ``.`` — this rejects
    explicitly so the ValueError message surfaces the traversal intent
    instead of a generic regex mismatch.
    """

    if (
        ".." in session_id
        or "/" in session_id
        or "\\" in session_id
        or session_id.startswith(".")
    ):
        raise EarTestValidationError(
            f"session_id contains path-traversal characters: "
            f"{session_id!r}"
        )


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomic file write — mirrors vibemix.debrief.persistence."""
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


def write_ear_test_log(
    payload: EarTestPayload,
    base_dir: Path | str = EAR_TEST_LOG_DIR,
    schema_path: Path | None = None,
) -> Path:
    """Validate + atomically persist an ear-test log JSON file.

    Returns the path of the written file. Raises
    :class:`EarTestValidationError` on schema or path-traversal failures
    (no file is written in that case).
    """

    base_dir = Path(base_dir)

    # Validate first — never touch disk on a malformed payload.
    validate_payload(payload, schema_path=schema_path)

    # Defense-in-depth: the schema regex already excludes traversal
    # chars; this surfaces the failure with a clearer message.
    _reject_path_traversal(payload.session_id)

    out_path = base_dir / f"{payload.session_id}.json"

    body = json.dumps(payload.to_dict(), ensure_ascii=False, indent=2)
    _atomic_write_bytes(out_path, body.encode("utf-8"))

    logger.info(
        "[ear-test] wrote %s (genre=%s, duration_s=%d)",
        out_path,
        payload.genre,
        payload.duration_s,
    )
    return out_path
