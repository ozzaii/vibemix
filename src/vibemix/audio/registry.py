# SPDX-License-Identifier: Apache-2.0
"""Value object aggregating the audio primitives that Plan 04's AudioMacOS
constructor accepts.

`audio` is the gain-boosted state buffer (v4:1880, sized 140s); `clean_audio` is
the natural-level LLM-snapshot buffer (v4:1881, sized INVOKE_AUDIO_SECONDS + 5s).
Both are AudioBuffer instances with different `seconds`; the gain difference is
applied by the input callback before pushing.

`levels` is the shared Levels instance threaded into MicBuffer (for `_current_gain`)
and PlaybackQueue (for `update_voice` / `decay_voice`). Holding it in the registry
makes the canonical reference explicit and prevents callers from accidentally
constructing distinct Levels instances per buffer.
"""

from __future__ import annotations

from dataclasses import dataclass

from vibemix.audio.buffers import AudioBuffer, MicBuffer, PassthroughBuffer, PlaybackQueue
from vibemix.audio.levels import Levels


@dataclass(frozen=True)
class BufferRegistry:
    """Bundles the four audio buffers + Levels for the AudioMacOS constructor.

    Frozen so the registry can't be mutated after construction — the four
    buffer references are wired once at startup and threaded through the
    sounddevice callbacks (Plan 04).
    """

    audio: AudioBuffer
    clean_audio: AudioBuffer
    mic: MicBuffer
    passthrough: PassthroughBuffer
    playback: PlaybackQueue
    levels: Levels
