# SPDX-License-Identifier: Apache-2.0
"""Beat-trusted track-position interpolation between slow now-playing polls."""

from __future__ import annotations

from dataclasses import dataclass

BEAT_TRUST_CONFIDENCE_FLOOR = 0.6
MAX_DEAD_RECKON_AGE_S = 2.5


@dataclass(frozen=True)
class VirtualTrackPosition:
    position_sec: float | None
    confidence: float
    source: str


def virtual_position_sec(
    *,
    position_sec: float | None,
    position_sampled_at: float | None,
    now: float,
    duration_sec: float | None,
    playback_rate: float | None,
    bpm: float,
    bpm_confidence: float,
    track_confidence: float,
    max_age_s: float = MAX_DEAD_RECKON_AGE_S,
) -> VirtualTrackPosition:
    """Return a safe current-position estimate in seconds.

    The OS now-playing clock reports seconds at roughly 1 Hz. When the current
    BPM lock is trustworthy, advance that raw seconds position across the short
    gap until the next OS poll. BPM is used as the honesty gate, not as a unit
    conversion: seconds still advance by elapsed wall time times playback_rate.
    """
    raw = _bounded_position(position_sec, duration_sec)
    if raw is None:
        return VirtualTrackPosition(None, 0.0, "missing")

    raw_confidence = _bounded_confidence(track_confidence)
    if (
        position_sampled_at is None
        or now <= position_sampled_at
        or bpm <= 0.0
        or bpm_confidence < BEAT_TRUST_CONFIDENCE_FLOOR
    ):
        return VirtualTrackPosition(raw, raw_confidence, "raw")

    age_s = now - position_sampled_at
    if age_s > max_age_s:
        return VirtualTrackPosition(raw, raw_confidence, "stale_raw")

    rate = 1.0 if playback_rate is None else max(0.0, float(playback_rate))
    virtual = _bounded_position(raw + age_s * rate, duration_sec)
    return VirtualTrackPosition(
        virtual,
        min(raw_confidence, _bounded_confidence(bpm_confidence)),
        "dead_reckoned",
    )


def _bounded_position(value: float | None, duration_sec: float | None) -> float | None:
    if value is None:
        return None
    out = max(0.0, float(value))
    if duration_sec is not None and duration_sec > 0:
        out = min(out, float(duration_sec))
    return out


def _bounded_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
