# SPDX-License-Identifier: Apache-2.0
"""main() must feed the snapshot's run_state from the live lifecycle slots —
the field the shell reconciles its optimistic data-runstate against."""

from __future__ import annotations

from pathlib import Path


def test_main_wires_session_running_probe_into_ws_broadcast() -> None:
    src = Path("src/vibemix/__main__.py").read_text(encoding="utf-8")
    assert "def _is_session_graph_engaged() -> bool:" in src
    assert "session_running=_DynamicBool(_is_session_graph_engaged)" in src
