# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn live-proof artifact runner."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts import run_learn_live_proof as runner


def _args(tmp_path: Path, **overrides: Any) -> SimpleNamespace:
    values = {
        "url": "ws://127.0.0.1:8765",
        "progress_path": str(tmp_path / "learn-progress.json"),
        "seed_course3_unlocked": False,
        "input_device": None,
        "output_device": None,
        "mic_device": None,
        "auto_master_input": False,
        "start_app": False,
        "start_timeout": 0.1,
        "screen": True,
        "screen_seconds": 1.0,
        "screen_lesson_id": "L1.01",
        "physical": False,
        "physical_seconds": 1.0,
        "say_physical_prompts": False,
        "wait_physical_seconds": 0.0,
        "course3": False,
        "nudge_rekordbox_playback": False,
        "rekordbox_nudge_delay": 0.0,
        "say_course3_prompts": False,
        "course3_seconds": 1.0,
        "course3_context_seconds": 0.0,
        "course3_lesson_id": "L3.01",
        "loopback_signal_seconds": 0.0,
        "loopback_self_test_seconds": 0.0,
        "capture_matrix_seconds": 0.0,
        "wait_course3_seconds": 0.0,
        "wait_loopback_signal_seconds": 0.0,
        "wait_capture_signal_seconds": 0.0,
        "wait_interval": 0.01,
        "require_count_in": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _readiness(
    *,
    screen: bool = True,
    physical: bool = False,
    course3: bool = False,
    loopback_signal: bool | None = None,
    capture_signal: bool | None = None,
    course3_route_doctor: dict[str, Any] | None = None,
    course3_audio_diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    if loopback_signal is not None:
        checks["loopback_signal"] = {
            "enabled": True,
            "ok": loopback_signal,
            "rms": 0.01 if loopback_signal else 0.0,
            "peak": 0.05 if loopback_signal else 0.0,
        }
    if capture_signal is not None:
        checks["capture_matrix"] = {
            "enabled": True,
            "ok": capture_signal,
            "top_signal": {"name": "rekordbox Aggregate Device"} if capture_signal else None,
            "rows": [],
        }
    summary = {
        "passed": True,
        "readiness": {
            "screen_learn": screen,
            "physical_learn": physical,
            "course3_audio": course3,
        },
        "blockers": [],
        "checks": checks,
    }
    if course3_route_doctor is not None:
        summary["course3_route_doctor"] = course3_route_doctor
    if course3_audio_diagnosis is not None:
        summary["course3_audio_diagnosis"] = course3_audio_diagnosis
    return summary


def test_artifact_passed_respects_requested_stages() -> None:
    stages = {
        "screen_probe": runner.make_stage(status="passed"),
        "physical_probe": runner.make_stage(status="skipped"),
        "course3_probe": runner.make_stage(status="skipped"),
    }

    assert runner.artifact_passed(
        stages,
        require_screen=True,
        require_physical=False,
        require_course3=False,
    )
    assert not runner.artifact_passed(
        stages,
        require_screen=True,
        require_physical=True,
        require_course3=False,
    )


def test_broadest_readiness_requirement_prefers_course3() -> None:
    assert (
        runner.broadest_readiness_requirement(
            _args(Path("/tmp"), screen=True, physical=True, course3=True)
        )
        == "course3"
    )
    assert (
        runner.broadest_readiness_requirement(
            _args(Path("/tmp"), screen=True, physical=True, course3=False)
        )
        == "physical"
    )
    assert (
        runner.broadest_readiness_requirement(
            _args(Path("/tmp"), screen=True, physical=False, course3=False)
        )
        == "screen"
    )
    assert (
        runner.broadest_readiness_requirement(
            _args(Path("/tmp"), screen=False, physical=False, course3=False)
        )
        == "none"
    )


def test_write_and_read_progress_artifact(tmp_path: Path) -> None:
    out = tmp_path / "proof.json"
    progress = tmp_path / "learn-progress.json"
    progress.write_text(json.dumps({"lessons": {"L1.01": {"completed": True}}}))

    runner.write_artifact({"passed": True}, out)

    assert json.loads(out.read_text(encoding="utf-8")) == {"passed": True}
    assert runner.read_progress_file(progress)["lessons"]["L1.01"]["completed"] is True


def test_seed_course3_unlocked_progress_writes_isolated_unlock_file(tmp_path: Path) -> None:
    progress_path = tmp_path / "learn-progress.json"

    result = runner.seed_course3_unlocked_progress(progress_path)
    snapshot = runner.read_progress_file(progress_path)

    assert result["course_2_unlocked"] is True
    assert result["course_3_unlocked"] is True
    assert snapshot is not None
    assert snapshot["course_2_unlocked"] is True
    assert snapshot["course_3_unlocked"] is True
    assert snapshot["schema_version"] == 2


def test_parse_app_audio_runtime_records_live_auto_master_choice() -> None:
    result = runner.parse_app_audio_runtime(
        "[audio] auto master input: BlackHole 16ch @ 48000Hz "
        "rms=0.0187 peak=0.1400\n"
    )

    selected = result["auto_master_input"]
    assert selected["selected"] is True
    assert selected["name"] == "BlackHole 16ch"
    assert selected["sample_rate"] == 48000
    assert selected["live_signal"] is True
    assert selected["reason"] == "live_signal"
    assert selected["rms"] == 0.0187
    assert selected["peak"] == 0.14


def test_parse_app_audio_runtime_records_auto_master_fallback_choice() -> None:
    result = runner.parse_app_audio_runtime(
        "[audio] auto master input: BlackHole 16ch @ 48000Hz "
        "(48k fallback; no live signal during startup probe)\n"
    )

    selected = result["auto_master_input"]
    assert selected["name"] == "BlackHole 16ch"
    assert selected["sample_rate"] == 48000
    assert selected["live_signal"] is False
    assert selected["reason"] == "48k_fallback"


def test_parse_app_audio_runtime_records_preferred_fallback_choice() -> None:
    result = runner.parse_app_audio_runtime(
        "[audio] auto master input: BlackHole 2ch @ 48000Hz "
        "(preferred fallback; no live signal during startup probe)\n"
    )

    selected = result["auto_master_input"]
    assert selected["name"] == "BlackHole 2ch"
    assert selected["sample_rate"] == 48000
    assert selected["live_signal"] is False
    assert selected["reason"] == "preferred_fallback"


def test_attach_app_audio_runtime_copies_choice_to_app_start() -> None:
    stages = {
        "app_start": runner.make_stage(
            status="passed",
            result={"audio_env": {"auto_master_input": True}},
        )
    }
    stop_result = {
        "audio_runtime": {
            "auto_master_input": {
                "selected": True,
                "name": "BlackHole 16ch",
                "sample_rate": 48000,
                "live_signal": False,
                "reason": "48k_fallback",
            }
        }
    }

    runner.attach_app_audio_runtime(stages, stop_result)

    assert (
        stages["app_start"]["result"]["audio_runtime"]["auto_master_input"]["name"]
        == "BlackHole 16ch"
    )


def test_nudge_rekordbox_playback_records_osascript_success(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        assert kwargs["timeout"] == 5
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.nudge_rekordbox_playback(delay_s=0.1)

    assert result["ok"] is True
    assert result["action"] == "rekordbox_spacebar"
    assert result["stdout"] == "ok"
    assert calls[0][0] == "osascript"
    assert "keystroke space" in calls[0][2]


def test_course3_say_prompt_uses_macos_say_when_enabled(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Proc:
        pass

    def fake_popen(argv: list[str], **_kwargs: Any) -> Proc:
        calls.append(argv)
        return Proc()

    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)

    summary = runner.course3_operator_prompt_summary(
        _readiness(course3=False, loopback_signal=False),
        enabled=True,
    )

    assert summary["spoken"] is True
    assert summary["skipped"] is False
    assert calls == [["say", runner.COURSE3_OPERATOR_PROMPT]]


def test_course3_say_prompt_uses_route_doctor_next_step(monkeypatch) -> None:
    calls: list[list[str]] = []
    prompt = (
        "Set Rekordbox's 'Aggregate Device' route, sampled as "
        "'rekordbox Aggregate Device', from 44100Hz to 48000Hz."
    )

    class Proc:
        pass

    def fake_popen(argv: list[str], **_kwargs: Any) -> Proc:
        calls.append(argv)
        return Proc()

    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)

    summary = runner.course3_operator_prompt_summary(
        _readiness(
            course3=False,
            loopback_signal=False,
            course3_route_doctor={
                "diagnosis_code": "rekordbox_saved_route_capture_rate_mismatch",
                "next_step": prompt,
                "route": None,
                "operator_steps": [prompt, "Play a real Rekordbox library track."],
            },
        ),
        enabled=True,
    )

    assert summary["spoken"] is True
    assert summary["prompt"] == prompt
    assert summary["prompt_source"] == "course3_route_doctor.next_step"
    assert summary["diagnosis_code"] == "rekordbox_saved_route_capture_rate_mismatch"
    assert summary["operator_steps"] == [prompt, "Play a real Rekordbox library track."]
    assert calls == [["say", prompt]]


def test_course3_say_prompt_stays_quiet_when_signal_present(monkeypatch) -> None:
    def fail_popen(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("say should not be invoked when Course 3 signal exists")

    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(runner.subprocess, "Popen", fail_popen)

    summary = runner.course3_operator_prompt_summary(
        _readiness(course3=False, loopback_signal=True),
        enabled=True,
    )

    assert summary["spoken"] is False
    assert summary["skipped"] is True
    assert summary["precheck"]["loopback_ok"] is True


def test_course3_prompt_text_falls_back_to_audio_diagnosis() -> None:
    prompt = "Start real Rekordbox deck playback and route its master output."

    selected = runner.course3_operator_prompt_text(
        _readiness(
            course3_audio_diagnosis={
                "code": "loopback_route_healthy_external_playback_absent",
                "next_action": prompt,
            }
        )
    )

    assert selected == {
        "prompt": prompt,
        "source": "course3_audio_diagnosis.next_action",
        "diagnosis_code": "loopback_route_healthy_external_playback_absent",
        "route": None,
        "operator_steps": None,
    }


def test_course3_signal_summary_detects_existing_loopback_signal() -> None:
    summary = runner.course3_signal_summary(_readiness(loopback_signal=True))

    assert summary["ok"] is True
    assert summary["loopback_ok"] is True
    assert summary["loopback_rms"] == 0.01


def test_maybe_nudge_rekordbox_skips_spacebar_when_signal_present(monkeypatch) -> None:
    def fail_nudge(**_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("should not press space when signal is already present")

    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(loopback_signal=True),
    )
    monkeypatch.setattr(runner, "nudge_rekordbox_playback", fail_nudge)

    result = runner.maybe_nudge_rekordbox_playback(
        url="ws://127.0.0.1:8765",
        delay_s=0.0,
        live_context_seconds=0.0,
        loopback_signal_seconds=0.01,
        capture_matrix_seconds=0.01,
    )

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["action"] == "rekordbox_spacebar_skipped_signal_present"
    assert result["precheck"]["loopback_ok"] is True


def test_maybe_nudge_rekordbox_presses_spacebar_when_signal_absent(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(loopback_signal=False, capture_signal=False),
    )
    monkeypatch.setattr(
        runner,
        "nudge_rekordbox_playback",
        lambda **_kwargs: {"ok": True, "action": "rekordbox_spacebar"},
    )

    result = runner.maybe_nudge_rekordbox_playback(
        url="ws://127.0.0.1:8765",
        delay_s=0.0,
        live_context_seconds=0.0,
        loopback_signal_seconds=0.01,
        capture_matrix_seconds=0.01,
    )

    assert result["ok"] is True
    assert result["action"] == "rekordbox_spacebar"
    assert result["precheck"]["ok"] is False


def test_resolve_app_audio_env_uses_rekordbox_route_as_safe_auto_fallback() -> None:
    readiness = {
        "auto_master_recommendation": {
            "ok": True,
            "source": "rekordbox_audio_settings",
            "reason": "saved_loopback_route",
            "device_name": "BlackHole 2ch",
            "sample_rate": 48000,
            "live_signal": False,
        },
        "checks": {
            "rekordbox_audio_settings": {
                "current": {"audio_output_device_name": "BlackHole 2ch"}
            },
            "capture_matrix": {
                "rows": [
                    {"name": "BlackHole 2ch", "sample_rate": 48000},
                    {"name": "BlackHole 16ch", "sample_rate": 48000},
                ]
            },
        }
    }

    plan = runner.resolve_app_audio_env(
        input_device=None,
        output_device=None,
        mic_device=None,
        auto_master_input=True,
        readiness_before=readiness,
    )

    assert plan["auto_master_input"] is True
    assert plan["auto_master_fallback_device"] == "BlackHole 2ch"
    assert plan["auto_master_fallback_source"] == "rekordbox_audio_settings"
    assert plan["auto_master_fallback_rejected_reason"] is None


def test_resolve_app_audio_env_uses_live_auto_master_recommendation() -> None:
    readiness = {
        "auto_master_recommendation": {
            "ok": True,
            "source": "capture_matrix_top_signal",
            "reason": "live_signal",
            "device_name": "BlackHole 16ch",
            "sample_rate": 48000,
            "live_signal": True,
        },
        "checks": {},
    }

    plan = runner.resolve_app_audio_env(
        input_device=None,
        output_device=None,
        mic_device=None,
        auto_master_input=True,
        readiness_before=readiness,
    )

    assert plan["auto_master_fallback_device"] == "BlackHole 16ch"
    assert plan["auto_master_fallback_source"] == "capture_matrix_top_signal"
    assert plan["auto_master_fallback_candidate"]["reason"] == "live_signal"


def test_resolve_app_audio_env_rejects_rekordbox_fallback_rate_mismatch() -> None:
    readiness = {
        "auto_master_recommendation": {
            "ok": False,
            "source": "rekordbox_audio_settings",
            "reason": "saved_loopback_rate_mismatch",
            "device_name": "BlackHole 2ch",
            "sample_rate": 44100,
            "live_signal": False,
        },
        "checks": {
            "rekordbox_audio_settings": {
                "current": {"audio_output_device_name": "BlackHole 2ch"}
            },
            "capture_matrix": {
                "rows": [
                    {"name": "BlackHole 2ch", "sample_rate": 44100},
                    {"name": "BlackHole 16ch", "sample_rate": 48000},
                ]
            },
        }
    }

    plan = runner.resolve_app_audio_env(
        input_device=None,
        output_device=None,
        mic_device=None,
        auto_master_input=True,
        readiness_before=readiness,
    )

    assert plan["auto_master_fallback_device"] is None
    assert plan["auto_master_fallback_candidate"]["name"] == "BlackHole 2ch"
    assert "44100Hz" in plan["auto_master_fallback_rejected_reason"]


def test_resolve_app_audio_env_does_not_use_unprobed_rekordbox_fallback() -> None:
    readiness = {
        "checks": {
            "rekordbox_audio_settings": {
                "current": {"audio_output_device_name": "Aggregate Device"}
            },
            "capture_matrix": None,
        }
    }

    plan = runner.resolve_app_audio_env(
        input_device=None,
        output_device=None,
        mic_device=None,
        auto_master_input=True,
        readiness_before=readiness,
    )

    assert plan["auto_master_fallback_device"] is None
    assert plan["auto_master_fallback_candidate"]["name"] == "Aggregate Device"
    assert "not sampled in the capture matrix" in plan["auto_master_fallback_rejected_reason"]


def test_run_proof_records_passing_screen_probe(monkeypatch, tmp_path: Path) -> None:
    progress = tmp_path / "learn-progress.json"
    progress.write_text(json.dumps({"lessons": {"L1.01": {"completed": True}}}))

    async def fake_screen_probe(**_kwargs: Any) -> dict[str, Any]:
        return {
            "passed": True,
            "lesson_id": "L1.01",
            "acks_sent": 4,
            "advance_count": 4,
            "complete_seen": True,
            "progress_completed": True,
        }

    monkeypatch.setattr(runner, "collect_readiness", lambda **_kwargs: _readiness())
    monkeypatch.setattr(runner, "run_screen_probe", fake_screen_probe)

    report = asyncio.run(runner.run_proof(_args(tmp_path)))

    assert report["passed"] is True
    assert report["validation"]["valid"] is True
    assert report["stages"]["screen_probe"]["status"] == "passed"
    assert report["stages"]["physical_probe"]["status"] == "skipped"
    assert report["stages"]["course3_probe"]["status"] == "skipped"


def test_run_proof_top_level_pass_uses_strict_validation(monkeypatch, tmp_path: Path) -> None:
    async def fake_screen_probe(**_kwargs: Any) -> dict[str, Any]:
        return {
            "passed": True,
            "lesson_id": "L1.01",
            "acks_sent": 4,
            "advance_count": 4,
            "complete_seen": True,
            "progress_completed": True,
        }

    monkeypatch.setattr(runner, "collect_readiness", lambda **_kwargs: _readiness())
    monkeypatch.setattr(runner, "run_screen_probe", fake_screen_probe)

    report = asyncio.run(runner.run_proof(_args(tmp_path)))

    assert report["stages"]["screen_probe"]["status"] == "passed"
    assert report["stages"]["progress_file"]["status"] == "skipped"
    assert report["passed"] is False
    assert report["validation"]["valid"] is False
    assert "progress_file stage did not pass" in report["validation"]["errors"]


def test_run_proof_records_physical_skip_as_failure_when_requested(
    monkeypatch,
    tmp_path: Path,
) -> None:
    progress = tmp_path / "learn-progress.json"
    progress.write_text(json.dumps({"lessons": {"L1.01": {"completed": True}}}))
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(screen=True, physical=False, course3=False),
    )

    report = asyncio.run(runner.run_proof(_args(tmp_path, screen=False, physical=True)))

    assert report["passed"] is False
    assert report["stages"]["physical_probe"]["status"] == "skipped"
    assert report["stages"]["physical_probe"]["reason"] == "physical readiness failed"
    assert report["stages"]["progress_file"]["status"] == "skipped"
    assert (
        report["stages"]["progress_file"]["reason"]
        == "progress file exists but no screen proof passed in this run"
    )


def test_wait_for_readiness_polls_until_requirement_passes(monkeypatch) -> None:
    calls = 0

    def fake_collect(**_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _readiness(physical=calls >= 2)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_readiness(
            requirement="physical",
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
        )
    )

    assert result["ok"] is True
    assert result["attempts"] == 2
    assert result["last"]["readiness"]["physical_learn"] is True


def test_wait_for_readiness_passes_live_context_seconds_to_course3(monkeypatch) -> None:
    seen: list[float] = []

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        seen.append(float(kwargs.get("live_context_seconds") or 0.0))
        return _readiness(course3=True)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_readiness(
            requirement="course3",
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            live_context_seconds=2.5,
        )
    )

    assert result["ok"] is True
    assert seen == [2.5]


def test_wait_for_readiness_passes_loopback_signal_seconds(monkeypatch) -> None:
    seen: list[float] = []

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        seen.append(float(kwargs.get("loopback_signal_seconds") or 0.0))
        return _readiness(course3=True)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_readiness(
            requirement="course3",
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            live_context_seconds=2.5,
            loopback_signal_seconds=0.75,
        )
    )

    assert result["ok"] is True
    assert seen == [0.75]


def test_wait_for_readiness_passes_capture_matrix_seconds(monkeypatch) -> None:
    seen: list[float] = []

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        seen.append(float(kwargs.get("capture_matrix_seconds") or 0.0))
        return _readiness(course3=True)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_readiness(
            requirement="course3",
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            live_context_seconds=2.5,
            loopback_signal_seconds=0.75,
            capture_matrix_seconds=0.5,
        )
    )

    assert result["ok"] is True
    assert seen == [0.5]


def test_wait_for_readiness_passes_loopback_self_test_seconds(monkeypatch) -> None:
    seen: list[float] = []

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        seen.append(float(kwargs.get("loopback_self_test_seconds") or 0.0))
        return _readiness(course3=True)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_readiness(
            requirement="course3",
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            live_context_seconds=2.5,
            loopback_signal_seconds=0.75,
            loopback_self_test_seconds=0.4,
            capture_matrix_seconds=0.5,
        )
    )

    assert result["ok"] is True
    assert seen == [0.4]


def test_wait_for_loopback_signal_polls_until_signal_passes(monkeypatch) -> None:
    calls = 0

    def fake_collect(**_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _readiness(loopback_signal=calls >= 2)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_loopback_signal(
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            loopback_signal_seconds=0.25,
        )
    )

    assert result["ok"] is True
    assert result["attempts"] == 2
    assert result["last"]["checks"]["loopback_signal"]["ok"] is True


def test_wait_for_loopback_signal_uses_course3_route_lens(monkeypatch) -> None:
    seen: list[str] = []

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        seen.append(str(kwargs["requirement"]))
        return _readiness(loopback_signal=True)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_loopback_signal(
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            loopback_signal_seconds=0.25,
        )
    )

    assert result["ok"] is True
    assert seen == ["course3"]


def test_wait_for_capture_signal_polls_until_matrix_passes(monkeypatch) -> None:
    calls = 0

    def fake_collect(**_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _readiness(capture_signal=calls >= 2)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_capture_signal(
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            capture_matrix_seconds=0.25,
        )
    )

    assert result["ok"] is True
    assert result["attempts"] == 2
    assert result["last"]["checks"]["capture_matrix"]["top_signal"]["name"] == (
        "rekordbox Aggregate Device"
    )


def test_wait_for_capture_signal_uses_course3_route_lens(monkeypatch) -> None:
    seen: list[str] = []

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        seen.append(str(kwargs["requirement"]))
        return _readiness(capture_signal=True)

    monkeypatch.setattr(runner, "collect_readiness", fake_collect)

    result = asyncio.run(
        runner.wait_for_capture_signal(
            url="ws://127.0.0.1:8765",
            timeout_s=1.0,
            interval_s=0.01,
            capture_matrix_seconds=0.25,
        )
    )

    assert result["ok"] is True
    assert seen == ["course3"]


def test_run_proof_records_loopback_signal_wait_for_course3(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(screen=True, physical=True, course3=False, loopback_signal=False),
    )

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                course3=True,
                wait_loopback_signal_seconds=0.01,
                loopback_signal_seconds=0.01,
                loopback_self_test_seconds=0.01,
                capture_matrix_seconds=0.01,
                wait_interval=0.01,
            )
        )
    )

    assert report["passed"] is False
    assert report["stages"]["loopback_signal_wait"]["status"] == "failed"
    assert report["stages"]["loopback_signal_wait"]["result"]["last"]["checks"][
        "loopback_signal"
    ]["ok"] is False


def test_run_proof_records_capture_signal_wait_for_course3(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(screen=True, physical=True, course3=False, capture_signal=False),
    )

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                course3=True,
                wait_capture_signal_seconds=0.01,
                capture_matrix_seconds=0.01,
                wait_interval=0.01,
            )
        )
    )

    assert report["passed"] is False
    assert report["stages"]["capture_signal_wait"]["status"] == "failed"
    assert report["stages"]["capture_signal_wait"]["result"]["last"]["checks"][
        "capture_matrix"
    ]["ok"] is False


def test_run_proof_records_rekordbox_playback_nudge_for_course3(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(screen=True, physical=True, course3=False),
    )
    monkeypatch.setattr(
        runner,
        "nudge_rekordbox_playback",
        lambda **_kwargs: {"ok": True, "action": "rekordbox_spacebar"},
    )

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                course3=True,
                nudge_rekordbox_playback=True,
            )
        )
    )

    assert report["passed"] is False
    assert report["stages"]["rekordbox_playback_nudge"]["status"] == "passed"
    assert (
        report["stages"]["rekordbox_playback_nudge"]["result"]["action"]
        == "rekordbox_spacebar"
    )
    assert (
        report["stages"]["rekordbox_playback_nudge"]["result"]["precheck"]["ok"]
        is False
    )


def test_run_proof_records_course3_operator_say_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    prompts: list[tuple[str, bool]] = []

    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(screen=True, physical=True, course3=False),
    )

    def fake_say(text: str, *, enabled: bool) -> bool:
        prompts.append((text, enabled))
        return enabled

    monkeypatch.setattr(runner, "say_operator_prompt", fake_say)

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                course3=True,
                say_course3_prompts=True,
            )
        )
    )

    stage = report["stages"]["course3_operator_prompt"]
    assert stage["status"] == "passed"
    assert stage["result"]["spoken"] is True
    assert prompts == [(runner.COURSE3_OPERATOR_PROMPT, True)]


def test_run_proof_records_course3_route_doctor_say_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    prompts: list[tuple[str, bool]] = []
    next_step = (
        "Set Rekordbox's 'Aggregate Device' route, sampled as "
        "'rekordbox Aggregate Device', from 44100Hz to 48000Hz."
    )

    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(
            screen=True,
            physical=True,
            course3=False,
            course3_route_doctor={
                "diagnosis_code": "rekordbox_saved_route_capture_rate_mismatch",
                "next_step": next_step,
                "operator_steps": [next_step],
            },
        ),
    )

    def fake_say(text: str, *, enabled: bool) -> bool:
        prompts.append((text, enabled))
        return enabled

    monkeypatch.setattr(runner, "say_operator_prompt", fake_say)

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                course3=True,
                say_course3_prompts=True,
            )
        )
    )

    stage = report["stages"]["course3_operator_prompt"]
    assert stage["status"] == "passed"
    assert stage["result"]["prompt"] == next_step
    assert stage["result"]["prompt_source"] == "course3_route_doctor.next_step"
    assert stage["result"]["diagnosis_code"] == "rekordbox_saved_route_capture_rate_mismatch"
    assert prompts == [(next_step, True)]


def test_run_proof_skips_rekordbox_spacebar_when_course3_signal_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(
            screen=True,
            physical=True,
            course3=False,
            loopback_signal=True,
        ),
    )

    def fail_nudge(**_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("should not press space when signal is already present")

    monkeypatch.setattr(runner, "nudge_rekordbox_playback", fail_nudge)

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                course3=True,
                nudge_rekordbox_playback=True,
                loopback_signal_seconds=0.01,
                capture_matrix_seconds=0.01,
            )
        )
    )

    assert report["passed"] is False
    nudge = report["stages"]["rekordbox_playback_nudge"]["result"]
    assert nudge["action"] == "rekordbox_spacebar_skipped_signal_present"
    assert nudge["skipped"] is True
    assert nudge["precheck"]["loopback_ok"] is True


def test_run_proof_records_physical_wait_before_skip(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        runner,
        "collect_readiness",
        lambda **_kwargs: _readiness(screen=True, physical=False, course3=False),
    )

    report = asyncio.run(
        runner.run_proof(
            _args(
                tmp_path,
                screen=False,
                physical=True,
                wait_physical_seconds=0.01,
                wait_interval=0.01,
            )
        )
    )

    assert report["passed"] is False
    assert report["stages"]["physical_readiness_wait"]["status"] == "failed"
    assert report["stages"]["physical_readiness_wait"]["result"]["attempts"] >= 1
    assert report["stages"]["physical_probe"]["status"] == "skipped"


def test_runner_help_runs_when_invoked_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/run_learn_live_proof.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "--start-app" in proc.stdout
    assert "--wait-physical-seconds" in proc.stdout
    assert "--physical" in proc.stdout
    assert "--course3" in proc.stdout
    assert "--auto-master-input" in proc.stdout
    assert "--nudge-rekordbox-playback" in proc.stdout
    assert "--say-course3-prompts" in proc.stdout
    assert "--loopback-signal-seconds" in proc.stdout
    assert "--loopback-self-test-seconds" in proc.stdout
    assert "--capture-matrix-seconds" in proc.stdout
    assert "--wait-loopback-signal-seconds" in proc.stdout
    assert "--wait-capture-signal-seconds" in proc.stdout
