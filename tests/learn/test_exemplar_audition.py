# SPDX-License-Identifier: Apache-2.0
"""Contracts for the packaged Learn exemplar audition helper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import audition_learn_exemplars as audition


def test_audit_packaged_bank_reports_all_four_band_exemplars() -> None:
    summary = audition.audit_packaged_bank()

    assert summary["passed"] is True
    assert summary["technical_passed"] is True
    assert summary["release_ready"] is False
    assert summary["human_ear_pass_required"] is True
    assert summary["technical_failures"] == []
    assert summary["diagnosis"]["code"] == "technical_audit_passed_ear_pass_pending"
    assert summary["diagnosis"]["severity"] == "needs_ear_pass"
    assert summary["bank_fingerprint"]["algorithm"] == "sha256-canonical-json-v1"
    assert len(summary["bank_fingerprint"]["digest"]) == 64
    assert len(summary["bank_fingerprint"]["manifest_sha256"]) == 64
    assert summary["bank_fingerprint"]["track_count"] == 4
    rows = summary["tracks"]
    assert {row["band"] for row in rows} == {"sub", "low", "mid", "high"}
    assert len(rows) == 4
    for row in rows:
        assert row["integrity_passed"] is True
        assert row["technical_passed"] is True
        assert row["hash_matches"] is True
        assert row["sample_rate_matches"] is True
        assert row["stereo"] is True
        assert row["channels"] == 2
        assert row["sample_rate_hz"] == row["manifest_sample_rate_hz"]
        assert row["duration_s"] > 0
        assert row["duration_valid"] is True
        assert row["peak"] <= 1.0
        assert row["rms"] > 0.0
        assert row["clip_free"] is True
        assert row["non_silent"] is True
        assert row["needs_human_ear_pass"] is True


def test_audit_packaged_bank_keeps_human_ear_pass_pending() -> None:
    summary = audition.audit_packaged_bank()

    assert summary["human_ear_pass"] is None
    assert "play the four loops" in summary["next_action"]
    assert summary["operator_commands"]["list_output_devices"].endswith(
        "--list-devices"
    )
    assert "--device-index <output-device-index>" in summary["operator_commands"]["play"]
    assert "--say-prompts" in summary["operator_commands"]["play"]
    assert "learn-exemplar-audition-current.json" in summary["operator_commands"]["play"]
    assert "--approve-ear-pass" in summary["operator_commands"]["approve"]
    assert "--audition" in summary["operator_commands"]["approve"]
    assert "four EQ exemplar loops" in summary["operator_action"]["prompt"]
    assert summary["operator_action"]["steps"][0].endswith("--list-devices")


def test_list_output_devices_filters_input_only_rows(monkeypatch) -> None:
    class FakeSoundDevice:
        default = type("Default", (), {"device": [0, 2]})()

        @staticmethod
        def query_devices() -> list[dict[str, object]]:
            return [
                {
                    "name": "Built-in Mic",
                    "hostapi": 0,
                    "max_output_channels": 0,
                    "default_samplerate": 48000.0,
                },
                {
                    "name": "Headphones",
                    "hostapi": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 48000.0,
                },
                {
                    "name": "BlackHole 2ch",
                    "hostapi": 1,
                    "max_output_channels": 2,
                    "default_samplerate": 48000.0,
                },
            ]

        @staticmethod
        def query_hostapis() -> list[dict[str, object]]:
            return [{"name": "Core Audio"}, {"name": "Virtual"}]

    real_import_module = audition.importlib.import_module

    def fake_import_module(name: str):
        if name == "sounddevice":
            return FakeSoundDevice
        return real_import_module(name)

    monkeypatch.setattr(audition.importlib, "import_module", fake_import_module)

    rows = audition.list_output_devices()

    assert [row["name"] for row in rows] == ["Headphones", "BlackHole 2ch"]
    assert rows[0]["hostapi"] == "Core Audio"
    assert rows[1]["hostapi"] == "Virtual"
    assert rows[1]["is_default_output"] is True


def test_recommended_output_devices_avoid_loopback_default() -> None:
    rows = [
        {
            "index": 1,
            "name": "BlackHole 16ch",
            "max_output_channels": 16,
            "is_default_output": True,
        },
        {
            "index": 4,
            "name": "MacBook Pro Speakers",
            "max_output_channels": 2,
            "is_default_output": False,
        },
        {
            "index": 0,
            "name": "DDJ-FLX4",
            "max_output_channels": 4,
            "is_default_output": False,
        },
    ]

    recommended = audition.recommended_output_devices(rows)
    action = audition.ear_pass_operator_action(rows)

    assert [row["name"] for row in recommended] == ["MacBook Pro Speakers", "DDJ-FLX4"]
    assert action["recommended_output_devices"][0]["index"] == 4
    assert "--device-index 4" in action["steps"][1]
    assert "--say-prompts" in action["steps"][1]
    assert "learn-exemplar-audition-current.json" in action["steps"][1]


def test_say_prompt_uses_macos_say_when_enabled(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs):
        calls.append(argv)
        assert kwargs["timeout"] == 5
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(audition.sys, "platform", "darwin")
    monkeypatch.setattr(audition.subprocess, "run", fake_run)

    assert audition._say_prompt("Sub EQ exemplar.", enabled=True) is True
    assert calls == [["say", "Sub EQ exemplar."]]


def test_say_prompt_stays_quiet_when_disabled(monkeypatch) -> None:
    def fail_run(*_args, **_kwargs):
        raise AssertionError("say should not run when prompts are disabled")

    monkeypatch.setattr(audition.sys, "platform", "darwin")
    monkeypatch.setattr(audition.subprocess, "run", fail_run)

    assert audition._say_prompt("Sub EQ exemplar.", enabled=False) is False


def test_play_tracks_speaks_band_labels_when_requested(monkeypatch, tmp_path: Path) -> None:
    played: list[str] = []
    stopped = 0
    spoken: list[tuple[str, bool]] = []

    class FakePlayer:
        def __init__(self, *, device_index, state):
            self.device_index = device_index
            self.state = state

        def play(self, path: str) -> None:
            played.append(path)

        def stop(self) -> None:
            nonlocal stopped
            stopped += 1

    class FakeMusicState:
        pass

    class FakeAudioCue:
        ExemplarPlayer = FakePlayer

    class FakeMusicStateModule:
        MusicState = FakeMusicState

    real_import_module = audition.importlib.import_module

    def fake_import_module(name: str):
        if name == "vibemix.learn.audio_cue":
            return FakeAudioCue
        if name == "vibemix.state.music_state":
            return FakeMusicStateModule
        return real_import_module(name)

    def fake_say(text: str, *, enabled: bool) -> bool:
        spoken.append((text, enabled))
        return enabled

    monkeypatch.setattr(audition.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(audition, "_say_prompt", fake_say)
    monkeypatch.setattr(audition.time, "sleep", lambda _seconds: None)

    row_path = tmp_path / "sub.wav"
    result = audition.play_tracks(
        [
            {
                "abs_path": str(row_path),
                "band": "sub",
                "title": "Sub pulse",
                "duration_s": 0.01,
            }
        ],
        device_index=3,
        gap_s=0.0,
        say_prompts=True,
    )

    assert played == [str(row_path)]
    assert stopped >= 2
    assert spoken == [("sub EQ exemplar.", True)]
    assert result == {
        "device_index": 3,
        "say_prompts": True,
        "spoken_prompt_count": 1,
        "played_count": 1,
    }


def test_play_without_device_index_surfaces_device_choices(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        audition,
        "list_output_devices",
        lambda: [
            {
                "index": 7,
                "name": "Headphones",
                "hostapi": "Core Audio",
                "max_output_channels": 2,
                "default_sample_rate": 48000,
                "is_default_output": True,
            }
        ],
    )

    result = audition.main(["--play"])
    output = json.loads(capsys.readouterr().out)

    assert result == 1
    assert output["error"] == "--play requires --device-index"
    assert output["output_devices"][0]["index"] == 7
    assert output["operator_action"]["recommended_output_devices"][0]["index"] == 7
    assert "--device-index 7" in output["operator_action"]["steps"][1]
    assert "--say-prompts" in output["operator_action"]["steps"][1]
    assert "learn-exemplar-audition-current.json" in output["operator_action"]["steps"][1]
    assert "choose an output_devices[].index" in output["next_action"]


def test_ear_pass_approval_matches_current_hashes(tmp_path: Path) -> None:
    summary = audition.audit_packaged_bank()
    approval_path = tmp_path / "learn-exemplar-ear-pass-current.json"

    approval = audition.write_ear_pass_approval(
        summary,
        approval_path,
        approved_by="Kaan",
    )
    approved_summary = audition.audit_packaged_bank(approval_path=approval_path)

    assert approval["approved"] is True
    assert approval["bank_fingerprint"] == summary["bank_fingerprint"]
    assert approval_path.exists()
    assert approved_summary["release_ready"] is True
    assert approved_summary["human_ear_pass_required"] is False
    assert approved_summary["diagnosis"]["code"] == "technical_and_ear_pass_approved"
    assert approved_summary["human_ear_pass"]["approved"] is True


def _valid_audition_summary() -> dict:
    summary = audition.audit_packaged_bank()
    summary["human_ear_pass"] = "auditioned_by_user"
    summary["playback"] = {
        "device_index": 3,
        "played_count": len(summary["tracks"]),
        "say_prompts": True,
        "spoken_prompt_count": len(summary["tracks"]),
    }
    return summary


def test_validate_audition_artifact_accepts_matching_playback() -> None:
    summary = audition.audit_packaged_bank()
    status = audition.validate_audition_artifact(summary, _valid_audition_summary())

    assert status["played"] is True
    assert status["errors"] == []


def test_validate_audition_artifact_rejects_missing_playback() -> None:
    summary = audition.audit_packaged_bank()
    audition_summary = _valid_audition_summary()
    audition_summary.pop("playback")

    status = audition.validate_audition_artifact(summary, audition_summary)

    assert status["played"] is False
    assert "audition playback metadata is missing" in status["errors"]


def test_ear_pass_approval_rejects_stale_hashes(tmp_path: Path) -> None:
    summary = audition.audit_packaged_bank()
    approval_path = tmp_path / "learn-exemplar-ear-pass-current.json"
    approval = audition.write_ear_pass_approval(
        summary,
        approval_path,
        approved_by="Kaan",
    )
    approval["tracks"][0]["sha256"] = "stale"
    approval_path.write_text(json.dumps(approval), encoding="utf-8")

    approved_summary = audition.audit_packaged_bank(approval_path=approval_path)

    assert approved_summary["release_ready"] is False
    assert approved_summary["human_ear_pass_required"] is True
    assert any(
        "approval hash mismatch" in error
        for error in approved_summary["human_ear_pass"]["errors"]
    )


def test_ear_pass_approval_rejects_missing_bank_fingerprint(tmp_path: Path) -> None:
    summary = audition.audit_packaged_bank()
    approval_path = tmp_path / "learn-exemplar-ear-pass-current.json"
    approval = audition.write_ear_pass_approval(
        summary,
        approval_path,
        approved_by="Kaan",
    )
    approval.pop("bank_fingerprint")
    approval_path.write_text(json.dumps(approval), encoding="utf-8")

    approved_summary = audition.audit_packaged_bank(approval_path=approval_path)

    assert approved_summary["release_ready"] is False
    assert "approval bank_fingerprint is missing" in approved_summary["human_ear_pass"][
        "errors"
    ]


def test_ear_pass_approval_rejects_bank_fingerprint_mismatch(tmp_path: Path) -> None:
    summary = audition.audit_packaged_bank()
    approval_path = tmp_path / "learn-exemplar-ear-pass-current.json"
    approval = audition.write_ear_pass_approval(
        summary,
        approval_path,
        approved_by="Kaan",
    )
    approval["bank_fingerprint"]["digest"] = "0" * 64
    approval_path.write_text(json.dumps(approval), encoding="utf-8")

    approved_summary = audition.audit_packaged_bank(approval_path=approval_path)

    assert approved_summary["release_ready"] is False
    assert "approval bank fingerprint mismatch" in approved_summary["human_ear_pass"][
        "errors"
    ]


def test_write_audit_summary_persists_release_artifact(tmp_path: Path) -> None:
    summary = audition.audit_packaged_bank()
    out_path = tmp_path / "learn-exemplar-audit.json"

    written = audition.write_audit_summary(summary, out_path)

    assert written == out_path
    persisted = json.loads(out_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 2
    assert persisted["technical_passed"] is True
    assert persisted["release_ready"] is False
    assert persisted["diagnosis"]["code"] == "technical_audit_passed_ear_pass_pending"


def test_audition_helper_out_writes_json_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_path = tmp_path / "learn-exemplar-audit.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/audition_learn_exemplars.py",
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert proc.returncode == 0
    stdout_summary = json.loads(proc.stdout)
    file_summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert stdout_summary["technical_passed"] is True
    assert file_summary["technical_passed"] is True
    assert file_summary["release_ready"] is False


def test_audition_helper_can_write_explicit_approval_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_path = tmp_path / "learn-exemplar-audit.json"
    approval_path = tmp_path / "learn-exemplar-ear-pass-current.json"
    audition_path = tmp_path / "learn-exemplar-audition-current.json"
    audition_path.write_text(
        json.dumps(_valid_audition_summary(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/audition_learn_exemplars.py",
            "--approve-ear-pass",
            "--approved-by",
            "Kaan",
            "--audition",
            str(audition_path),
            "--approval-out",
            str(approval_path),
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert proc.returncode == 0
    stdout_summary = json.loads(proc.stdout)
    file_summary = json.loads(out_path.read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    assert stdout_summary["release_ready"] is True
    assert file_summary["release_ready"] is True
    assert approval["proof"] == "learn_exemplar_ear_pass"
    assert approval["approved_by"] == "Kaan"
    assert len(approval["bank_fingerprint"]["digest"]) == 64
    assert stdout_summary["audition"]["played"] is True


def test_audition_helper_rejects_approval_without_audition_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    approval_path = tmp_path / "learn-exemplar-ear-pass-current.json"
    missing_audition = tmp_path / "missing-audition.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/audition_learn_exemplars.py",
            "--approve-ear-pass",
            "--approved-by",
            "Kaan",
            "--audition",
            str(missing_audition),
            "--approval-out",
            str(approval_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    summary = json.loads(proc.stdout)
    assert proc.returncode == 1
    assert summary["passed"] is False
    assert "valid audition artifact is required" in summary["error"]
    assert summary["audition"]["played"] is False
    assert not approval_path.exists()


def test_audition_helper_help_runs_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/audition_learn_exemplars.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "packaged Learn EQ exemplar bank" in proc.stdout
    assert "--out" in proc.stdout
    assert "--approve-ear-pass" in proc.stdout
    assert "--list-devices" in proc.stdout
    assert "--say-prompts" in proc.stdout
    assert "--audition" in proc.stdout
