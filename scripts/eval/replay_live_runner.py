# SPDX-License-Identifier: Apache-2.0
"""Live replay runner for the overnight QA harness.

This is the realtime half of replay QA: launch current-source ``python -m vibemix``
with ``VIBEMIX_REPLAY_SESSION`` pointed at a recorded session directory, isolate
HOME + ports per instance, let the app run briefly, stop with SIGINT, then write a
findings report from stdout/stderr + the recording artifacts it produced.

It does not judge Sven's prose and it does not time-warp. Its job is narrower and
load-bearing: prove the real app can hear a replayed set without physical audio
hardware or room speakers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import wave
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_MUSIC_RE = re.compile(r"music=([0-9]+(?:\.[0-9]+)?)")
_AUDIBLE_RE = re.compile(r"audible=1")
_FATAL_RE = re.compile(r"(Traceback|\\bFATAL\\b)", re.IGNORECASE)
_LLM_TO_TTS_DELTA_EVENT_TYPE = "llm_to_tts_delta_ms"
_LATE_LLM_TO_TTS_BUDGET_MS = 6000.0


@dataclass(frozen=True)
class LiveReplayConfig:
    repo_root: Path
    output_dir: Path
    duration_s: float = 20.0
    stop_grace_s: float = 5.0
    base_ws_port: int = 18765
    base_debrief_port: int = 18865
    output_device: str | None = "BlackHole 2ch"
    python_executable: str = sys.executable


@dataclass
class LiveReplayResult:
    scenario: str
    session_dir: Path
    run_dir: Path
    home_dir: Path
    ws_port: int
    debrief_port: int
    returncode: int | None
    stdout_path: Path
    stderr_path: Path
    recording_dir: Path | None
    recording_input_wav: Path | None
    recording_input_duration_s: float
    events_jsonl: Path | None
    max_music: float
    audible_seen: bool
    replay_capture_seen: bool
    replay_midi_seen: bool
    replay_nowplaying_seen: bool
    ws_seen: bool
    voice_muted_seen: bool
    fatal_seen: bool
    killed_after_timeout: bool = False
    command: list[str] = field(default_factory=list)


def discover_sessions(corpus_root: Path) -> list[Path]:
    """Return session directories carrying ``input.wav``."""

    root = corpus_root.resolve()
    if not root.exists():
        return []
    out: list[Path] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "input.wav").exists():
            out.append(child)
    sessions_dir = root / "sessions"
    if sessions_dir.is_dir():
        for child in sorted(sessions_dir.iterdir()):
            if child.is_dir() and (child / "input.wav").exists():
                out.append(child)
    return out


def run_live_replay_session(
    session_dir: Path,
    *,
    index: int,
    config: LiveReplayConfig,
    popen_factory: Callable[..., Any] = subprocess.Popen,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> LiveReplayResult:
    """Launch one current-source replay scenario and collect proof artifacts."""

    scenario = session_dir.name
    run_dir = config.output_dir / f"{index:03d}-{_safe_name(scenario)}"
    home_dir = run_dir / "home"
    run_dir.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    ws_port = config.base_ws_port + index
    debrief_port = config.base_debrief_port + index
    command = [config.python_executable, "-m", "vibemix"]

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home_dir),
            "VIBEMIX_DEV_SIDECAR": "1",
            "VIBEMIX_LOCAL_TTS": "0",
            "VIBEMIX_REPLAY_SESSION": str(session_dir.resolve()),
            "VIBEMIX_WS_PORT": str(ws_port),
            "VIBEMIX_DEBRIEF_PORT": str(debrief_port),
        }
    )
    if config.output_device:
        env["VIBEMIX_OUTPUT_DEVICE"] = config.output_device
    env["PYTHONPATH"] = _prepend_pythonpath(config.repo_root / "src", env.get("PYTHONPATH"))

    proc = popen_factory(
        command,
        cwd=str(config.repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    killed = False
    sleep_fn(max(0.0, float(config.duration_s)))
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
    try:
        stdout, stderr = proc.communicate(timeout=max(0.1, float(config.stop_grace_s)))
    except subprocess.TimeoutExpired:
        killed = True
        proc.kill()
        stdout, stderr = proc.communicate(timeout=2.0)

    stdout_path.write_text(stdout or "", encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")
    recording_dir = _latest_recording_dir(home_dir)
    recording_input = recording_dir / "input.wav" if recording_dir is not None else None
    events_jsonl = recording_dir / "events.jsonl" if recording_dir is not None else None
    recording_duration = (
        _wav_duration(recording_input)
        if recording_input is not None and recording_input.exists()
        else 0.0
    )
    max_music = _max_music(stdout or "")

    return LiveReplayResult(
        scenario=scenario,
        session_dir=session_dir.resolve(),
        run_dir=run_dir,
        home_dir=home_dir,
        ws_port=ws_port,
        debrief_port=debrief_port,
        returncode=proc.returncode,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        recording_dir=recording_dir,
        recording_input_wav=recording_input if recording_input and recording_input.exists() else None,
        recording_input_duration_s=recording_duration,
        events_jsonl=events_jsonl if events_jsonl and events_jsonl.exists() else None,
        max_music=max_music,
        audible_seen=bool(_AUDIBLE_RE.search(stdout or "")),
        replay_capture_seen="-> replay capture:" in (stdout or ""),
        replay_midi_seen=("midi.jsonl" not in _session_optional_files(session_dir))
        or ("-> replay MIDI tape:" in (stdout or "")),
        replay_nowplaying_seen=("nowplaying.jsonl" not in _session_optional_files(session_dir))
        or ("-> replay nowplaying:" in (stdout or "")),
        ws_seen=f"ws://127.0.0.1:{ws_port}" in (stdout or ""),
        voice_muted_seen="AI voice output muted" in (stdout or ""),
        fatal_seen=bool(_FATAL_RE.search((stdout or "") + "\n" + (stderr or ""))),
        killed_after_timeout=killed,
        command=command,
    )


def build_findings(results: list[LiveReplayResult]) -> dict[str, Any]:
    rows = [_scenario_row(result) for result in results]
    return {
        "schema": "vibemix_live_replay_findings_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "verdict": "fail" if any(row["flags"] for row in rows) else "pass",
        "scenarios": rows,
    }


def _scenario_row(result: LiveReplayResult) -> dict[str, Any]:
    events_summary = _events_summary(result.events_jsonl)
    flags: list[str] = []
    if result.returncode not in {0, None}:
        flags.append("app_nonzero_exit")
    if result.killed_after_timeout:
        flags.append("teardown_timeout")
    if result.fatal_seen:
        flags.append("fatal_log")
    if not result.replay_capture_seen:
        flags.append("replay_capture_not_selected")
    if not result.replay_midi_seen:
        flags.append("replay_midi_not_selected")
    if not result.replay_nowplaying_seen:
        flags.append("replay_nowplaying_not_selected")
    if not result.ws_seen:
        flags.append("ws_not_ready")
    if not result.voice_muted_seen:
        flags.append("voice_not_muted")
    if result.max_music <= 0.01:
        flags.append("no_music_meter")
    if not result.audible_seen:
        flags.append("no_audible_meter")
    if result.recording_input_duration_s <= 0.1:
        flags.append("no_recorded_input")
    if events_summary["events"] > 0 and events_summary["llm_invokes"] == 0:
        flags.append("mute")
    if events_summary["citation_zero_non_ack"] > 0:
        flags.append("citation_zero")
    if events_summary["slop_suppressed"] > 0:
        flags.append("slop_suppressed")
    if events_summary["max_latency_ms"] > _LATE_LLM_TO_TTS_BUDGET_MS:
        flags.append("late")

    evidence = [str(result.stdout_path), str(result.stderr_path)]
    if result.events_jsonl is not None:
        evidence.append(str(result.events_jsonl))
    if result.recording_input_wav is not None:
        evidence.append(str(result.recording_input_wav))

    return {
        "scenario": result.scenario,
        "lane": "live-replay",
        "instance_port": result.ws_port,
        "debrief_port": result.debrief_port,
        "session_dir": str(result.session_dir),
        "home_dir": str(result.home_dir),
        "recording_dir": str(result.recording_dir) if result.recording_dir else None,
        "verdict": "fail" if flags else "pass",
        "checklist": {
            "replay_capture_selected": result.replay_capture_seen,
            "replay_midi_selected": result.replay_midi_seen,
            "replay_nowplaying_selected": result.replay_nowplaying_seen,
            "ws_ready": result.ws_seen,
            "voice_muted": result.voice_muted_seen,
            "music_meter_max": round(result.max_music, 4),
            "audible_seen": result.audible_seen,
            "recorded_input_duration_s": round(result.recording_input_duration_s, 3),
            "events": events_summary["events"],
            "llm_invokes": events_summary["llm_invokes"],
            "cited_emits": events_summary["cited_emits"],
            "citation_zero_non_ack": events_summary["citation_zero_non_ack"],
            "slop_suppressed": events_summary["slop_suppressed"],
            "max_latency_ms": round(events_summary["max_latency_ms"]),
        },
        "flags": flags,
        "evidence": evidence,
    }


def _safe_name(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-") or "session"


def _prepend_pythonpath(src: Path, existing: str | None) -> str:
    return str(src) if not existing else f"{src}{os.pathsep}{existing}"


def _session_optional_files(session_dir: Path) -> set[str]:
    return {p.name for p in session_dir.iterdir() if p.is_file()}


def _max_music(stdout: str) -> float:
    values = [float(match.group(1)) for match in _MUSIC_RE.finditer(stdout)]
    return max(values) if values else 0.0


def _latest_recording_dir(home_dir: Path) -> Path | None:
    roots = list(home_dir.rglob("recordings"))
    candidates: list[Path] = []
    for root in roots:
        candidates.extend(child for child in root.iterdir() if child.is_dir())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wf:
            sr = wf.getframerate()
            if sr <= 0:
                return 0.0
            return wf.getnframes() / float(sr)
    except (wave.Error, OSError):
        return 0.0


def _events_summary(path: Path | None) -> dict[str, Any]:
    rows = _load_jsonl(path)
    event_rows = [row for row in rows if _row_kind(row) == "event"]
    llm_invokes = [row for row in rows if _row_kind(row) == "llm_invoke"]
    citation_rows = [row for row in rows if _row_kind(row) == "citation_count"]
    deltas = [
        value
        for row in rows
        if _row_kind(row) == _LLM_TO_TTS_DELTA_EVENT_TYPE
        for value in [_numeric(row.get("delta_ms"))]
        if value is not None
    ]
    return {
        "events": len(event_rows),
        "llm_invokes": len(llm_invokes),
        "cited_emits": sum(
            1
            for row in citation_rows
            if isinstance(row.get("count"), (int, float)) and int(row["count"]) >= 1
        ),
        "citation_zero_non_ack": sum(
            1
            for row in citation_rows
            if isinstance(row.get("count"), (int, float)) and int(row["count"]) == 0
        ),
        "slop_suppressed": sum(1 for row in rows if _row_kind(row) == "slop_suppressed"),
        "max_latency_ms": max(deltas) if deltas else 0.0,
    }


def _load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _row_kind(row: dict[str, Any]) -> str:
    kind = row.get("kind")
    if isinstance(kind, str) and kind:
        return kind
    typ = row.get("type")
    return typ if isinstance(typ, str) else ""


def _numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run current-source vibemix against VIBEMIX_REPLAY_SESSION scenarios."
    )
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--findings-json", type=Path, default=None)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--stop-grace", type=float, default=5.0)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--base-ws-port", type=int, default=18765)
    parser.add_argument("--base-debrief-port", type=int, default=18865)
    parser.add_argument("--output-device", type=str, default="BlackHole 2ch")
    parser.add_argument("--python-executable", type=str, default=sys.executable)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sessions = discover_sessions(args.corpus)
    config = LiveReplayConfig(
        repo_root=repo_root,
        output_dir=output_dir,
        duration_s=args.duration,
        stop_grace_s=args.stop_grace,
        base_ws_port=args.base_ws_port,
        base_debrief_port=args.base_debrief_port,
        output_device=args.output_device or None,
        python_executable=args.python_executable,
    )

    jobs = max(1, int(args.jobs))
    if jobs == 1:
        results = [
            run_live_replay_session(session, index=index, config=config)
            for index, session in enumerate(sessions)
        ]
    else:
        with ThreadPoolExecutor(max_workers=min(jobs, max(1, len(sessions)))) as pool:
            futures = [
                pool.submit(run_live_replay_session, session, index=index, config=config)
                for index, session in enumerate(sessions)
            ]
            results = [future.result() for future in futures]

    findings = build_findings(results)
    findings_path = args.findings_json or (output_dir / "live-replay-findings.json")
    findings_path.parent.mkdir(parents=True, exist_ok=True)
    findings_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(json.dumps(findings, indent=2))
    return 1 if findings["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
