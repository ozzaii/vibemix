"""DDJ controller sniff CLI. Run: python scripts/sniff_controller.py --port FLX4 --seconds 300

Standalone MIDI capture tool — emits one JSONL frame per CC/note event to stdout.
NO imports from src/vibemix/ — designed so a community contributor can run it
with just `pip install mido python-rtmidi` (CONTRIBUTING.md path).

Output schema (per T-23-02 mitigation, audited by test_sniff_controller.py):
  {"ts": float, "type": "cc"|"note_on"|"note_off",
   "channel": 0-15, "data1": 0-127, "data1_hex": "0xNN", "data2": 0-127}

On Ctrl-C / timeout, prints a final summary line:
  {"summary": true, "duration_s": float, "frames": int,
   "raw_messages": int, "unsupported_types": {...},
   "unique_cc": [...], "unique_notes": [...]}

License: Apache-2.0 (matches repo).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

__all__ = [
    "AmbiguousPortError",
    "diagnose_summary",
    "enumerate_ports",
    "format_frame",
    "main",
    "match_port",
    "summarize",
]

SUPPORTED_TYPES = frozenset({"control_change", "note_on", "note_off"})


class AmbiguousPortError(Exception):
    """Raised when --port substring matches more than one MIDI input."""

    def __init__(self, substring: str, matches: list[str]) -> None:
        self.substring = substring
        self.matches = matches
        joined = ", ".join(matches)
        super().__init__(
            f"--port '{substring}' is ambiguous; matches: [{joined}]. Be more specific."
        )


def enumerate_ports() -> list[str]:
    """Return mido.get_input_names() — separate fn for testability."""
    import mido  # type: ignore[import-not-found]

    return list(mido.get_input_names())


def match_port(substring: str, port_names: list[str]) -> str | None:
    """Case-insensitive substring match against port names.

    Returns the single matching port name, or None if no match.
    Raises AmbiguousPortError if more than one matches.
    """
    needle = substring.lower()
    matches = [name for name in port_names if needle in name.lower()]
    if not matches:
        return None
    if len(matches) > 1:
        raise AmbiguousPortError(substring, matches)
    return matches[0]


def format_frame(msg: Any, ts: float) -> dict:
    """Convert a mido.Message to a JSONL-friendly dict.

    T-23-02: schema is intentionally minimal — ts + type + channel + data1 +
    data1_hex + data2. No env, no clipboard, no audio. test_format_frame_threat_T_23_02
    pins the exact key set so any future leak is caught at test time.
    """
    if msg.type == "control_change":
        kind = "cc"
        data1 = msg.control
        data2 = msg.value
    elif msg.type == "note_on":
        kind = "note_on"
        data1 = msg.note
        data2 = msg.velocity
    elif msg.type == "note_off":
        kind = "note_off"
        data1 = msg.note
        data2 = msg.velocity
    else:
        # Unknown / unsupported — caller filters before this point, but be safe.
        kind = msg.type
        data1 = getattr(msg, "control", getattr(msg, "note", 0))
        data2 = getattr(msg, "value", getattr(msg, "velocity", 0))
    return {
        "ts": ts,
        "type": kind,
        "channel": int(msg.channel),
        "data1": int(data1),
        "data1_hex": f"0x{int(data1):02x}",
        "data2": int(data2),
    }


def summarize(
    frames: list[dict],
    duration_s: float,
    *,
    unsupported_types: dict[str, int] | None = None,
) -> dict:
    """Aggregate captured frames into a final summary line.

    unique_cc and unique_notes are returned as sorted ascending lists so
    grep / diff over multiple sniff sessions stays stable.
    """
    cc_set: set[int] = set()
    note_set: set[int] = set()
    for f in frames:
        if f["type"] == "cc":
            cc_set.add(int(f["data1"]))
        elif f["type"] in ("note_on", "note_off"):
            note_set.add(int(f["data1"]))
    unsupported = dict(sorted((unsupported_types or {}).items()))
    return {
        "summary": True,
        "duration_s": float(duration_s),
        "frames": len(frames),
        "raw_messages": len(frames) + sum(unsupported.values()),
        "unsupported_types": unsupported,
        "unique_cc": sorted(cc_set),
        "unique_notes": sorted(note_set),
    }


def diagnose_summary(summary: dict) -> dict:
    """Add a bounded setup diagnosis to a capture summary.

    The sniff tool is often used when macOS can see a controller port but the
    app receives no usable controller data. Preserve the small JSONL schema for
    frames, but make the final summary actionable enough to archive as proof.
    """
    frames = int(summary.get("frames") or 0)
    raw_messages = int(summary.get("raw_messages") or frames)
    out = dict(summary)
    if frames > 0:
        out["diagnosis"] = "midi_frames_observed"
        out["next_action"] = "Use the emitted CC/note rows to map or verify the controller."
        return out

    if raw_messages > 0:
        out["diagnosis"] = "unsupported_midi_messages_observed"
        out["next_action"] = (
            "MIDI traffic arrived, but not as CC/note messages. Capture the unsupported "
            "types from this summary, then extend the controller mapper or choose an "
            "EQ/fader/pad control that emits CC/note data."
        )
        return out

    out["diagnosis"] = "port_visible_no_supported_midi_frames"
    out["next_action"] = (
        "Move an EQ knob, fader, jog, or pad while sniffing. If this still shows "
        "zero frames, enable controller MIDI output in DJ software or close any "
        "app that has exclusive access to the controller port."
    )
    return out


def _emit(frame: dict) -> None:
    """Write one JSONL line to stdout, flushed."""
    sys.stdout.write(json.dumps(frame) + "\n")
    sys.stdout.flush()


def _record_supported_msg(
    msg: Any,
    frames: list[dict],
    unsupported_types: dict[str, int],
    start: float,
) -> bool:
    """Emit a supported MIDI message and append it to ``frames``.

    Returns True when a frame was captured. Unsupported MIDI traffic is ignored
    so the public JSONL schema stays minimal and threat-modelled.
    """
    if msg.type not in SUPPORTED_TYPES:
        unsupported_types[str(msg.type)] = unsupported_types.get(str(msg.type), 0) + 1
        return False
    ts = time.monotonic() - start
    frame = format_frame(msg, ts)
    frames.append(frame)
    _emit(frame)
    return True


def _run_poll_capture(mido: Any, port_name: str, seconds: int) -> int:
    frames: list[dict] = []
    unsupported_types: dict[str, int] = {}
    start = time.monotonic()
    deadline = start + seconds
    try:
        with mido.open_input(port_name) as port:
            print(
                f"# sniffing '{port_name}' for {seconds}s via poll — Ctrl-C to stop early",
                file=sys.stderr,
                flush=True,
            )
            while time.monotonic() < deadline:
                msg = port.poll()
                if msg is None:
                    # Avoid busy-loop; 1ms idle keeps us under <1% CPU.
                    time.sleep(0.001)
                    continue
                _record_supported_msg(msg, frames, unsupported_types, start)
    except KeyboardInterrupt:
        pass
    duration = time.monotonic() - start
    _emit(diagnose_summary(summarize(frames, duration, unsupported_types=unsupported_types)))
    return 0


def _run_callback_capture(mido: Any, port_name: str, seconds: int) -> int:
    frames: list[dict] = []
    unsupported_types: dict[str, int] = {}
    start = time.monotonic()
    deadline = start + seconds

    def _callback(msg: Any) -> None:
        _record_supported_msg(msg, frames, unsupported_types, start)

    try:
        with mido.open_input(port_name, callback=_callback):
            print(
                f"# sniffing '{port_name}' for {seconds}s via callback — Ctrl-C to stop early",
                file=sys.stderr,
                flush=True,
            )
            while time.monotonic() < deadline:
                time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    duration = time.monotonic() - start
    _emit(diagnose_summary(summarize(frames, duration, unsupported_types=unsupported_types)))
    return 0


def _run_capture(port_name: str, seconds: int, mode: str = "poll") -> int:
    """Open the port, capture for `seconds`, print JSONL + summary. Returns exit code."""
    import mido  # type: ignore[import-not-found]

    if mode == "callback":
        return _run_callback_capture(mido, port_name, seconds)
    return _run_poll_capture(mido, port_name, seconds)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sniff_controller",
        description=(
            "Standalone DJ-controller MIDI sniff CLI. Captures CC + note "
            "events and emits JSONL frames to stdout. Used by Phase 23 to "
            "resolve DDJ-FLX4 Sync note ambiguity and by community PRs to "
            "draft new controller JSON mappings."
        ),
    )
    p.add_argument(
        "--port",
        type=str,
        default=None,
        help="Substring of MIDI input port name to capture (case-insensitive). "
        "Use --list to enumerate.",
    )
    p.add_argument(
        "--seconds",
        type=int,
        default=300,
        help="Capture duration in seconds (default: 300 = 5 min, matches Pitfall 25 window).",
    )
    p.add_argument(
        "--mode",
        choices=("poll", "callback"),
        default="poll",
        help=(
            "capture mode: poll (default, mirrors vibemix listener) or callback "
            "(independent python-rtmidi callback diagnostic)"
        ),
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="Enumerate available MIDI input ports and exit.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list:
        for name in enumerate_ports():
            print(name)
        return 0

    if not args.port:
        parser.error("--port is required (or use --list to enumerate)")

    try:
        matched = match_port(args.port, enumerate_ports())
    except AmbiguousPortError as e:
        print(str(e), file=sys.stderr)
        return 2
    if matched is None:
        print(
            f"No MIDI input port matches substring '{args.port}'. "
            f"Run with --list to see available ports.",
            file=sys.stderr,
        )
        return 3

    return _run_capture(matched, args.seconds, mode=args.mode)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
