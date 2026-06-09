# SPDX-License-Identifier: Apache-2.0
"""Env-overridable BPM confidence floor (replay/QA measurement knob).

`estimate_bpm` floors its output to 0.0 below a confidence bar. Since the
2026-06-09 calibration the default bar is lane-split (see the calibration
note in `audio/features.py`): strict 0.70 for synthetic-strength periodicity
(keeps the merged-two-tempo suppress), calibrated 0.06 for real-world music
(the flat 0.70 had zeroed `state.bpm` on every real session since
2026-06-05; history in `.planning/eval-runs/REPLAY-MEASUREMENT-WALL-2026-06-09.md`).

`VIBEMIX_BPM_CONFIDENCE_FLOOR`, when set, replaces the floor for BOTH lanes —
an explicit replay/QA knob beats the lane split. The packaged product never
sets it.
"""

from __future__ import annotations

import numpy as np

from vibemix.audio.buffers import AudioBuffer
from vibemix.audio.features import (
    _BPM_CONFIDENCE_FLOOR,
    _resolve_bpm_confidence_floor,
    estimate_bpm,
    estimate_bpm_with_confidence,
)


def _click_train_buffer(*, bpm: float = 120.0, seconds: float = 8.0, sr: int = 16000) -> AudioBuffer:
    """A clean periodic click train — high-confidence, unambiguous tempo."""
    n = int(sr * seconds)
    sig = np.zeros(n, dtype=np.float32)
    period = int(sr * 60.0 / bpm)
    # a short decaying burst at each beat so the RMS envelope has clear peaks
    burst = (np.hanning(int(sr * 0.04)) * 0.9).astype(np.float32)
    for start in range(0, n - burst.size, period):
        sig[start : start + burst.size] += burst
    pcm = np.clip(sig * 32767.0, -32768, 32767).astype(np.int16)
    buf = AudioBuffer(seconds=seconds + 4, sr=sr)
    buf.push(pcm)
    return buf


def test_resolve_floor_defaults_to_constant(monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", raising=False)
    assert _resolve_bpm_confidence_floor() == _BPM_CONFIDENCE_FLOOR


def test_resolve_floor_reads_env_override(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", "0.05")
    assert _resolve_bpm_confidence_floor() == 0.05


def test_resolve_floor_ignores_garbage_env(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", "not-a-number")
    assert _resolve_bpm_confidence_floor() == _BPM_CONFIDENCE_FLOOR


def test_estimate_bpm_honors_relaxed_floor(monkeypatch) -> None:
    buf = _click_train_buffer()
    bpm_raw, conf = estimate_bpm_with_confidence(buf, seconds=6.0)
    assert bpm_raw > 0  # the estimator found *a* tempo on the click train

    # Floor strictly above the measured confidence → wrapper suppresses to 0.
    monkeypatch.setenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", f"{conf + 0.01:.6f}")
    assert estimate_bpm(buf, seconds=6.0) == 0.0

    # Floor at the bottom → the wrapper passes the estimate through.
    monkeypatch.setenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", "0.0")
    assert estimate_bpm(buf, seconds=6.0) > 0.0


def test_estimate_bpm_default_floor_unchanged(monkeypatch) -> None:
    # No env → behaves exactly as before (0.70 floor); a low-confidence buffer
    # still floors to 0. Guards against the override leaking into the product.
    monkeypatch.delenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", raising=False)
    buf = AudioBuffer(seconds=12, sr=16000)
    buf.push(np.zeros(int(16000 * 8), dtype=np.int16))  # silence → conf 0
    assert estimate_bpm(buf, seconds=6.0) == 0.0
