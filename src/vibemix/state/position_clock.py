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
    beat_fraction: float | None = None
    seconds_to_nearest_beat: float | None = None


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
        beat_fraction, beat_offset = _beat_timing(
            raw,
            bpm=bpm,
            bpm_confidence=bpm_confidence,
        )
        return VirtualTrackPosition(raw, raw_confidence, "raw", beat_fraction, beat_offset)

    age_s = now - position_sampled_at
    if age_s > max_age_s:
        return VirtualTrackPosition(raw, raw_confidence, "stale_raw")

    rate = 1.0 if playback_rate is None else max(0.0, float(playback_rate))
    virtual = _bounded_position(raw + age_s * rate, duration_sec)
    beat_fraction, beat_offset = _beat_timing(
        virtual,
        bpm=bpm,
        bpm_confidence=bpm_confidence,
    )
    return VirtualTrackPosition(
        virtual,
        min(raw_confidence, _bounded_confidence(bpm_confidence)),
        "dead_reckoned",
        beat_fraction,
        beat_offset,
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


def _beat_timing(
    position_sec: float | None,
    *,
    bpm: float,
    bpm_confidence: float,
) -> tuple[float | None, float | None]:
    """Return beat-distance metadata for the current virtual playhead.

    ``beat_fraction`` is the fraction through the current beat, not a bar. The
    paired offset is distance to the nearest beat boundary in seconds, so live
    proof can judge whether a predicted DROP was actually beat-aligned without
    pretending the slow OS now-playing poll is a high-rate clock.
    """
    if position_sec is None or bpm <= 0.0 or bpm_confidence < BEAT_TRUST_CONFIDENCE_FLOOR:
        return None, None
    beat_len_s = 60.0 / float(bpm)
    if beat_len_s <= 0.0:
        return None, None
    fraction = (float(position_sec) / beat_len_s) % 1.0
    nearest = min(fraction, 1.0 - fraction) * beat_len_s
    return fraction, nearest
