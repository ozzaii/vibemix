# SPDX-License-Identifier: Apache-2.0
"""Phase 33 + Phase 40 — One-click install helpers.

Probes for system-level prerequisites (BlackHole 2ch on macOS) and
surfaces install affordances back to the wizard via the IPC bus.

Phase 40 / AUDIO-07 added structured-event emission on top of the
Phase 33 return-dict contract — re-exported here for downstream
imports (``from vibemix.install import probe_blackhole, emit_cta_fired``).
"""

from vibemix.install.blackhole_probe import (
    BLACKHOLE_INSTALL_URL,
    BlackHoleProbeResult,
    EmitEvent,
    emit_cta_fired,
    probe_blackhole,
)

__all__ = [
    "BLACKHOLE_INSTALL_URL",
    "BlackHoleProbeResult",
    "EmitEvent",
    "emit_cta_fired",
    "probe_blackhole",
]
