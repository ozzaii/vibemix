# SPDX-License-Identifier: Apache-2.0
"""Unit coverage for the live replay runner."""

from __future__ import annotations

import json
import signal
import wave
from pathlib import Path

from scripts.eval.replay_live_runner import (
    LiveReplayConfig,
    build_findings,
    discover_sessions,
    run_live_replay_session,
)


def _write_wav(path: Path, *, sample_rate: int = 16000, frames: int = 1600) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\0\0" * frames)


def test_discover_sessions_finds_direct_and_nested(tmp_path: Path) -> None:
    direct = tmp_path / "direct"
    nested = tmp_path / "sessions" / "nested"
    direct.mkdir()
    nested.mkdir(parents=True)
    _write_wav(direct / "input.wav")
    _write_wav(nested / "input.wav")

    assert discover_sessions(tmp_path) == [direct, nested]


def test_run_live_replay_session_sets_env_and_reports_pass(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_BPM_CONFIDENCE_FLOOR", raising=False)
    session = tmp_path / "corpus" / "set-one"
    session.mkdir(parents=True)
    _write_wav(session / "input.wav")
    (session / "midi.jsonl").write_text(
        json.dumps({"ts": 0.0, "type": "cc", "channel": 0, "data1": 19, "data2": 110})
        + "\n",
        encoding="utf-8",
    )
    (session / "nowplaying.jsonl").write_text(
        json.dumps({"ts": 0.0, "title": "Track", "client_bundle_id": "rekordbox"})
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    class FakeProc:
        def __init__(self, command, *, cwd, env, stdout, stderr, text):
            seen["command"] = command
            seen["cwd"] = cwd
            seen["env"] = env
            self.returncode = None

        def poll(self):
            return self.returncode

        def send_signal(self, sig):
            assert sig == signal.SIGINT
            self.returncode = 0
            home = Path(seen["env"]["HOME"])  # type: ignore[index]
            recording = home / "Library" / "Application Support" / "vibemix" / "recordings" / "r1"
            recording.mkdir(parents=True)
            _write_wav(recording / "input.wav", frames=32000)
            (recording / "events.jsonl").write_text("", encoding="utf-8")

        def communicate(self, timeout=None):
            return (
                "\n".join(
                    [
                        "-> replay MIDI tape: /tmp/session/midi.jsonl",
                        "-> replay nowplaying: /tmp/session/nowplaying.jsonl",
                        "-> replay capture: /tmp/session",
                        "-> AI voice output muted (no local TTS); stream not opened",
                        "-> mascot bus on ws://127.0.0.1:19000",
                        "[live] music=0.249 | audible=1 deck=A phase=peak",
                    ]
                ),
                "",
            )

        def kill(self):
            self.returncode = -9

    config = LiveReplayConfig(
        repo_root=tmp_path,
        output_dir=tmp_path / "out",
        duration_s=0.0,
        base_ws_port=19000,
        base_debrief_port=19100,
        output_device="BlackHole 2ch",
        python_executable="/python",
    )

    result = run_live_replay_session(
        session,
        index=0,
        config=config,
        popen_factory=FakeProc,
        sleep_fn=lambda _: None,
    )
    env = seen["env"]

    assert seen["command"] == ["/python", "-m", "vibemix"]
    assert env["VIBEMIX_REPLAY_SESSION"] == str(session.resolve())
    assert env["VIBEMIX_WS_PORT"] == "19000"
    assert env["VIBEMIX_DEBRIEF_PORT"] == "19100"
    assert env["VIBEMIX_TTS_ENGINE"] == "off"
    assert env["VIBEMIX_OUTPUT_DEVICE"] == "BlackHole 2ch"
    # Without this, the replayed set sits at the armed start gate forever and the
    # run captures zero events — the runner must auto-fire one session.start.
    assert env["VIBEMIX_AUTOSTART"] == "1"
    # The runner must NOT relax the BPM confidence floor anymore — since the
    # 2026-06-09 two-lane calibration (audio/features.py) the PRODUCT floor
    # locks on real audio, and replay's whole point is measuring the shipped
    # perception unmodified.
    assert "VIBEMIX_BPM_CONFIDENCE_FLOOR" not in env
    assert result.max_music == 0.249
    assert result.audible_seen is True
    assert result.recording_input_duration_s == 2.0
    findings = build_findings([result])
    assert findings["verdict"] == "pass"
    assert findings["scenarios"][0]["checklist"]["events"] == 0
    assert findings["scenarios"][0]["checklist"]["citation_zero_non_ack"] == 0


def test_build_findings_flags_broken_replay(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _write_wav(session / "input.wav")
    config = LiveReplayConfig(repo_root=tmp_path, output_dir=tmp_path / "out", duration_s=0.0)

    class SilentProc:
        returncode = None

        def poll(self):
            return self.returncode

        def send_signal(self, sig):
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("", "Traceback: nope")

        def kill(self):
            self.returncode = -9

    result = run_live_replay_session(
        session,
        index=0,
        config=config,
        popen_factory=lambda *args, **kwargs: SilentProc(),
        sleep_fn=lambda _: None,
    )

    row = build_findings([result])["scenarios"][0]
    assert row["verdict"] == "fail"
    assert "fatal_log" in row["flags"]
    assert "replay_capture_not_selected" in row["flags"]
    assert "no_music_meter" in row["flags"]


def test_build_findings_routes_event_log_failures(tmp_path: Path) -> None:
    session = tmp_path / "corpus" / "set-one"
    session.mkdir(parents=True)
    _write_wav(session / "input.wav")

    class EventfulProc:
        returncode = None

        def __init__(self, command, *, cwd, env, stdout, stderr, text):
            self.env = env

        def poll(self):
            return self.returncode

        def send_signal(self, sig):
            self.returncode = 0
            home = Path(self.env["HOME"])
            recording = home / "Library" / "Application Support" / "vibemix" / "recordings" / "r1"
            recording.mkdir(parents=True)
            _write_wav(recording / "input.wav", frames=32000)
            (recording / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"kind": "event", "type": "TRACK_CHANGE"}),
                        json.dumps({"kind": "citation_count", "count": 0}),
                        json.dumps({"kind": "slop_suppressed"}),
                        json.dumps({"kind": "llm_to_tts_delta_ms", "delta_ms": 7001}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

        def communicate(self, timeout=None):
            return (
                "\n".join(
                    [
                        "-> replay capture: /tmp/session",
                        "-> AI voice output muted (no local TTS); stream not opened",
                        "-> mascot bus on ws://127.0.0.1:18765",
                        "[live] music=0.249 | audible=1 deck=A phase=peak",
                    ]
                ),
                "",
            )

        def kill(self):
            self.returncode = -9

    result = run_live_replay_session(
        session,
        index=0,
        config=LiveReplayConfig(repo_root=tmp_path, output_dir=tmp_path / "out", duration_s=0.0),
        popen_factory=EventfulProc,
        sleep_fn=lambda _: None,
    )

    row = build_findings([result])["scenarios"][0]
    assert row["verdict"] == "fail"
    assert row["checklist"]["events"] == 1
    assert row["checklist"]["llm_invokes"] == 0
    assert row["checklist"]["citation_zero_non_ack"] == 1
    assert row["checklist"]["slop_suppressed"] == 1
    assert row["checklist"]["max_latency_ms"] == 7001
    assert "mute" in row["flags"]
    assert "citation_zero" in row["flags"]
    assert "slop_suppressed" in row["flags"]
    assert "late" in row["flags"]
