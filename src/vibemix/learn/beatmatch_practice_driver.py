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

from typing import Any

import numpy as np

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import MiniDeck
from vibemix.learn.runtime import BeatmatchPracticeSnapshot

_SAMPLE_RATE = 44_100
_PRACTICE_BPM = 128.0
_CENTER_CC = 64.0
_TEMPO_CC_RATE_SPAN = 640.0
_PRACTICE_LESSONS = frozenset({"L2.01", "L2.02"})
_EQ_PRACTICE_LESSONS = frozenset({"L2.04", "L2.05"})


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
    n_beats = 64
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


class BeatmatchPracticeDriver:
    """Convert authored Learn beatmatch actions into owned-deck snapshots."""

    def __init__(self) -> None:
        self._deck = MiniDeck(
            _practice_loop(bass_hz=82.0),
            _practice_loop(bass_hz=98.0),
            rate_a=1.0,
            rate_b=0.97,
            xfader=0.5,
            sample_rate=_SAMPLE_RATE,
        )
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

        if lesson_id not in _PRACTICE_LESSONS | _EQ_PRACTICE_LESSONS:
            self._armed = False
            return False

        deck = _deck_from_midi(midi).upper()
        control = _control_from_midi(midi)
        if lesson_id in _EQ_PRACTICE_LESSONS:
            self._armed = False
            if control == "eq_low" and deck in {"A", "B"}:
                self._deck.set_eq(deck, low=midi.get("value"))
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


__all__ = ["BeatmatchPracticeDriver"]
