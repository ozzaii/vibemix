# SPDX-License-Identifier: Apache-2.0
"""Learn-owned beatmatch practice driver.

The live co-host observes Rekordbox/FLX4 and cannot honestly grade beatmatching
there without per-deck beat grids. Learn is different: it owns a tiny two-deck
practice island, so it can produce the exact ``DeckState`` the Beatmatch Judge
requires. This driver is deliberately small: it records only the authored
Course 2 beatmatch actions and exposes a snapshot for ``LessonRuntime`` to
grade through ``learn.practice_loop``.
"""

from __future__ import annotations

import wave
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

import numpy as np

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import MiniDeck
from vibemix.audio.waveform_peaks import compute_three_band_peaks
from vibemix.learn.runtime import BeatmatchPracticeSnapshot

_SAMPLE_RATE = 44_100
_PRACTICE_BPM = 128.0
_CENTER_CC = 64.0
_TEMPO_CC_RATE_SPAN = 640.0
_PRACTICE_LESSONS = frozenset({"L2.01", "L2.02"})
_EQ_PRACTICE_LESSONS = frozenset({"L2.04", "L2.05"})
_MIXER_CONTROLS = frozenset({"eq_hi", "eq_mid", "eq_low", "filter", "vol"})
_ASSET_PACKAGE = "vibemix.learn.assets.band_exemplars"
_DEMO_LOOP_BEATS = 64


def _deck_from_midi(midi: dict[str, Any]) -> str:
    deck = str(midi.get("deck", "") or "").strip()
    control = str(midi.get("control", "") or "").strip()
    if not deck and ":" in control:
        _control, _sep, parsed = control.rpartition(":")
        deck = parsed.strip()
    return deck


def _control_from_midi(midi: dict[str, Any]) -> str:
    control = str(midi.get("control", "") or "").strip()
    if ":" in control:
        control, _sep, _deck = control.rpartition(":")
    return control


def _tempo_rate_from_cc(value: Any) -> float:
    """Map the pitch-fader CC to the owned deck's playback rate.

    Value 64 is the centered pitch fader and therefore exact tempo lock. The
    span is intentionally gentle: values near center remain a close practice
    match, while large moves grade as tempo-off instead of earning credit.
    """

    try:
        cc = float(value)
    except (TypeError, ValueError):
        cc = _CENTER_CC
    cc = min(127.0, max(0.0, cc))
    return 1.0 + (cc - _CENTER_CC) / _TEMPO_CC_RATE_SPAN


def _practice_loop(*, bass_hz: float, hat_hz: float = 6_500.0) -> np.ndarray:
    """Build a small self-authored practice loop with kick, bass, and hats."""

    beat_s = 60.0 / _PRACTICE_BPM
    n_beats = _DEMO_LOOP_BEATS
    n_frames = round(_SAMPLE_RATE * beat_s * n_beats)
    t = np.arange(n_frames, dtype=np.float32) / float(_SAMPLE_RATE)
    beat_phase = np.mod(t, beat_s)

    kick_env = np.exp(-beat_phase * 28.0)
    kick = kick_env * np.sin(2.0 * np.pi * (55.0 + 40.0 * kick_env) * beat_phase)
    bass = 0.36 * np.sin(2.0 * np.pi * bass_hz * t)
    hat = 0.08 * np.sin(2.0 * np.pi * hat_hz * t) * (beat_phase < 0.045)
    body = 0.11 * np.sin(2.0 * np.pi * 440.0 * t) * (beat_phase < beat_s * 0.55)
    mono = (0.58 * kick + bass + hat + body).astype(np.float32)
    mono *= 0.7 / max(0.7, float(np.max(np.abs(mono))))
    return np.column_stack([mono, mono]).astype(np.float32)


def _read_wav_stereo(path: Path) -> tuple[np.ndarray, int]:
    """Read a bundled PCM WAV into ``(frames, 2)`` float32 samples."""

    with wave.open(str(path), "rb") as wf:
        channels = int(wf.getnchannels())
        sample_width = int(wf.getsampwidth())
        sample_rate = int(wf.getframerate())
        frames = int(wf.getnframes())
        raw = wf.readframes(frames)
    if sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width: {sample_width}")
    if channels <= 0:
        raise ValueError("WAV has no channels")
    samples = samples.reshape(-1, channels)
    if channels == 1:
        samples = np.column_stack([samples[:, 0], samples[:, 0]])
    elif channels > 2:
        samples = samples[:, :2]
    return samples.astype(np.float32, copy=False), sample_rate


def _resample_linear(samples: np.ndarray, *, src_sr: int, dst_sr: int) -> np.ndarray:
    """Small deterministic resampler for bundled fallback loops."""

    if src_sr == dst_sr:
        return samples.astype(np.float32, copy=False)
    if samples.size == 0:
        return samples.astype(np.float32, copy=False)
    target_n = max(1, round(samples.shape[0] * float(dst_sr) / float(src_sr)))
    src_x = np.linspace(0.0, samples.shape[0] - 1, samples.shape[0], dtype=np.float64)
    dst_x = np.linspace(0.0, samples.shape[0] - 1, target_n, dtype=np.float64)
    left = np.interp(dst_x, src_x, samples[:, 0])
    right = np.interp(dst_x, src_x, samples[:, 1])
    return np.column_stack([left, right]).astype(np.float32)


def _load_packaged_band_loop(rel_path: str) -> np.ndarray:
    resource = files(_ASSET_PACKAGE).joinpath(rel_path)
    with as_file(resource) as path:
        samples, sample_rate = _read_wav_stereo(path)
    return _resample_linear(samples, src_sr=sample_rate, dst_sr=_SAMPLE_RATE)


def _tile_to_frames(samples: np.ndarray, frames: int) -> np.ndarray:
    if samples.shape[0] <= 0:
        raise ValueError("cannot tile an empty loop")
    repeats = int(np.ceil(frames / float(samples.shape[0])))
    return np.tile(samples, (repeats, 1))[:frames].astype(np.float32, copy=False)


def _packaged_demo_loop(*, bass_hz: float, deck: str) -> np.ndarray:
    """Build a 64-beat demo track from bundled Apache-2.0 Learn loops.

    The generated kick/bass loop remains underneath so the L2.01 kill criterion
    stays literal: the beginner always hears kicks. The packaged band exemplars
    give L1.13 a real, bundled waveform with visible section changes.
    """

    base = _practice_loop(bass_hz=bass_hz)
    target_frames = base.shape[0]
    try:
        low = _tile_to_frames(
            _load_packaged_band_loop("low/vibemix_internal_low_bass_gate.wav"),
            target_frames,
        )
        mid = _tile_to_frames(
            _load_packaged_band_loop("mid/vibemix_internal_mid_chord_body.wav"),
            target_frames,
        )
        high = _tile_to_frames(
            _load_packaged_band_loop("high/vibemix_internal_high_hat_air.wav"),
            target_frames,
        )
        sub = _tile_to_frames(
            _load_packaged_band_loop("sub/vibemix_internal_sub_pulse.wav"),
            target_frames,
        )
    except Exception:
        return base

    beat_frames = round(_SAMPLE_RATE * 60.0 / _PRACTICE_BPM)
    if deck.upper() == "B":
        low = np.roll(low, beat_frames, axis=0)
        mid = np.roll(mid, beat_frames * 2, axis=0)
        high = np.roll(high, beat_frames // 2, axis=0)
    quarter = max(1, target_frames // 4)
    section_gain = np.ones((target_frames, 1), dtype=np.float32)
    section_gain[2 * quarter : 3 * quarter] = 0.34
    section_gain[3 * quarter :] = 0.72
    layered = (
        0.58 * base
        + 0.22 * low * section_gain
        + 0.18 * mid * section_gain
        + 0.16 * high
        + 0.10 * sub
    )
    peak = float(np.max(np.abs(layered))) if layered.size else 0.0
    if peak > 0.0:
        layered *= 0.82 / max(0.82, peak)
    return layered.astype(np.float32, copy=False)


def _demo_cues() -> list[dict[str, float | str]]:
    """Author-visible waveform bands for intro/drop/breakdown scanning."""

    return [
        {"label": "intro", "start_s": 0.0, "end_s": 7.5},
        {"label": "drop", "start_s": 7.5, "end_s": 15.0},
        {"label": "breakdown", "start_s": 15.0, "end_s": 22.5},
        {"label": "outro", "start_s": 22.5, "end_s": 30.0},
    ]


class BeatmatchPracticeDriver:
    """Convert authored Learn beatmatch actions into owned-deck snapshots."""

    def __init__(self) -> None:
        src_a = _packaged_demo_loop(bass_hz=82.0, deck="A")
        src_b = _packaged_demo_loop(bass_hz=98.0, deck="B")
        self._deck = MiniDeck(
            src_a,
            src_b,
            rate_a=1.0,
            rate_b=0.97,
            xfader=0.5,
            sample_rate=_SAMPLE_RATE,
            loop=True,
        )
        self._waveform_decks = {
            "A": {
                "bpm": _PRACTICE_BPM,
                "duration_s": float(src_a.shape[0]) / float(_SAMPLE_RATE),
                "peaks": compute_three_band_peaks(src_a, sample_rate=_SAMPLE_RATE),
                "cues": _demo_cues(),
            },
            "B": {
                "bpm": _PRACTICE_BPM,
                "duration_s": float(src_b.shape[0]) / float(_SAMPLE_RATE),
                "peaks": compute_three_band_peaks(src_b, sample_rate=_SAMPLE_RATE),
                "cues": _demo_cues(),
            },
        }
        self._grid_a = BeatGrid(
            anchor_frame=0.0,
            bpm=_PRACTICE_BPM,
            sample_rate=_SAMPLE_RATE,
        )
        self._grid_b = BeatGrid(
            anchor_frame=0.0,
            bpm=_PRACTICE_BPM,
            sample_rate=_SAMPLE_RATE,
        )
        self._armed = False

    @property
    def deck(self) -> MiniDeck:
        """Return the exact owned deck that snapshots grade."""

        return self._deck

    def record_action(self, lesson_id: str | None, midi: dict[str, Any]) -> bool:
        """Record one matched Learn action.

        Returns ``True`` only when the action belongs to the owned beatmatch
        practice lane and should be graded. The driver never reads live
        Rekordbox decks; it only reacts to the authored L2.01/L2.02 practice
        actions that ``LessonRuntime`` has already matched.
        """

        deck = _deck_from_midi(midi).upper()
        control = _control_from_midi(midi)
        value = midi.get("value")
        if control == "xfader":
            try:
                cc = float(value)
            except (TypeError, ValueError):
                cc = _CENTER_CC
            self._deck.xfader = min(1.0, max(0.0, cc / 127.0))
            return False
        if control in _MIXER_CONTROLS and deck in {"A", "B"}:
            if control == "vol":
                self._deck.set_volume(deck, value)
            elif control == "filter":
                self._deck.set_filter(deck, value)
            else:
                band = control.removeprefix("eq_")
                self._deck.set_eq(
                    deck,
                    low=value if band == "low" else None,
                    mid=value if band == "mid" else None,
                    high=value if band == "hi" else None,
                )
            return False

        if lesson_id not in _PRACTICE_LESSONS:
            self._armed = False
            return False

        if deck != "B":
            return False
        if lesson_id == "L2.01" and control == "tempo":
            self._deck.set_rates(
                rate_a=1.0,
                rate_b=_tempo_rate_from_cc(midi.get("value")),
                smooth=False,
            )
            self._armed = True
            return True
        if lesson_id == "L2.02" and control == "sync":
            self._deck.set_rates(rate_a=1.0, rate_b=1.0, smooth=False)
            self._armed = True
            return True
        return False

    def snapshot(self) -> BeatmatchPracticeSnapshot | None:
        """Return the latest owned practice state, if a practice action armed it."""

        if not self._armed:
            return None
        return BeatmatchPracticeSnapshot(
            grid_a=self._grid_a,
            grid_b=self._grid_b,
            deck_state=self._deck.state(),
        )

    def waveform_payload(self) -> dict[str, Any]:
        """Return compact two-deck waveform payload for Learn Canvas rendering."""

        return {
            "sample_rate": _SAMPLE_RATE,
            "beat_interval_s": 60.0 / _PRACTICE_BPM,
            "decks": self._waveform_decks,
        }

    def playhead_payload(self) -> dict[str, Any]:
        """Return current owned-deck playheads and BPMs for the Learn UI."""

        state = self._deck.state()
        duration_a = float(self._waveform_decks["A"]["duration_s"])
        duration_b = float(self._waveform_decks["B"]["duration_s"])
        frame_a = float(state.a_frame % max(1.0, duration_a * _SAMPLE_RATE))
        frame_b = float(state.b_frame % max(1.0, duration_b * _SAMPLE_RATE))
        return {
            "sample_rate": _SAMPLE_RATE,
            "decks": {
                "A": {
                    "frame": frame_a,
                    "position_s": frame_a / float(_SAMPLE_RATE),
                    "bpm": _PRACTICE_BPM * state.rate_a,
                },
                "B": {
                    "frame": frame_b,
                    "position_s": frame_b / float(_SAMPLE_RATE),
                    "bpm": _PRACTICE_BPM * state.rate_b,
                },
            },
        }


__all__ = ["BeatmatchPracticeDriver"]
