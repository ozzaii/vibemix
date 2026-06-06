# SPDX-License-Identifier: Apache-2.0
"""Regression pins for Learn observer boot wiring.

The EQ exemplar and recital classes are useful only if the live app registers
them with ``LessonRuntime``. These tests intentionally inspect the startup
source because ``vibemix.__main__.main`` owns a large hardware/audio boot graph
that is not practical to instantiate in a unit test.
"""

from __future__ import annotations

from pathlib import Path

MAIN_PATH = Path("src/vibemix/__main__.py")


def _main_source() -> str:
    return MAIN_PATH.read_text()


def test_learn_special_lesson_observers_are_registered_in_main() -> None:
    src = _main_source()

    assert "from vibemix.learn.exemplar_lesson import ExemplarLessonController" in src
    assert "from vibemix.learn.recital import RecitalRuntime" in src
    assert 'lesson_runtime.register_lesson_observer(\n            "L1.14"' in src
    assert 'lesson_runtime.register_lesson_observer(\n            "L1.16"' in src
    assert 'lesson_runtime.register_lesson_observer(\n            "L2.14"' in src
    assert "ExemplarFinder(registry=evidence_registry)" in src


def test_observer_complete_envelopes_return_to_lesson_runtime() -> None:
    src = _main_source()

    assert "def _learn_observer_emit(msg: dict) -> None:" in src
    assert 'msg.get("type") != "ipc.learn.complete_lesson"' in src
    assert "lesson_runtime.complete_observer_lesson(" in src
    assert 'completed=reason == "completed"' in src


def test_observer_tutor_speak_is_logged_as_ai_message() -> None:
    src = _main_source()

    assert "learn_tutor_speak_observability_events" in src
    assert 'msg.get("type") == "ipc.learn.tutor_speak"' in src
    assert 'source="learn_observer"' in src
    assert "_learn_session_event(kind, fields)" in src


def test_exemplar_observer_has_safe_noop_player_fallback() -> None:
    src = _main_source()

    assert "class _NoopLearnExemplarPlayer:" in src
    assert "read_learn_headphone_device_index" in src
    assert "from vibemix.learn.audio_cue import ExemplarPlayer" in src
    assert "exemplar_player = ExemplarPlayer(" in src


def test_beatmatch_practice_audio_uses_shared_learn_output_device() -> None:
    src = _main_source()

    assert "learn headphone device" in src
    assert "max_output_channels" in src
    assert "from vibemix.learn.two_deck_player import TwoDeckPlayer" in src
    assert "beatmatch_practice_player = TwoDeckPlayer(" in src
    assert "beatmatch_practice_driver.deck" in src
    assert "def _prepare_learn_save_mode_sources()" in src
    assert "def _set_learn_save_mode_source_reason(reason: str | None) -> None:" in src
    assert "set_source_reason" in src
    assert "load_save_mode_sources(lib, store)" in src
    assert "beatmatch_practice_prepare=_prepare_learn_save_mode_sources" in src
    assert "beatmatch_practice_difficulty_setter=_beatmatch_practice_set_difficulty" in src
    assert "beatmatch_practice_sandbox_loader=_beatmatch_practice_sandbox_snapshot" in src
    assert "lesson_runtime.set_beatmatch_practice_player(beatmatch_practice_player)" in src
    assert "lesson_runtime.set_beatmatch_practice_player(None)" in src


def test_lesson_runtime_uses_shared_evidence_registry_in_main() -> None:
    src = _main_source()

    assert "lesson_runtime = LessonRuntime(" in src
    assert "evidence_registry=evidence_registry" in src
    assert "evidence_clock=lambda: state.set_seconds" in src


def test_lesson_runtime_uses_latest_prepared_pool_loader_in_main() -> None:
    src = _main_source()

    assert "load_latest_prepared_pool as _load_latest_prepared_pool" in src
    assert "prepared_pool_loader=_load_latest_prepared_pool" in src


def test_lesson_runtime_uses_library_harmonic_pair_loader_in_main() -> None:
    src = _main_source()

    assert "def _load_learn_harmonic_pair()" in src
    assert "pick_harmonic_practice_pair(lib)" in src
    assert "harmonic_pair_loader=_load_learn_harmonic_pair" in src


def test_lesson_runtime_uses_graduation_summary_loader_in_main() -> None:
    src = _main_source()

    assert "from vibemix.learn.graduation import build_graduation_summary" in src
    assert "graduation_summary_loader=build_graduation_summary" in src
