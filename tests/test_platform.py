# SPDX-License-Identifier: Apache-2.0
"""Protocol introspection + OS-leak AST guard for src/vibemix/platform/.

The load-bearing test is `test_no_os_leaks` — it AST-parses every .py file under
src/vibemix/platform/ and fails if any forbidden OS-specific import is present.
This enforces the Phase 1 architectural rule: Protocols are typing-only;
concrete impls (sounddevice / mss / Quartz / mido / subprocess / win32) live in
sibling _audio_macos.py / _audio_windows.py / etc. introduced Phase 2+.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import runtime_checkable

PLATFORM_DIR = Path(__file__).resolve().parent.parent / "src" / "vibemix" / "platform"

FORBIDDEN_TOP_LEVEL = {
    "sounddevice",
    "mss",
    "PIL",
    "Pillow",
    "mido",
    "rtmidi",
    "python_rtmidi",
    "Quartz",
    "objc",
    "Foundation",
    "AppKit",
    "subprocess",
    "winreg",
    "numpy",
    "scipy",
}


def _is_forbidden(top_level: str) -> bool:
    if top_level in FORBIDDEN_TOP_LEVEL:
        return True
    if top_level.startswith("win32"):
        return True
    return False


def test_protocols_exported():
    from vibemix.platform import (  # noqa: F401
        AudioBackend,
        MidiBackend,
        ScreenBackend,
        TrackInfoBackend,
    )


def test_value_dataclasses_exported():
    from vibemix.platform import (  # noqa: F401
        AudioCallback,
        AudioStream,
        CapturedFrame,
        Kind,
        MidiMessage,
        MidiPort,
        NowPlayingSnapshot,
        WindowBounds,
    )


def test_runtime_checkable():
    from vibemix.platform import (
        AudioBackend,
        MidiBackend,
        ScreenBackend,
        TrackInfoBackend,
    )

    for proto in (AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend):
        assert runtime_checkable(proto) is proto
        assert isinstance(object(), proto) is False


def test_protocol_surface():
    from vibemix.platform import (
        AudioBackend,
        MidiBackend,
        ScreenBackend,
        TrackInfoBackend,
    )

    assert {
        "find_device",
        "open_capture",
        "open_passthrough_output",
        "open_voice_output",
    } <= set(dir(AudioBackend))
    assert {"is_available", "find_window_bounds", "capture"} <= set(dir(ScreenBackend))
    assert {"list_input_ports", "open_input"} <= set(dir(MidiBackend))
    assert {"is_available", "poll"} <= set(dir(TrackInfoBackend))


def test_no_os_leaks():
    """AST-scan every src/vibemix/platform/*.py for forbidden OS imports."""
    files = sorted(PLATFORM_DIR.glob("*.py"))
    assert files, f"expected .py files under {PLATFORM_DIR}"
    violations: list[str] = []
    for file in files:
        tree = ast.parse(file.read_text(), filename=str(file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if _is_forbidden(top):
                        violations.append(
                            f"{file.name}:{node.lineno}: forbidden import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top = node.module.split(".")[0]
                if _is_forbidden(top):
                    violations.append(
                        f"{file.name}:{node.lineno}: forbidden from-import {node.module}"
                    )
    assert not violations, "OS-leak guard tripped:\n  " + "\n  ".join(violations)
