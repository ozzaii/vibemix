# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 03 — 3-trigger retention sweep integration tests.

Covers the 7 plan Test scenarios:

  1. Boot trigger:  SessionLoop's recordings-init path calls run_retention_sweep
                    once with current config.
  2. Settings change trigger: SettingsApplier._apply_retention fires sweep with
                              the NEW value AFTER save_config.
  3. Session close trigger: SessionLoop.on_session_close() fires sweep.
  4. ∞ sentinel: retention_days=36500 returns [] WITHOUT scanning (mocked
                 scandir asserted not called).
  5. Usage emit after sweep: ipc.recordings.usage emitted on the bus after
                             each sweep trigger; payload matches RecordingsIndex.compute_usage.
  6. Best-effort sweep: one rmtree raise doesn't block subsequent entries +
                        usage still emitted.
  7. Events handler: SessionLoop._on_recordings_events emits events_result on
                     valid payload + ipc.error on path-traversal.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.recordings_index import (
    RecordingsIndex,
    RetentionSweepResult,
    run_retention_sweep,
)
from vibemix.runtime.session_loop import SessionLoop
from vibemix.runtime.settings import SettingsApplier
from vibemix.ui_bus.validator import validate_message


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------


class FakeBus:
    """In-memory stand-in for ``vibemix.runtime.ws_bus.WizardBus``."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self.emitted: list[dict] = []
        self.started = False
        self.stopped = False

    def register_handler(
        self, message_type: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        self.handlers[message_type] = handler

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def emit(self, msg: dict) -> None:
        validate_message(msg)
        self.emitted.append(json.loads(json.dumps(msg)))

    def emitted_by_type(self, msg_type: str) -> list[dict]:
        return [m for m in self.emitted if m.get("type") == msg_type]


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture(autouse=True)
def _redirect_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    return target


# ---------------------------------------------------------------------------
# Test 1 — boot trigger fires sweep once with current retention_days
# ---------------------------------------------------------------------------


def test_boot_fires_retention_sweep_once_with_current_config(
    tmp_recordings_dir: Path, fake_bus: FakeBus
) -> None:
    cfg = ConfigStore(retention_days=5)
    with patch(
        "vibemix.runtime.session_loop.run_retention_sweep",
        return_value=RetentionSweepResult([], 0),
    ) as sweep_mock:
        loop = SessionLoop(
            fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
        )
        asyncio.run(loop.run_boot_sweeps())

    sweep_mock.assert_called_once()
    args = sweep_mock.call_args
    assert args[0][0] == tmp_recordings_dir
    assert args[0][1] == 5


def test_boot_emits_recordings_usage_after_sweep(
    tmp_recordings_dir: Path, fake_bus: FakeBus, make_fake_session
) -> None:
    # Plant 2 sessions so usage is non-zero.
    make_fake_session(name="20260513-100000")
    make_fake_session(name="20260513-110000")
    cfg = ConfigStore(retention_days=36500)  # ∞ — no prune; just usage emit
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    asyncio.run(loop.run_boot_sweeps())

    usages = fake_bus.emitted_by_type("ipc.recordings.usage")
    assert len(usages) >= 1
    final_payload = usages[-1]["payload"]
    assert final_payload["sessions"] == 2
    # bytes_total is the scandir-summed value — assert it matches compute_usage.
    _, expected_bytes = RecordingsIndex(tmp_recordings_dir).compute_usage()
    assert final_payload["bytes_total"] == expected_bytes


# ---------------------------------------------------------------------------
# Test 2 — settings-change trigger fires sweep with NEW value
# ---------------------------------------------------------------------------


def test_settings_change_fires_sweep_with_new_value(
    tmp_recordings_dir: Path, fake_bus: FakeBus
) -> None:
    cfg = ConfigStore(retention_days=7)
    applier = SettingsApplier(
        config_store=cfg, recordings_root=tmp_recordings_dir, ws_bus=fake_bus
    )
    with patch(
        "vibemix.runtime.recordings_index.run_retention_sweep",
        return_value=RetentionSweepResult([], 0),
    ) as sweep_mock:
        ok, err = asyncio.run(applier.apply("retention_days", 3))
    assert ok is True
    assert err is None
    sweep_mock.assert_called_once()
    args = sweep_mock.call_args
    assert args[0][0] == tmp_recordings_dir
    assert args[0][1] == 3  # NEW value, not previous (7)
    assert cfg.retention_days == 3


# ---------------------------------------------------------------------------
# Test 3 — session-close trigger fires sweep
# ---------------------------------------------------------------------------


def test_session_close_fires_sweep_and_emits_usage(
    tmp_recordings_dir: Path, fake_bus: FakeBus, make_fake_session
) -> None:
    make_fake_session(name="20260513-100000")
    cfg = ConfigStore(retention_days=7)
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    with patch(
        "vibemix.runtime.session_loop.run_retention_sweep",
        return_value=RetentionSweepResult([], 0),
    ) as sweep_mock:
        asyncio.run(loop.on_session_close())
    sweep_mock.assert_called_once()
    args = sweep_mock.call_args
    assert args[0][0] == tmp_recordings_dir
    assert args[0][1] == 7
    usages = fake_bus.emitted_by_type("ipc.recordings.usage")
    assert len(usages) == 1


# ---------------------------------------------------------------------------
# Test 4 — ∞ sentinel skip — run_retention_sweep itself returns [] without scan
# ---------------------------------------------------------------------------


def test_sentinel_36500_skips_scandir(
    tmp_recordings_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_calls: list[Any] = []
    real_scandir = __import__("os").scandir

    def tracking_scandir(*args, **kwargs):
        scan_calls.append(args)
        return real_scandir(*args, **kwargs)

    monkeypatch.setattr("vibemix.runtime.recordings_index.os.scandir", tracking_scandir)
    result = run_retention_sweep(tmp_recordings_dir, 36500)
    assert result.deleted_names == []
    assert result.bytes_pruned == 0
    assert scan_calls == []  # sentinel short-circuited BEFORE any scandir call


def test_sentinel_skips_when_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "definitely-not-there"
    sentinel_result = run_retention_sweep(missing, 36500)
    assert sentinel_result.deleted_names == []
    assert sentinel_result.bytes_pruned == 0
    short_result = run_retention_sweep(missing, 7)
    assert short_result.deleted_names == []
    assert short_result.bytes_pruned == 0


def test_retention_sweep_deletes_only_old_sessions(
    tmp_recordings_dir: Path, make_fake_session
) -> None:
    # Two sessions: one 10 days old (should be pruned with retention=7),
    # one fresh (must remain).
    old_name = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d-%H%M%S")
    new_name = datetime.now().strftime("%Y%m%d-%H%M%S")
    old = make_fake_session(name=old_name)
    new = make_fake_session(name=new_name)

    result = run_retention_sweep(tmp_recordings_dir, 7)
    assert old_name in result.deleted_names
    assert new_name not in result.deleted_names
    assert not old.exists()
    assert new.exists()


# ---------------------------------------------------------------------------
# Test 5 — usage emit after settings-change sweep
# ---------------------------------------------------------------------------


def test_settings_change_emits_recordings_usage(
    tmp_recordings_dir: Path, fake_bus: FakeBus, make_fake_session
) -> None:
    make_fake_session(name="20260513-100000")
    make_fake_session(name="20260513-110000")
    cfg = ConfigStore(retention_days=36500)
    applier = SettingsApplier(
        config_store=cfg, recordings_root=tmp_recordings_dir, ws_bus=fake_bus
    )
    ok, err = asyncio.run(applier.apply("retention_days", 36500))
    assert ok is True
    assert err is None
    usages = fake_bus.emitted_by_type("ipc.recordings.usage")
    assert len(usages) == 1
    payload = usages[0]["payload"]
    assert payload["sessions"] == 2
    _, expected = RecordingsIndex(tmp_recordings_dir).compute_usage()
    assert payload["bytes_total"] == expected


# ---------------------------------------------------------------------------
# Test 6 — best-effort: one rmtree raise doesn't block other entries
# ---------------------------------------------------------------------------


def test_best_effort_sweep_continues_past_rmtree_error(
    tmp_recordings_dir: Path,
    fake_bus: FakeBus,
    make_fake_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Two old sessions — both eligible for prune.
    old_a = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d-%H%M%S")
    older_b = (datetime.now() - timedelta(days=20)).strftime("%Y%m%d-%H%M%S")
    sd_a = make_fake_session(name=old_a)
    sd_b = make_fake_session(name=older_b)

    real_rmtree = shutil.rmtree

    def patched_rmtree(path, *args, **kwargs):
        # Raise on the first dir only — defeats ignore_errors=True by raising
        # OUTSIDE the rmtree internals (the outer try/except in
        # run_retention_sweep is what we're exercising here).
        if str(path).endswith(old_a):
            raise OSError("simulated lock on %s" % path)
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(
        "vibemix.runtime.recordings_index.shutil.rmtree", patched_rmtree
    )
    result = run_retention_sweep(tmp_recordings_dir, 7)
    # The locked one is NOT in deleted, the other IS.
    assert old_a not in result.deleted_names
    assert older_b in result.deleted_names
    # Locked dir still on disk; other one is gone.
    assert sd_a.exists()
    assert not sd_b.exists()


# ---------------------------------------------------------------------------
# Test 7 — _on_recordings_events handler — valid + path-traversal
# ---------------------------------------------------------------------------


def test_on_recordings_events_valid_emits_events_result(
    tmp_recordings_dir: Path, fake_bus: FakeBus, make_fake_session
) -> None:
    sd = make_fake_session(name="20260513-210410")
    events_path = sd / "events.jsonl"
    events_path.write_text(
        '{"t": 0.0, "kind": "session_start"}\n'
        '{"t": 1.5, "kind": "trigger", "reason": "manual"}\n'
        '{"t": 5.0, "kind": "ai_text", "text": "hype"\n'  # malformed (no brace)
        '{"t": 7.0, "kind": "controller_move", "control": "play_a"}\n',
        encoding="utf-8",
    )
    cfg = ConfigStore()
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    loop.register_handlers()

    msg = {
        "type": "ipc.recordings.events",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {"session_dir": "20260513-210410"},
    }
    asyncio.run(loop._on_recordings_events(msg))
    results = fake_bus.emitted_by_type("ipc.recordings.events_result")
    assert len(results) == 1
    payload = results[0]["payload"]
    assert payload["session_dir"] == "20260513-210410"
    assert isinstance(payload["events"], list)
    # 3 valid records, malformed line skipped.
    assert len(payload["events"]) == 3
    assert payload["events"][0]["kind"] == "session_start"
    assert payload["events"][1]["kind"] == "trigger"
    assert payload["events"][2]["kind"] == "controller_move"


def test_on_recordings_events_rejects_path_traversal(
    tmp_recordings_dir: Path, fake_bus: FakeBus
) -> None:
    # Plant a sentinel outside recordings_root — must never be read.
    sibling = tmp_recordings_dir.parent / "secret.txt"
    sibling.write_text('{"t": 0.0, "kind": "leaked"}\n', encoding="utf-8")

    cfg = ConfigStore()
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    msg = {
        "type": "ipc.recordings.events",
        # Wire path-traversal — payload would fail the schema gate at the
        # bus boundary, but we test the handler's runtime guard here so the
        # defense-in-depth invariant is exercised even on a hostile direct
        # invocation.
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {"session_dir": "00000000-000000"},  # schema-shaped but not on disk
    }
    asyncio.run(loop._on_recordings_events(msg))
    # Not-on-disk + path-shape-valid → empty events list (well-defined success).
    results = fake_bus.emitted_by_type("ipc.recordings.events_result")
    assert len(results) == 1
    assert results[0]["payload"]["events"] == []

    # Now directly hit read_events with traversal — bypass schema; the handler
    # MUST emit ipc.error rather than returning empty events.
    fake_bus.emitted.clear()
    # We can't put a traversal string in `session_dir` and still satisfy the
    # schema for the outer envelope. Call the index directly via the handler's
    # protected path: build a manually-crafted dict (validate_message would
    # reject this at the bus boundary, but the handler must defend itself
    # when called directly from a test or a partial-validation path).
    msg_bad = {
        "type": "ipc.recordings.events",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {"session_dir": "../../etc/passwd"},
    }
    asyncio.run(loop._on_recordings_events(msg_bad))
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) >= 1
    assert any(
        "path_traversal_rejected" in (e["payload"].get("reason") or "")
        for e in errors
    )
    assert sibling.read_text(encoding="utf-8") == '{"t": 0.0, "kind": "leaked"}\n'


# ---------------------------------------------------------------------------
# Bonus — _on_recordings_list + _on_recordings_delete also covered
# (verifies the 3-handler registration + their bus-emit shapes)
# ---------------------------------------------------------------------------


def test_on_recordings_list_emits_list_result(
    tmp_recordings_dir: Path, fake_bus: FakeBus, make_fake_session
) -> None:
    make_fake_session(name="20260513-100000")
    make_fake_session(name="20260513-110000")
    cfg = ConfigStore()
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    msg = {
        "type": "ipc.recordings.list",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {},
    }
    asyncio.run(loop._on_recordings_list(msg))
    results = fake_bus.emitted_by_type("ipc.recordings.list_result")
    assert len(results) == 1
    payload = results[0]["payload"]
    assert len(payload["sessions"]) == 2
    # Newest first.
    assert payload["sessions"][0]["session_dir"] == "20260513-110000"


def test_on_recordings_delete_removes_dir_and_emits_usage(
    tmp_recordings_dir: Path, fake_bus: FakeBus, make_fake_session
) -> None:
    sd = make_fake_session(name="20260513-210410")
    assert sd.exists()
    cfg = ConfigStore()
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    msg = {
        "type": "ipc.recordings.delete",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {"session_dir": "20260513-210410"},
    }
    asyncio.run(loop._on_recordings_delete(msg))
    assert not sd.exists()
    acks = fake_bus.emitted_by_type("ipc.recordings.delete_ack")
    assert len(acks) == 1
    assert acks[0]["payload"]["ok"] is True
    # Usage is emitted after the delete so the drawer's disk line updates.
    usages = fake_bus.emitted_by_type("ipc.recordings.usage")
    assert len(usages) == 1


def test_handler_registration_includes_three_recordings_types(
    tmp_recordings_dir: Path, fake_bus: FakeBus
) -> None:
    cfg = ConfigStore()
    loop = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )
    loop.register_handlers()
    assert "ipc.recordings.list" in fake_bus.handlers
    assert "ipc.recordings.delete" in fake_bus.handlers
    assert "ipc.recordings.events" in fake_bus.handlers
