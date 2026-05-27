# SPDX-License-Identifier: Apache-2.0
"""Backend-neutral embedding strategy constants."""

from __future__ import annotations

# Strategy names shared by the local CLAP embedder and legacy migration tests.
EMBED_STRATEGIES = ("mean_excerpt", "cue_anchored")
DEFAULT_EMBED_STRATEGY = "mean_excerpt"

# Cache-key namespace for cue-anchored vectors. Distinct from legacy excerpt
# strategy versions so cue rows never collide with plain mean-excerpt rows.
CUE_ANCHORED_STRATEGY_VERSION = "v1-cueanchored-mean"

# Cue windows are capped at 80 seconds for both local CLAP and the legacy path.
CUE_WINDOW_SECONDS = 80
MAX_CUES_PER_TRACK = 4

__all__ = [
    "CUE_ANCHORED_STRATEGY_VERSION",
    "CUE_WINDOW_SECONDS",
    "DEFAULT_EMBED_STRATEGY",
    "EMBED_STRATEGIES",
    "MAX_CUES_PER_TRACK",
]
