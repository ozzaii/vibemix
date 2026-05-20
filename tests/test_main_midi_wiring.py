# SPDX-License-Identifier: Apache-2.0
"""Phase 53 BRINGUP-03 — guard test for the live hot-plug watcher wiring.

At HEAD before Phase 53, the hot-plug watcher (``port_watcher_task`` /
``MidiMacOS.start_port_watcher``) existed and was unit-tested, but ``__main__``
NEVER started it — so mid-session unplug/replug was undetected in a real run
(the BRINGUP-03 gap). Phase 53 Plan 02 wires it in. This is a SOURCE-LEVEL
guard (mirrors Phase 52's input-path source assertion) so the live wiring
can't silently regress: it reads ``src/vibemix/__main__.py`` as text and
asserts the watcher is spawned on a dedicated asyncio stop event and cleaned
up in the finally block. It deliberately does NOT import the heavy ``main()``
(which needs real audio devices).
"""

from __future__ import annotations

import pathlib
import re

_MAIN = pathlib.Path(__file__).resolve().parents[1] / "src" / "vibemix" / "__main__.py"


def _source() -> str:
    assert _MAIN.is_file(), f"__main__.py not found at {_MAIN}"
    return _MAIN.read_text(encoding="utf-8")


def test_main_spawns_port_watcher():
    """The live session spawns the hot-plug watcher."""
    src = _source()
    assert "start_port_watcher(" in src, "__main__ must spawn start_port_watcher"


def test_main_uses_dedicated_asyncio_stop_event_for_watcher():
    """The watcher gets its OWN asyncio.Event stop signal (distinct from the
    threading.Event the static listener uses)."""
    src = _source()
    assert "midi_watcher_stop" in src, "__main__ must define a midi_watcher_stop event"
    # The stop event is an asyncio.Event() (not the threading.Event for the listener).
    assert re.search(r"midi_watcher_stop\s*=\s*asyncio\.Event\(\)", src), (
        "midi_watcher_stop must be an asyncio.Event()"
    )


def test_main_cleans_up_watcher_in_finally():
    """The watcher stop event is set AND the watcher task is in cleanup_tasks,
    so the watcher exits cooperatively + its task is cancelled on shutdown."""
    src = _source()
    assert "midi_watcher_stop.set()" in src, "finally must set midi_watcher_stop"
    # The watcher task name must appear in the cleanup_tasks list.
    assert "midi_watcher_task" in src, "__main__ must capture the watcher task"
    cleanup_match = re.search(r"cleanup_tasks[^=]*=\s*\[(.*?)\]", src, re.DOTALL)
    assert cleanup_match, "cleanup_tasks list not found"
    assert "midi_watcher_task" in cleanup_match.group(1), (
        "midi_watcher_task must be in the cleanup_tasks list"
    )


def test_main_sets_watcher_stop_alongside_midi_stop():
    """midi_watcher_stop.set() lives in the same finally region as midi_stop.set()
    (both shutdown signals fire together)."""
    src = _source()
    midi_stop_idx = src.find("midi_stop.set()")
    watcher_stop_idx = src.find("midi_watcher_stop.set()")
    assert midi_stop_idx != -1 and watcher_stop_idx != -1
    # They should be close together (same cleanup block) — within ~500 chars.
    assert abs(watcher_stop_idx - midi_stop_idx) < 500, (
        "midi_watcher_stop.set() should be in the same cleanup block as midi_stop.set()"
    )


def test_midi_macos_has_start_port_watcher():
    """The watcher entry point exists on MidiMacOS (import-level pin)."""
    from vibemix.platform import MidiMacOS

    assert hasattr(MidiMacOS, "start_port_watcher")


def test_main_module_parses():
    """__main__.py has no syntax error after the wiring edit."""
    import ast

    ast.parse(_source())
