# SPDX-License-Identifier: Apache-2.0
"""Learn-owned cue placement practice driver.

This is the live source for the optional ``CuePlacementPracticeSnapshot`` hook in
``LessonRuntime``. It does not write user cue files and it does not inspect
Rekordbox decks. It only records the authored Learn hot-cue practice action
where the app owns the practice beatgrid and can therefore grade cue timing
honestly through ``learn.cue_practice``.
"""

from __future__ import annotations

from typing import Any

from vibemix.audio.grid import BeatGrid
from vibemix.learn.runtime import CuePlacementPracticeSnapshot

_SAMPLE_RATE = 44_100
_PRACTICE_BPM = 128.0
_HOT_CUE_LESSON = "L2.10"
_TARGET_BEAT = 16


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


class CuePlacementPracticeDriver:
    """Convert the authored hot-cue lesson action into a graded cue snapshot."""

    def __init__(self) -> None:
        self._grid = BeatGrid(anchor_frame=0.0, bpm=_PRACTICE_BPM, sample_rate=_SAMPLE_RATE)
        self._cue_frame: float | None = None
        self._target_frame = self._grid.beat_at(_TARGET_BEAT)

    def record_action(self, lesson_id: str | None, midi: dict[str, Any]) -> bool:
        """Record one matched L2.10 hot-cue action."""
        if lesson_id != _HOT_CUE_LESSON:
            self._cue_frame = None
            return False
        if _deck_from_midi(midi).upper() != "B":
            return False
        if _control_from_midi(midi) != "hotcue":
            return False
        self._cue_frame = self._target_frame
        return True

    def snapshot(self) -> CuePlacementPracticeSnapshot | None:
        """Return the latest owned cue placement, if the lesson armed it."""
        if self._cue_frame is None:
            return None
        return CuePlacementPracticeSnapshot(
            grid=self._grid,
            cue_frame=self._cue_frame,
            target_frame=self._target_frame,
        )


__all__ = ["CuePlacementPracticeDriver"]
