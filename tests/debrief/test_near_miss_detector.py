# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest

from vibemix.__main__ import _run_debrief_cli, cli_entry
from vibemix.debrief.near_miss_detector import detect_near_miss_from_samples

_SR = 16_000
_BPM = 120.0


def _kick_loop(duration_s: float, *, shifted: bool) -> np.ndarray:
    beat_s = 60.0 / _BPM
    samples = np.zeros(int(duration_s * _SR), dtype=np.float32)
    kick_len = int(0.09 * _SR)
    t = np.arange(kick_len, dtype=np.float32) / _SR
    kick = 0.85 * np.sin(2.0 * np.pi * 60.0 * t) * np.exp(-42.0 * t)
    n_beats = int(duration_s / beat_s)
    for beat_idx in range(n_beats):
        beat_t = beat_idx * beat_s
        offset_beats = 0.16 if shifted and 12.0 <= beat_t < 18.0 else 0.0
        start = int((beat_t + offset_beats * beat_s) * _SR)
        end = start + kick_len
        if start < 0 or end > samples.size:
            continue
        samples[start:end] += kick
    return np.clip(samples, -1.0, 1.0)


def _events() -> list[dict]:
    return [
        {"kind": "session_start", "t": 0.0},
        {"kind": "event", "type": "MIX_MOVE", "t": 14.0},
        {"kind": "event", "type": "TRACK_CHANGE", "t": 22.0},
    ]


def _write_session(root: Path, samples: np.ndarray) -> Path:
    session = root / "20260606-121212"
    session.mkdir(parents=True)
    (session / "events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in _events()),
        encoding="utf-8",
    )
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(session / "input.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SR)
        wf.writeframes(pcm.tobytes())
    return session


def test_detect_near_miss_reports_one_out_to_in_recovery_from_input_audio() -> None:
    result = detect_near_miss_from_samples(
        _kick_loop(36.0, shifted=True),
        _SR,
        _events(),
    )

    assert result is not None
    assert result.event_type == "MIX_MOVE"
    assert result.depth_beats >= 0.09
    assert result.recovery_bars <= 5.0
    assert result.confidence >= 0.38
    assert result.citation.startswith("[mix:near_miss@")
    assert result.to_dict()["language_subject"] == "the mix"


def test_detect_near_miss_abstains_on_clean_grid() -> None:
    result = detect_near_miss_from_samples(
        _kick_loop(36.0, shifted=False),
        _SR,
        _events(),
    )

    assert result is None


def test_debrief_near_miss_cli_validates_root_and_emits_json(
    tmp_path: Path,
    capsys,
) -> None:
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    _write_session(recordings, _kick_loop(36.0, shifted=True))

    exit_code = _run_debrief_cli(
        [
            "near-miss",
            "20260606-121212",
            "--recordings-root",
            str(recordings),
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["near_miss"]["event_type"] == "MIX_MOVE"
    assert payload["near_miss"]["citation"].startswith("[mix:near_miss@")


def test_cli_entry_dispatches_debrief_near_miss_before_live_runtime(
    tmp_path: Path,
    capsys,
) -> None:
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    _write_session(recordings, _kick_loop(36.0, shifted=True))

    with pytest.raises(SystemExit) as raised:
        cli_entry(
            [
                "debrief",
                "near-miss",
                "20260606-121212",
                "--recordings-root",
                str(recordings),
                "--json",
            ]
        )

    assert raised.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["near_miss"]["language_subject"] == "the mix"
