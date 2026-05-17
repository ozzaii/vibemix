# SPDX-License-Identifier: Apache-2.0
"""Phase 44 Plan 44-04 — Bravoh waitlist opt-in field on ConfigStore.

LAUNCH-05 adds a single new persisted bool to the sidecar config store:
``bravoh_waitlist_opt_in`` (default ``False``). The toggle is the only
Bravoh-funnel surface in vibemix; it is opt-in, default-OFF, signed-out
telemetry default-off per CONTEXT §LAUNCH-05.

These tests pin:
  a. The default-OFF contract — a fresh ``ConfigStore()`` reads
     ``bravoh_waitlist_opt_in == False``.
  b. The on-disk JSON read path — a saved ``true`` round-trips back.
  c. The round-trip — mutating the field, saving, and reloading
     recovers the change.
  d. The Phase 11/12 superset contract regression — adding the new
     key MUST NOT break the rule that unknown top-level keys (e.g.
     tauri-plugin-store's ``first_run_state`` wrapper, or a future
     field a newer build wrote) survive a load → save cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

from vibemix.runtime.config_store import ConfigStore, load_config, save_config


# ---------------------------------------------------------------------------
# (a) Default is OFF
# ---------------------------------------------------------------------------


def test_bravoh_waitlist_opt_in_default_off() -> None:
    """A fresh ``ConfigStore()`` has ``bravoh_waitlist_opt_in == False``.

    This is the LAUNCH-05 default-OFF contract — the user must explicitly
    opt in via the debrief toggle for any Bravoh-funnel surface to appear.
    """
    cfg = ConfigStore()
    assert cfg.bravoh_waitlist_opt_in is False


def test_load_missing_file_returns_bravoh_default_off(tmp_path: Path) -> None:
    """No config file on disk → defaults include ``bravoh_waitlist_opt_in=False``."""
    target = tmp_path / "config.json"
    cfg = load_config(target)
    assert cfg.bravoh_waitlist_opt_in is False


# ---------------------------------------------------------------------------
# (b) Loads a saved true
# ---------------------------------------------------------------------------


def test_load_existing_file_with_bravoh_true(tmp_path: Path) -> None:
    """A config.json with ``bravoh_waitlist_opt_in: true`` loads as True."""
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"bravoh_waitlist_opt_in": True}))
    cfg = load_config(target)
    assert cfg.bravoh_waitlist_opt_in is True


def test_load_existing_file_with_bravoh_false(tmp_path: Path) -> None:
    """A config.json with ``bravoh_waitlist_opt_in: false`` loads as False."""
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"bravoh_waitlist_opt_in": False}))
    cfg = load_config(target)
    assert cfg.bravoh_waitlist_opt_in is False


# ---------------------------------------------------------------------------
# (c) Round-trip mutate + save + reload
# ---------------------------------------------------------------------------


def test_bravoh_round_trip(tmp_path: Path) -> None:
    """Mutate → save → reload recovers the field verbatim."""
    target = tmp_path / "config.json"
    cfg = ConfigStore()
    assert cfg.bravoh_waitlist_opt_in is False
    cfg.bravoh_waitlist_opt_in = True
    save_config(cfg, target)

    on_disk = json.loads(target.read_text())
    assert on_disk["bravoh_waitlist_opt_in"] is True

    reloaded = load_config(target)
    assert reloaded.bravoh_waitlist_opt_in is True


def test_bravoh_round_trip_off_to_on_to_off(tmp_path: Path) -> None:
    """Toggle ON then OFF round-trips both directions."""
    target = tmp_path / "config.json"
    cfg = ConfigStore()
    cfg.bravoh_waitlist_opt_in = True
    save_config(cfg, target)
    assert load_config(target).bravoh_waitlist_opt_in is True

    cfg.bravoh_waitlist_opt_in = False
    save_config(cfg, target)
    assert load_config(target).bravoh_waitlist_opt_in is False


# ---------------------------------------------------------------------------
# (d) Phase 11/12 superset regression — unknown keys still survive
# ---------------------------------------------------------------------------


def test_bravoh_addition_preserves_unknown_top_level_keys(tmp_path: Path) -> None:
    """Adding the bravoh field must not break the Phase 12 superset contract.

    A config.json written by a future build (with an unknown top-level
    key) AND with bravoh_waitlist_opt_in set must round-trip both: the
    unknown key survives, AND the bravoh field is preserved.
    """
    target = tmp_path / "config.json"
    target.write_text(
        json.dumps(
            {
                "bravoh_waitlist_opt_in": True,
                "future_field_we_dont_own": {"nested": "value"},
                "first_run_state": {"first_run_completed": True},
            }
        )
    )
    loaded = load_config(target)
    assert loaded.bravoh_waitlist_opt_in is True
    assert "future_field_we_dont_own" in loaded.extra
    assert "first_run_state" in loaded.extra

    # Mutate something unrelated and save — unknown keys + bravoh both survive.
    loaded.voice = "puck"
    save_config(loaded, target)
    on_disk = json.loads(target.read_text())
    assert on_disk["voice"] == "puck"
    assert on_disk["bravoh_waitlist_opt_in"] is True
    assert on_disk["future_field_we_dont_own"] == {"nested": "value"}
    assert on_disk["first_run_state"] == {"first_run_completed": True}


def test_bravoh_drops_non_bool_from_disk(tmp_path: Path) -> None:
    """A corrupted on-disk value (e.g. ``"yes"`` or ``1``) falls back to False.

    Mirrors the existing ``lighter_blur`` / ``telemetry_consent`` guard —
    bool fields silently drop garbage rather than coercing truthiness.
    """
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"bravoh_waitlist_opt_in": "yes"}))
    cfg = load_config(target)
    assert cfg.bravoh_waitlist_opt_in is False

    target.write_text(json.dumps({"bravoh_waitlist_opt_in": 1}))
    cfg = load_config(target)
    assert cfg.bravoh_waitlist_opt_in is False
