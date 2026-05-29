#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run Learn live-proof probes and persist one JSON artifact.

The individual probes answer narrow questions. This runner records the sequence
as a durable artifact for the integration handoff:

* readiness before probes,
* optional app start with isolated Learn progress,
* on-screen Learn proof,
* optional physical jog proof,
* optional Course 3 live-lens proof,
* progress-file evidence and exact blockers when a path is not ready.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.learn_live_readiness import (  # noqa: E402
    DEFAULT_WS_URL,
    check_socket,
    collect_readiness,
    requirement_to_readiness_key,
)
from scripts.live_course3_lens_probe import run_course3_lens_probe  # noqa: E402
from scripts.live_learn_screen_probe import run_screen_probe  # noqa: E402
from scripts.live_learn_socket_jog_probe import run_socket_probe  # noqa: E402
from scripts.validate_learn_live_proof import Requirement, validate_artifact  # noqa: E402

StageStatus = Literal["passed", "failed", "skipped"]
DEFAULT_PROGRESS_PATH = Path("/tmp/vibemix-live-learn-proof/learn-progress.json")
AUTO_MASTER_FALLBACK_ENV = "VIBEMIX_AUTO_MASTER_FALLBACK_DEVICE"
EXPECTED_INPUT_SAMPLE_RATE = 48000
LOOPBACK_NAME_TOKENS = ("blackhole", "loopback", "vb-cable", "soundflower", "aggregate")
COURSE3_OPERATOR_PROMPT = (
    "Route Rekordbox master audio to BlackHole. "
    "Press play on a deck with channel and master faders up."
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def default_artifact_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return _REPO_ROOT / ".planning" / "eval-runs" / f"learn-live-proof-{stamp}.json"


def make_stage(
    *,
    status: StageStatus,
    result: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"status": status}
    if reason:
        row["reason"] = reason
    if result is not None:
        row["result"] = result
    return row


def nudge_rekordbox_playback(*, delay_s: float = 0.2) -> dict[str, Any]:
    """Focus Rekordbox and press Space once to start/stop deck playback."""
    script = f"""
tell application "rekordbox" to activate
delay {max(0.0, float(delay_s)):.3f}
tell application "System Events"
    if not (exists process "rekordbox") then error "rekordbox process not visible"
    keystroke space
end tell
"""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "action": "rekordbox_spacebar",
            "error": repr(exc),
        }
    return {
        "ok": proc.returncode == 0,
        "action": "rekordbox_spacebar",
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def say_operator_prompt(text: str, *, enabled: bool) -> bool:
    """Speak an operator prompt on macOS. Best-effort and safe for CI."""
    if not enabled or sys.platform != "darwin":
        return False
    try:
        subprocess.Popen(
            ["say", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False
    return True


def course3_signal_summary(readiness: dict[str, Any]) -> dict[str, Any]:
    """Summarize whether Course 3 already has audio signal before toggling playback."""
    checks = readiness.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    readiness_map = readiness.get("readiness")
    readiness_map = readiness_map if isinstance(readiness_map, dict) else {}

    loopback = checks.get("loopback_signal")
    loopback_ok = isinstance(loopback, dict) and loopback.get("ok") is True
    capture = checks.get("capture_matrix")
    capture_ok = isinstance(capture, dict) and capture.get("ok") is True
    live_context = checks.get("course3_live_context")
    live_context_ok = (
        isinstance(live_context, dict)
        and live_context.get("audio_active") is True
        and live_context.get("deck_attributed") is True
    )
    course3_audio_ready = readiness_map.get("course3_audio") is True
    top_signal = capture.get("top_signal") if isinstance(capture, dict) else None
    return {
        "ok": bool(loopback_ok or capture_ok or live_context_ok or course3_audio_ready),
        "loopback_ok": loopback_ok,
        "capture_ok": capture_ok,
        "live_context_ok": live_context_ok,
        "course3_audio_ready": course3_audio_ready,
        "loopback_rms": loopback.get("rms") if isinstance(loopback, dict) else None,
        "loopback_peak": loopback.get("peak") if isinstance(loopback, dict) else None,
        "top_signal": top_signal if isinstance(top_signal, dict) else None,
    }


def course3_operator_prompt_text(readiness: dict[str, Any]) -> dict[str, Any]:
    """Pick the most specific Course 3 operator prompt available."""
    route_doctor = readiness.get("course3_route_doctor")
    if isinstance(route_doctor, dict):
        next_step = str(route_doctor.get("next_step") or "").strip()
        if next_step:
            return {
                "prompt": next_step,
                "source": "course3_route_doctor.next_step",
                "diagnosis_code": route_doctor.get("diagnosis_code"),
                "route": route_doctor.get("route"),
                "operator_steps": route_doctor.get("operator_steps")
                if isinstance(route_doctor.get("operator_steps"), list)
                else None,
            }

    diagnosis = readiness.get("course3_audio_diagnosis")
    if isinstance(diagnosis, dict):
        next_action = str(diagnosis.get("next_action") or "").strip()
        if next_action:
            return {
                "prompt": next_action,
                "source": "course3_audio_diagnosis.next_action",
                "diagnosis_code": diagnosis.get("code"),
                "route": None,
                "operator_steps": None,
            }

    return {
        "prompt": COURSE3_OPERATOR_PROMPT,
        "source": "fallback",
        "diagnosis_code": None,
        "route": None,
        "operator_steps": None,
    }


def course3_operator_prompt_summary(
    readiness: dict[str, Any],
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Record whether the external Course 3 playback cue was spoken."""
    signal = course3_signal_summary(readiness)
    should_prompt = signal["ok"] is not True
    prompt = course3_operator_prompt_text(readiness)
    spoken = say_operator_prompt(
        str(prompt["prompt"]),
        enabled=enabled and should_prompt,
    )
    return {
        "enabled": bool(enabled),
        "prompt": prompt["prompt"],
        "prompt_source": prompt["source"],
        "diagnosis_code": prompt["diagnosis_code"],
        "route": prompt["route"],
        "operator_steps": prompt["operator_steps"],
        "spoken": spoken,
        "skipped": not should_prompt,
        "reason": (
            "Course 3 signal already present; no external playback prompt needed."
            if not should_prompt
            else "Course 3 signal absent; operator prompt requested."
        ),
        "precheck": signal,
    }


def maybe_nudge_rekordbox_playback(
    *,
    url: str,
    delay_s: float,
    live_context_seconds: float,
    loopback_signal_seconds: float,
    capture_matrix_seconds: float,
) -> dict[str, Any]:
    """Press Space only when Course 3 signal is not already present."""
    precheck = collect_readiness(
        requirement="course3",
        url=url,
        live_context_seconds=max(0.0, live_context_seconds),
        loopback_signal_seconds=loopback_signal_seconds if loopback_signal_seconds > 0 else 0.5,
        loopback_self_test_seconds=0.0,
        capture_matrix_seconds=capture_matrix_seconds if capture_matrix_seconds > 0 else 0.5,
    )
    signal = course3_signal_summary(precheck)
    if signal["ok"] is True:
        return {
            "ok": True,
            "action": "rekordbox_spacebar_skipped_signal_present",
            "skipped": True,
            "reason": "Course 3 signal is already present; not toggling Rekordbox playback.",
            "precheck": signal,
        }
    result = nudge_rekordbox_playback(delay_s=delay_s)
    result["precheck"] = signal
    return result


def artifact_passed(
    stages: dict[str, dict[str, Any]],
    *,
    require_screen: bool,
    require_physical: bool,
    require_course3: bool,
) -> bool:
    if require_screen and stages.get("screen_probe", {}).get("status") != "passed":
        return False
    if require_physical and stages.get("physical_probe", {}).get("status") != "passed":
        return False
    if require_course3 and stages.get("course3_probe", {}).get("status") != "passed":
        return False
    return True


def requested_requirements(args: argparse.Namespace) -> set[Requirement]:
    requirements: set[Requirement] = set()
    if args.screen:
        requirements.add("screen")
    if args.physical:
        requirements.add("physical")
    if args.course3:
        requirements.add("course3")
    return requirements


def broadest_readiness_requirement(args: argparse.Namespace) -> Requirement:
    """Pick the most demanding route lens needed by this proof run."""
    if args.course3:
        return "course3"
    if args.physical:
        return "physical"
    if args.screen:
        return "screen"
    return "none"


def write_artifact(report: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def read_progress_file(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def seed_course3_unlocked_progress(path: Path) -> dict[str, Any]:
    """Write proof-only unlocked progress so Course 3 lessons can be started."""
    from vibemix.learn.progress import LearnProgress

    progress = LearnProgress(course_2_unlocked=True, course_3_unlocked=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(progress.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "path": str(path),
        "schema_version": progress.schema_version,
        "course_2_unlocked": progress.course_2_unlocked,
        "course_3_unlocked": progress.course_3_unlocked,
    }


def _loopbackish_name(name: str | None) -> bool:
    value = str(name or "").strip().lower()
    return bool(value) and any(token in value for token in LOOPBACK_NAME_TOKENS)


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _rekordbox_settings_output(readiness: dict[str, Any]) -> str | None:
    checks = readiness.get("checks")
    if not isinstance(checks, dict):
        return None
    settings = checks.get("rekordbox_audio_settings")
    if not isinstance(settings, dict):
        return None
    current = settings.get("current")
    if not isinstance(current, dict):
        return None
    output = current.get("audio_output_device_name")
    return str(output).strip() if output else None


def _capture_matrix_row(readiness: dict[str, Any], device_name: str) -> dict[str, Any] | None:
    checks = readiness.get("checks")
    if not isinstance(checks, dict):
        return None
    matrix = checks.get("capture_matrix")
    if not isinstance(matrix, dict):
        return None
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        return None
    target = device_name.strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("name") or "").strip().lower() == target:
            return row
    return None


def _auto_master_recommendation(readiness: dict[str, Any]) -> dict[str, Any] | None:
    recommendation = readiness.get("auto_master_recommendation")
    return recommendation if isinstance(recommendation, dict) else None


def resolve_app_audio_env(
    *,
    input_device: str | None,
    output_device: str | None,
    mic_device: str | None,
    auto_master_input: bool,
    readiness_before: dict[str, Any],
) -> dict[str, Any]:
    """Resolve audio env plus a safe auto-master fallback for proof runs."""
    plan: dict[str, Any] = {
        "input_device": input_device,
        "output_device": output_device,
        "mic_device": mic_device,
        "auto_master_input": bool(auto_master_input),
        "auto_master_fallback_device": None,
        "auto_master_fallback_source": None,
        "auto_master_fallback_candidate": None,
        "auto_master_fallback_rejected_reason": None,
    }
    if input_device or not auto_master_input:
        return plan

    recommendation = _auto_master_recommendation(readiness_before)
    if recommendation and recommendation.get("device_name"):
        plan["auto_master_fallback_candidate"] = {
            "name": recommendation.get("device_name"),
            "sample_rate": recommendation.get("sample_rate"),
            "source": recommendation.get("source"),
            "reason": recommendation.get("reason"),
            "live_signal": recommendation.get("live_signal"),
        }
        sample_rate = _safe_int(recommendation.get("sample_rate"))
        if sample_rate is not None and sample_rate != EXPECTED_INPUT_SAMPLE_RATE:
            plan["auto_master_fallback_rejected_reason"] = (
                f"{recommendation.get('device_name')} is {sample_rate}Hz; "
                f"vibemix capture expects {EXPECTED_INPUT_SAMPLE_RATE}Hz"
            )
            return plan
        if recommendation.get("ok") is True:
            plan["auto_master_fallback_device"] = str(recommendation["device_name"])
            plan["auto_master_fallback_source"] = str(recommendation.get("source") or "readiness")
            return plan

    candidate = _rekordbox_settings_output(readiness_before)
    if candidate is None or not _loopbackish_name(candidate):
        return plan

    row = _capture_matrix_row(readiness_before, candidate)
    sample_rate = _safe_int(row.get("sample_rate")) if isinstance(row, dict) else None
    plan["auto_master_fallback_candidate"] = {
        "name": candidate,
        "sample_rate": sample_rate,
        "source": "rekordbox_audio_settings",
    }
    if not isinstance(row, dict):
        plan["auto_master_fallback_rejected_reason"] = (
            f"{candidate} was not sampled in the capture matrix; "
            "not using it as an auto-master fallback"
        )
        return plan
    if sample_rate is not None and sample_rate != EXPECTED_INPUT_SAMPLE_RATE:
        plan["auto_master_fallback_rejected_reason"] = (
            f"{candidate} is {sample_rate}Hz; vibemix capture expects "
            f"{EXPECTED_INPUT_SAMPLE_RATE}Hz"
        )
        return plan

    plan["auto_master_fallback_device"] = candidate
    plan["auto_master_fallback_source"] = "rekordbox_audio_settings"
    return plan


async def wait_for_socket(url: str, *, timeout_s: float = 20.0) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.1, timeout_s)
    last: dict[str, Any] = {"ok": False, "url": url}
    while time.monotonic() < deadline:
        last = check_socket(url)
        if last.get("ok") is True:
            return last
        await asyncio.sleep(0.2)
    return last


async def wait_for_readiness(
    *,
    requirement: str,
    url: str,
    timeout_s: float,
    interval_s: float,
    live_context_seconds: float = 0.0,
    loopback_signal_seconds: float = 0.0,
    loopback_self_test_seconds: float = 0.0,
    capture_matrix_seconds: float = 0.0,
) -> dict[str, Any]:
    """Poll live readiness until a requirement passes or timeout expires."""
    started = time.monotonic()
    deadline = started + max(0.0, timeout_s)
    attempts = 0
    last: dict[str, Any] | None = None
    while True:
        attempts += 1
        last = collect_readiness(  # type: ignore[arg-type]
            requirement=requirement,
            url=url,
            live_context_seconds=live_context_seconds,
            loopback_signal_seconds=loopback_signal_seconds,
            loopback_self_test_seconds=loopback_self_test_seconds,
            capture_matrix_seconds=capture_matrix_seconds,
        )
        readiness = last.get("readiness")
        readiness_key = requirement_to_readiness_key(requirement)  # type: ignore[arg-type]
        if isinstance(readiness, dict) and readiness.get(readiness_key) is True:
            return {
                "ok": True,
                "requirement": requirement,
                "attempts": attempts,
                "elapsed_s": round(time.monotonic() - started, 3),
                "last": last,
            }
        now = time.monotonic()
        if now >= deadline:
            return {
                "ok": False,
                "requirement": requirement,
                "attempts": attempts,
                "elapsed_s": round(now - started, 3),
                "last": last,
            }
        await asyncio.sleep(min(max(0.05, interval_s), max(0.0, deadline - now)))


async def wait_for_loopback_signal(
    *,
    url: str,
    timeout_s: float,
    interval_s: float,
    loopback_signal_seconds: float,
    requirement: Requirement = "course3",
    loopback_self_test_seconds: float = 0.0,
    capture_matrix_seconds: float = 0.0,
) -> dict[str, Any]:
    """Poll direct loopback capture until signal is present or timeout expires."""
    started = time.monotonic()
    deadline = started + max(0.0, timeout_s)
    attempts = 0
    last: dict[str, Any] | None = None
    sample_seconds = loopback_signal_seconds if loopback_signal_seconds > 0 else 0.5
    while True:
        attempts += 1
        last = collect_readiness(
            requirement=requirement,
            url=url,
            loopback_signal_seconds=sample_seconds,
            loopback_self_test_seconds=loopback_self_test_seconds,
            capture_matrix_seconds=capture_matrix_seconds,
        )
        checks = last.get("checks")
        signal = checks.get("loopback_signal") if isinstance(checks, dict) else None
        if isinstance(signal, dict) and signal.get("ok") is True:
            return {
                "ok": True,
                "attempts": attempts,
                "elapsed_s": round(time.monotonic() - started, 3),
                "sample_seconds": sample_seconds,
                "last": last,
            }
        now = time.monotonic()
        if now >= deadline:
            return {
                "ok": False,
                "attempts": attempts,
                "elapsed_s": round(now - started, 3),
                "sample_seconds": sample_seconds,
                "last": last,
            }
        await asyncio.sleep(min(max(0.05, interval_s), max(0.0, deadline - now)))


async def wait_for_capture_signal(
    *,
    url: str,
    timeout_s: float,
    interval_s: float,
    capture_matrix_seconds: float,
    requirement: Requirement = "course3",
    loopback_signal_seconds: float = 0.0,
    loopback_self_test_seconds: float = 0.0,
) -> dict[str, Any]:
    """Poll the capture matrix until any sampled input carries signal."""
    started = time.monotonic()
    deadline = started + max(0.0, timeout_s)
    attempts = 0
    last: dict[str, Any] | None = None
    sample_seconds = capture_matrix_seconds if capture_matrix_seconds > 0 else 0.5
    while True:
        attempts += 1
        last = collect_readiness(
            requirement=requirement,
            url=url,
            loopback_signal_seconds=loopback_signal_seconds,
            loopback_self_test_seconds=loopback_self_test_seconds,
            capture_matrix_seconds=sample_seconds,
        )
        checks = last.get("checks")
        matrix = checks.get("capture_matrix") if isinstance(checks, dict) else None
        if isinstance(matrix, dict) and matrix.get("ok") is True:
            return {
                "ok": True,
                "attempts": attempts,
                "elapsed_s": round(time.monotonic() - started, 3),
                "sample_seconds": sample_seconds,
                "last": last,
            }
        now = time.monotonic()
        if now >= deadline:
            return {
                "ok": False,
                "attempts": attempts,
                "elapsed_s": round(now - started, 3),
                "sample_seconds": sample_seconds,
                "last": last,
            }
        await asyncio.sleep(min(max(0.05, interval_s), max(0.0, deadline - now)))


def start_app(
    progress_path: Path,
    *,
    input_device: str | None = None,
    output_device: str | None = None,
    mic_device: str | None = None,
    auto_master_input: bool = False,
    auto_master_fallback_device: str | None = None,
) -> subprocess.Popen[str]:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["VIBEMIX_LEARN_PROGRESS_PATH"] = str(progress_path)
    if input_device:
        env["VIBEMIX_INPUT_DEVICE"] = input_device
    if output_device:
        env["VIBEMIX_OUTPUT_DEVICE"] = output_device
    if mic_device:
        env["VIBEMIX_MIC_DEVICE"] = mic_device
    if auto_master_input:
        env["VIBEMIX_AUTO_MASTER_INPUT"] = "1"
    if auto_master_fallback_device:
        env[AUTO_MASTER_FALLBACK_ENV] = auto_master_fallback_device
    return subprocess.Popen(
        [sys.executable, "-m", "vibemix"],
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_app(proc: subprocess.Popen[str] | None) -> dict[str, Any] | None:
    if proc is None:
        return None
    if proc.poll() is None:
        try:
            proc.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
    try:
        stdout, stderr = proc.communicate(timeout=12.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=5.0)
        audio_runtime = parse_app_audio_runtime(stderr)
        return {
            "returncode": proc.returncode,
            "forced_kill": True,
            "audio_runtime": audio_runtime,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
    audio_runtime = parse_app_audio_runtime(stderr)
    return {
        "returncode": proc.returncode,
        "forced_kill": False,
        "audio_runtime": audio_runtime,
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
    }


def _tail(text: str | None, *, max_chars: int = 4000) -> str:
    text = text or ""
    return text[-max_chars:]


_AUTO_MASTER_LINE_RE = re.compile(
    r"^\[audio\] auto master input: "
    r"(?P<name>.+?) @ (?P<sample_rate>\d+)Hz"
    r"(?: rms=(?P<rms>[0-9.]+) peak=(?P<peak>[0-9.]+))?"
    r"(?P<suffix>.*)$"
)


def parse_app_audio_runtime(stderr: str | None) -> dict[str, Any]:
    """Extract machine-readable audio startup decisions from app stderr."""
    result: dict[str, Any] = {}
    for line in (stderr or "").splitlines():
        match = _AUTO_MASTER_LINE_RE.match(line.strip())
        if match is None:
            continue
        suffix = match.group("suffix") or ""
        rms = match.group("rms")
        peak = match.group("peak")
        auto_master: dict[str, Any] = {
            "selected": True,
            "name": match.group("name"),
            "sample_rate": int(match.group("sample_rate")),
            "live_signal": rms is not None,
            "reason": "live_signal" if rms is not None else "48k_fallback",
            "raw": line.strip(),
        }
        if rms is not None:
            auto_master["rms"] = float(rms)
        if peak is not None:
            auto_master["peak"] = float(peak)
        suffix_low = suffix.lower()
        if "preferred fallback" in suffix_low:
            auto_master["live_signal"] = False
            auto_master["reason"] = "preferred_fallback"
        elif "no live signal" in suffix_low:
            auto_master["live_signal"] = False
            auto_master["reason"] = "48k_fallback"
        result["auto_master_input"] = auto_master
    return result


def attach_app_audio_runtime(
    stages: dict[str, dict[str, Any]],
    stop_result: dict[str, Any],
) -> None:
    """Copy runtime audio decisions onto app_start for easier artifact reading."""
    audio_runtime = stop_result.get("audio_runtime")
    if not isinstance(audio_runtime, dict) or not audio_runtime:
        return
    app_start_result = stages.get("app_start", {}).get("result")
    if isinstance(app_start_result, dict):
        app_start_result["audio_runtime"] = audio_runtime


async def run_proof(args: argparse.Namespace) -> dict[str, Any]:
    started_at = now_iso()
    stages: dict[str, dict[str, Any]] = {}
    app_proc: subprocess.Popen[str] | None = None
    progress_path = Path(args.progress_path).expanduser()
    readiness_requirement = broadest_readiness_requirement(args)

    readiness_before = collect_readiness(
        requirement=readiness_requirement,
        url=args.url,
        loopback_signal_seconds=args.loopback_signal_seconds,
        loopback_self_test_seconds=args.loopback_self_test_seconds,
        capture_matrix_seconds=args.capture_matrix_seconds,
    )
    stages["readiness_before"] = make_stage(
        status="passed",
        result=readiness_before,
    )
    app_audio_env = resolve_app_audio_env(
        input_device=args.input_device,
        output_device=args.output_device,
        mic_device=args.mic_device,
        auto_master_input=args.auto_master_input,
        readiness_before=readiness_before,
    )

    if args.seed_course3_unlocked:
        stages["progress_seed"] = make_stage(
            status="passed",
            result=seed_course3_unlocked_progress(progress_path),
        )
    else:
        stages["progress_seed"] = make_stage(
            status="skipped",
            reason="--seed-course3-unlocked not set",
        )

    if args.start_app:
        app_proc = start_app(
            progress_path,
            input_device=app_audio_env["input_device"],
            output_device=app_audio_env["output_device"],
            mic_device=app_audio_env["mic_device"],
            auto_master_input=app_audio_env["auto_master_input"],
            auto_master_fallback_device=app_audio_env["auto_master_fallback_device"],
        )
        socket_after_start = await wait_for_socket(args.url, timeout_s=args.start_timeout)
        stages["app_start"] = make_stage(
            status="passed" if socket_after_start.get("ok") else "failed",
            result={
                "pid": app_proc.pid,
                "socket": socket_after_start,
                "progress_path": str(progress_path),
                "audio_env": app_audio_env,
            },
        )
    else:
        stages["app_start"] = make_stage(status="skipped", reason="--start-app not set")

    try:
        readiness = collect_readiness(
            requirement=readiness_requirement,
            url=args.url,
            loopback_signal_seconds=args.loopback_signal_seconds,
            loopback_self_test_seconds=args.loopback_self_test_seconds,
            capture_matrix_seconds=args.capture_matrix_seconds,
        )
        stages["readiness_before_probes"] = make_stage(status="passed", result=readiness)

        if args.screen:
            if readiness["readiness"]["screen_learn"]:
                screen_result = await run_screen_probe(
                    url=args.url,
                    seconds=args.screen_seconds,
                    lesson_id=args.screen_lesson_id,
                )
                stages["screen_probe"] = make_stage(
                    status="passed" if screen_result.get("passed") else "failed",
                    result=screen_result,
                )
            else:
                stages["screen_probe"] = make_stage(
                    status="failed",
                    reason="screen readiness failed",
                    result=readiness,
                )
        else:
            stages["screen_probe"] = make_stage(status="skipped", reason="--no-screen set")

        readiness_after_screen = collect_readiness(
            requirement=readiness_requirement,
            url=args.url,
            loopback_signal_seconds=args.loopback_signal_seconds,
            loopback_self_test_seconds=args.loopback_self_test_seconds,
            capture_matrix_seconds=args.capture_matrix_seconds,
        )
        stages["readiness_after_screen"] = make_stage(
            status="passed",
            result=readiness_after_screen,
        )

        if args.physical:
            physical_readiness = collect_readiness(
                requirement="physical",
                url=args.url,
                loopback_signal_seconds=args.loopback_signal_seconds,
                loopback_self_test_seconds=args.loopback_self_test_seconds,
                capture_matrix_seconds=args.capture_matrix_seconds,
            )
            if (
                not physical_readiness["readiness"]["physical_learn"]
                and args.wait_physical_seconds > 0
            ):
                wait_result = await wait_for_readiness(
                    requirement="physical",
                    url=args.url,
                    timeout_s=args.wait_physical_seconds,
                    interval_s=args.wait_interval,
                    loopback_signal_seconds=args.loopback_signal_seconds,
                    loopback_self_test_seconds=args.loopback_self_test_seconds,
                    capture_matrix_seconds=args.capture_matrix_seconds,
                )
                stages["physical_readiness_wait"] = make_stage(
                    status="passed" if wait_result.get("ok") else "failed",
                    result=wait_result,
                )
                physical_readiness = wait_result.get("last") or physical_readiness
            else:
                stages["physical_readiness_wait"] = make_stage(
                    status="skipped",
                    reason="physical ready already or wait not requested",
                    result=physical_readiness,
                )

            if physical_readiness["readiness"]["physical_learn"]:
                physical_result = await run_socket_probe(
                    url=args.url,
                    seconds=args.physical_seconds,
                    say_prompts=args.say_physical_prompts,
                )
                stages["physical_probe"] = make_stage(
                    status="passed" if physical_result.get("passed") else "failed",
                    result=physical_result,
                )
            else:
                stages["physical_probe"] = make_stage(
                    status="skipped",
                    reason="physical readiness failed",
                    result=physical_readiness,
                )
        else:
            stages["physical_readiness_wait"] = make_stage(
                status="skipped",
                reason="--physical not set",
            )
            stages["physical_probe"] = make_stage(status="skipped", reason="--physical not set")

        if args.course3:
            course3_prompt = course3_operator_prompt_summary(
                readiness_after_screen,
                enabled=args.say_course3_prompts,
            )
            stages["course3_operator_prompt"] = make_stage(
                status="passed" if course3_prompt.get("skipped") or course3_prompt.get("spoken") else "skipped",
                reason=None if course3_prompt.get("spoken") else str(course3_prompt.get("reason")),
                result=course3_prompt,
            )
            if args.nudge_rekordbox_playback:
                nudge_result = maybe_nudge_rekordbox_playback(
                    url=args.url,
                    delay_s=args.rekordbox_nudge_delay,
                    live_context_seconds=args.course3_context_seconds,
                    loopback_signal_seconds=args.loopback_signal_seconds,
                    capture_matrix_seconds=args.capture_matrix_seconds,
                )
                stages["rekordbox_playback_nudge"] = make_stage(
                    status="passed" if nudge_result.get("ok") else "failed",
                    result=nudge_result,
                )
            else:
                stages["rekordbox_playback_nudge"] = make_stage(
                    status="skipped",
                    reason="--nudge-rekordbox-playback not set",
                )
            if args.wait_capture_signal_seconds > 0:
                wait_capture_result = await wait_for_capture_signal(
                    url=args.url,
                    timeout_s=args.wait_capture_signal_seconds,
                    interval_s=args.wait_interval,
                    capture_matrix_seconds=args.capture_matrix_seconds,
                    loopback_signal_seconds=args.loopback_signal_seconds,
                    loopback_self_test_seconds=args.loopback_self_test_seconds,
                )
                stages["capture_signal_wait"] = make_stage(
                    status="passed" if wait_capture_result.get("ok") else "failed",
                    result=wait_capture_result,
                )
            else:
                stages["capture_signal_wait"] = make_stage(
                    status="skipped",
                    reason="--wait-capture-signal-seconds not set",
                )
            if args.wait_loopback_signal_seconds > 0:
                wait_signal_result = await wait_for_loopback_signal(
                    url=args.url,
                    timeout_s=args.wait_loopback_signal_seconds,
                    interval_s=args.wait_interval,
                    loopback_signal_seconds=args.loopback_signal_seconds,
                    loopback_self_test_seconds=args.loopback_self_test_seconds,
                    capture_matrix_seconds=args.capture_matrix_seconds,
                )
                stages["loopback_signal_wait"] = make_stage(
                    status="passed" if wait_signal_result.get("ok") else "failed",
                    result=wait_signal_result,
                )
            else:
                stages["loopback_signal_wait"] = make_stage(
                    status="skipped",
                    reason="--wait-loopback-signal-seconds not set",
                )
            course3_readiness = collect_readiness(
                requirement="course3",
                url=args.url,
                live_context_seconds=args.course3_context_seconds,
                loopback_signal_seconds=args.loopback_signal_seconds,
                loopback_self_test_seconds=args.loopback_self_test_seconds,
                capture_matrix_seconds=args.capture_matrix_seconds,
            )
            if (
                not course3_readiness["readiness"]["course3_audio"]
                and args.wait_course3_seconds > 0
            ):
                wait_result = await wait_for_readiness(
                    requirement="course3",
                    url=args.url,
                    timeout_s=args.wait_course3_seconds,
                    interval_s=args.wait_interval,
                    live_context_seconds=args.course3_context_seconds,
                    loopback_signal_seconds=args.loopback_signal_seconds,
                    loopback_self_test_seconds=args.loopback_self_test_seconds,
                    capture_matrix_seconds=args.capture_matrix_seconds,
                )
                stages["course3_readiness_wait"] = make_stage(
                    status="passed" if wait_result.get("ok") else "failed",
                    result=wait_result,
                )
                course3_readiness = wait_result.get("last") or course3_readiness
            else:
                stages["course3_readiness_wait"] = make_stage(
                    status="skipped",
                    reason="course3 ready already or wait not requested",
                    result=course3_readiness,
                )
            if course3_readiness["readiness"]["course3_audio"]:
                course3_result = await run_course3_lens_probe(
                    url=args.url,
                    seconds=args.course3_seconds,
                    require_active=True,
                    require_count_in=args.require_count_in,
                    start_lesson_id=args.course3_lesson_id,
                )
                stages["course3_probe"] = make_stage(
                    status="passed" if course3_result.get("passed") else "failed",
                    result=course3_result,
                )
            else:
                stages["course3_probe"] = make_stage(
                    status="skipped",
                    reason="course3 readiness failed",
                    result=course3_readiness,
                )
        else:
            stages["rekordbox_playback_nudge"] = make_stage(
                status="skipped",
                reason="--course3 not set",
            )
            stages["capture_signal_wait"] = make_stage(
                status="skipped",
                reason="--course3 not set",
            )
            stages["loopback_signal_wait"] = make_stage(
                status="skipped",
                reason="--course3 not set",
            )
            stages["course3_operator_prompt"] = make_stage(
                status="skipped",
                reason="--course3 not set",
            )
            stages["course3_readiness_wait"] = make_stage(
                status="skipped",
                reason="--course3 not set",
            )
            stages["course3_probe"] = make_stage(status="skipped", reason="--course3 not set")
    finally:
        stop_result = stop_app(app_proc)
        if stop_result is not None:
            attach_app_audio_runtime(stages, stop_result)
            stages["app_stop"] = make_stage(
                status="passed" if stop_result.get("returncode") == 0 else "failed",
                result=stop_result,
            )

    progress_snapshot = read_progress_file(progress_path)
    progress_status: StageStatus = "skipped"
    progress_reason = "progress file not present"
    if progress_snapshot is not None:
        if stages.get("screen_probe", {}).get("status") == "passed":
            progress_status = "passed"
            progress_reason = None
        else:
            progress_reason = "progress file exists but no screen proof passed in this run"
    stages["progress_file"] = make_stage(
        status=progress_status,
        reason=progress_reason,
        result={
            "path": str(progress_path),
            "snapshot": progress_snapshot,
        },
    )

    finished_at = now_iso()
    requirements = {
        "screen": bool(args.screen),
        "physical": bool(args.physical),
        "course3": bool(args.course3),
    }
    report = {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": finished_at,
        "url": args.url,
        "requirements": requirements,
        "passed": False,
        "stages": stages,
    }
    validation = validate_artifact(
        report,
        required=requested_requirements(args),
        allow_skipped=set(),
    )
    report["validation"] = validation
    report["passed"] = bool(validation.get("valid"))
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_learn_live_proof",
        description="Run Learn live-proof probes and write one JSON artifact.",
    )
    parser.add_argument("--url", default=DEFAULT_WS_URL, help=f"Sidecar URL (default: {DEFAULT_WS_URL}).")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON artifact path.")
    parser.add_argument(
        "--progress-path",
        default=str(DEFAULT_PROGRESS_PATH),
        help=f"Isolated Learn progress path (default: {DEFAULT_PROGRESS_PATH}).",
    )
    parser.add_argument(
        "--seed-course3-unlocked",
        action="store_true",
        help="Seed the isolated progress file with Course 2/3 unlocked before starting the app.",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="Override VIBEMIX_INPUT_DEVICE for --start-app, e.g. 'BlackHole 16ch' or 'auto'.",
    )
    parser.add_argument(
        "--output-device",
        default=None,
        help="Override VIBEMIX_OUTPUT_DEVICE for --start-app.",
    )
    parser.add_argument(
        "--mic-device",
        default=None,
        help="Override VIBEMIX_MIC_DEVICE for --start-app.",
    )
    parser.add_argument(
        "--auto-master-input",
        action="store_true",
        help="Let the sidecar sample loopback/capture inputs and pick the live master input.",
    )
    parser.add_argument("--start-app", action="store_true", help="Start python -m vibemix for the run.")
    parser.add_argument("--start-timeout", type=float, default=25.0, help="Seconds to wait for sidecar socket.")
    parser.add_argument("--no-screen", dest="screen", action="store_false", help="Skip the screen Learn proof.")
    parser.set_defaults(screen=True)
    parser.add_argument("--screen-seconds", type=float, default=60.0, help="Screen proof capture window.")
    parser.add_argument("--screen-lesson-id", default="L1.01", help="Screen proof lesson id.")
    parser.add_argument("--physical", action="store_true", help="Attempt the live L1.07 jog socket proof.")
    parser.add_argument("--physical-seconds", type=float, default=20.0, help="Physical jog proof window.")
    parser.add_argument(
        "--say-physical-prompts",
        action="store_true",
        help="On macOS, speak the physical jog prompt with say(1).",
    )
    parser.add_argument(
        "--wait-physical-seconds",
        type=float,
        default=0.0,
        help="Poll for physical readiness before skipping the jog proof.",
    )
    parser.add_argument("--course3", action="store_true", help="Attempt the Course 3 live-lens proof.")
    parser.add_argument(
        "--nudge-rekordbox-playback",
        action="store_true",
        help=(
            "Before Course 3 waits, check for routed signal; if silent, focus "
            "Rekordbox and press Space once. Records the precheck and automation "
            "result in the artifact."
        ),
    )
    parser.add_argument(
        "--rekordbox-nudge-delay",
        type=float,
        default=0.2,
        help="Seconds to wait after focusing Rekordbox before pressing Space.",
    )
    parser.add_argument(
        "--say-course3-prompts",
        action="store_true",
        help="On macOS, speak the Course 3 route/playback prompt with say(1).",
    )
    parser.add_argument("--course3-seconds", type=float, default=30.0, help="Course 3 lens proof window.")
    parser.add_argument(
        "--course3-context-seconds",
        type=float,
        default=1.5,
        help=(
            "Before Course 3 proof, sample the live socket for audible deck "
            "and citable deck_state context."
        ),
    )
    parser.add_argument(
        "--loopback-signal-seconds",
        type=float,
        default=0.0,
        help="Optionally sample the selected loopback input directly and record RMS/peak.",
    )
    parser.add_argument(
        "--loopback-self-test-seconds",
        type=float,
        default=0.0,
        help="Optionally inject a quiet known tone through the selected loopback device.",
    )
    parser.add_argument(
        "--capture-matrix-seconds",
        type=float,
        default=0.0,
        help="Optionally sample DJ/controller/loopback inputs and rank where signal is present.",
    )
    parser.add_argument(
        "--course3-lesson-id",
        default="L3.01",
        help="Course 3 lesson to start before watching the live lens. Use '' to skip.",
    )
    parser.add_argument(
        "--wait-course3-seconds",
        type=float,
        default=0.0,
        help="Poll for Course 3 readiness before skipping the lens proof.",
    )
    parser.add_argument(
        "--wait-loopback-signal-seconds",
        type=float,
        default=0.0,
        help="Before Course 3 proof, poll direct loopback capture until RMS crosses the floor.",
    )
    parser.add_argument(
        "--wait-capture-signal-seconds",
        type=float,
        default=0.0,
        help="Before Course 3 proof, poll the capture matrix until any sampled input has signal.",
    )
    parser.add_argument(
        "--wait-interval",
        type=float,
        default=2.0,
        help="Seconds between readiness polls while waiting for hardware.",
    )
    parser.add_argument(
        "--require-count-in",
        action="store_true",
        help="For Course 3, require active next-phrase count-in evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_path = args.out or default_artifact_path()
    try:
        report = asyncio.run(run_proof(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        report = {
            "schema_version": 1,
            "started_at": now_iso(),
            "finished_at": now_iso(),
            "passed": False,
            "error": repr(exc),
            "stages": {},
        }
    path = write_artifact(report, Path(out_path))
    print(json.dumps({"passed": report.get("passed") is True, "artifact": str(path)}, sort_keys=True))
    return 0 if report.get("passed") is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
