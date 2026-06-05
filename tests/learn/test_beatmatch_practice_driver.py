# SPDX-License-Identifier: Apache-2.0
"""Learn-owned beatmatch practice driver tests."""

from __future__ import annotations

import numpy as np

from vibemix.learn.beatmatch_practice_driver import BeatmatchPracticeDriver
from vibemix.learn.practice_loop import grade_owned_beatmatch_state


def _grade(driver: BeatmatchPracticeDriver):
    snapshot = driver.snapshot()
    assert snapshot is not None
    return grade_owned_beatmatch_state(
        snapshot.grid_a,
        snapshot.grid_b,
        snapshot.deck_state,
    )


def test_driver_is_honest_null_until_a_beatmatch_lesson_action() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.snapshot() is None
    assert driver.record_action("L1.03", {"control": "tempo", "deck": "B", "value": 64}) is False
    assert driver.snapshot() is None


def test_ear_practice_centered_pitch_fader_produces_locked_owned_deck_state() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.record_action("L2.01", {"control": "tempo", "deck": "B", "value": 64}) is True
    grade = _grade(driver)

    assert grade.verdict == "locked"
    assert grade.tempo_matched is True
    assert grade.phase_locked is True


def test_driver_exposes_the_same_minideck_that_snapshots_grade() -> None:
    driver = BeatmatchPracticeDriver()
    assert driver.record_action("L2.01", {"control": "tempo", "deck": "B", "value": 64}) is True

    before = driver.snapshot()
    assert before is not None
    assert before.deck_state.a_frame == 0.0

    driver.deck.render_block(128)

    after = driver.snapshot()
    assert after is not None
    assert after.deck_state.a_frame == 128.0
    assert after.deck_state.b_frame == 128.0


def test_driver_practice_deck_renders_audible_audio() -> None:
    driver = BeatmatchPracticeDriver()

    out = driver.deck.render_block(512)

    assert out.shape == (512, 2)
    assert out.dtype == np.float32
    assert float(np.sqrt(np.mean(np.square(out)))) > 0.01


def test_driver_waveform_payload_uses_bundled_demo_sections() -> None:
    driver = BeatmatchPracticeDriver()

    payload = driver.waveform_payload()

    assert payload["sample_rate"] == 44_100
    assert sorted(payload["decks"]) == ["A", "B"]
    for deck in payload["decks"].values():
        assert deck["duration_s"] >= 29.0
        assert len(deck["peaks"]) > 100
        assert max(max(peak) for peak in deck["peaks"]) > 0
        assert {cue["label"] for cue in deck["cues"]} == {
            "intro",
            "drop",
            "breakdown",
            "outro",
        }


def test_eq_swap_action_filters_audio_without_arming_beatmatch_grade() -> None:
    neutral = BeatmatchPracticeDriver()
    cut = BeatmatchPracticeDriver()
    neutral.deck.xfader = 0.0
    cut.deck.xfader = 0.0

    assert cut.record_action("L2.04", {"control": "eq_low", "deck": "A", "value": 0}) is False
    assert cut.snapshot() is None
    neutral.deck.render_block(1024)
    cut.deck.render_block(1024)  # coefficient-change crossfade block

    neutral_out = neutral.deck.render_block(1024)
    cut_out = cut.deck.render_block(1024)

    neutral_rms = float(np.sqrt(np.mean(np.square(neutral_out[:, 0]))))
    cut_rms = float(np.sqrt(np.mean(np.square(cut_out[:, 0]))))
    assert cut_rms < neutral_rms * 0.75


def test_mixer_actions_route_to_owned_deck_without_arming_grade() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.record_action("L1.04", {"control": "xfader", "value": 0}) is False
    assert driver.record_action("L1.03", {"control": "vol", "deck": "A", "value": 0}) is False
    assert driver.record_action("L2.06", {"control": "filter", "deck": "B", "value": 127}) is False

    state = driver.deck.state()
    assert state.xfader == 0.0
    assert state.vol_a == 0.0
    assert state.vol_b == 1.0
    assert driver.snapshot() is None


def test_sandbox_actions_move_owned_deck_without_arming_grade() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.record_action(None, {"control": "tempo", "deck": "B", "value": 64}) is False
    tempo_state = driver.deck.state()
    assert tempo_state.rate_b == 1.0

    assert (
        driver.record_action(
            None,
            {"type": "button", "control": "sync", "deck": "B", "direction": "down"},
        )
        is False
    )
    assert driver.snapshot() is None

    before = driver.deck.state().b_frame
    assert (
        driver.record_action(
            None,
            {
                "type": "cc",
                "control": "jog",
                "deck": "B",
                "value": 127,
                "prev_value": 64,
                "direction": "down",
            },
        )
        is False
    )
    assert driver.deck.state().b_frame > before
    assert driver.snapshot() is None


def test_ear_practice_large_pitch_move_does_not_credit_as_locked() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.record_action("L2.01", {"control": "tempo", "deck": "B", "value": 100}) is True
    grade = _grade(driver)

    assert grade.verdict == "tempo_off"
    assert grade.tempo_matched is False


def test_sync_practice_snaps_owned_deck_to_locked_state() -> None:
    driver = BeatmatchPracticeDriver()

    assert (
        driver.record_action(
            "L2.02",
            {"type": "button", "control": "sync", "deck": "B", "direction": "down"},
        )
        is True
    )
    grade = _grade(driver)

    assert grade.verdict == "locked"
    assert grade.tempo_matched is True
    assert grade.phase_locked is True


def test_recovery_drills_arm_real_owned_deck_misses() -> None:
    driver = BeatmatchPracticeDriver()

    assert (
        driver.record_action(
            "L3.05",
            {"control": "recovery_drill", "deck": "B", "drill": "key_clash"},
        )
        is True
    )
    key_clash = _grade(driver)

    assert key_clash.verdict == "tempo_off"
    assert key_clash.tempo_matched is False

    assert (
        driver.record_action(
            "L3.05",
            {"control": "recovery_drill", "deck": "B", "drill": "misaligned_phrase"},
        )
        is True
    )
    phrase_miss = _grade(driver)

    assert phrase_miss.verdict == "trainwreck"
    assert phrase_miss.tempo_matched is True
    assert phrase_miss.phase_locked is False
