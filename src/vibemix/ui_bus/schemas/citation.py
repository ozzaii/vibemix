# SPDX-License-Identifier: Apache-2.0
"""Phase 20-04 — citation diagnostics IPC payload struct.

GROUND-06 + 20-CONTEXT D-Bypass-Audit-Surface: surface the linter's
``slop_ratio`` (cumulative stripped/total) + 15s rolling stripped rate +
the last-unverified-response text + the live ``bypass_active`` flag to
the Tauri Settings → Diagnostics drawer so Kaan can SEE the anti-slop
contract working in real time.

This module is the SINGLE SOURCE for the payload field set; the wrapper
class (``vibemix.ui_bus.messages.SessionCitation``) imports
``SessionCitationPayload`` from here, mirroring the
``schemas/<domain>.py`` subpackage layout the planner brief locked in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionCitationPayload:
    """Payload struct for the ``ipc.session.citation`` IPC message.

    Fields:
        slop_ratio: cumulative stripped/total ratio in ``[0, 1]``.
        stripped_rate_15s: 15-second rolling stripped rate in ``[0, 1]``.
        last_unverified_response: the most recent response text the linter
            stripped or bypass-blocked; ``None`` when nothing has been
            stripped yet this session.
        bypass_active: ``True`` when the bypass guard is currently
            silencing model output (per Plan 20-02 StrippedRateTracker).
    """

    slop_ratio: float
    stripped_rate_15s: float
    last_unverified_response: str | None
    bypass_active: bool
