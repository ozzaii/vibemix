# SPDX-License-Identifier: Apache-2.0
"""KickSwapDetector — within-track kick character change.

Fires when the 40-120Hz spectral centroid shifts by at least
``KICK_SWAP_CENTROID_DELTA_HZ`` across two consecutive ~4s windows while RMS
is above ``LOW_RMS``. The semantic moment captured: a DJ swapping kick
character mid-track (clean → distorted, soft → punchy) without disturbing
rhythm — exactly the kind of thing v4's existing ``LAYER_ARRIVAL`` detector
misses (LAYER_ARRIVAL only watches mid/high band jumps).

Anti-double-fire contract with TRACK_CHANGE (per Plan 17-02 threat register
T-17-02-01): the ``EventDetector`` chain that wraps this detector evaluates
``TRACK_CHANGE`` first (its 6s cooldown plus track-id confidence gate). When a
true track change happens, ``TRACK_CHANGE`` claims the moment first; KICK_SWAP's
14s cooldown then absorbs the centroid jump that the new track brings.

Pattern reference: cooldown gate idiom + dependency-injected refs are taken
from ``vibemix.state.event_detector.EventDetector`` per CONTEXT POC port-from
rule. State is intentionally minimal — only the previous centroid + the
timestamp it was captured. Phase 3 single-writer invariant is preserved
(detector NEVER writes to MusicState).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    KICK_SWAP_CENTROID_DELTA_HZ,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.detectors._dsp import kick_band_centroid
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.music_state import MusicState

# Trailing window we hand to ``kick_band_centroid``. Mirrors the ``pcm_for_crest``
# window used by ``state_refresh_loop._tick_once`` so centroid + crest stay
# aligned on the same 4s slice of audio.
_WINDOW_SEC: float = 4.0


class KickSwapDetector:
    """Stateful detector — keeps the prior centroid + the time it was captured
    so consecutive ``.detect()`` calls compare against a baseline that's at
    least ``_WINDOW_SEC`` old (avoids triggering against a baseline captured
    half a window ago, which would compare partly-overlapping audio).

    Fields are public-readable for tests + observability — never mutated by
    anything other than ``detect()``.
    """

    def __init__(self) -> None:
        self.last_event_at: float = 0.0
        self.last_centroid_hz: float | None = None
        self.last_centroid_at: float = 0.0

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer",
        now: float,
    ) -> Event | None:
        """Return an ``Event("KICK_SWAP", ...)`` when the kick-band centroid
        has shifted by ≥ ``KICK_SWAP_CENTROID_DELTA_HZ`` since the last
        captured baseline, else ``None``.

        Order of gates matters — silence gate fires FIRST so a silent buffer
        doesn't seed a phantom baseline (anti-hallucination per the v4
        "trust the audio" rule).
        """
        # 1. Silence gate: must be BEFORE baseline seeding. A breakdown / pause
        #    must NOT seed a "kick at 0Hz" baseline that the next audible tick
        #    would diff against.
        if state.rms < LOW_RMS:
            return None

        # 2-3. Snapshot the trailing _WINDOW_SEC and compute the kick-band
        #      centroid. ``audio_buf.snapshot()`` is a memcpy (not I/O) — cheap
        #      enough to do every tick per Plan 17-02 threat register T-17-02-04.
        n_samples = int(audio_buf._sr * _WINDOW_SEC)
        samples = audio_buf.snapshot(n_samples)
        current = kick_band_centroid(samples, audio_buf._sr)

        # 4. First call ever — seed baseline + bail. We need TWO snapshots
        #    before we can diff anything.
        if self.last_centroid_hz is None:
            self.last_centroid_hz = current
            self.last_centroid_at = now
            return None

        # 5. Window guard — the baseline must be at least one full _WINDOW_SEC
        #    old. Otherwise we'd be comparing centroids over partly-overlapping
        #    audio slices, which silently halves the achievable delta.
        if now - self.last_centroid_at < _WINDOW_SEC:
            return None

        # 6. Cooldown gate — even if a real shift just happened, refuse to
        #    fire twice within the per-type cooldown. Rotate baseline so the
        #    NEXT post-cooldown tick has a fresh anchor (per Plan step 6).
        cooldown = MIN_EVENT_GAP_PER_TYPE["KICK_SWAP"]
        if now - self.last_event_at < cooldown:
            self.last_centroid_hz = current
            self.last_centroid_at = now
            return None

        # 7-8. Compute delta + maybe fire.
        prev = self.last_centroid_hz
        delta = abs(current - prev)
        if delta >= KICK_SWAP_CENTROID_DELTA_HZ:
            ev = Event(
                "KICK_SWAP",
                state,
                extra={
                    "prev_centroid_hz": float(prev),
                    "new_centroid_hz": float(current),
                    "delta_hz": float(delta),
                },
            )
            self.last_centroid_hz = current
            self.last_centroid_at = now
            self.last_event_at = now
            return ev

        # 9. Slow-drift hygiene — rotate baseline so a 10-minute slow drift can
        #    never accumulate into a spurious fire. Same idiom as KickDensityShift.
        self.last_centroid_hz = current
        self.last_centroid_at = now
        return None
