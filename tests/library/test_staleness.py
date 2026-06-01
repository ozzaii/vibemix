# SPDX-License-Identifier: Apache-2.0
"""Plan 28-07 — staleness boundary + snooze persistence tests."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.library.staleness import (
    SNOOZE_DURATION_SECONDS,
    STALE_AGE_SECONDS,
    LibraryFreshness,
    apply_snooze_action,
    emit_nudge_if_stale,
    freshness_nudge_payload,
    is_snoozed,
    is_stale,
    library_freshness_status,
    load_snooze_state,
    save_snooze_state,
    watch_library_freshness,
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


def test_freshness_status_not_indexed(tmp_path: Path) -> None:
    status = library_freshness_status(tmp_path / "library.pkl")

    assert status.status == "not_indexed"
    assert status.stale is False
    assert status.reason == "library_cache_missing"
    assert status.age_days == 0
    assert status.to_dict()["source_path"] is None


def test_freshness_status_fresh_when_cache_matches_source(tmp_path: Path) -> None:
    from vibemix.library.rekordbox import RekordboxLibrary

    source = tmp_path / "collection.xml"
    source.write_text("<DJ_PLAYLISTS />", encoding="utf-8")
    mtime = time.time()
    os.utime(source, (mtime, mtime))
    cache = tmp_path / "library.pkl"
    old_cache = RekordboxLibrary.CACHE_PATH
    RekordboxLibrary.CACHE_PATH = cache
    try:
        RekordboxLibrary()._write_cache(str(source), mtime)
    finally:
        RekordboxLibrary.CACHE_PATH = old_cache

    status = library_freshness_status(cache, now=mtime + 10)

    assert status.status == "fresh"
    assert status.stale is False
    assert status.reason == "cache_current"
    assert status.source_path == str(source)


def test_freshness_status_stale_when_source_newer(tmp_path: Path) -> None:
    from vibemix.library.rekordbox import RekordboxLibrary

    source = tmp_path / "collection.xml"
    source.write_text("<DJ_PLAYLISTS />", encoding="utf-8")
    old_mtime = time.time() - 100
    os.utime(source, (old_mtime, old_mtime))
    cache = tmp_path / "library.pkl"
    old_cache = RekordboxLibrary.CACHE_PATH
    RekordboxLibrary.CACHE_PATH = cache
    try:
        RekordboxLibrary()._write_cache(str(source), old_mtime)
    finally:
        RekordboxLibrary.CACHE_PATH = old_cache
    new_mtime = old_mtime + 10
    os.utime(source, (new_mtime, new_mtime))

    status = library_freshness_status(cache, now=new_mtime + 1)

    assert status.status == "stale"
    assert status.stale is True
    assert status.reason == "source_newer_than_cache"
    assert status.source_mtime == new_mtime


def test_freshness_status_source_missing(tmp_path: Path) -> None:
    from vibemix.library.rekordbox import RekordboxLibrary

    source = tmp_path / "collection.xml"
    source.write_text("<DJ_PLAYLISTS />", encoding="utf-8")
    mtime = time.time()
    cache = tmp_path / "library.pkl"
    old_cache = RekordboxLibrary.CACHE_PATH
    RekordboxLibrary.CACHE_PATH = cache
    try:
        RekordboxLibrary()._write_cache(str(source), mtime)
    finally:
        RekordboxLibrary.CACHE_PATH = old_cache
    source.unlink()

    status = library_freshness_status(cache, now=mtime + 1)

    assert status.status == "source_missing"
    assert status.stale is True
    assert status.reason == "source_path_missing"


def test_freshness_nudge_payload_source_newer_than_cache(tmp_path: Path) -> None:
    from vibemix.library.rekordbox import RekordboxLibrary

    source = tmp_path / "collection.xml"
    source.write_text("<DJ_PLAYLISTS />", encoding="utf-8")
    old_mtime = time.time() - 100
    os.utime(source, (old_mtime, old_mtime))
    cache = tmp_path / "library.pkl"
    old_cache = RekordboxLibrary.CACHE_PATH
    RekordboxLibrary.CACHE_PATH = cache
    try:
        RekordboxLibrary()._write_cache(str(source), old_mtime)
    finally:
        RekordboxLibrary.CACHE_PATH = old_cache
    new_mtime = old_mtime + 10
    os.utime(source, (new_mtime, new_mtime))

    payload = freshness_nudge_payload(cache, tmp_path / "state.json", now=new_mtime + 1)

    assert payload is not None
    assert payload["age_days"] == 0
    assert payload["source_path"] == str(source)
    assert payload["reason"] == "source_newer_than_cache"
    assert payload["schema_version"] == "1"


def test_freshness_nudge_payload_skips_fresh_install(tmp_path: Path) -> None:
    payload = freshness_nudge_payload(tmp_path / "missing.pkl", tmp_path / "state.json")

    assert payload is None


def test_watch_library_freshness_emits_when_source_becomes_stale(tmp_path: Path) -> None:
    fresh = LibraryFreshness(
        status="fresh",
        stale=False,
        reason="cache_current",
        age_days=0,
        cache_path="/tmp/library.pkl",
        cache_mtime=1.0,
        source_mtime=1.0,
    )
    stale = LibraryFreshness(
        status="stale",
        stale=True,
        reason="source_newer_than_cache",
        age_days=0,
        cache_path="/tmp/library.pkl",
        cache_mtime=1.0,
        source_mtime=2.0,
    )
    calls = {"n": 0}

    def provider() -> LibraryFreshness:
        calls["n"] += 1
        return fresh if calls["n"] == 1 else stale

    async def _run() -> list[tuple[str, dict]]:
        stop = asyncio.Event()
        emitted: list[tuple[str, dict]] = []

        def emit(msg_type: str, payload: dict) -> None:
            emitted.append((msg_type, payload))
            stop.set()

        await asyncio.wait_for(
            watch_library_freshness(
                emit,
                stop,
                poll_seconds=0.01,
                state_path=tmp_path / "state.json",
                status_provider=provider,
            ),
            timeout=0.5,
        )
        return emitted

    emitted = asyncio.run(_run())

    assert emitted == [
        (
            "ipc.library.staleness_nudge",
            {
                "age_days": 0,
                "snoozed_until_ts": None,
                "source_path": None,
                "reason": "source_newer_than_cache",
                "schema_version": "1",
            },
        )
    ]


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
