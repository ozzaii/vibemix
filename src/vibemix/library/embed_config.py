# SPDX-License-Identifier: Apache-2.0
"""Backend-neutral embedding strategy constants."""

from __future__ import annotations

# Strategy names shared by the local CLAP embedder and legacy migration tests.
EMBED_STRATEGIES = ("mean_excerpt", "cue_anchored")
DEFAULT_EMBED_STRATEGY = "mean_excerpt"

# Cache-key namespace for cue-anchored vectors. Distinct from legacy excerpt
# strategy versions so cue rows never collide with plain mean-excerpt rows.
# v2: the cue-window slicer moved from an ffmpeg-binary 128k mp3 re-encode to
# a direct PyAV decode — slice bytes changed, so v1 cue rows must retire. The
# mean_excerpt whole-file path never shelled out and keeps its tag untouched.
CUE_ANCHORED_STRATEGY_VERSION = "v2-cueanchored-mean-pyav"

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
