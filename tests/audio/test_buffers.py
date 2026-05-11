# SPDX-License-Identifier: Apache-2.0
"""Ring-buffer test suite — wrap correctness, zero-alloc regression,
ndarray identity stability, cold-start, PassthroughBuffer drop-half,
PlaybackQueue ↔ Levels integration, BufferRegistry shape.

Pins the fix for the np.concatenate-per-callback regression at
cohost_v4.py:300 (AudioBuffer.push) + v4:462 (MicBuffer.push) — PITFALLS.md P5.
"""

from __future__ import annotations

import time
import tracemalloc

import numpy as np
import pytest
from pytest_mock import MockerFixture

from vibemix.audio import (
    AudioBuffer,
    BufferRegistry,
    Levels,
    MicBuffer,
    PassthroughBuffer,
    PlaybackQueue,
)

# ===== RING-01: AudioBuffer wrap correctness =====


def test_audio_buffer_wrap_preserves_recent() -> None:
    """Pushing more than `size` total samples then snapshotting `size` returns
    the most recent `size` samples in correct chronological order across wrap.
    Pins the modular-wrap implementation in buffers.py."""
    buf = AudioBuffer(seconds=0.1, sr=16000)  # 1600 samples
    data = (np.arange(4000) % 32767).astype(np.int16)
    buf.push(data[:1000])
    buf.push(data[1000:2500])
    buf.push(data[2500:4000])
    snap = buf.snapshot(1600)
    assert snap.size == 1600
    np.testing.assert_array_equal(snap, data[-1600:])


# ===== RING-02: AudioBuffer zero-alloc (tracemalloc) =====


def test_audio_buffer_push_zero_alloc_tracemalloc() -> None:
    """100 callback-sized pushes after warm-up allocate < 1KB in buffers.py.

    THE regression test for np.concatenate-per-callback at cohost_v4.py:300.
    Anything more than ~1KB means np.concatenate (or equivalent) crept back in.
    """
    buf = AudioBuffer(seconds=140.0, sr=16000)
    frame = np.zeros(480, dtype=np.int16)

    # Warm up so first-wrap allocations don't pollute the snapshot.
    for _ in range(5):
        buf.push(frame)

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    for _ in range(100):
        buf.push(frame)
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "filename")
    buffer_module_diff = sum(
        stat.size_diff for stat in stats if "buffers.py" in stat.traceback[0].filename
    )
    assert buffer_module_diff < 1024, (
        f"AudioBuffer.push allocated {buffer_module_diff} bytes in buffers.py "
        f"over 100 calls — expected ~0. Did np.concatenate creep back in?"
    )


# ===== RING-03: AudioBuffer underlying array identity =====


def test_audio_buffer_underlying_array_identity_stable() -> None:
    """id(buf._buf) is stable across 1000 pushes. Cheap canary that catches
    np.concatenate-style replacement without tracemalloc."""
    buf = AudioBuffer(seconds=140.0, sr=16000)
    initial_id = id(buf._buf)
    frame = np.zeros(480, dtype=np.int16)
    for _ in range(1000):
        buf.push(frame)
    assert id(buf._buf) == initial_id


# ===== RING-04: cold-start correctness =====


def test_audio_buffer_cold_start_returns_only_real_samples() -> None:
    """Snapshot when `_filled` < `n_samples` returns only the real samples,
    NOT the zero-init prefix of the pre-allocated buffer."""
    buf = AudioBuffer(seconds=0.1, sr=16000)  # 1600 capacity
    real = np.full(100, 12345, dtype=np.int16)
    buf.push(real)
    snap = buf.snapshot(1600)
    assert snap.size == 100, f"cold-start leaked zero-init: got size {snap.size}"
    np.testing.assert_array_equal(snap, real)


def test_audio_buffer_snapshot_reusable_out_param() -> None:
    """`out=` lets Phase 3 state_refresh_loop reuse a pre-allocated read buffer."""
    buf = AudioBuffer(seconds=0.1, sr=16000)
    buf.push(np.full(1600, 7, dtype=np.int16))
    out = np.empty(1600, dtype=np.int16)
    result = buf.snapshot(1600, out=out)
    assert result is out
    assert (out == 7).all()


# ===== RING-05: MicBuffer pull consumes read pointer =====


def test_mic_buffer_wrap_pull_consumes_read_pointer() -> None:
    """MicBuffer.pull advances the read pointer; consecutive pulls return
    consecutive halves (FIFO semantics, not snapshot of tail)."""
    lv = Levels()
    mic = MicBuffer(gain=1.0, levels=lv)
    samples = np.arange(200, dtype=np.float32) / 200.0
    mic.push(samples)
    first = mic.pull(100)
    second = mic.pull(100)
    # First should be samples[0:100], second samples[100:200]
    np.testing.assert_allclose(first, samples[:100], atol=1e-6)
    np.testing.assert_allclose(second, samples[100:], atol=1e-6)


# ===== RING-06: MicBuffer current_gain zero when AI talking =====


def test_mic_buffer_current_gain_zero_when_ai_talking() -> None:
    """levels.voice > AI_TALK_THRESHOLD → mic gain goes to 0.0 immediately.

    The LOAD-BEARING feedback-suppression IP. v4:449-457.
    """
    lv = Levels()
    mic = MicBuffer(gain=1.0, levels=lv)
    lv.voice = 0.5  # above AI_TALK_THRESHOLD=0.02
    mic.push(np.full(480, 1.0, dtype=np.float32))
    # Gain was zeroed before levels.update_mic was called
    assert lv.mic == 0.0


# ===== RING-07: MicBuffer hold-after-AI 350ms =====


def test_mic_buffer_hold_after_ai_350ms(mocker: MockerFixture) -> None:
    """Within MIC_HOLD_AFTER_AI_MS of last AI-active, gain stays 0 even after
    levels.voice falls below threshold. v4:451-459.
    """
    lv = Levels()
    mic = MicBuffer(gain=1.0, levels=lv)
    t0 = 1000.0
    fake_time = mocker.patch("vibemix.audio.buffers.time.time")
    # Flip AI-active state
    fake_time.return_value = t0
    lv.voice = 0.5
    assert mic._current_gain() == 0.0
    # Drop voice level but stay within hold window
    lv.voice = 0.0
    fake_time.return_value = t0 + 0.2  # 200ms < 350ms
    assert mic._current_gain() == 0.0
    # Past hold window
    fake_time.return_value = t0 + 0.5  # 500ms > 350ms
    assert mic._current_gain() == 1.0


# ===== RING-08: PassthroughBuffer drop-half on overflow =====


def test_passthrough_buffer_drop_half_on_overflow() -> None:
    """Overflow drops back to ~50% capacity. Verbatim v4:487-492."""
    pt = PassthroughBuffer()
    pt.push(b"\x00" * (PassthroughBuffer.MAX_BYTES + 1000))
    # Drop logic: drop = len - MAX//2 → remaining ~= MAX//2 + 1000
    remaining = len(pt._buf)
    assert PassthroughBuffer.MAX_BYTES // 2 <= remaining <= PassthroughBuffer.MAX_BYTES // 2 + 1500


# ===== RING-09: PassthroughBuffer pull zero-pads on underflow =====


def test_passthrough_buffer_pull_zero_pads_on_underflow() -> None:
    """Pull more than available → returns the available bytes followed by
    zero-pad. PATTERNS.md §7 — diverges from v4's b\"\" return.
    """
    pt = PassthroughBuffer()
    pt.push(b"\xff" * 100)
    out = pt.pull(200)
    assert len(out) == 200
    assert out[:100] == b"\xff" * 100
    assert out[100:] == b"\x00" * 100


# ===== RING-10: PlaybackQueue.push triggers levels.update_voice =====


def test_playback_queue_push_triggers_levels_update_voice() -> None:
    """Pushing AI audio updates levels.voice within the call. v4:511-512."""
    lv = Levels()
    pq = PlaybackQueue(lv)
    pcm = np.full(2048, 16384, dtype=np.int16).tobytes()
    pq.push(pcm)
    assert lv.voice > 0.1


# ===== RING-11: PlaybackQueue empty pull triggers decay_voice =====


def test_playback_queue_empty_pull_triggers_decay_voice() -> None:
    """Empty pull → levels.voice multiplied by 0.7. v4:517-520."""
    lv = Levels()
    pq = PlaybackQueue(lv)
    lv.voice = 1.0
    pq.pull(1024)  # buffer is empty
    assert abs(lv.voice - 0.7) < 1e-9


# ===== RING-12: BufferRegistry holds all six fields =====


def test_buffer_registry_holds_all_six_fields() -> None:
    """BufferRegistry aggregates two AudioBuffers + MicBuffer + PassthroughBuffer
    + PlaybackQueue + Levels; the Levels reference matches everywhere."""
    lv = Levels()
    pq = PlaybackQueue(lv)
    mic = MicBuffer(gain=1.0, levels=lv)
    reg = BufferRegistry(
        audio=AudioBuffer(seconds=1.0),
        clean_audio=AudioBuffer(seconds=1.0),
        mic=mic,
        passthrough=PassthroughBuffer(),
        playback=pq,
        levels=lv,
    )
    assert reg.levels is lv
    assert reg.mic._levels is lv
    assert reg.playback._levels is lv


# ===== Bonus: MicBuffer.push zero-alloc (mirrors RING-02 for the second bug) =====


def test_mic_buffer_push_zero_alloc_tracemalloc() -> None:
    """100 mic pushes after warm-up allocate < 1KB in buffers.py.

    Pins the v4:462 bug fix (the second np.concatenate site). Without the
    pre-allocated ring this allocates ~38KB x 100 = 3.8MB.
    """
    lv = Levels()
    mic = MicBuffer(gain=1.0, levels=lv)
    frame = np.zeros(480, dtype=np.float32)

    for _ in range(5):
        mic.push(frame)

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    for _ in range(100):
        mic.push(frame)
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "filename")
    buffer_module_diff = sum(
        stat.size_diff for stat in stats if "buffers.py" in stat.traceback[0].filename
    )
    # Slightly more slack — MicBuffer.push does `samples * gain` (alloc per call by
    # numpy) before levels.update_mic; that alloc lives in levels.py, not buffers.py,
    # so it doesn't show up in this diff. Anything > 1KB in buffers.py means
    # the ring itself reallocated.
    assert buffer_module_diff < 1024, (
        f"MicBuffer.push allocated {buffer_module_diff} bytes in buffers.py "
        f"over 100 calls — expected ~0. Did np.concatenate creep back in?"
    )


def test_mic_buffer_underlying_array_identity_stable() -> None:
    """id(mic._buf) is stable across 1000 pushes — v4:462 fix canary."""
    lv = Levels()
    mic = MicBuffer(gain=1.0, levels=lv)
    initial_id = id(mic._buf)
    for _ in range(1000):
        mic.push(np.zeros(480, dtype=np.float32))
    assert id(mic._buf) == initial_id


# ===== Underflow + edge cases =====


def test_audio_buffer_push_empty_no_op() -> None:
    """Pushing an empty ndarray is a no-op (does not raise)."""
    buf = AudioBuffer(seconds=1.0, sr=16000)
    buf.push(np.zeros(0, dtype=np.int16))
    assert buf._filled == 0


def test_audio_buffer_push_oversized_keeps_tail() -> None:
    """Pushing more samples than the ring holds keeps the tail (defensive
    pathological-input branch)."""
    buf = AudioBuffer(seconds=0.1, sr=16000)  # 1600 capacity
    data = (np.arange(2000) % 32767).astype(np.int16)
    buf.push(data)
    snap = buf.snapshot(1600)
    np.testing.assert_array_equal(snap, data[-1600:])


def test_mic_buffer_pull_zero_pads_on_underflow() -> None:
    """Pulling more than available → zero-pad. PATTERNS.md §7."""
    lv = Levels()
    mic = MicBuffer(gain=1.0, levels=lv)
    mic.push(np.full(50, 0.5, dtype=np.float32))
    out = mic.pull(200)
    assert out.size == 200
    # First 50 samples should be 0.5; remainder zero
    assert (out[:50] == 0.5).all()
    assert (out[50:] == 0.0).all()


@pytest.mark.parametrize("seconds,sr", [(140.0, 16000), (23.0, 16000), (1.0, 48000)])
def test_audio_buffer_init_sizes(seconds: float, sr: int) -> None:
    """The pre-allocated ring is exactly seconds*sr samples and never resized."""
    buf = AudioBuffer(seconds=seconds, sr=sr)
    assert buf._buf.size == int(sr * seconds)
    assert buf._buf.dtype == np.int16
    # `time` import is implicit via buffers.py; make sure the test module also
    # has access in case of future refactors that read time on init.
    _ = time.time()
