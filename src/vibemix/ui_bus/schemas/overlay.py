# SPDX-License-Identifier: Apache-2.0
"""Phase 24-02 — overlay-highlight diagnostics IPC payload struct.

OVERLAY-01: when the LLM emits a valid ``[screen:<element_id>]`` citation
AND the citation linter's action is ``emit`` (i.e. the user actually heard
the response — not stripped, not bypassed), the Python sidecar publishes
an ``ipc.session.overlay-highlight`` envelope on the ws bus. The Tauri
shell receives this and invokes the Rust ``show_overlay_highlight``
command, which queries djay Pro AX for the element's screen bounds and
opens a transparent click-through always-on-top WebviewWindow rendering
an amber ring CSS animation for ``duration_ms`` ms.

This module is the SINGLE SOURCE for the payload field set; the wrapper
class (``vibemix.ui_bus.messages.SessionOverlayHighlight``) imports
``SessionOverlayHighlightPayload`` from here, mirroring the
``schemas/<domain>.py`` subpackage layout the planner brief locked in
for Plan 20-04 (and reused here).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class SessionOverlayHighlightPayload:
    """Payload struct for the ``ipc.session.overlay-highlight`` IPC message.

    Fields:
        element_id: stable identifier from the 12-element djay Pro v5
            map (e.g. ``"waveform_a"``, ``"deck_a_low_eq"``). The Rust
            side ``djay_ax::query_element_bounds`` allowlists this against
            its known map; unknown ids are graceful no-ops.
        color: ring color token. Allowlisted to ``amber | red | green |
            blue`` to refuse arbitrary CSS color injection.
        duration_ms: total ring animation time in milliseconds (fade-in +
            hold + fade-out). Clamped to ``[0, 8000]`` to refuse runaway
            rings that would freeze on screen.
    """

    element_id: str
    color: Literal["amber", "red", "green", "blue"]
    duration_ms: int
