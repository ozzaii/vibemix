# SPDX-License-Identifier: Apache-2.0
"""Build a Respan-ready package from recorded Sven bench results.

The live Sven lane needs a durable iteration loop: run the existing bench, then
ship the recorded lines into the five product-quality judge dimensions without
turning missing credentials into a fake verdict. This module is deliberately
offline-only. It writes the request-log rows, dataset rows, evaluator rubrics,
and experiment metadata that Respan can ingest later, but it never performs a
network call and never reads a key.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PACKAGE_SCHEMA = "vibemix_sven_bench_respan_package_v1"
LIVE_PACKAGE_SCHEMA = "vibemix_sven_live_respan_package_v1"
REQUEST_LOG_SCHEMA = "vibemix_sven_bench_respan_request_log_v1"
LIVE_REQUEST_LOG_SCHEMA = "vibemix_sven_live_respan_request_log_v1"
DATASET_ROW_SCHEMA = "vibemix_sven_bench_respan_dataset_row_v1"
EVALUATORS_SCHEMA = "vibemix_sven_bench_respan_evaluators_v1"
EXPERIMENTS_SCHEMA = "vibemix_sven_bench_respan_experiments_v1"

DEFAULT_CATEGORY = "sven-bench-offline"
DEFAULT_LIVE_CATEGORY = "sven-live-session"
DEFAULT_SUITE_NAME = "sven_offline_bench"
DEFAULT_LIVE_SUITE_NAME = "sven_live_session"
DEFAULT_MAX_INPUT_CHARS = 5000

RESPAN_REQUEST_LOG_TARGET = "POST /api/request-logs/"
RESPAN_DATASET_TARGET = "DatasetAPI.create + add_logs_to_dataset"
RESPAN_EVALUATOR_TARGET = "EvaluatorAPI.create"
RESPAN_EXPERIMENT_TARGET = "DatasetAPI.run_dataset_evaluation"

JUDGE_DIMENSION_NAMES = (
    "friend_not_narrator",
    "grounded_not_fabricated",
    "earned_not_constant",
    "move_specific_not_spectrum",
    "voice_no_slop",
)

_FIRST_WORD_ACTIONS = frozenset(
    {
        "bring",
        "cut",
        "drop",
        "duck",
        "filter",
        "give",
        "hold",
        "keep",
        "kill",
        "leave",
        "lift",
        "loop",
        "open",
        "pull",
        "push",
        "ride",
        "swap",
        "trim",
        "wait",
    }
)
_ACTION_MOVE_TERMS = _FIRST_WORD_ACTIONS | frozenset(
    {
        "bar",
        "bars",
        "blend",
        "breakdown",
        "cue",
        "deck a",
        "deck b",
        "fader",
        "filter",
        "phrase",
    }
)

_MOVE_TERM_RE = re.compile(
    r"\b("
    r"bar|bars|bass|blend|breakdown|bring|cue|cut|deck\s*[ab]|drop|duck|"
    r"fader|filter|high|highs|hold|kill|layer|lift|loop|low|lows|mid|mids|"
    r"phrase|pull|push|ride|swap|top|trim|wait"
    r")\b",
    re.IGNORECASE,
)
_NARRATION_TERM_RE = re.compile(
    r"\b("
    r"airy|bright|brightness|dark|energy|frequency|metallic|motion|spectrum|"
    r"texture|tonal|vibe|warm|wide"
    r")\b",
    re.IGNORECASE,
)
_SLOP_TERM_RE = re.compile(
    r"\b("
    r"as an ai|i cannot|i can't|i am listening|i'm listening|it seems|"
    r"it sounds like|overall|perhaps|vibes?"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvaluatorSpec:
    """One Sven judge dimension that Respan should create as a 0-3 evaluator."""

    name: str
    summary: str
    rubric: dict[str, str]
    threshold: float | None = None

    def to_respan_payload(self) -> dict[str, Any]:
        """Return a provider-agnostic evaluator payload template."""

        return {
            "name": f"sven_{self.name}",
            "dimension": self.name,
            "score_range": {"min": 0, "max": 3, "integer": True},
            "threshold": self.threshold,
            "input_template": "{{input}}",
            "output_template": "{{output}}",
            "rubric": self.rubric,
            "judge_prompt": _judge_prompt_for(self),
        }


EVALUATOR_SPECS: tuple[EvaluatorSpec, ...] = (
    EvaluatorSpec(
        name="friend_not_narrator",
        summary="Sven coaches like a DJ friend instead of describing sound back.",
        threshold=2.0,
        rubric={
            "0": "Pure sound narration, no usable takeaway.",
            "1": "Mostly narration with a weak or buried point.",
            "2": "Usable move or read, but mixed with narration.",
            "3": "Clean coaching: one move, read, or forward nudge.",
        },
    ),
    EvaluatorSpec(
        name="grounded_not_fabricated",
        summary="Every specific claim is backed by the supplied evidence.",
        threshold=2.4,
        rubric={
            "0": "Invents a move, deck, track, or fact absent from evidence.",
            "1": "Partly unsupported.",
            "2": "Mostly backed by evidence.",
            "3": "Every specific is backed; copied real citations count.",
        },
    ),
    EvaluatorSpec(
        name="earned_not_constant",
        summary="The interruption is worth saying, not filler.",
        threshold=2.0,
        rubric={
            "0": "Filler or tells the DJ nothing useful.",
            "1": "Marginal value.",
            "2": "Worth saying.",
            "3": "Clearly worth interrupting for.",
        },
    ),
    EvaluatorSpec(
        name="move_specific_not_spectrum",
        summary="The line names a real DJ move or concrete direction.",
        threshold=None,
        rubric={
            "0": "Vague spectrum or sound-only language.",
            "1": "Sound specifics only, no move.",
            "2": "Names a real move or concrete direction.",
            "3": "Gives a specific actionable next step.",
        },
    ),
    EvaluatorSpec(
        name="voice_no_slop",
        summary="The line sounds like Sven, not generic assistant prose.",
        threshold=2.0,
        rubric={
            "0": "Generic AI narration or slop.",
            "1": "Stiff or unnatural.",
            "2": "Mostly natural.",
            "3": "A real DJ friend in the ear.",
        },
    ),
)


def load_bench_results(path: Path) -> list[dict[str, Any]]:
    """Load a ``results_to_json`` bench artifact or a dict wrapper containing rows."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("results") or data.get("rows") or data.get("bench_results")
    else:
        rows = None
    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain a bench results list")
    bad = [i for i, row in enumerate(rows) if not isinstance(row, dict)]
    if bad:
        raise ValueError(f"{path} contains non-object bench rows at indexes {bad[:5]}")
    return rows


def build_respan_package(
    results: list[dict[str, Any]],
    *,
    suite_name: str = DEFAULT_SUITE_NAME,
    category: str = DEFAULT_CATEGORY,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    """Assemble all offline Respan payloads from recorded bench rows."""

    request_logs = [
        build_request_log_payload(
            row,
            index=index,
            suite_name=suite_name,
            category=category,
            max_input_chars=max_input_chars,
        )
        for index, row in enumerate(results)
    ]
    dataset_rows = [
        build_dataset_row(log)
        for log in request_logs
        if log.get("metadata", {}).get("should_evaluate") is True
    ]
    summary = summarize_package(request_logs, dataset_rows)
    return {
        "schema": PACKAGE_SCHEMA,
        "suite_name": suite_name,
        "category": category,
        "api_targets": {
            "request_logs": RESPAN_REQUEST_LOG_TARGET,
            "dataset": RESPAN_DATASET_TARGET,
            "evaluators": RESPAN_EVALUATOR_TARGET,
            "experiments": RESPAN_EXPERIMENT_TARGET,
        },
        "summary": summary,
        "request_logs": request_logs,
        "dataset_rows": dataset_rows,
        "evaluators": build_evaluator_payloads(),
        "experiments": build_experiment_payloads(
            suite_name=suite_name,
            category=category,
        ),
    }


def build_request_log_payload(
    result: dict[str, Any],
    *,
    index: int,
    suite_name: str,
    category: str,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    """Return the request-log object accepted by the manual Respan log path."""

    cell = _cell_axes(result.get("cell"))
    respan_model = _respan_model_for_alias(cell.get("model_path"))
    output = str(result.get("output") or "")
    error = result.get("error")
    custom_id = _custom_id(cell, index)
    input_text = _judge_input(result, cell=cell, max_chars=max_input_chars)
    actionability = local_actionability_audit(output, errored=error is not None)
    should_evaluate = bool(output.strip()) and error is None
    metadata = {
        "schema": REQUEST_LOG_SCHEMA,
        "suite_name": suite_name,
        "bench_index": index,
        "bench_custom_id": custom_id,
        "respan_model": respan_model,
        "cell": cell,
        "usage": result.get("usage") if isinstance(result.get("usage"), dict) else {},
        "error": error,
        "should_evaluate": should_evaluate,
        "local_actionability_audit": actionability,
        "dsp_snapshot_summary": _dsp_snapshot_summary(result.get("dsp_snapshot")),
        "privacy": {
            "contains_audio_bytes": False,
            "contains_screen_frames": False,
            "source": "bench_results_json_text_only",
        },
    }
    return {
        "schema": REQUEST_LOG_SCHEMA,
        "model": respan_model,
        "log_type": "chat",
        "input": [{"role": "user", "content": input_text}],
        "output": {"role": "assistant", "content": output},
        "prompt_messages": [{"role": "user", "content": input_text}],
        "completion_message": {"role": "assistant", "content": output},
        "usage": _respan_usage(result.get("usage")),
        "status": "success" if error is None else "error",
        "status_code": 200 if error is None else 599,
        "error_message": str(error) if error is not None else None,
        "category": category,
        "custom_identifier": custom_id,
        "metadata": metadata,
    }


def build_dataset_row(log: dict[str, Any]) -> dict[str, Any]:
    """Return a compact dataset row derived from a request-log payload."""

    metadata = dict(log.get("metadata") or {})
    metadata["schema"] = DATASET_ROW_SCHEMA
    input_value = log.get("input")
    output_value = log.get("output")
    if not input_value:
        input_value = log.get("prompt_messages") or []
    if not output_value:
        output_value = log.get("completion_message") or {}
    return {
        "schema": DATASET_ROW_SCHEMA,
        "id": log.get("custom_identifier"),
        "input": _message_content(input_value),
        "output": _message_content(output_value),
        "metadata": metadata,
    }


def build_evaluator_payloads() -> dict[str, Any]:
    """Return the five Sven quality evaluator definitions."""

    return {
        "schema": EVALUATORS_SCHEMA,
        "count": len(EVALUATOR_SPECS),
        "dimensions": list(JUDGE_DIMENSION_NAMES),
        "evaluators": [spec.to_respan_payload() for spec in EVALUATOR_SPECS],
        "note": (
            "These are the five offline Sven bench dimensions. should_speak is "
            "left to the live/session lane because the bench forces a line."
        ),
    }


def build_experiment_payloads(*, suite_name: str, category: str) -> dict[str, Any]:
    """Return experiment metadata for comparing bench cells by their axes."""

    return {
        "schema": EXPERIMENTS_SCHEMA,
        "experiments": [
            {
                "name": f"{suite_name}_quality_matrix",
                "dataset_category": category,
                "evaluators": [f"sven_{name}" for name in JUDGE_DIMENSION_NAMES],
                "group_by": [
                    "cell.model_path",
                    "cell.grounding",
                    "cell.prompting",
                    "cell.contexting",
                    "cell.lens",
                    "cell.taste",
                ],
                "compare_metric": "mean_score_by_dimension",
                "owner_note": (
                    "Use the Respan judge scores for decisions; local_actionability_audit "
                    "is only a no-key smoke signal."
                ),
            }
        ],
    }


def summarize_package(
    request_logs: list[dict[str, Any]],
    dataset_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a small manifest summary for humans and automation."""

    errored = sum(1 for row in request_logs if row.get("metadata", {}).get("error"))
    audit_scores = [
        row.get("metadata", {})
        .get("local_actionability_audit", {})
        .get("move_specific_score_0_to_3")
        for row in request_logs
    ]
    numeric_scores = [float(score) for score in audit_scores if isinstance(score, int | float)]
    move_named = sum(
        1
        for row in request_logs
        if row.get("metadata", {}).get("local_actionability_audit", {}).get("move_named")
    )
    return {
        "bench_rows": len(request_logs),
        "dataset_rows": len(dataset_rows),
        "parked_errors": errored,
        "five_dim_evaluators": len(EVALUATOR_SPECS),
        "local_actionability": {
            "move_named_rows": move_named,
            "mean_move_specific_score_0_to_3": (
                round(sum(numeric_scores) / len(numeric_scores), 3) if numeric_scores else None
            ),
            "status": "metadata_only_not_a_respan_verdict",
        },
    }


def write_respan_package(
    results_path: Path,
    out_dir: Path,
    *,
    suite_name: str = DEFAULT_SUITE_NAME,
    category: str = DEFAULT_CATEGORY,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    """Load a bench results file, write the package directory, and return manifest."""

    results = load_bench_results(results_path)
    package = build_respan_package(
        results,
        suite_name=suite_name,
        category=category,
        max_input_chars=max_input_chars,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    request_logs_path = out_dir / "respan_request_logs.jsonl"
    dataset_rows_path = out_dir / "dataset_rows.jsonl"
    evaluators_path = out_dir / "evaluators.json"
    experiments_path = out_dir / "experiments.json"
    manifest_path = out_dir / "manifest.json"
    readme_path = out_dir / "README.md"

    _write_jsonl(request_logs_path, package["request_logs"])
    _write_jsonl(dataset_rows_path, package["dataset_rows"])
    _write_json(evaluators_path, package["evaluators"])
    _write_json(experiments_path, package["experiments"])

    manifest = {
        "schema": PACKAGE_SCHEMA,
        "suite_name": suite_name,
        "category": category,
        "source_results": str(results_path),
        "out_dir": str(out_dir),
        "files": {
            "request_logs": request_logs_path.name,
            "dataset_rows": dataset_rows_path.name,
            "evaluators": evaluators_path.name,
            "experiments": experiments_path.name,
            "readme": readme_path.name,
        },
        "api_targets": package["api_targets"],
        "summary": package["summary"],
    }
    _write_json(manifest_path, manifest)
    readme_path.write_text(_format_readme(manifest), encoding="utf-8")
    return manifest


def build_live_respan_package(
    spans: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]] | None = None,
    *,
    session_dir: Path | None = None,
    suite_name: str = DEFAULT_LIVE_SUITE_NAME,
    category: str = DEFAULT_LIVE_CATEGORY,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    """Assemble a text-only Respan package from live Sven session artifacts."""

    feedback_by_response = _latest_feedback_by_response(feedback_rows or [])
    request_logs = [
        build_live_request_log_payload(
            span,
            index=index,
            session_dir=session_dir,
            feedback=feedback_by_response.get(_live_response_id(span, index=index)),
            suite_name=suite_name,
            category=category,
            max_input_chars=max_input_chars,
        )
        for index, span in enumerate(spans)
    ]
    dataset_rows = [
        build_dataset_row(log)
        for log in request_logs
        if log.get("metadata", {}).get("should_evaluate") is True
    ]
    summary = summarize_live_package(request_logs, feedback_rows or [], dataset_rows)
    return {
        "schema": LIVE_PACKAGE_SCHEMA,
        "suite_name": suite_name,
        "category": category,
        "api_targets": {
            "request_logs": RESPAN_REQUEST_LOG_TARGET,
            "dataset": RESPAN_DATASET_TARGET,
            "evaluators": RESPAN_EVALUATOR_TARGET,
            "experiments": RESPAN_EXPERIMENT_TARGET,
        },
        "summary": summary,
        "request_logs": request_logs,
        "dataset_rows": dataset_rows,
        "feedback_labels": list(feedback_rows or []),
        "evaluators": build_evaluator_payloads(),
        "experiments": build_live_experiment_payloads(
            suite_name=suite_name,
            category=category,
        ),
    }


def build_live_request_log_payload(
    span: dict[str, Any],
    *,
    index: int,
    suite_name: str,
    category: str,
    session_dir: Path | None = None,
    feedback: dict[str, Any] | None = None,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    """Return one live span row normalized for the offline Respan package."""

    if not isinstance(span, dict):
        raise ValueError(f"live span at index {index} is not an object")
    response_id = _live_response_id(span, index=index)
    metadata = dict(span.get("metadata") or {})
    source_privacy = metadata.get("privacy") if isinstance(metadata.get("privacy"), dict) else {}
    input_text = _bounded_text(_message_content(span.get("input")), max_chars=max_input_chars)
    output_text = _message_content(span.get("output"))
    status = str(span.get("status") or "success")
    feedback_payload = _compact_live_feedback(feedback)
    should_evaluate = (
        bool(output_text.strip())
        and status == "success"
        and bool(metadata.get("should_evaluate_five_dim"))
    )

    metadata.update(
        {
            "schema": LIVE_REQUEST_LOG_SCHEMA,
            "source_schema": span.get("schema"),
            "suite_name": suite_name,
            "live_index": index,
            "live_custom_id": response_id,
            "session_id": metadata.get("session_id") or _session_id_from_dir(session_dir),
            "session_dir": str(session_dir) if session_dir is not None else None,
            "should_evaluate": should_evaluate,
            "operator_feedback": feedback_payload,
            "local_actionability_audit": local_actionability_audit(
                output_text,
                errored=status != "success",
            ),
            "privacy": {
                "contains_audio_bytes": bool(source_privacy.get("contains_audio_bytes")),
                "contains_screen_frames": bool(source_privacy.get("contains_screen_frames")),
                "contains_full_prompt": bool(source_privacy.get("contains_full_prompt")),
                "source": "live_respan_spans_jsonl_text_only",
            },
        }
    )
    if feedback_payload is None:
        metadata.pop("operator_feedback", None)

    return {
        "schema": LIVE_REQUEST_LOG_SCHEMA,
        "model": span.get("model") or "unknown",
        "log_type": span.get("log_type") or "chat",
        "input": [{"role": "user", "content": input_text}],
        "output": {"role": "assistant", "content": output_text},
        "prompt_messages": [{"role": "user", "content": input_text}],
        "completion_message": {"role": "assistant", "content": output_text},
        "usage": span.get("usage") if isinstance(span.get("usage"), dict) else {},
        "status": status,
        "status_code": span.get("status_code") or (200 if status == "success" else 599),
        "error_message": span.get("error_message"),
        "category": category,
        "custom_identifier": response_id,
        "metadata": metadata,
    }


def build_live_experiment_payloads(*, suite_name: str, category: str) -> dict[str, Any]:
    """Return experiment metadata for live-session Sven quality review."""

    return {
        "schema": EXPERIMENTS_SCHEMA,
        "experiments": [
            {
                "name": f"{suite_name}_live_quality",
                "dataset_category": category,
                "evaluators": [f"sven_{name}" for name in JUDGE_DIMENSION_NAMES],
                "group_by": [
                    "event",
                    "live_decision",
                    "citation.action",
                    "operator_feedback.label",
                ],
                "compare_metric": "mean_score_by_dimension",
                "owner_note": (
                    "Live package rows are text-only. Operator feedback labels are "
                    "training metadata, not judge verdicts."
                ),
            }
        ],
    }


def summarize_live_package(
    request_logs: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    dataset_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a compact summary for live-session packages."""

    spoken = sum(1 for row in request_logs if _message_content(row.get("output")).strip())
    feedback_by_response = _latest_feedback_by_response(feedback_rows)
    positive = sum(1 for row in feedback_by_response.values() if row.get("score") == 1)
    negative = sum(1 for row in feedback_by_response.values() if row.get("score") == -1)
    return {
        "live_spans": len(request_logs),
        "spoken_spans": spoken,
        "silent_spans": len(request_logs) - spoken,
        "dataset_rows": len(dataset_rows),
        "feedback_rows": len(feedback_rows),
        "labeled_responses": len(feedback_by_response),
        "positive_labels": positive,
        "negative_labels": negative,
        "five_dim_evaluators": len(EVALUATOR_SPECS),
        "local_actionability": {
            "status": "metadata_only_not_a_respan_verdict",
        },
        "privacy": {
            "contains_audio_bytes": False,
            "contains_screen_frames": False,
            "contains_full_prompt": False,
        },
    }


def write_live_respan_package(
    session_dir: Path,
    out_dir: Path,
    *,
    suite_name: str = DEFAULT_LIVE_SUITE_NAME,
    category: str = DEFAULT_LIVE_CATEGORY,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    """Write an offline package from a live session's spans and feedback labels."""

    session_root = Path(session_dir)
    spans_path = session_root / "respan_spans.jsonl"
    feedback_path = session_root / "sven_feedback.jsonl"
    spans = _read_jsonl(spans_path, required=True)
    feedback_rows = _read_jsonl(feedback_path, required=False)
    package = build_live_respan_package(
        spans,
        feedback_rows,
        session_dir=session_root,
        suite_name=suite_name,
        category=category,
        max_input_chars=max_input_chars,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    request_logs_path = out_dir / "respan_request_logs.jsonl"
    dataset_rows_path = out_dir / "dataset_rows.jsonl"
    feedback_labels_path = out_dir / "feedback_labels.jsonl"
    evaluators_path = out_dir / "evaluators.json"
    experiments_path = out_dir / "experiments.json"
    manifest_path = out_dir / "manifest.json"
    readme_path = out_dir / "README.md"

    _write_jsonl(request_logs_path, package["request_logs"])
    _write_jsonl(dataset_rows_path, package["dataset_rows"])
    _write_jsonl(feedback_labels_path, package["feedback_labels"])
    _write_json(evaluators_path, package["evaluators"])
    _write_json(experiments_path, package["experiments"])

    manifest = {
        "schema": LIVE_PACKAGE_SCHEMA,
        "suite_name": suite_name,
        "category": category,
        "source_session": str(session_root),
        "out_dir": str(out_dir),
        "files": {
            "request_logs": request_logs_path.name,
            "dataset_rows": dataset_rows_path.name,
            "feedback_labels": feedback_labels_path.name,
            "evaluators": evaluators_path.name,
            "experiments": experiments_path.name,
            "readme": readme_path.name,
        },
        "api_targets": package["api_targets"],
        "summary": package["summary"],
    }
    _write_json(manifest_path, manifest)
    readme_path.write_text(_format_live_readme(manifest), encoding="utf-8")
    return manifest


def local_actionability_audit(text: str, *, errored: bool = False) -> dict[str, Any]:
    """Deterministic no-key metadata for spotting obvious narrator rows.

    This is intentionally not the judge. It gives the package a useful smoke
    signal while preserving Respan as the decision-grade scorer.
    """

    if errored:
        return {
            "status": "parked_error_not_scored",
            "move_specific_score_0_to_3": None,
            "move_named": False,
            "should_not_have_spoken_hint": None,
            "flags": ["parked_error"],
        }

    clean = " ".join(str(text or "").split())
    if not clean:
        return {
            "status": "empty_output_not_scored",
            "move_specific_score_0_to_3": 0,
            "move_named": False,
            "should_not_have_spoken_hint": True,
            "flags": ["empty_output"],
        }

    first = clean.split(maxsplit=1)[0].strip(".,:;!?").lower()
    action_first = first in _FIRST_WORD_ACTIONS
    move_terms = _unique_matches(_MOVE_TERM_RE, clean)
    narration_terms = _unique_matches(_NARRATION_TERM_RE, clean)
    slop_terms = _unique_matches(_SLOP_TERM_RE, clean)
    move_named = action_first or any(term in _ACTION_MOVE_TERMS for term in move_terms)

    if action_first and move_named and not slop_terms:
        score = 3
    elif move_named and len(slop_terms) <= 1:
        score = 2
    elif narration_terms and not move_named:
        score = 1
    else:
        score = 1 if not slop_terms else 0

    flags: list[str] = []
    if not move_named:
        flags.append("no_move_named")
    if narration_terms and not move_named:
        flags.append("sound_narration_only")
    if slop_terms:
        flags.append("generic_slop")
    if len(clean.split()) > 24:
        flags.append("long_line")

    return {
        "status": "metadata_only_not_a_respan_verdict",
        "move_specific_score_0_to_3": score,
        "move_named": move_named,
        "action_first": action_first,
        "move_terms": move_terms[:12],
        "narration_terms": narration_terms[:12],
        "slop_terms": slop_terms[:12],
        "should_not_have_spoken_hint": ("sound_narration_only" in flags or "generic_slop" in flags),
        "flags": flags,
    }


def _judge_prompt_for(spec: EvaluatorSpec) -> str:
    rubric = "\n".join(f"{score}: {text}" for score, text in spec.rubric.items())
    return (
        "You are a blind judge grading one line spoken by Sven, an AI DJ co-host. "
        "Grade only this dimension: "
        f"{spec.name}. Input is the evidence/prompt excerpt Sven had. Output is "
        "the line Sven spoke. Return only compact JSON: "
        f'{{"{spec.name}":N,"why":"<=12 words"}}.\n\n'
        f"Dimension summary: {spec.summary}\nRubric 0-3:\n{rubric}"
    )


def _judge_input(result: dict[str, Any], *, cell: dict[str, Any], max_chars: int) -> str:
    prompt = str(result.get("prompt") or "")
    excerpt = _extract_prompt_excerpt(prompt, max_chars=max_chars)
    dsp_summary = _dsp_snapshot_summary(result.get("dsp_snapshot"))
    return (
        "SVEN BENCH EVIDENCE/PROMPT EXCERPT\n"
        f"cell={json.dumps(cell, sort_keys=True, ensure_ascii=False)}\n"
        f"dsp_snapshot_summary={json.dumps(dsp_summary, sort_keys=True, ensure_ascii=False)}\n\n"
        f"{excerpt}"
    ).strip()


def _extract_prompt_excerpt(prompt: str, *, max_chars: int) -> str:
    text = str(prompt or "").strip()
    if not text:
        return ""
    evidence_start = text.rfind("[hearing[")
    excerpt = text[evidence_start:] if evidence_start >= 0 else text
    return _bounded_text(excerpt, max_chars=max_chars)


def _bounded_text(text: str, *, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    keep_head = max(1, max_chars // 2)
    keep_tail = max(1, max_chars - keep_head)
    return f"{text[:keep_head]}\n...[truncated]...\n{text[-keep_tail:]}"


def _cell_axes(cell: Any) -> dict[str, Any]:
    if isinstance(cell, dict):
        return {
            "model_path": cell.get("model_path"),
            "grounding": cell.get("grounding"),
            "prompting": cell.get("prompting"),
            "contexting": cell.get("contexting"),
            "lens": cell.get("lens"),
            "taste": cell.get("taste"),
            "skill": cell.get("skill"),
            "track": cell.get("track"),
        }
    return {
        "model_path": getattr(cell, "model_path", None),
        "grounding": getattr(cell, "grounding", None),
        "prompting": getattr(cell, "prompting", None),
        "contexting": getattr(cell, "contexting", None),
        "lens": getattr(cell, "lens", None),
        "taste": getattr(cell, "taste", None),
        "skill": getattr(cell, "skill", None),
        "track": getattr(cell, "track", None),
    }


def _respan_model_for_alias(alias: Any) -> str:
    if not alias:
        return "unknown_router_alias"
    alias_text = str(alias)
    try:
        from vibemix.llm.model_router import resolve_model

        model = resolve_model(alias_text)
    except Exception:
        return alias_text
    if model.startswith("google/"):
        return model.replace("google/", "gemini/", 1)
    return model


def _dsp_snapshot_summary(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"sources": {}, "source_count": 0}
    sources: dict[str, Any] = {}
    for source, atoms in sorted(snapshot.items(), key=lambda item: str(item[0])):
        if not isinstance(atoms, dict):
            continue
        keys = sorted(str(key) for key in atoms)
        sources[str(source)] = {"atom_count": len(keys), "atoms": keys[:24]}
    return {"source_count": len(sources), "sources": sources}


def _respan_usage(usage: Any) -> dict[str, Any]:
    if not isinstance(usage, dict):
        return {}
    prompt_tokens = _nonnegative_int(usage.get("prompt_token_count"))
    completion_tokens = _nonnegative_int(usage.get("candidates_token_count"))
    total_tokens = _nonnegative_int(usage.get("total_token_count"))
    if total_tokens == 0 and (prompt_tokens or completion_tokens):
        total_tokens = prompt_tokens + completion_tokens
    out: dict[str, Any] = {}
    if prompt_tokens:
        out["prompt_tokens"] = prompt_tokens
    if completion_tokens:
        out["completion_tokens"] = completion_tokens
    if total_tokens:
        out["total_tokens"] = total_tokens
    cached = _nonnegative_int(usage.get("cached_content_token_count"))
    if cached:
        out["prompt_tokens_details"] = {"cached_tokens": cached}
    return out


def _nonnegative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _message_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("content") or "")
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("content") or "")
    return ""


def _custom_id(cell: dict[str, Any], index: int) -> str:
    parts = [
        "sven",
        "bench",
        f"{index:03d}",
        str(cell.get("model_path") or "model"),
        str(cell.get("grounding") or "grounding"),
        str(cell.get("lens") or "lens"),
        str(cell.get("taste") or "taste"),
    ]
    slug = "_".join(_slug(part) for part in parts)
    if len(slug) <= 140:
        return slug
    digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()[:10]
    return f"{slug[:129]}_{digest}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "x"


def _unique_matches(pattern: re.Pattern[str], text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        term = " ".join(match.group(0).lower().split())
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path, *, required: bool) -> list[dict[str, Any]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSONL row") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: JSONL row is not an object")
        rows.append(row)
    return rows


def _format_readme(manifest: dict[str, Any]) -> str:
    files = manifest["files"]
    summary = manifest["summary"]
    return (
        "# Sven Bench Respan Package\n\n"
        f"Schema: `{manifest['schema']}`\n\n"
        "This package is offline and keyless. It contains text-only bench lines "
        "and metadata for Respan ingestion; it does not contain raw audio, screen "
        "frames, API keys, or a judge verdict.\n\n"
        "Files:\n"
        f"- `{files['request_logs']}`: payloads shaped for {RESPAN_REQUEST_LOG_TARGET}\n"
        f"- `{files['dataset_rows']}`: evaluable input/output rows\n"
        f"- `{files['evaluators']}`: the five Sven 0-3 evaluator rubrics\n"
        f"- `{files['experiments']}`: grouping metadata for the bench matrix\n\n"
        "Summary:\n"
        f"- bench_rows: {summary['bench_rows']}\n"
        f"- dataset_rows: {summary['dataset_rows']}\n"
        f"- parked_errors: {summary['parked_errors']}\n"
        f"- five_dim_evaluators: {summary['five_dim_evaluators']}\n"
    )


def _format_live_readme(manifest: dict[str, Any]) -> str:
    files = manifest["files"]
    summary = manifest["summary"]
    return (
        "# Sven Live Respan Package\n\n"
        f"Schema: `{manifest['schema']}`\n\n"
        "This package is offline and keyless. It joins live Sven text-only "
        "decision spans with local by-ear feedback labels; it does not contain "
        "raw audio, screen frames, full prompt bodies, API keys, or a judge "
        "verdict.\n\n"
        "Files:\n"
        f"- `{files['request_logs']}`: live span payloads shaped for {RESPAN_REQUEST_LOG_TARGET}\n"
        f"- `{files['dataset_rows']}`: spoken-line input/output rows for five-dim judging\n"
        f"- `{files['feedback_labels']}`: local operator labels, when present\n"
        f"- `{files['evaluators']}`: the five Sven 0-3 evaluator rubrics\n"
        f"- `{files['experiments']}`: grouping metadata for live-session review\n\n"
        "Summary:\n"
        f"- live_spans: {summary['live_spans']}\n"
        f"- spoken_spans: {summary['spoken_spans']}\n"
        f"- silent_spans: {summary['silent_spans']}\n"
        f"- dataset_rows: {summary['dataset_rows']}\n"
        f"- labeled_responses: {summary['labeled_responses']}\n"
        f"- positive_labels: {summary['positive_labels']}\n"
        f"- negative_labels: {summary['negative_labels']}\n"
    )


def _live_response_id(span: dict[str, Any], *, index: int) -> str:
    metadata = span.get("metadata") if isinstance(span.get("metadata"), dict) else {}
    response_id = span.get("custom_identifier") or metadata.get("response_id")
    text = str(response_id or "").strip()
    return text or f"live_span_{index:04d}"


def _latest_feedback_by_response(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        response_id = str(row.get("response_id") or "").strip()
        if not response_id:
            continue
        out[response_id] = row
    return out


def _compact_live_feedback(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    out = {
        "label": row.get("label"),
        "score": row.get("score"),
        "note": _bounded_text(str(row.get("note") or ""), max_chars=500),
        "source": row.get("source"),
    }
    target = row.get("target")
    if isinstance(target, dict):
        out["target"] = {
            key: target.get(key)
            for key in (
                "event",
                "live_decision",
                "stop_reason",
                "suppression",
                "citation_action",
                "citation_count",
            )
            if key in target
        }
    return {key: value for key, value in out.items() if value not in (None, "", {})}


def _session_id_from_dir(path: Path | None) -> str | None:
    return path.name if path is not None else None


__all__ = [
    "DEFAULT_CATEGORY",
    "DEFAULT_LIVE_CATEGORY",
    "DEFAULT_LIVE_SUITE_NAME",
    "DEFAULT_SUITE_NAME",
    "EVALUATOR_SPECS",
    "JUDGE_DIMENSION_NAMES",
    "LIVE_PACKAGE_SCHEMA",
    "PACKAGE_SCHEMA",
    "build_dataset_row",
    "build_evaluator_payloads",
    "build_experiment_payloads",
    "build_live_request_log_payload",
    "build_live_respan_package",
    "build_request_log_payload",
    "build_respan_package",
    "load_bench_results",
    "local_actionability_audit",
    "summarize_live_package",
    "summarize_package",
    "write_live_respan_package",
    "write_respan_package",
]
