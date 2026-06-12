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
from vibemix.learn.save_mode_loader import PracticeDeckSource, PracticeDeckSources

_SAMPLE_RATE = 44_100
_PRACTICE_BPM = 128.0
_CENTER_CC = 64.0
_TEMPO_CC_RATE_SPAN = 640.0
_PRACTICE_LESSONS = frozenset({"L2.01", "L2.02"})
_EQ_PRACTICE_LESSONS = frozenset({"L2.04", "L2.05"})
_RECOVERY_DRILL_LESSONS = frozenset({"L3.05"})
_MIXER_CONTROLS = frozenset({"eq_hi", "eq_mid", "eq_low", "filter", "vol"})
_ASSET_PACKAGE = "vibemix.learn.assets.band_exemplars"
_DEMO_LOOP_BEATS = 64
_SANDBOX_JOG_BEATS = 0.08


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


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


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


def _cc_float(value: Any, *, default: float = _CENTER_CC) -> float:
    try:
        cc = float(value)
    except (TypeError, ValueError):
        cc = default
    return min(127.0, max(0.0, cc))


def _beat_frames() -> int:
    return round(_SAMPLE_RATE * 60.0 / _PRACTICE_BPM)


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


def _demo_waveform_deck(samples: np.ndarray, *, bpm: float, deck: str) -> dict[str, Any]:
    return {
        "track_id": f"learn-demo-{deck.lower()}",
        "title": f"Practice Loop {deck.upper()}",
        "artist": "Vibemix",
        "source": "bundled_demo",
        "bpm": bpm,
        "duration_s": float(samples.shape[0]) / float(_SAMPLE_RATE),
        "peaks": compute_three_band_peaks(samples, sample_rate=_SAMPLE_RATE),
        "cues": _demo_cues(),
    }


def _source_waveform_deck(source: PracticeDeckSource) -> dict[str, Any]:
    return {
        "track_id": source.track_id,
        "title": source.title,
        "artist": source.artist,
        "source": "library_save_mode",
        "bpm": source.bpm,
        "duration_s": float(source.samples.shape[0]) / float(source.sample_rate),
        "peaks": compute_three_band_peaks(source.samples, sample_rate=source.sample_rate),
        "cues": list(source.cues),
        "source_start_s": source.source_start_s,
    }


class BeatmatchPracticeDriver:
    """Convert authored Learn beatmatch actions into owned-deck snapshots."""

    def __init__(self, sources: PracticeDeckSources | None = None) -> None:
        if sources is None:
            src_a = _packaged_demo_loop(bass_hz=82.0, deck="A")
            src_b = _packaged_demo_loop(bass_hz=98.0, deck="B")
            self._sample_rate = _SAMPLE_RATE
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
            initial_rate_b = 0.97
            self._waveform_decks = {
                "A": _demo_waveform_deck(src_a, bpm=_PRACTICE_BPM, deck="A"),
                "B": _demo_waveform_deck(src_b, bpm=_PRACTICE_BPM, deck="B"),
            }
        else:
            src_a = sources.deck_a.samples.astype(np.float32, copy=False)
            src_b = sources.deck_b.samples.astype(np.float32, copy=False)
            self._sample_rate = int(sources.sample_rate)
            self._grid_a = sources.deck_a.grid
            self._grid_b = sources.deck_b.grid
            initial_rate_b = self._rate_b_for_lock() * 0.97
            self._waveform_decks = {
                "A": _source_waveform_deck(sources.deck_a),
                "B": _source_waveform_deck(sources.deck_b),
            }
        self._practice_source = str(
            self._waveform_decks.get("A", {}).get("source")
            or self._waveform_decks.get("B", {}).get("source")
            or "bundled_demo"
        )
        self._source_reason: str | None = None
        self._deck = MiniDeck(
            src_a,
            src_b,
            rate_a=1.0,
            rate_b=initial_rate_b,
            xfader=0.5,
            sample_rate=self._sample_rate,
            loop=True,
        )
        self._armed = False
        self._sandbox_active = False
        self._save_difficulty_level = 1

    @property
    def deck(self) -> MiniDeck:
        """Return the exact owned deck that snapshots grade."""

        return self._deck

    @property
    def save_difficulty_level(self) -> int:
        """Return the current Save challenge level used by recovery drills."""

        return self._save_difficulty_level

    def set_save_difficulty(self, level: int) -> None:
        """Set the bounded Save-mode challenge level.

        Runtime owns escalation. The driver owns what that level means for the
        audible owned deck: a larger tempo shove for key-clash drills and a
        larger phase shove for phrase-miss drills.
        """

        try:
            raw = int(level)
        except (TypeError, ValueError):
            raw = 1
        self._save_difficulty_level = max(1, min(5, raw))

    def set_source_reason(self, reason: str | None) -> None:
        """Record why Save mode stayed on bundled practice loops."""

        self._source_reason = _optional_text(reason)

    def record_action(self, lesson_id: str | None, midi: dict[str, Any]) -> bool:
        """Record one matched Learn action.

        Returns ``True`` only when the action belongs to the owned beatmatch
        practice lane and should be graded. The driver never reads live
        Rekordbox decks; it only reacts to the authored L2.01/L2.02 practice
        actions that ``LessonRuntime`` has already matched.

        ``lesson_id is None`` is the free-practice sandbox. It updates the same
        owned deck so the learner can play before starting a lesson, but it
        never arms a graded snapshot.
        """

        sandbox = lesson_id is None
        if not sandbox:
            self._sandbox_active = False
        deck = _deck_from_midi(midi).upper()
        control = _control_from_midi(midi)
        value = midi.get("value")
        if control == "xfader":
            try:
                cc = float(value)
            except (TypeError, ValueError):
                cc = _CENTER_CC
            self._deck.xfader = min(1.0, max(0.0, cc / 127.0))
            if sandbox:
                self._sandbox_active = True
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
            if sandbox:
                self._sandbox_active = True
            return False

        if sandbox:
            self._record_sandbox_action(control=control, deck=deck, midi=midi)
            return False

        if lesson_id in _RECOVERY_DRILL_LESSONS and control == "recovery_drill":
            self._arm_recovery_drill(midi)
            return True

        if lesson_id not in _PRACTICE_LESSONS:
            self._armed = False
            return False

        if deck != "B":
            return False
        if lesson_id == "L2.01" and control == "tempo":
            self._deck.set_rates(
                rate_a=1.0,
                rate_b=self._tempo_rate_for_deck("B", midi.get("value")),
                smooth=False,
            )
            self._armed = True
            return True
        if lesson_id == "L2.02" and control == "sync":
            self._deck.set_rates(rate_a=1.0, rate_b=self._rate_b_for_lock(), smooth=False)
            self._armed = True
            return True
        return False

    def _record_sandbox_action(
        self,
        *,
        control: str,
        deck: str,
        midi: dict[str, Any],
    ) -> None:
        """Apply a free-practice gesture without arming a lesson grade."""

        deck = deck.upper()
        if deck not in {"A", "B"}:
            deck = "B"
        if control == "tempo":
            rate = self._tempo_rate_for_deck(deck, midi.get("value"))
            if deck == "A":
                self._deck.set_rates(rate_a=rate, smooth=True)
            else:
                self._deck.set_rates(rate_b=rate, smooth=True)
            self._sandbox_active = True
            return
        if control == "sync":
            state = self._deck.state()
            if deck == "A":
                self._deck.set_rates(rate_a=self._rate_a_for_lock(state.rate_b), smooth=False)
            else:
                self._deck.set_rates(rate_b=self._rate_b_for_lock(state.rate_a), smooth=False)
            self._sandbox_active = True
            return
        if control in {"jog", "jog_touch", "jog_touched"}:
            direction = str(midi.get("direction", "") or "")
            value = _cc_float(midi.get("value"))
            prev = _cc_float(midi.get("prev_value"), default=value)
            delta = value - prev
            if abs(delta) < 1.0:
                delta = 1.0 if direction != "up" else -1.0
            self._deck.offset_playhead(
                deck,
                self._beat_frames_for(deck) * _SANDBOX_JOG_BEATS * (delta / 64.0),
            )
            self._sandbox_active = True

    def _arm_recovery_drill(self, midi: dict[str, Any]) -> None:
        """Introduce one authored L3.05 train-wreck state on the owned deck."""

        deck = _deck_from_midi(midi).upper() or "B"
        drill = str(midi.get("drill", "") or "").strip()
        self._deck.set_rates(rate_a=1.0, rate_b=self._rate_b_for_lock(), smooth=False)
        if drill == "key_clash":
            rate_shove = min(0.12, 0.065 + (self._save_difficulty_level * 0.015))
            self._deck.set_rates(
                rate_a=1.0,
                rate_b=self._rate_b_for_lock() * (1.0 + rate_shove),
                smooth=False,
            )
        else:
            phase_shove = min(0.38, 0.20 + (self._save_difficulty_level * 0.05))
            self._deck.offset_playhead(deck, self._beat_frames_for(deck) * phase_shove)
        self._armed = True

    def wreck(self, kind: str, level: int) -> None:
        """Shove deck B off for a Wreck Room round (sandbox lane).

        Same authored shove math as the L3.05 recovery drill, but it arms the
        SANDBOX snapshot, never a graded lesson snapshot — wreck rounds are
        feedback-only and write no evidence.
        """

        bounded = max(1, min(5, int(level)))
        self._deck.set_rates(rate_a=1.0, rate_b=self._rate_b_for_lock(), smooth=False)
        if kind == "phase":
            phase_shove = min(0.38, 0.20 + (bounded * 0.05))
            self._deck.offset_playhead("B", self._beat_frames_for("B") * phase_shove)
        else:
            rate_shove = min(0.12, 0.065 + (bounded * 0.015))
            self._deck.set_rates(
                rate_a=1.0,
                rate_b=self._rate_b_for_lock() * (1.0 + rate_shove),
                smooth=False,
            )
        self._armed = False
        self._sandbox_active = True

    def lock_b(self) -> None:
        """Lock deck B to deck A in both tempo and phase (the groove state)."""

        state = self._deck.state()
        self._deck.set_rates(rate_a=1.0, rate_b=self._rate_b_for_lock(), smooth=False)
        phase_a = self._grid_a.beat_index(state.a_frame) % 1.0
        phase_b = self._grid_b.beat_index(state.b_frame) % 1.0
        err = (phase_a - phase_b + 0.5) % 1.0 - 0.5
        if abs(err) > 1e-6:
            self._deck.offset_playhead("B", self._beat_frames_for("B") * err)
        self._sandbox_active = True

    def yank_b(self) -> None:
        """Cut deck B's channel fader (the missed-window theater)."""

        self._deck.set_volume("B", 0)
        self._sandbox_active = True

    def restore_b(self) -> None:
        """Bring deck B's channel fader back for the next groove."""

        self._deck.set_volume("B", 127)
        self._sandbox_active = True

    def snapshot(self) -> BeatmatchPracticeSnapshot | None:
        """Return the latest owned practice state, if a practice action armed it."""

        if not self._armed:
            return None
        return self._snapshot()

    def sandbox_snapshot(self) -> BeatmatchPracticeSnapshot | None:
        """Return the current free-practice state without arming lesson credit."""

        if not self._sandbox_active:
            return None
        return self._snapshot()

    def _snapshot(self) -> BeatmatchPracticeSnapshot:
        return BeatmatchPracticeSnapshot(
            grid_a=self._grid_a,
            grid_b=self._grid_b,
            deck_state=self._deck.state(),
            practice_source=self._practice_source,
            deck_a_track_id=_optional_text(self._waveform_decks["A"].get("track_id")),
            deck_b_track_id=_optional_text(self._waveform_decks["B"].get("track_id")),
            deck_a_title=_optional_text(self._waveform_decks["A"].get("title")),
            deck_b_title=_optional_text(self._waveform_decks["B"].get("title")),
        )

    def _tempo_rate_for_deck(self, deck: str, value: Any) -> float:
        rate = _tempo_rate_from_cc(value)
        if deck == "B":
            return self._rate_b_for_lock() * rate
        return rate

    def _rate_b_for_lock(self, rate_a: float = 1.0) -> float:
        return float(rate_a) * self._grid_a.bpm / self._grid_b.bpm

    def _rate_a_for_lock(self, rate_b: float = 1.0) -> float:
        return float(rate_b) * self._grid_b.bpm / self._grid_a.bpm

    def _beat_frames_for(self, deck: str) -> int:
        grid = self._grid_b if deck == "B" else self._grid_a
        return round(grid.beat_len_frames)

    def waveform_payload(self) -> dict[str, Any]:
        """Return compact two-deck waveform payload for Learn Canvas rendering."""

        decks = self._waveform_decks
        if self._source_reason is not None:
            decks = {
                deck: {**row, "source_reason": self._source_reason}
                for deck, row in self._waveform_decks.items()
            }
        return {
            "sample_rate": self._sample_rate,
            "beat_interval_s": 60.0 / self._grid_a.bpm,
            "decks": decks,
        }

    def playhead_payload(self) -> dict[str, Any]:
        """Return current owned-deck playheads and BPMs for the Learn UI."""

        state = self._deck.state()
        duration_a = float(self._waveform_decks["A"]["duration_s"])
        duration_b = float(self._waveform_decks["B"]["duration_s"])
        frame_a = float(state.a_frame % max(1.0, duration_a * self._sample_rate))
        frame_b = float(state.b_frame % max(1.0, duration_b * self._sample_rate))
        return {
            "sample_rate": self._sample_rate,
            "decks": {
                "A": {
                    "frame": frame_a,
                    "position_s": frame_a / float(self._sample_rate),
                    "bpm": self._grid_a.bpm * state.rate_a,
                },
                "B": {
                    "frame": frame_b,
                    "position_s": frame_b / float(self._sample_rate),
                    "bpm": self._grid_b.bpm * state.rate_b,
                },
            },
        }


__all__ = ["BeatmatchPracticeDriver"]
