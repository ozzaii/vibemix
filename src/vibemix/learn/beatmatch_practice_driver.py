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


class BeatmatchPracticeDriver:
    """Convert authored Learn beatmatch actions into owned-deck snapshots."""

    def __init__(self) -> None:
        silent = np.zeros((2, 2), dtype=np.float32)
        self._deck = MiniDeck(silent, silent, rate_a=1.0, rate_b=0.97, xfader=0.5)
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

        if lesson_id not in _PRACTICE_LESSONS:
            self._armed = False
            return False
        if _deck_from_midi(midi).upper() != "B":
            return False

        control = _control_from_midi(midi)
        if lesson_id == "L2.01" and control == "tempo":
            self._deck.rate_a = 1.0
            self._deck.rate_b = _tempo_rate_from_cc(midi.get("value"))
            self._armed = True
            return True
        if lesson_id == "L2.02" and control == "sync":
            self._deck.rate_a = 1.0
            self._deck.rate_b = 1.0
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
