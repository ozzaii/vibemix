# SPDX-License-Identifier: Apache-2.0
"""Wreck Room round director + runtime wiring tests.

The wreck lane is the Learn front door's playable loop. These tests pin the
round FSM (groove → break → hunt → hold → groove), the honesty contract
(sandbox = feedback only, zero evidence writes), and the ack-wire entry
(``control_id: wreck_round`` riding the existing ``ipc.learn.ack``).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import MagicMock

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState
from vibemix.learn.beatmatch_judge import BeatmatchGrade, grade_beatmatch
from vibemix.learn.beatmatch_practice_driver import BeatmatchPracticeDriver
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import BeatmatchPracticeSnapshot, LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.learn.wreck_round import WreckRound

_BEAT_S = 60.0 / 128.0


def _grade(verdict: str = "locked", phase: float = 0.0) -> BeatmatchGrade:
    return BeatmatchGrade(
        abstain=verdict == "abstain",
        tempo_error=0.05 if verdict == "tempo_off" else 0.0,
        phase_error_beats=phase,
        tempo_matched=verdict != "tempo_off",
        phase_locked=verdict == "locked",
        recoverable_late=False,
        verdict=verdict,
        score=1.0 if verdict == "locked" else 0.2,
    )


class _FakeDriver:
    def __init__(self) -> None:
        self.wrecks: list[tuple[str, int]] = []
        self.locks = 0
        self.yanks = 0
        self.restores = 0

    def wreck(self, kind: str, level: int) -> None:
        self.wrecks.append((kind, level))

    def lock_b(self) -> None:
        self.locks += 1

    def yank_b(self) -> None:
        self.yanks += 1

    def restore_b(self) -> None:
        self.restores += 1

    def waveform_payload(self) -> dict:
        return {"sample_rate": 44_100, "beat_interval_s": _BEAT_S, "decks": {}}


def _round(tmp_path: Path, driver: _FakeDriver | None = None) -> tuple[WreckRound, _FakeDriver]:
    fake = driver if driver is not None else _FakeDriver()
    wr = WreckRound(
        lambda: fake,
        rng=random.Random(7),
        ledger_path=tmp_path / "rounds.jsonl",
    )
    return wr, fake


def _drive_to_hunt(wr: WreckRound, fake: _FakeDriver) -> None:
    """start() then tick past the groove deadline so the break fires."""

    assert wr.start() is not None
    tick = wr.tick(_grade("locked"), 0.0)  # stamps the groove deadline
    assert tick.fields["save_attempt_active"] is False
    tick = wr.tick(_grade("locked"), 60.0)  # way past any groove window
    assert fake.wrecks, "the break should shove deck B"
    assert tick.fields["save_attempt_active"] is True


# ---- director FSM -----------------------------------------------------------


def test_start_locks_decks_and_barks(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    bark = wr.start()
    assert wr.active
    assert fake.locks == 1 and fake.restores == 1
    assert bark is not None and bark.text


def test_groove_break_opens_save_window_with_bark(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    assert wr.start() is not None
    wr.tick(_grade("locked"), 0.0)
    tick = wr.tick(_grade("locked"), 60.0)
    assert fake.wrecks == [("tempo", 1)]  # difficulty 1 = audible tempo shove
    assert tick.barks and tick.barks[0].text
    assert tick.fields["save_floor_seconds_total"] == 14.0
    assert tick.fields["save_floor_seconds_remaining"] == 14.0


def test_lock_inside_window_lands_save_edge(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    _drive_to_hunt(wr, fake)
    wr.tick(_grade("tempo_off", phase=0.3), 61.0)
    tick = wr.tick(_grade("locked"), 63.0)
    assert tick.fields["save_landed"] is True
    assert tick.fields["save_streak"] == 1
    assert tick.fields["save_from_verdict"] == "tempo_off"
    assert tick.barks and "pocket" in tick.barks[0].text or tick.barks[0].text


def test_held_lock_escalates_difficulty(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    _drive_to_hunt(wr, fake)
    wr.tick(_grade("locked"), 62.0)  # landed -> hold
    tick = wr.tick(_grade("locked"), 62.0 + 16.0 * _BEAT_S + 0.1)
    assert tick.fields["save_difficulty_level"] == 2
    assert tick.barks
    rows = [
        json.loads(line)
        for line in (tmp_path / "rounds.jsonl").read_text().splitlines()
    ]
    assert rows[-1]["landed"] is True and rows[-1]["held"] is True


def test_slipped_hold_keeps_difficulty(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    _drive_to_hunt(wr, fake)
    wr.tick(_grade("locked"), 62.0)  # landed -> hold
    tick = wr.tick(_grade("drifting", phase=0.05), 63.0)
    assert tick.fields["save_difficulty_level"] == 1
    assert tick.barks
    rows = [
        json.loads(line)
        for line in (tmp_path / "rounds.jsonl").read_text().splitlines()
    ]
    assert rows[-1]["landed"] is True and rows[-1]["held"] is False


def test_expired_window_yanks_resets_streak_then_regrooves(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    _drive_to_hunt(wr, fake)
    tick = wr.tick(_grade("drifting", phase=0.1), 60.0 + 15.0)
    assert tick.fields["save_floor_expired"] is True
    assert tick.fields["save_streak"] == 0
    assert fake.yanks == 1
    assert tick.barks
    # the verdict rest passes, deck B comes back, groove resumes
    tick = wr.tick(_grade("abstain"), 60.0 + 18.0)
    assert fake.restores == 2  # start() + the post-miss restore
    assert fake.locks == 2
    assert tick.barks


def test_abstain_freezes_the_round(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    _drive_to_hunt(wr, fake)
    tick = wr.tick(_grade("abstain"), 1000.0)
    assert tick.fields["save_floor_expired"] is False
    assert fake.yanks == 0


def test_stop_returns_to_idle(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    assert wr.start() is not None
    wr.stop()
    assert not wr.active
    tick = wr.tick(_grade("locked"), 5.0)
    assert tick.fields["save_attempt_active"] is False
    assert tick.barks == ()


def test_landed_bark_compares_to_ledger_history(tmp_path: Path) -> None:
    ledger = tmp_path / "rounds.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "ts": "2026-06-11T00:00:00+00:00",
                "difficulty": 1,
                "kind": "tempo",
                "landed": True,
                "held": True,
                "time_to_lock_s": 100.0,
                "window_s": 14.0,
            }
        )
        + "\n"
    )
    wr, fake = _round(tmp_path)
    _drive_to_hunt(wr, fake)
    tick = wr.tick(_grade("locked"), 62.0)
    assert tick.barks
    assert "last save took" in tick.barks[0].text


def test_anti_repeat_picker_never_repeats_consecutively(tmp_path: Path) -> None:
    wr, fake = _round(tmp_path)
    picks: list[str] = []
    for _ in range(9):
        bark = wr.start()  # every restart re-picks the groove_open slot
        assert bark is not None
        picks.append(bark.text)
    assert all(a != b for a, b in zip(picks, picks[1:]))


def test_no_copy_slop_in_bark_bank() -> None:
    import vibemix.learn.wreck_round as wreck_round_module

    banks = [
        getattr(wreck_round_module, name)
        for name in dir(wreck_round_module)
        if name.startswith("_BARKS_") or name.startswith("_BARK_")
    ]
    texts: list[str] = []
    for bank in banks:
        if isinstance(bank, str):
            texts.append(bank)
        else:
            texts.extend(bank)
    texts.append(wreck_round_module.BARK_BOOTH_BUSY)
    texts.append(wreck_round_module.BARK_NO_DECK)
    for text in texts:
        assert "—" not in text and "--" not in text, f"em dash in bark: {text!r}"


# ---- the real driver's wreck-lane methods -----------------------------------


def test_driver_lock_b_produces_locked_grade() -> None:
    driver = BeatmatchPracticeDriver()
    driver.lock_b()
    grade = grade_beatmatch(driver._grid_a, driver._grid_b, driver.deck.state())
    assert grade.verdict == "locked"
    assert driver.sandbox_snapshot() is not None
    assert driver.snapshot() is None  # never arms the graded lesson lane


def test_driver_tempo_wreck_breaks_the_lock() -> None:
    driver = BeatmatchPracticeDriver()
    driver.lock_b()
    driver.wreck("tempo", 3)
    grade = grade_beatmatch(driver._grid_a, driver._grid_b, driver.deck.state())
    assert grade.verdict == "tempo_off"
    assert driver.snapshot() is None


def test_driver_phase_wreck_breaks_the_lock() -> None:
    driver = BeatmatchPracticeDriver()
    driver.lock_b()
    driver.wreck("phase", 2)
    grade = grade_beatmatch(driver._grid_a, driver._grid_b, driver.deck.state())
    assert grade.verdict in {"drifting", "trainwreck"}


def test_driver_yank_and_restore_move_channel_fader() -> None:
    driver = BeatmatchPracticeDriver()
    driver.yank_b()
    assert driver.deck.state().vol_b == 0.0
    driver.restore_b()
    assert driver.deck.state().vol_b == 1.0


# ---- runtime wiring ----------------------------------------------------------


class _FakePlayer:
    def __init__(self, *, playable: bool = True) -> None:
        self.playable = playable
        self.starts = 0
        self.stops = 0

    def can_play(self) -> bool:
        return self.playable

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> None:
        self.stops += 1


def _locked_snapshot() -> BeatmatchPracticeSnapshot:
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=44_100)
    return BeatmatchPracticeSnapshot(
        grid_a=grid,
        grid_b=grid,
        deck_state=DeckState(
            a_frame=0.0, b_frame=0.0, rate_a=1.0, rate_b=1.0, xfader=0.5
        ),
    )


def _snap(rate_b: float = 1.0, phase_beats: float = 0.0) -> BeatmatchPracticeSnapshot:
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=44_100)
    frames_per_beat = 44_100 * 60.0 / 128.0
    return BeatmatchPracticeSnapshot(
        grid_a=grid,
        grid_b=grid,
        deck_state=DeckState(
            a_frame=0.0,
            b_frame=phase_beats * frames_per_beat,
            rate_a=1.0,
            rate_b=rate_b,
            xfader=0.5,
        ),
    )


def _runtime_with_round(
    tmp_path: Path,
    *,
    clock: list[float],
    playable: bool = True,
    loader: Callable[[], BeatmatchPracticeSnapshot] | None = None,
) -> tuple[LessonRuntime, MagicMock, _FakePlayer, WreckRound, _FakeDriver]:
    ipc = MagicMock(name="ipc_router")
    registry = MagicMock(name="evidence_registry")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: clock[0],
        beatmatch_practice_sandbox_loader=(
            loader if loader is not None else _locked_snapshot
        ),
        waveform_payload_loader=lambda: {
            "sample_rate": 44_100,
            "beat_interval_s": _BEAT_S,
            "decks": {},
        },
    )
    player = _FakePlayer(playable=playable)
    runtime.set_beatmatch_practice_player(player)
    fake_driver = _FakeDriver()
    wreck = WreckRound(
        lambda: fake_driver,
        rng=random.Random(7),
        ledger_path=tmp_path / "rounds.jsonl",
    )
    runtime.set_wreck_round(wreck)
    return runtime, ipc, player, wreck, fake_driver


def _payloads(ipc: MagicMock, message_type: str) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == message_type
    ]


def _wreck_ack(control: str = "wreck_round") -> dict:
    return {
        "type": "button",
        "control": control,
        "deck": "",
        "direction": "down",
        "value": 127,
        "prev_value": 0,
        "source": "click",
    }


def test_wreck_round_ack_starts_player_and_round(tmp_path: Path) -> None:
    clock = [0.0]
    runtime, ipc, player, wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    assert runtime.handle_wreck_round_ack(_wreck_ack()) is True
    assert player.starts == 1
    assert wreck.active
    speaks = _payloads(ipc, "ipc.learn.tutor_speak")
    assert speaks and speaks[-1]["citations"] == []


def test_wreck_round_ack_ignores_other_controls(tmp_path: Path) -> None:
    clock = [0.0]
    runtime, _ipc, _player, _wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    assert runtime.handle_wreck_round_ack(_wreck_ack(control="tempo")) is False


def test_wreck_round_ack_consumed_during_lesson(tmp_path: Path) -> None:
    clock = [0.0]
    runtime, _ipc, player, wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    assert runtime.handle_wreck_round_ack(_wreck_ack()) is True
    assert player.starts == 0
    assert not wreck.active


def test_booth_revives_after_a_completed_lesson(tmp_path: Path) -> None:
    """``current_lesson_id`` stays set in ``completed`` (the relaunch flow
    reads it), so the booth/sandbox lane must gate on a RUNNING lesson —
    otherwise the first completed lesson of a session permanently kills the
    Learn front door with no voice and a false device diagnosis."""

    clock = [0.0]
    runtime, ipc, player, wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("observer_complete")
    assert runtime.current_state.id == "completed"
    assert runtime.handle_wreck_round_ack(_wreck_ack()) is True
    assert wreck.active, "the booth must revive once the lesson is over"
    assert player.starts >= 1
    # the sandbox grade loop revives with it (live_grade flows again)
    runtime._emit_live_beatmatch_grade_tick()
    assert _payloads(ipc, "ipc.learn.live_grade")


def test_wreck_round_ack_voices_busy_when_set_is_live(tmp_path: Path) -> None:
    clock = [0.0]
    runtime, ipc, player, wreck, _ = _runtime_with_round(
        tmp_path, clock=clock, playable=False
    )
    assert runtime.handle_wreck_round_ack(_wreck_ack()) is True
    assert player.starts == 0
    assert not wreck.active
    speaks = _payloads(ipc, "ipc.learn.tutor_speak")
    assert speaks and "booth waits" in speaks[-1]["text"]


def test_wreck_stop_ack_stops_round_and_player(tmp_path: Path) -> None:
    clock = [0.0]
    runtime, _ipc, player, wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    runtime.handle_wreck_round_ack(_wreck_ack())
    assert runtime.handle_wreck_round_ack(_wreck_ack(control="wreck_stop")) is True
    assert not wreck.active
    assert player.stops >= 1


def test_sandbox_tick_carries_round_save_fields_and_writes_no_evidence(
    tmp_path: Path,
) -> None:
    clock = [0.0]
    runtime, ipc, _player, _wreck, fake_driver = _runtime_with_round(
        tmp_path, clock=clock
    )
    runtime.handle_wreck_round_ack(_wreck_ack())
    registry = runtime._evidence_registry
    # tick 1 stamps the groove deadline; jump the clock past it for the break
    runtime._emit_live_beatmatch_grade_tick()
    clock[0] = 60.0
    runtime._emit_live_beatmatch_grade_tick()
    assert fake_driver.wrecks, "the round should have shoved deck B"
    grades = _payloads(ipc, "ipc.learn.live_grade")
    assert grades and grades[-1]["save_attempt_active"] is True
    assert grades[-1]["save_floor_seconds_total"] == 14.0
    assert not registry.write.called, "wreck lane must never write evidence"


def _generic_grade_speaks(ipc: MagicMock) -> list[dict]:
    return [
        s
        for s in _payloads(ipc, "ipc.learn.tutor_speak")
        if s["tts_marker"].endswith(".grade")
    ]


def test_wreck_barks_swallow_their_own_generic_grade_edge(tmp_path: Path) -> None:
    """One moment, one voice: the verdict edge a bark announces stays silent.

    The shove lands in the measured grade one tick AFTER the break bark, so the
    suppression has to survive to the next generic edge, then expire (one-shot,
    never a blanket mute on hunt coaching).
    """

    clock = [0.0]
    holder = {"snap": _snap()}
    runtime, ipc, _player, _wreck, _ = _runtime_with_round(
        tmp_path, clock=clock, loader=lambda: holder["snap"]
    )
    runtime.handle_wreck_round_ack(_wreck_ack())  # groove_open bark
    runtime._emit_live_beatmatch_grade_tick()  # locked edge right after the bark
    clock[0] = 60.0
    runtime._emit_live_beatmatch_grade_tick()  # break tick: bark, grade still pre-shove
    holder["snap"] = _snap(rate_b=1.08)  # the shove lands in the measured grade
    clock[0] = 60.2
    runtime._emit_live_beatmatch_grade_tick()  # tempo_off edge = the bark's own moment
    assert not _generic_grade_speaks(ipc), (
        "generic grade line double-voiced a bark's own verdict edge"
    )
    # one-shot, not a mute: the learner's next measured move still gets coaching
    holder["snap"] = _snap(phase_beats=0.1)
    clock[0] = 60.4
    runtime._emit_live_beatmatch_grade_tick()  # drifting edge, no bark on this tick
    assert len(_generic_grade_speaks(ipc)) == 1


def test_held_bark_at_difficulty_cap_promises_no_escalation(tmp_path: Path) -> None:
    """At the cap the window cannot shrink; the bark must not claim it will."""

    wr, fake = _round(tmp_path)
    wr._difficulty = 5
    _drive_to_hunt(wr, fake)
    wr.tick(_grade("locked"), 62.0)  # landed -> hold
    tick = wr.tick(_grade("locked"), 62.0 + 16.0 * _BEAT_S + 0.1)
    assert tick.fields["save_difficulty_level"] == 5
    assert tick.barks
    text = tick.barks[0].text
    for promise in ("shorter", "sooner", "pushing harder"):
        assert promise not in text, f"hollow escalation promise at the cap: {text!r}"


def test_wreck_round_ack_voices_no_deck_when_player_cannot_start(
    tmp_path: Path,
) -> None:
    """A press that cannot raise a deck gets an honest line, never silence."""

    clock = [0.0]
    runtime, ipc, _player, wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    runtime.set_beatmatch_practice_player(None)
    runtime._prepare_beatmatch_practice_audio = lambda: None  # type: ignore[method-assign]
    assert runtime.handle_wreck_round_ack(_wreck_ack()) is True
    assert not wreck.active
    speaks = _payloads(ipc, "ipc.learn.tutor_speak")
    assert speaks and speaks[-1]["tts_marker"] == "wreck_round.no_deck"
    assert "output" in speaks[-1]["text"]


def test_sandbox_locked_copy_never_promises_proof(tmp_path: Path) -> None:
    """Sandbox has no credit lane; 'until proof lands' would be a lie there."""

    clock = [0.0]
    runtime, _ipc, _player, _wreck, _ = _runtime_with_round(tmp_path, clock=clock)
    result: Any = SimpleNamespace(grade=_grade("locked"), event=None)
    text = runtime._beatmatch_grade_text(result)
    assert text is not None and "proof" not in text
    # the lesson lane CAN land proof, so its promise stays
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    lesson_text = runtime._beatmatch_grade_text(result)
    assert lesson_text is not None and "until proof lands" in lesson_text
