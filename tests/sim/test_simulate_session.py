# SPDX-License-Identifier: Apache-2.0
"""v8.0 P72 — offline simulation harness CI proof (SIM-01 / SIM-02 / SIM-03).

Runs the no-hardware, no-Gemini session simulation headlessly and pins its
contract: device-select lands on BlackHole (never the controller), the FLX4
synthetic MIDI stream decodes, the offline reaction path (real
EvidenceRegistry + EventDetector + CitationLinter) runs to completion, and a
deterministic ``sim_report.json`` artifact is written. This is the software
stand-in for the §V7-LIVE hardware ear-passes.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sim.simulate_session import main, run_simulation


def test_run_simulation_all_legs_pass(tmp_path: Path) -> None:
    report = run_simulation(tmp_path)
    assert report["pass"] is True, report
    legs = report["legs"]
    # SIM-02 device: BlackHole chosen over the controller, raises when absent.
    assert legs["device"]["founder_rig_choice"] == "BlackHole 2ch"
    assert legs["device"]["no_blackhole_raises"] is True
    # SIM-02 midi: FLX4 synthetic stream decodes deck-A state + events.
    assert legs["midi"]["deck_a_vol"] == 110
    assert legs["midi"]["deck_a_play"] is True
    assert legs["midi"]["events"] >= 2
    # SIM-01 reaction: offline harness ran the real stack, no Gemini.
    assert legs["reaction"]["harness_rc"] == 0
    assert legs["reaction"]["sessions"] >= 1
    # SIM-01 citation: the linter ran (anti-slop gate exercised headlessly).
    assert "ungrounded_valid" in legs["citation"]
    # "simulate everybody, every interaction": 6 distinct personas (3 levels ×
    # 2 modes) + every event type in the taxonomy resolved through the prompt
    # builder.
    assert legs["interactions"]["personas_distinct"] == 6
    assert len(legs["interactions"]["personas"]) == 6
    assert all(legs["interactions"]["events"].values())
    assert set(legs["interactions"]["events"]) == {
        "TRACK_CHANGE",
        "PHASE",
        "LAYER_ARRIVAL",
        "MIX_MOVE",
        "HEARTBEAT",
        "KAAN_SPOKE",
        "MANUAL",
    }


def test_simulation_writes_deterministic_artifact(tmp_path: Path) -> None:
    """SIM-03: sim_report.json exists with stable leg verdicts across runs."""
    run_simulation(tmp_path)
    artifact = tmp_path / "sim_report.json"
    assert artifact.is_file()
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["hardware"].startswith("none")
    assert data["gemini"].startswith("none")
    # Leg verdicts are deterministic (only the timestamp varies run-to-run).
    other = tmp_path / "rerun"
    second = run_simulation(other)
    assert {k: v["pass"] for k, v in data["legs"].items()} == {
        k: v["pass"] for k, v in second["legs"].items()
    }


def test_simulation_cli_exit_zero(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path / "cli")]) == 0
