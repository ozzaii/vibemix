# SPDX-License-Identifier: Apache-2.0
"""SMOKE-01..06 — integration smoke tests for src/vibemix/__main__.py.

Verifies end-to-end wiring without real audio devices, LiveKit room, or
Gemini connectivity. Mocks ``AudioMacOS`` factories, the LiveKit
``AgentSession``, the ``build_llm`` + ``build_tts_chain`` factories, the
``DJCoHostAgent`` + ``PlaybackQueueAudioOutput`` constructors, and the
``genai.Client`` so the smoke test runs in CI on any machine.

Strategy:
- Patch ``AudioMacOS.find_device`` to return canned device indices.
- Patch the 4 ``open_*`` methods to return mocks with start/stop/close.
- Patch ``ScreenMacOS.run_capture_loop`` / ``TrackMacOS.run_poll_loop`` to
  no-op coroutines so they don't try to call mss / nowplaying-cli.
- Patch ``MidiMacOS.start_listener_thread`` to return a no-op thread.
- Patch ``AgentSession`` so ``session.start`` is an AsyncMock.
- Patch ``genai.Client`` so it doesn't try to authenticate.
- Patch ``DJCoHostAgent`` and ``PlaybackQueueAudioOutput`` to MagicMocks.
- Patch ``vibemix.runtime.coach.asyncio.sleep`` to fast-forward through
  the 2.0s warmup + the 0.1s poll cadence.
- Fire ``manual_trigger.set()`` via the test driver, then set
  ``stop_event`` to tear down cleanly.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from livekit.agents import NOT_GIVEN

from vibemix import __version__
from vibemix.agent.local_tts import LocalTTSUnavailable

_REAL_SLEEP = asyncio.sleep


def test_direct_genai_client_sets_request_timeout(mocker):
    """Direct mode must not leave raw Gemini requests unbounded."""
    import vibemix.__main__ as main_mod

    client = object()
    ctor = mocker.patch.object(main_mod.genai, "Client", return_value=client)

    assert main_mod._direct_genai_client("dummy-key") is client
    assert ctor.call_args.kwargs["api_key"] == "dummy-key"
    assert ctor.call_args.kwargs["http_options"].timeout == 120_000


def test_input_callback_uses_background_audio_processor(monkeypatch):
    """Live input resampling must not run on the CoreAudio callback thread."""
    import vibemix.__main__ as main_mod

    resample_threads: list[str] = []
    resampled = threading.Event()

    def fake_resample(samples, *, source_sr, target_sr):
        resample_threads.append(threading.current_thread().name)
        resampled.set()
        return np.zeros(max(1, len(samples) // 3), dtype=np.float32)

    class BufferSpy:
        def __init__(self) -> None:
            self.items: list[object] = []

        def push(self, item) -> None:
            self.items.append(item)

    class RecorderSpy:
        def __init__(self) -> None:
            self.items: list[bytes] = []

        def push_input(self, item: bytes) -> None:
            self.items.append(item)

    class LevelsSpy:
        def __init__(self) -> None:
            self.updated = False

        def update_music(self, _pcm) -> None:
            self.updated = True

    class MicSpy:
        def pull(self, _frames):
            return b""

    monkeypatch.setattr(main_mod, "resample_audio", fake_resample)
    audio_buf = BufferSpy()
    clean_audio_buf = BufferSpy()
    recorder = RecorderSpy()
    processor = main_mod._InputAudioProcessor(
        audio_buf=audio_buf,
        clean_audio_buf=clean_audio_buf,
        recorder=recorder,
        source_sr=48000,
    )
    levels = LevelsSpy()
    try:
        callback = main_mod._input_callback_factory(
            levels,
            BufferSpy(),
            MicSpy(),
            audio_buf,
            clean_audio_buf,
            recorder,
            source_sr=48000,
            input_audio_processor=processor,
        )
        callback(np.ones((480, 2), dtype=np.float32) * 0.1, 480, None, None)

        assert resampled.wait(timeout=1.0)
    finally:
        processor.close()

    assert levels.updated is True
    assert resample_threads == ["vibemix-input-audio-worker"]
    assert audio_buf.items
    assert clean_audio_buf.items
    assert recorder.items


def test_input_callback_throttles_deck_audio_context_updates():
    """Full deck-audio evidence context is too heavy to rebuild every 10ms."""
    import vibemix.__main__ as main_mod

    class BufferSpy:
        def push(self, _item) -> None:
            pass

    class LevelsSpy:
        def update_music(self, _pcm) -> None:
            pass

    class MicSpy:
        def pull(self, _frames):
            return b""

    class ProcessorSpy:
        def __init__(self) -> None:
            self.blocks = 0

        def push(self, _music48) -> None:
            self.blocks += 1

    class DeckCaptureSpy:
        def __init__(self) -> None:
            self._clock_s = 0.0
            self.context_calls = 0

        def process(self, indata, *, source_sr, **_kwargs):
            self._clock_s += indata.shape[0] / float(source_sr)
            mono = indata.mean(axis=1).astype(np.float32)
            stereo = np.repeat(mono[:, None], 2, axis=1).astype(np.float32)
            return SimpleNamespace(master_mono=mono, passthrough_stereo=stereo)

        def context(self):
            self.context_calls += 1
            return {"deck_audio_rms": {"A": 0.1, "B": 0.0}}

    deck_capture = DeckCaptureSpy()
    audio_context: dict[str, object] = {}
    processor = ProcessorSpy()
    callback = main_mod._input_callback_factory(
        LevelsSpy(),
        BufferSpy(),
        MicSpy(),
        BufferSpy(),
        BufferSpy(),
        SimpleNamespace(push_input=lambda _pcm: None),
        deck_audio_capture=deck_capture,
        audio_capture_context=audio_context,
        source_sr=48000,
        input_audio_processor=processor,
    )

    block = np.ones((480, 4), dtype=np.float32) * 0.1
    for _ in range(30):
        callback(block, 480, None, None)

    assert processor.blocks == 30
    assert deck_capture.context_calls == 2
    assert audio_context["deck_audio_rms"] == {"A": 0.1, "B": 0.0}


def _assert_tts_chain_boot_call(build_tts_chain: MagicMock) -> object:
    build_tts_chain.assert_called_once()
    kwargs = build_tts_chain.call_args.kwargs
    assert kwargs["mode"] == "direct"
    assert kwargs["voice"] == "Adam"
    assert set(kwargs) == {"mode", "voice", "moss"}
    moss = kwargs["moss"]
    assert hasattr(moss, "set_voice")
    assert hasattr(moss, "synthesize_pcm")
    return moss


# ---------------------------------------------------------------------------
# SMOKE-01 — --version exits zero without devices / keys
# ---------------------------------------------------------------------------


def test_smoke_01_version_exits_zero_without_devices_or_keys():
    """SMOKE-01: ``python -m vibemix --version`` returns code 0 and prints
    the package version. Runs in a subprocess so we can verify env-stripped
    behavior (no GEMINI_API_KEY required for argparse to short-circuit)."""
    result = subprocess.run(
        [sys.executable, "-m", "vibemix", "--version"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert f"vibemix {__version__}" in result.stdout


def test_smoke_01b_main_import_does_not_load_cohost_provider_plugins():
    """Importing the CLI module must stay light for library/model commands."""
    code = """
import sys
import vibemix.__main__  # noqa
loaded = [
    m for m in sys.modules
    if m == "grpc" or m.startswith("google.cloud") or m.startswith("livekit.plugins")
]
if loaded:
    raise SystemExit("\\n".join(loaded))
print("ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "ok" in result.stdout


def test_smoke_01c_bench_cli_is_source_only_in_frozen_sidecar(mocker, capsys):
    """The dev bench harness should fail clearly when omitted from frozen builds."""
    import vibemix.__main__ as main_mod

    mocker.patch.object(main_mod.sys, "frozen", True, create=True)

    assert main_mod._run_bench_cli(["run"]) == 2
    assert "source-only dev/eval command" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# SMOKE-02 — missing GEMINI_API_KEY exits non-zero
# ---------------------------------------------------------------------------


def test_smoke_02_missing_gemini_key_exits_nonzero(monkeypatch):
    """SMOKE-02: ``cli_entry([])`` with no GEMINI_API_KEY raises SystemExit.

    Tricky timing: ``vibemix.__main__`` calls ``load_dotenv()`` at module
    load. If the module hasn't been imported yet in this test process,
    the import below triggers the load and re-populates os.environ from
    .env. So we must delete the env vars AFTER the import (after
    load_dotenv has run) so the in-process check inside ``main()`` sees
    them as absent."""
    # Trigger module load (and the module-level load_dotenv() side effect)
    from vibemix.__main__ import cli_entry

    # NOW clear the env vars — main() reads them fresh on each call
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc:
        cli_entry([])

    # RELEASE-AUTH: the missing-key gate now exits with the no-retry sentinel
    # code 4 (the Tauri watchdog routes it to the "set your API key" banner
    # instead of looping). The human-readable [FATAL] explanation goes to
    # stderr (verified by the watchdog's read_last_log_line), so the
    # SystemExit payload is the bare exit code, not the message string.
    assert exc.value.code == 4


# ---------------------------------------------------------------------------
# SMOKE-03 — full wiring smoke
# ---------------------------------------------------------------------------


def _build_audio_mocks(mocker):
    """Patch all AudioMacOS factories. Returns the find_device + open_*
    mocks for assertion."""
    import vibemix.__main__ as main_mod

    find_device = MagicMock(
        side_effect=lambda name, kind: {
            "BlackHole 2ch": 0,
            "AI Capture": 1,
            "MacBook Pro Microphone": 2,
        }.get(name, 99)
    )
    mocker.patch.object(main_mod.AudioMacOS, "find_device", find_device)

    # find_output_device (graceful output resolver) — delegate to the canned
    # find_device for parity with the pre-2026-05-29 single-call behavior.
    find_output_device = MagicMock(
        side_effect=lambda preferred_index, fallback_name: find_device(fallback_name, "output")
    )
    mocker.patch.object(main_mod.AudioMacOS, "find_output_device", find_output_device)

    def _stream():
        s = MagicMock()
        s.start = MagicMock()
        s.stop = MagicMock()
        s.close = MagicMock()
        return s

    open_capture = MagicMock(return_value=_stream())
    open_voice_output = MagicMock(return_value=_stream())
    open_passthrough_output = MagicMock(return_value=_stream())
    open_mic_capture = MagicMock(return_value=_stream())
    describe_capture_input = MagicMock(
        return_value={
            "requested_device": "BlackHole 2ch",
            "device_name": "BlackHole 2ch",
            "input_channels": 2,
            "opened_channels": 2,
            "sample_rate": 48000,
        }
    )
    mocker.patch.object(main_mod.AudioMacOS, "open_capture", open_capture)
    mocker.patch.object(main_mod.AudioMacOS, "open_voice_output", open_voice_output)
    mocker.patch.object(main_mod.AudioMacOS, "open_passthrough_output", open_passthrough_output)
    mocker.patch.object(main_mod.AudioMacOS, "open_mic_capture", open_mic_capture)
    mocker.patch.object(main_mod.AudioMacOS, "describe_capture_input", describe_capture_input)

    return {
        "find_device": find_device,
        "find_output_device": find_output_device,
        "open_capture": open_capture,
        "open_voice_output": open_voice_output,
        "open_passthrough_output": open_passthrough_output,
        "open_mic_capture": open_mic_capture,
        "describe_capture_input": describe_capture_input,
    }


def test_deck_audio_auto_upgrades_default_blackhole_input(monkeypatch, mocker):
    import vibemix.__main__ as main_mod

    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "auto")
    monkeypatch.delenv("VIBEMIX_INPUT_DEVICE", raising=False)
    backend = MagicMock()
    backend.find_device.return_value = 16

    def _describe(device_index, *, requested_device, opened_channels):
        return {
            "requested_device": requested_device,
            "device_name": requested_device,
            "input_channels": 16 if requested_device == "BlackHole 16ch" else 2,
            "opened_channels": opened_channels,
            "sample_rate": 48000,
            "device_index": device_index,
        }

    backend.describe_capture_input.side_effect = _describe
    original_routing = MagicMock(
        reason="capture_device_too_few_channels",
        required_opened_channels=4,
        opened_channels=2,
    )
    upgraded_routing = MagicMock(enabled=True, opened_channels=4)
    routing_from_env = mocker.patch.object(
        main_mod,
        "deck_audio_routing_from_env",
        return_value=upgraded_routing,
    )

    idx, name, context, routing = main_mod._maybe_upgrade_input_device_for_deck_audio(
        backend,
        input_idx=0,
        input_device_name="BlackHole 2ch",
        base_audio_capture_context=_describe(
            0,
            requested_device="BlackHole 2ch",
            opened_channels=2,
        ),
        deck_audio_routing=original_routing,
    )

    assert idx == 16
    assert name == "BlackHole 16ch"
    assert context["requested_device"] == "BlackHole 16ch"
    assert context["opened_channels"] == 4
    assert routing is upgraded_routing
    backend.find_device.assert_called_once_with("BlackHole 16ch", "input")
    routing_from_env.assert_called_once()
    assert routing_from_env.call_args.kwargs["input_channels"] == 16


def test_deck_audio_auto_respects_explicit_input_device(monkeypatch):
    import vibemix.__main__ as main_mod

    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "auto")
    monkeypatch.setenv("VIBEMIX_INPUT_DEVICE", "BlackHole 2ch")
    backend = MagicMock()
    original_context = {"requested_device": "BlackHole 2ch"}
    original_routing = MagicMock(
        reason="capture_device_too_few_channels",
        required_opened_channels=4,
        opened_channels=2,
    )

    idx, name, context, routing = main_mod._maybe_upgrade_input_device_for_deck_audio(
        backend,
        input_idx=0,
        input_device_name="BlackHole 2ch",
        base_audio_capture_context=original_context,
        deck_audio_routing=original_routing,
    )

    assert (idx, name, context, routing) == (
        0,
        "BlackHole 2ch",
        original_context,
        original_routing,
    )
    backend.find_device.assert_not_called()


def test_deck_audio_global_default_upgrades_blackhole_without_env(monkeypatch, mocker):
    # ZERO-CONFIG (Kaan 2026-05-30: "nobody will set this"): with NO env var, a
    # rekordbox external-mixer config that needs more channels than the default
    # 2ch BlackHole must STILL upgrade the input to BlackHole 16ch. The routing's
    # `capture_device_too_few_channels` reason is the only signal we need — it no
    # longer requires VIBEMIX_DECK_AUDIO_CHANNELS=auto to act.
    import vibemix.__main__ as main_mod

    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)  # global default
    monkeypatch.delenv("VIBEMIX_INPUT_DEVICE", raising=False)
    backend = MagicMock()
    backend.find_device.return_value = 16

    def _describe(device_index, *, requested_device, opened_channels):
        return {
            "requested_device": requested_device,
            "device_name": requested_device,
            "input_channels": 16 if requested_device == "BlackHole 16ch" else 2,
            "opened_channels": opened_channels,
            "sample_rate": 48000,
            "device_index": device_index,
        }

    backend.describe_capture_input.side_effect = _describe
    original_routing = MagicMock(
        reason="capture_device_too_few_channels",
        required_opened_channels=4,
        opened_channels=2,
    )
    upgraded_routing = MagicMock(enabled=True, opened_channels=4)
    mocker.patch.object(main_mod, "deck_audio_routing_from_env", return_value=upgraded_routing)

    idx, name, context, routing = main_mod._maybe_upgrade_input_device_for_deck_audio(
        backend,
        input_idx=0,
        input_device_name="BlackHole 2ch",
        base_audio_capture_context=_describe(
            0,
            requested_device="BlackHole 2ch",
            opened_channels=2,
        ),
        deck_audio_routing=original_routing,
    )

    assert idx == 16
    assert name == "BlackHole 16ch"
    assert context["opened_channels"] == 4
    assert routing is upgraded_routing
    backend.find_device.assert_called_once_with("BlackHole 16ch", "input")


def test_deck_audio_global_default_skips_upgrade_without_too_few_signal(monkeypatch):
    # The relaxed gate must not over-trigger: with NO env var AND a routing reason
    # that is not the device-too-narrow upgrade signal, leave the input untouched.
    import vibemix.__main__ as main_mod

    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_INPUT_DEVICE", raising=False)
    backend = MagicMock()
    original_context = {"requested_device": "BlackHole 2ch"}
    original_routing = MagicMock(
        reason="disabled",
        required_opened_channels=0,
        opened_channels=2,
    )

    result = main_mod._maybe_upgrade_input_device_for_deck_audio(
        backend,
        input_idx=0,
        input_device_name="BlackHole 2ch",
        base_audio_capture_context=original_context,
        deck_audio_routing=original_routing,
    )

    assert result == (0, "BlackHole 2ch", original_context, original_routing)
    backend.find_device.assert_not_called()


def _build_sensor_mocks(mocker):
    """Patch screen / midi / track backends to no-op."""
    import vibemix.__main__ as main_mod

    screen_capture = AsyncMock(return_value=None)
    track_poll = AsyncMock(return_value=None)
    mocker.patch.object(main_mod.ScreenMacOS, "run_capture_loop", screen_capture)
    mocker.patch.object(main_mod.TrackMacOS, "run_poll_loop", track_poll)

    fake_midi_thread = MagicMock()
    fake_midi_thread.is_alive = MagicMock(return_value=True)
    mocker.patch.object(
        main_mod.MidiMacOS,
        "start_listener_thread",
        MagicMock(return_value=fake_midi_thread),
    )
    return {
        "screen_capture": screen_capture,
        "track_poll": track_poll,
    }


def test_deck_vision_capture_env_gate_defaults_off(monkeypatch):
    import vibemix.__main__ as main_mod

    monkeypatch.delenv("VIBEMIX_DECK_VISION", raising=False)
    assert main_mod._deck_vision_capture_enabled() is False

    monkeypatch.setenv("VIBEMIX_DECK_VISION", "1")
    assert main_mod._deck_vision_capture_enabled() is True

    monkeypatch.setenv("VIBEMIX_DECK_VISION", "true")
    assert main_mod._deck_vision_capture_enabled() is True

    monkeypatch.setenv("VIBEMIX_DECK_VISION", "off")
    assert main_mod._deck_vision_capture_enabled() is False


def _build_state_refresh_noop(mocker):
    """Patch state_refresh_loop to no-op so it doesn't touch the audio_buf."""
    import vibemix.__main__ as main_mod

    async def noop_async(*a, **kw):
        # Wait on stop_event so the task stays alive until cancelled
        stop_event = a[4] if len(a) > 4 else None
        if stop_event is not None:
            await stop_event.wait()
        return None

    mocker.patch.object(main_mod, "state_refresh_loop", noop_async)


def _build_livekit_mocks(mocker):
    """Patch AgentSession + genai.Client + DJCoHostAgent + PlaybackQueueAudioOutput."""
    import vibemix.__main__ as main_mod

    session_mock = MagicMock()
    session_mock.start = AsyncMock(return_value=None)
    session_mock.aclose = AsyncMock(return_value=None)
    session_mock.generate_reply = MagicMock(
        return_value=MagicMock(wait_for_playout=AsyncMock(return_value=None))
    )

    # output is a MagicMock with an audio attribute that's settable
    output_obj = MagicMock()
    output_obj.audio = None
    session_mock.output = output_obj

    agent_session_factory = MagicMock(return_value=session_mock)
    mocker.patch.object(main_mod, "AgentSession", agent_session_factory)

    # genai.Client and its async generate_content_stream
    async def fake_stream(*a, **kw):
        async def gen():
            for word in ("hello", " ", "kaan"):
                yield MagicMock(text=word)

        return gen()

    genai_client_mock = MagicMock()
    genai_client_mock.aio.models.generate_content_stream = AsyncMock(side_effect=fake_stream)
    mocker.patch.object(main_mod.genai, "Client", MagicMock(return_value=genai_client_mock))

    # build_llm + build_tts_chain → MagicMocks
    build_llm_mock = MagicMock(return_value=MagicMock())
    build_tts_mock = MagicMock(return_value=MagicMock())
    mocker.patch.object(main_mod, "build_llm", build_llm_mock)
    mocker.patch.object(main_mod, "build_tts_chain", build_tts_mock)

    # DJCoHostAgent + PlaybackQueueAudioOutput → MagicMocks
    agent_factory = MagicMock(return_value=MagicMock())
    sink_factory = MagicMock(return_value=MagicMock())
    mocker.patch.object(main_mod, "DJCoHostAgent", agent_factory)
    mocker.patch.object(main_mod, "PlaybackQueueAudioOutput", sink_factory)

    return {
        "session": session_mock,
        "AgentSession": agent_session_factory,
        "genai_client": genai_client_mock,
        "build_llm": build_llm_mock,
        "build_tts_chain": build_tts_mock,
        "DJCoHostAgent": agent_factory,
        "PlaybackQueueAudioOutput": sink_factory,
    }


def _patch_runtime_for_fast_smoke(mocker, tasks_seen: list):
    """Patch coach_loop / diag_loop / ws_broadcast to no-op coroutines that
    just exit on stop_event. Also patch the actual asyncio.create_task usage
    to record which coroutines are spawned (for assertion)."""
    import vibemix.__main__ as main_mod

    async def coach_noop(*a, **kw):
        tasks_seen.append("coach")
        stop_event = a[-1] if a else kw.get("stop_event")
        if stop_event is not None:
            await stop_event.wait()

    async def diag_noop(*a, **kw):
        tasks_seen.append("diag")
        stop_event = a[-1] if a else kw.get("stop_event")
        if stop_event is not None:
            await stop_event.wait()

    async def ws_noop(*a, **kw):
        tasks_seen.append("ws")
        stop_event = a[-1] if a else kw.get("stop_event")
        if stop_event is not None:
            await stop_event.wait()

    mocker.patch.object(main_mod, "coach_loop", coach_noop)
    mocker.patch.object(main_mod, "diag_loop", diag_noop)
    mocker.patch.object(main_mod, "ws_broadcast", ws_noop)


def _patch_voice_recorder(mocker, tmp_path):
    """Use a tmp_path-rooted VoiceRecorder so the test doesn't pollute the
    project's recordings/ folder. Accepts and discards any kwargs main()
    happens to pass (currently ``root=``) so the override always wins."""
    import vibemix.__main__ as main_mod

    real_vr = main_mod.VoiceRecorder

    def factory(*_a, **_kw):
        return real_vr(root=tmp_path / "recordings")

    mocker.patch.object(main_mod, "VoiceRecorder", factory)


def test_smoke_03_full_wiring(monkeypatch, mocker, tmp_path):
    """SMOKE-03: full main() wiring smoke. Mocks all device + LiveKit +
    Gemini surfaces and verifies the orchestration."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
    monkeypatch.delenv("VIBEMIX_RECALL_ENABLED", raising=False)
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)
    # Importing vibemix.__main__ can load the developer .env before the patch
    # above takes effect; re-assert the dummy keys after that import side effect.
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
    monkeypatch.delenv("VIBEMIX_RECALL_ENABLED", raising=False)
    # MOSS is the only voice; legacy cloud voice env must not affect boot.
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_DECK_VISION", raising=False)
    # Pin per-deck OFF so the device-upgrade path is deterministic regardless of
    # the host's real rekordbox config — the zero-config global default reads
    # ~/Library Pioneer settings, and this is a wiring smoke, not a per-deck test.
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "off")
    monkeypatch.setenv("VIBEMIX_ENABLE_MIC", "1")

    audio_mocks = _build_audio_mocks(mocker)
    sensor_mocks = _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    livekit_mocks = _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)

    tasks_seen: list = []
    _patch_runtime_for_fast_smoke(mocker, tasks_seen)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        # Give main() a moment to wire everything up
        await _REAL_SLEEP(0.05)
        # Verify state-of-the-world AFTER setup but before teardown
        # Then tear down by simulating SIGINT — find the stop_event
        # actually used by main() — but since it's a local var, just wait
        # then cancel the main_task.
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    # (a) find_device called 3 times (input, output, mic)
    assert audio_mocks["find_device"].call_count == 3

    # (b) all 4 open_* called once
    assert audio_mocks["open_capture"].call_count == 1
    assert audio_mocks["open_voice_output"].call_count == 1
    assert audio_mocks["open_passthrough_output"].call_count == 1
    assert audio_mocks["open_mic_capture"].call_count == 1

    # (c) build_llm called with the dummy key in direct mode (Phase 5 explicit mode kwarg)
    livekit_mocks["build_llm"].assert_called_once_with("dummy-key", mode="direct")

    # (d) build_tts_chain gets the persisted MOSS voice + shared MOSS hook;
    # cloud keys stay out of voice.
    _assert_tts_chain_boot_call(livekit_mocks["build_tts_chain"])

    # (e) DJCoHostAgent constructed with non-None kwargs
    agent_call = livekit_mocks["DJCoHostAgent"].call_args
    for kw in (
        "genai_client",
        "clean_audio_buf",
        "screen_buf",
        "state",
        "recorder",
        "llm_inst",
        "tts_inst",
    ):
        assert agent_call.kwargs.get(kw) is not None, f"missing kwarg {kw}"
    assert agent_call.kwargs.get("recall") is None
    assert agent_call.kwargs.get("recall_enabled") is False
    assert livekit_mocks["genai_client"].models.embed_content.call_count == 0

    # (f) AgentSession constructed with llm + tts
    as_call = livekit_mocks["AgentSession"].call_args
    assert "llm" in as_call.kwargs
    assert "tts" in as_call.kwargs

    # (g) session.output.audio was assigned to a PlaybackQueueAudioOutput
    # (i.e. the constructor was called and the result assigned)
    assert livekit_mocks["PlaybackQueueAudioOutput"].call_count == 1
    assert livekit_mocks["session"].output.audio is not None

    # (h) session.start was awaited (with agent)
    assert livekit_mocks["session"].start.await_count == 1

    # (j) all 3 runtime loops were spawned (we can't easily test all 6 here;
    # the 3 we patched are confirmation enough for the wiring path)
    assert "coach" in tasks_seen
    assert "diag" in tasks_seen
    assert "ws" in tasks_seen
    sensor_mocks["screen_capture"].assert_not_called()
    sensor_mocks["track_poll"].assert_called_once()


def test_screen_vision_capture_opt_in_spawns_capture_task(monkeypatch, mocker, tmp_path):
    """Screen capture is a dormant live leg unless the explicit eval flag is set."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
    monkeypatch.delenv("VIBEMIX_RECALL_ENABLED", raising=False)
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "off")
    monkeypatch.setenv("VIBEMIX_DECK_VISION", "1")

    _build_audio_mocks(mocker)
    sensor_mocks = _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)

    tasks_seen: list = []
    _patch_runtime_for_fast_smoke(mocker, tasks_seen)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        await _REAL_SLEEP(0.05)
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    sensor_mocks["screen_capture"].assert_called_once()
    sensor_mocks["track_poll"].assert_called_once()


# ---------------------------------------------------------------------------
# SMOKE-04 — no OPENROUTER key still works
# ---------------------------------------------------------------------------


def test_smoke_04_no_openrouter_key(monkeypatch, mocker, tmp_path):
    """SMOKE-04: no OPENROUTER_API_KEY still boots MOSS-only voice."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    # MOSS is the only voice; legacy cloud voice env must not affect boot.
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    # Per-deck OFF — deterministic boot regardless of host rekordbox config.
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "off")

    _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    livekit_mocks = _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)

    tasks_seen: list = []
    _patch_runtime_for_fast_smoke(mocker, tasks_seen)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        await _REAL_SLEEP(0.05)
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    _assert_tts_chain_boot_call(livekit_mocks["build_tts_chain"])


def test_smoke_04b_missing_moss_model_boots_muted_not_cloud_fallback(
    monkeypatch,
    mocker,
    tmp_path,
    capsys,
):
    """Missing MOSS must not crash boot or create a cloud-TTS fallback."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "off")

    audio_mocks = _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    livekit_mocks = _build_livekit_mocks(mocker)
    livekit_mocks["build_tts_chain"].side_effect = LocalTTSUnavailable("MOSS model missing")
    _patch_voice_recorder(mocker, tmp_path)

    tasks_seen: list = []
    _patch_runtime_for_fast_smoke(mocker, tasks_seen)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        await _REAL_SLEEP(0.05)
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    _assert_tts_chain_boot_call(livekit_mocks["build_tts_chain"])
    assert livekit_mocks["AgentSession"].call_args.kwargs["tts"] is NOT_GIVEN
    assert livekit_mocks["DJCoHostAgent"].call_args.kwargs["tts_inst"] is NOT_GIVEN
    livekit_mocks["session"].output.set_audio_enabled.assert_called_once_with(False)
    assert audio_mocks["open_voice_output"].call_count == 0
    assert livekit_mocks["PlaybackQueueAudioOutput"].call_count == 0
    assert livekit_mocks["session"].output.audio is None
    assert livekit_mocks["session"].start.await_count == 1
    assert "voice muted, no cloud fallback" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# SMOKE-05 — cleanup runs all stream closes
# ---------------------------------------------------------------------------


def test_smoke_05_cleanup_closes_all_streams(monkeypatch, mocker, tmp_path):
    """SMOKE-05: after teardown, voice/pass/input/mic streams all had stop()
    AND close() called."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
    monkeypatch.setenv("VIBEMIX_ENABLE_MIC", "1")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    audio_mocks = _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)

    tasks_seen: list = []
    _patch_runtime_for_fast_smoke(mocker, tasks_seen)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        await _REAL_SLEEP(0.05)
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    # Each open_* returned a mock; access return_value.stop / close call_count
    for key in ("open_capture", "open_voice_output", "open_passthrough_output", "open_mic_capture"):
        stream_mock = audio_mocks[key].return_value
        assert stream_mock.stop.call_count >= 1, f"{key}: stop not called"
        assert stream_mock.close.call_count >= 1, f"{key}: close not called"


def test_close_tts_chain_closes_nested_providers_once() -> None:
    """The live TTS adapter owns nested provider sessions that need closing."""
    from vibemix.__main__ import _close_tts_chain

    class OwnedSession:
        def __init__(self) -> None:
            self.closed = False
            self.close_count = 0

        async def close(self) -> None:
            self.close_count += 1
            self.closed = True

    class Provider:
        def __init__(self) -> None:
            self.closed = 0

        async def aclose(self) -> None:
            self.closed += 1

    session = OwnedSession()
    child = Provider()
    child._session = session
    parent = Provider()
    parent._tts_instances = [child, child]
    parent._session = session

    asyncio.run(_close_tts_chain(parent))

    assert parent.closed == 1
    assert child.closed == 1
    assert session.close_count == 1


# ---------------------------------------------------------------------------
# Phase 5 — MAIN-03..07: proxy mode dispatch + failure paths
# ---------------------------------------------------------------------------


def _build_proxy_mocks(mocker, jwt_value="test-jwt", install_uuid_value="a" * 32):
    """Patch the Phase 5 install_uuid + get_or_refresh_jwt + build_proxy_genai_client."""
    import vibemix.__main__ as main_mod

    install_mock = MagicMock(return_value=install_uuid_value)
    mocker.patch.object(main_mod, "get_or_create_install_uuid", install_mock)

    async def fake_refresh(uuid, base_url, version):
        return jwt_value

    refresh_mock = MagicMock(side_effect=fake_refresh)
    mocker.patch.object(main_mod, "get_or_refresh_jwt", refresh_mock)

    proxy_genai_mock = MagicMock(return_value=MagicMock())
    mocker.patch.object(main_mod, "build_proxy_genai_client", proxy_genai_mock)

    return {
        "get_or_create_install_uuid": install_mock,
        "get_or_refresh_jwt": refresh_mock,
        "build_proxy_genai_client": proxy_genai_mock,
    }


def test_main_03_proxy_register_401_exits(monkeypatch, mocker, tmp_path):
    """MAIN-03: get_or_refresh_jwt raises RuntimeError → SystemExit, no fallback."""
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "proxy")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    import vibemix.__main__ as main_mod

    mocker.patch.object(main_mod, "get_or_create_install_uuid", MagicMock(return_value="a" * 32))

    async def boom(*a, **kw):
        raise RuntimeError("proxy /register rejected install_uuid (status=401)")

    mocker.patch.object(main_mod, "get_or_refresh_jwt", MagicMock(side_effect=boom))

    from vibemix.__main__ import main

    with pytest.raises(SystemExit) as exc:
        asyncio.run(main())
    msg = str(exc.value)
    assert "Proxy mode setup failed" in msg


def test_main_04_proxy_network_error_exits(monkeypatch, mocker):
    """MAIN-04: httpx.HTTPError → SystemExit, no fallback."""
    import httpx

    monkeypatch.setenv("VIBEMIX_LLM_MODE", "proxy")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    import vibemix.__main__ as main_mod

    mocker.patch.object(main_mod, "get_or_create_install_uuid", MagicMock(return_value="a" * 32))

    async def neterr(*a, **kw):
        raise httpx.ConnectError("no route")

    mocker.patch.object(main_mod, "get_or_refresh_jwt", MagicMock(side_effect=neterr))

    from vibemix.__main__ import main

    with pytest.raises(SystemExit) as exc:
        asyncio.run(main())
    assert "Proxy /register network error" in str(exc.value)


def test_main_05_proxy_mode_does_not_require_gemini_key(monkeypatch, mocker, tmp_path):
    """MAIN-05: proxy mode does not require GEMINI_API_KEY. Test runs main() to
    the LiveKit-mock teardown without raising SystemExit('GEMINI_API_KEY not set')."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "proxy")
    monkeypatch.setenv("VIBEMIX_PROXY_BASE_URL", "https://test.altidus.world")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)
    _patch_runtime_for_fast_smoke(mocker, [])
    proxy_mocks = _build_proxy_mocks(mocker)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        await _REAL_SLEEP(0.05)
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    # install_uuid + jwt refresh both called
    assert proxy_mocks["get_or_create_install_uuid"].call_count == 1
    assert proxy_mocks["get_or_refresh_jwt"].call_count == 1
    # Refresh got the right base_url
    args = proxy_mocks["get_or_refresh_jwt"].call_args
    assert args.args[0] == "a" * 32
    assert args.args[1] == "https://test.altidus.world"


def test_main_06_proxy_base_url_defaults_to_altidus(monkeypatch, mocker, tmp_path):
    """MAIN-06: default VIBEMIX_PROXY_BASE_URL = 'https://api.altidus.world'."""
    monkeypatch.delenv("VIBEMIX_PROXY_BASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "proxy")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)
    _patch_runtime_for_fast_smoke(mocker, [])
    proxy_mocks = _build_proxy_mocks(mocker)

    from vibemix.__main__ import main

    async def driver():
        main_task = asyncio.create_task(main())
        await _REAL_SLEEP(0.05)
        main_task.cancel()
        try:
            await asyncio.wait_for(main_task, timeout=3.0)
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(driver())

    args = proxy_mocks["get_or_refresh_jwt"].call_args
    assert args.args[1] == "https://api.altidus.world"


def test_main_07_unknown_mode_exits(monkeypatch):
    """MAIN-07: VIBEMIX_LLM_MODE=garbage → SystemExit."""
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "garbage")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    from vibemix.__main__ import main

    with pytest.raises(SystemExit) as exc:
        asyncio.run(main())
    assert "VIBEMIX_LLM_MODE" in str(exc.value)


# ---------------------------------------------------------------------------
# Phase 6 — VIBEMIX_GENRE_PROFILE env dispatch via apply_genre_env() helper
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_active_profile_for_genre_tests():
    """Wipe the active-profile singleton before and after the genre-env tests
    so cross-test pollution can't leak."""
    from vibemix.state.genre import profile as _mod

    _mod._ACTIVE_PROFILE = None
    yield
    _mod._ACTIVE_PROFILE = None


def test_main_genre_default_is_unpinned(monkeypatch):
    """Absent VIBEMIX_GENRE_PROFILE leaves live genre to auto-detect."""
    monkeypatch.delenv("VIBEMIX_GENRE_PROFILE", raising=False)
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied is None
    assert get_active_profile() is None


def test_main_genre_pop(monkeypatch):
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "pop")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied == "pop"
    assert get_active_profile().name == "pop"


def test_main_genre_drum_and_bass(monkeypatch):
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "drum_and_bass")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied == "drum_and_bass"
    assert get_active_profile().name == "drum_and_bass"


def test_main_genre_none_disables_active_profile(monkeypatch):
    """VIBEMIX_GENRE_PROFILE=none → Phase 3 absolute-threshold fallback."""
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "none")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied is None
    assert get_active_profile() is None


def test_main_genre_unknown_alias_disables(monkeypatch):
    """'unknown' is also an explicit alias for None."""
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "unknown")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied is None
    assert get_active_profile() is None


def test_main_genre_empty_string_disables(monkeypatch):
    """Empty string is treated as 'none' (defensive)."""
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    # Default kicks in for empty string since os.environ.get returns "" → strip → "" → into alias.
    applied = apply_genre_env()
    assert applied is None
    assert get_active_profile() is None


def test_main_genre_case_insensitive(monkeypatch):
    """Env value is .strip().lower()-ed before lookup."""
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "TECHNO")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied == "techno"
    assert get_active_profile().name == "techno"


def test_main_genre_whitespace_stripped(monkeypatch):
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "  house  ")
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied == "house"
    assert get_active_profile().name == "house"


def test_main_genre_unknown_sys_exits(monkeypatch):
    """Unknown profile name → sys.exit with clear message listing valid choices."""
    monkeypatch.setenv("VIBEMIX_GENRE_PROFILE", "reggaeton")
    from vibemix._main_helpers import apply_genre_env

    with pytest.raises(SystemExit) as exc:
        apply_genre_env()
    msg = str(exc.value)
    assert "VIBEMIX_GENRE_PROFILE" in msg
    assert "reggaeton" in msg
    # Valid choices listed:
    assert "techno" in msg
    assert "none" in msg


# ---------------------------------------------------------------------------
# Plan 19-05 — SMOKE-07/08 — GeminiContextCache wiring assertions
# ---------------------------------------------------------------------------
#
# These tests verify that __main__.py's source declares the cache + ack +
# cancel + ttft wiring symbols expected by Plan 19-05. The pre-existing
# smoke_03/04/05 failures (carried in baseline 9-failure set) prevent us
# from running main() to completion and asserting runtime cache.create
# behavior here — those failures are unrelated to Plan 19-05 (they exist
# in the wiring even before this plan's __main__ edits). We use AST-level
# inspection so the wiring contract is locked even when the live-runtime
# smoke harness is broken.


def test_smoke_07_main_imports_cache_and_latency_primitives() -> None:
    """SMOKE-07: __main__.py imports the post-ack-bank wiring symbols
    (GeminiContextCache + CancelGate + TTFTMeter).

    The AckBank surface was retired with the placeholder OPUS clips, so
    this test now asserts it is NOT importable from __main__.
    """
    from vibemix import __main__ as main_mod

    assert hasattr(main_mod, "GeminiContextCache"), "missing GeminiContextCache import"
    assert not hasattr(main_mod, "AckBank"), (
        "AckBank import leaked back into __main__.py — the placeholder ack-bank surface is retired"
    )
    assert hasattr(main_mod, "CancelGate"), "missing CancelGate import"
    assert hasattr(main_mod, "TTFTMeter"), "missing TTFTMeter import"
    assert hasattr(main_mod, "SYSTEM_INSTRUCTION"), "missing SYSTEM_INSTRUCTION import"


def test_smoke_08_main_source_wires_cache_create_with_graceful_degradation() -> None:
    """SMOKE-08: __main__.py source contains the cache.create + graceful-
    degradation pattern + the agent kwargs + the coach_loop kwargs.

    AST-level grep of the source file: avoids the smoke_03/04/05 pre-existing
    failure (main() teardown bug carried in baseline 9-failure set) while
    still locking the Plan 19-05 wiring contract. If a future regression
    drops cache=cache from DJCoHostAgent kwargs or removes the try/except
    around cache.create, this test catches it.
    """
    src = Path("src/vibemix/__main__.py").read_text()

    # Cache construction
    assert "GeminiContextCache(" in src, "GeminiContextCache constructor call missing"
    # The original v1 contract baked `system_instruction_body=SYSTEM_INSTRUCTION`
    # (= HYPE_INTERMEDIATE, Turkish hype). The 2026-05-21 fix (cache ≡ agent
    # invariant: the cached system instruction MUST match the agent's resolved
    # cell from VIBEMIX_SKILL_LEVEL / VIBEMIX_MODE / VIBEMIX_MOOD — otherwise
    # a warm cache silently overrides COACH_PRO/English with HYPE_INTERMEDIATE/
    # Turkish at runtime) replaced the hardcoded constant with a resolved local
    # `cache_system_instruction = _resolve_prompt_cell()`. Accept either form;
    # the load-bearing contract is "the cache is built with a system-instruction
    # body kwarg" — not which constant feeds it. Updated 2026-05-23 (Phase 67
    # / Plan 67P01).
    assert (
        "system_instruction_body=SYSTEM_INSTRUCTION" in src
        or "system_instruction_body=cache_system_instruction" in src
    ), (
        "GeminiContextCache must be built with a system_instruction_body kwarg "
        "(SYSTEM_INSTRUCTION OR cache_system_instruction)"
    )
    # `cache.create()` must be awaited. The 2026-05-21 fix wrapped the await
    # in `asyncio.wait_for(cache.create(), timeout=4.0)` (fail-fast against the
    # SDK's lack of a built-in timeout — a free-tier key on a project where
    # context caching is paid-tier hangs `caches.create()` indefinitely and
    # blocks boot before "listening to"). Accept the bare-await form OR the
    # timeout-wrapped form; both must include the `await` keyword.
    # WR-03 tightening (Phase 67 REVIEW): the wait_for-branch substring now
    # carries the `await ` prefix, so a future refactor that drops the
    # leading `await` (e.g. `_unused = asyncio.wait_for(cache.create(), …)`)
    # would silently never start the coroutine and silently regress the
    # cache-boot fail-fast guarantee — this test now catches that drift.
    # Updated 2026-05-23 (Phase 67 / Plan 67P01 + REVIEW WR-03).
    assert "await cache.create()" in src or "await asyncio.wait_for(cache.create()" in src, (
        "cache.create not awaited (bare or wait_for-wrapped form must be awaited)"
    )
    # Graceful degradation — cache=None on failure, no propagation of exception
    assert "cache = None" in src, "graceful-degradation cache=None branch missing"
    # Plan 41-02 — wall-clock refresh_loop deleted. Cache refresh is event-
    # driven (EvidenceRegistry.write() schedules a debounced cache.refresh()
    # via on_mutation callback). The smoke test now asserts the inverse:
    # the old background-task spawn must NOT appear in __main__.py.
    assert "cache.refresh_loop(" not in src, (
        "stale refresh_loop background task still spawned in __main__.py "
        "(Plan 41-02 removed wall-clock refresh)"
    )
    # And the new wiring must be present — EvidenceRegistry built with the
    # cache.refresh callback hooked via on_mutation.
    assert "on_mutation=lambda: cache.refresh()" in src, (
        "EvidenceRegistry(on_mutation=lambda: cache.refresh()) wiring "
        "missing — Plan 41-02 mutation-driven refresh must be wired"
    )
    # Agent gets cache + ttft_meter kwargs
    assert "cache=cache" in src, "DJCoHostAgent must receive cache=cache kwarg"
    assert "ttft_meter=ttft_meter" in src, "DJCoHostAgent must receive ttft_meter=ttft_meter kwarg"
    # coach_loop gets cancel_gate + ttft_meter + playback (no ack_bank
    # since the placeholder surface is retired).
    assert "ack_bank=" not in src, "ack_bank= kwarg leaked back into __main__.py wiring"
    assert "cancel_gate=cancel_gate" in src, "coach_loop must receive cancel_gate kwarg"
    assert "playback=playback" in src, "coach_loop must receive playback kwarg"
    # Construction order — TTFTMeter + CancelGate before agent. AckBank
    # is explicitly NOT instantiated anymore.
    assert "TTFTMeter()" in src, "TTFTMeter not instantiated"
    assert "AckBank(" not in src, "AckBank constructor leaked back into __main__.py"
    assert "CancelGate()" in src, "CancelGate not instantiated"


# ---------------------------------------------------------------------------
# Packaged defaults — the free on-device voice ships ON
# ---------------------------------------------------------------------------


def test_apply_packaged_defaults_opts_moss_in_when_absent(monkeypatch):
    """With no operator override, the packaged app turns the free MOSS voice ON.

    It does not turn the drop-call oracle on; spoken drop calls stay explicitly
    opted in until the mix-timing lane has live grounding proof.
    """
    from vibemix.__main__ import _apply_packaged_defaults

    monkeypatch.delenv("VIBEMIX_LOCAL_TTS", raising=False)
    monkeypatch.delenv("VIBEMIX_DROP_CALL", raising=False)

    _apply_packaged_defaults()

    assert os.environ["VIBEMIX_LOCAL_TTS"] == "1"
    assert "VIBEMIX_DROP_CALL" not in os.environ


def test_apply_packaged_defaults_respects_explicit_off(monkeypatch):
    """An explicit ``VIBEMIX_*=0`` is never clobbered — setdefault, not assign."""
    from vibemix.__main__ import _apply_packaged_defaults

    monkeypatch.setenv("VIBEMIX_LOCAL_TTS", "0")
    monkeypatch.setenv("VIBEMIX_DROP_CALL", "0")

    _apply_packaged_defaults()

    assert os.environ["VIBEMIX_LOCAL_TTS"] == "0"
    assert os.environ["VIBEMIX_DROP_CALL"] == "0"
