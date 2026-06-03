# SPDX-License-Identifier: Apache-2.0
"""Per-instance websocket port overrides for headless QA fan-out."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _port_snapshot(*, ws_port: str | None, debrief_port: str | None) -> dict[str, int]:
    repo = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    if ws_port is None:
        env.pop("VIBEMIX_WS_PORT", None)
    else:
        env["VIBEMIX_WS_PORT"] = ws_port
    if debrief_port is None:
        env.pop("VIBEMIX_DEBRIEF_PORT", None)
    else:
        env["VIBEMIX_DEBRIEF_PORT"] = debrief_port
    src = str(repo / "src")
    existing_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing_path else src + os.pathsep + existing_path

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from vibemix.audio import WS_PORT as audio_ws; "
                "from vibemix.runtime import ws_bus; "
                "from vibemix.__main__ import DEBRIEF_PORT; "
                "print(json.dumps({'audio_ws': audio_ws, 'ws_bus': ws_bus.WS_PORT, "
                "'debrief': DEBRIEF_PORT}, sort_keys=True))"
            ),
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_runtime_ports_default_to_cardinal_ports() -> None:
    assert _port_snapshot(ws_port=None, debrief_port=None) == {
        "audio_ws": 8765,
        "ws_bus": 8765,
        "debrief": 8766,
    }


def test_runtime_ports_can_be_overridden_per_process() -> None:
    assert _port_snapshot(ws_port="18765", debrief_port="18766") == {
        "audio_ws": 18765,
        "ws_bus": 18765,
        "debrief": 18766,
    }


def test_runtime_ports_reject_invalid_env_values() -> None:
    assert _port_snapshot(ws_port="0", debrief_port="not-a-port") == {
        "audio_ws": 8765,
        "ws_bus": 8765,
        "debrief": 8766,
    }
