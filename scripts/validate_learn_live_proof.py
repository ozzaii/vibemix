#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate a Learn live-proof JSON artifact.

The proof runner records what happened. This validator turns that report into a
small machine-gradable verdict so handoffs cannot quietly overclaim: screen,
physical, and Course 3 requirements are checked separately, and skipped stages
only pass when the caller explicitly allows that requirement to be unavailable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

Requirement = Literal["screen", "physical", "course3"]
REQUIREMENTS: tuple[Requirement, ...] = ("screen", "physical", "course3")


def load_artifact(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("artifact root must be an object")
    return raw


def _stage(artifact: dict[str, Any], name: str) -> dict[str, Any]:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return {}
    stage = stages.get(name)
    return stage if isinstance(stage, dict) else {}


def _result(stage: dict[str, Any]) -> dict[str, Any]:
    result = stage.get("result")
    return result if isinstance(result, dict) else {}


def _lesson_completed(progress_stage: dict[str, Any], lesson_id: str) -> bool:
    result = _result(progress_stage)
    snapshot = result.get("snapshot")
    if not isinstance(snapshot, dict):
        return False
    lessons = snapshot.get("lessons")
    if not isinstance(lessons, dict):
        return False
    row = lessons.get(lesson_id)
    return isinstance(row, dict) and row.get("completed") is True


def _unavailable(stage: dict[str, Any]) -> bool:
    if stage.get("status") != "skipped":
        return False
    return bool(_stage_blockers(stage))


def _string_blockers(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str) and item]


def _stage_blockers(stage: dict[str, Any]) -> list[str]:
    """Extract human-actionable blockers from a stage result.

    Readiness artifacts can store blockers either directly on ``result`` or
    inside wait-wrapper shapes such as ``result.last``. Course 3 live-context
    checks add an even narrower nested blocker list under
    ``checks.course3_live_context``. Surface all of them so a failed proof says
    what to fix, not merely which stage skipped.
    """
    result = _result(stage)
    blockers = _string_blockers(result.get("blockers"))

    last = result.get("last")
    if isinstance(last, dict):
        blockers.extend(_string_blockers(last.get("blockers")))
        last_checks = last.get("checks")
        if isinstance(last_checks, dict):
            live_context = last_checks.get("course3_live_context")
            if isinstance(live_context, dict):
                blockers.extend(_string_blockers(live_context.get("blockers")))

    checks = result.get("checks")
    if isinstance(checks, dict):
        live_context = checks.get("course3_live_context")
        if isinstance(live_context, dict):
            blockers.extend(_string_blockers(live_context.get("blockers")))

    deduped: list[str] = []
    seen: set[str] = set()
    for blocker in blockers:
        if blocker in seen:
            continue
        seen.add(blocker)
        deduped.append(blocker)
    return deduped


def _check_screen(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    screen = _stage(artifact, "screen_probe")
    result = _result(screen)
    if screen.get("status") != "passed":
        errors.append("screen_probe did not pass")
    if result.get("passed") is not True:
        errors.append("screen_probe.result.passed is not true")
    if int(result.get("acks_sent") or 0) < 4:
        errors.append("screen proof sent fewer than 4 ACKs")
    if int(result.get("advance_count") or 0) < 4:
        errors.append("screen proof saw fewer than 4 advances")
    if result.get("complete_seen") is not True:
        errors.append("screen proof did not see completion")
    if result.get("progress_completed") is not True:
        errors.append("screen proof did not see completed progress")

    progress = _stage(artifact, "progress_file")
    if progress.get("status") != "passed":
        errors.append("progress_file stage did not pass")
    if not _lesson_completed(progress, "L1.01"):
        errors.append("progress_file does not show L1.01 completed")

    return errors


def _check_lifecycle(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    app_start = _stage(artifact, "app_start")
    app_stop = _stage(artifact, "app_stop")
    if app_start.get("status") == "failed":
        errors.append("app_start stage failed")
    if app_start.get("status") == "passed" and app_stop.get("status") != "passed":
        errors.append("app was started but app_stop did not pass")
    if app_stop.get("status") == "failed":
        errors.append("app_stop stage failed")
    return errors


def _check_physical(artifact: dict[str, Any], *, allow_skipped: set[str]) -> list[str]:
    stage = _stage(artifact, "physical_probe")
    result = _result(stage)
    if stage.get("status") == "skipped":
        if "physical" in allow_skipped and _unavailable(stage):
            return []
        errors = [f"physical_probe skipped: {stage.get('reason', 'no reason')}"]
        errors.extend(f"physical readiness: {blocker}" for blocker in _stage_blockers(stage))
        return errors
    errors: list[str] = []
    if stage.get("status") != "passed":
        errors.append("physical_probe did not pass")
    if result.get("passed") is not True:
        errors.append("physical_probe.result.passed is not true")
    if result.get("lesson_id") != "L1.07":
        errors.append("physical proof lesson_id is not L1.07")
    if result.get("control_id") != "jog:A":
        errors.append("physical proof control_id is not jog:A")
    if result.get("lesson_loaded") is not True:
        errors.append("physical proof did not load the lesson")
    if result.get("jog_position_seen") is not True:
        errors.append("physical proof did not see the jog position")
    if result.get("ack_sent") is not True:
        errors.append("physical proof did not send ACK")
    if result.get("advance_seen") is not True:
        errors.append("physical proof did not see advance")
    return errors


def _check_course3(artifact: dict[str, Any], *, allow_skipped: set[str]) -> list[str]:
    stage = _stage(artifact, "course3_probe")
    result = _result(stage)
    if stage.get("status") == "skipped":
        if "course3" in allow_skipped and _unavailable(stage):
            return []
        errors = [f"course3_probe skipped: {stage.get('reason', 'no reason')}"]
        errors.extend(f"course3 readiness: {blocker}" for blocker in _stage_blockers(stage))
        return errors
    errors: list[str] = []
    if stage.get("status") != "passed":
        errors.append("course3_probe did not pass")
    if result.get("passed") is not True:
        errors.append("course3_probe.result.passed is not true")
    if int(result.get("lens_frames") or 0) < 1:
        errors.append("course3 proof saw no lens frames")
    if result.get("active_seen") is not True:
        errors.append("course3 proof did not see active Course 3")
    if result.get("count_in_seen") is not True:
        errors.append("course3 proof did not see count-in evidence")
    last_lens = result.get("last_lens")
    if not isinstance(last_lens, dict):
        errors.append("course3 proof has no last_lens object")
    elif not last_lens.get("next_phrase_cue_id"):
        errors.append("course3 proof has no citable next phrase cue id")
    diagnostics = result.get("diagnostics")
    if isinstance(diagnostics, dict):
        blockers = diagnostics.get("blockers")
        if isinstance(blockers, list):
            errors.extend(
                f"course3 diagnostic: {blocker}"
                for blocker in blockers
                if isinstance(blocker, str)
            )
        operator_action = diagnostics.get("operator_action")
        if isinstance(operator_action, dict) and operator_action.get("prompt"):
            errors.append(f"course3 operator action: {operator_action['prompt']}")
    return errors


def validate_artifact(
    artifact: dict[str, Any],
    *,
    required: set[Requirement],
    allow_skipped: set[Requirement],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if artifact.get("schema_version") != 1:
        errors.append("schema_version is not 1")
    if not isinstance(artifact.get("stages"), dict):
        errors.append("stages object missing")
    else:
        errors.extend(_check_lifecycle(artifact))

    if "screen" in required:
        errors.extend(_check_screen(artifact))
    if "physical" in required:
        errors.extend(_check_physical(artifact, allow_skipped=set(allow_skipped)))
    if "course3" in required:
        errors.extend(_check_course3(artifact, allow_skipped=set(allow_skipped)))

    for requirement in sorted(allow_skipped):
        if requirement not in required:
            warnings.append(f"allow-skipped {requirement} ignored because it was not required")

    return {
        "valid": not errors,
        "required": sorted(required),
        "allow_skipped": sorted(allow_skipped),
        "errors": errors,
        "warnings": warnings,
    }


def _requirements(values: list[str]) -> set[Requirement]:
    return {value for value in values if value in REQUIREMENTS}  # type: ignore[return-value]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_learn_live_proof",
        description="Validate a Learn live-proof JSON artifact.",
    )
    parser.add_argument("artifact", type=Path, help="Path to proof JSON from run_learn_live_proof.py.")
    parser.add_argument(
        "--require",
        action="append",
        choices=REQUIREMENTS,
        default=[],
        help="Requirement to validate. Repeat for multiple. Defaults to screen.",
    )
    parser.add_argument(
        "--allow-skipped",
        action="append",
        choices=("physical", "course3"),
        default=[],
        help="Accept a skipped unavailable requirement when blockers are recorded.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    required = _requirements(args.require or ["screen"])
    allow_skipped = _requirements(args.allow_skipped or [])
    try:
        artifact = load_artifact(args.artifact)
        verdict = validate_artifact(
            artifact,
            required=required,
            allow_skipped=allow_skipped,
        )
    except Exception as exc:
        verdict = {
            "valid": False,
            "required": sorted(required),
            "allow_skipped": sorted(allow_skipped),
            "errors": [repr(exc)],
            "warnings": [],
        }
    print(json.dumps(verdict, sort_keys=True))
    return 0 if verdict.get("valid") is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
