# SPDX-License-Identifier: Apache-2.0
"""Plan 28-07 — staleness boundary + snooze persistence tests."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.library.staleness import (
    SNOOZE_DURATION_SECONDS,
    STALE_AGE_SECONDS,
    apply_snooze_action,
    emit_nudge_if_stale,
    is_snoozed,
    is_stale,
    load_snooze_state,
    save_snooze_state,
)


def _touch_with_age(path: Path, age_seconds: float) -> None:
    """Create empty file at path with mtime = now - age_seconds."""
    path.write_bytes(b"")
    target = time.time() - age_seconds
    os.utime(path, (target, target))


def test_30_day_boundary_below(tmp_path: Path) -> None:
    pkl = tmp_path / "library.pkl"
    _touch_with_age(pkl, STALE_AGE_SECONDS - 1)
    stale, age_days = is_stale(pkl)
    assert stale is False
    assert age_days == 29


def test_30_day_boundary_above(tmp_path: Path) -> None:
    pkl = tmp_path / "library.pkl"
    _touch_with_age(pkl, STALE_AGE_SECONDS + 1)
    stale, age_days = is_stale(pkl)
    assert stale is True
    assert age_days == 30


def test_31_day_stale(tmp_path: Path) -> None:
    pkl = tmp_path / "library.pkl"
    _touch_with_age(pkl, 31 * 86400)
    stale, age_days = is_stale(pkl)
    assert stale is True
    assert age_days == 31


def test_no_library_returns_false(tmp_path: Path) -> None:
    pkl = tmp_path / "no_such.pkl"
    stale, age_days = is_stale(pkl)
    assert stale is False
    assert age_days == 0


def test_snooze_persists(tmp_path: Path) -> None:
    sp = tmp_path / "state.json"
    target = time.time() + SNOOZE_DURATION_SECONDS
    save_snooze_state(target, sp)
    loaded = load_snooze_state(sp)
    assert loaded is not None
    assert abs(loaded - target) < 1.0


def test_emit_nudge_skipped_when_snoozed(tmp_path: Path) -> None:
    pkl = tmp_path / "library.pkl"
    _touch_with_age(pkl, 35 * 86400)  # stale
    sp = tmp_path / "state.json"
    save_snooze_state(time.time() + 86400, sp)  # snoozed for 1 day

    emit_ipc = MagicMock()
    fired = emit_nudge_if_stale(emit_ipc, pkl, sp)
    assert fired is False
    emit_ipc.assert_not_called()


def test_emit_nudge_after_snooze_expired(tmp_path: Path) -> None:
    pkl = tmp_path / "library.pkl"
    _touch_with_age(pkl, 35 * 86400)  # stale
    sp = tmp_path / "state.json"
    save_snooze_state(time.time() - 86400, sp)  # snooze expired yesterday

    emit_ipc = MagicMock()
    fired = emit_nudge_if_stale(emit_ipc, pkl, sp)
    assert fired is True
    emit_ipc.assert_called_once()
    msg_type, payload = emit_ipc.call_args.args
    assert msg_type == "ipc.library.staleness_nudge"
    assert payload["age_days"] == 35
    assert payload["schema_version"] == "1"


def test_emit_nudge_skipped_for_fresh_install(tmp_path: Path) -> None:
    """No library.pkl → no nudge for fresh-install users."""
    emit_ipc = MagicMock()
    fired = emit_nudge_if_stale(
        emit_ipc, tmp_path / "no_such.pkl", tmp_path / "state.json"
    )
    assert fired is False
    emit_ipc.assert_not_called()


def test_malformed_state_treated_as_empty(tmp_path: Path) -> None:
    sp = tmp_path / "state.json"
    sp.write_text("not json")
    assert load_snooze_state(sp) is None
    assert is_snoozed(sp) is False


def test_apply_snooze_7d_persists(tmp_path: Path) -> None:
    sp = tmp_path / "state.json"
    apply_snooze_action("snooze_7d", sp)
    loaded = load_snooze_state(sp)
    assert loaded is not None
    assert loaded - time.time() > SNOOZE_DURATION_SECONDS - 5
    assert loaded - time.time() < SNOOZE_DURATION_SECONDS + 5


def test_apply_dismiss_no_op(tmp_path: Path) -> None:
    sp = tmp_path / "state.json"
    apply_snooze_action("dismiss", sp)
    assert load_snooze_state(sp) is None


def test_apply_unknown_action_raises(tmp_path: Path) -> None:
    sp = tmp_path / "state.json"
    with pytest.raises(ValueError):
        apply_snooze_action("delete_library", sp)


def test_save_snooze_preserves_other_keys(tmp_path: Path) -> None:
    sp = tmp_path / "state.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({"unrelated_key": "preserve_me"}))
    save_snooze_state(time.time() + 1000, sp)
    data = json.loads(sp.read_text())
    assert data["unrelated_key"] == "preserve_me"
    assert "library_staleness_snoozed_until" in data


def test_atomic_write_no_corruption_on_dir_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sp = tmp_path / "state.json"
    save_snooze_state(time.time() + 1000, sp)
    original = sp.read_text()

    # Force os.replace to raise — simulates mid-write power-loss after the
    # tmp file is written but before atomic rename.
    def boom(*args, **kwargs):
        raise OSError("simulated power loss")

    monkeypatch.setattr("vibemix.library.staleness.os.replace", boom)

    with pytest.raises(OSError):
        save_snooze_state(time.time() + 99999, sp)

    # Original state must still be readable + intact.
    assert sp.read_text() == original
