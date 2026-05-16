# SPDX-License-Identifier: Apache-2.0
"""DistortionClimbDetector — Hard Tek "wall is getting taller" structural moment.

Fires when ALL THREE conditions co-occur within a 2s window:
    1. Band-limited spectral flatness (200-2000Hz) has risen by at least
       ``DISTORTION_FLATNESS_DELTA_MIN`` over the last
       ``DISTORTION_FLATNESS_WINDOW`` (4) detector ticks. Flatness rising =
       signal becoming more noise-like = more distortion stack.
    2. Harmonic-distortion proxy (odd-vs-even harmonic energy ratio at the
       kick fundamental) >= ``DISTORTION_HARMONIC_RATIO_MIN`` (1.5). Clipping
       / saturation emphasises odd harmonics.
    3. Sustained kick density >= ``DISTORTION_KICK_DENSITY_MIN`` (8/sec) for
       at least ``DISTORTION_KICK_DENSITY_SUSTAIN_S`` (4s). Without sustained
       kick density the signal is in a breakdown, not climbing.

Anti-hallucination contract (CONTEXT D + cohost_v4.py "trust the audio" rule):
    - Silence gate FIRST (state.rms < LOW_RMS) — clears density streak so a
      breakdown can never inherit a stale "kick density was high 6s ago" mark.
    - audio_buf None → graceful no-op.
    - All three gates required simultaneously — partial signals never fire.

Hard Tek genre gate: this detector is only INSERTED into the chain by
``build_hard_tek_chain``. House/techno sessions never see it, so the active
genre IS the gate (no extra ``if state.active_genre != "hard_tek"`` check
inside the detector — chain composition is the only signal that matters).

Payload (CONTEXT decision):
    chain_position : int  # 1-indexed sequential per session
    distortion_db  : float # 20·log10(harmonic_ratio); -inf clamped to -60

Cooldown: 6s per type (``MIN_EVENT_GAP_PER_TYPE["DISTORTION_CLIMB"]``).
"""

from __future__ import annotations

from collections import deque
from math import log10
from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    DISTORTION_FLATNESS_DELTA_MIN,
    DISTORTION_FLATNESS_WINDOW,
    DISTORTION_FUNDAMENTAL_HZ,
    DISTORTION_HARMONIC_RATIO_MIN,
    DISTORTION_KICK_DENSITY_MIN,
    DISTORTION_KICK_DENSITY_SUSTAIN_S,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.detectors._dsp import (
    band_spectral_flatness,
    harmonic_distortion_proxy,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.music_state import MusicState

# 4s snapshot window — matches KickSwap window so detectors stay aligned on
# the same trailing slice + the harmonic proxy + flatness measurements get
# enough integration for the FFT to settle.
_SNAPSHOT_WINDOW_SEC: float = 4.0

# Floor for the dB log so a zero-energy harmonic ratio doesn't blow up to
# -inf. -60 dB is the standard "musically inaudible" floor.
_DISTORTION_DB_FLOOR: float = -60.0


class DistortionClimbDetector:
    """Stateful detector — keeps a deque of recent flatness measurements
    + a density-streak start timestamp so the sustained-kick gate ages
    correctly across ticks.

    Fields are public-readable for tests + observability — never mutated
    by anything other than ``detect()``.
    """

    def __init__(self) -> None:
        self.last_event_at: float = 0.0
        self.chain_position: int = 0
        self._flatness_history: deque[float] = deque(maxlen=DISTORTION_FLATNESS_WINDOW)
        # None = not currently in a sustained-density streak. Float = the
        # timestamp when this streak STARTED. Cleared on silence / when
        # state.onset_density falls below the floor.
        self._density_streak_start: float | None = None

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return ``Event("DISTORTION_CLIMB", ...)`` when all three gates pass.

        Silence gate FIRST — a breakdown must not carry a stale density
        streak into the next audible tick; clearing it here means the
        streak rebuilds from scratch after silence (anti-hallucination
        per the v4 "trust the audio" rule).
        """
        # 1. Silence gate — clear streak + bail.
        if state.rms < LOW_RMS:
            self._density_streak_start = None
            return None

        # 1b. audio_buf-required gate — graceful no-op without raw samples.
        if audio_buf is None:
            return None

        # 2. Cooldown gate — refuse to fire twice within 6s, but keep
        #    streak + flatness history maintained so the post-cooldown tick
        #    sees a fresh-enough picture.
        cooldown = MIN_EVENT_GAP_PER_TYPE["DISTORTION_CLIMB"]
        if now - self.last_event_at < cooldown:
            return None

        # 3. Sustained density tracking — must happen on every audible tick,
        #    not just when the other gates pass, so the streak ages across
        #    ticks where flatness/harmonic gates haven't fired yet.
        if state.onset_density >= DISTORTION_KICK_DENSITY_MIN:
            if self._density_streak_start is None:
                self._density_streak_start = now
        else:
            self._density_streak_start = None

        # 4. Snapshot the trailing 4s and feed the flatness window.
        n_samples = int(audio_buf._sr * _SNAPSHOT_WINDOW_SEC)
        samples = audio_buf.snapshot(n_samples)
        # Need at least a partial window — snapshot returns < requested on
        # cold-start.
        if samples.size < audio_buf._sr * 0.5:
            return None

        current_flatness = band_spectral_flatness(samples, audio_buf._sr)
        self._flatness_history.append(current_flatness)

        # 5. Need a FULL window of flatness samples before evaluating delta.
        if len(self._flatness_history) < DISTORTION_FLATNESS_WINDOW:
            return None

        flatness_delta = self._flatness_history[-1] - self._flatness_history[0]
        if flatness_delta < DISTORTION_FLATNESS_DELTA_MIN:
            return None

        # 6. Harmonic distortion proxy gate.
        harmonic_ratio = harmonic_distortion_proxy(
            samples, audio_buf._sr, fundamental_hz=DISTORTION_FUNDAMENTAL_HZ
        )
        if harmonic_ratio < DISTORTION_HARMONIC_RATIO_MIN:
            return None

        # 7. Sustained density gate — streak must be at least 4s old.
        if self._density_streak_start is None:
            return None
        if now - self._density_streak_start < DISTORTION_KICK_DENSITY_SUSTAIN_S:
            return None

        # 8. ALL THREE gates pass — fire.
        self.chain_position += 1
        if harmonic_ratio > 0.0:
            distortion_db_raw = 20.0 * log10(harmonic_ratio)
        else:
            distortion_db_raw = _DISTORTION_DB_FLOOR
        distortion_db = max(distortion_db_raw, _DISTORTION_DB_FLOOR)

        ev = Event(
            "DISTORTION_CLIMB",
            state,
            extra={
                "chain_position": int(self.chain_position),
                "distortion_db": round(float(distortion_db), 2),
            },
        )
        self.last_event_at = now
        # Force fresh accumulation post-fire so the next event needs a new
        # 4-window flatness rise; otherwise a sustained-distortion track
        # would re-fire every 6s on the same tail-end flatness reading.
        self._flatness_history.clear()
        return ev
