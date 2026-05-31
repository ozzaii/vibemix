# SPDX-License-Identifier: Apache-2.0
"""Duck-and-mix the co-host voice over the live mix — the viral drop moment.

When the AI calls the drop, the music dips under the voice for the length of the
line, then comes back — a real DJ leaning into your ear. The demo's audio callback
runs on the OS audio thread, so the mix is this one pure, allocation-light numpy
function: given a block of the mix, the full voice-line buffer, and a play cursor
into it, return the ducked+mixed block and the advanced cursor.
"""
from __future__ import annotations

import numpy as np

# Music gain while the voice is talking. -7 dB-ish: the mix stays present (the drop
# is the point) but the line cuts through. Below the voice, never under it.
_DEFAULT_DUCK_GAIN: float = 0.45


def mix_voice_over(
    music: np.ndarray,
    voice: np.ndarray,
    cursor: int,
    *,
    voice_gain: float = 1.0,
    duck_gain: float = _DEFAULT_DUCK_GAIN,
) -> tuple[np.ndarray, int]:
    """Mix one block of ``voice`` (from ``cursor``) over ``music``, ducking the music.

    ``music`` is the current ``(frames, 2)`` output block; ``voice`` is the whole
    finished line buffer ``(N, 2)``; ``cursor`` is the next unplayed voice sample.
    Only the frames that overlap remaining voice are ducked — once the line ends
    inside the block, the rest of the block is the mix at full level. Returns a NEW
    block (never mutates ``music``) and the advanced cursor (capped at ``len(voice)``).
    """
    out = np.array(music, dtype=np.float32, copy=True)
    remaining = int(voice.shape[0]) - int(cursor)
    if remaining <= 0:
        return out, int(cursor)  # voice exhausted — pass the mix through untouched
    n = min(int(music.shape[0]), remaining)
    out[:n] = music[:n] * duck_gain + voice[cursor : cursor + n] * voice_gain
    return out, int(cursor) + n
