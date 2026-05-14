"""Unit tests for scripts/sniff_controller.py — pure-Python pieces only.

No live MIDI required. mido is mocked via sys.modules patch so this runs on
macOS CI without `python-rtmidi` install issues (per 23-01 plan spec).
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module loader — re-imports sniff_controller fresh with a stubbed mido so
# each test gets a clean slate.
# ---------------------------------------------------------------------------

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "sniff_controller.py"
)


def _fresh_module(fake_mido: types.ModuleType | None = None):
    """Import scripts/sniff_controller as a module with optional mido stub."""
    if fake_mido is None:
        fake_mido = types.SimpleNamespace(
            get_input_names=lambda: [],
            open_input=lambda name: MagicMock(),
        )
    # Stub `mido` in sys.modules so the script's `import mido` resolves to ours.
    sys.modules["mido"] = fake_mido  # type: ignore[assignment]
    spec = importlib.util.spec_from_file_location(
        "sniff_controller_under_test", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# ---------------------------------------------------------------------------
# match_port helper
# ---------------------------------------------------------------------------


def test_match_port_exact_substring_returns_port():
    mod = _fresh_module()
    result = mod.match_port("FLX4", ["DDJ-FLX4 Port 1", "Other Port"])
    assert result == "DDJ-FLX4 Port 1"


def test_match_port_case_insensitive():
    mod = _fresh_module()
    result = mod.match_port("flx4", ["DDJ-FLX4 Port 1", "Other Port"])
    assert result == "DDJ-FLX4 Port 1"


def test_match_port_no_match_returns_none():
    mod = _fresh_module()
    result = mod.match_port("nope", ["DDJ-FLX4 Port 1", "Other Port"])
    assert result is None


def test_match_port_ambiguous_raises():
    mod = _fresh_module()
    with pytest.raises(mod.AmbiguousPortError) as excinfo:
        mod.match_port("port", ["A Port", "B Port"])
    msg = str(excinfo.value)
    assert "A Port" in msg
    assert "B Port" in msg


def test_match_port_empty_list_returns_none():
    mod = _fresh_module()
    assert mod.match_port("FLX4", []) is None


# ---------------------------------------------------------------------------
# format_frame helper
# ---------------------------------------------------------------------------


def _mock_cc(channel: int, control: int, value: int) -> MagicMock:
    m = MagicMock()
    m.type = "control_change"
    m.channel = channel
    m.control = control
    m.value = value
    return m


def _mock_note_on(channel: int, note: int, velocity: int) -> MagicMock:
    m = MagicMock()
    m.type = "note_on"
    m.channel = channel
    m.note = note
    m.velocity = velocity
    return m


def _mock_note_off(channel: int, note: int, velocity: int) -> MagicMock:
    m = MagicMock()
    m.type = "note_off"
    m.channel = channel
    m.note = note
    m.velocity = velocity
    return m


def test_format_frame_cc_has_hex_field():
    mod = _fresh_module()
    frame = mod.format_frame(_mock_cc(channel=0, control=0x60, value=127), ts=1.5)
    assert frame["type"] == "cc"
    assert frame["channel"] == 0
    assert frame["data1"] == 0x60
    assert frame["data1_hex"] == "0x60"
    assert frame["data2"] == 127
    assert frame["ts"] == 1.5


def test_format_frame_note_on():
    mod = _fresh_module()
    frame = mod.format_frame(_mock_note_on(channel=1, note=0x58, velocity=100), ts=2.0)
    assert frame["type"] == "note_on"
    assert frame["channel"] == 1
    assert frame["data1"] == 0x58
    assert frame["data1_hex"] == "0x58"
    assert frame["data2"] == 100


def test_format_frame_note_off():
    mod = _fresh_module()
    frame = mod.format_frame(_mock_note_off(channel=0, note=0x60, velocity=0), ts=3.0)
    assert frame["type"] == "note_off"
    assert frame["channel"] == 0
    assert frame["data1"] == 0x60
    assert frame["data2"] == 0


def test_format_frame_threat_T_23_02_only_minimal_fields():
    """T-23-02 mitigation: format_frame MUST NOT emit env, clipboard, audio,
    or any field beyond the documented audit trail. This pins the schema so
    no future regression can leak metadata into the captured raw JSONL.
    """
    mod = _fresh_module()
    frame = mod.format_frame(_mock_cc(0, 0x60, 127), ts=1.0)
    allowed = {"ts", "type", "channel", "data1", "data1_hex", "data2"}
    assert set(frame.keys()) == allowed


def test_format_frame_json_roundtrip():
    mod = _fresh_module()
    frame = mod.format_frame(_mock_cc(0, 7, 64), ts=0.1)
    s = json.dumps(frame)
    parsed = json.loads(s)
    assert parsed == frame


# ---------------------------------------------------------------------------
# summarize helper
# ---------------------------------------------------------------------------


def test_summarize_aggregates_unique_cc_and_notes_sorted():
    mod = _fresh_module()
    frames = [
        {"type": "cc", "channel": 0, "data1": 7, "data1_hex": "0x07", "data2": 64, "ts": 0.0},
        {"type": "cc", "channel": 0, "data1": 11, "data1_hex": "0x0b", "data2": 64, "ts": 0.1},
        {"type": "cc", "channel": 0, "data1": 7, "data1_hex": "0x07", "data2": 65, "ts": 0.2},
        {"type": "note_on", "channel": 0, "data1": 0x60, "data1_hex": "0x60", "data2": 127, "ts": 0.3},
        {"type": "note_on", "channel": 0, "data1": 0x58, "data1_hex": "0x58", "data2": 127, "ts": 0.4},
        {"type": "note_off", "channel": 0, "data1": 0x60, "data1_hex": "0x60", "data2": 0, "ts": 0.5},
    ]
    summary = mod.summarize(frames, duration_s=1.0)
    assert summary["summary"] is True
    assert summary["frames"] == 6
    assert summary["duration_s"] == 1.0
    assert summary["unique_cc"] == [7, 11]  # sorted ascending
    assert summary["unique_notes"] == [0x58, 0x60]  # sorted ascending


def test_summarize_empty_frames():
    mod = _fresh_module()
    summary = mod.summarize([], duration_s=0.0)
    assert summary["summary"] is True
    assert summary["frames"] == 0
    assert summary["unique_cc"] == []
    assert summary["unique_notes"] == []


# ---------------------------------------------------------------------------
# CLI surface — --list, --help (sanity)
# ---------------------------------------------------------------------------


def test_enumerate_ports_calls_mido():
    fake = types.SimpleNamespace(
        get_input_names=lambda: ["DDJ-FLX4 Port 1", "IAC Driver Bus 1"],
        open_input=lambda name: MagicMock(),
    )
    mod = _fresh_module(fake)
    names = mod.enumerate_ports()
    assert names == ["DDJ-FLX4 Port 1", "IAC Driver Bus 1"]


def test_main_list_prints_ports_and_exits_zero(capsys):
    fake = types.SimpleNamespace(
        get_input_names=lambda: ["DDJ-FLX4 Port 1", "IAC"],
        open_input=lambda name: MagicMock(),
    )
    mod = _fresh_module(fake)
    rc = mod.main(["--list"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "DDJ-FLX4 Port 1" in captured.out
    assert "IAC" in captured.out


def test_main_no_port_exits_nonzero_when_no_args(capsys):
    fake = types.SimpleNamespace(
        get_input_names=lambda: [],
        open_input=lambda name: MagicMock(),
    )
    mod = _fresh_module(fake)
    # argparse will SystemExit on missing required arg
    with pytest.raises(SystemExit):
        mod.main([])


def test_main_port_not_found_exits_nonzero(capsys):
    fake = types.SimpleNamespace(
        get_input_names=lambda: ["IAC Driver Bus 1"],
        open_input=lambda name: MagicMock(),
    )
    mod = _fresh_module(fake)
    rc = mod.main(["--port", "FLX4", "--seconds", "1"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "FLX4" in captured.err or "FLX4" in captured.out


def test_main_ambiguous_port_exits_nonzero(capsys):
    fake = types.SimpleNamespace(
        get_input_names=lambda: ["DDJ-FLX4 Port 1", "DDJ-FLX4 Port 2"],
        open_input=lambda name: MagicMock(),
    )
    mod = _fresh_module(fake)
    rc = mod.main(["--port", "FLX4", "--seconds", "1"])
    captured = capsys.readouterr()
    assert rc != 0
    # Both ambiguous candidates should be surfaced
    assert "Port 1" in (captured.out + captured.err)
    assert "Port 2" in (captured.out + captured.err)
