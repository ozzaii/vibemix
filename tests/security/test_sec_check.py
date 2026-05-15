# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-10 — sec_check boot banner + outbound sync.

The boot banner in ``runtime.sec_check`` is the single source of truth
for vibemix's privacy claim. SECURITY.md§Outbound endpoints mirrors it.
This test fails the build if the two surfaces drift.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

from vibemix.runtime import sec_check


REPO_ROOT = Path(__file__).resolve().parents[2]
SECURITY_MD = REPO_ROOT / "SECURITY.md"


# ---------------------------------------------------------------------------
# Banner behavior
# ---------------------------------------------------------------------------

def test_banner_default_telemetry_off():
    lines = sec_check.banner_lines(telemetry_on=False, version="0.1.0")
    joined = "\n".join(lines)
    assert "Telemetry: OFF" in joined
    assert "Telemetry: ON" not in joined


def test_banner_with_telemetry_on_lists_telemetry_endpoint():
    lines = sec_check.banner_lines(telemetry_on=True, version="0.1.0")
    joined = "\n".join(lines)
    assert "Telemetry: ON" in joined
    assert "telemetry.altidus.world" in joined


def test_banner_mentions_audio_midi_screen_local():
    lines = sec_check.banner_lines(telemetry_on=False, version="0.1.0")
    joined = "\n".join(lines)
    assert "Audio capture: local" in joined
    assert "MIDI input: local" in joined
    assert "Screen capture: local" in joined
    assert "never leaves machine" in joined


def test_print_security_banner_goes_to_stream():
    buf = io.StringIO()
    sec_check.print_security_banner(telemetry_on=False, version="0.1.0", stream=buf)
    out = buf.getvalue()
    assert "vibemix v0.1.0" in out
    assert "Telemetry: OFF" in out


def test_endpoint_urls_returns_full_inventory():
    urls = sec_check.endpoint_urls()
    assert "https://api.bravoh.altidus.world" in urls
    assert "https://api.altidus.world/vibemix/latest.json" in urls
    assert "https://telemetry.altidus.world/vibemix/v1/event" in urls


# ---------------------------------------------------------------------------
# Sync gate: banner ↔ SECURITY.md
# ---------------------------------------------------------------------------

URL_RE = re.compile(r"https?://[A-Za-z0-9./_\-]+")


def _security_md_outbound_urls() -> set[str]:
    """Extract URLs from the Outbound endpoints table in SECURITY.md."""
    text = SECURITY_MD.read_text(encoding="utf-8")
    # Slice the section between "## Outbound endpoints" and the next "##".
    start = text.find("## Outbound endpoints")
    assert start >= 0, "SECURITY.md must have a '## Outbound endpoints' section"
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    section = text[start:end]
    urls = set(URL_RE.findall(section))
    # Strip trailing punctuation.
    return {u.rstrip(".,;)") for u in urls}


def test_security_md_outbound_section_exists():
    text = SECURITY_MD.read_text(encoding="utf-8")
    assert "## Outbound endpoints" in text


def test_banner_outbound_list_matches_security_md():
    """Every endpoint in OUTBOUND_ENDPOINTS must appear in SECURITY.md and vice versa."""
    banner_urls = set(sec_check.endpoint_urls())
    md_urls = _security_md_outbound_urls()

    missing_in_md = banner_urls - md_urls
    missing_in_banner = md_urls - banner_urls

    assert not missing_in_md, (
        f"Endpoints in sec_check but NOT in SECURITY.md: {missing_in_md}. "
        "Update SECURITY.md§Outbound endpoints in the same PR."
    )
    assert not missing_in_banner, (
        f"Endpoints in SECURITY.md but NOT in sec_check: {missing_in_banner}. "
        "Update src/vibemix/runtime/sec_check.py in the same PR."
    )


def test_telemetry_endpoint_marked_opt_in():
    """The telemetry endpoint must carry the opt-in condition."""
    matches = [
        ep for ep in sec_check.OUTBOUND_ENDPOINTS if "telemetry" in ep.url
    ]
    assert len(matches) == 1
    assert matches[0].condition == "opt-in"


def test_no_unexpected_conditions():
    """Only the three documented conditions are allowed."""
    allowed = {"always", "opt-in", "user-click"}
    for ep in sec_check.OUTBOUND_ENDPOINTS:
        assert ep.condition in allowed, (
            f"Unknown condition {ep.condition!r} on {ep.url}"
        )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
