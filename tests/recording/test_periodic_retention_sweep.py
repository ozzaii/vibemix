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

import shutil
from datetime import datetime
from pathlib import Path

import pytest

from vibemix.runtime.recordings_index import (
    RetentionSweepResult,
    run_retention_sweep,
)


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
