# SPDX-License-Identifier: Apache-2.0
"""−60 dB silence cues — the first/last audible sample bounds (scar 20 §3.3).

Clean-room port of Mixxx ``AnalyzerSilence`` (GPLv2 — fact re-derived, no source
copied): the −60 dB threshold (``0.001``) marks the first and last audible sample
of a track. These bounds are what the transition clock's skip-silence modes use
instead of marked intro/outro cues, so the auto-mix reel runs on REAL decoded audio
(the common un-analyzed case) — :func:`track_cues_from_audio` packages them into
the :class:`~vibemix.state.transition_clock.TrackCues` the clock consumes.
"""
from __future__ import annotations

import numpy as np

from vibemix.state.transition_clock import TrackCues

SILENCE: float = 0.001  # 10**(-60/20), -60 dBFS — the audible/silent boundary


def _abs_mono(samples) -> np.ndarray:
    """|amplitude| collapsed to a 1-D envelope; a frame is audible if ANY channel is."""
    a = np.abs(np.asarray(samples, dtype=np.float64))
    return a.max(axis=1) if a.ndim == 2 else a


def first_sound_frame(samples) -> int:
    """Index of the first sample at or above −60 dB; ``0`` if the track is silent."""
    mask = _abs_mono(samples) >= SILENCE
    return int(np.argmax(mask)) if bool(mask.any()) else 0


def last_sound_frame(samples) -> int:
    """Index of the last sample at or above −60 dB; ``len`` if the track is silent."""
    mask = _abs_mono(samples)
    mask = mask >= SILENCE
    if not bool(mask.any()):
        return int(len(mask))  # all silent -> end sentinel (mirrors signalEnd=framesProcessed)
    return int(len(mask) - 1 - np.argmax(mask[::-1]))


def track_cues_from_audio(
    samples,
    sample_rate: int,
    *,
    intro_start_sec: float | None = None,
    intro_end_sec: float | None = None,
    outro_start_sec: float | None = None,
    outro_end_sec: float | None = None,
) -> TrackCues:
    """Build :class:`TrackCues` from decoded audio + any known marked cues.

    Computes the −60 dB first/last-sound bounds from the samples and the duration
    from their length; marked intro/outro cues (e.g. from Rekordbox metadata) are
    passed through when available, else left ``None`` (the clock's fallback ladder
    and skip-silence modes use the sound bounds). Audio-derived bounds never
    override a supplied marker — they only fill what analysis left blank.
    """
    env = _abs_mono(samples)
    n = int(len(env))
    if sample_rate <= 0:
        return TrackCues(duration_sec=0.0)
    duration = n / sample_rate
    first_sec = first_sound_frame(samples) / sample_rate
    last_sec = min(last_sound_frame(samples) / sample_rate, duration)
    return TrackCues(
        duration_sec=duration,
        intro_start_sec=intro_start_sec,
        intro_end_sec=intro_end_sec,
        outro_start_sec=outro_start_sec,
        outro_end_sec=outro_end_sec,
        first_sound_sec=first_sec,
        last_sound_sec=last_sec,
    )
