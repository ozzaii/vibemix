# SPDX-License-Identifier: Apache-2.0
"""Headless post-session timing near-miss detector.

The detector reads ``input.wav`` and ``events.jsonl`` from a recorded session,
then looks for one grounded "OUT -> IN" beat-phase recovery around a transition
window. It is deliberately conservative: no usable input audio, no transition
anchor, low BPM confidence, or no clean recovery all return ``None``.
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from vibemix.learn.beatmatch_judge import _phase_error
from vibemix.state.detectors._phrase_dsp import band_limited_autocorr

_BPM_MIN = 70.0
_BPM_MAX = 180.0
_MIN_CLIP_SECONDS = 10.0
_TRANSITION_PAD_BEFORE_S = 24.0
_TRANSITION_PAD_AFTER_S = 32.0
_OUT_ERROR_BEATS = 0.09
_IN_ERROR_BEATS = 0.035
_MAX_RECOVERY_BARS = 8.0
_MIN_OUT_POINTS = 2
_MIN_BPM_CONFIDENCE = 0.18
_DEFAULT_MIN_CONFIDENCE = 0.38


@dataclass(frozen=True, slots=True)
class PhasePoint:
    """One measured beat-grid residual, expressed in beats."""

    t_s: float
    error_beats: float
    strength: float = 1.0


@dataclass(frozen=True, slots=True)
class TransitionWindow:
    """A transition-shaped span from session events."""

    start_s: float
    end_s: float
    event_type: str
    event_t_s: float

    def overlaps(self, start_s: float, end_s: float) -> bool:
        return self.start_s <= end_s and start_s <= self.end_s


@dataclass(frozen=True, slots=True)
class NearMissResult:
    """One confident post-session timing recovery."""

    t_center_s: float
    window_start_s: float
    window_end_s: float
    depth_beats: float
    recovery_bars: float
    confidence: float
    bpm: float
    phase_error_beats_peak: float
    citation: str
    event_type: str
    event_t_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "t_center_s": round(self.t_center_s, 3),
            "window_start_s": round(self.window_start_s, 3),
            "window_end_s": round(self.window_end_s, 3),
            "depth_beats": round(self.depth_beats, 4),
            "recovery_bars": round(self.recovery_bars, 3),
            "confidence": round(self.confidence, 4),
            "bpm": round(self.bpm, 3),
            "phase_error_beats_peak": round(self.phase_error_beats_peak, 4),
            "citation": self.citation,
            "event_type": self.event_type,
            "event_t_s": round(self.event_t_s, 3),
            "language_subject": "the mix",
        }


def detect_near_miss(
    session_dir: Path | str,
    *,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
) -> NearMissResult | None:
    """Return one confident near miss for ``session_dir``, or ``None``.

    This is a debrief/learn primitive, not a live-runtime detector. It never
    starts the co-host and never calls an LLM.
    """
    session_path = Path(session_dir)
    events = _read_events_jsonl(session_path / "events.jsonl")
    if not events:
        return None
    audio = _read_wav_mono_float32(session_path / "input.wav")
    if audio is None:
        return None
    samples, sample_rate = audio
    return detect_near_miss_from_samples(
        samples,
        sample_rate,
        events,
        min_confidence=min_confidence,
    )


def detect_near_miss_from_samples(
    samples: np.ndarray,
    sample_rate: int,
    events: list[dict[str, Any]],
    *,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
) -> NearMissResult | None:
    """Detect a near miss from decoded mono samples and parsed events."""
    if sample_rate <= 0 or samples.size < int(_MIN_CLIP_SECONDS * max(sample_rate, 1)):
        return None

    duration_s = samples.size / float(sample_rate)
    windows = _transition_windows(events, duration_s)
    if not windows:
        return None

    best: NearMissResult | None = None
    for window in windows:
        clip_start_s = max(0.0, window.start_s)
        clip_end_s = min(duration_s, window.end_s)
        if clip_end_s - clip_start_s < _MIN_CLIP_SECONDS:
            continue
        start_i = int(clip_start_s * sample_rate)
        end_i = min(samples.size, int(clip_end_s * sample_rate))
        result = _detect_in_clip(
            samples[start_i:end_i],
            sample_rate,
            clip_offset_s=clip_start_s,
            transition_window=window,
            min_confidence=min_confidence,
        )
        if result is None:
            continue
        if best is None or result.confidence > best.confidence:
            best = result
    return best


def _detect_in_clip(
    clip: np.ndarray,
    sample_rate: int,
    *,
    clip_offset_s: float,
    transition_window: TransitionWindow,
    min_confidence: float,
) -> NearMissResult | None:
    bpm, bpm_confidence = _estimate_bpm(clip, sample_rate)
    if bpm is None or bpm_confidence < _MIN_BPM_CONFIDENCE:
        return None

    peaks = _onset_peaks(clip, sample_rate, bpm=bpm, offset_s=clip_offset_s)
    if len(peaks) < 12:
        return None
    points = _phase_points_from_peaks(peaks, bpm=bpm)
    if len(points) < 8:
        return None
    return _find_out_in_candidate(
        points,
        bpm=bpm,
        bpm_confidence=bpm_confidence,
        transition_window=transition_window,
        min_confidence=min_confidence,
    )


def _estimate_bpm(samples: np.ndarray, sample_rate: int) -> tuple[float | None, float]:
    ac = band_limited_autocorr(samples, sample_rate, max_lag_seconds=60.0 / _BPM_MIN)
    if ac.size == 0:
        return (None, 0.0)
    min_lag = max(1, int(sample_rate * 60.0 / _BPM_MAX))
    max_lag = min(ac.size - 1, int(sample_rate * 60.0 / _BPM_MIN))
    if max_lag <= min_lag:
        return (None, 0.0)
    region = ac[min_lag : max_lag + 1]
    if region.size == 0:
        return (None, 0.0)
    best_rel = int(np.argmax(region))
    best_lag = min_lag + best_rel
    peak = float(region[best_rel])
    if not math.isfinite(peak) or peak <= 0.0:
        return (None, 0.0)
    median = float(np.median(region))
    confidence = max(0.0, min(1.0, (peak - median) / 0.35))
    bpm = 60.0 * sample_rate / float(best_lag)
    if bpm < _BPM_MIN or bpm > _BPM_MAX:
        return (None, 0.0)
    return (float(bpm), confidence)


@dataclass(frozen=True, slots=True)
class _OnsetPeak:
    t_s: float
    strength: float


def _onset_peaks(
    samples: np.ndarray,
    sample_rate: int,
    *,
    bpm: float,
    offset_s: float,
) -> list[_OnsetPeak]:
    if samples.size == 0 or sample_rate <= 0 or bpm <= 0.0:
        return []
    frame = max(1, int(sample_rate * 0.01))
    n_frames = samples.size // frame
    if n_frames < 8:
        return []
    trimmed = samples[: n_frames * frame].reshape(n_frames, frame)
    energy = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    deltas = np.clip(np.diff(energy), a_min=0.0, a_max=None)
    if deltas.size < 3:
        return []
    smooth = np.convolve(deltas, np.array([0.25, 0.5, 0.25], dtype=np.float32), mode="same")
    max_strength = float(np.max(smooth))
    if max_strength <= 1e-7:
        return []
    median = float(np.median(smooth))
    mad = float(np.median(np.abs(smooth - median)))
    threshold = max(median + 3.0 * mad, max_strength * 0.12)
    beat_s = 60.0 / bpm
    min_gap_frames = max(1, int((beat_s * 0.42) / 0.01))

    raw: list[tuple[int, float]] = []
    for i in range(1, smooth.size - 1):
        value = float(smooth[i])
        if value < threshold:
            continue
        if value >= float(smooth[i - 1]) and value > float(smooth[i + 1]):
            raw.append((i, value))
    if not raw:
        return []

    chosen: list[tuple[int, float]] = []
    for idx, strength in raw:
        if chosen and idx - chosen[-1][0] < min_gap_frames:
            if strength > chosen[-1][1]:
                chosen[-1] = (idx, strength)
            continue
        chosen.append((idx, strength))

    return [
        _OnsetPeak(t_s=offset_s + (idx * frame / sample_rate), strength=strength / max_strength)
        for idx, strength in chosen
    ]


def _phase_points_from_peaks(peaks: list[_OnsetPeak], *, bpm: float) -> list[PhasePoint]:
    if len(peaks) < 2 or bpm <= 0.0:
        return []
    beat_s = 60.0 / bpm
    anchor_s = peaks[0].t_s
    raw_errors = [_beat_residual(p.t_s, anchor_s=anchor_s, beat_s=beat_s) for p in peaks]
    baseline = float(np.median(np.asarray(raw_errors, dtype=np.float32)))
    points = []
    for peak, raw_error in zip(peaks, raw_errors, strict=True):
        centered = _phase_error((raw_error - baseline) % 1.0, 0.0)
        points.append(
            PhasePoint(
                t_s=peak.t_s,
                error_beats=float(-centered),
                strength=float(max(0.0, min(1.0, peak.strength))),
            )
        )
    return points


def _beat_residual(t_s: float, *, anchor_s: float, beat_s: float) -> float:
    raw = ((t_s - anchor_s + beat_s * 0.5) % beat_s) - beat_s * 0.5
    return raw / beat_s


def _find_out_in_candidate(
    points: list[PhasePoint],
    *,
    bpm: float,
    bpm_confidence: float,
    transition_window: TransitionWindow,
    min_confidence: float,
) -> NearMissResult | None:
    if bpm <= 0.0:
        return None
    bar_s = 4.0 * 60.0 / bpm
    max_recovery_s = _MAX_RECOVERY_BARS * bar_s
    best: NearMissResult | None = None

    for start_idx, start in enumerate(points):
        if abs(start.error_beats) < _OUT_ERROR_BEATS:
            continue
        out_points = [start]
        peak = start
        for next_point in points[start_idx + 1 :]:
            elapsed = next_point.t_s - start.t_s
            if elapsed <= 0.0:
                continue
            if elapsed > max_recovery_s:
                break
            if abs(next_point.error_beats) >= _OUT_ERROR_BEATS:
                out_points.append(next_point)
                if abs(next_point.error_beats) > abs(peak.error_beats):
                    peak = next_point
                continue
            if abs(next_point.error_beats) > _IN_ERROR_BEATS:
                continue
            if len(out_points) < _MIN_OUT_POINTS:
                continue
            window_start_s = max(0.0, start.t_s - 0.5 * bar_s)
            window_end_s = next_point.t_s + 0.5 * bar_s
            if not transition_window.overlaps(window_start_s, window_end_s):
                continue
            depth = abs(peak.error_beats)
            recovery_bars = max(0.0, (next_point.t_s - peak.t_s) / bar_s)
            confidence = _near_miss_confidence(
                depth=depth,
                recovery_bars=recovery_bars,
                bpm_confidence=bpm_confidence,
                point_strength=min(peak.strength, next_point.strength),
            )
            if confidence < min_confidence:
                continue
            candidate = NearMissResult(
                t_center_s=(peak.t_s + next_point.t_s) / 2.0,
                window_start_s=window_start_s,
                window_end_s=window_end_s,
                depth_beats=depth,
                recovery_bars=recovery_bars,
                confidence=confidence,
                bpm=bpm,
                phase_error_beats_peak=peak.error_beats,
                citation=f"[mix:near_miss@{((peak.t_s + next_point.t_s) / 2.0):.3f}]",
                event_type=transition_window.event_type,
                event_t_s=transition_window.event_t_s,
            )
            if best is None or candidate.confidence > best.confidence:
                best = candidate
            break
    return best


def _near_miss_confidence(
    *,
    depth: float,
    recovery_bars: float,
    bpm_confidence: float,
    point_strength: float,
) -> float:
    depth_score = max(0.0, min(1.0, (depth - _OUT_ERROR_BEATS) / 0.16))
    recovery_score = max(0.0, min(1.0, 1.0 - max(0.0, recovery_bars - 4.0) / 8.0))
    strength_score = max(0.0, min(1.0, point_strength))
    confidence = (
        0.38 * depth_score
        + 0.24 * recovery_score
        + 0.24 * max(0.0, min(1.0, bpm_confidence))
        + 0.14 * strength_score
    )
    return float(max(0.0, min(1.0, confidence)))


def _transition_windows(events: list[dict[str, Any]], duration_s: float) -> list[TransitionWindow]:
    windows: list[TransitionWindow] = []
    for event in events:
        event_type = _transition_event_type(event)
        if event_type is None:
            continue
        t_s = _event_time_s(event)
        if t_s is None:
            continue
        windows.append(
            TransitionWindow(
                start_s=max(0.0, t_s - _TRANSITION_PAD_BEFORE_S),
                end_s=min(duration_s, t_s + _TRANSITION_PAD_AFTER_S),
                event_type=event_type,
                event_t_s=t_s,
            )
        )
    return windows


def _transition_event_type(event: dict[str, Any]) -> str | None:
    kind = str(event.get("kind") or "")
    event_type = str(event.get("type") or event.get("ev_type") or "")
    if kind == "transition_judged":
        return "transition_judged"
    if kind == "event" and event_type in {"TRACK_CHANGE", "MIX_MOVE"}:
        return event_type
    if event_type in {"TRACK_CHANGE", "MIX_MOVE"}:
        return event_type
    return None


def _event_time_s(event: dict[str, Any]) -> float | None:
    for key in ("t", "t_session", "time_s"):
        value = event.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def _read_events_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _read_wav_mono_float32(path: Path) -> tuple[np.ndarray, int] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    except (wave.Error, OSError):
        return None
    if channels <= 0 or sample_width != 2 or sample_rate <= 0 or not frames:
        return None
    arr = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        usable = (arr.size // channels) * channels
        if usable == 0:
            return None
        arr = arr[:usable].reshape(-1, channels).mean(axis=1)
    return (arr.astype(np.float32, copy=False), sample_rate)
