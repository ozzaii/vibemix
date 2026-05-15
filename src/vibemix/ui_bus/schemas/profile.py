# SPDX-License-Identifier: Apache-2.0
"""Phase 32 — profile-domain IPC payload structs.

Same convention as ``library.py`` / ``debrief.py`` — frozen, slotted
dataclasses imported by ``vibemix.ui_bus.messages``. No pydantic
(D-Area-4.4); validation runs through jsonschema at the envelope boundary.

Five payload types ship in Phase 32:

- ``ProfileSetConsentPayload`` — shell → sidecar. Toggle profile_consent.
- ``ProfileConsentStatePayload`` — sidecar → shell. Reflects current state.
- ``ProfileViewResultPayload`` — sidecar → shell. Current profile + byte count.
- ``ProfileRegenerateResultPayload`` — sidecar → shell. ok / new profile / error.
- ``ProfileDeleteAckPayload`` — sidecar → shell. ok / error.

Pitfall P51 + P53 + P60 are addressed in the builder/cache/agent layers;
this module is the wire shape only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfileSetConsentPayload:
    """Shell → sidecar. Persists profile_consent to state.json.

    Wizard's profile-consent step + Settings → Profile panel both emit
    this. Default-OFF is enforced at the producer side; the sidecar honors
    whatever boolean arrives.
    """

    consent: bool


@dataclass(frozen=True, slots=True)
class ProfileConsentStatePayload:
    """Sidecar → shell. Current profile_consent from disk."""

    consent: bool


@dataclass(frozen=True, slots=True)
class ProfileViewResultPayload:
    """Sidecar → shell. Snapshot of the on-disk profile + envelope size.

    Fields:
        profile: parsed profile dict, or ``None`` if absent / consent OFF.
        bytes: UTF-8 byte length of the serialized profile (0 when None).
        consent: current profile_consent state (so the UI can render the
            consent-off empty state without a second request).
    """

    profile: dict | None
    bytes: int
    consent: bool


@dataclass(frozen=True, slots=True)
class ProfileRegenerateResultPayload:
    """Sidecar → shell. Reply to ipc.profile.regenerate.

    Fields:
        ok: True iff a new profile was built AND saved.
        profile: the new profile dict (when ok), else ``None``.
        error: short reason string when ok=False (e.g. ``"consent_off"``,
            ``"insufficient_evidence"``). Truncated to ≤200 chars at the
            handler boundary.
    """

    ok: bool
    profile: dict | None
    error: str | None


@dataclass(frozen=True, slots=True)
class ProfileDeleteAckPayload:
    """Sidecar → shell. Reply to ipc.profile.delete."""

    ok: bool
    error: str | None
