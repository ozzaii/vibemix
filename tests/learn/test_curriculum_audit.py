# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn curriculum/course-pack audit surface."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from vibemix.learn import curriculum_audit
from vibemix.learn.curriculum import CourseMeta
from vibemix.learn.curriculum_audit import audit_curriculum
from vibemix.learn.lesson_flow import AdaptiveHint, LessonFlow, LessonStep, VerificationSpec

FRONTEND_CURRICULUM_META = (
    Path(__file__).resolve().parent.parent.parent
    / "tauri"
    / "ui"
    / "src"
    / "learn"
    / "lesson"
    / "curriculum-meta.ts"
)


def test_curriculum_audit_passes_current_beginner_module() -> None:
    report = audit_curriculum(frontend_path=FRONTEND_CURRICULUM_META)

    assert report["passed"] is True
    assert report["errors"] == []
    assert report["counts"]["beginner_lessons"] == 36
    assert report["beginner_course_ids"] == [
        "course_1_anatomy",
        "course_2_transitions",
        "course_3_play_mode",
    ]
    assert report["frontend_projection"]["up_to_date"] is True
    assert {row["course_id"] for row in report["course_rows"]} >= {
        "course_1_anatomy",
        "course_2_transitions",
        "course_3_play_mode",
    }
    course3 = next(
        row for row in report["course_rows"] if row["course_id"] == "course_3_play_mode"
    )
    assert course3["frontstage_mode"] == "live_play_mode"
    assert "live_audio" in course3["capabilities"]
    assert "live_audio" in course3["observed_capabilities"]
    flow_summary = report["flow_contract_summary"]
    assert flow_summary["beginner_flows_ok"] is True
    assert flow_summary["beginner_lessons"] == 36
    assert flow_summary["min_hint_count"] >= 3
    assert flow_summary["total_steps"] >= 36
    assert flow_summary["prompt_contract"] == {
        "ok": True,
        "max_chars": 150,
        "max_words": 24,
        "max_sentences": 2,
        "single_line": True,
        "inline_lists_forbidden": True,
        "observed_max_chars": 115,
        "observed_max_words": 23,
        "observed_max_sentences": 2,
        "exempt_step_ids": ["L1.01.beat.3"],
        "failing_lesson_ids": [],
    }
    assert flow_summary["teaching_grounding_contract"] == {
        "ok": True,
        "teaching_turn_count": 76,
        "grounded_teaching_turn_count": 76,
        "cited_teaching_turn_count": 76,
        "failing_lesson_ids": [],
    }
    assert flow_summary["hint_grounding_contract"] == {
        "ok": True,
        "hint_turn_count": 228,
        "grounded_hint_turn_count": 228,
        "cited_hint_turn_count": 228,
        "failing_lesson_ids": [],
    }
    assert flow_summary["input_surfaces"] == ["hardware", "screen"]
    assert flow_summary["input_surface_step_counts"] == {
        "hardware+screen": 32,
        "screen": 44,
    }
    assert flow_summary["verification_kind_counts"] == {
        "button_press": 51,
        "cc_delta": 25,
    }
    assert flow_summary["observable_control_count"] >= 10
    inventory = report["transcript_inventory"]
    assert inventory["ok"] is True
    assert inventory["fixture_count"] == len(report["lesson_rows"])
    assert inventory["declared_count"] == len(report["lesson_rows"])
    assert inventory["orphan_paths"] == []
    assert inventory["missing_paths"] == []
    truthfulness = report["copy_truthfulness_contract"]
    assert truthfulness["ok"] is True
    assert truthfulness["unsupported_debrief_auto_open_claims"] == []
    assert "debrief opens" in truthfulness["unsupported_auto_open_phrases"]


def test_curriculum_audit_proves_all_beginner_flows_compile() -> None:
    report = audit_curriculum()
    beginner_rows = [row for row in report["lesson_rows"] if row["beginner"]]

    assert len(beginner_rows) == 36
    assert all(row["transcript_ok"] is True for row in beginner_rows)
    assert all(row["flow_ok"] is True for row in beginner_rows)
    assert all(row["flow_summary"]["ok"] is True for row in beginner_rows)
    assert all(row["flow_summary"]["min_hint_count"] >= 3 for row in beginner_rows)
    assert all(row["flow_summary"]["prompt_contract"]["ok"] for row in beginner_rows)
    assert all(
        row["flow_summary"]["teaching_grounding_contract"]["ok"]
        for row in beginner_rows
    )
    assert all(
        row["flow_summary"]["hint_grounding_contract"]["ok"]
        for row in beginner_rows
    )
    assert all(row["flow_summary"]["observable_controls"] for row in beginner_rows)
    assert all(row["flow_summary"]["input_surfaces"] for row in beginner_rows)
    assert all(row["flow_summary"]["verification_kind_counts"] for row in beginner_rows)
    assert all(row["flow_summary"]["input_surface_step_counts"] for row in beginner_rows)

    total_steps = sum(row["flow_summary"]["step_count"] for row in beginner_rows)
    total_verifiers = sum(
        sum(row["flow_summary"]["verification_kind_counts"].values())
        for row in beginner_rows
    )
    total_surface_steps = sum(
        sum(row["flow_summary"]["input_surface_step_counts"].values())
        for row in beginner_rows
    )
    total_teaching_turns = sum(
        row["flow_summary"]["teaching_grounding_contract"]["teaching_turn_count"]
        for row in beginner_rows
    )
    total_grounded_teaching_turns = sum(
        row["flow_summary"]["teaching_grounding_contract"][
            "grounded_teaching_turn_count"
        ]
        for row in beginner_rows
    )
    total_cited_teaching_turns = sum(
        row["flow_summary"]["teaching_grounding_contract"]["cited_teaching_turn_count"]
        for row in beginner_rows
    )
    total_hint_turns = sum(
        row["flow_summary"]["hint_grounding_contract"]["hint_turn_count"]
        for row in beginner_rows
    )
    total_grounded_hint_turns = sum(
        row["flow_summary"]["hint_grounding_contract"]["grounded_hint_turn_count"]
        for row in beginner_rows
    )
    total_cited_hint_turns = sum(
        row["flow_summary"]["hint_grounding_contract"]["cited_hint_turn_count"]
        for row in beginner_rows
    )
    assert total_steps == 76
    assert total_verifiers == total_steps
    assert total_surface_steps == total_steps
    assert total_teaching_turns == total_steps
    assert total_grounded_teaching_turns == total_teaching_turns
    assert total_cited_teaching_turns == total_teaching_turns
    assert total_hint_turns == 228
    assert total_grounded_hint_turns == total_hint_turns
    assert total_cited_hint_turns == total_hint_turns


def test_curriculum_audit_rejects_syllabus_wall_flow_prompt(monkeypatch) -> None:
    long_prompt = (
        "First, stare at the whole interface before touching the deck. "
        "Second, memorize every label and every blinking light. "
        "Third, press cue after the checklist has finally ended."
    )
    action = {
        "type": "button",
        "control": "cue",
        "deck": "A",
        "direction": "down",
    }
    flow = LessonFlow(
        lesson_id="L9.99",
        course_id="course_9_lab",
        title="bad prompt lab",
        primary_expected_action=action,
        steps=(
            LessonStep(
                step_id="L9.99.practice",
                kind="practice",
                prompt=long_prompt,
                tts_marker="L999.beat0",
                citations=(),
                expected_action=action,
                verification=VerificationSpec(
                    kind="button_press",
                    control="cue",
                    deck="A",
                    observable_control_ids=("cue:A",),
                    input_surfaces=("hardware", "screen"),
                    direction="down",
                ),
                hints=(
                    AdaptiveHint(1, "press cue.", "L999.hint1", ()),
                    AdaptiveHint(2, "stay on deck A.", "L999.hint2", ()),
                    AdaptiveHint(3, "use the cue button.", "L999.hint3", ()),
                ),
            ),
        ),
        backstage_lenses=("evidence_registry", "controller_state"),
    )

    monkeypatch.setattr(curriculum_audit, "build_lesson_flow", lambda _lesson_id: flow)

    errors: list[dict] = []
    summary = curriculum_audit._check_flow_contract("L9.99", errors)

    assert summary["ok"] is False
    assert summary["prompt_contract"]["ok"] is False
    assert summary["prompt_contract"]["error_codes"] == [
        "lesson_flow_step_prompt_too_long",
        "lesson_flow_step_prompt_too_many_sentences",
        "lesson_flow_step_prompt_too_wordy",
    ]
    assert {error["code"] for error in errors} >= set(
        summary["prompt_contract"]["error_codes"]
    )


def test_curriculum_audit_exposes_machine_readable_course_pack_contract() -> None:
    report = audit_curriculum()
    contract = report["course_pack_contract"]

    assert contract["schema_version"] == 1
    assert contract["source_of_truth"] == {
        "python_curriculum": "src/vibemix/learn/curriculum.py",
        "transcript_root": "src/vibemix/learn/transcripts/",
        "frontend_projection": "tauri/ui/src/learn/lesson/curriculum-meta.ts",
        "draft_preflight": "src/vibemix/learn/course_pack.py",
        "draft_preflight_cli": "scripts/validate_learn_course_pack.py",
    }
    assert (
        contract["draft_validator"]["function"]
        == "vibemix.learn.course_pack.validate_course_pack_draft"
    )
    assert (
        contract["draft_validator"]["cli"]
        == "uv run python scripts/validate_learn_course_pack.py <course-pack.json>"
    )
    assert contract["draft_validator"]["template_cli"] == (
        "uv run python scripts/validate_learn_course_pack.py "
        "--init-template <dir> --course-number 4 --slug <slug>"
    )
    assert "observed_capabilities" in contract["draft_validator"]["result_fields"]
    assert "flow_preview" in contract["draft_validator"]["result_fields"]
    assert "integration_plan" in contract["draft_validator"]["result_fields"]
    assert "prompt_contract" in contract["draft_validator"]["result_fields"]
    assert "teaching_grounding_contract" in contract["draft_validator"][
        "result_fields"
    ]
    assert "hint_grounding_contract" in contract["draft_validator"]["result_fields"]
    assert "authoring_contract" in contract["draft_validator"]["result_fields"]
    assert "copy_truthfulness" in contract["draft_validator"]["result_fields"]
    assert contract["flow_contract"]["teaching_loop_contract"] == {
        "teaching_turns": (
            "every compiled step must plan through plan_teaching_turn, "
            "remain grounded, and carry a citation"
        ),
        "hint_turns": (
            "the first three adaptive hints must plan through plan_hint_turn, "
            "remain grounded, and carry citations"
        ),
    }
    assert [entry["name"] for entry in contract["python_entries"]] == [
        "COURSE_REGISTRY",
        "COURSE_FRAMES",
        "CURRICULUM",
    ]
    assert "capabilities" in contract["python_entries"][0]["required_fields"]
    assert contract["capability_contract"]["frontstage_modes"] == [
        "legacy_demo",
        "live_play_mode",
        "practice_booth",
    ]
    assert "library_exemplars" in contract["capability_contract"]["capabilities"]
    assert "live_audio" in contract["capability_contract"]["capabilities"]
    assert contract["unlock_gate_contract"] == {
        "progress_model": "src/vibemix/learn/progress.py:LearnProgress",
        "supported_unlock_gates": ["course_2_unlocked", "course_3_unlocked"],
        "rule": (
            "CourseMeta.unlock_gate must be null or a boolean persisted by "
            "LearnProgress.to_dict(); adding a new locked course requires a "
            "progress-schema field and generated frontend projection."
        ),
    }
    assert "automatic debrief opening" in contract["copy_truthfulness_contract"]["rule"]
    assert "system_instruction_addendum" in contract["transcript_required_fields"]
    assert contract["canonical_id_contract"] == {
        "course_id_pattern": "course_<number>_<slug>",
        "lesson_id_pattern": "L<number>.<two digits>",
        "rule": (
            "Future course-pack lesson IDs must match the numeric course "
            "prefix and be contiguous from .01."
        ),
        "starter_template": "scripts/validate_learn_course_pack.py --init-template",
    }
    assert contract["starter_template_contract"] == {
        "writes_manifest_authoring_contract": True,
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
    assert "debrief opens" in contract["copy_truthfulness_contract"][
        "unsupported_auto_open_phrases"
    ]
    assert "automatic debrief opening" in contract["copy_truthfulness_contract"]["rule"]
    assert "claimed by exactly one LessonMeta" in contract[
        "transcript_inventory_contract"
    ]
    assert (
        contract["flow_contract"]["compiler"]
        == "vibemix.learn.lesson_flow.build_lesson_flow"
    )
    assert contract["flow_contract"]["prompt_contract"] == {
        "max_chars": 150,
        "max_words": 24,
        "max_sentences": 2,
        "single_line": True,
        "inline_lists_forbidden": True,
    }
    assert contract["frontend_contract"]["manual_frontend_edits"] == "forbidden"
    assert (
        "uv run python scripts/export_learn_curriculum_meta.py --check"
        in contract["verification_commands"]
    )
    assert (
        "uv run pytest -q tests/learn/test_course_pack.py"
        in contract["verification_commands"]
    )
    assert (
        "uv run python scripts/validate_learn_course_pack.py <course-pack.json>"
        in contract["verification_commands"]
    )


def test_curriculum_audit_rejects_unlock_gate_not_backed_by_progress(monkeypatch) -> None:
    monkeypatch.setitem(
        curriculum_audit.COURSE_REGISTRY,
        "course_2_transitions",
        CourseMeta(
            label="Course 2 · Transitions",
            hud_label="COURSE 2 · TRANSITIONS",
            unlock_gate="course_4_unlocked",
            lock_reason="pass the prior course to unlock transitions",
            capabilities=("evidence_registry", "controller_state", "on_screen_deck"),
        ),
    )

    report = audit_curriculum()

    assert report["passed"] is False
    assert report["unlock_gate_contract"]["unsupported_unlock_gates"] == [
        "course_4_unlocked"
    ]
    assert any(
        error["code"] == "course_unlock_gate_not_persisted"
        for error in report["errors"]
    )


def test_curriculum_audit_detects_stale_frontend_projection(tmp_path: Path) -> None:
    stale = tmp_path / "curriculum-meta.ts"
    stale.write_text("// stale\n", encoding="utf-8")

    report = audit_curriculum(frontend_path=stale)

    assert report["passed"] is False
    assert report["frontend_projection"] == {
        "checked": True,
        "up_to_date": False,
        "path": str(stale),
    }
    assert any(error["code"] == "frontend_projection_stale" for error in report["errors"])


def test_curriculum_audit_detects_missing_frontend_projection(tmp_path: Path) -> None:
    missing = tmp_path / "missing" / "curriculum-meta.ts"

    report = audit_curriculum(frontend_path=missing)

    assert report["passed"] is False
    assert report["frontend_projection"] == {
        "checked": True,
        "up_to_date": False,
        "path": str(missing),
    }
    assert any(error["code"] == "frontend_projection_missing" for error in report["errors"])


def test_curriculum_audit_script_writes_json_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_path = tmp_path / "learn-curriculum-audit.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/audit_learn_curriculum.py",
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert proc.returncode == 0
    stdout_report = json.loads(proc.stdout)
    file_report = json.loads(out_path.read_text(encoding="utf-8"))
    assert stdout_report["passed"] is True
    assert file_report["counts"]["beginner_lessons"] == 36
    assert file_report["frontend_projection"]["up_to_date"] is True
