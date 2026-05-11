# SPDX-License-Identifier: Apache-2.0
"""VocalDetector — band/onset heuristics + 1.5s in / 2.5s out hysteresis.

Phase 6 Wave 2. Heuristics from 06-CONTEXT.md §Vocal-Section Detector — any
2 of 3 rules → "above threshold":

    rule1 (mid dominance):
        features['mid_share'] > 0.45 AND mid sustained over last 3 snapshots
    rule2 (rising onsets):
        onsets_per_sec strictly increasing over last 3 snapshots
        (vocal phrasing surfaces as accelerating onset density)
    rule3 (vocal sits above sub-bass):
        features['high_share'] > 0.20 AND features['sub_share'] < 0.30

Hysteresis: 1.5s sustained above-threshold to flip True. 2.5s sustained
below-threshold to flip back to False. Brief dips do NOT toggle the state
(critical to prevent flicker mid-vocal-phrase). Implementation tracks the
timestamps of the last-seen-above and last-seen-below transitions.

The ``profile`` parameter is accepted but unused in v1 — reserved for future
per-genre threshold tuning (a D&B vocal section sits at different band
ratios than a pop chorus). Heuristics are genre-agnostic for v1.
"""

from __future__ import annotations

import time

from vibemix.state.genre.profile import GenreProfile


class VocalDetector:
    """Hysteresis-bounded vocal-section detector.

    Caller invokes ``is_vocal_section(features, recent_features, now=t)`` once
    per state-refresh tick (10Hz). Internal state mutates only inside that
    method; the returned bool is the CURRENT vocal_active label after the
    hysteresis update.
    """

    def __init__(
        self,
        profile: GenreProfile | None = None,
        *,
        in_dwell_sec: float = 1.5,
        out_dwell_sec: float = 2.5,
        mid_share_threshold: float = 0.45,
        high_share_threshold: float = 0.20,
        sub_share_ceiling: float = 0.30,
    ):
        self.profile = profile  # reserved for v2 per-genre tuning; unused in v1
        self.in_dwell_sec = in_dwell_sec
        self.out_dwell_sec = out_dwell_sec
        self.mid_thr = mid_share_threshold
        self.high_thr = high_share_threshold
        self.sub_ceil = sub_share_ceiling
        # Hysteresis state:
        self._active: bool = False
        self._above_since: float | None = None
        self._below_since: float | None = None

    def is_vocal_section(
        self,
        features: dict,
        recent_features: list[dict],
        *,
        now: float | None = None,
    ) -> bool:
        """Returns the CURRENT vocal_active boolean after applying hysteresis.

        ``recent_features`` is the last ~5 snapshots (oldest first). ``now``
        defaults to time.time().
        """
        if now is None:
            now = time.time()

        # rule1 — mid dominance sustained over current + last 2 snapshots.
        # 06-CONTEXT specifies 2s sustained at 10Hz; we approximate via the
        # available 5-deep history. Require all-of-(current + last 2) >= mid_thr.
        mid_current = features.get("mid_share", 0.0)
        tail_mids = [r.get("mid_share", 0.0) for r in recent_features[-2:]]
        sustained_mids = [mid_current, *tail_mids]
        if len(sustained_mids) >= 3:
            rule1 = all(v >= self.mid_thr for v in sustained_mids)
        else:
            # Not enough history → require only current (avoids cold-start
            # blocking the rule entirely; recents accumulate over ~3 ticks).
            rule1 = False

        # rule2 — rising onset trend over last 3 snapshots (recent_features
        # last 2 + current). Strict monotonic climb.
        onset_seq = [r.get("onsets_per_sec", 0.0) for r in recent_features[-2:]] + [
            features.get("onsets_per_sec", 0.0)
        ]
        if len(onset_seq) >= 3:
            rule2 = onset_seq[-1] > onset_seq[-2] > onset_seq[-3]
        else:
            rule2 = False

        # rule3 — vocals sit above sub-bass.
        rule3 = (
            features.get("high_share", 0.0) > self.high_thr
            and features.get("sub_share", 0.0) < self.sub_ceil
        )

        above_threshold = (int(rule1) + int(rule2) + int(rule3)) >= 2

        # Hysteresis update — the only state mutation.
        if above_threshold:
            self._below_since = None
            if self._above_since is None:
                self._above_since = now
            if not self._active and (now - self._above_since) >= self.in_dwell_sec:
                self._active = True
        else:
            self._above_since = None
            if self._below_since is None:
                self._below_since = now
            if self._active and (now - self._below_since) >= self.out_dwell_sec:
                self._active = False

        return self._active
