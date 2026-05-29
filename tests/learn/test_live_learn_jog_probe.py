# SPDX-License-Identifier: Apache-2.0
"""Contracts for the focused live Learn jog probe."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import live_learn_jog_probe as probe


def _frame(channel: int = 0, data1: int = 0x21, data2: int = 65) -> dict:
    return {
        "ts": 0.12,
        "type": "cc",
        "channel": channel,
        "data1": data1,
        "data1_hex": f"0x{data1:02x}",
        "data2": data2,
    }


def test_left_jog_matcher_accepts_live_discovered_flx4_cc33_tick() -> None:
    assert probe.is_left_jog_frame(_frame()) is True


def test_left_jog_matcher_rejects_neutral_deck_b_and_other_controls() -> None:
    assert probe.is_left_jog_frame(_frame(data2=64)) is False
    assert probe.is_left_jog_frame(_frame(channel=1)) is False
    assert probe.is_left_jog_frame(_frame(data1=0x13)) is False
    assert probe.is_left_jog_frame({"type": "note_on", "channel": 0, "data1": 0x21}) is False


def test_build_summary_names_first_live_match_and_expected_lesson() -> None:
    frames = [_frame(data1=0x13), _frame(data2=65), _frame(data2=63)]
    summary = probe.build_summary(
        frames=frames,
        duration_s=1.25,
        port_name="DDJ-FLX4",
        learn_verifier={"passed": True},
    )

    assert summary["passed"] is True
    assert summary["frames"] == 3
    assert summary["matched_left_jog_frames"] == 2
    assert summary["first_left_jog_frame"] == frames[1]
    assert summary["expected"]["lesson_id"] == "L1.07"
    assert summary["expected"]["control_id"] == "jog:A"


def test_captured_flx4_jog_byte_reaches_lesson_verifier() -> None:
    proof = probe.verify_frame_reaches_lesson(_frame(data2=65))

    assert proof["passed"] is True
    assert proof["lesson_id"] == "L1.07"
    assert proof["positions"]["jog:A"] == 127
    assert proof["state"] in {"advancing", "completed"}


def test_probe_help_runs_when_invoked_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/live_learn_jog_probe.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "left-jog byte" in proc.stdout
