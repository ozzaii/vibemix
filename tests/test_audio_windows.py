# SPDX-License-Identifier: Apache-2.0
"""Mocked PyAudioWPatch unit tests for vibemix.platform._audio_windows.AudioWindows.

Strategy:
- We never import the real ``pyaudiowpatch`` (it isn't installed on macOS — the
  pyproject marker gates it on ``sys_platform == 'win32'``). All tests inject a
  ``MagicMock`` into ``sys.modules["pyaudiowpatch"]`` BEFORE the lazy import
  inside an ``AudioWindows`` method body fires.
- The ``_audio_windows`` module itself MUST import cleanly on darwin without
  pulling ``pyaudiowpatch`` (Critical Constraint 3 — top-level lazy import
  discipline).
- Tests assert call shapes against the ``open(...)`` mock so we can pin the
  exact PyAudio param contract (format, channels, rate, input/output booleans,
  device index, frames_per_buffer, stream_callback).

Covers Wave 2 Task 1 behaviors: module-import cleanliness, AudioBackend Protocol
satisfaction, find_device (Windows-style names with parens + Unicode), the
WASAPI loopback sample-rate guard (pass + raise), open_capture wiring (uses the
loopback index from ``get_default_wasapi_loopback_device()``), and the
``_PyAudioStreamHandle`` adapter satisfying the ``AudioStream`` Protocol.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.audio import (
    AudioBuffer,
    BufferRegistry,
    Levels,
    MicBuffer,
    PassthroughBuffer,
    PlaybackQueue,
    VoiceRecorder,
)
from vibemix.audio.errors import SampleRateMismatchError
from vibemix.platform.audio import AudioBackend, AudioStream

# NOTE: We import AudioWindows from its private sibling module directly. The
# package selector at vibemix.platform.__init__ wires ``AudioImpl = AudioWindows``
# only on win32; on darwin we go around the selector and target the file
# directly so the test runs on Kaan's macOS dev box.


# ---------- Fixtures ----------


@pytest.fixture
def make_registry_recorder():
    """Factory that returns a (registry, recorder) pair using a temp recorder root."""

    def _make() -> tuple[BufferRegistry, VoiceRecorder]:
        lv = Levels()
        reg = BufferRegistry(
            audio=AudioBuffer(seconds=1.0),
            clean_audio=AudioBuffer(seconds=1.0),
            mic=MicBuffer(gain=1.0, levels=lv),
            passthrough=PassthroughBuffer(),
            playback=PlaybackQueue(lv),
            levels=lv,
        )
        rec = VoiceRecorder(root=Path(tempfile.mkdtemp()))
        return reg, rec

    return _make


def _make_fake_pa(
    devices: list[dict] | None = None,
    loopback_info: dict | None = None,
):
    """Build a MagicMock structured like the real ``pyaudiowpatch`` module.

    ``pyaudiowpatch.PyAudio()`` returns an instance with:
      - ``get_device_count() -> int``
      - ``get_device_info_by_index(idx) -> dict``
      - ``get_default_wasapi_loopback_device() -> dict``
      - ``open(...) -> Stream``
      - ``terminate()``
    Plus module constants ``paInt16 = 8`` and ``paFloat32 = 1`` (matches the
    real PortAudio constant values).

    The returned ``open()`` Stream mock has the four methods our adapter calls:
    ``start_stream``, ``stop_stream``, ``close``, ``get_input_latency``,
    ``get_output_latency``. ``get_input_latency`` / ``get_output_latency``
    default to ``0.005`` (5ms) so ``latency_ms`` returns ``5.0``.
    """
    devices = devices or []
    loopback_info = loopback_info or {
        "index": 7,
        "name": "Speakers (Realtek(R) Audio) [Loopback]",
        "defaultSampleRate": 48000.0,
        "maxInputChannels": 2,
    }

    fake_module = MagicMock()
    fake_module.paInt16 = 8
    fake_module.paFloat32 = 1

    fake_stream = MagicMock()
    fake_stream.start_stream = MagicMock()
    fake_stream.stop_stream = MagicMock()
    fake_stream.close = MagicMock()
    fake_stream.get_input_latency = MagicMock(return_value=0.005)
    fake_stream.get_output_latency = MagicMock(return_value=0.005)

    fake_pa_instance = MagicMock()
    fake_pa_instance.get_device_count = MagicMock(return_value=len(devices))
    fake_pa_instance.get_device_info_by_index = MagicMock(side_effect=lambda i: devices[i])
    fake_pa_instance.get_default_wasapi_loopback_device = MagicMock(return_value=loopback_info)
    fake_pa_instance.open = MagicMock(return_value=fake_stream)
    fake_pa_instance.terminate = MagicMock()

    # ``pa.PyAudio()`` returns the same instance each time so tests can assert
    # against ``fake_pa_instance.open.call_args`` without juggling per-call
    # state.
    fake_module.PyAudio = MagicMock(return_value=fake_pa_instance)

    # Convenience handles for tests.
    return SimpleNamespace(
        module=fake_module,
        instance=fake_pa_instance,
        stream=fake_stream,
    )


# ---------- AW-01: module imports on macOS without pyaudiowpatch ----------


def test_module_imports_on_macos_without_pyaudiowpatch():
    """``from vibemix.platform._audio_windows import AudioWindows`` must succeed
    on darwin without pulling pyaudiowpatch into ``sys.modules`` (Critical
    Constraint 3 — lazy import discipline).
    """
    # Drop pyaudiowpatch + the audio_windows module from sys.modules so we
    # re-import cleanly.
    for mod in ("pyaudiowpatch", "vibemix.platform._audio_windows"):
        sys.modules.pop(mod, None)

    from vibemix.platform._audio_windows import (  # noqa: F401
        AudioWindows,
        assert_wasapi_loopback_rate,
    )

    assert "pyaudiowpatch" not in sys.modules


# ---------- AW-02: AudioBackend Protocol satisfaction ----------


def test_audio_windows_satisfies_protocol(monkeypatch, make_registry_recorder):
    """``isinstance(AudioWindows(reg, rec), AudioBackend) is True`` — structural
    @runtime_checkable Protocol confirms required method names exist.
    """
    fake = _make_fake_pa()
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(registry=reg, recorder=rec)
    assert isinstance(backend, AudioBackend) is True


# ---------- AW-03: find_device input substring match (Windows-style names) ----------


def test_find_device_input_substring_match(monkeypatch, make_registry_recorder):
    """Match a device name with parens + suffix style typical on Windows
    ("Microphone (Realtek(R) Audio)") on input substring "Realtek".
    """
    devices = [
        {"name": "Microphone (Realtek(R) Audio)", "maxInputChannels": 2, "maxOutputChannels": 0},
        {"name": "Speakers (Realtek(R) Audio)", "maxInputChannels": 0, "maxOutputChannels": 2},
        {"name": "Headphones (USB Audio)", "maxInputChannels": 0, "maxOutputChannels": 2},
    ]
    fake = _make_fake_pa(devices=devices)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(reg, rec)
    assert backend.find_device("Realtek", "input") == 0
    assert backend.find_device("Headphones", "output") == 2


# ---------- AW-04: find_device raises with candidate list on miss ----------


def test_find_device_raises_with_candidate_list(monkeypatch, make_registry_recorder):
    """Substring "Bose" with no match → RuntimeError whose message includes
    "Available input devices:" and the candidate device names.
    """
    devices = [
        {"name": "Microphone (Realtek(R) Audio)", "maxInputChannels": 2, "maxOutputChannels": 0},
        {"name": "Speakers (Realtek(R) Audio)", "maxInputChannels": 0, "maxOutputChannels": 2},
        {"name": "Headphones (USB Audio)", "maxInputChannels": 0, "maxOutputChannels": 2},
    ]
    fake = _make_fake_pa(devices=devices)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(reg, rec)
    with pytest.raises(RuntimeError) as exc_info:
        backend.find_device("Bose", "input")
    msg = str(exc_info.value)
    assert "Available input devices:" in msg
    assert "Microphone (Realtek(R) Audio)" in msg


# ---------- AW-05: find_device handles Unicode names ----------


def test_find_device_unicode_match(monkeypatch, make_registry_recorder):
    """Unicode device name + Unicode substring match (case-insensitive)."""
    devices = [
        {"name": "Microfón (USB) ñ", "maxInputChannels": 1, "maxOutputChannels": 0},
        {"name": "Speakers", "maxInputChannels": 0, "maxOutputChannels": 2},
    ]
    fake = _make_fake_pa(devices=devices)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(reg, rec)
    assert backend.find_device("Microfón", "input") == 0


# ---------- AW-06: assert_wasapi_loopback_rate passes on 48000 ----------


def test_assert_wasapi_loopback_rate_passes(monkeypatch):
    """Loopback device reports 48000 default rate + we expect 48000 → no raise.

    Returns ``(index, name)`` so the caller (open_capture) can use the loopback
    index directly without re-querying.
    """
    fake = _make_fake_pa(
        loopback_info={
            "index": 7,
            "name": "Speakers (Loopback)",
            "defaultSampleRate": 48000.0,
            "maxInputChannels": 2,
        }
    )
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import assert_wasapi_loopback_rate

    idx, name = assert_wasapi_loopback_rate(expected=48000)
    assert idx == 7
    assert name == "Speakers (Loopback)"
    # PyAudio instance was created + terminated (no leak).
    fake.module.PyAudio.assert_called_once()
    fake.instance.terminate.assert_called_once()


# ---------- AW-07: assert_wasapi_loopback_rate raises on non-48000 ----------


def test_assert_wasapi_loopback_rate_raises_on_44100(monkeypatch):
    """Loopback device at 44100 + expected 48000 → SampleRateMismatchError with
    Windows-specific message ("Control Panel", "Sound", "Default Format",
    "48,000 Hz"). Includes the device name in the message so the user knows
    which "Speakers" to fix.
    """
    fake = _make_fake_pa(
        loopback_info={
            "index": 7,
            "name": "Speakers (Loopback)",
            "defaultSampleRate": 44100.0,
            "maxInputChannels": 2,
        }
    )
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import assert_wasapi_loopback_rate

    with pytest.raises(SampleRateMismatchError) as exc_info:
        assert_wasapi_loopback_rate(expected=48000)

    msg = str(exc_info.value)
    assert "Control Panel" in msg
    assert "Sound" in msg
    assert "Default Format" in msg
    assert "48,000 Hz" in msg
    assert "Speakers (Loopback)" in msg
    # PyAudio was still terminated even when the guard raised — no instance leak.
    fake.instance.terminate.assert_called_once()


# ---------- AW-08: open_capture uses WASAPI loopback index ----------


def test_open_capture_uses_wasapi_loopback_index(monkeypatch, make_registry_recorder):
    """``open_capture(device_index=999, ...)`` ignores the supplied
    device_index in favour of the loopback index returned by
    ``get_default_wasapi_loopback_device()`` (here = 7). Asserts the exact
    PyAudio ``open(...)`` call shape: format=paInt16, channels=2, rate=48000,
    input=True, input_device_index=7, frames_per_buffer=480, stream_callback
    truthy.
    """
    fake = _make_fake_pa(
        loopback_info={
            "index": 7,
            "name": "Speakers (Loopback)",
            "defaultSampleRate": 48000.0,
            "maxInputChannels": 2,
        }
    )
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(reg, rec)

    def cb(*_a, **_kw):  # pragma: no cover — not called in mock
        return None

    backend.open_capture(
        999,  # IGNORED by WASAPI loopback path
        sample_rate=48000,
        channels=2,
        block_size=480,
        callback=cb,
    )

    # Pull the ``open`` kwargs (we expect kwargs, not positional).
    fake.instance.open.assert_called_once()
    kwargs = fake.instance.open.call_args.kwargs
    assert kwargs["format"] == fake.module.paInt16
    assert kwargs["channels"] == 2
    assert kwargs["rate"] == 48000
    assert kwargs["input"] is True
    assert kwargs["input_device_index"] == 7
    assert kwargs["frames_per_buffer"] == 480
    assert kwargs["stream_callback"] is cb


# ---------- AW-09: open_capture pre-open guard short-circuits ----------


def test_open_capture_pre_open_guard(monkeypatch, make_registry_recorder):
    """Loopback at 44100 + open_capture(48000) → SampleRateMismatchError
    raised BEFORE ``PyAudio().open(...)`` is invoked.
    """
    fake = _make_fake_pa(
        loopback_info={
            "index": 7,
            "name": "Speakers (Loopback)",
            "defaultSampleRate": 44100.0,
            "maxInputChannels": 2,
        }
    )
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(reg, rec)

    with pytest.raises(SampleRateMismatchError):
        backend.open_capture(
            0, sample_rate=48000, channels=2, block_size=480, callback=lambda *a: None
        )

    # ``open`` must NOT have been called — the guard short-circuited.
    assert fake.instance.open.call_count == 0


# ---------- AW-10: returned stream handle satisfies AudioStream Protocol ----------


def test_open_capture_stream_handle_satisfies_audio_stream_protocol(
    monkeypatch, make_registry_recorder
):
    """Returned handle has ``latency_ms`` property + ``start()`` + ``stop()`` +
    ``close()`` methods. ``isinstance(handle, AudioStream)`` is True via the
    structural protocol check.
    """
    fake = _make_fake_pa()
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake.module)

    from vibemix.platform._audio_windows import AudioWindows

    reg, rec = make_registry_recorder()
    backend = AudioWindows(reg, rec)
    handle = backend.open_capture(
        0, sample_rate=48000, channels=2, block_size=480, callback=lambda *a: None
    )

    # Structural protocol check — Phase 1 AudioStream Protocol is not
    # @runtime_checkable but the duck-typed interface is the contract:
    # latency_ms (property), start, stop, close.
    assert isinstance(handle.latency_ms, float)
    assert handle.latency_ms == pytest.approx(5.0)
    assert callable(handle.start)
    assert callable(handle.stop)
    assert callable(handle.close)

    # Lifecycle methods delegate to the underlying PyAudio Stream.
    handle.stop()
    fake.stream.stop_stream.assert_called_once()
    handle.close()
    fake.stream.close.assert_called_once()
    # close() also terminates the parent PyAudio instance (no leaks).
    fake.instance.terminate.assert_called_once()

    # Bonus: AudioStream protocol structural check (it's NOT runtime_checkable
    # but we duck-type-verify the interface above; this is documentation).
    _ = AudioStream  # imported above for reference
