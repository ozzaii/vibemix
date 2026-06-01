# SPDX-License-Identifier: Apache-2.0
"""Plan 42-03 Task 1 — ear-test capture validator contract.

Pins the schema-aligned validator + path-traversal rejection for
``vibemix.debrief.ear_test_capture``. Live writes are owned by the Rust
``write_ear_test_log`` Tauri command.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vibemix.debrief.ear_test_capture import (
    SCHEMA_PATH,
    SLOP_FLAG_KEYS,
    EarTestPayload,
    EarTestValidationError,
    validate_payload,
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


@pytest.mark.parametrize("session_id", ["..escape", "evil/path", ".hidden"])
def test_path_traversal_session_ids_reject(session_id: str):
    """Traversal-shaped ``session_id`` values reject at schema level."""
    payload = _happy_payload(session_id=session_id)
    with pytest.raises(EarTestValidationError):
        validate_payload(payload, schema_path=SCHEMA_PATH)
