# SPDX-License-Identifier: Apache-2.0
"""Display helpers for live drop countdown surfaces."""

from __future__ import annotations

import math


def predicted_drop_bars(predicted_drop_in_sec: object, bpm: object) -> int | None:
    """Convert a second-level drop estimate into whole 4-beat bars.

    The runtime only shows the drop chip when both the prediction and BPM are
    finite. Returning ``None`` keeps the UI silent instead of implying a lock.
    """

    try:
        seconds = float(predicted_drop_in_sec)  # type: ignore[arg-type]
        bpm_value = float(bpm)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    if (
        not math.isfinite(seconds)
        or not math.isfinite(bpm_value)
        or seconds < 0.0
        or bpm_value <= 0.0
    ):
        return None

    seconds_per_bar = 240.0 / bpm_value
    return max(0, math.ceil(seconds / seconds_per_bar))
