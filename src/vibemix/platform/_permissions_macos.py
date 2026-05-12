# SPDX-License-Identifier: Apache-2.0
"""macOS permission probes for the Phase 11 calibration wizard.

Owns the AVFoundation + Quartz imports required to read the user's current
TCC grants. The platform firewall (Phase 1) allows underscore-prefixed
concrete impl modules to import OS-specific packages directly — this module
is one of them.

Two read-only probes + one prompt-trigger:
  - ``check_microphone_permission()`` returns the live
    ``AVAuthorizationStatusForMediaType(AVMediaTypeAudio)`` mapped to the
    schema's ``{authorized, denied, notDetermined, restricted}`` enum.
  - ``check_screen_recording_permission()`` returns
    ``CGPreflightScreenCaptureAccess()`` as ``authorized`` (bool True) or
    ``denied`` (False).
  - ``request_microphone_permission()`` triggers the macOS Mic dialog via
    ``AVCaptureDevice.requestAccessForMediaType:completionHandler:``. The
    sidecar polls ``check_microphone_permission()`` after the dialog is
    dismissed (the completion-handler is fire-and-forget; the wizard's
    1-Hz poll picks up the new state).

Imports are deferred into function bodies (NOT module-top) so this module
is cheap to import on Windows or in test environments without pyobjc.
That also keeps the Phase 1 firewall sane — ``vibemix.platform.permissions``
selector imports this module unconditionally on darwin without dragging
AVFoundation into win32 test runs.
"""

from __future__ import annotations

from typing import Literal

PermissionStatus = Literal["authorized", "denied", "notDetermined", "restricted"]


def check_microphone_permission() -> PermissionStatus:
    """Return the live AVCaptureDevice authorization status for audio.

    Mapping (per AVFoundation header):
        0 = notDetermined  → first launch, dialog not yet shown
        1 = restricted     → MDM / parental controls blocked it
        2 = denied         → user said no
        3 = authorized     → granted

    Any unexpected value is mapped to ``denied`` (fail-safe).
    """
    # Deferred import — pyobjc-framework-AVFoundation is a darwin dep.
    from AVFoundation import (  # type: ignore[import-not-found]
        AVCaptureDevice,
        AVMediaTypeAudio,
    )

    status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
    return {
        0: "notDetermined",
        1: "restricted",
        2: "denied",
        3: "authorized",
    }.get(int(status), "denied")


def check_screen_recording_permission() -> PermissionStatus:
    """Return the live CGPreflightScreenCaptureAccess status.

    macOS doesn't expose a four-state value for screen recording — it's a
    bool gate. We map ``True → "authorized"`` and ``False → "denied"`` so
    the UI can render the same enum across both permission cards.

    Note: this call is NON-prompting (the "preflight" variant). Calling
    ``CGRequestScreenCaptureAccess`` would surface the system dialog; we
    avoid it in the wizard probe because the Step 1 UI flows the user to
    System Settings via the apple-systempreferences deep-link instead.
    """
    import Quartz  # type: ignore[import-not-found]

    return "authorized" if Quartz.CGPreflightScreenCaptureAccess() else "denied"


def request_microphone_permission() -> None:
    """Trigger the macOS Microphone dialog. Non-blocking.

    The completion handler is a no-op — the wizard's 1-Hz permission poll
    will pick up the new state after the dialog is dismissed. We don't
    need to drive an async result back because the handler runs on a
    background grand-central-dispatch queue; bridging it to asyncio is
    more machinery than the poll loop deserves.
    """
    from AVFoundation import (  # type: ignore[import-not-found]
        AVCaptureDevice,
        AVMediaTypeAudio,
    )

    AVCaptureDevice.requestAccessForMediaType_completionHandler_(
        AVMediaTypeAudio, lambda _granted: None
    )


__all__ = [
    "PermissionStatus",
    "check_microphone_permission",
    "check_screen_recording_permission",
    "request_microphone_permission",
]
