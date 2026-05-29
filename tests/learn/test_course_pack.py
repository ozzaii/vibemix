# SPDX-License-Identifier: Apache-2.0
"""Executable preflight for adding future Learn courses."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts import validate_learn_course_pack as cli

import vibemix.learn.course_pack as course_pack_module
from vibemix.learn.course_pack import (
    course_pack_template,
    load_course_pack_manifest,
    validate_course_pack_draft,
    validate_course_pack_manifest,
    write_course_pack_template,
)
from vibemix.learn.curriculum import CourseMeta, LessonMeta
from vibemix.learn.teaching_loop import (
    plan_hint_turn as real_plan_hint_turn,
)
from vibemix.learn.teaching_loop import (
    plan_teaching_turn as real_plan_teaching_turn,
)

COURSE_ID = "course_4_sampler"
ADDENDUM = "SAMPLER ADDENDUM: teach one visible cue action, then verify it."


def _lesson_meta(*, course_id: str = COURSE_ID) -> LessonMeta:
    return LessonMeta(
        title="cue sampler",
        course_id=course_id,
        system_instruction_addendum=ADDENDUM,
        transcript_path="course_4_sampler/01_cue_sampler.json",
    )


def _script(*, lesson_id: str = "L4.01") -> dict:
    return {
        "lesson_id": lesson_id,
        "title": "cue sampler",
        "system_instruction_addendum": ADDENDUM,
        "tutor_speak": [
            {
                "text": "press deck A cue once.",
                "tts_marker": "L401.beat0",
                "citations": ["[screen:cue:A]"],
            }
        ],
        "expected_action": {
            "type": "button",
            "control": "cue",
            "deck": "A",
            "direction": "down",
        },
        "hints": [
            {
                "text": "use the cue button on deck A.",
                "tts_marker": "L401.hint1",
                "citations": ["[screen:cue:A]"],
            },
            {
                "text": "stay on deck A, then press cue.",
                "tts_marker": "L401.hint2",
                "citations": ["[screen:cue:A]"],
            },
            {
                "text": "press the lit cue control.",
                "tts_marker": "L401.hint3",
                "citations": ["[screen:cue:A]"],
            },
        ],
    }


def _meta(*, capabilities=None, unlock_gate=None) -> CourseMeta:
    return CourseMeta(
        label="Course 4 · Sampler",
        hud_label="COURSE 4 · SAMPLER",
        unlock_gate=unlock_gate,
        lock_reason="pass the sampler gate" if unlock_gate else None,
        capabilities=capabilities
        or ("evidence_registry", "controller_state", "on_screen_deck"),
    )


def _write_manifest_pack(tmp_path: Path, *, script: dict | None = None) -> Path:
    transcript_path = Path("course_4_sampler/01_cue_sampler.json")
    full_transcript_path = tmp_path / transcript_path
    full_transcript_path.parent.mkdir(parents=True)
    full_transcript_path.write_text(
        json.dumps(script or _script()),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "course_id": COURSE_ID,
        "label": "Course 4 · Sampler",
        "hud_label": "COURSE 4 · SAMPLER",
        "frame": "Course 4 keeps the same one-action booth contract.",
        "frontstage_mode": "practice_booth",
        "capabilities": ["evidence_registry", "controller_state", "on_screen_deck"],
        "authoring_contract": course_pack_template(
            course_number=4,
            slug="sampler",
        )["manifest"]["authoring_contract"],
        "lessons": [
            {
                "lesson_id": "L4.01",
                "title": "cue sampler",
                "system_instruction_addendum": ADDENDUM,
                "transcript_path": str(transcript_path),
            }
        ],
    }
    manifest_path = tmp_path / "course-pack.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_valid_future_course_pack_compiles_without_global_mutation() -> None:
    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": _script()},
    )

    assert result.ok is True
    assert result.lesson_count == 1
    assert result.step_count == 1
    assert result.to_dict()["flow_preview"] == [
        {
            "lesson_id": "L4.01",
            "title": "cue sampler",
            "step_count": 1,
            "backstage_lenses": ["controller_state", "evidence_registry"],
            "steps": [
                {
                    "step_id": "L4.01.practice",
                    "kind": "practice",
                    "prompt": "press deck A cue once.",
                    "prompt_metrics": {
                        "chars": 22,
                        "words": 5,
                        "sentences": 1,
                        "single_line": True,
                        "has_inline_list": False,
                        "within_contract": True,
                    },
                    "verification_kind": "button_press",
                    "control": "cue",
                    "deck": "A",
                    "input_surfaces": ["hardware", "screen"],
                    "observable_control_ids": ["cue:A"],
                    "hint_count": 3,
                }
            ],
        }
    ]
    assert result.required_progress_fields == ()
    assert result.to_dict()["integration_plan"] == {
        "merge_ready": True,
        "summary": (
            "copy these rows into the shipped curriculum and regenerate the "
            "frontend projection"
        ),
        "target_files": {
            "python_curriculum": "src/vibemix/learn/curriculum.py",
            "transcript_root": "src/vibemix/learn/transcripts/",
            "frontend_projection": "tauri/ui/src/learn/lesson/curriculum-meta.ts",
            "progress_model": "src/vibemix/learn/progress.py",
        },
        "python_edits": [
            {
                "target": "COURSE_REGISTRY",
                "action": "add CourseMeta row",
                "course_id": COURSE_ID,
                "value": {
                    "label": "Course 4 · Sampler",
                    "hud_label": "COURSE 4 · SAMPLER",
                    "unlock_gate": None,
                    "lock_reason": None,
                    "frontstage_mode": "practice_booth",
                    "capabilities": [
                        "evidence_registry",
                        "controller_state",
                        "on_screen_deck",
                    ],
                    "beginner": True,
                },
            },
            {
                "target": "COURSE_FRAMES",
                "action": "add course frame",
                "course_id": COURSE_ID,
                "value": "Course 4 keeps the same one-action booth contract.",
            },
            {
                "target": "CURRICULUM",
                "action": "add LessonMeta rows",
                "course_id": COURSE_ID,
                "lesson_ids": ["L4.01"],
            },
        ],
        "transcript_paths": ["course_4_sampler/01_cue_sampler.json"],
        "commands": [
            "uv run python scripts/validate_learn_course_pack.py <course-pack.json>",
            "uv run python scripts/export_learn_curriculum_meta.py --check",
            "uv run pytest -q tests/learn/test_course_pack.py",
            "uv run python scripts/run_learn_python_quality.py --out /tmp/vibemix-live-learn-proof/learn-python-quality-current.json",
            "uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json",
        ],
    }
    assert result.to_dict()["copy_truthfulness"] == {
        "ok": True,
        "unsupported_debrief_auto_open_claims": [],
    }
    assert result.to_dict()["prompt_contract"] == {
        "ok": True,
        "max_chars": 150,
        "max_words": 24,
        "max_sentences": 2,
        "single_line": True,
        "inline_lists_forbidden": True,
        "observed_max_chars": 22,
        "observed_max_words": 5,
        "observed_max_sentences": 1,
        "error_codes": [],
    }
    assert result.to_dict()["teaching_grounding_contract"] == {
        "ok": True,
        "teaching_turn_count": 1,
        "grounded_teaching_turn_count": 1,
        "cited_teaching_turn_count": 1,
        "error_codes": [],
    }
    assert result.to_dict()["hint_grounding_contract"] == {
        "ok": True,
        "hint_turn_count": 3,
        "grounded_hint_turn_count": 3,
        "cited_hint_turn_count": 3,
        "error_codes": [],
    }
    assert result.observed_capabilities == (
        "controller_state",
        "evidence_registry",
        "on_screen_deck",
    )
    assert result.to_dict()["errors"] == []


def test_course_pack_template_is_canonical_and_valid(tmp_path: Path) -> None:
    template = course_pack_template(course_number=4, slug="sampler", lesson_count=2)
    report = write_course_pack_template(
        tmp_path / "starter",
        course_number=4,
        slug="sampler",
        lesson_count=2,
    )

    assert template["manifest"]["course_id"] == "course_4_sampler"
    assert template["manifest"]["authoring_contract"] == {
        "frontstage": "one prompt, one action, one grounded response",
        "default_input_surfaces": ["hardware", "screen"],
        "starter_expected_action": {
            "type": "button",
            "control": "cue",
            "deck": "A",
            "direction": "down",
        },
        "required_hint_count": 3,
        "prompt_limits": {
            "max_chars": 150,
            "max_words": 24,
            "max_sentences": 2,
            "single_line": True,
            "inline_lists_forbidden": True,
        },
        "copy_rules": [
            "cite the observable control on every teaching and hint turn",
            "do not promise automatic debrief opening",
        ],
        "post_merge_commands": [
            "uv run python scripts/export_learn_curriculum_meta.py --check",
            "uv run pytest -q tests/learn/test_course_pack.py",
            (
                "uv run python scripts/run_learn_perfection_package.py --out "
                "/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json"
            ),
        ],
    }
    assert [row["lesson_id"] for row in template["manifest"]["lessons"]] == [
        "L4.01",
        "L4.02",
    ]
    assert report["ok"] is True
    assert report["validation"]["lesson_count"] == 2
    assert report["validation"]["authoring_contract"]["ok"] is True
    assert report["validation"]["authoring_contract"]["required"] is True
    assert [row["lesson_id"] for row in report["validation"]["flow_preview"]] == [
        "L4.01",
        "L4.02",
    ]
    assert report["validation"]["errors"] == []


def test_course_pack_template_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "starter"
    write_course_pack_template(
        target,
        course_number=4,
        slug="sampler",
    )

    try:
        write_course_pack_template(
            target,
            course_number=4,
            slug="sampler",
        )
    except FileExistsError as exc:
        assert "would overwrite existing files" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected FileExistsError")


def test_future_course_pack_reports_missing_flow_capabilities() -> None:
    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(capabilities=("evidence_registry",)),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": _script()},
    )

    assert result.ok is False
    codes = {error.code for error in result.errors}
    assert "draft_capability_missing_for_flow" in codes
    assert {
        error.expected
        for error in result.errors
        if error.code == "draft_capability_missing_for_flow"
    } == {"controller_state", "on_screen_deck"}


def test_future_course_pack_reports_transcript_drift_and_hint_floor() -> None:
    broken = _script()
    broken["title"] = "wrong title"
    broken["hints"] = broken["hints"][:2]

    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": broken},
    )

    assert result.ok is False
    by_code = {error.code: error for error in result.errors}
    assert by_code["draft_transcript_metadata_drift"].field == "title"
    assert by_code["draft_hints_too_few"].actual == 2
    assert result.step_count == 0


def test_future_course_pack_rejects_syllabus_wall_prompt() -> None:
    broken = _script()
    broken["tutor_speak"][0]["text"] = (
        "First, read the whole booth before touching anything. "
        "Second, compare the two decks and memorize what every light means. "
        "Third, choose cue only after the long checklist is complete."
    )

    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": broken},
    )

    assert result.ok is False
    assert result.prompt_contract["ok"] is False
    assert result.prompt_contract["error_codes"] == [
        "draft_frontstage_prompt_too_long",
        "draft_frontstage_prompt_too_many_sentences",
        "draft_frontstage_prompt_too_wordy",
    ]
    assert {error.code for error in result.errors} >= set(
        result.prompt_contract["error_codes"]
    )


def test_future_course_pack_rejects_uncited_teaching_and_hint_turns(monkeypatch) -> None:
    def uncited_teaching_turn(**kwargs):
        return replace(real_plan_teaching_turn(**kwargs), citations=())

    def uncited_hint_turn(**kwargs):
        turn = real_plan_hint_turn(**kwargs)
        assert turn is not None
        return replace(turn, citations=())

    monkeypatch.setattr(
        course_pack_module,
        "plan_teaching_turn",
        uncited_teaching_turn,
    )
    monkeypatch.setattr(course_pack_module, "plan_hint_turn", uncited_hint_turn)

    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": _script()},
    )

    assert result.ok is False
    assert result.teaching_grounding_contract == {
        "ok": False,
        "teaching_turn_count": 1,
        "grounded_teaching_turn_count": 1,
        "cited_teaching_turn_count": 0,
        "error_codes": ["draft_teaching_turn_uncited"],
    }
    assert result.hint_grounding_contract == {
        "ok": False,
        "hint_turn_count": 3,
        "grounded_hint_turn_count": 3,
        "cited_hint_turn_count": 0,
        "error_codes": ["draft_hint_turn_uncited"],
    }
    assert {error.code for error in result.errors} >= {
        "draft_teaching_turn_uncited",
        "draft_hint_turn_uncited",
    }


def test_future_course_pack_rejects_unwired_debrief_auto_open_copy() -> None:
    broken = _script()
    broken["hints"][0]["text"] = "When this ends, the debrief opens automatically."

    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": broken},
    )

    assert result.ok is False
    assert result.copy_truthfulness["ok"] is False
    assert result.copy_truthfulness["unsupported_debrief_auto_open_claims"] == [
        {
            "lesson_id": "L4.01",
            "phrases": ["debrief opens", "opens automatically"],
        }
    ]
    by_code = {error.code: error for error in result.errors}
    assert by_code["draft_transcript_debrief_auto_open_unwired"].field == "learner_copy"


def test_future_course_pack_rejects_noncanonical_ids() -> None:
    result = validate_course_pack_draft(
        course_id="sampler_course",
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"cue-one": _lesson_meta(course_id="sampler_course")},
        scripts={"cue-one": _script(lesson_id="cue-one")},
    )

    codes = {error.code for error in result.errors}
    assert result.ok is False
    assert "draft_course_id_not_canonical" in codes
    assert "draft_lesson_id_not_canonical" in codes


def test_future_course_pack_rejects_lesson_number_mismatch_and_gaps() -> None:
    lessons = {
        "L5.01": _lesson_meta(),
        "L4.03": LessonMeta(
            title="second cue sampler",
            course_id=COURSE_ID,
            system_instruction_addendum=ADDENDUM,
            transcript_path="course_4_sampler/03_second_cue_sampler.json",
        ),
    }
    scripts = {
        lesson_id: _script(lesson_id=lesson_id)
        for lesson_id in lessons
    }

    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons=lessons,
        scripts=scripts,
    )

    codes = {error.code for error in result.errors}
    assert result.ok is False
    assert "draft_lesson_id_course_number_mismatch" in codes
    assert "draft_lesson_ids_not_contiguous" in codes


def test_future_locked_course_pack_surfaces_required_progress_field() -> None:
    result = validate_course_pack_draft(
        course_id=COURSE_ID,
        meta=_meta(unlock_gate="course_4_unlocked"),
        frame="Course 4 keeps the same one-action booth contract.",
        lessons={"L4.01": _lesson_meta()},
        scripts={"L4.01": _script()},
    )

    assert result.ok is True
    assert result.required_progress_fields == ("course_4_unlocked",)
    assert result.integration_plan["python_edits"][-1] == {
        "target": "src/vibemix/learn/progress.py:LearnProgress",
        "action": "add boolean progress fields before using this unlock gate",
        "fields": ["course_4_unlocked"],
    }


def test_course_pack_manifest_loads_json_and_validates(tmp_path: Path) -> None:
    manifest_path = _write_manifest_pack(tmp_path)

    draft = load_course_pack_manifest(manifest_path)
    result = validate_course_pack_manifest(manifest_path)

    assert draft.course_id == COURSE_ID
    assert tuple(draft.lessons) == ("L4.01",)
    assert draft.authoring_contract["frontstage"] == (
        "one prompt, one action, one grounded response"
    )
    assert result.ok is True
    assert result.to_dict()["step_count"] == 1
    assert result.to_dict()["authoring_contract"]["ok"] is True


def test_course_pack_manifest_rejects_missing_authoring_contract(tmp_path: Path) -> None:
    manifest_path = _write_manifest_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("authoring_contract")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_course_pack_manifest(manifest_path)

    assert result.ok is False
    assert result.to_dict()["authoring_contract"] == {
        "ok": False,
        "required": True,
        "frontstage": None,
        "default_input_surfaces": [],
        "required_hint_count": None,
        "prompt_limits": {},
        "copy_rules": [],
        "post_merge_commands": [],
        "error_codes": ["draft_authoring_contract_missing"],
    }
    assert "draft_authoring_contract_missing" in {
        error.code for error in result.errors
    }


def test_course_pack_manifest_reports_missing_transcript(tmp_path: Path) -> None:
    manifest_path = _write_manifest_pack(tmp_path)
    (tmp_path / "course_4_sampler" / "01_cue_sampler.json").unlink()

    result = validate_course_pack_manifest(manifest_path)

    assert result.ok is False
    assert result.errors[0].code == "draft_manifest_invalid"
    assert "transcript file not found" in result.errors[0].message


def test_validate_learn_course_pack_cli_writes_report(tmp_path: Path) -> None:
    manifest_path = _write_manifest_pack(tmp_path)
    out_path = tmp_path / "course-pack-validation.json"

    assert cli.main([str(manifest_path), "--out", str(out_path)]) == 0

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["flow_preview"][0]["steps"][0]["observable_control_ids"] == ["cue:A"]
    assert report["copy_truthfulness"]["ok"] is True
    assert report["authoring_contract"]["ok"] is True
    assert report["authoring_contract"]["required"] is True
    assert report["observed_capabilities"] == [
        "controller_state",
        "evidence_registry",
        "on_screen_deck",
    ]


def test_validate_learn_course_pack_cli_initializes_template(tmp_path: Path) -> None:
    target = tmp_path / "starter"

    assert cli.main(
        [
            "--init-template",
            str(target),
            "--course-number",
            "4",
            "--slug",
            "sampler",
            "--lesson-count",
            "2",
        ]
    ) == 0

    manifest_path = target / "course-pack.json"
    report = validate_course_pack_manifest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report.ok is True
    assert [row["lesson_id"] for row in manifest["lessons"]] == ["L4.01", "L4.02"]
    assert manifest["authoring_contract"]["frontstage"] == (
        "one prompt, one action, one grounded response"
    )
    assert manifest["authoring_contract"]["required_hint_count"] == 3
    assert [row["step_count"] for row in report.to_dict()["flow_preview"]] == [1, 1]
