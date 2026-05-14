# SPDX-License-Identifier: Apache-2.0
"""vibemix.coach — Phase 20 anti-slop chokepoint package.

Houses the citation grounding linter (``CitationLinter`` + ``LintResult``),
the rolling-window stripped-rate telemetry guard
(``StrippedRateTracker``), and the four locked tolerance / threshold
constants. ``DJCoHostAgent.llm_node`` wires all of these into the post-
stream gate — see Plan 20-01 Task 2 for the integration shape.
"""

from __future__ import annotations

from vibemix.coach.citation_ipc_shim import CitationIpcShim
from vibemix.coach.citation_linter import CitationLinter, LintResult
from vibemix.coach.constants import (
    DEBRIEF_TOLERANCE_S,
    LIVE_TOLERANCE_S,
    STRIPPED_RATE_THRESHOLD,
    STRIPPED_RATE_WINDOW_S,
)
from vibemix.coach.prompt_fragments import FAIL_SOFT_EXAMPLES, IM_LISTENING_FRAGMENT
from vibemix.coach.stripped_rate import StrippedRateTracker

__all__ = [
    "CitationIpcShim",
    "CitationLinter",
    "DEBRIEF_TOLERANCE_S",
    "FAIL_SOFT_EXAMPLES",
    "IM_LISTENING_FRAGMENT",
    "LIVE_TOLERANCE_S",
    "LintResult",
    "STRIPPED_RATE_THRESHOLD",
    "STRIPPED_RATE_WINDOW_S",
    "StrippedRateTracker",
]
