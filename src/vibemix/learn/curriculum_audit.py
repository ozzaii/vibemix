# SPDX-License-Identifier: Apache-2.0
"""Audit helpers for Learn curriculum/course-pack integration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vibemix.learn.copy_truth import (
    SPECULATIVE_DEBRIEF_AUTO_OPEN_PHRASES,
    unsupported_debrief_auto_open_phrases,
)
from vibemix.learn.curriculum import (
    COURSE_CAPABILITIES,
    COURSE_FRAMES,
    COURSE_FRONTSTAGE_MODES,
    COURSE_REGISTRY,
    CURRICULUM,
    beginner_course_ids,
    beginner_lesson_ids,
    course_lesson_ids,
)
from vibemix.learn.curriculum_projection import render_curriculum_meta_ts
from vibemix.learn.lesson_flow import (
    MAX_FRONTSTAGE_PROMPT_CHARS,
    MAX_FRONTSTAGE_PROMPT_SENTENCES,
    MAX_FRONTSTAGE_PROMPT_WORDS,
    build_lesson_flow,
    frontstage_prompt_contract_exempt,
    frontstage_prompt_metrics,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.teaching_loop import (
    plan_hint_turn,
    plan_teaching_turn,
    teaching_turn_is_grounded,
)

_FLOW_LENS_CAPABILITIES = {
    "controller_state": "controller_state",
    "cue_section_lookahead": "cue_section_lookahead",
    "debrief": "debrief",
    "dj_profile": "dj_profile",
    "evidence_registry": "evidence_registry",
    "library_exemplars": "library_exemplars",
    "library_suggestions": "library_suggestions",
    "live_audio": "live_audio",
    "prepared_pool": "prepared_pool",
    "recital_observer": "recital_observer",
    "recovery_drill": "recovery_drill",
    "session_recording": "session_recording",
    "session_state": "session_state",
}

def audit_curriculum(frontend_path: Path | None = None) -> dict[str, Any]:
    """Return a JSON-safe audit report for the Learn curriculum contract."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    unlock_gate_contract = _unlock_gate_contract(errors)
    course_rows = _course_rows(errors)
    beginner_ids = beginner_lesson_ids()
    lesson_rows = _lesson_rows(errors, beginner_ids)
    flow_contract_summary = _flow_contract_summary(lesson_rows)
    transcript_inventory = _transcript_inventory(errors)
    copy_truthfulness_contract = _copy_truthfulness_contract(errors)

    if set(COURSE_FRAMES) != set(COURSE_REGISTRY):
        errors.append(
            {
                "code": "registry_frame_mismatch",
                "message": "COURSE_FRAMES and COURSE_REGISTRY keys must match.",
                "registry_only": sorted(set(COURSE_REGISTRY) - set(COURSE_FRAMES)),
                "frames_only": sorted(set(COURSE_FRAMES) - set(COURSE_REGISTRY)),
            }
        )

    frontend_projection = _frontend_projection_check(frontend_path, errors)
    return {
        "schema_version": 1,
        "passed": not errors,
        "counts": {
            "courses": len(COURSE_REGISTRY),
            "beginner_courses": len(beginner_course_ids()),
            "lessons": len(CURRICULUM),
            "beginner_lessons": len(beginner_ids),
        },
        "beginner_course_ids": list(beginner_course_ids()),
        "beginner_lesson_ids": list(beginner_ids),
        "course_rows": course_rows,
        "lesson_rows": lesson_rows,
        "flow_contract_summary": flow_contract_summary,
        "unlock_gate_contract": unlock_gate_contract,
        "copy_truthfulness_contract": copy_truthfulness_contract,
        "transcript_inventory": transcript_inventory,
        "frontend_projection": frontend_projection,
        "errors": errors,
        "warnings": warnings,
        "course_pack_contract": course_pack_contract(),
        "new_course_contract": [
            "preflight the draft with validate_course_pack_draft before merging",
            "add COURSE_REGISTRY metadata",
            "keep course_id and lesson_id numbering canonical and contiguous",
            "declare frontstage_mode and capabilities for every coded seam",
            "add matching COURSE_FRAMES entry",
            "add LessonMeta rows pointing at transcript JSON fixtures",
            "keep lesson_id, title, and system_instruction_addendum byte-aligned",
            "make every beginner lesson compile through build_lesson_flow",
            "keep course capabilities covering every compiled backstage lens",
            "keep learner-facing copy truthful about runtime-owned actions",
            "run codegen:learn so the frontend projection stays generated",
        ],
    }


def course_pack_contract() -> dict[str, Any]:
    """Return a machine-readable checklist for adding future Learn courses."""
    supported_unlock_gates = _supported_unlock_gates()
    return {
        "schema_version": 1,
        "source_of_truth": {
            "python_curriculum": "src/vibemix/learn/curriculum.py",
            "transcript_root": "src/vibemix/learn/transcripts/",
            "frontend_projection": "tauri/ui/src/learn/lesson/curriculum-meta.ts",
            "draft_preflight": "src/vibemix/learn/course_pack.py",
            "draft_preflight_cli": "scripts/validate_learn_course_pack.py",
        },
        "draft_validator": {
            "function": "vibemix.learn.course_pack.validate_course_pack_draft",
            "cli": "uv run python scripts/validate_learn_course_pack.py <course-pack.json>",
            "template_cli": (
                "uv run python scripts/validate_learn_course_pack.py "
                "--init-template <dir> --course-number 4 --slug <slug>"
            ),
            "rule": (
                "Future courses are validated against CourseMeta, LessonMeta, "
                "transcript metadata, hint floors, observed capabilities, and "
                "the canonical structured-flow compiler before global tables "
                "or fixture files are edited."
            ),
            "result_fields": [
                "ok",
                "lesson_count",
                "step_count",
                "flow_preview",
                "observed_capabilities",
                "required_progress_fields",
                "integration_plan",
                "prompt_contract",
                "teaching_grounding_contract",
                "hint_grounding_contract",
                "authoring_contract",
                "copy_truthfulness",
                "errors",
            ],
        },
        "canonical_id_contract": {
            "course_id_pattern": "course_<number>_<slug>",
            "lesson_id_pattern": "L<number>.<two digits>",
            "rule": (
                "Future course-pack lesson IDs must match the numeric course "
                "prefix and be contiguous from .01."
            ),
            "starter_template": "scripts/validate_learn_course_pack.py --init-template",
        },
        "starter_template_contract": {
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
                "max_chars": MAX_FRONTSTAGE_PROMPT_CHARS,
                "max_words": MAX_FRONTSTAGE_PROMPT_WORDS,
                "max_sentences": MAX_FRONTSTAGE_PROMPT_SENTENCES,
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
        },
        "copy_truthfulness_contract": {
            "unsupported_auto_open_phrases": list(
                SPECULATIVE_DEBRIEF_AUTO_OPEN_PHRASES
            ),
            "rule": (
                "Draft course-pack transcript copy must not promise automatic "
                "debrief opening unless a runtime command and frontend invoke "
                "path are added to the Learn contract."
            ),
        },
        "python_entries": [
            {
                "name": "COURSE_REGISTRY",
                "required_fields": [
                    "label",
                    "hud_label",
                    "unlock_gate",
                    "lock_reason",
                    "beginner",
                    "frontstage_mode",
                    "capabilities",
                ],
            },
            {
                "name": "COURSE_FRAMES",
                "required_fields": ["course_id", "course_context_text"],
                "rule": "keys must exactly match COURSE_REGISTRY",
            },
            {
                "name": "CURRICULUM",
                "required_fields": [
                    "lesson_id",
                    "title",
                    "course_id",
                    "system_instruction_addendum",
                    "transcript_path",
                ],
            },
        ],
        "transcript_required_fields": [
            "lesson_id",
            "title",
            "system_instruction_addendum",
            "tutor_speak",
            "expected_action",
            "hints",
        ],
        "transcript_inventory_contract": (
            "every transcript JSON under src/vibemix/learn/transcripts is claimed "
            "by exactly one LessonMeta row, and every LessonMeta transcript_path exists"
        ),
        "flow_contract": {
            "compiler": "vibemix.learn.lesson_flow.build_lesson_flow",
            "beginner_gate": "every beginner lesson must compile to at least one step",
            "prompt_contract": {
                "max_chars": MAX_FRONTSTAGE_PROMPT_CHARS,
                "max_words": MAX_FRONTSTAGE_PROMPT_WORDS,
                "max_sentences": MAX_FRONTSTAGE_PROMPT_SENTENCES,
                "single_line": True,
                "inline_lists_forbidden": True,
            },
            "verification": (
                "each step must expose one calm frontstage prompt, observable "
                "controls, deterministic input surfaces, and at least three "
                "adaptive hints"
            ),
            "teaching_loop_contract": {
                "teaching_turns": (
                    "every compiled step must plan through plan_teaching_turn, "
                    "remain grounded, and carry a citation"
                ),
                "hint_turns": (
                    "the first three adaptive hints must plan through plan_hint_turn, "
                    "remain grounded, and carry citations"
                ),
            },
        },
        "capability_contract": {
            "frontstage_modes": sorted(COURSE_FRONTSTAGE_MODES),
            "capabilities": sorted(COURSE_CAPABILITIES),
            "rule": (
                "COURSE_REGISTRY capabilities must cover every compiled "
                "backstage lens and input surface used by its lesson flows."
            ),
        },
        "unlock_gate_contract": {
            "progress_model": "src/vibemix/learn/progress.py:LearnProgress",
            "supported_unlock_gates": supported_unlock_gates,
            "rule": (
                "CourseMeta.unlock_gate must be null or a boolean persisted by "
                "LearnProgress.to_dict(); adding a new locked course requires a "
                "progress-schema field and generated frontend projection."
            ),
        },
        "frontend_contract": {
            "generated_by": "scripts/export_learn_curriculum_meta.py",
            "manual_frontend_edits": "forbidden",
            "check_command": "uv run python scripts/export_learn_curriculum_meta.py --check",
        },
        "verification_commands": [
            "uv run python scripts/audit_learn_curriculum.py",
            "uv run python scripts/export_learn_curriculum_meta.py --check",
            "uv run python scripts/validate_learn_course_pack.py <course-pack.json>",
            "uv run pytest -q tests/learn/test_course_pack.py",
            "uv run pytest -q tests/learn/test_curriculum_audit.py",
            "uv run pytest -q tests/learn/test_lesson_flow_contract.py",
            "npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts",
        ],
    }


def _course_rows(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for course_id, meta in COURSE_REGISTRY.items():
        lessons = course_lesson_ids(course_id)
        observed_capabilities = _observed_course_capabilities(
            course_id,
            lessons,
            errors,
        )
        row = {
            "course_id": course_id,
            "label": meta.label,
            "hud_label": meta.hud_label,
            "unlock_gate": meta.unlock_gate,
            "lock_reason": meta.lock_reason,
            "beginner": meta.beginner,
            "frontstage_mode": meta.frontstage_mode,
            "capabilities": list(meta.capabilities),
            "observed_capabilities": list(observed_capabilities),
            "has_frame": course_id in COURSE_FRAMES,
            "lesson_count": len(lessons),
            "lesson_ids": list(lessons),
        }
        rows.append(row)
        if meta.frontstage_mode not in COURSE_FRONTSTAGE_MODES:
            errors.append(
                {
                    "code": "course_frontstage_mode_unknown",
                    "course_id": course_id,
                    "frontstage_mode": meta.frontstage_mode,
                    "message": "CourseMeta.frontstage_mode must be a known mode.",
                }
            )
        if not meta.capabilities:
            errors.append(
                {
                    "code": "course_capabilities_empty",
                    "course_id": course_id,
                    "message": "Every course must declare at least one capability.",
                }
            )
        unknown_capabilities = sorted(set(meta.capabilities) - set(COURSE_CAPABILITIES))
        if unknown_capabilities:
            errors.append(
                {
                    "code": "course_capability_unknown",
                    "course_id": course_id,
                    "capabilities": unknown_capabilities,
                    "message": "CourseMeta.capabilities contains an unknown capability.",
                }
            )
        missing_capabilities = sorted(set(observed_capabilities) - set(meta.capabilities))
        if missing_capabilities:
            errors.append(
                {
                    "code": "course_capability_missing_for_flow",
                    "course_id": course_id,
                    "capabilities": missing_capabilities,
                    "message": (
                        "CourseMeta.capabilities must cover the compiled "
                        "lesson flow's backstage requirements."
                    ),
                }
            )
        if not row["has_frame"]:
            errors.append(
                {
                    "code": "course_frame_missing",
                    "course_id": course_id,
                    "message": "Every registered course needs a COURSE_FRAMES entry.",
                }
            )
        if not lessons:
            errors.append(
                {
                    "code": "course_has_no_lessons",
                    "course_id": course_id,
                    "message": "Every registered course needs at least one lesson.",
                }
            )
    return rows


def _unlock_gate_contract(errors: list[dict[str, Any]]) -> dict[str, Any]:
    supported_gates = _supported_unlock_gates()
    used_gates = sorted(
        {
            meta.unlock_gate
            for meta in COURSE_REGISTRY.values()
            if isinstance(meta.unlock_gate, str) and meta.unlock_gate
        }
    )
    unsupported_gates = sorted(set(used_gates) - set(supported_gates))
    if unsupported_gates:
        errors.append(
            {
                "code": "course_unlock_gate_not_persisted",
                "unlock_gates": unsupported_gates,
                "supported_unlock_gates": supported_gates,
                "message": (
                    "CourseMeta.unlock_gate must be backed by a persisted "
                    "LearnProgress boolean before the frontend can unlock it."
                ),
            }
        )
    missing_lock_reasons = sorted(
        course_id
        for course_id, meta in COURSE_REGISTRY.items()
        if meta.unlock_gate and not meta.lock_reason
    )
    if missing_lock_reasons:
        errors.append(
            {
                "code": "course_unlock_gate_missing_lock_reason",
                "course_ids": missing_lock_reasons,
                "message": "Locked courses need a learner-facing lock_reason.",
            }
        )
    return {
        "progress_model": "src/vibemix/learn/progress.py:LearnProgress",
        "supported_unlock_gates": supported_gates,
        "used_unlock_gates": used_gates,
        "unsupported_unlock_gates": unsupported_gates,
        "missing_lock_reason_course_ids": missing_lock_reasons,
        "ok": not unsupported_gates and not missing_lock_reasons,
    }


def _supported_unlock_gates() -> list[str]:
    snapshot = LearnProgress().to_dict()
    return sorted(
        key
        for key, value in snapshot.items()
        if key.startswith("course_") and key.endswith("_unlocked") and isinstance(value, bool)
    )


def _flow_contract_summary(lesson_rows: list[dict[str, Any]]) -> dict[str, Any]:
    beginner_rows = [row for row in lesson_rows if row.get("beginner") is True]
    summaries = [
        row.get("flow_summary")
        for row in beginner_rows
        if isinstance(row.get("flow_summary"), dict)
    ]
    input_surfaces: set[str] = set()
    backstage_lenses: set[str] = set()
    observable_controls: set[str] = set()
    total_steps = 0
    hint_counts: list[int] = []
    failing_lesson_ids: list[str] = []
    prompt_failing_lesson_ids: list[str] = []
    prompt_exempt_step_ids: list[str] = []
    verification_kind_counts: dict[str, int] = {}
    input_surface_step_counts: dict[str, int] = {}
    max_prompt_chars = 0
    max_prompt_words = 0
    max_prompt_sentences = 0
    teaching_turn_count = 0
    grounded_teaching_turn_count = 0
    cited_teaching_turn_count = 0
    teaching_grounding_failing_lesson_ids: list[str] = []
    hint_turn_count = 0
    grounded_hint_turn_count = 0
    cited_hint_turn_count = 0
    hint_grounding_failing_lesson_ids: list[str] = []
    for row in beginner_rows:
        summary = row.get("flow_summary")
        if row.get("flow_ok") is not True:
            failing_lesson_ids.append(str(row.get("lesson_id")))
        if not isinstance(summary, dict):
            continue
        total_steps += int(summary.get("step_count") or 0)
        hint_counts.append(int(summary.get("min_hint_count") or 0))
        input_surfaces.update(str(value) for value in summary.get("input_surfaces") or [])
        backstage_lenses.update(str(value) for value in summary.get("backstage_lenses") or [])
        observable_controls.update(
            str(value) for value in summary.get("observable_controls") or []
        )
        _merge_counts(verification_kind_counts, summary.get("verification_kind_counts"))
        _merge_counts(input_surface_step_counts, summary.get("input_surface_step_counts"))
        prompt_contract = summary.get("prompt_contract")
        if isinstance(prompt_contract, dict):
            if prompt_contract.get("ok") is not True:
                prompt_failing_lesson_ids.append(str(row.get("lesson_id")))
            max_prompt_chars = max(
                max_prompt_chars,
                int(prompt_contract.get("observed_max_chars") or 0),
            )
            max_prompt_words = max(
                max_prompt_words,
                int(prompt_contract.get("observed_max_words") or 0),
            )
            max_prompt_sentences = max(
                max_prompt_sentences,
                int(prompt_contract.get("observed_max_sentences") or 0),
            )
            prompt_exempt_step_ids.extend(
                str(value) for value in prompt_contract.get("exempt_step_ids") or []
            )
        hint_grounding_contract = summary.get("hint_grounding_contract")
        if isinstance(hint_grounding_contract, dict):
            hint_turn_count += int(hint_grounding_contract.get("hint_turn_count") or 0)
            grounded_hint_turn_count += int(
                hint_grounding_contract.get("grounded_hint_turn_count") or 0
            )
            cited_hint_turn_count += int(
                hint_grounding_contract.get("cited_hint_turn_count") or 0
            )
            if hint_grounding_contract.get("ok") is not True:
                hint_grounding_failing_lesson_ids.append(str(row.get("lesson_id")))
        teaching_grounding_contract = summary.get("teaching_grounding_contract")
        if isinstance(teaching_grounding_contract, dict):
            teaching_turn_count += int(
                teaching_grounding_contract.get("teaching_turn_count") or 0
            )
            grounded_teaching_turn_count += int(
                teaching_grounding_contract.get("grounded_teaching_turn_count") or 0
            )
            cited_teaching_turn_count += int(
                teaching_grounding_contract.get("cited_teaching_turn_count") or 0
            )
            if teaching_grounding_contract.get("ok") is not True:
                teaching_grounding_failing_lesson_ids.append(str(row.get("lesson_id")))
    return {
        "beginner_lessons": len(beginner_rows),
        "beginner_flows_ok": len(summaries) == len(beginner_rows) and not failing_lesson_ids,
        "failing_lesson_ids": failing_lesson_ids,
        "total_steps": total_steps,
        "min_hint_count": min(hint_counts) if hint_counts else 0,
        "prompt_contract": {
            "ok": len(summaries) == len(beginner_rows) and not prompt_failing_lesson_ids,
            "max_chars": MAX_FRONTSTAGE_PROMPT_CHARS,
            "max_words": MAX_FRONTSTAGE_PROMPT_WORDS,
            "max_sentences": MAX_FRONTSTAGE_PROMPT_SENTENCES,
            "single_line": True,
            "inline_lists_forbidden": True,
            "observed_max_chars": max_prompt_chars,
            "observed_max_words": max_prompt_words,
            "observed_max_sentences": max_prompt_sentences,
            "exempt_step_ids": prompt_exempt_step_ids,
            "failing_lesson_ids": prompt_failing_lesson_ids,
        },
        "teaching_grounding_contract": {
            "ok": (
                len(summaries) == len(beginner_rows)
                and not teaching_grounding_failing_lesson_ids
                and teaching_turn_count == total_steps
                and teaching_turn_count == grounded_teaching_turn_count
                and teaching_turn_count == cited_teaching_turn_count
            ),
            "teaching_turn_count": teaching_turn_count,
            "grounded_teaching_turn_count": grounded_teaching_turn_count,
            "cited_teaching_turn_count": cited_teaching_turn_count,
            "failing_lesson_ids": teaching_grounding_failing_lesson_ids,
        },
        "hint_grounding_contract": {
            "ok": (
                len(summaries) == len(beginner_rows)
                and not hint_grounding_failing_lesson_ids
                and hint_turn_count == grounded_hint_turn_count
                and hint_turn_count == cited_hint_turn_count
            ),
            "hint_turn_count": hint_turn_count,
            "grounded_hint_turn_count": grounded_hint_turn_count,
            "cited_hint_turn_count": cited_hint_turn_count,
            "failing_lesson_ids": hint_grounding_failing_lesson_ids,
        },
        "input_surfaces": sorted(input_surfaces),
        "input_surface_step_counts": dict(sorted(input_surface_step_counts.items())),
        "backstage_lenses": sorted(backstage_lenses),
        "observable_control_count": len(observable_controls),
        "verification_kind_counts": dict(sorted(verification_kind_counts.items())),
    }


def _merge_counts(target: dict[str, int], raw: Any) -> None:
    if not isinstance(raw, dict):
        return
    for key, value in raw.items():
        name = str(key)
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        target[name] = target.get(name, 0) + count


def _transcript_inventory(errors: list[dict[str, Any]]) -> dict[str, Any]:
    transcript_root = Path(__file__).parent / "transcripts"
    fixture_paths = sorted(
        str(path.relative_to(transcript_root))
        for path in transcript_root.rglob("*.json")
        if path.is_file()
    )
    declared_paths = [meta.transcript_path for meta in CURRICULUM.values()]
    declared_set = set(declared_paths)
    fixture_set = set(fixture_paths)

    duplicate_paths = sorted(
        path for path in declared_set if declared_paths.count(path) > 1
    )
    missing_paths = sorted(declared_set - fixture_set)
    orphan_paths = sorted(fixture_set - declared_set)
    for path in duplicate_paths:
        errors.append(
            {
                "code": "transcript_path_duplicate",
                "transcript_path": path,
                "message": "A transcript_path must be claimed by exactly one LessonMeta row.",
            }
        )
    for path in missing_paths:
        errors.append(
            {
                "code": "transcript_path_missing",
                "transcript_path": path,
                "message": "LessonMeta.transcript_path points at a missing fixture.",
            }
        )
    for path in orphan_paths:
        errors.append(
            {
                "code": "transcript_fixture_orphaned",
                "transcript_path": path,
                "message": "Transcript fixture is not claimed by any LessonMeta row.",
            }
        )

    return {
        "root": str(transcript_root),
        "fixture_count": len(fixture_paths),
        "declared_count": len(declared_paths),
        "duplicate_paths": duplicate_paths,
        "missing_paths": missing_paths,
        "orphan_paths": orphan_paths,
        "ok": not duplicate_paths and not missing_paths and not orphan_paths,
    }


def _copy_truthfulness_contract(errors: list[dict[str, Any]]) -> dict[str, Any]:
    """Reject learner-facing copy that promises unwired runtime actions."""
    unsupported_debrief_auto_open_claims: list[dict[str, Any]] = []
    for lesson_id, meta in CURRICULUM.items():
        try:
            script = meta.script
        except (OSError, json.JSONDecodeError):
            continue
        hits = unsupported_debrief_auto_open_phrases(script)
        if hits:
            unsupported_debrief_auto_open_claims.append(
                {
                    "lesson_id": lesson_id,
                    "transcript_path": meta.transcript_path,
                    "phrases": hits,
                }
            )

    if unsupported_debrief_auto_open_claims:
        errors.append(
            {
                "code": "transcript_debrief_auto_open_unwired",
                "claims": unsupported_debrief_auto_open_claims,
                "message": (
                    "Learn copy must not promise automatic debrief opening until "
                    "the runtime and frontend own a proven open-debrief command."
                ),
            }
        )

    return {
        "unsupported_auto_open_phrases": list(
            SPECULATIVE_DEBRIEF_AUTO_OPEN_PHRASES
        ),
        "unsupported_debrief_auto_open_claims": unsupported_debrief_auto_open_claims,
        "ok": not unsupported_debrief_auto_open_claims,
    }

def _observed_course_capabilities(
    course_id: str,
    lesson_ids: tuple[str, ...],
    errors: list[dict[str, Any]],
) -> tuple[str, ...]:
    observed: set[str] = set()
    for lesson_id in lesson_ids:
        try:
            flow = build_lesson_flow(lesson_id)
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(
                {
                    "code": "course_capability_flow_compile_failed",
                    "course_id": course_id,
                    "lesson_id": lesson_id,
                    "message": str(exc),
                }
            )
            continue
        for lens in flow.backstage_lenses:
            capability = _FLOW_LENS_CAPABILITIES.get(str(lens))
            if capability is not None:
                observed.add(capability)
        for step in flow.steps:
            surfaces = set(step.verification.input_surfaces)
            if "screen" in surfaces:
                observed.add("on_screen_deck")
            if "hardware" in surfaces:
                observed.add("controller_state")
    return tuple(sorted(observed))


def _lesson_rows(
    errors: list[dict[str, Any]], beginner_ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    beginner_set = set(beginner_ids)
    for lesson_id, meta in CURRICULUM.items():
        transcript_status = _check_transcript(lesson_id, errors)
        flow_summary = (
            _check_flow_contract(lesson_id, errors) if lesson_id in beginner_set else None
        )
        rows.append(
            {
                "lesson_id": lesson_id,
                "course_id": meta.course_id,
                "title": meta.title,
                "transcript_path": meta.transcript_path,
                "beginner": lesson_id in beginner_set,
                "course_registered": meta.course_id in COURSE_REGISTRY,
                "transcript_ok": transcript_status,
                "flow_ok": flow_summary.get("ok") if isinstance(flow_summary, dict) else None,
                "flow_summary": flow_summary,
            }
        )
        if meta.course_id not in COURSE_REGISTRY:
            errors.append(
                {
                    "code": "lesson_course_unregistered",
                    "lesson_id": lesson_id,
                    "course_id": meta.course_id,
                    "message": "LessonMeta.course_id must exist in COURSE_REGISTRY.",
                }
            )
    return rows


def _check_transcript(lesson_id: str, errors: list[dict[str, Any]]) -> bool:
    meta = CURRICULUM[lesson_id]
    try:
        script = meta.script
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(
            {
                "code": "transcript_unreadable",
                "lesson_id": lesson_id,
                "transcript_path": meta.transcript_path,
                "message": str(exc),
            }
        )
        return False
    if not isinstance(script, dict):
        errors.append(
            {
                "code": "transcript_not_object",
                "lesson_id": lesson_id,
                "transcript_path": meta.transcript_path,
                "message": "Transcript JSON root must be an object.",
            }
        )
        return False

    ok = True
    checks = {
        "lesson_id": lesson_id,
        "title": meta.title,
        "system_instruction_addendum": meta.system_instruction_addendum,
    }
    for field, expected in checks.items():
        if script.get(field) != expected:
            ok = False
            errors.append(
                {
                    "code": "transcript_metadata_drift",
                    "lesson_id": lesson_id,
                    "field": field,
                    "expected": expected,
                    "actual": script.get(field),
                    "message": "Transcript metadata must match LessonMeta.",
                }
            )
    for field in ("tutor_speak", "expected_action", "hints"):
        if field not in script:
            ok = False
            errors.append(
                {
                    "code": "transcript_required_field_missing",
                    "lesson_id": lesson_id,
                    "field": field,
                    "message": "Transcript is missing a required lesson field.",
                }
            )
    return ok


def _check_flow_contract(lesson_id: str, errors: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        flow = build_lesson_flow(lesson_id)
    except (KeyError, ValueError, TypeError) as exc:
        errors.append(
            {
                "code": "lesson_flow_compile_failed",
                "lesson_id": lesson_id,
                "message": str(exc),
            }
        )
        return {
            "ok": False,
            "step_count": 0,
            "backstage_lenses": [],
            "input_surfaces": [],
            "observable_controls": [],
            "min_hint_count": 0,
            "teaching_grounding_contract": {
                "ok": False,
                "teaching_turn_count": 0,
                "grounded_teaching_turn_count": 0,
                "cited_teaching_turn_count": 0,
                "error_codes": ["lesson_flow_compile_failed"],
            },
            "hint_grounding_contract": {
                "ok": False,
                "hint_turn_count": 0,
                "grounded_hint_turn_count": 0,
                "cited_hint_turn_count": 0,
                "error_codes": ["lesson_flow_compile_failed"],
            },
            "error_codes": ["lesson_flow_compile_failed"],
        }

    error_codes: list[str] = []

    def add_error(code: str, step_id: str | None, message: str) -> None:
        error_codes.append(code)
        row: dict[str, Any] = {
            "code": code,
            "lesson_id": lesson_id,
            "message": message,
        }
        if step_id is not None:
            row["step_id"] = step_id
        errors.append(row)

    if not flow.steps:
        add_error(
            "lesson_flow_empty",
            None,
            "Beginner lesson flow compiled with zero steps.",
        )

    input_surfaces: set[str] = set()
    observable_controls: set[str] = set()
    min_hint_count = min((len(step.hints) for step in flow.steps), default=0)
    seen_step_ids: set[str] = set()
    verification_kind_counts: dict[str, int] = {}
    input_surface_step_counts: dict[str, int] = {}
    prompt_error_codes: list[str] = []
    prompt_exempt_step_ids: list[str] = []
    max_prompt_chars = 0
    max_prompt_words = 0
    max_prompt_sentences = 0
    teaching_turn_count = 0
    grounded_teaching_turn_count = 0
    cited_teaching_turn_count = 0
    teaching_grounding_error_codes: list[str] = []
    hint_turn_count = 0
    grounded_hint_turn_count = 0
    cited_hint_turn_count = 0
    hint_grounding_error_codes: list[str] = []
    for step in flow.steps:
        if step.step_id in seen_step_ids:
            add_error(
                "lesson_flow_duplicate_step_id",
                step.step_id,
                "Lesson flow step ids must be unique.",
            )
        seen_step_ids.add(step.step_id)
        if not step.step_id.startswith(f"{lesson_id}."):
            add_error(
                "lesson_flow_step_id_scope",
                step.step_id,
                "Lesson flow step id must be scoped to its lesson id.",
            )
        if not step.prompt.strip():
            add_error(
                "lesson_flow_step_prompt_missing",
                step.step_id,
                "Lesson flow step prompt must be authored.",
            )
            prompt_error_codes.append("lesson_flow_step_prompt_missing")
        prompt_exempt = frontstage_prompt_contract_exempt(step.step_id)
        if prompt_exempt:
            prompt_exempt_step_ids.append(step.step_id)
        prompt_metrics = frontstage_prompt_metrics(step.prompt)
        if not prompt_exempt:
            max_prompt_chars = max(max_prompt_chars, int(prompt_metrics["chars"]))
            max_prompt_words = max(max_prompt_words, int(prompt_metrics["words"]))
            max_prompt_sentences = max(
                max_prompt_sentences,
                int(prompt_metrics["sentences"]),
            )
        if (
            not prompt_exempt
            and int(prompt_metrics["chars"]) > MAX_FRONTSTAGE_PROMPT_CHARS
        ):
            code = "lesson_flow_step_prompt_too_long"
            add_error(
                code,
                step.step_id,
                "Frontstage prompts must stay short enough for one-action practice.",
            )
            prompt_error_codes.append(code)
        if (
            not prompt_exempt
            and int(prompt_metrics["words"]) > MAX_FRONTSTAGE_PROMPT_WORDS
        ):
            code = "lesson_flow_step_prompt_too_wordy"
            add_error(
                code,
                step.step_id,
                "Frontstage prompts must stay under the word cap.",
            )
            prompt_error_codes.append(code)
        if (
            not prompt_exempt
            and int(prompt_metrics["sentences"]) > MAX_FRONTSTAGE_PROMPT_SENTENCES
        ):
            code = "lesson_flow_step_prompt_too_many_sentences"
            add_error(
                code,
                step.step_id,
                "Frontstage prompts must not become multi-sentence mini-lessons.",
            )
            prompt_error_codes.append(code)
        if not prompt_exempt and prompt_metrics["single_line"] is not True:
            code = "lesson_flow_step_prompt_multiline"
            add_error(
                code,
                step.step_id,
                "Frontstage prompts must render as one line of authored copy.",
            )
            prompt_error_codes.append(code)
        if not prompt_exempt and prompt_metrics["has_inline_list"] is True:
            code = "lesson_flow_step_prompt_listlike"
            add_error(
                code,
                step.step_id,
                "Frontstage prompts must not contain inline bullet or numbered lists.",
            )
            prompt_error_codes.append(code)
        if not step.tts_marker.strip():
            add_error(
                "lesson_flow_step_tts_marker_missing",
                step.step_id,
                "Lesson flow step must carry a deterministic TTS marker.",
            )

        expected_control = str(step.expected_action.get("control") or "").strip()
        if not expected_control:
            add_error(
                "lesson_flow_expected_control_missing",
                step.step_id,
                "Lesson flow step expected_action must name an observable control.",
            )
        if step.verification.control != expected_control:
            add_error(
                "lesson_flow_verification_control_mismatch",
                step.step_id,
                "Verification control must match expected_action.control.",
            )
        verification_kind = str(step.verification.kind)
        verification_kind_counts[verification_kind] = (
            verification_kind_counts.get(verification_kind, 0) + 1
        )
        if verification_kind not in {"button_press", "cc_delta"}:
            add_error(
                "lesson_flow_verification_kind_unknown",
                step.step_id,
                "Verification kind must be button_press or cc_delta.",
            )
        if verification_kind == "button_press" and step.verification.direction not in {
            "",
            "up",
            "down",
        }:
            add_error(
                "lesson_flow_button_direction_unknown",
                step.step_id,
                "Button verification direction must be empty, up, or down.",
            )
        if verification_kind == "cc_delta" and step.verification.min_delta <= 0:
            add_error(
                "lesson_flow_cc_delta_not_positive",
                step.step_id,
                "CC verification must carry a positive min_delta.",
            )
        if not step.verification.observable_control_ids:
            add_error(
                "lesson_flow_observable_controls_missing",
                step.step_id,
                "Verification must expose at least one observable control id.",
            )
        observable_controls.update(step.verification.observable_control_ids)

        surfaces = set(step.verification.input_surfaces)
        if not surfaces:
            add_error(
                "lesson_flow_input_surface_missing",
                step.step_id,
                "Verification must declare at least one input surface.",
            )
        unknown_surfaces = sorted(surfaces - {"hardware", "screen"})
        if unknown_surfaces:
            add_error(
                "lesson_flow_input_surface_unknown",
                step.step_id,
                f"Verification declares unknown input surfaces: {unknown_surfaces}",
            )
        input_surfaces.update(surfaces)
        surface_key = "+".join(step.verification.input_surfaces)
        input_surface_step_counts[surface_key] = (
            input_surface_step_counts.get(surface_key, 0) + 1
        )

        teaching_turn_count += 1
        teaching_turn = plan_teaching_turn(
            lesson_id=lesson_id,
            step=step,
        )
        if teaching_turn_is_grounded(teaching_turn):
            grounded_teaching_turn_count += 1
            if teaching_turn.citations:
                cited_teaching_turn_count += 1
            else:
                code = "lesson_flow_teaching_turn_uncited"
                add_error(
                    code,
                    step.step_id,
                    "Teaching turns must carry a deterministic control citation.",
                )
                teaching_grounding_error_codes.append(code)
        else:
            code = "lesson_flow_teaching_turn_not_grounded"
            add_error(
                code,
                step.step_id,
                "Teaching turns must retain lesson, control, and verification ground.",
            )
            teaching_grounding_error_codes.append(code)

        if len(step.hints) < 3:
            add_error(
                "lesson_flow_adaptive_hints_too_few",
                step.step_id,
                "Every beginner lesson step must expose at least three adaptive hints.",
            )
        for strike, hint in enumerate(step.hints[:3], start=1):
            hint_turn_count += 1
            if hint.strike != strike:
                code = "lesson_flow_adaptive_hint_strike_mismatch"
                add_error(
                    code,
                    step.step_id,
                    "Adaptive hints must use deterministic strike positions one, two, three.",
                )
                hint_grounding_error_codes.append(code)
            if not hint.text.strip() or not hint.tts_marker.strip():
                code = "lesson_flow_adaptive_hint_incomplete"
                add_error(
                    code,
                    step.step_id,
                    "Adaptive hints must carry authored text and a deterministic TTS marker.",
                )
                hint_grounding_error_codes.append(code)
            turn = plan_hint_turn(lesson_id=lesson_id, step=step, strike=strike)
            if turn is None:
                code = "lesson_flow_adaptive_hint_turn_missing"
                add_error(
                    code,
                    step.step_id,
                    "Adaptive hints must compile into first-class teaching-loop turns.",
                )
                hint_grounding_error_codes.append(code)
            elif teaching_turn_is_grounded(turn):
                grounded_hint_turn_count += 1
                if turn.citations:
                    cited_hint_turn_count += 1
                else:
                    code = "lesson_flow_adaptive_hint_turn_uncited"
                    add_error(
                        code,
                        step.step_id,
                        "Adaptive hint turns must carry a deterministic control citation.",
                    )
                    hint_grounding_error_codes.append(code)
            else:
                code = "lesson_flow_adaptive_hint_turn_not_grounded"
                add_error(
                    code,
                    step.step_id,
                    "Adaptive hint turns must retain lesson, control, and verification ground.",
                )
                hint_grounding_error_codes.append(code)

    return {
        "ok": not error_codes,
        "step_count": len(flow.steps),
        "backstage_lenses": list(flow.backstage_lenses),
        "input_surfaces": sorted(input_surfaces),
        "input_surface_step_counts": dict(sorted(input_surface_step_counts.items())),
        "observable_controls": sorted(observable_controls),
        "min_hint_count": min_hint_count,
        "prompt_contract": {
            "ok": not prompt_error_codes,
            "max_chars": MAX_FRONTSTAGE_PROMPT_CHARS,
            "max_words": MAX_FRONTSTAGE_PROMPT_WORDS,
            "max_sentences": MAX_FRONTSTAGE_PROMPT_SENTENCES,
            "single_line": True,
            "inline_lists_forbidden": True,
            "observed_max_chars": max_prompt_chars,
            "observed_max_words": max_prompt_words,
            "observed_max_sentences": max_prompt_sentences,
            "exempt_step_ids": prompt_exempt_step_ids,
            "error_codes": sorted(set(prompt_error_codes)),
        },
        "teaching_grounding_contract": {
            "ok": not teaching_grounding_error_codes
            and teaching_turn_count == grounded_teaching_turn_count
            and teaching_turn_count == cited_teaching_turn_count,
            "teaching_turn_count": teaching_turn_count,
            "grounded_teaching_turn_count": grounded_teaching_turn_count,
            "cited_teaching_turn_count": cited_teaching_turn_count,
            "error_codes": sorted(set(teaching_grounding_error_codes)),
        },
        "hint_grounding_contract": {
            "ok": not hint_grounding_error_codes
            and hint_turn_count == grounded_hint_turn_count
            and hint_turn_count == cited_hint_turn_count,
            "hint_turn_count": hint_turn_count,
            "grounded_hint_turn_count": grounded_hint_turn_count,
            "cited_hint_turn_count": cited_hint_turn_count,
            "error_codes": sorted(set(hint_grounding_error_codes)),
        },
        "verification_kind_counts": dict(sorted(verification_kind_counts.items())),
        "error_codes": sorted(set(error_codes)),
    }


def _frontend_projection_check(
    frontend_path: Path | None,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    if frontend_path is None:
        return {"checked": False, "up_to_date": None, "path": None}
    expected = render_curriculum_meta_ts()
    if not frontend_path.exists():
        errors.append(
            {
                "code": "frontend_projection_missing",
                "path": str(frontend_path),
                "message": "Frontend curriculum projection was not found.",
            }
        )
        return {"checked": True, "up_to_date": False, "path": str(frontend_path)}
    current = frontend_path.read_text(encoding="utf-8")
    up_to_date = current == expected
    if not up_to_date:
        errors.append(
            {
                "code": "frontend_projection_stale",
                "path": str(frontend_path),
                "message": "Run npm --prefix tauri/ui run codegen:learn.",
            }
        )
    return {"checked": True, "up_to_date": up_to_date, "path": str(frontend_path)}
