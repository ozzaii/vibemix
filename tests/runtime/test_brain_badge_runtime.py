# SPDX-License-Identifier: Apache-2.0
"""The gemini badge must reflect RUNTIME brain health, not stay constant-ok.

Source contract for main()'s closure wiring (the badge path is
_is_brain_configured → _DynamicBool → ws_broadcast status tick, ws_bus:1498).
Behavioral coverage of the accessor itself lives in
tests/agent/test_dj_cohost.py::test_brain_runtime_down_reason_tracks_outage_oneshots;
the live end-to-end gate is tests/test_main_smoke.py::test_main_03 (proxy
failure at Start prints the actionable hint).
"""

from __future__ import annotations

from pathlib import Path

_SRC = Path("src/vibemix/__main__.py").read_text(encoding="utf-8")


def test_status_badge_reads_live_agent_runtime_health() -> None:
    assert 'live_brain_agent: dict[str, Any] = {"agent": None}' in _SRC
    assert 'live_brain_agent["agent"] = agent' in _SRC
    assert 'live_brain_agent["agent"] = None' in _SRC
    assert "brain_runtime_down_reason()" in _SRC
    # Idle ≠ fault: with no live agent parked, the boot-config read stays the
    # final word (pin shared with tests/test_main_smoke.py:1242).
    assert "return brain_unavailable_reason is None" in _SRC


def test_proxy_setup_failure_logs_actionable_brain_hint() -> None:
    assert '_log_brain_unavailable(f"proxy setup failed: {exc}")' in _SRC
