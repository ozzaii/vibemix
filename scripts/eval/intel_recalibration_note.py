# SPDX-License-Identifier: Apache-2.0
"""Render a redacted INTEL threshold recalibration-log entry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_LOCK = ROOT / "eval" / "INTEL-THRESHOLD-LOCK.md"
DEFAULT_LOG = ROOT / "eval" / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
APPEND_MARKER = "<!-- Real redacted private-label entries append below. -->"

EVIDENCE_TIERS = frozenset(
    {
        "tier1_private_calibration",
        "tier2_private_holdout_canary",
    }
)
FORBIDDEN_PRIVATE_PATTERNS = (
    re.compile(r"/Users/"),
    re.compile(r"/Volumes/"),
    re.compile(r"\b[A-Za-z]:\\\\"),
    re.compile(r"file://", re.I),
    re.compile(r"\.(?:wav|aiff|aif|mp3|flac)\b", re.I),
    re.compile(r"\braw_(?:audio|vector)s?\b", re.I),
    re.compile(r"\b(?:track_title|deck_id|session_id|free_form)\b", re.I),
)


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric: str
    threshold: str
    direction: str


KEY_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("section_role_hit_at_5_delta", "section_role_hit_at_5_delta_min", "min"),
    MetricSpec("transition_accept_at_3", "transition_accept_at_3_min", "min"),
    MetricSpec(
        "decision_exact_timing_floor_violation_rate",
        "decision_exact_timing_floor_violation_rate_max",
        "max",
    ),
    MetricSpec(
        "taste_accepted_suggestion_lift",
        "taste_accepted_suggestion_lift_min",
        "min",
    ),
)


def build_recalibration_note(
    *,
    scorecard: dict[str, Any],
    gold_report: dict[str, Any],
    lock_path: Path | str = DEFAULT_LOCK,
    evidence_tier: str,
    taste_scorecard: dict[str, Any] | None = None,
    gate_report: dict[str, Any] | None = None,
    timestamp: str | None = None,
    run_id: str | None = None,
    promote_release: bool = False,
) -> dict[str, Any]:
    """Build a public, redacted recalibration-log entry from private reports."""
    errors: list[str] = []
    if evidence_tier not in EVIDENCE_TIERS:
        errors.append(f"unknown_evidence_tier:{evidence_tier}")
    lock_hash = _file_sha256(Path(lock_path))

    reports = {
        "scorecard": scorecard,
        "gold_report": gold_report,
        "taste_scorecard": taste_scorecard or {},
        "gate": gate_report or {},
    }
    errors.extend(_privacy_errors(reports))
    errors.extend(
        _report_contract_errors(
            scorecard,
            gold_report,
            taste_scorecard,
            gate_report,
            expected_lock_hash=lock_hash,
            require_gate=promote_release,
        )
    )

    splits = _split_counts(gold_report)
    if evidence_tier == "tier2_private_holdout_canary" or promote_release:
        for split in ("calibration", "holdout", "canary"):
            if splits.get(split, 0) <= 0:
                errors.append(f"missing_private_split:{split}")

    metrics = _metric_snapshot(scorecard)
    metric_failures = _metric_failures(metrics)
    if metric_failures:
        errors.extend(f"metric_failed:{name}" for name in metric_failures)
    report_hashes = _report_hashes(
        scorecard=scorecard,
        gold_report=gold_report,
        taste_scorecard=taste_scorecard,
        gate_report=gate_report,
    )

    if promote_release:
        if evidence_tier != "tier2_private_holdout_canary":
            errors.append("release_promotion_requires_tier2_private_holdout_canary")
        verdict = "release_promoted" if not errors else "private_recalibration_required"
    elif metric_failures:
        verdict = "private_recalibration_required"
    else:
        verdict = "private_in_tolerance"

    action = (
        "PROMOTE_LOCK_WITH_PR"
        if verdict == "release_promoted"
        else "RECALIBRATION_REQUIRED"
        if verdict == "private_recalibration_required"
        else "none"
    )
    timestamp = timestamp or _now_iso()
    run_id = run_id or _default_run_id(timestamp, evidence_tier, scorecard, gold_report)
    label_kinds = _label_kind_counts(gold_report, taste_scorecard)
    entry = _render_entry(
        timestamp=timestamp,
        verdict=verdict,
        run_id=run_id,
        lock_hash=lock_hash,
        evidence_tier=evidence_tier,
        splits=splits,
        label_kinds=label_kinds,
        metrics=metrics,
        report_hashes=report_hashes,
        action=action,
    )
    return {
        "schema": "intel_recalibration_note_v1",
        "valid": not errors,
        "errors": tuple(errors),
        "verdict": verdict,
        "action": action,
        "report_hashes": report_hashes,
        "entry": entry,
    }


def _render_entry(
    *,
    timestamp: str,
    verdict: str,
    run_id: str,
    lock_hash: str,
    evidence_tier: str,
    splits: dict[str, int],
    label_kinds: dict[str, int],
    metrics: dict[str, dict[str, float]],
    report_hashes: dict[str, str],
    action: str,
) -> str:
    return "\n".join(
        [
            f"### {timestamp} - verdict={verdict}",
            f"- run_id: {run_id}",
            f"- lock: eval/INTEL-THRESHOLD-LOCK.md ({lock_hash})",
            f"- evidence_tier: {evidence_tier}",
            "- splits: "
            f"calibration={splits.get('calibration', 0)} "
            f"holdout={splits.get('holdout', 0)} "
            f"canary={splits.get('canary', 0)}",
            "- label_kinds: "
            f"section={label_kinds.get('section', 0)} "
            f"transition={label_kinds.get('transition', 0)} "
            f"cue={label_kinds.get('cue', 0)} "
            f"live_pill={label_kinds.get('live_pill', 0)} "
            f"representation={label_kinds.get('representation', 0)} "
            f"taste={label_kinds.get('taste', 0)}",
            "- reports: "
            f"gold_report={_report_label(report_hashes['gold_report'])} "
            f"scorecard={_report_label(report_hashes['scorecard'])} "
            f"taste_scorecard={_report_label(report_hashes['taste_scorecard'])} "
            f"gate={_report_label(report_hashes['gate'])}",
            "- report_hashes: " + _format_report_hashes(report_hashes),
            "- measured: " + _format_metric_line(metrics, "measured"),
            "- locked:   " + _format_metric_line(metrics, "locked"),
            "- delta:    " + _format_metric_line(metrics, "delta"),
            "- privacy: "
            "local_paths_redacted=true ids_hashed=true raw_audio_committed=false "
            "raw_vectors_committed=false free_form_notes_committed=false",
            f"- verdict: {verdict}",
            f"- action: {action}",
            "",
        ]
    )


def _format_report_hashes(report_hashes: dict[str, str]) -> str:
    return " ".join(f"{name}={report_hashes[name]}" for name in _REPORT_HASH_ORDER)


def _report_label(report_hash: str) -> str:
    return "null" if report_hash == "null" else "private:redacted"


def _format_metric_line(metrics: dict[str, dict[str, float]], field: str) -> str:
    parts: list[str] = []
    for spec in KEY_METRICS:
        key = spec.metric if field != "locked" else spec.threshold
        value = metrics[spec.metric][field]
        parts.append(f"{key}={value:+.2f}" if field == "delta" else f"{key}={value:.2f}")
    return " ".join(parts)


_REPORT_HASH_ORDER = ("gold_report", "scorecard", "taste_scorecard", "gate")


def _report_hashes(
    *,
    scorecard: dict[str, Any],
    gold_report: dict[str, Any],
    taste_scorecard: dict[str, Any] | None,
    gate_report: dict[str, Any] | None,
) -> dict[str, str]:
    return {
        "gold_report": _json_sha256(gold_report),
        "scorecard": _json_sha256(scorecard),
        "taste_scorecard": _json_sha256(taste_scorecard),
        "gate": _json_sha256(gate_report),
    }


def _json_sha256(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "null"
    blob = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _metric_snapshot(scorecard: dict[str, Any]) -> dict[str, dict[str, float]]:
    metrics = scorecard.get("metrics") if isinstance(scorecard.get("metrics"), dict) else {}
    thresholds = (
        scorecard.get("thresholds") if isinstance(scorecard.get("thresholds"), dict) else {}
    )
    out: dict[str, dict[str, float]] = {}
    for spec in KEY_METRICS:
        measured = _float(metrics.get(spec.metric))
        locked = _float(thresholds.get(spec.threshold))
        out[spec.metric] = {
            "measured": measured,
            "locked": locked,
            "delta": measured - locked,
        }
    return out


def _metric_failures(metrics: dict[str, dict[str, float]]) -> tuple[str, ...]:
    failures: list[str] = []
    for spec in KEY_METRICS:
        measured = metrics[spec.metric]["measured"]
        locked = metrics[spec.metric]["locked"]
        if spec.direction == "min" and measured < locked:
            failures.append(spec.metric)
        if spec.direction == "max" and measured > locked:
            failures.append(spec.metric)
    return tuple(failures)


def _report_contract_errors(
    scorecard: dict[str, Any],
    gold_report: dict[str, Any],
    taste_scorecard: dict[str, Any] | None,
    gate_report: dict[str, Any] | None,
    *,
    expected_lock_hash: str,
    require_gate: bool = False,
) -> tuple[str, ...]:
    errors: list[str] = []
    if scorecard.get("schema") != "intel_scorecard_v1":
        errors.append("scorecard.schema")
    if scorecard.get("privacy", {}).get("local_paths_redacted") is not True:
        errors.append("scorecard.privacy.local_paths_redacted")
    if gold_report.get("schema") != "intel_gold_report_v1":
        errors.append("gold_report.schema")
    privacy = gold_report.get("privacy", {})
    if privacy.get("local_paths_redacted") is not True:
        errors.append("gold_report.privacy.local_paths_redacted")
    if privacy.get("ids_hashed") is not True:
        errors.append("gold_report.privacy.ids_hashed")
    if taste_scorecard is not None:
        if taste_scorecard.get("schema") != "intel_taste_scorecard_v1":
            errors.append("taste_scorecard.schema")
        if taste_scorecard.get("privacy", {}).get("local_paths_redacted") is not True:
            errors.append("taste_scorecard.privacy.local_paths_redacted")
    if require_gate:
        errors.extend(_scorecard_promotion_errors(scorecard, expected_lock_hash))
    if require_gate and gate_report is None:
        errors.append("release_promotion_requires_gate_report")
    if gate_report is not None:
        if gate_report.get("schema") != "intel_gate_v1":
            errors.append("gate.schema")
        if require_gate:
            errors.extend(_gate_promotion_errors(gate_report, expected_lock_hash, scorecard))
    return tuple(errors)


def _scorecard_promotion_errors(
    scorecard: dict[str, Any], expected_lock_hash: str
) -> tuple[str, ...]:
    provenance = (
        scorecard.get("provenance") if isinstance(scorecard.get("provenance"), dict) else {}
    )
    threshold_lock = (
        provenance.get("threshold_lock")
        if isinstance(provenance.get("threshold_lock"), dict)
        else {}
    )
    errors: list[str] = []
    if scorecard.get("valid") is not True:
        errors.append("scorecard.valid")
    if scorecard.get("passed") is not True:
        errors.append("scorecard.passed")
    if threshold_lock.get("hash") != expected_lock_hash:
        errors.append("scorecard.provenance.threshold_lock.hash")
    if not provenance.get("thresholds_hash"):
        errors.append("scorecard.provenance.thresholds_hash")
    return tuple(errors)


def _gate_promotion_errors(
    gate_report: dict[str, Any],
    expected_lock_hash: str,
    scorecard_report: dict[str, Any],
) -> tuple[str, ...]:
    stages = gate_report.get("stages") if isinstance(gate_report.get("stages"), dict) else {}
    scorecard = stages.get("scorecard") if isinstance(stages.get("scorecard"), dict) else {}
    scorecard_provenance = (
        scorecard.get("provenance") if isinstance(scorecard.get("provenance"), dict) else {}
    )
    report_provenance = (
        scorecard_report.get("provenance")
        if isinstance(scorecard_report.get("provenance"), dict)
        else {}
    )
    provenance = stages.get("provenance") if isinstance(stages.get("provenance"), dict) else {}
    provenance_lock = (
        provenance.get("threshold_lock")
        if isinstance(provenance.get("threshold_lock"), dict)
        else {}
    )
    errors: list[str] = []
    if gate_report.get("valid") is not True:
        errors.append("gate.valid")
    if scorecard.get("valid") is not True:
        errors.append("gate.scorecard.valid")
    if scorecard.get("passed") is not True:
        errors.append("gate.scorecard.passed")
    if provenance.get("valid") is not True:
        errors.append("gate.provenance.valid")
    if scorecard_provenance.get("threshold_lock_hash") != expected_lock_hash:
        errors.append("gate.scorecard.threshold_lock_hash")
    if provenance_lock.get("hash") != expected_lock_hash:
        errors.append("gate.provenance.threshold_lock.hash")
    if report_provenance.get("thresholds_hash") and scorecard_provenance.get(
        "thresholds_hash"
    ) != report_provenance.get("thresholds_hash"):
        errors.append("gate.scorecard.thresholds_hash_mismatch")
    if report_provenance.get("thresholds_hash") and provenance.get(
        "thresholds_hash"
    ) != report_provenance.get("thresholds_hash"):
        errors.append("gate.provenance.thresholds_hash_mismatch")
    return tuple(errors)


def _privacy_errors(reports: dict[str, Any]) -> tuple[str, ...]:
    text = json.dumps(reports, sort_keys=True, default=str)
    return tuple(
        f"private_payload_present:{pattern.pattern}"
        for pattern in FORBIDDEN_PRIVATE_PATTERNS
        if pattern.search(text)
    )


def _split_counts(gold_report: dict[str, Any]) -> dict[str, int]:
    counts = gold_report.get("counts") if isinstance(gold_report.get("counts"), dict) else {}
    splits = counts.get("splits") if isinstance(counts.get("splits"), dict) else {}
    return {split: int(_float(splits.get(split))) for split in ("calibration", "holdout", "canary")}


def _label_kind_counts(
    gold_report: dict[str, Any],
    taste_scorecard: dict[str, Any] | None,
) -> dict[str, int]:
    counts = gold_report.get("counts") if isinstance(gold_report.get("counts"), dict) else {}
    kinds = counts.get("kinds") if isinstance(counts.get("kinds"), dict) else {}
    out = {
        kind: int(_float(kinds.get(kind)))
        for kind in ("section", "transition", "cue", "live_pill", "representation")
    }
    taste_counts = (
        taste_scorecard.get("counts")
        if taste_scorecard is not None and isinstance(taste_scorecard.get("counts"), dict)
        else {}
    )
    out["taste"] = int(_float(taste_counts.get("events")))
    return out


def _default_run_id(
    timestamp: str,
    evidence_tier: str,
    scorecard: dict[str, Any],
    gold_report: dict[str, Any],
) -> str:
    blob = json.dumps(
        {
            "timestamp": timestamp,
            "evidence_tier": evidence_tier,
            "scorecard_metrics": scorecard.get("metrics"),
            "gold_counts": gold_report.get("counts"),
        },
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    short = hashlib.sha256(blob).hexdigest()[:10]
    date = timestamp[:10].replace("-", "")
    return f"intel_private_{date}_{short}"


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_recalibration_note(
    log_path: Path | str,
    result: dict[str, Any],
    *,
    threshold_lock: Path | str = DEFAULT_LOCK,
) -> Path:
    """Append one valid rendered note to the public recalibration log."""
    if result.get("valid") is not True:
        raise ValueError("refusing to append invalid recalibration note")
    entry = str(result.get("entry") or "").strip()
    if not entry:
        raise ValueError("refusing to append empty recalibration note")
    path = Path(log_path)
    text = path.read_text(encoding="utf-8")
    if APPEND_MARKER not in text:
        raise ValueError(f"append marker missing from {path}")
    suffix = "" if text.endswith("\n") else "\n"
    candidate = f"{text}{suffix}\n{entry}\n"

    from scripts.eval.intel_recalibration_log_validate import validate_recalibration_log_text

    report = validate_recalibration_log_text(
        candidate,
        path=path,
        threshold_lock=threshold_lock,
    )
    if not report.valid:
        errors = ",".join(report.errors)
        raise ValueError(f"refusing to append invalid recalibration log: {errors}")
    path.write_text(candidate, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", type=Path, required=True)
    parser.add_argument("--gold-report", type=Path, required=True)
    parser.add_argument("--taste-scorecard", type=Path)
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--lock-path", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--evidence-tier", choices=sorted(EVIDENCE_TIERS), required=True)
    parser.add_argument("--timestamp")
    parser.add_argument("--run-id")
    parser.add_argument("--promote-release", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--append-log", type=Path, help="Append the valid entry to the log")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = build_recalibration_note(
        scorecard=_load_json(args.scorecard),
        gold_report=_load_json(args.gold_report),
        taste_scorecard=_load_json(args.taste_scorecard) if args.taste_scorecard else None,
        gate_report=_load_json(args.gate) if args.gate else None,
        lock_path=args.lock_path,
        evidence_tier=args.evidence_tier,
        timestamp=args.timestamp,
        run_id=args.run_id,
        promote_release=args.promote_release,
    )
    if result["valid"]:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result["entry"], encoding="utf-8")
        if args.append_log:
            append_recalibration_note(args.append_log, result, threshold_lock=args.lock_path)
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(result["entry"])
        if result["errors"]:
            sys.stderr.write("\n".join(str(error) for error in result["errors"]) + "\n")
    return 0 if result["valid"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
