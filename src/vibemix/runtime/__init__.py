# SPDX-License-Identifier: Apache-2.0
"""vibemix.runtime — asyncio runtime loops.

Coach event pump (10Hz event polling + AI reaction firing), terminal diag
meter (1Hz), and WebSocket mascot bus (30Hz outbound + inbound manual
trigger). Verbatim ports of cohost_v4.py:1754-1918 with one structural
change: the v4 ``_HAS_WS`` feature flag is dropped because ``websockets``
is now an explicit pyproject dep (Phase 2 already declared it). On import
failure the program fails loud — no silent degradation (Phase 2 PATTERNS
§AntiPatterns-2).

These three loops run alongside ``state_refresh_loop`` (Phase 3) and the
audio I/O streams (Phase 2) inside ``__main__.py`` (plan 04-04). All three
are pure asyncio with no audio/sounddevice touchpoints.
"""

from __future__ import annotations

from vibemix.runtime.coach import coach_loop
from vibemix.runtime.diag import diag_loop
from vibemix.runtime.session_loop import SessionLoop, run_session
from vibemix.runtime.wizard import WizardLoop, run_wizard
from vibemix.runtime.ws_bus import ws_broadcast

__all__ = [
    "SessionLoop",
    "WizardLoop",
    "coach_loop",
    "diag_loop",
    "run_session",
    "run_wizard",
    "ws_broadcast",
]
