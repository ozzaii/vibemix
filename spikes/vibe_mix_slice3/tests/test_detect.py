# SPDX-License-Identifier: Apache-2.0
"""Detection on a synthetic track with a KNOWN structure (no ffmpeg needed)."""
import numpy as np

from spikes.vibe_mix_slice0.confidence_gate import gate_cues
from spikes.vibe_mix_slice3.detect import (
    SR,
    detect_from_samples,
    estimate_tempo,
    onset_envelope,
)

_BPM = 120.0


def _synth(duration_s=60.0, bpm=_BPM, sr=SR):
    """4-on-the-floor kicks at a fixed BPM with full -> breakdown -> drop energy.

    0..30s full, 30..40s breakdown (quiet), 40..end drop (full re-entry).
    """
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    x = np.zeros(n, dtype=np.float32)
    period = 60.0 / bpm
    kick_len = int(0.08 * sr)
    env = np.exp(-np.linspace(0, 8, kick_len))
    tone = np.sin(2 * np.pi * 60 * np.arange(kick_len) / sr) * env
    for k in range(int(duration_s / period)):
        i = int(k * period * sr)
        if i + kick_len < n:
            x[i : i + kick_len] += tone.astype(np.float32)
    # Section gains: breakdown 30-40s quiet, else full.
    gain = np.ones(n, dtype=np.float32)
    gain[(t >= 30) & (t < 40)] = 0.12
    return x * gain


def test_estimate_tempo_recovers_120_bpm():
    x = _synth()
    bpm = estimate_tempo(onset_envelope(x))
    assert abs(bpm - _BPM) < 5.0


def test_detects_intro_breakdown_drop_at_known_positions():
    cues = {c.name: c for c in detect_from_samples(_synth(), SR, "file:///x.wav")}
    assert set(cues) == {"INTRO", "BREAKDOWN", "DROP"}
    assert cues["INTRO"].start_s < 1.0
    assert 28.0 <= cues["BREAKDOWN"].start_s <= 42.0      # the quiet section
    assert 38.0 <= cues["DROP"].start_s <= 44.0           # re-entry at ~40s
    assert cues["DROP"].number == 3                        # hot-cue slot


def test_strong_drop_passes_the_confidence_gate():
    cues = detect_from_samples(_synth(), SR, "file:///x.wav")
    kept = {c.name for c in gate_cues(cues)}              # default 0.85
    assert "DROP" in kept
    assert "BREAKDOWN" in kept                             # deep dip -> confident


def test_flat_track_yields_no_confident_breakdown_or_drop():
    # A constant-energy loop has no structure: anti-slop => don't invent cues.
    sr = SR
    t = np.arange(int(20 * sr)) / sr
    flat = (0.2 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
    kept = {c.name for c in gate_cues(detect_from_samples(flat, sr, "f"))}
    assert "DROP" not in kept and "BREAKDOWN" not in kept


def test_deterministic():
    x = _synth()
    a = [(c.name, round(c.start_s, 3)) for c in detect_from_samples(x, SR, "f")]
    b = [(c.name, round(c.start_s, 3)) for c in detect_from_samples(x, SR, "f")]
    assert a == b
