# SPDX-License-Identifier: Apache-2.0
"""Dedicated headphone player for Learn-owned two-deck practice.

The beatmatch practice lane owns a :class:`MiniDeck`; the judge grades that
deck's exact frame cursors. This player renders the same object to a dedicated
``sounddevice.OutputStream`` so audio playback and grading advance together.

Like ``ExemplarPlayer``, this never pushes into the co-host playback queue. The
co-host queue is mic-gated; practice audio belongs on the learner headphone bus.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np
import sounddevice as sd

from vibemix.audio.miniplayer import MiniDeck

_DEFAULT_SAMPLE_RATE = 44_100


class TwoDeckPlayer:
    """Render a Learn-owned :class:`MiniDeck` through a headphone OutputStream."""

    def __init__(
        self,
        device_index: int,
        mini_deck: MiniDeck,
        *,
        state: Any,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
    ) -> None:
        self._device_index = device_index
        self._deck = mini_deck
        self._state = state
        self._sample_rate = int(sample_rate)
        self._stream: sd.OutputStream | None = None
        self._lock = threading.Lock()

    def can_play(self) -> bool:
        """Refuse lesson audio while a live set is active and audible."""

        session_active = bool(getattr(self._state, "session_active", False))
        audible_deck = getattr(self._state, "audible_deck", "none")
        return not (session_active and audible_deck != "none")

    def start(self) -> None:
        """Start rendering the practice deck. Idempotent."""

        self.stop()
        if not self.can_play():
            return

        def _callback(outdata, frames, time_info, status) -> None:
            del time_info, status
            try:
                with self._lock:
                    block = self._deck.render_block(int(frames))
                _copy_block(outdata, block)
            except Exception:
                outdata.fill(0)

        self._stream = sd.OutputStream(
            device=self._device_index,
            samplerate=self._sample_rate,
            channels=2,
            dtype="float32",
            latency="low",
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop and close the output stream. Safe to call repeatedly."""

        stream = self._stream
        self._stream = None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:  # pragma: no cover - sounddevice cleanup is best-effort
            pass


def _copy_block(outdata: np.ndarray, block: np.ndarray) -> None:
    """Copy ``block`` into ``outdata``, padding with silence if needed."""

    outdata.fill(0)
    if block.ndim != 2 or block.shape[1] != 2:
        return
    n = min(outdata.shape[0], block.shape[0])
    outdata[:n, :2] = block[:n, :2]


__all__ = ["TwoDeckPlayer"]
