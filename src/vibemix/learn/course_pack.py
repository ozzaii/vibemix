# SPDX-License-Identifier: Apache-2.0
"""Executable preflight for future Learn course packs.

The shipped beginner module is authored directly in ``curriculum.py`` plus the
JSON transcript fixtures. This module validates the same shape for a draft
course before that course is merged into the global tables. It deliberately
does not write files or mutate ``COURSE_REGISTRY`` / ``CURRICULUM``: the value
is an honest backstage check that says "this future course will compile through
the same lesson-flow machinery" without turning the Learn UI into a course
builder.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vibemix.learn.copy_truth import unsupported_debrief_auto_open_phrases
from vibemix.learn.curriculum import (
    COURSE_CAPABILITIES,
    COURSE_FRAMES,
    COURSE_FRONTSTAGE_MODES,
    COURSE_REGISTRY,
    CURRICULUM,
    CourseMeta,
    LessonMeta,
)
from vibemix.learn.lesson_flow import (
    MAX_FRONTSTAGE_PROMPT_CHARS,
    MAX_FRONTSTAGE_PROMPT_SENTENCES,
    MAX_FRONTSTAGE_PROMPT_WORDS,
    build_lesson_flow_from_meta,
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

_UNLOCK_GATE_RE = re.compile(r"^course_[a-z0-9_]+_unlocked$")
_COURSE_PACK_ID_RE = re.compile(
    r"^course_(?P<number>[1-9][0-9]*)_[a-z0-9][a-z0-9_]*$"
)
_LESSON_ID_RE = re.compile(r"^L(?P<number>[1-9][0-9]*)\.(?P<ordinal>[0-9]{2})$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
_AUTHORING_FRONTSTAGE = "one prompt, one action, one grounded response"
_AUTHORING_COPY_RULES = (
    "cite the observable control on every teaching and hint turn",
    "do not promise automatic debrief opening",
)
_AUTHORING_POST_MERGE_COMMANDS = (
    "uv run python scripts/export_learn_curriculum_meta.py --check",
    "uv run pytest -q tests/learn/test_course_pack.py",
    (
        "uv run python scripts/run_learn_perfection_package.py --out "
        "/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json"
    ),
)


@dataclass(frozen=True, slots=True)
class CoursePackValidationError:
    """One machine-readable course-pack preflight failure."""

    code: str
    message: str
    course_id: str | None = None
    lesson_id: str | None = None
    field: str | None = None
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        row = {
            "code": self.code,
            "message": self.message,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
        }
        return {key: value for key, value in row.items() if value is not None}


@dataclass(frozen=True, slots=True)
class CoursePackValidation:
    """Result of validating a draft course pack."""

    course_id: str
    ok: bool
    lesson_count: int
    step_count: int
    flow_preview: tuple[dict[str, Any], ...]
    observed_capabilities: tuple[str, ...]
    required_progress_fields: tuple[str, ...]
    integration_plan: dict[str, Any]
    prompt_contract: dict[str, Any]
    teaching_grounding_contract: dict[str, Any]
    hint_grounding_contract: dict[str, Any]
    authoring_contract: dict[str, Any]
    copy_truthfulness: dict[str, Any]
    errors: tuple[CoursePackValidationError, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_id": self.course_id,
            "ok": self.ok,
            "lesson_count": self.lesson_count,
            "step_count": self.step_count,
            "flow_preview": list(self.flow_preview),
            "observed_capabilities": list(self.observed_capabilities),
            "required_progress_fields": list(self.required_progress_fields),
            "integration_plan": self.integration_plan,
            "prompt_contract": self.prompt_contract,
            "teaching_grounding_contract": self.teaching_grounding_contract,
            "hint_grounding_contract": self.hint_grounding_contract,
            "authoring_contract": self.authoring_contract,
            "copy_truthfulness": self.copy_truthfulness,
            "errors": [error.to_dict() for error in self.errors],
        }


@dataclass(frozen=True, slots=True)
class CoursePackDraft:
    """Loaded JSON course-pack draft ready for validation."""

    course_id: str
    meta: CourseMeta
    frame: str
    lessons: dict[str, LessonMeta]
    scripts: dict[str, dict[str, Any]]
    authoring_contract: Any = None


def course_pack_template(
    *,
    course_number: int,
    slug: str,
    lesson_count: int = 1,
) -> dict[str, Any]:
    """Return a minimal canonical course-pack draft that validates as-is."""
    if course_number < 1:
        raise ValueError("course_number must be positive")
    if lesson_count < 1:
        raise ValueError("lesson_count must be positive")
    if _SLUG_RE.fullmatch(slug) is None:
        raise ValueError("slug must use lowercase letters, digits, and underscores")

    course_id = f"course_{course_number}_{slug}"
    title_words = slug.replace("_", " ")
    addendum = (
        f"{slug.upper()} ADDENDUM: give one clear prompt, verify one visible "
        "DJ action, and adapt from evidence."
    )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "course_id": course_id,
        "label": f"Course {course_number} - {title_words.title()}",
        "hud_label": f"COURSE {course_number} - {title_words.upper()}",
        "frame": (
            f"Course {course_number} keeps the same one-action practice-booth "
            "contract."
        ),
        "frontstage_mode": "practice_booth",
        "capabilities": ["evidence_registry", "controller_state", "on_screen_deck"],
        "authoring_contract": _starter_authoring_contract(),
        "lessons": [],
    }
    transcripts: dict[str, dict[str, Any]] = {}
    for ordinal in range(1, lesson_count + 1):
        lesson_id = f"L{course_number}.{ordinal:02d}"
        lesson_title = f"{title_words} lesson {ordinal}"
        transcript_path = f"{course_id}/{ordinal:02d}_{slug}.json"
        manifest["lessons"].append(
            {
                "lesson_id": lesson_id,
                "title": lesson_title,
                "system_instruction_addendum": addendum,
                "transcript_path": transcript_path,
            }
        )
        transcripts[transcript_path] = {
            "lesson_id": lesson_id,
            "title": lesson_title,
            "system_instruction_addendum": addendum,
            "tutor_speak": [
                {
                    "text": "press deck A cue once.",
                    "tts_marker": f"L{course_number}{ordinal:02d}.beat0",
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
                    "tts_marker": f"L{course_number}{ordinal:02d}.hint1",
                    "citations": ["[screen:cue:A]"],
                },
                {
                    "text": "stay on deck A, then press cue.",
                    "tts_marker": f"L{course_number}{ordinal:02d}.hint2",
                    "citations": ["[screen:cue:A]"],
                },
                {
                    "text": "press the lit cue control.",
                    "tts_marker": f"L{course_number}{ordinal:02d}.hint3",
                    "citations": ["[screen:cue:A]"],
                },
            ],
        }
    return {
        "schema_version": 1,
        "manifest": manifest,
        "transcripts": transcripts,
    }


def _starter_authoring_contract() -> dict[str, Any]:
    """Return the authoring rules every generated starter manifest carries."""
    return {
        "frontstage": _AUTHORING_FRONTSTAGE,
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
        "copy_rules": list(_AUTHORING_COPY_RULES),
        "post_merge_commands": list(_AUTHORING_POST_MERGE_COMMANDS),
    }


def write_course_pack_template(
    out_dir: Path,
    *,
    course_number: int,
    slug: str,
    lesson_count: int = 1,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a canonical starter course pack and validate it immediately."""
    template = course_pack_template(
        course_number=course_number,
        slug=slug,
        lesson_count=lesson_count,
    )
    out_dir = out_dir.expanduser().resolve()
    manifest_path = out_dir / "course-pack.json"
    writes: dict[Path, dict[str, Any]] = {manifest_path: template["manifest"]}
    for rel_path, transcript in template["transcripts"].items():
        writes[out_dir / str(rel_path)] = transcript

    existing = [path for path in writes if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "course-pack template would overwrite existing files: "
            + ", ".join(str(path) for path in existing)
        )

    for path, payload in writes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    validation = validate_course_pack_manifest(manifest_path, transcript_root=out_dir)
    return {
        "ok": validation.ok,
        "manifest_path": str(manifest_path),
        "transcript_paths": sorted(
            str(out_dir / str(rel_path))
            for rel_path in template["transcripts"]
        ),
        "validation": validation.to_dict(),
    }


def validate_course_pack_manifest(
    manifest_path: Path,
    *,
    transcript_root: Path | None = None,
) -> CoursePackValidation:
    """Load and validate a JSON course-pack draft from disk."""
    try:
        draft = load_course_pack_manifest(
            manifest_path,
            transcript_root=transcript_root,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        course_id = _manifest_course_id_fallback(manifest_path)
        return CoursePackValidation(
            course_id=course_id,
            ok=False,
            lesson_count=0,
            step_count=0,
            flow_preview=(),
            observed_capabilities=(),
            required_progress_fields=(),
            integration_plan=_integration_plan(
                course_id,
                None,
                "",
                {},
                ok=False,
                required_progress_fields=(),
            ),
            prompt_contract=_prompt_contract_summary([], []),
            teaching_grounding_contract=_teaching_grounding_contract_summary([], []),
            hint_grounding_contract=_hint_grounding_contract_summary([], []),
            authoring_contract=_authoring_contract_summary(
                None,
                required=True,
                errors=[],
            ),
            copy_truthfulness={
                "ok": False,
                "unsupported_debrief_auto_open_claims": [],
            },
            errors=(
                CoursePackValidationError(
                    code="draft_manifest_invalid",
                    message=str(exc),
                    course_id=course_id,
                    field="manifest",
                    actual=str(manifest_path),
                ),
            ),
        )
    return validate_course_pack_draft(
        course_id=draft.course_id,
        meta=draft.meta,
        frame=draft.frame,
        lessons=draft.lessons,
        scripts=draft.scripts,
        authoring_contract=draft.authoring_contract,
        require_authoring_contract=True,
    )


def load_course_pack_manifest(
    manifest_path: Path,
    *,
    transcript_root: Path | None = None,
) -> CoursePackDraft:
    """Load a JSON course-pack draft without mutating the app curriculum.

    Manifest shape:

    ``schema_version``
        Must be ``1``.
    ``course_id``, ``label``, ``hud_label``, ``frame``
        Required course metadata.
    ``unlock_gate``, ``lock_reason``, ``beginner``, ``frontstage_mode``,
    ``capabilities``
        Optional/standard :class:`CourseMeta` fields.
    ``lessons``
        List of rows with ``lesson_id``, ``title``,
        ``system_instruction_addendum``, and ``transcript_path``. The
        ``transcript_path`` is the future ``LessonMeta.transcript_path`` value;
        the CLI reads it relative to ``transcript_root`` when supplied, otherwise
        relative to the manifest directory.
    """
    manifest_path = manifest_path.expanduser().resolve()
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("course-pack manifest root must be an object")
    if raw.get("schema_version") != 1:
        raise ValueError("course-pack manifest schema_version must be 1")

    course_id = _required_string(raw, "course_id")
    meta = CourseMeta(
        label=_required_string(raw, "label"),
        hud_label=_required_string(raw, "hud_label"),
        unlock_gate=_optional_string(raw, "unlock_gate"),
        lock_reason=_optional_string(raw, "lock_reason"),
        beginner=bool(raw.get("beginner", False)),
        frontstage_mode=str(raw.get("frontstage_mode") or "practice_booth"),
        capabilities=tuple(
            str(capability)
            for capability in _required_list(raw, "capabilities")
        ),
    )
    frame = _required_string(raw, "frame")
    lesson_rows = _required_list(raw, "lessons")
    root = transcript_root.expanduser().resolve() if transcript_root else manifest_path.parent
    lessons: dict[str, LessonMeta] = {}
    scripts: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(lesson_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"lessons[{idx}] must be an object")
        lesson_id = _required_string(row, "lesson_id")
        transcript_path = _required_string(row, "transcript_path")
        if lesson_id in lessons:
            raise ValueError(f"duplicate lesson_id {lesson_id!r} in manifest")
        lessons[lesson_id] = LessonMeta(
            title=_required_string(row, "title"),
            course_id=str(row.get("course_id") or course_id),
            system_instruction_addendum=_required_string(
                row,
                "system_instruction_addendum",
            ),
            transcript_path=transcript_path,
        )
        scripts[lesson_id] = _read_transcript_script(root / transcript_path, lesson_id)

    return CoursePackDraft(
        course_id=course_id,
        meta=meta,
        frame=frame,
        lessons=lessons,
        scripts=scripts,
        authoring_contract=raw.get("authoring_contract"),
    )


def validate_course_pack_draft(
    *,
    course_id: str,
    meta: CourseMeta,
    frame: str,
    lessons: Mapping[str, LessonMeta],
    scripts: Mapping[str, Mapping[str, Any]],
    authoring_contract: Mapping[str, Any] | None = None,
    require_authoring_contract: bool = False,
) -> CoursePackValidation:
    """Validate a draft course against the same contracts as shipped lessons.

    Args:
        course_id: Proposed ``COURSE_REGISTRY`` key.
        meta: Proposed course metadata.
        frame: Proposed ``COURSE_FRAMES[course_id]`` text.
        lessons: Proposed ``CURRICULUM`` rows for the course.
        scripts: Already-loaded transcript JSON objects, keyed by lesson id.

    Returns:
        A JSON-safe validation object. ``ok=True`` means the course draft has
        no id/path collisions, every transcript aligns with its ``LessonMeta``,
        all lessons compile through the canonical structured-flow compiler, and
        the course capabilities cover the observed backstage/input surfaces.
    """
    errors: list[CoursePackValidationError] = []
    observed_capabilities: set[str] = set()
    required_progress_fields: set[str] = set()
    unsupported_copy_claims: list[dict[str, Any]] = []
    flow_preview: list[dict[str, Any]] = []
    grounding_rows: list[dict[str, Any]] = []
    step_count = 0

    _check_course_shape(course_id, meta, frame, lessons, errors)
    _check_unlock_gate(course_id, meta, required_progress_fields, errors)
    _check_lesson_paths(course_id, lessons, errors)
    authoring_contract_summary = _authoring_contract_summary(
        authoring_contract,
        required=require_authoring_contract,
        errors=errors,
        course_id=course_id,
    )

    for lesson_id, lesson_meta in lessons.items():
        script = scripts.get(lesson_id)
        if not isinstance(script, Mapping):
            errors.append(
                CoursePackValidationError(
                    code="draft_transcript_missing",
                    message="Every LessonMeta row needs a matching transcript object.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                )
            )
            continue
        _check_transcript_metadata(course_id, lesson_id, lesson_meta, script, errors)
        _check_transcript_fields(course_id, lesson_id, script, errors)
        _check_transcript_truthfulness(
            course_id,
            lesson_id,
            script,
            errors,
            unsupported_copy_claims,
        )
        if any(error.lesson_id == lesson_id for error in errors):
            continue
        try:
            flow = build_lesson_flow_from_meta(
                lesson_id,
                lesson_meta,
                dict(script),
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(
                CoursePackValidationError(
                    code="draft_flow_compile_failed",
                    message=str(exc),
                    course_id=course_id,
                    lesson_id=lesson_id,
                )
            )
            continue
        step_count += len(flow.steps)
        observed_capabilities.update(_observed_capabilities_for_flow(flow))
        flow_preview.append(_flow_preview_row(flow))
        _check_flow_prompt_contract(course_id, lesson_id, flow, errors)
        grounding_rows.append(
            _check_flow_grounding_contract(course_id, lesson_id, flow, errors)
        )

    missing_capabilities = sorted(observed_capabilities - set(meta.capabilities))
    for capability in missing_capabilities:
        errors.append(
            CoursePackValidationError(
                code="draft_capability_missing_for_flow",
                message=(
                    "CourseMeta.capabilities must cover the draft lesson flow's "
                    "backstage requirements."
                ),
                course_id=course_id,
                field="capabilities",
                expected=capability,
                actual=list(meta.capabilities),
            )
        )

    return CoursePackValidation(
        course_id=course_id,
        ok=not errors,
        lesson_count=len(lessons),
        step_count=step_count,
        flow_preview=tuple(flow_preview),
        observed_capabilities=tuple(sorted(observed_capabilities)),
        required_progress_fields=tuple(sorted(required_progress_fields)),
        integration_plan=_integration_plan(
            course_id,
            meta,
            frame,
            lessons,
            ok=not errors,
            required_progress_fields=tuple(sorted(required_progress_fields)),
        ),
        prompt_contract=_prompt_contract_summary(flow_preview, errors),
        teaching_grounding_contract=_teaching_grounding_contract_summary(
            grounding_rows,
            errors,
        ),
        hint_grounding_contract=_hint_grounding_contract_summary(grounding_rows, errors),
        authoring_contract=authoring_contract_summary,
        copy_truthfulness={
            "ok": not unsupported_copy_claims,
            "unsupported_debrief_auto_open_claims": unsupported_copy_claims,
        },
        errors=tuple(errors),
    )


def _check_course_shape(
    course_id: str,
    meta: CourseMeta,
    frame: str,
    lessons: Mapping[str, LessonMeta],
    errors: list[CoursePackValidationError],
) -> None:
    if not course_id.strip():
        errors.append(
            CoursePackValidationError(
                code="draft_course_id_empty",
                message="A course pack needs a non-empty course_id.",
                course_id=course_id,
                field="course_id",
            )
        )
    elif _COURSE_PACK_ID_RE.fullmatch(course_id) is None:
        errors.append(
            CoursePackValidationError(
                code="draft_course_id_not_canonical",
                message="course_id must look like course_<number>_<slug>.",
                course_id=course_id,
                field="course_id",
                expected="course_<number>_<slug>",
                actual=course_id,
            )
        )
    if course_id in COURSE_REGISTRY or course_id in COURSE_FRAMES:
        errors.append(
            CoursePackValidationError(
                code="draft_course_id_collision",
                message="Draft course_id already exists in the shipped registry.",
                course_id=course_id,
                field="course_id",
            )
        )
    if meta.frontstage_mode not in COURSE_FRONTSTAGE_MODES:
        errors.append(
            CoursePackValidationError(
                code="draft_frontstage_mode_unknown",
                message="CourseMeta.frontstage_mode must be a known mode.",
                course_id=course_id,
                field="frontstage_mode",
                actual=meta.frontstage_mode,
            )
        )
    unknown_capabilities = sorted(set(meta.capabilities) - set(COURSE_CAPABILITIES))
    for capability in unknown_capabilities:
        errors.append(
            CoursePackValidationError(
                code="draft_capability_unknown",
                message="CourseMeta.capabilities contains an unknown capability.",
                course_id=course_id,
                field="capabilities",
                actual=capability,
            )
        )
    if not meta.capabilities:
        errors.append(
            CoursePackValidationError(
                code="draft_capabilities_empty",
                message="Every course must declare at least one capability.",
                course_id=course_id,
                field="capabilities",
            )
        )
    if not frame.strip():
        errors.append(
            CoursePackValidationError(
                code="draft_frame_empty",
                message="Every course needs a non-empty course frame.",
                course_id=course_id,
                field="frame",
            )
        )
    if not lessons:
        errors.append(
            CoursePackValidationError(
                code="draft_course_has_no_lessons",
                message="Every course pack needs at least one lesson.",
                course_id=course_id,
            )
        )


def _check_unlock_gate(
    course_id: str,
    meta: CourseMeta,
    required_progress_fields: set[str],
    errors: list[CoursePackValidationError],
) -> None:
    gate = meta.unlock_gate
    if gate is None:
        return
    if not gate.strip() or _UNLOCK_GATE_RE.fullmatch(gate) is None:
        errors.append(
            CoursePackValidationError(
                code="draft_unlock_gate_invalid",
                message="unlock_gate must look like course_<name>_unlocked.",
                course_id=course_id,
                field="unlock_gate",
                actual=gate,
            )
        )
    if not meta.lock_reason:
        errors.append(
            CoursePackValidationError(
                code="draft_unlock_gate_missing_lock_reason",
                message="Locked courses need learner-facing lock_reason copy.",
                course_id=course_id,
                field="lock_reason",
            )
        )
    if gate not in LearnProgress().to_dict():
        required_progress_fields.add(gate)


def _check_lesson_paths(
    course_id: str,
    lessons: Mapping[str, LessonMeta],
    errors: list[CoursePackValidationError],
) -> None:
    existing_paths = {meta.transcript_path for meta in CURRICULUM.values()}
    draft_paths: list[str] = []
    course_number = _course_number(course_id)
    lesson_ordinals: list[int] = []
    for lesson_id, meta in lessons.items():
        if lesson_id in CURRICULUM:
            errors.append(
                CoursePackValidationError(
                    code="draft_lesson_id_collision",
                    message="Draft lesson_id already exists in the shipped curriculum.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field="lesson_id",
                )
            )
        lesson_match = _LESSON_ID_RE.fullmatch(lesson_id)
        if lesson_match is None:
            errors.append(
                CoursePackValidationError(
                    code="draft_lesson_id_not_canonical",
                    message="lesson_id must look like L<number>.<two digits>.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field="lesson_id",
                    expected="L<number>.<two digits>",
                    actual=lesson_id,
                )
            )
        else:
            lesson_number = lesson_match.group("number")
            lesson_ordinals.append(int(lesson_match.group("ordinal")))
            if course_number is not None and lesson_number != course_number:
                errors.append(
                    CoursePackValidationError(
                        code="draft_lesson_id_course_number_mismatch",
                        message="lesson_id course number must match course_id.",
                        course_id=course_id,
                        lesson_id=lesson_id,
                        field="lesson_id",
                        expected=f"L{course_number}.<two digits>",
                        actual=lesson_id,
                    )
                )
        if meta.course_id != course_id:
            errors.append(
                CoursePackValidationError(
                    code="draft_lesson_course_mismatch",
                    message="LessonMeta.course_id must match the draft course_id.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field="course_id",
                    expected=course_id,
                    actual=meta.course_id,
                )
            )
        draft_paths.append(meta.transcript_path)
        if meta.transcript_path in existing_paths:
            errors.append(
                CoursePackValidationError(
                    code="draft_transcript_path_collision",
                    message="Draft transcript_path would overwrite a shipped fixture.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field="transcript_path",
                    actual=meta.transcript_path,
                )
            )
    for path in sorted({path for path in draft_paths if draft_paths.count(path) > 1}):
        errors.append(
            CoursePackValidationError(
                code="draft_transcript_path_duplicate",
                message="Draft transcript_path must be unique within the course pack.",
                course_id=course_id,
                field="transcript_path",
                actual=path,
            )
        )
    expected_ordinals = list(range(1, len(lesson_ordinals) + 1))
    if lesson_ordinals and sorted(lesson_ordinals) != expected_ordinals:
        errors.append(
            CoursePackValidationError(
                code="draft_lesson_ids_not_contiguous",
                message="Draft lesson_id ordinals must be contiguous from .01.",
                course_id=course_id,
                field="lesson_id",
                expected=expected_ordinals,
                actual=sorted(lesson_ordinals),
            )
        )


def _check_transcript_metadata(
    course_id: str,
    lesson_id: str,
    meta: LessonMeta,
    script: Mapping[str, Any],
    errors: list[CoursePackValidationError],
) -> None:
    expected = {
        "lesson_id": lesson_id,
        "title": meta.title,
        "system_instruction_addendum": meta.system_instruction_addendum,
    }
    for field, expected_value in expected.items():
        if script.get(field) != expected_value:
            errors.append(
                CoursePackValidationError(
                    code="draft_transcript_metadata_drift",
                    message="Transcript metadata must stay byte-aligned to LessonMeta.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=field,
                    expected=expected_value,
                    actual=script.get(field),
                )
            )


def _check_transcript_fields(
    course_id: str,
    lesson_id: str,
    script: Mapping[str, Any],
    errors: list[CoursePackValidationError],
) -> None:
    tutor_speak = script.get("tutor_speak")
    if not isinstance(tutor_speak, list) or not tutor_speak:
        errors.append(
            CoursePackValidationError(
                code="draft_tutor_speak_missing",
                message="Transcript needs at least one tutor_speak row.",
                course_id=course_id,
                lesson_id=lesson_id,
                field="tutor_speak",
            )
        )
    expected_action = script.get("expected_action")
    if not isinstance(expected_action, Mapping):
        errors.append(
            CoursePackValidationError(
                code="draft_expected_action_missing",
                message="Transcript expected_action must be an object.",
                course_id=course_id,
                lesson_id=lesson_id,
                field="expected_action",
            )
        )
    elif not expected_action.get("type") or not expected_action.get("control"):
        errors.append(
            CoursePackValidationError(
                code="draft_expected_action_incomplete",
                message="expected_action needs type and control.",
                course_id=course_id,
                lesson_id=lesson_id,
                field="expected_action",
            )
        )
    hints = script.get("hints")
    if not isinstance(hints, list) or len(hints) < 3:
        errors.append(
            CoursePackValidationError(
                code="draft_hints_too_few",
                message="Every lesson needs at least three adaptive hints.",
                course_id=course_id,
                lesson_id=lesson_id,
                field="hints",
                expected=3,
                actual=len(hints) if isinstance(hints, list) else 0,
            )
        )
        return
    for idx, hint in enumerate(hints[:3], start=1):
        if not isinstance(hint, Mapping) or not str(hint.get("text", "")).strip():
            errors.append(
                CoursePackValidationError(
                    code="draft_hint_text_missing",
                    message="The first three hints need learner-facing text.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"hints[{idx - 1}].text",
                )
            )


def _check_transcript_truthfulness(
    course_id: str,
    lesson_id: str,
    script: Mapping[str, Any],
    errors: list[CoursePackValidationError],
    unsupported_claims: list[dict[str, Any]],
) -> None:
    hits = unsupported_debrief_auto_open_phrases(script)
    if not hits:
        return
    unsupported_claims.append(
        {
            "lesson_id": lesson_id,
            "phrases": list(hits),
        }
    )
    errors.append(
        CoursePackValidationError(
            code="draft_transcript_debrief_auto_open_unwired",
            message=(
                "Draft transcript copy must not promise automatic debrief "
                "opening until Learn owns a proven open-debrief command."
            ),
            course_id=course_id,
            lesson_id=lesson_id,
            field="learner_copy",
            expected="no unsupported debrief auto-open promise",
            actual=list(hits),
        )
    )


def _observed_capabilities_for_flow(flow: Any) -> set[str]:
    observed: set[str] = set()
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
    return observed


def _check_flow_prompt_contract(
    course_id: str,
    lesson_id: str,
    flow: Any,
    errors: list[CoursePackValidationError],
) -> None:
    for step in flow.steps:
        metrics = frontstage_prompt_metrics(str(step.prompt))
        step_id = str(step.step_id)
        if int(metrics["chars"]) > MAX_FRONTSTAGE_PROMPT_CHARS:
            errors.append(
                CoursePackValidationError(
                    code="draft_frontstage_prompt_too_long",
                    message="Frontstage prompts must stay short enough for one action.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].prompt",
                    expected=f"<= {MAX_FRONTSTAGE_PROMPT_CHARS} chars",
                    actual=metrics["chars"],
                )
            )
        if int(metrics["words"]) > MAX_FRONTSTAGE_PROMPT_WORDS:
            errors.append(
                CoursePackValidationError(
                    code="draft_frontstage_prompt_too_wordy",
                    message="Frontstage prompts must stay under the word cap.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].prompt",
                    expected=f"<= {MAX_FRONTSTAGE_PROMPT_WORDS} words",
                    actual=metrics["words"],
                )
            )
        if int(metrics["sentences"]) > MAX_FRONTSTAGE_PROMPT_SENTENCES:
            errors.append(
                CoursePackValidationError(
                    code="draft_frontstage_prompt_too_many_sentences",
                    message="Frontstage prompts must not become mini-lessons.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].prompt",
                    expected=f"<= {MAX_FRONTSTAGE_PROMPT_SENTENCES} sentences",
                    actual=metrics["sentences"],
                )
            )
        if metrics["single_line"] is not True:
            errors.append(
                CoursePackValidationError(
                    code="draft_frontstage_prompt_multiline",
                    message="Frontstage prompts must be one line.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].prompt",
                    expected="single line",
                    actual="multiline",
                )
            )
        if metrics["has_inline_list"] is True:
            errors.append(
                CoursePackValidationError(
                    code="draft_frontstage_prompt_listlike",
                    message="Frontstage prompts must not contain inline lists.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].prompt",
                    expected="no inline lists",
                    actual="list-like prompt",
                )
            )


def _check_flow_grounding_contract(
    course_id: str,
    lesson_id: str,
    flow: Any,
    errors: list[CoursePackValidationError],
) -> dict[str, Any]:
    row = {
        "lesson_id": lesson_id,
        "teaching_turn_count": 0,
        "grounded_teaching_turn_count": 0,
        "cited_teaching_turn_count": 0,
        "hint_turn_count": 0,
        "grounded_hint_turn_count": 0,
        "cited_hint_turn_count": 0,
    }
    for step in flow.steps:
        step_id = str(step.step_id)
        row["teaching_turn_count"] += 1
        teaching_turn = plan_teaching_turn(lesson_id=lesson_id, step=step)
        if teaching_turn_is_grounded(teaching_turn):
            row["grounded_teaching_turn_count"] += 1
        else:
            errors.append(
                CoursePackValidationError(
                    code="draft_teaching_turn_not_grounded",
                    message=(
                        "Every course-pack teaching turn must resolve through "
                        "the grounded Learn teaching loop."
                    ),
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].teaching_turn",
                )
            )
        if teaching_turn.citations:
            row["cited_teaching_turn_count"] += 1
        else:
            errors.append(
                CoursePackValidationError(
                    code="draft_teaching_turn_uncited",
                    message="Every course-pack teaching turn needs a visible citation.",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    field=f"flow.steps[{step_id}].teaching_turn.citations",
                )
            )

        for strike in (1, 2, 3):
            row["hint_turn_count"] += 1
            hint_turn = plan_hint_turn(
                lesson_id=lesson_id,
                step=step,
                strike=strike,
            )
            if hint_turn is None:
                errors.append(
                    CoursePackValidationError(
                        code="draft_hint_turn_missing",
                        message="The first three adaptive hints must compile to tutor turns.",
                        course_id=course_id,
                        lesson_id=lesson_id,
                        field=f"flow.steps[{step_id}].hints[{strike}]",
                    )
                )
                continue
            if teaching_turn_is_grounded(hint_turn):
                row["grounded_hint_turn_count"] += 1
            else:
                errors.append(
                    CoursePackValidationError(
                        code="draft_hint_turn_not_grounded",
                        message=(
                            "Every course-pack hint turn must resolve through "
                            "the grounded Learn teaching loop."
                        ),
                        course_id=course_id,
                        lesson_id=lesson_id,
                        field=f"flow.steps[{step_id}].hints[{strike}].turn",
                    )
                )
            if hint_turn.citations:
                row["cited_hint_turn_count"] += 1
            else:
                errors.append(
                    CoursePackValidationError(
                        code="draft_hint_turn_uncited",
                        message="Every course-pack hint turn needs a visible citation.",
                        course_id=course_id,
                        lesson_id=lesson_id,
                        field=f"flow.steps[{step_id}].hints[{strike}].citations",
                    )
                )
    return row


_TEACHING_GROUNDING_ERROR_CODES = frozenset(
    {
        "draft_teaching_turn_not_grounded",
        "draft_teaching_turn_uncited",
    }
)
_HINT_GROUNDING_ERROR_CODES = frozenset(
    {
        "draft_hint_turn_missing",
        "draft_hint_turn_not_grounded",
        "draft_hint_turn_uncited",
    }
)


def _teaching_grounding_contract_summary(
    grounding_rows: list[dict[str, Any]],
    errors: list[CoursePackValidationError],
) -> dict[str, Any]:
    teaching_turn_count = sum(
        int(row.get("teaching_turn_count") or 0)
        for row in grounding_rows
    )
    grounded_teaching_turn_count = sum(
        int(row.get("grounded_teaching_turn_count") or 0)
        for row in grounding_rows
    )
    cited_teaching_turn_count = sum(
        int(row.get("cited_teaching_turn_count") or 0)
        for row in grounding_rows
    )
    error_codes = sorted(
        {
            error.code
            for error in errors
            if error.code in _TEACHING_GROUNDING_ERROR_CODES
        }
    )
    return {
        "ok": (
            bool(grounding_rows)
            and not error_codes
            and teaching_turn_count == grounded_teaching_turn_count
            and teaching_turn_count == cited_teaching_turn_count
        ),
        "teaching_turn_count": teaching_turn_count,
        "grounded_teaching_turn_count": grounded_teaching_turn_count,
        "cited_teaching_turn_count": cited_teaching_turn_count,
        "error_codes": error_codes,
    }


def _hint_grounding_contract_summary(
    grounding_rows: list[dict[str, Any]],
    errors: list[CoursePackValidationError],
) -> dict[str, Any]:
    hint_turn_count = sum(
        int(row.get("hint_turn_count") or 0)
        for row in grounding_rows
    )
    grounded_hint_turn_count = sum(
        int(row.get("grounded_hint_turn_count") or 0)
        for row in grounding_rows
    )
    cited_hint_turn_count = sum(
        int(row.get("cited_hint_turn_count") or 0)
        for row in grounding_rows
    )
    error_codes = sorted(
        {
            error.code
            for error in errors
            if error.code in _HINT_GROUNDING_ERROR_CODES
        }
    )
    return {
        "ok": (
            bool(grounding_rows)
            and not error_codes
            and hint_turn_count == grounded_hint_turn_count
            and hint_turn_count == cited_hint_turn_count
        ),
        "hint_turn_count": hint_turn_count,
        "grounded_hint_turn_count": grounded_hint_turn_count,
        "cited_hint_turn_count": cited_hint_turn_count,
        "error_codes": error_codes,
    }


def _prompt_contract_summary(
    flow_preview: list[dict[str, Any]],
    errors: list[CoursePackValidationError],
) -> dict[str, Any]:
    prompt_errors = [
        error for error in errors if error.code.startswith("draft_frontstage_prompt_")
    ]
    metrics = [
        step.get("prompt_metrics")
        for flow in flow_preview
        for step in flow.get("steps", [])
        if isinstance(step.get("prompt_metrics"), dict)
    ]
    return {
        "ok": not prompt_errors,
        "max_chars": MAX_FRONTSTAGE_PROMPT_CHARS,
        "max_words": MAX_FRONTSTAGE_PROMPT_WORDS,
        "max_sentences": MAX_FRONTSTAGE_PROMPT_SENTENCES,
        "single_line": True,
        "inline_lists_forbidden": True,
        "observed_max_chars": max((int(row.get("chars") or 0) for row in metrics), default=0),
        "observed_max_words": max((int(row.get("words") or 0) for row in metrics), default=0),
        "observed_max_sentences": max(
            (int(row.get("sentences") or 0) for row in metrics),
            default=0,
        ),
        "error_codes": sorted({error.code for error in prompt_errors}),
    }


def _authoring_contract_summary(
    contract: Any,
    *,
    required: bool,
    errors: list[CoursePackValidationError],
    course_id: str | None = None,
) -> dict[str, Any]:
    """Validate the course-pack authoring contract carried by manifest drafts."""
    error_codes: list[str] = []

    def add_error(
        code: str,
        message: str,
        *,
        field: str,
        expected: Any = None,
        actual: Any = None,
    ) -> None:
        error_codes.append(code)
        errors.append(
            CoursePackValidationError(
                code=code,
                message=message,
                course_id=course_id,
                field=field,
                expected=expected,
                actual=actual,
            )
        )

    if contract is None:
        if required:
            add_error(
                "draft_authoring_contract_missing",
                "Manifest needs an authoring_contract from the starter template.",
                field="authoring_contract",
            )
        return {
            "ok": not error_codes,
            "required": required,
            "frontstage": None,
            "default_input_surfaces": [],
            "required_hint_count": None,
            "prompt_limits": {},
            "copy_rules": [],
            "post_merge_commands": [],
            "error_codes": error_codes,
        }

    if not isinstance(contract, Mapping):
        add_error(
            "draft_authoring_contract_invalid",
            "authoring_contract must be an object.",
            field="authoring_contract",
            expected="object",
            actual=type(contract).__name__,
        )
        contract = {}

    prompt_limits = contract.get("prompt_limits")
    prompt_limits = prompt_limits if isinstance(prompt_limits, Mapping) else {}
    copy_rules = contract.get("copy_rules")
    copy_rules = copy_rules if isinstance(copy_rules, list) else []
    post_merge_commands = contract.get("post_merge_commands")
    post_merge_commands = (
        post_merge_commands if isinstance(post_merge_commands, list) else []
    )

    if contract.get("frontstage") != _AUTHORING_FRONTSTAGE:
        add_error(
            "draft_authoring_frontstage_rule_missing",
            "authoring_contract must preserve the one-action booth rule.",
            field="authoring_contract.frontstage",
            expected=_AUTHORING_FRONTSTAGE,
            actual=contract.get("frontstage"),
        )
    if contract.get("default_input_surfaces") != ["hardware", "screen"]:
        add_error(
            "draft_authoring_input_surfaces_missing",
            "authoring_contract must name hardware and screen input surfaces.",
            field="authoring_contract.default_input_surfaces",
            expected=["hardware", "screen"],
            actual=contract.get("default_input_surfaces"),
        )
    if contract.get("required_hint_count") != 3:
        add_error(
            "draft_authoring_hint_floor_missing",
            "authoring_contract must keep the three-hint floor.",
            field="authoring_contract.required_hint_count",
            expected=3,
            actual=contract.get("required_hint_count"),
        )

    expected_prompt_limits = {
        "max_chars": MAX_FRONTSTAGE_PROMPT_CHARS,
        "max_words": MAX_FRONTSTAGE_PROMPT_WORDS,
        "max_sentences": MAX_FRONTSTAGE_PROMPT_SENTENCES,
        "single_line": True,
        "inline_lists_forbidden": True,
    }
    for field, expected in expected_prompt_limits.items():
        if prompt_limits.get(field) != expected:
            add_error(
                "draft_authoring_prompt_limits_incomplete",
                "authoring_contract must carry the frontstage prompt limits.",
                field=f"authoring_contract.prompt_limits.{field}",
                expected=expected,
                actual=prompt_limits.get(field),
            )

    for rule in _AUTHORING_COPY_RULES:
        if rule not in copy_rules:
            add_error(
                "draft_authoring_copy_rule_missing",
                "authoring_contract must carry the Learn copy-truthfulness rules.",
                field="authoring_contract.copy_rules",
                expected=rule,
                actual=copy_rules,
            )
    for command in _AUTHORING_POST_MERGE_COMMANDS:
        if command not in post_merge_commands:
            add_error(
                "draft_authoring_post_merge_command_missing",
                "authoring_contract must list the post-merge verification commands.",
                field="authoring_contract.post_merge_commands",
                expected=command,
                actual=post_merge_commands,
            )

    return {
        "ok": not error_codes,
        "required": required,
        "frontstage": contract.get("frontstage"),
        "default_input_surfaces": list(contract.get("default_input_surfaces") or []),
        "required_hint_count": contract.get("required_hint_count"),
        "prompt_limits": dict(prompt_limits),
        "copy_rules": list(copy_rules),
        "post_merge_commands": list(post_merge_commands),
        "error_codes": sorted(set(error_codes)),
    }


def _flow_preview_row(flow: Any) -> dict[str, Any]:
    """Return a compact JSON-safe preview of a compiled draft lesson flow."""
    return {
        "lesson_id": str(flow.lesson_id),
        "title": str(flow.title),
        "step_count": len(flow.steps),
        "backstage_lenses": sorted(str(lens) for lens in flow.backstage_lenses),
        "steps": [
            {
                "step_id": str(step.step_id),
                "kind": str(step.kind),
                "prompt": str(step.prompt),
                "prompt_metrics": frontstage_prompt_metrics(str(step.prompt)),
                "verification_kind": str(step.verification.kind),
                "control": str(step.verification.control),
                "deck": str(step.verification.deck),
                "input_surfaces": [
                    str(surface)
                    for surface in step.verification.input_surfaces
                ],
                "observable_control_ids": [
                    str(control_id)
                    for control_id in step.verification.observable_control_ids
                ],
                "hint_count": len(step.hints),
            }
            for step in flow.steps
        ],
    }


def _integration_plan(
    course_id: str,
    meta: CourseMeta | None,
    frame: str,
    lessons: Mapping[str, LessonMeta],
    *,
    ok: bool,
    required_progress_fields: tuple[str, ...],
) -> dict[str, Any]:
    """Return the concrete merge checklist for a validated course pack."""
    lesson_ids = sorted(lessons)
    transcript_paths = [
        str(lessons[lesson_id].transcript_path)
        for lesson_id in lesson_ids
    ]
    progress_steps = [
        {
            "target": "src/vibemix/learn/progress.py:LearnProgress",
            "action": "add boolean progress fields before using this unlock gate",
            "fields": list(required_progress_fields),
        }
    ] if required_progress_fields else []
    course_meta: dict[str, Any] = {}
    if meta is not None:
        course_meta = {
            "label": meta.label,
            "hud_label": meta.hud_label,
            "unlock_gate": meta.unlock_gate,
            "lock_reason": meta.lock_reason,
            "frontstage_mode": meta.frontstage_mode,
            "capabilities": list(meta.capabilities),
            "beginner": meta.beginner,
        }
    return {
        "merge_ready": ok,
        "summary": (
            "fix validation errors before merging"
            if not ok
            else "copy these rows into the shipped curriculum and regenerate the frontend projection"
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
                "course_id": course_id,
                "value": course_meta,
            },
            {
                "target": "COURSE_FRAMES",
                "action": "add course frame",
                "course_id": course_id,
                "value": frame,
            },
            {
                "target": "CURRICULUM",
                "action": "add LessonMeta rows",
                "course_id": course_id,
                "lesson_ids": lesson_ids,
            },
            *progress_steps,
        ],
        "transcript_paths": transcript_paths,
        "commands": [
            "uv run python scripts/validate_learn_course_pack.py <course-pack.json>",
            "uv run python scripts/export_learn_curriculum_meta.py --check",
            "uv run pytest -q tests/learn/test_course_pack.py",
            "uv run python scripts/run_learn_python_quality.py --out /tmp/vibemix-live-learn-proof/learn-python-quality-current.json",
            "uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json",
        ],
    }


def _manifest_course_id_fallback(manifest_path: Path) -> str:
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    if isinstance(raw, Mapping) and isinstance(raw.get("course_id"), str):
        return raw["course_id"]
    return "unknown"


def _course_number(course_id: str) -> str | None:
    match = _COURSE_PACK_ID_RE.fullmatch(course_id)
    return match.group("number") if match is not None else None


def _required_string(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_string(row: Mapping[str, Any], field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    return value or None


def _required_list(row: Mapping[str, Any], field: str) -> list[Any]:
    value = row.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    return value


def _read_transcript_script(path: Path, lesson_id: str) -> dict[str, Any]:
    try:
        script = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{lesson_id}: transcript file not found: {path}") from exc
    if not isinstance(script, dict):
        raise ValueError(f"{lesson_id}: transcript root must be an object")
    return script


__all__ = [
    "CoursePackDraft",
    "CoursePackValidation",
    "CoursePackValidationError",
    "course_pack_template",
    "load_course_pack_manifest",
    "validate_course_pack_draft",
    "validate_course_pack_manifest",
    "write_course_pack_template",
]
