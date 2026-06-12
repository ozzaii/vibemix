# SPDX-License-Identifier: Apache-2.0
"""Learn tutor speech audio callback wiring."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from vibemix.__main__ import _build_learn_tutor_speak_audio
from vibemix.learn.bark_cache import BarkPcmCache
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState


def _runtime(
    callback=None,
) -> tuple[LessonRuntime, MagicMock]:
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(
            current_lesson_id="L2.01",
            current_course_id="course_2_transitions",
            current_controller_id="pioneer_ddj_flx4",
        ),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        tutor_speak_audio=callback,
    )
    return runtime, ipc


def test_tutor_beat_calls_audio_callback_once_with_text_and_marker() -> None:
    calls: list[tuple[str, str]] = []
    runtime, ipc = _runtime(lambda text, marker: calls.append((text, marker)))

    runtime._emit_tutor_beat(0)

    assert len(calls) == 1
    text, marker = calls[0]
    assert text.startswith("sync stays off")
    assert marker == "L201.beat0"
    payload = ipc.emit.call_args.args[0]["payload"]
    assert payload["text"] == text
    assert payload["tts_marker"] == marker


def test_missing_tutor_audio_callback_keeps_subtitle_emit_safe() -> None:
    runtime, ipc = _runtime(None)

    runtime._emit_tutor_beat(0)

    payload = ipc.emit.call_args.args[0]["payload"]
    assert payload["tts_marker"] == "L201.beat0"


class _FakePlayback:
    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    def push(self, pcm: bytes) -> None:
        self.chunks.append(pcm)


class _FakeTutorTTS:
    sample_rate = 24_000

    def synthesize_pcm(self, text: str, on_pcm) -> None:
        assert text
        on_pcm(b"\x01\x00" * 32)


class _FailingTutorTTS:
    sample_rate = 24_000

    def synthesize_pcm(self, _text: str, _on_pcm) -> None:
        raise RuntimeError("voice offline")


def _wait_for(done: threading.Event) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if done.wait(0.01):
            return
    raise AssertionError("timed out waiting for Learn tutor voice thread")


def test_learn_tutor_voice_logs_queue_and_completion() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    done = threading.Event()

    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        if kind == "learn_tutor_voice_complete":
            done.set()

    speak = _build_learn_tutor_speak_audio(
        voice_tts=_FakeTutorTTS(),
        playback=playback,
        muted=lambda: False,
        event_logger=log,
    )

    speak("sync stays off for this drill.", "L201.beat0")
    _wait_for(done)

    assert [kind for kind, _fields in events] == [
        "learn_tutor_voice_queued",
        "learn_tutor_voice_complete",
    ]
    assert events[0][1] == {"tts_marker": "L201.beat0", "chars": 30}
    assert events[1][1] == {"tts_marker": "L201.beat0", "bytes": 64}
    assert playback.chunks == [b"\x01\x00" * 32]


def test_learn_tutor_voice_loads_provider_lazily() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    done = threading.Event()
    provider_calls = 0

    def provider() -> _FakeTutorTTS:
        nonlocal provider_calls
        provider_calls += 1
        return _FakeTutorTTS()

    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        if kind == "learn_tutor_voice_complete":
            done.set()

    speak = _build_learn_tutor_speak_audio(
        voice_tts_provider=provider,
        playback=playback,
        muted=lambda: False,
        event_logger=log,
    )

    speak("line", "sandbox.grade")
    _wait_for(done)

    assert provider_calls == 1
    assert [kind for kind, _fields in events] == [
        "learn_tutor_voice_queued",
        "learn_tutor_voice_complete",
    ]
    assert playback.chunks == [b"\x01\x00" * 32]


def test_learn_tutor_voice_logs_unavailable_provider_skip() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    done = threading.Event()

    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        if kind == "learn_tutor_voice_skipped":
            done.set()

    speak = _build_learn_tutor_speak_audio(
        voice_tts_provider=lambda: None,
        playback=playback,
        muted=lambda: False,
        event_logger=log,
    )

    speak("line", "sandbox.grade")
    _wait_for(done)

    assert events == [
        ("learn_tutor_voice_queued", {"tts_marker": "sandbox.grade", "chars": 4}),
        (
            "learn_tutor_voice_skipped",
            {"reason": "unavailable", "tts_marker": "sandbox.grade"},
        ),
    ]
    assert playback.chunks == []


def test_learn_tutor_voice_logs_muted_skip_without_thread() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    speak = _build_learn_tutor_speak_audio(
        voice_tts=_FakeTutorTTS(),
        playback=playback,
        muted=lambda: True,
        event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    speak("line", "L201.beat0")

    assert events == [
        (
            "learn_tutor_voice_skipped",
            {"reason": "muted", "tts_marker": "L201.beat0"},
        )
    ]
    assert playback.chunks == []


class _CountingTutorTTS:
    sample_rate = 24_000

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._lock = threading.Lock()

    def synthesize_pcm(self, text: str, on_pcm) -> None:
        with self._lock:
            self.calls.append(text)
        on_pcm(b"\x01\x00" * 16)


def _logger(events: list[tuple[str, dict]], signal: dict[str, threading.Event]):
    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        ev = signal.get(kind)
        if ev is not None:
            ev.set()

    return log


def test_first_wreck_marker_warms_the_fixed_bark_bank() -> None:
    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    cache = BarkPcmCache()
    events: list[tuple[str, dict]] = []
    warm_done = threading.Event()
    warm_texts = ("bark one ready.", "bark two ready.")
    speak = _build_learn_tutor_speak_audio(
        voice_tts=tts,
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(events, {"learn_tutor_bark_warm_done": warm_done}),
        bark_cache=cache,
        bark_warm_texts=lambda: warm_texts,
    )

    speak("there it goes. B is running hot. reel it in.", "wreck_round.break.1")
    _wait_for(warm_done)

    for text in warm_texts:
        assert cache.get(text) is not None, f"warm text not cached: {text!r}"
        assert tts.calls.count(text) == 1
    done = [fields for kind, fields in events if kind == "learn_tutor_bark_warm_done"]
    assert done == [{"cached": 2, "bytes": done[0]["bytes"], "errors": 0}]
    assert done[0]["bytes"] > 0


def test_warm_is_one_shot_across_wreck_barks() -> None:
    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    cache = BarkPcmCache()
    events: list[tuple[str, dict]] = []
    warm_done = threading.Event()
    speak = _build_learn_tutor_speak_audio(
        voice_tts=tts,
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(events, {"learn_tutor_bark_warm_done": warm_done}),
        bark_cache=cache,
        bark_warm_texts=lambda: ("bark one ready.",),
    )

    speak("bark one ready.", "wreck_round.groove_open.1")
    _wait_for(warm_done)
    speak("bark one ready.", "wreck_round.groove_back.2")

    started = [kind for kind, _f in events if kind == "learn_tutor_bark_warm_started"]
    assert started == ["learn_tutor_bark_warm_started"]


def test_cached_bark_pushes_synchronously_without_a_synth_job() -> None:
    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    cache = BarkPcmCache()
    cache.put("I pulled it. that was a trainwreck.", b"\x05\x06" * 8, pinned=True)
    events: list[tuple[str, dict]] = []
    speak = _build_learn_tutor_speak_audio(
        voice_tts=tts,
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(events, {}),
        bark_cache=cache,
        bark_warm_texts=lambda: (),
    )

    speak("I pulled it. that was a trainwreck.", "wreck_round.missed.3")

    # No thread, no synth: the cached PCM is already on the queue when we return.
    assert playback.chunks == [b"\x05\x06" * 8]
    assert tts.calls == []
    hits = [(kind, f) for kind, f in events if kind == "learn_tutor_voice_cache_hit"]
    assert hits == [
        ("learn_tutor_voice_cache_hit", {"tts_marker": "wreck_round.missed.3", "bytes": 16})
    ]


def test_warm_retries_after_engine_unavailable() -> None:
    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    engine: dict[str, _CountingTutorTTS | None] = {"tts": None}
    cache = BarkPcmCache()
    events: list[tuple[str, dict]] = []
    warm_skipped = threading.Event()
    warm_done = threading.Event()
    speak = _build_learn_tutor_speak_audio(
        voice_tts_provider=lambda: engine["tts"],
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(
            events,
            {
                "learn_tutor_bark_warm_skipped": warm_skipped,
                "learn_tutor_bark_warm_done": warm_done,
            },
        ),
        bark_cache=cache,
        bark_warm_texts=lambda: ("bark one ready.",),
    )

    speak("two decks, locked. enjoy it while it lasts.", "wreck_round.groove_open.1")
    _wait_for(warm_skipped)
    assert cache.get("bark one ready.") is None

    engine["tts"] = tts  # the voice comes up before the next round
    speak("back in. listen to the lock.", "wreck_round.groove_back.2")
    _wait_for(warm_done)
    assert cache.get("bark one ready.") is not None


def test_refusal_barks_never_trigger_the_warm() -> None:
    """busy fires DURING a live set: ~27 sequential MLX synths on the shared
    live voice engine would make Sven late mid-set — the exact line that
    promises the booth keeps its hands off the decks. Warm waits for a round
    that actually engaged."""

    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    cache = BarkPcmCache()
    events: list[tuple[str, dict]] = []
    complete = threading.Event()
    speak = _build_learn_tutor_speak_audio(
        voice_tts=tts,
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(events, {"learn_tutor_voice_complete": complete}),
        bark_cache=cache,
        bark_warm_texts=lambda: ("bark one ready.",),
    )

    speak(
        "your set has the decks. the booth waits until you're off the air.",
        "wreck_round.busy",
    )
    _wait_for(complete)
    complete.clear()
    speak(
        "no deck answered. check your output device, then press it again.",
        "wreck_round.no_deck",
    )
    _wait_for(complete)

    assert not any(kind == "learn_tutor_bark_warm_started" for kind, _f in events)
    assert "bark one ready." not in tts.calls


def test_repeated_live_line_is_served_from_cache_after_first_synth() -> None:
    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    cache = BarkPcmCache()
    events: list[tuple[str, dict]] = []
    complete = threading.Event()
    speak = _build_learn_tutor_speak_audio(
        voice_tts=tts,
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(events, {"learn_tutor_voice_complete": complete}),
        bark_cache=cache,
        bark_warm_texts=lambda: (),
    )

    speak("pocket is centered - hold it there.", "sandbox.grade")
    _wait_for(complete)
    speak("pocket is centered - hold it there.", "sandbox.grade")

    assert tts.calls == ["pocket is centered - hold it there."]
    assert len(playback.chunks) == 2
    assert any(kind == "learn_tutor_voice_cache_hit" for kind, _f in events)


def test_non_wreck_markers_never_trigger_the_bark_warm() -> None:
    playback = _FakePlayback()
    tts = _CountingTutorTTS()
    cache = BarkPcmCache()
    events: list[tuple[str, dict]] = []
    complete = threading.Event()
    speak = _build_learn_tutor_speak_audio(
        voice_tts=tts,
        playback=playback,
        muted=lambda: False,
        event_logger=_logger(events, {"learn_tutor_voice_complete": complete}),
        bark_cache=cache,
        bark_warm_texts=lambda: ("bark one ready.",),
    )

    speak("sync stays off for this drill.", "L201.beat0")
    _wait_for(complete)

    assert not any(kind == "learn_tutor_bark_warm_started" for kind, _f in events)
    assert "bark one ready." not in tts.calls


def test_learn_tutor_voice_logs_synthesis_error() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    done = threading.Event()

    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        if kind == "learn_tutor_voice_error":
            done.set()

    speak = _build_learn_tutor_speak_audio(
        voice_tts=_FailingTutorTTS(),
        playback=playback,
        muted=lambda: False,
        event_logger=log,
    )

    speak("line", "L201.beat0")
    _wait_for(done)

    assert [kind for kind, _fields in events] == [
        "learn_tutor_voice_queued",
        "learn_tutor_voice_error",
    ]
    assert events[1][1] == {"tts_marker": "L201.beat0", "error": "RuntimeError"}
    assert playback.chunks == []
