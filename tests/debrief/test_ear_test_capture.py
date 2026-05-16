# SPDX-License-Identifier: Apache-2.0
"""Plan 42-03 Task 1 — ear-test capture writer contract.

Pins the schema-aligned validator + path-traversal rejection + atomic
write-then-read roundtrip for ``vibemix.debrief.ear_test_capture``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vibemix.debrief.ear_test_capture import (
    EarTestPayload,
    EarTestValidationError,
    SCHEMA_PATH,
    SLOP_FLAG_KEYS,
    validate_payload,
    write_ear_test_log,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _started_iso(seconds_ago: int = 3600) -> str:
    return (
        datetime.now(UTC) - timedelta(seconds=seconds_ago)
    ).replace(microsecond=0).isoformat()


def _zero_slop_flags() -> dict[str, bool]:
    return {k: False for k in SLOP_FLAG_KEYS}


def _happy_payload(**overrides) -> EarTestPayload:
    base = dict(
        session_id="20260516-001",
        started_at=_started_iso(),
        duration_s=1800,
        genre="techno",
        slop_flags=_zero_slop_flags(),
        free_form="Sounded grounded across all three transitions.",
        signed_by="kaan",
        signed_at=_now_iso(),
    )
    base.update(overrides)
    return EarTestPayload(**base)


# ---------------------------------------------------------------------------
# Schema-shape tests (validate_payload)
# ---------------------------------------------------------------------------


def test_payload_validates_happy_path():
    """All required fields populated, slop_flags all false → no exception."""
    payload = _happy_payload()
    # Should not raise.
    validate_payload(payload, schema_path=SCHEMA_PATH)


def test_payload_rejects_short_duration():
    """30 min minimum (1800 s) enforced at schema level."""
    payload = _happy_payload(duration_s=1500)
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_payload_rejects_unknown_signer():
    """v3.0 is single-DJ — only ``kaan`` allowed."""
    payload = _happy_payload(signed_by="francis")
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_payload_rejects_extra_property():
    """``additionalProperties: false`` — unknown keys reject."""
    # Bypass dataclass by passing a raw dict with an extra field.
    bad_dict = _happy_payload().to_dict()
    bad_dict["smuggled"] = "value"
    with pytest.raises(EarTestValidationError):
        validate_payload(bad_dict, schema_path=SCHEMA_PATH)


def test_payload_rejects_invalid_genre():
    """Genre enum is closed."""
    payload = _happy_payload(genre="trance")
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_slop_flag_keys_required():
    """All 4 slop-flag keys must be present."""
    bad_flags = {k: False for k in SLOP_FLAG_KEYS if k != "felt_late"}
    payload = _happy_payload(slop_flags=bad_flags)
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_slop_flag_extra_keys_rejected():
    """``additionalProperties: false`` on slop_flags object too."""
    extra_flags = _zero_slop_flags()
    extra_flags["felt_extra"] = False
    payload = _happy_payload(slop_flags=extra_flags)
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_slop_flag_value_must_be_bool():
    """Schema pins each slop_flag to boolean."""
    flags = _zero_slop_flags()
    flags["felt_slop"] = "false"  # type: ignore[assignment]
    payload = _happy_payload(slop_flags=flags)
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_free_form_maxlength_4000():
    """4001-char free_form rejects."""
    payload = _happy_payload(free_form="x" * 4001)
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


def test_session_id_pattern_enforced():
    """Disallowed chars in session_id reject at schema level."""
    payload = _happy_payload(session_id="bad space")
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)


# ---------------------------------------------------------------------------
# Path-traversal + atomic-write tests (write_ear_test_log)
# ---------------------------------------------------------------------------


def test_path_traversal_rejected(tmp_path: Path):
    """``session_id`` with ``..`` raises and writes nothing."""
    bad = _happy_payload()
    # Bypass dataclass frozen check by constructing a dict-shaped payload
    # — but write_ear_test_log accepts EarTestPayload only. Use the
    # explicit constructor with traversal char.
    with pytest.raises(EarTestValidationError):
        # The schema regex rejects ``..`` first (pattern excludes dots).
        # Both validators (jsonschema + fallback) reject before any disk
        # write occurs.
        write_ear_test_log(
            EarTestPayload(
                session_id="..escape",
                started_at=bad.started_at,
                duration_s=bad.duration_s,
                genre=bad.genre,
                slop_flags=bad.slop_flags,
                free_form=bad.free_form,
                signed_by=bad.signed_by,
                signed_at=bad.signed_at,
            ),
            base_dir=tmp_path,
            schema_path=SCHEMA_PATH,
        )
    # No file written.
    assert list(tmp_path.iterdir()) == []


def test_path_traversal_slash_rejected(tmp_path: Path):
    """Forward-slash in session_id also rejects."""
    bad = _happy_payload()
    with pytest.raises(EarTestValidationError):
        write_ear_test_log(
            EarTestPayload(
                session_id="evil/path",
                started_at=bad.started_at,
                duration_s=bad.duration_s,
                genre=bad.genre,
                slop_flags=bad.slop_flags,
                free_form=bad.free_form,
                signed_by=bad.signed_by,
                signed_at=bad.signed_at,
            ),
            base_dir=tmp_path,
            schema_path=SCHEMA_PATH,
        )
    assert list(tmp_path.iterdir()) == []


def test_atomic_write_roundtrip(tmp_path: Path):
    """write → read JSON → deep-equal to payload.to_dict()."""
    payload = _happy_payload(
        free_form="Transitions felt grounded; layer arrival "
        "on track 3 was a touch dry but not slop."
    )
    out_path = write_ear_test_log(
        payload, base_dir=tmp_path, schema_path=SCHEMA_PATH
    )
    assert out_path == tmp_path / f"{payload.session_id}.json"
    assert out_path.is_file()
    re_read = json.loads(out_path.read_text(encoding="utf-8"))
    assert re_read == payload.to_dict()


def test_write_creates_base_dir(tmp_path: Path):
    """Writer creates the parent dir if absent (mirror persistence.py)."""
    target = tmp_path / "nested" / "ear-test-logs"
    assert not target.exists()
    payload = _happy_payload()
    write_ear_test_log(payload, base_dir=target, schema_path=SCHEMA_PATH)
    assert (target / f"{payload.session_id}.json").is_file()


def test_write_overwrites_existing(tmp_path: Path):
    """Same session_id rewrites — last sign-off wins for that session."""
    p1 = _happy_payload(free_form="first take")
    p2 = _happy_payload(free_form="second take, same session")
    write_ear_test_log(p1, base_dir=tmp_path, schema_path=SCHEMA_PATH)
    write_ear_test_log(p2, base_dir=tmp_path, schema_path=SCHEMA_PATH)
    re_read = json.loads(
        (tmp_path / f"{p1.session_id}.json").read_text(encoding="utf-8")
    )
    assert re_read["free_form"] == "second take, same session"
