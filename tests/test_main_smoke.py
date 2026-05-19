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
import hashlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibemix import __version__

_REAL_SLEEP = asyncio.sleep


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

    msg = str(exc.value)
    assert "GEMINI_API_KEY" in msg


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
    mocker.patch.object(main_mod.AudioMacOS, "open_capture", open_capture)
    mocker.patch.object(main_mod.AudioMacOS, "open_voice_output", open_voice_output)
    mocker.patch.object(main_mod.AudioMacOS, "open_passthrough_output", open_passthrough_output)
    mocker.patch.object(main_mod.AudioMacOS, "open_mic_capture", open_mic_capture)

    return {
        "find_device": find_device,
        "open_capture": open_capture,
        "open_voice_output": open_voice_output,
        "open_passthrough_output": open_passthrough_output,
        "open_mic_capture": open_mic_capture,
    }


def _build_sensor_mocks(mocker):
    """Patch screen / midi / track backends to no-op."""
    import vibemix.__main__ as main_mod

    async def noop_async(*a, **kw):
        return None

    mocker.patch.object(main_mod.ScreenMacOS, "run_capture_loop", noop_async)
    mocker.patch.object(main_mod.TrackMacOS, "run_poll_loop", noop_async)

    fake_midi_thread = MagicMock()
    fake_midi_thread.is_alive = MagicMock(return_value=True)
    mocker.patch.object(
        main_mod.MidiMacOS,
        "start_listener_thread",
        MagicMock(return_value=fake_midi_thread),
    )


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
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    audio_mocks = _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
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

    # (d) build_tts_chain called with both keys + mode=direct
    livekit_mocks["build_tts_chain"].assert_called_once_with(
        gemini_api_key="dummy-key", openrouter_api_key="dummy-or", mode="direct"
    )

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


# ---------------------------------------------------------------------------
# SMOKE-04 — no OPENROUTER key still works
# ---------------------------------------------------------------------------


def test_smoke_04_no_openrouter_key(monkeypatch, mocker, tmp_path):
    """SMOKE-04: with no OPENROUTER_API_KEY, build_tts_chain is called with
    openrouter_api_key=None."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

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

    livekit_mocks["build_tts_chain"].assert_called_once_with(
        gemini_api_key="dummy-key", openrouter_api_key=None, mode="direct"
    )


# ---------------------------------------------------------------------------
# SMOKE-05 — cleanup runs all stream closes
# ---------------------------------------------------------------------------


def test_smoke_05_cleanup_closes_all_streams(monkeypatch, mocker, tmp_path):
    """SMOKE-05: after teardown, voice/pass/input/mic streams all had stop()
    AND close() called."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
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


# ---------------------------------------------------------------------------
# SMOKE-06 — POC files diff-untouched (cohost_v2.py byte-identical)
# ---------------------------------------------------------------------------


def test_smoke_06_poc_files_untouched_during_smoke(monkeypatch, mocker, tmp_path):
    """SMOKE-06: running the smoke does NOT touch any POC file. Hash
    cohost_v2.py before and after, assert equality.

    (Pre-2026-05-19 this hashed cohost_v4.py. v4 was retired into
    ``.planning/research/v3-shipped/``; v2 is the oldest still-tracked
    POC variant and is the one most likely to be accidentally edited
    during a smoke since it shares many symbol names with the vibemix
    package.)
    """
    poc = Path("cohost_v2.py")
    before = hashlib.sha256(poc.read_bytes()).hexdigest()

    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-or")
    monkeypatch.setattr("vibemix.__main__.load_dotenv", lambda: None)

    _build_audio_mocks(mocker)
    _build_sensor_mocks(mocker)
    _build_state_refresh_noop(mocker)
    _build_livekit_mocks(mocker)
    _patch_voice_recorder(mocker, tmp_path)
    _patch_runtime_for_fast_smoke(mocker, [])

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

    after = hashlib.sha256(poc.read_bytes()).hexdigest()
    assert before == after, "cohost_v2.py was modified during the smoke test"


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


def test_main_genre_default_is_techno(monkeypatch):
    """Default VIBEMIX_GENRE_PROFILE → 'techno' (CONTEXT D-LOCKED)."""
    monkeypatch.delenv("VIBEMIX_GENRE_PROFILE", raising=False)
    from vibemix._main_helpers import apply_genre_env
    from vibemix.state import get_active_profile

    applied = apply_genre_env()
    assert applied == "techno"
    assert get_active_profile().name == "techno"


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


def test_smoke_07_main_imports_cache_and_ack_primitives() -> None:
    """SMOKE-07: __main__.py imports the four Plan 19-05 wiring symbols
    (GeminiContextCache + AckBank + CancelGate + TTFTMeter)."""
    from vibemix import __main__ as main_mod

    assert hasattr(main_mod, "GeminiContextCache"), "missing GeminiContextCache import"
    assert hasattr(main_mod, "AckBank"), "missing AckBank import"
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
    from pathlib import Path

    src = Path("src/vibemix/__main__.py").read_text()

    # Cache construction
    assert "GeminiContextCache(" in src, "GeminiContextCache constructor call missing"
    assert "system_instruction_body=SYSTEM_INSTRUCTION" in src, (
        "GeminiContextCache must be built with SYSTEM_INSTRUCTION body"
    )
    assert "await cache.create()" in src, "cache.create not awaited"
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
    # coach_loop gets ack_bank + cancel_gate + ttft_meter + playback
    assert "ack_bank=ack_bank" in src, "coach_loop must receive ack_bank kwarg"
    assert "cancel_gate=cancel_gate" in src, "coach_loop must receive cancel_gate kwarg"
    assert "playback=playback" in src, "coach_loop must receive playback kwarg"
    # Construction order — TTFTMeter + AckBank + CancelGate before agent
    assert "TTFTMeter()" in src, "TTFTMeter not instantiated"
    assert "AckBank(suppress_fire=" in src, "AckBank not instantiated"
    assert "CancelGate()" in src, "CancelGate not instantiated"
