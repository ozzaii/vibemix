# SPDX-License-Identifier: Apache-2.0
"""TrackInfoBackend protocol — OS now-playing surface (title / artist / position).

Lifted from cohost_v3.py:518-541 (subprocess poll of nowplaying-cli on macOS — wraps the
private MediaRemote framework). Phase 3 macOS impl wraps nowplaying-cli; Phase 7 Windows
impl wraps SMTC (Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager).

Note: cohost_v3.py:1112-1133 derive_audible_track() — the cross-reference logic between
this surface and MIDI deck weights — belongs in the sensing layer (Phase 3), NOT this
Protocol. This surface is dumb: it reports what the OS reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class NowPlayingSnapshot:
    """OS now-playing surface snapshot. All fields best-effort.

    Backends MUST set unknown fields to None (not empty string) so callers can
    distinguish 'no track' from 'track with no title'.
    """

    title: str | None
    artist: str | None
    album: str | None
    duration_sec: float | None
    position_sec: float | None


@runtime_checkable
class TrackInfoBackend(Protocol):
    """OS now-playing firewall — synchronous best-effort poll.

    is_available() lets the caller skip impls that require missing helpers (e.g.
    nowplaying-cli not installed on macOS).
    """

    def is_available(self) -> bool: ...

    def poll(self) -> NowPlayingSnapshot | None:
        """Synchronous + blocking. Caller offloads to executor (POC pattern at
        cohost_v3.py:548). Returns None when no track is currently reported by the
        OS now-playing surface.
        """
        ...
