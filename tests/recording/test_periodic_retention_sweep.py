# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 02 — periodic 6h retention sweep + events.jsonl logging.

Two task surfaces under test (Task 2 cases land alongside the periodic-loop
implementation in the same plan):

  Task 1 — `run_retention_sweep` extended to return ``RetentionSweepResult``
            (named tuple of ``deleted_names`` + ``bytes_pruned``). Bytes are
            summed BEFORE rmtree so the count reflects what was actually
            deleted, not what was attempted (Pitfall 4 partial-failure
            accounting).

  Task 2 — `SessionLoop` spawns a periodic asyncio task on ``run()`` that
            fires `run_retention_sweep` every ``RETENTION_SWEEP_INTERVAL_S``
            seconds (6h in production, mockable for tests). Per-tick
            cancellation via the `_stop` event must be sub-second. When
            ``count > 0`` AND a live ``VoiceRecorder`` is registered, write
            one events.jsonl line ``{kind: "retention_pruned", count, bytes,
            t}`` per pruned sweep.

Schema reconciliation note (15-CONTEXT.md vs recorder.py:294):
  CONTEXT.md says ``{"event": "retention_pruned", "count": N, "bytes": M,
  "t_session": ...}``. The runtime contract uses ``{"t", "kind",
  **fields}`` (recorder.py:304). We honor the EXISTING schema — the events
  list will contain ``{"t": ..., "kind": "retention_pruned", "count": N,
  "bytes": M}``. The CONTEXT.md wording was approximate; recorder.py wins.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.recordings_index import (
    RetentionSweepResult,
    run_retention_sweep,
)
from vibemix.runtime.session_loop import (
    RETENTION_SWEEP_INTERVAL_S,
    SessionLoop,
)
from vibemix.ui_bus.validator import validate_message


# ===========================================================================
# Task 1 — run_retention_sweep returns (names, bytes_pruned)
# ===========================================================================


def _plant_session_with_files(
    root: Path,
    name: str,
    *,
    voice_bytes: int = 1024,
    input_bytes: int = 2048,
    events_bytes: int = 512,
) -> Path:
    """Create root/<name>/{voice.wav,input.wav,events.jsonl} with controllable sizes."""
    session_dir = root / name
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "voice.wav").write_bytes(b"\0" * voice_bytes)
    (session_dir / "input.wav").write_bytes(b"\0" * input_bytes)
    (session_dir / "events.jsonl").write_bytes(b"\0" * events_bytes)
    return session_dir


def test_run_retention_sweep_returns_bytes_pruned(tmp_path: Path) -> None:
    """Test 1A — bytes_pruned is the sum of file sizes BEFORE rmtree."""
    root = tmp_path / "recordings"
    root.mkdir()
    # Plant one prunable session: voice.wav=1024 + input.wav=2048 + events.jsonl=512 = 3584.
    _plant_session_with_files(
        root,
        "20260101-120000",
        voice_bytes=1024,
        input_bytes=2048,
        events_bytes=512,
    )
    result = run_retention_sweep(
        root,
        retention_days=7,
        now=datetime(2026, 5, 14, 12, 0, 0),
    )
    assert isinstance(result, RetentionSweepResult)
    assert result.deleted_names == ["20260101-120000"]
    assert result.bytes_pruned == 3584


def test_run_retention_sweep_back_compat_iterable_unpack(tmp_path: Path) -> None:
    """Test 1B — RetentionSweepResult is tuple-iterable + truthy on prunes.

    Existing call sites in __main__.py + settings.py + session_loop.py were
    updated to use ``.deleted_names`` (Option A: minimal-diff caller refactor).
    The named-tuple shape preserves tuple-iterability so any test or
    third-party caller doing ``names, bytes_pruned = run_retention_sweep(...)``
    still works.
    """
    root = tmp_path / "recordings"
    root.mkdir()
    _plant_session_with_files(root, "20260101-120000")

    result = run_retention_sweep(
        root,
        retention_days=7,
        now=datetime(2026, 5, 14, 12, 0, 0),
    )
    # Tuple unpack still works.
    names, bytes_pruned = result
    assert names == ["20260101-120000"]
    assert bytes_pruned > 0
    # Field-style access works (the canonical post-Plan-15-02 idiom).
    assert result.deleted_names == names
    assert result.bytes_pruned == bytes_pruned
    # Truthy on prune via the field accessor — the canonical replacement
    # for the old `if pruned:` idiom is `if result.deleted_names:`.
    assert bool(result.deleted_names)


def test_infinite_sentinel_short_circuit_with_bytes(tmp_path: Path) -> None:
    """Test 1C — ∞ sentinel returns RetentionSweepResult([], 0)."""
    root = tmp_path / "recordings"
    root.mkdir()
    _plant_session_with_files(root, "20200101-000000")

    result = run_retention_sweep(root, retention_days=36500)
    assert isinstance(result, RetentionSweepResult)
    assert result.deleted_names == []
    assert result.bytes_pruned == 0


def test_partial_failure_sums_bytes_for_successful_deletes_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 1D — partial rmtree failure: bytes_pruned counts only successful deletes."""
    root = tmp_path / "recordings"
    root.mkdir()
    # Two prunable dirs of known size.
    _plant_session_with_files(
        root, "20260101-120000", voice_bytes=100, input_bytes=200, events_bytes=50
    )  # 350 bytes — will FAIL rmtree
    _plant_session_with_files(
        root, "20260102-120000", voice_bytes=400, input_bytes=600, events_bytes=100
    )  # 1100 bytes — will succeed

    real_rmtree = shutil.rmtree

    def patched_rmtree(path, *args, **kwargs):
        # Fail the FIRST call (alphabetically earlier dir = 20260101).
        if str(path).endswith("20260101-120000"):
            raise OSError("simulated lock on first dir")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(
        "vibemix.runtime.recordings_index.shutil.rmtree", patched_rmtree
    )
    result = run_retention_sweep(
        root,
        retention_days=7,
        now=datetime(2026, 5, 14, 12, 0, 0),
    )
    # Only the successful one is in deleted_names + counted in bytes_pruned.
    assert result.deleted_names == ["20260102-120000"]
    assert result.bytes_pruned == 1100  # NOT 1450 (would include the failed dir)


# ===========================================================================
# Task 2 — periodic 6h sweep loop in SessionLoop
# ===========================================================================


class FakeBus:
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


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture(autouse=True)
def _redirect_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    return target


def test_constant_is_six_hours() -> None:
    """RETENTION_SWEEP_INTERVAL_S = 6h = 21600s, per CONTEXT.md §Retention Enforcement."""
    assert RETENTION_SWEEP_INTERVAL_S == 6 * 60 * 60
    assert RETENTION_SWEEP_INTERVAL_S == 21600


def test_periodic_sweep_fires_at_interval(
    tmp_recordings_dir: Path, fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 2A — at a 50ms interval, ≥3 sweeps fire in 200ms (boot + 2+ ticks).

    Verifies the periodic loop is actually spawned by ``SessionLoop.run()``
    AND fires at the configured cadence. Boot sweep (1 call) + ≥2 periodic
    ticks at 50ms over 200ms = ≥3 total calls.
    """
    # Patch the interval to 50ms — tests must run fast.
    monkeypatch.setattr(
        "vibemix.runtime.session_loop.RETENTION_SWEEP_INTERVAL_S", 0.05
    )
    sweep_mock = MagicMock(return_value=RetentionSweepResult([], 0))
    monkeypatch.setattr(
        "vibemix.runtime.session_loop.run_retention_sweep", sweep_mock
    )

    cfg = ConfigStore(retention_days=7)
    loop_obj = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )

    async def _drive() -> None:
        run_task = asyncio.create_task(loop_obj.run())
        try:
            await asyncio.sleep(0.20)
        finally:
            loop_obj.request_stop()
            try:
                await asyncio.wait_for(run_task, timeout=1.0)
            except asyncio.TimeoutError:
                run_task.cancel()
                try:
                    await run_task
                except (asyncio.CancelledError, Exception):
                    pass

    asyncio.run(_drive())

    # Boot sweep + ≥2 periodic ticks. We use ≥3 to keep the test resilient
    # to scheduler jitter on a heavily loaded CI box (could be 4 or 5).
    assert sweep_mock.call_count >= 3, (
        f"expected ≥3 sweep calls (boot + ≥2 periodic ticks at 50ms over 200ms), "
        f"got {sweep_mock.call_count}"
    )


def test_periodic_sweep_respects_stop_event(
    tmp_recordings_dir: Path, fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 2B — request_stop completes the loop in <0.5s even with a 10s interval.

    Proves the loop awaits on _stop.wait() races (NOT a bare asyncio.sleep)
    so SIGTERM/SIGINT shutdown does not hang the sidecar for up to 6h
    (T-15-02-01 disposition).
    """
    monkeypatch.setattr(
        "vibemix.runtime.session_loop.RETENTION_SWEEP_INTERVAL_S", 10.0
    )
    sweep_mock = MagicMock(return_value=RetentionSweepResult([], 0))
    monkeypatch.setattr(
        "vibemix.runtime.session_loop.run_retention_sweep", sweep_mock
    )

    cfg = ConfigStore(retention_days=7)
    loop_obj = SessionLoop(
        fake_bus, config_store=cfg, recordings_root=tmp_recordings_dir
    )

    elapsed_holder: dict[str, float] = {}

    async def _drive() -> None:
        run_task = asyncio.create_task(loop_obj.run())
        await asyncio.sleep(0.05)  # let boot sweep + the periodic loop spawn
        t0 = time.monotonic()
        loop_obj.request_stop()
        try:
            await asyncio.wait_for(run_task, timeout=2.0)
        except asyncio.TimeoutError:
            run_task.cancel()
            try:
                await run_task
            except (asyncio.CancelledError, Exception):
                pass
            elapsed_holder["t"] = float("inf")
            return
        elapsed_holder["t"] = time.monotonic() - t0

    asyncio.run(_drive())
    assert elapsed_holder["t"] < 0.5, (
        f"request_stop must complete within 0.5s; took {elapsed_holder['t']:.3f}s. "
        "If this fails, the periodic loop is using a bare asyncio.sleep instead "
        "of an asyncio.wait race against _stop."
    )


def test_periodic_sweep_logs_events_jsonl_when_recorder_active(
    tmp_recordings_dir: Path, fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 2C — when active_recorder is present + count>0, an events.jsonl line is written.

    Schema: ``{"t": <float>, "kind": "retention_pruned", "count": N, "bytes": M}``
    via VoiceRecorder.log_event (NOT CONTEXT.md's approximate
    ``{"event", ..., "t_session"}`` wording).
    """
    # Build a real VoiceRecorder so its events.jsonl is on disk for inspection.
    from vibemix.audio.recorder import VoiceRecorder

    recorder = VoiceRecorder(root=tmp_recordings_dir)
    try:
        # Patch sweep to return a non-empty result.
        sweep_mock = MagicMock(
            return_value=RetentionSweepResult(["20260101-120000"], 4096)
        )
        monkeypatch.setattr(
            "vibemix.runtime.session_loop.run_retention_sweep", sweep_mock
        )

        cfg = ConfigStore(retention_days=7)
        loop_obj = SessionLoop(
            fake_bus,
            config_store=cfg,
            recordings_root=tmp_recordings_dir,
            active_recorder=recorder,
        )

        # Drive ONE periodic tick directly via the shared helper.
        asyncio.run(loop_obj._fire_one_retention_sweep("periodic"))

        # Inspect events.jsonl tail line.
        events_path = recorder.events_path
        lines = events_path.read_text(encoding="utf-8").splitlines()
        # Skip blank lines.
        non_empty = [ln for ln in lines if ln.strip()]
        assert non_empty, "events.jsonl must have at least one line (session_start)"
        # The retention_pruned line is the last one written.
        last = json.loads(non_empty[-1])
        assert last["kind"] == "retention_pruned"
        assert last["count"] == 1
        assert last["bytes"] == 4096
        assert isinstance(last["t"], (int, float))
    finally:
        recorder.close()


def test_periodic_sweep_no_events_log_when_no_active_recorder(
    tmp_recordings_dir: Path, fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 2D — active_recorder=None: sweep fires + logs to logger only, no jsonl write."""
    sweep_mock = MagicMock(
        return_value=RetentionSweepResult(["20260101-120000"], 4096)
    )
    monkeypatch.setattr(
        "vibemix.runtime.session_loop.run_retention_sweep", sweep_mock
    )

    cfg = ConfigStore(retention_days=7)
    loop_obj = SessionLoop(
        fake_bus,
        config_store=cfg,
        recordings_root=tmp_recordings_dir,
        active_recorder=None,  # explicit
    )

    # Must not raise.
    asyncio.run(loop_obj._fire_one_retention_sweep("periodic"))

    # No session dirs were created by anything other than the (mocked) sweep.
    # Confirm no events.jsonl exists anywhere under recordings_root.
    jsonl_files = list(tmp_recordings_dir.rglob("events.jsonl"))
    assert jsonl_files == [], (
        f"no events.jsonl should be written when no active_recorder; found {jsonl_files!r}"
    )


def test_periodic_sweep_skips_jsonl_log_on_zero_pruned(
    tmp_recordings_dir: Path, fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 2E — count=0 ticks skip the events.jsonl write to keep noise down.

    6h cadence × ~99% no-op rate = up to 24 zero-prune ticks per day. Logging
    each one would flood events.jsonl with noise. We log only when count > 0
    (T-15-02-04 disposition).
    """
    from vibemix.audio.recorder import VoiceRecorder

    recorder = VoiceRecorder(root=tmp_recordings_dir)
    try:
        sweep_mock = MagicMock(return_value=RetentionSweepResult([], 0))
        monkeypatch.setattr(
            "vibemix.runtime.session_loop.run_retention_sweep", sweep_mock
        )

        cfg = ConfigStore(retention_days=7)
        loop_obj = SessionLoop(
            fake_bus,
            config_store=cfg,
            recordings_root=tmp_recordings_dir,
            active_recorder=recorder,
        )
        asyncio.run(loop_obj._fire_one_retention_sweep("periodic"))

        events_path = recorder.events_path
        lines = [
            ln
            for ln in events_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        # session_start is line 0; no retention_pruned line should follow.
        kinds = [json.loads(ln).get("kind") for ln in lines]
        assert "retention_pruned" not in kinds, (
            f"zero-prune ticks must NOT write retention_pruned; events kinds: {kinds!r}"
        )
    finally:
        recorder.close()


def test_periodic_sweep_short_circuits_when_recordings_root_none(
    fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stand-alone --session mode without recordings_root: periodic loop must no-op."""
    sweep_mock = MagicMock(return_value=RetentionSweepResult([], 0))
    monkeypatch.setattr(
        "vibemix.runtime.session_loop.run_retention_sweep", sweep_mock
    )

    cfg = ConfigStore(retention_days=7)
    # recordings_root NOT provided.
    loop_obj = SessionLoop(fake_bus, config_store=cfg, recordings_root=None)

    # Direct invocation must early-return (no exception, no sweep).
    asyncio.run(loop_obj._fire_one_retention_sweep("periodic"))
    sweep_mock.assert_not_called()
