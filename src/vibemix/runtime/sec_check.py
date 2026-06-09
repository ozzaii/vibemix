# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-10 — auditable privacy claim, boot banner.

On every vibemix startup we print a short security-posture banner to
stderr describing:

  - What local-only data we touch (audio, MIDI, screen).
  - The closed list of outbound endpoints.
  - Current telemetry state (OFF or ON-with-consent).

This is the **single source of truth** for the privacy claim that
SECURITY.md§Outbound endpoints mirrors. The CI test
``tests/security/test_sec_check.py`` parses both surfaces and fails
the build on drift.

Why a banner and not a doc-only claim? Because the user can verify on
launch — they don't need to trust SECURITY.md to read the same thing
the binary itself prints. This closes the "claims vs. reality" gap.

This module imports cleanly with no side effects. Call
``print_security_banner()`` from ``__main__`` (or any wrapper) to
emit the banner.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Canonical outbound endpoint inventory.
#
# Every entry MUST mirror the table in SECURITY.md§Outbound endpoints.
# Reordering or rewording requires an update to BOTH files in the same
# commit; the CI test parses both and diffs them.
#
# Format: tuple (endpoint, description, condition).
#
# Conditions:
#   "brain"      — the live reaction-planning LLM. Exactly ONE of the two
#                  brain endpoints is active per launch (llm_mode: proxy is
#                  the fresh-install default; direct needs the user's own
#                  GEMINI_API_KEY). Every reaction request to the active
#                  brain carries short master-output audio snapshots, plus
#                  the booth mic while the user is speaking to Sven — this
#                  is the one place raw audio leaves the machine.
#   "always"     — reachable whenever the app is running (no audio).
#   "user-click" — shell-out only, on an explicit click.
#   "opt-in"     — only after the user toggles telemetry consent ON.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OutboundEndpoint:
    url: str
    purpose: str
    condition: str  # "brain" | "always" | "opt-in" | "user-click"


OUTBOUND_ENDPOINTS: tuple[OutboundEndpoint, ...] = (
    OutboundEndpoint(
        # Must match the code's actual default — VIBEMIX_PROXY_BASE_URL
        # defaults to https://api.altidus.world in __main__.main().
        url="https://api.altidus.world",
        purpose="Bravoh proxy — Gemini reaction planning, receives audio snapshots (default mode)",
        condition="brain",
    ),
    OutboundEndpoint(
        url="https://generativelanguage.googleapis.com",
        purpose="Google Gemini — reaction planning, receives audio snapshots (direct mode, your own GEMINI_API_KEY)",
        condition="brain",
    ),
    OutboundEndpoint(
        url="https://api.altidus.world/vibemix/latest.json",
        purpose="Updater manifest (~once/day)",
        condition="always",
    ),
    OutboundEndpoint(
        url="https://github.com/bravoh-ai/vibemix",
        purpose="User click in settings (shell-out)",
        condition="user-click",
    ),
    OutboundEndpoint(
        url="https://existential.audio/blackhole",
        purpose="User click in wizard install hint (shell-out)",
        condition="user-click",
    ),
    OutboundEndpoint(
        url="https://telemetry.altidus.world/vibemix/v1/event",
        purpose="Anonymous diagnostics — only when consent toggled ON",
        condition="opt-in",
    ),
)


def banner_lines(telemetry_on: bool, version: str = "unknown") -> list[str]:
    """Return the banner as a list of lines (test-friendly)."""
    lines: list[str] = []
    lines.append(f"vibemix v{version} — privacy posture")
    lines.append(
        "  Audio capture: local (BlackHole / Loopback); live-session reaction "
        "snapshots (master output + mic while you speak to Sven) are sent to "
        "the active brain endpoint below"
    )
    lines.append("  MIDI input: local (USB) — raw MIDI never leaves machine; detected moves reach the brain as text")
    lines.append("  Screen capture: local (macOS Quartz / Win SCK) — pixels never leave machine; track titles reach the brain as text")
    lines.append("  Brain endpoint (ONE active per launch, by llm mode — receives the audio snapshots):")
    for ep in OUTBOUND_ENDPOINTS:
        if ep.condition == "brain":
            lines.append(f"    - {ep.url}  [{ep.purpose}]")
    lines.append("  Network out (always):")
    for ep in OUTBOUND_ENDPOINTS:
        if ep.condition == "always":
            lines.append(f"    - {ep.url}  [{ep.purpose}]")
    lines.append("  Network out (user-click only):")
    for ep in OUTBOUND_ENDPOINTS:
        if ep.condition == "user-click":
            lines.append(f"    - {ep.url}  [{ep.purpose}]")
    if telemetry_on:
        lines.append("  Telemetry: ON (user opted in)")
        for ep in OUTBOUND_ENDPOINTS:
            if ep.condition == "opt-in":
                lines.append(f"    - {ep.url}  [{ep.purpose}]")
    else:
        lines.append("  Telemetry: OFF")
    return lines


def print_security_banner(
    telemetry_on: bool = False,
    version: str = "unknown",
    stream=sys.stderr,
) -> None:
    """Emit the banner to stderr (or test-supplied stream).

    Stderr is the right channel: it's visible in CLI launches, terminal
    sidecar output, and the macOS console.app sidecar log. We deliberately
    do not write to stdout so a piped audio pass-through never accidentally
    catches the banner.
    """
    for line in banner_lines(telemetry_on=telemetry_on, version=version):
        print(line, file=stream)


def endpoint_urls() -> list[str]:
    """Just the URLs — used by SECURITY.md sync test."""
    return [ep.url for ep in OUTBOUND_ENDPOINTS]


__all__ = [
    "OUTBOUND_ENDPOINTS",
    "OutboundEndpoint",
    "banner_lines",
    "endpoint_urls",
    "print_security_banner",
]
