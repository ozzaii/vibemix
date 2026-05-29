#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Live sidecar socket probe for Learn L1.07.

Start vibemix first, then run:

    uv run python scripts/live_learn_socket_jog_probe.py --seconds 20

When prompted, nudge the left jog wheel. This probe uses the established
ws://127.0.0.1:8765 bus instead of opening MIDI itself:

1. send ``ipc.learn.start_lesson`` for L1.07,
2. wait for a live ``ipc.learn.midi_position`` frame with ``jog:A == 127``,
3. send the same ``ipc.learn.ack`` the Learn UI would send,
4. wait for ``ipc.learn.advance`` from the sidecar runtime.

It prints one JSON proof summary to stdout.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

DEFAULT_WS_URL = "ws://127.0.0.1:8765"
LESSON_ID = "L1.07"
CONTROL_ID = "jog:A"
MIDI_POSITION_SAMPLE_LIMIT = 12


def envelope(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": message_type,
        "ts": datetime.now(UTC).isoformat(),
        "payload": payload,
    }


def midi_positions(msg: dict[str, Any]) -> dict[str, int] | None:
    if msg.get("type") != "ipc.learn.midi_position":
        return None
    payload = msg.get("payload")
    if not isinstance(payload, dict):
        return None
    positions = payload.get("positions")
    if not isinstance(positions, dict):
        return None
    out: dict[str, int] = {}
    for key, value in positions.items():
        if not isinstance(key, str):
            continue
        try:
            out[key] = int(value)
        except (TypeError, ValueError):
            continue
    return out


def is_left_jog_position(msg: dict[str, Any]) -> bool:
    positions = midi_positions(msg)
    return positions is not None and int(positions.get(CONTROL_ID, 0)) >= 127


def _safe_json_loads(raw: str | bytes) -> dict[str, Any] | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _say_prompt(text: str, *, enabled: bool) -> bool:
    """Speak an operator prompt on macOS. Best-effort and testable."""
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


async def run_socket_probe(
    *,
    url: str = DEFAULT_WS_URL,
    seconds: float = 20.0,
    send_start: bool = True,
    auto_ack: bool = True,
    say_prompts: bool = False,
) -> dict[str, Any]:
    """Run the socket probe and return a JSON-serializable summary."""
    import websockets

    observed_types: list[str] = []
    lesson_loaded: dict[str, Any] | None = None
    jog_frame: dict[str, Any] | None = None
    advance: dict[str, Any] | None = None
    ack_sent = False
    start_messages_sent = 0
    midi_position_count = 0
    midi_position_samples: list[dict[str, Any]] = []
    jog_values: list[int] = []
    ready_prompt_sent = False
    operator_prompt_spoken = False
    fallback_ready_prompt_at: float | None = None
    deadline = asyncio.get_running_loop().time() + max(1.0, float(seconds))

    async with websockets.connect(url) as ws:
        async def send_start_lesson() -> None:
            nonlocal start_messages_sent
            await ws.send(
                json.dumps(
                    envelope(
                        "ipc.learn.start_lesson",
                        {"lesson_id": LESSON_ID, "level": "fresh"},
                    ),
                    separators=(",", ":"),
                )
            )
            start_messages_sent += 1

        if send_start:
            await send_start_lesson()
        next_start_retry_at = asyncio.get_running_loop().time() + 1.0
        print(
            f"connected to {url}. Waiting for L1.07 + live MIDI frames.",
            file=sys.stderr,
            flush=True,
        )
        while asyncio.get_running_loop().time() < deadline:
            now = asyncio.get_running_loop().time()
            if (
                send_start
                and lesson_loaded is None
                and now >= next_start_retry_at
            ):
                await send_start_lesson()
                next_start_retry_at = now + 1.0
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                raw = await asyncio.wait_for(
                    ws.recv(),
                    timeout=max(0.05, min(0.25, remaining)),
                )
            except TimeoutError:
                continue
            msg = _safe_json_loads(raw)
            if msg is None:
                continue
            msg_type = msg.get("type")
            if isinstance(msg_type, str):
                observed_types.append(msg_type)
            if msg_type == "ipc.learn.lesson_loaded":
                lesson_loaded = msg
                if fallback_ready_prompt_at is None:
                    fallback_ready_prompt_at = asyncio.get_running_loop().time() + 1.0
            positions = midi_positions(msg)
            if positions is not None:
                midi_position_count += 1
                if CONTROL_ID in positions:
                    jog_values.append(int(positions[CONTROL_ID]))
                if len(midi_position_samples) < MIDI_POSITION_SAMPLE_LIMIT:
                    payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                    midi_position_samples.append(
                        {
                            "controller_id": payload.get("controller_id"),
                            "positions": dict(sorted(positions.items())),
                        }
                    )
                if lesson_loaded is not None and not ready_prompt_sent:
                    print(
                        "ready: L1.07 is loaded and midi_position is live. "
                        "Nudge the LEFT jog wheel now.",
                        file=sys.stderr,
                        flush=True,
                    )
                    operator_prompt_spoken = _say_prompt(
                        "Move the left jog wheel now.",
                        enabled=say_prompts,
                    )
                    ready_prompt_sent = True
            if (
                lesson_loaded is not None
                and not ready_prompt_sent
                and fallback_ready_prompt_at is not None
                and asyncio.get_running_loop().time() >= fallback_ready_prompt_at
            ):
                print(
                    "ready: L1.07 is loaded. Keep rotating the LEFT jog wheel "
                    "until the proof completes.",
                    file=sys.stderr,
                    flush=True,
                )
                operator_prompt_spoken = _say_prompt(
                    "Keep rotating the left jog wheel.",
                    enabled=say_prompts,
                )
                ready_prompt_sent = True
            if (
                jog_frame is None
                and positions is not None
                and int(positions.get(CONTROL_ID, 0)) >= 127
            ):
                jog_frame = msg
                if auto_ack:
                    await ws.send(
                        json.dumps(
                            envelope(
                                "ipc.learn.ack",
                                {
                                    "control_id": CONTROL_ID,
                                    "source": "midi",
                                    "value": int(positions.get(CONTROL_ID, 127)),
                                    "prev_value": 0,
                                    "direction": "down",
                                },
                            ),
                            separators=(",", ":"),
                        )
                    )
                    ack_sent = True
            if msg_type == "ipc.learn.advance":
                advance = msg
                break

    passed = jog_frame is not None and (not auto_ack or advance is not None)
    diagnosis = physical_probe_diagnosis(
        lesson_loaded=lesson_loaded is not None,
        jog_position_seen=jog_frame is not None,
        ack_sent=ack_sent,
        advance_seen=advance is not None,
        start_messages_sent=start_messages_sent,
        midi_position_count=midi_position_count,
        jog_values=jog_values,
    )
    return {
        "passed": passed,
        "url": url,
        "lesson_id": LESSON_ID,
        "control_id": CONTROL_ID,
        "start_messages_sent": start_messages_sent,
        "lesson_loaded": lesson_loaded is not None,
        "lesson_loaded_controller_id": (
            lesson_loaded.get("payload", {}).get("controller_id")
            if lesson_loaded is not None
            else None
        ),
        "jog_position_seen": jog_frame is not None,
        "ack_sent": ack_sent,
        "advance_seen": advance is not None,
        "midi_position_count": midi_position_count,
        "midi_position_samples": midi_position_samples,
        "jog_values": jog_values,
        "operator_prompt_spoken": operator_prompt_spoken,
        "observed_types": observed_types,
        "diagnosis": diagnosis,
        "operator_action": diagnosis["operator_action"],
    }


def physical_probe_diagnosis(
    *,
    lesson_loaded: bool,
    jog_position_seen: bool,
    ack_sent: bool,
    advance_seen: bool,
    start_messages_sent: int,
    midi_position_count: int = 0,
    jog_values: list[int] | None = None,
) -> dict[str, Any]:
    if not lesson_loaded:
        return {
            "code": "learn_lesson_not_loaded",
            "message": (
                "The socket was open, but L1.07 did not emit lesson_loaded after "
                f"{start_messages_sent} start_lesson request(s)."
            ),
            "operator_action": {
                "prompt": "Restart the proof from a clean Learn sidecar socket.",
                "steps": [
                    "Make sure no other vibemix sidecar owns ws://127.0.0.1:8765.",
                    "Rerun the physical proof with --start-app.",
                    "Nudge the left jog wheel only after the probe prints the connected prompt.",
                ],
            },
        }
    if not jog_position_seen:
        detail = ""
        if midi_position_count > 0:
            sampled = sorted(set(jog_values or []))
            detail = (
                f" The socket emitted {midi_position_count} midi_position frame(s); "
                f"sampled {CONTROL_ID} values were {sampled}."
            )
        return {
            "code": "left_jog_not_observed",
            "message": (
                "L1.07 loaded, but no ipc.learn.midi_position frame reached jog:A."
                + detail
            ),
            "operator_action": {
                "prompt": "Nudge the left jog wheel after the probe says midi_position is live.",
                "steps": [
                    "When the proof says midi_position is live, rotate the left jog wheel.",
                    "If it still fails, run scripts/sniff_controller.py and move the same jog.",
                    "Keep the DDJ-FLX4 connected directly over USB.",
                ],
            },
        }
    if not ack_sent:
        return {
            "code": "jog_seen_ack_not_sent",
            "message": "The left jog frame was seen, but the Learn ACK was not sent.",
            "operator_action": {
                "prompt": "Rerun the proof; this is a probe-side ACK failure.",
                "steps": ["Rerun the physical proof and preserve the artifact."],
            },
        }
    if not advance_seen:
        return {
            "code": "jog_ack_no_advance",
            "message": "The left jog ACK was sent, but Learn did not emit advance.",
            "operator_action": {
                "prompt": "Rerun the proof and inspect Learn runtime guard logs.",
                "steps": [
                    "Rerun the physical proof.",
                    "If advance is still missing, inspect the L1.07 expected-action guard.",
                ],
            },
        }
    return {
        "code": "physical_l1_07_proven",
        "message": "L1.07 loaded, left jog was observed, ACK was sent, and advance was seen.",
        "operator_action": {
            "prompt": "Physical L1.07 proof is complete.",
            "steps": [],
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="live_learn_socket_jog_probe",
        description="Prove live Learn L1.07 jog movement over ws://127.0.0.1:8765.",
    )
    parser.add_argument("--url", default=DEFAULT_WS_URL, help=f"WebSocket URL (default: {DEFAULT_WS_URL}).")
    parser.add_argument("--seconds", type=float, default=20.0, help="Capture window in seconds.")
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Do not send start_lesson; assume L1.07 is already active.",
    )
    parser.add_argument(
        "--no-ack",
        action="store_true",
        help="Do not send the Learn ACK after the jog pulse is observed.",
    )
    parser.add_argument(
        "--say-prompts",
        action="store_true",
        help="On macOS, speak the operator jog prompt using say(1).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = asyncio.run(
            run_socket_probe(
                url=args.url,
                seconds=args.seconds,
                send_start=not args.no_start,
                auto_ack=not args.no_ack,
                say_prompts=args.say_prompts,
            )
        )
    except OSError as exc:
        summary = {
            "passed": False,
            "url": args.url,
            "error": f"could not connect to live sidecar socket: {exc}",
        }
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        summary = {"passed": False, "url": args.url, "error": repr(exc)}
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("passed") is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
