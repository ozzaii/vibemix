# SPDX-License-Identifier: Apache-2.0
"""AcidLineEntryDetector — TB-303-style acid bassline arrives mid-track.

Fires when BOTH conditions co-occur within a 3s evaluation window:
    1. Dominant frequency in [200, 800]Hz band traces a sweep with
       |slope| >= ``ACID_SWEEP_SLOPE_MIN_OCT_PER_S`` (0.2 oct/sec) over
       at least ``ACID_SWEEP_MIN_SPAN_S`` (1.5s) of history.
    2. Band resonance Q proxy (peak-to-mean magnitude) starts BELOW
       ``ACID_RESONANCE_LOW_MAX`` (3) and ends ABOVE
       ``ACID_RESONANCE_HIGH_MIN`` (8) over the same window — the
       characteristic "resonance creeping up" envelope of a 303 cutoff
       opening.

Anti-hallucination contract:
    - Silence gate FIRST.
    - audio_buf None → graceful no-op.
    - ``dominant_freq_in_band == 0.0`` (out-of-band guard tripped) →
      do NOT seed sweep history.
    - Both gates required — flat-tone + low-Q signals never fire.

Hard Tek genre gate: only inserted into the chain by
``build_hard_tek_chain``. Active genre IS the gate.

Payload:
    formant_hz  : float  # median dominant freq over the sweep window
    resonance_q : float  # peak Q during the sweep window

Cooldown: 8s (``MIN_EVENT_GAP_PER_TYPE["ACID_LINE_ENTRY"]``).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import numpy as np

from vibemix.audio.constants import (
    ACID_FORMANT_HIGH_HZ,
    ACID_FORMANT_LOW_HZ,
    ACID_RESONANCE_HIGH_MIN,
    ACID_RESONANCE_LOW_MAX,
    ACID_SNAPSHOT_WINDOW_S,
    ACID_SWEEP_MIN_SPAN_S,
    ACID_SWEEP_SLOPE_MIN_OCT_PER_S,
    ACID_SWEEP_WINDOW_S,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.detectors._dsp import (
    band_resonance_q,
    dominant_freq_in_band,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.music_state import MusicState

# Max history length — covers 3s @ 100ms tick cadence (30 entries) with
# generous headroom for variable cadence.
_HISTORY_MAXLEN: int = 64


class AcidLineEntryDetector:
    """Stateful detector — keeps rolling (t, freq) + (t, q) histories trimmed
    to the last ``ACID_SWEEP_WINDOW_S`` seconds.

    Fields are public-readable for tests + observability — never mutated
    by anything other than ``detect()``.
    """

    def __init__(self) -> None:
        self.last_event_at: float = 0.0
        self._freq_history: deque[tuple[float, float]] = deque(maxlen=_HISTORY_MAXLEN)
        self._q_history: deque[tuple[float, float]] = deque(maxlen=_HISTORY_MAXLEN)

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return ``Event("ACID_LINE_ENTRY", ...)`` on combined sweep + Q rise."""
        # 1. Silence gate — clear histories so a breakdown can't carry a
        #    stale sweep into the next audible tick.
        if state.rms < LOW_RMS:
            self._freq_history.clear()
            self._q_history.clear()
            return None

        if audio_buf is None:
            return None

        # 2. Cooldown gate.
        cooldown = MIN_EVENT_GAP_PER_TYPE["ACID_LINE_ENTRY"]
        if now - self.last_event_at < cooldown:
            return None

        # 3. Snapshot 1.5s of trailing audio + compute the two band features.
        n_samples = int(audio_buf._sr * ACID_SNAPSHOT_WINDOW_S)
        samples = audio_buf.snapshot(n_samples)
        if samples.size < audio_buf._sr * 0.5:
            # Cold-start: not enough audio yet.
            return None

        freq = dominant_freq_in_band(
            samples,
            audio_buf._sr,
            low_hz=ACID_FORMANT_LOW_HZ,
            high_hz=ACID_FORMANT_HIGH_HZ,
        )
        q = band_resonance_q(
            samples,
            audio_buf._sr,
            low_hz=ACID_FORMANT_LOW_HZ,
            high_hz=ACID_FORMANT_HIGH_HZ,
        )

        # 4. Out-of-band guard tripped → don't seed history (anti-
        #    hallucination — sweep that starts on a hi-hat is fake).
        if freq <= 0.0:
            return None

        self._freq_history.append((now, freq))
        self._q_history.append((now, q))

        # 5. Trim entries older than ACID_SWEEP_WINDOW_S so the slope +
        #    early/late Q split look at the same window.
        cutoff = now - ACID_SWEEP_WINDOW_S
        while self._freq_history and self._freq_history[0][0] < cutoff:
            self._freq_history.popleft()
        while self._q_history and self._q_history[0][0] < cutoff:
            self._q_history.popleft()

        # 6. Need enough points + enough time-span for a meaningful slope.
        if len(self._freq_history) < 8:
            return None
        first_t = self._freq_history[0][0]
        last_t = self._freq_history[-1][0]
        span = last_t - first_t
        if span < ACID_SWEEP_MIN_SPAN_S:
            return None

        # 7. Linear regression of log2(freq) vs t — slope in oct/sec.
        times = np.array([t for t, _ in self._freq_history], dtype=np.float64)
        freqs = np.array([f for _, f in self._freq_history], dtype=np.float64)
        # Guard against zero frequencies (shouldn't happen — out-of-band
        # guard above filters them — but defend the log).
        if np.any(freqs <= 0.0):
            return None
        log_freqs = np.log2(freqs)
        # np.polyfit returns [slope, intercept] for degree=1.
        slope_oct_per_s, _intercept = np.polyfit(times, log_freqs, 1)
        if abs(slope_oct_per_s) < ACID_SWEEP_SLOPE_MIN_OCT_PER_S:
            return None

        # 8. Resonance-rise envelope — split q_history in half, require
        #    early-low + late-high.
        q_vals = [q_v for _, q_v in self._q_history]
        mid = len(q_vals) // 2
        if mid < 2:
            return None
        early_min = min(q_vals[:mid])
        late_max = max(q_vals[mid:])
        if not (early_min < ACID_RESONANCE_LOW_MAX and late_max > ACID_RESONANCE_HIGH_MIN):
            return None

        # 9. All gates pass — fire.
        formant_hz = float(np.median(freqs))
        resonance_q = float(max(q_vals))
        ev = Event(
            "ACID_LINE_ENTRY",
            state,
            extra={
                "formant_hz": round(formant_hz, 1),
                "resonance_q": round(resonance_q, 2),
            },
        )
        self.last_event_at = now
        # Clear histories post-fire so the next event needs a fresh sweep.
        self._freq_history.clear()
        self._q_history.clear()
        return ev
