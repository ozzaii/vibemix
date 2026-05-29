# SPDX-License-Identifier: Apache-2.0
"""Phase 96 Plan 03 — Course 3 fixtures + curriculum.py extension validation.

Pins:
  - 6 hand-authored Course 3 JSON fixtures exist + parse + match P92 canonical
    shape (lesson_id / title / addendum / tutor_speak / expected_action /
    hints×3).
  - proactive_lens_active + exemplar_audio_forbidden booleans correct per
    lesson (L3.01-L3.05 = true / true; L3.06 = false / false).
  - curriculum.py COURSE_FRAMES["course_3_play_mode"] frame exists + ≤ soft cap.
  - curriculum.py CURRICULUM has 6 new L3.NN entries with addendum byte-equal
    to their fixture's system_instruction_addendum (drift gate).
  - Existing CURRICULUM entries (L0.00, L1.01..L1.16, L2.01..L2.14) UNCHANGED.
  - L3.05 carries the drill_shapes array with the two CONTEXT-locked drills.

REQ-IDs: CURR-3.01..3.06.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM, LessonMeta

_REPO = Path(__file__).resolve().parent.parent.parent
_BASE = _REPO / "src" / "vibemix" / "learn" / "transcripts" / "course_3_play_mode"

_EXPECTED_FIXTURES: tuple[tuple[str, str, bool, bool], ...] = (
    # (lesson_id, filename, proactive_lens_active, exemplar_audio_forbidden)
    ("L3.01", "01_first_5_minute_mix.json", True, True),
    ("L3.02", "02_first_15_minute_set.json", True, True),
    ("L3.03", "03_reading_the_room.json", True, True),
    ("L3.04", "04_first_30_minute_capstone.json", True, True),
    ("L3.05", "05_recovery_drills.json", True, True),
    ("L3.06", "06_dj_profile_graduation.json", False, False),
)


@pytest.mark.parametrize(
    "lesson_id,filename,_lens,_forbidden", _EXPECTED_FIXTURES
)
def test_fixture_exists_and_parses(
    lesson_id: str, filename: str, _lens: bool, _forbidden: bool
) -> None:
    path = _BASE / filename
    assert path.exists(), f"missing fixture: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["lesson_id"] == lesson_id


@pytest.mark.parametrize(
    "lesson_id,filename,_lens,_forbidden", _EXPECTED_FIXTURES
)
def test_fixture_canonical_shape(
    lesson_id: str, filename: str, _lens: bool, _forbidden: bool
) -> None:
    data = json.loads((_BASE / filename).read_text(encoding="utf-8"))
    assert "title" in data
    assert "system_instruction_addendum" in data
    assert len(data["system_instruction_addendum"]) <= 200, (
        f"{filename}: addendum > 200 chars"
    )
    assert "tutor_speak" in data and isinstance(data["tutor_speak"], list)
    assert "expected_action" in data
    assert "hints" in data and len(data["hints"]) == 3


@pytest.mark.parametrize(
    "lesson_id,filename,lens,_forbidden", _EXPECTED_FIXTURES
)
def test_proactive_lens_active_field(
    lesson_id: str, filename: str, lens: bool, _forbidden: bool
) -> None:
    data = json.loads((_BASE / filename).read_text(encoding="utf-8"))
    assert data.get("proactive_lens_active") is lens, (
        f"{lesson_id} proactive_lens_active expected {lens}, got "
        f"{data.get('proactive_lens_active')!r}"
    )


@pytest.mark.parametrize(
    "lesson_id,filename,_lens,forbidden", _EXPECTED_FIXTURES
)
def test_exemplar_audio_forbidden_field(
    lesson_id: str, filename: str, _lens: bool, forbidden: bool
) -> None:
    data = json.loads((_BASE / filename).read_text(encoding="utf-8"))
    assert data.get("exemplar_audio_forbidden") is forbidden, (
        f"{lesson_id} exemplar_audio_forbidden expected {forbidden}, got "
        f"{data.get('exemplar_audio_forbidden')!r}"
    )


def test_course_3_frame_present() -> None:
    assert "course_3_play_mode" in COURSE_FRAMES, (
        "COURSE_FRAMES missing course_3_play_mode"
    )
    frame = COURSE_FRAMES["course_3_play_mode"]
    assert isinstance(frame, str)
    assert 50 <= len(frame) <= 500, (
        f"course_3_play_mode frame length {len(frame)} outside [50, 500]"
    )


@pytest.mark.parametrize(
    "lesson_id,filename,_lens,_forbidden", _EXPECTED_FIXTURES
)
def test_curriculum_entry_present(
    lesson_id: str, filename: str, _lens: bool, _forbidden: bool
) -> None:
    assert lesson_id in CURRICULUM
    meta = CURRICULUM[lesson_id]
    assert isinstance(meta, LessonMeta)
    assert meta.course_id == "course_3_play_mode"
    assert meta.transcript_path == f"course_3_play_mode/{filename}"
    assert len(meta.system_instruction_addendum) <= 200


@pytest.mark.parametrize(
    "lesson_id,filename,_lens,_forbidden", _EXPECTED_FIXTURES
)
def test_addendum_byte_equal_between_curriculum_and_fixture(
    lesson_id: str, filename: str, _lens: bool, _forbidden: bool
) -> None:
    meta = CURRICULUM[lesson_id]
    script = json.loads((_BASE / filename).read_text(encoding="utf-8"))
    assert script["system_instruction_addendum"] == meta.system_instruction_addendum, (
        f"{lesson_id} addendum drift between fixture and curriculum entry"
    )


def test_existing_course_entries_untouched() -> None:
    """P92's hello-world entry + P94's L1.01..L1.16 + P95's L2.01..L2.14
    stay byte-identical. Plan 96-03 only APPENDS."""
    assert "L0.00-press-play" in CURRICULUM
    assert CURRICULUM["L0.00-press-play"].course_id == "course_0"
    for n in range(1, 17):
        lid = f"L1.{n:02d}"
        assert lid in CURRICULUM, f"{lid} dropped"
        assert CURRICULUM[lid].course_id == "course_1_anatomy"
    for n in range(1, 15):
        lid = f"L2.{n:02d}"
        assert lid in CURRICULUM, f"{lid} dropped"
        assert CURRICULUM[lid].course_id == "course_2_transitions"


def test_l3_06_is_post_set_review() -> None:
    """L3.06 specific shape: NO active session → no lens, no exemplar
    forbiddance (debrief is the surface)."""
    data = json.loads(
        (_BASE / "06_dj_profile_graduation.json").read_text(encoding="utf-8")
    )
    assert data["proactive_lens_active"] is False
    assert data["exemplar_audio_forbidden"] is False


def test_l3_04_capstone_does_not_promise_debrief_auto_open() -> None:
    """The capstone can save session evidence, but auto-open is not wired."""
    data = json.loads(
        (_BASE / "04_first_30_minute_capstone.json").read_text(encoding="utf-8")
    )
    text = " ".join(
        [data["system_instruction_addendum"]]
        + [row["text"] for row in data["tutor_speak"]]
        + [row["text"] for row in data["hints"]]
    ).lower()

    assert "post-set debrief" in text
    assert "debrief opens" not in text
    assert "opens automatically" not in text
    assert "should have opened automatically" not in text


def test_l3_05_declares_drill_shapes() -> None:
    """L3.05 declares the train-wreck drill shapes the future runtime
    consumes (per CONTEXT.md §Claude's Discretion: drill mechanism is
    playback-rate / pitch drift on deck B)."""
    data = json.loads(
        (_BASE / "05_recovery_drills.json").read_text(encoding="utf-8")
    )
    assert "drill_shapes" in data
    drills = data["drill_shapes"]
    assert isinstance(drills, list) and len(drills) == 2
    drill_names = {d["drill"] for d in drills}
    assert drill_names == {"key_clash", "misaligned_phrase"}


def test_course_3_lesson_count_locked() -> None:
    """Anti-creep: exactly 6 Course 3 lessons land per PROJECT.md curriculum
    count (anatomy 16 + transitions 14 + play-mode 6 = 36 lessons total)."""
    course_3_keys = [
        lid for lid, meta in CURRICULUM.items()
        if meta.course_id == "course_3_play_mode"
    ]
    assert len(course_3_keys) == 6, (
        f"Course 3 count drift — expected 6, got {len(course_3_keys)}: "
        f"{course_3_keys}"
    )
