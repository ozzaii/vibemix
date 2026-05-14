# SPDX-License-Identifier: Apache-2.0
"""Phase 20 anti-slop constants — locked floats, no enum, no dataclass.

Each constant is the ground-truth source for downstream imports
(``vibemix.coach.citation_linter``, ``vibemix.coach.stripped_rate``,
``vibemix.agent.dj_cohost``). Any change here is a breaking-contract change
and MUST be reflected in 20-CONTEXT.md + a new SUMMARY entry.
"""

from __future__ import annotations

# Live-mode citation timestamp tolerance band (CONTEXT D-Pitfall-18).
# A cited @t is valid iff some registry observation lies within ±this many
# seconds. Boundary INCLUSIVE — see test_boundary_tolerance_inclusive.
LIVE_TOLERANCE_S = 1.0

# Debrief-mode tolerance — wider band tolerates the post-session cursor
# drift Phase 25 (pyrekordbox import / debrief replay) introduces. Defined
# here as the architectural slot; v2.0 has no path that uses it.
DEBRIEF_TOLERANCE_S = 2.0

# Stripped-rate one-shot-bypass threshold (CONTEXT D-Telemetry-Guard).
# When the rolling-window rate of stripped responses exceeds this, the next
# response bypasses the linter exactly once and emits with an
# ``[unverified]`` audit row. Closes T-20-01-02 (silence-streak DoS).
STRIPPED_RATE_THRESHOLD = 0.4

# Rolling window for the stripped-rate calculation, in seconds (CONTEXT
# D-Telemetry-Guard). 15s matches the cohost_v4 short-term reaction horizon
# — long enough to smooth single-turn noise, short enough that recovery
# re-arms the bypass quickly.
STRIPPED_RATE_WINDOW_S = 15.0
