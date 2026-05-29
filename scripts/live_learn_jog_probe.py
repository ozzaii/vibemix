#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Live FLX4 jog-wheel probe for the Learn L1.07 proof.

Run with the DDJ-FLX4 plugged in:

    uv run python scripts/live_learn_jog_probe.py --port FLX4 --seconds 20

When prompted, nudge the left jog wheel. The script captures a real MIDI frame,
checks for the FLX4 left-jog CC33 shape, then feeds that captured byte through
ControllerState, MidiMirror, the Learn IPC ACK handler, and the L1.07 verifier.
It prints one JSON summary to stdout and human instructions to stderr.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_sniff_controller = importlib.import_module("scripts.sniff_controller")
AmbiguousPortError = _sniff_controller.AmbiguousPortError
enumerate_ports = _sniff_controller.enumerate_ports
format_frame = _sniff_controller.format_frame
match_port = _sniff_controller.match_port

EXPECTED_LEFT_JOG = {
    "type": "cc",
    "channel": 0,
    "data1": 0x21,
    "neutral": 64,
    "lesson_id": "L1.07",
    "control_id": "jog:A",
}


class _EmitSink:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def emit(self, msg: dict) -> None:
        self.messages.append(msg)


def is_left_jog_frame(frame: dict[str, Any]) -> bool:
    """Return True for a live FLX4 left-jog movement frame."""
    return (
        frame.get("type") == EXPECTED_LEFT_JOG["type"]
        and int(frame.get("channel", -1)) == EXPECTED_LEFT_JOG["channel"]
        and int(frame.get("data1", -1)) == EXPECTED_LEFT_JOG["data1"]
        and int(frame.get("data2", EXPECTED_LEFT_JOG["neutral"]))
        != EXPECTED_LEFT_JOG["neutral"]
    )


def build_summary(
    *,
    frames: list[dict[str, Any]],
    duration_s: float,
    port_name: str,
    learn_verifier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    matches = [frame for frame in frames if is_left_jog_frame(frame)]
    passed = bool(matches) and (
        learn_verifier is None or learn_verifier.get("passed") is True
    )
    return {
        "passed": passed,
        "port_name": port_name,
        "duration_s": float(duration_s),
        "frames": len(frames),
        "matched_left_jog_frames": len(matches),
        "first_left_jog_frame": matches[0] if matches else None,
        "expected": dict(EXPECTED_LEFT_JOG),
        "learn_verifier": learn_verifier,
    }


async def _dispatch(router: Any, msg: dict[str, Any]) -> bool:
    return bool(await router.dispatch(msg))


def verify_frame_reaches_lesson(frame: dict[str, Any]) -> dict[str, Any]:
    """Feed a captured raw FLX4 byte into the Learn L1.07 verifier."""
    try:
        from vibemix.learn.ipc_handlers import register_learn_handlers
        from vibemix.learn.midi_mirror import MidiMirror
        from vibemix.learn.progress import LearnProgress
        from vibemix.learn.runtime import LessonRuntime
        from vibemix.learn.state import LearnState
        from vibemix.midi import ControllerState, load_profile
        from vibemix.runtime.ws_bus import IpcRouterBus
    except Exception as exc:  # pragma: no cover - import environment guard
        return {"passed": False, "error": f"import failed: {exc!r}"}

    profile = load_profile("pioneer_ddj_flx4")
    if profile is None:
        return {"passed": False, "error": "pioneer_ddj_flx4 profile missing"}

    controller_state = ControllerState(profile=profile)
    controller_state.mark_connected("DDJ-FLX4")
    midi_mirror = MidiMirror(controller_state=controller_state)
    midi_mirror.bind_profile(profile)
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=_EmitSink(),
        progress_store=progress,
    )
    router = IpcRouterBus()
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    start_handled = asyncio.run(
        _dispatch(
            router,
            {
                "type": "ipc.learn.start_lesson",
                "payload": {"lesson_id": "L1.07", "level": "fresh"},
            },
        )
    )
    controller_state.handle_msg(
        SimpleNamespace(
            type="control_change",
            channel=int(frame["channel"]),
            control=int(frame["data1"]),
            value=int(frame["data2"]),
        )
    )
    pulse = midi_mirror.snapshot()
    positions = pulse["payload"]["positions"] if pulse is not None else {}
    ack_handled = asyncio.run(
        _dispatch(
            router,
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "jog:A",
                    "source": "midi",
                    "value": int(positions.get("jog:A", 0)),
                    "prev_value": 0,
                    "direction": "down",
                },
            },
        )
    )
    state_id = runtime.current_state.id
    return {
        "passed": start_handled
        and ack_handled
        and positions.get("jog:A") == 127
        and state_id in {"advancing", "completed"},
        "lesson_id": "L1.07",
        "start_handled": start_handled,
        "ack_handled": ack_handled,
        "state": state_id,
        "positions": positions,
    }


def capture_left_jog(
    *,
    port_name: str,
    seconds: int,
    stop_on_match: bool = True,
) -> tuple[list[dict[str, Any]], float]:
    """Capture supported MIDI frames from a port until timeout or jog match."""
    import mido  # type: ignore[import-not-found]

    frames: list[dict[str, Any]] = []
    start = time.monotonic()
    deadline = start + max(1, int(seconds))

    def _callback(msg: Any) -> None:
        if msg.type not in {"control_change", "note_on", "note_off"}:
            return
        frame = format_frame(msg, time.monotonic() - start)
        frames.append(frame)
        print(f"captured {json.dumps(frame)}", file=sys.stderr, flush=True)

    with mido.open_input(port_name, callback=_callback):
        print(
            f"listening on {port_name!r}. Nudge the LEFT jog wheel now.",
            file=sys.stderr,
            flush=True,
        )
        while time.monotonic() < deadline:
            if stop_on_match and any(is_left_jog_frame(frame) for frame in frames):
                break
            time.sleep(0.01)

    return frames, time.monotonic() - start


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="live_learn_jog_probe",
        description="Capture a live FLX4 left-jog byte and prove it reaches Learn L1.07.",
    )
    parser.add_argument(
        "--port",
        default="FLX4",
        help="Substring of MIDI input port name to capture (default: FLX4).",
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=20,
        help="Capture window in seconds (default: 20).",
    )
    parser.add_argument(
        "--no-stop-on-match",
        action="store_true",
        help="Keep listening for the full capture window after the first match.",
    )
    parser.add_argument(
        "--skip-learn-verify",
        action="store_true",
        help="Only capture MIDI; do not feed the matched byte through Learn.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        matched = match_port(args.port, enumerate_ports())
    except AmbiguousPortError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if matched is None:
        print(
            f"No MIDI input port matches {args.port!r}. Run scripts/sniff_controller.py --list.",
            file=sys.stderr,
        )
        return 3

    frames, duration_s = capture_left_jog(
        port_name=matched,
        seconds=args.seconds,
        stop_on_match=not args.no_stop_on_match,
    )
    matches = [frame for frame in frames if is_left_jog_frame(frame)]
    learn_verifier = None
    if matches and not args.skip_learn_verify:
        learn_verifier = verify_frame_reaches_lesson(matches[0])
    summary = build_summary(
        frames=frames,
        duration_s=duration_s,
        port_name=matched,
        learn_verifier=learn_verifier,
    )
    print(json.dumps(summary, sort_keys=True))
    if not matches:
        return 4
    if learn_verifier is not None and learn_verifier.get("passed") is not True:
        return 5
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
