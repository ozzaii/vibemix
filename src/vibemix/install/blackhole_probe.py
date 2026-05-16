# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / INSTALL-03 + Phase 40 / AUDIO-07 — BlackHole 2ch CoreAudio probe.

Returns a structured dict the IPC layer can serialize back to the
wizard. The wizard renders an "Install BlackHole 2ch" affordance when
the probe reports the device is absent.

We accept any BlackHole variant (2ch / 16ch / 64ch) as "installed" —
they are functionally identical for vibemix's audio-routing surface;
only the channel count differs. The variant tag surfaces in the
diagnostic payload but the wizard only branches on the boolean
``installed`` flag.

The probe never raises. If ``sounddevice.query_devices()`` itself
fails (no audio backend, permissions revoked mid-poll, etc.), we
return ``installed=False`` with ``device_name=None`` and the caller
gracefully advances with a warning.

Phase 40 / AUDIO-07 extensions
------------------------------

The probe gained two optional behaviors on top of the Phase 33 return
contract — both purely additive (legacy `probe_blackhole()` with no
args still returns the same dict):

1. **Structured-event emission** via an optional ``emit_event`` callable.
   When passed, the probe emits ``audio.probe.detected`` (with the
   detected device name) or ``audio.probe.missing`` (with a null
   device name) reflecting the final outcome. A sibling helper
   ``emit_cta_fired`` emits ``audio.probe.cta_fired`` when the wizard
   layer dispatches the install-link CTA. Emit failures are swallowed
   (try/except wrapper) — telemetry must never crash the probe.

2. **Pitfall 5 retry** — on a fresh boot, ``sounddevice.query_devices``
   can return the partial CoreAudio list before BlackHole is
   enumerated, even when it IS installed. When the first probe returns
   ``installed=False`` and ``retry_on_missing=True`` (default), we
   sleep 1.5s and re-query once before emitting ``audio.probe.missing``.
   Only ONE event is emitted regardless of retry path (based on the
   final outcome). Tests pass ``retry_on_missing=False`` to keep
   runtime fast.

Wiring contract (left for the wizard owner — not in Plan 40-06)
---------------------------------------------------------------

The Phase 40 plan exposes the hooks but does NOT wire them. The wizard
or sidecar entry point owns the ``VoiceRecorder`` instance and adapts
its ``log_event(kind, **fields)`` signature into the ``emit_event``
shape::

    emit_event = lambda name, payload: recorder.log_event(name, **payload)
    result = probe_blackhole(emit_event=emit_event)
    if not result["installed"]:
        # surface install CTA in UI, then on user click:
        emit_cta_fired(emit_event)

That adapter wrap lives in v3.0 Phase 45 / SHIP-04 (INSTALL-VM-RUN) or
the existing Phase 33 install-wizard module.
"""

from __future__ import annotations

import time
from typing import Any, Callable, TypedDict


class BlackHoleProbeResult(TypedDict):
    installed: bool
    device_name: str | None


# AUDIO-07 — emit_event callable shape.
# ``name`` is the event kind (one of the three ``audio.probe.*`` names);
# ``payload`` is a free-form dict. The wizard wraps its
# ``VoiceRecorder.log_event(kind, **fields)`` into this shape via
# ``lambda name, payload: recorder.log_event(name, **payload)``.
EmitEvent = Callable[[str, dict], None]


def _query_devices() -> list[dict[str, Any]]:
    """Indirection point — tests monkeypatch ``sounddevice.query_devices``
    via the existing ``mock_sounddevice`` fixture. Returns an empty list
    when the import or query fails."""
    try:
        import sounddevice as sd  # local import — keep module import-safe
    except Exception:
        return []
    try:
        devices = sd.query_devices()
    except Exception:
        return []
    # sounddevice can return a single dict (one device), a list, or a
    # DeviceList; normalize to a plain list of dicts.
    if isinstance(devices, dict):
        return [devices]
    try:
        return list(devices)
    except Exception:
        return []


def _probe_once() -> BlackHoleProbeResult:
    """Single-shot probe — substring match on the device-list ``name`` field.

    Extracted from the original ``probe_blackhole`` body verbatim so the
    Pitfall 5 retry path can reuse it without duplicating the query +
    match logic.
    """
    for entry in _query_devices():
        name = entry.get("name")
        if isinstance(name, str) and "BlackHole" in name:
            return {"installed": True, "device_name": name}
    return {"installed": False, "device_name": None}


def _safe_emit(emit_event: EmitEvent | None, name: str, payload: dict) -> None:
    """Emit + swallow. Telemetry must never crash the probe (disk-full
    VoiceRecorder, broken IPC channel, etc.). T-40-06-01 mitigation."""
    if emit_event is None:
        return
    try:
        emit_event(name, payload)
    except Exception:
        # Intentional: emit failures are non-fatal. We do NOT re-raise,
        # log, or report — the probe's job is to return a dict, not to
        # surface telemetry failures upstream.
        pass


def probe_blackhole(
    emit_event: EmitEvent | None = None,
    *,
    retry_on_missing: bool = True,
) -> BlackHoleProbeResult:
    """Probe CoreAudio for a BlackHole device.

    Args:
        emit_event: Optional callable taking ``(name, payload)`` — when
            present, the probe emits exactly one ``audio.probe.detected``
            or ``audio.probe.missing`` event reflecting the final
            outcome. Emit failures are swallowed.
        retry_on_missing: When True (default), a first-call
            ``installed=False`` triggers a single 1.5s sleep + re-query
            (Pitfall 5 — CoreAudio fresh-boot race defense). Tests pass
            ``False`` to keep runtime fast.

    Returns:
        ``{"installed": bool, "device_name": str | None}`` — the
        original Phase 33 contract. ``installed`` is True iff at least
        one device name contains the case-sensitive substring
        ``"BlackHole"``; ``device_name`` is the first matching name,
        or None.
    """
    result = _probe_once()
    if not result["installed"] and retry_on_missing:
        # Pitfall 5 — CoreAudio race on fresh boot. The first probe
        # may have arrived before sounddevice/PortAudio finished its
        # initial device enumeration; a single 1.5s pause is the
        # RESEARCH-recommended mitigation (matches the same race that
        # bit Phase 33-04). We only retry once — repeated misses are
        # real misses, not a race.
        time.sleep(1.5)
        result = _probe_once()

    # Single emission, based on the final (post-retry) outcome.
    if result["installed"]:
        _safe_emit(
            emit_event,
            "audio.probe.detected",
            {"device_name": result["device_name"]},
        )
    else:
        _safe_emit(
            emit_event,
            "audio.probe.missing",
            {"device_name": None},
        )
    return result


# Public install URL — opens in the OS default browser via the Tauri
# shell.open command. The capability allowlist already permits
# https://existential.audio/blackhole.
BLACKHOLE_INSTALL_URL = "https://existential.audio/blackhole/"


def emit_cta_fired(
    emit_event: EmitEvent,
    cta: str = "blackhole_install_link_opened",
) -> None:
    """Emit ``audio.probe.cta_fired`` when the wizard dispatches the
    install-link CTA.

    The wizard calls this once per user-click on the "Install
    BlackHole" affordance; the payload carries the CTA identifier and
    the URL the user was sent to. Emit failures are swallowed (same
    contract as ``probe_blackhole`` — telemetry must never crash the
    install flow).

    Args:
        emit_event: Callable taking ``(name, payload)``. Same shape as
            ``probe_blackhole``'s ``emit_event``.
        cta: Identifier for which CTA fired. Defaults to
            ``"blackhole_install_link_opened"``; future surfaces (e.g.
            in-app "retry probe" button) can pass their own tag.
    """
    _safe_emit(
        emit_event,
        "audio.probe.cta_fired",
        {"cta": cta, "url": BLACKHOLE_INSTALL_URL},
    )
