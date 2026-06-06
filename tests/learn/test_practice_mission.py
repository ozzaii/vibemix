# SPDX-License-Identifier: Apache-2.0
"""Next-practice mission is a derived booth hint, not stored progress."""

from __future__ import annotations

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.practice_mission import next_practice_mission
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST


def _make_skill_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        meta = CURRICULUM[lesson_id]
        progress.mark_completed(meta.course_id, lesson_id)
    setattr(progress, spec.gate, True)


def test_fresh_mission_starts_with_useful_controller_practice() -> None:
    mission = next_practice_mission(LearnProgress())

    assert mission["lesson_id"] == "L1.02"
    assert mission["mode"] == "start"
    assert mission["title"] == "meet your controller"
    assert "deck control" in mission["command"]
    assert mission["estimated_minutes"] >= 1
    assert mission["focus"] == "first_rep"
    assert mission["focus_label"] == "first rep"
    assert mission["challenge"] == "Touch the control before you read ahead."
    assert mission["meter_label"] == "first rep"
    assert mission["meter_value"] == 0
    assert mission["meter_max"] == 1
    assert mission["meter_state"] == "armed"
    assert mission["meter_caption"] == "touch the control to begin"
    assert [step["lesson_id"] for step in mission["chain"]] == ["L1.02", "L1.03", "L1.04"]
    assert mission["chain"][0]["state"] == "now"
    assert mission["chain"][0]["label"] == "first rep"
    assert mission["chain"][1]["state"] == "next"


def test_in_progress_mission_keeps_the_user_on_the_current_move() -> None:
    progress = LearnProgress()
    progress.mark_started("course_1_anatomy", "L1.03")
    progress.mark_hint_strike("course_1_anatomy", "L1.03", 2)
    progress.mark_practice_source("course_1_anatomy", "L1.03", "screen")

    mission = next_practice_mission(progress)

    assert mission["lesson_id"] == "L1.03"
    assert mission["mode"] == "finish"
    assert mission["focus"] == "retry"
    assert mission["focus_label"] == "retry 2/3"
    assert mission["command"] == "Retry channel strip; no hints, one clean move is the checkpoint."
    assert mission["challenge"] == "No hint this time; one clean move clears the loop."
    assert mission["proof"] == "screen deck has worked; repeat it cleanly"
    assert mission["meter_label"] == "retry loop"
    assert mission["meter_value"] == 2
    assert mission["meter_max"] == 3
    assert mission["meter_state"] == "retry"
    assert mission["meter_caption"] == "one clean move clears it"
    assert mission["chain"][0]["lesson_id"] == "L1.03"
    assert mission["chain"][0]["label"] == "retry 2/3"


def test_screen_free_practice_receipt_becomes_banked_finish_mission() -> None:
    progress = LearnProgress()
    progress.mark_practice_source("course_1_anatomy", "L1.03", "screen")

    mission = next_practice_mission(progress)

    assert mission["lesson_id"] == "L1.03"
    assert mission["mode"] == "finish"
    assert mission["focus_label"] == "practice bank 1/3"
    assert mission["proof"] == "screen deck has worked; repeat it cleanly"
    assert mission["challenge"] == "Repeat a banked move inside the lesson."
    assert mission["meter_label"] == "practice bank"
    assert mission["meter_value"] == 1
    assert mission["meter_max"] == 3
    assert mission["meter_state"] == "armed"
    assert mission["meter_caption"] == "1 screen rep banked"


def test_hardware_free_practice_receipt_becomes_controller_finish_mission() -> None:
    progress = LearnProgress()
    progress.mark_practice_source("course_1_anatomy", "L1.07", "midi")

    mission = next_practice_mission(progress)

    assert mission["lesson_id"] == "L1.07"
    assert mission["mode"] == "finish"
    assert mission["focus"] == "hardware"
    assert mission["focus_label"] == "practice bank 1/3"
    assert mission["proof"] == "last pass used hardware; repeat it on the controller"
    assert mission["challenge"] == "Repeat the controller move inside the lesson."
    assert mission["meter_label"] == "practice bank"
    assert mission["meter_value"] == 1
    assert mission["meter_max"] == 3
    assert mission["meter_caption"] == "1 controller rep banked"


def test_mixed_free_practice_receipts_build_a_three_rep_bank() -> None:
    progress = LearnProgress()
    progress.mark_practice_source("course_1_anatomy", "L1.03", "screen")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "screen")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "screen")

    mission = next_practice_mission(progress)

    assert mission["lesson_id"] == "L1.03"
    assert mission["focus_label"] == "practice bank 3/3"
    assert mission["meter_label"] == "practice bank"
    assert mission["meter_value"] == 3
    assert mission["meter_max"] == 3
    assert mission["meter_caption"] == "3 reps banked: screen + hardware"


def test_practice_chain_labels_later_banked_steps() -> None:
    progress = LearnProgress()
    progress.mark_practice_source("course_1_anatomy", "L1.03", "screen")
    progress.mark_practice_source("course_1_anatomy", "L1.04", "screen")
    progress.mark_practice_source("course_1_anatomy", "L1.04", "midi")

    mission = next_practice_mission(progress)

    assert [step["lesson_id"] for step in mission["chain"][:3]] == [
        "L1.03",
        "L1.04",
        "L1.05",
    ]
    assert mission["chain"][0]["label"] == "practice bank 1/3"
    assert mission["chain"][1]["label"] == "banked 2/3"
    assert mission["chain"][2]["label"] == "next rep"


def test_locked_next_course_replays_cleared_open_course() -> None:
    progress = LearnProgress()
    for lesson_id in [f"L1.{i:02d}" for i in range(1, 17)]:
        progress.mark_completed("course_1_anatomy", lesson_id)

    mission = next_practice_mission(progress)

    assert mission["lesson_id"] == "L1.01"
    assert mission["mode"] == "replay"
    assert "course 1" in mission["why"].lower() or "deck control" in mission["why"]


def test_cleared_competent_skill_turns_into_cited_proof_mission() -> None:
    progress = LearnProgress(course_2_unlocked=True, course_3_unlocked=True)
    for lesson_id, meta in CURRICULUM.items():
        if not lesson_id.startswith("L0."):
            progress.mark_completed(meta.course_id, lesson_id)
    progress.skills["deck_control"]["live_proof_count"] = 1

    mission = next_practice_mission(progress)

    assert mission["mode"] == "prove"
    assert mission["lesson_id"] == "L1.02"
    assert mission["focus"] == "proof"
    assert mission["focus_label"] == "proof 1/3"
    assert mission["proof"] == "1 cited proof banked; 2 left"
    assert mission["challenge"] == "Only cited live proof moves Mastery."
    assert mission["meter_label"] == "proof bank"
    assert mission["meter_value"] == 1
    assert mission["meter_max"] == 3
    assert mission["meter_state"] == "proof"
    assert mission["meter_caption"] == "2 proofs left to Mastery"


def test_zpd_frontier_proof_mission_beats_linear_empty_lesson() -> None:
    progress = LearnProgress(course_2_unlocked=True, course_3_unlocked=True)
    _make_skill_competent(progress, "deck_control")
    _make_skill_competent(progress, "beatmatching")
    _make_skill_competent(progress, "eq_mixing")

    mission = next_practice_mission(progress)

    assert mission["mode"] == "prove"
    assert mission["skill_id"] == "eq_mixing"
    assert mission["lesson_id"] == "L1.14"
    assert mission["focus"] == "proof"
    assert mission["challenge"] == "Only cited live proof moves Mastery."


def test_active_competent_lesson_becomes_the_current_proof_mission() -> None:
    progress = LearnProgress()
    _make_skill_competent(progress, "deck_control")
    _make_skill_competent(progress, "beatmatching")
    progress.skills["beatmatching"]["live_proof_count"] = 2

    mission = next_practice_mission(progress, active_lesson_id="L2.01")

    assert mission["lesson_id"] == "L2.01"
    assert mission["mode"] == "prove"
    assert mission["focus_label"] == "proof 2/3"
    assert mission["proof"] == "2 cited proofs banked; 1 left"
    assert mission["meter_label"] == "proof bank"
    assert mission["meter_value"] == 2
    assert mission["meter_max"] == 3
    assert mission["meter_caption"] == "1 proof left to Mastery"


def test_measured_miss_turns_current_proof_mission_into_recovery_target() -> None:
    progress = LearnProgress(course_2_unlocked=True)
    _make_skill_competent(progress, "beatmatching")
    progress.skills["beatmatching"]["live_proof_count"] = 1
    progress.mark_practice_feedback(
        "course_2_transitions",
        "L2.01",
        kind="beatmatch",
        label="phase drift",
        message="Deck B is late; nudge it forward before chasing proof.",
        detail="0.05 beats from lock",
    )

    mission = next_practice_mission(progress, active_lesson_id="L2.01")

    assert mission["lesson_id"] == "L2.01"
    assert mission["mode"] == "prove"
    assert mission["focus"] == "recovery"
    assert mission["focus_label"] == "phase drift"
    assert mission["command"] == (
        "Fix phase drift on beatmatching by ear; "
        "Deck B is late; nudge it forward before chasing proof."
    )
    assert mission["proof"] == "last measured miss: phase drift"
    assert mission["why"] == "fix the measured miss before chasing the next proof"
    assert mission["challenge"] == "Deck B is late; nudge it forward before chasing proof."
    assert mission["meter_label"] == "recovery target"
    assert mission["meter_value"] == 0
    assert mission["meter_max"] == 1
    assert mission["meter_state"] == "retry"
    assert mission["meter_caption"] == "0.05 beats from lock"


def test_active_mastered_lesson_becomes_the_current_mastery_mission() -> None:
    progress = LearnProgress()
    _make_skill_competent(progress, "deck_control")
    _make_skill_competent(progress, "beatmatching")
    threshold = SKILL_MANIFEST["beatmatching"].mastered_threshold
    progress.skills["beatmatching"] = {
        "live_proof_count": threshold,
        "mastered": True,
        "first_mastered_at": "2026-06-05T19:00:00Z",
    }

    mission = next_practice_mission(progress, active_lesson_id="L2.01")

    assert mission["lesson_id"] == "L2.01"
    assert mission["mode"] == "mastered"
    assert mission["focus"] == "mastery"
    assert mission["focus_label"] == "mastered"
    assert mission["command"] == (
        "Review beatmatching by ear; carry the mastered beatmatching move into a real set."
    )
    assert mission["proof"] == "3 cited proofs banked; Mastery earned"
    assert mission["why"] == "Mastery earned from cited live proof"
    assert mission["challenge"] == "Carry it into a real set while it is fresh."
    assert mission["meter_label"] == "mastery"
    assert mission["meter_value"] == 3
    assert mission["meter_max"] == 3
    assert mission["meter_state"] == "mastered"
    assert mission["meter_caption"] == "Mastery earned"
