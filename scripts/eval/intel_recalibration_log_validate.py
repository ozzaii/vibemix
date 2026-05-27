# SPDX-License-Identifier: Apache-2.0
"""Validate the public INTEL threshold recalibration log."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.intel_recalibration_note import (  # noqa: E402
    APPEND_MARKER,
    DEFAULT_LOCK,
    EVIDENCE_TIERS,
    FORBIDDEN_PRIVATE_PATTERNS,
    KEY_METRICS,
    RUN_ID_RE,
)

DEFAULT_LOG = ROOT / "eval" / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
LOCK_FIELD_PREFIX = "eval/INTEL-THRESHOLD-LOCK.md ("

ENTRY_RE = re.compile(
    r"^### (?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"- verdict=(?P<verdict>[a-z_]+)$"
)
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
SIGNED_NUMBER_RE = re.compile(r"^[+-]\d+(?:\.\d+)?$")
REPORT_HASH_KEYS = ("gold_report", "scorecard", "taste_scorecard", "gate")
ALWAYS_REQUIRED_REPORT_HASHES = ("gold_report", "scorecard")
SPLIT_KEYS = ("calibration", "holdout", "canary")
LABEL_KIND_KEYS = ("section", "transition", "cue", "live_pill", "representation", "taste")
REQUIRED_FIELDS = (
    "run_id",
    "lock",
    "evidence_tier",
    "splits",
    "label_kinds",
    "reports",
    "report_hashes",
    "measured",
    "locked",
    "delta",
    "privacy",
    "verdict",
    "action",
)
ALLOWED_VERDICTS = (
    "private_in_tolerance",
    "private_recalibration_required",
    "release_promoted",
)
ALLOWED_ACTIONS = ("none", "RECALIBRATION_REQUIRED", "PROMOTE_LOCK_WITH_PR")
EXPECTED_PRIVACY = {
    "local_paths_redacted": "true",
    "ids_hashed": "true",
    "raw_audio_committed": "false",
    "raw_vectors_committed": "false",
    "free_form_notes_committed": "false",
}


@dataclass(frozen=True, slots=True)
class LogValidationReport:
    valid: bool
    errors: tuple[str, ...]
    summary: dict[str, Any]


def validate_recalibration_log(
    path: Path | str = DEFAULT_LOG,
    *,
    threshold_lock: Path | str | None = DEFAULT_LOCK,
) -> LogValidationReport:
    """Validate schema, privacy, and hash bindings in the public log."""
    log_path = Path(path)
    text = log_path.read_text(encoding="utf-8")
    return validate_recalibration_log_text(text, path=log_path, threshold_lock=threshold_lock)


def validate_recalibration_log_text(
    text: str,
    *,
    path: Path | str = DEFAULT_LOG,
    threshold_lock: Path | str | None = DEFAULT_LOCK,
) -> LogValidationReport:
    """Validate schema, privacy, and hash bindings in public log text."""
    log_path = Path(path)
    errors = _privacy_errors(text)
    lock_path = Path(threshold_lock) if threshold_lock is not None else None
    expected_lock_hash = _expected_lock_hash(lock_path, errors)
    if APPEND_MARKER not in text:
        errors.append("append_marker_missing")
        return _report(
            path=log_path,
            entries=0,
            errors=errors,
            threshold_lock=lock_path,
            threshold_lock_hash=expected_lock_hash,
        )

    real_tail = text.split(APPEND_MARKER, maxsplit=1)[1].strip()
    entries = _parse_entries(real_tail)
    seen_run_ids: set[str] = set()
    previous_timestamp: str | None = None
    for index, entry in enumerate(entries, start=1):
        errors.extend(_validate_entry(entry, index=index, expected_lock_hash=expected_lock_hash))
        timestamp, run_id = _entry_sequence_metadata(entry)
        if timestamp is not None:
            if previous_timestamp is not None and timestamp < previous_timestamp:
                errors.append(f"entry[{index}].timestamp.out_of_order")
            previous_timestamp = timestamp
        if run_id:
            if run_id in seen_run_ids:
                errors.append(f"entry[{index}].run_id.duplicate")
            seen_run_ids.add(run_id)
    return _report(
        path=log_path,
        entries=len(entries),
        errors=errors,
        threshold_lock=lock_path,
        threshold_lock_hash=expected_lock_hash,
    )


def _parse_entries(text: str) -> list[str]:
    if not text:
        return []
    return [
        (chunk.strip() if chunk.startswith("### ") else "### " + chunk.strip())
        for chunk in text.split("\n### ")
        if chunk.strip()
    ]


def _validate_entry(entry: str, *, index: int, expected_lock_hash: str | None) -> list[str]:
    lines = [line.rstrip() for line in entry.splitlines() if line.strip()]
    errors: list[str] = []
    if not lines:
        return [f"entry[{index}].empty"]

    header = ENTRY_RE.match(lines[0])
    if header is None:
        errors.append(f"entry[{index}].header")
        header_verdict = ""
        header_timestamp = ""
    else:
        header_verdict = header.group("verdict")
        header_timestamp = header.group("timestamp")
        if header_verdict not in ALLOWED_VERDICTS:
            errors.append(f"entry[{index}].header.verdict")

    fields = _entry_fields(lines[1:], index=index, errors=errors)
    for field in REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"entry[{index}].missing:{field}")

    if not _run_id_valid(str(fields.get("run_id", "")), header_timestamp):
        errors.append(f"entry[{index}].run_id")
    lock_digest = _lock_field_digest(fields.get("lock", ""))
    if lock_digest is None:
        errors.append(f"entry[{index}].lock")
    elif expected_lock_hash is not None and lock_digest != expected_lock_hash:
        errors.append(f"entry[{index}].lock.hash_mismatch")
    if fields.get("evidence_tier") not in EVIDENCE_TIERS:
        errors.append(f"entry[{index}].evidence_tier")
    if (
        header_verdict == "release_promoted"
        and fields.get("evidence_tier") != "tier2_private_holdout_canary"
    ):
        errors.append(f"entry[{index}].release_evidence_tier")

    splits = _parse_key_values(
        fields.get("splits", ""),
        field="splits",
        index=index,
        errors=errors,
        expected_keys=SPLIT_KEYS,
    )
    for split in SPLIT_KEYS:
        if split not in splits or not splits[split].isdigit():
            errors.append(f"entry[{index}].splits.{split}")
    if (
        fields.get("evidence_tier") == "tier2_private_holdout_canary"
        or header_verdict == "release_promoted"
    ):
        for split in SPLIT_KEYS:
            if int(splits.get(split, "0")) <= 0:
                errors.append(f"entry[{index}].splits.{split}.empty")

    label_kinds = _parse_key_values(
        fields.get("label_kinds", ""),
        field="label_kinds",
        index=index,
        errors=errors,
        expected_keys=LABEL_KIND_KEYS,
    )
    for kind in LABEL_KIND_KEYS:
        if kind not in label_kinds or not label_kinds[kind].isdigit():
            errors.append(f"entry[{index}].label_kinds.{kind}")

    errors.extend(_validate_report_bindings(fields, index=index, verdict=header_verdict))
    metric_errors, metric_failures = _validate_metric_lines(fields, index=index)
    errors.extend(metric_errors)

    privacy = _parse_key_values(
        fields.get("privacy", ""),
        field="privacy",
        index=index,
        errors=errors,
        expected_keys=tuple(EXPECTED_PRIVACY),
    )
    for key, expected in EXPECTED_PRIVACY.items():
        if privacy.get(key) != expected:
            errors.append(f"entry[{index}].privacy.{key}")

    if fields.get("verdict") != header_verdict:
        errors.append(f"entry[{index}].verdict_mismatch")
    if fields.get("action") not in ALLOWED_ACTIONS:
        errors.append(f"entry[{index}].action")
    if header_verdict == "release_promoted" and fields.get("action") != "PROMOTE_LOCK_WITH_PR":
        errors.append(f"entry[{index}].release_action")
    if (
        header_verdict == "private_recalibration_required"
        and fields.get("action") != "RECALIBRATION_REQUIRED"
    ):
        errors.append(f"entry[{index}].recalibration_action")
    if header_verdict == "private_in_tolerance" and fields.get("action") != "none":
        errors.append(f"entry[{index}].tolerance_action")
    if header_verdict != "release_promoted" and fields.get("action") == "PROMOTE_LOCK_WITH_PR":
        errors.append(f"entry[{index}].action_without_release")
    if metric_failures and header_verdict != "private_recalibration_required":
        errors.append(f"entry[{index}].verdict.metric_failures:{','.join(metric_failures)}")
    if header_verdict == "private_recalibration_required" and not metric_failures:
        errors.append(f"entry[{index}].verdict.no_metric_failures")
    return errors


def _entry_sequence_metadata(entry: str) -> tuple[str | None, str | None]:
    lines = [line.rstrip() for line in entry.splitlines() if line.strip()]
    if not lines:
        return None, None
    header = ENTRY_RE.match(lines[0])
    timestamp = header.group("timestamp") if header is not None else None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if not line.startswith("- ") or ": " not in line:
            continue
        key, value = line[2:].split(": ", maxsplit=1)
        fields.setdefault(key, value)
    return timestamp, fields.get("run_id")


def _validate_metric_lines(fields: dict[str, str], *, index: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    failures: list[str] = []
    measured = _parse_key_values(
        fields.get("measured", ""),
        field="measured",
        index=index,
        errors=errors,
        expected_keys=tuple(spec.metric for spec in KEY_METRICS),
    )
    locked = _parse_key_values(
        fields.get("locked", ""),
        field="locked",
        index=index,
        errors=errors,
        expected_keys=tuple(spec.threshold for spec in KEY_METRICS),
    )
    delta = _parse_key_values(
        fields.get("delta", ""),
        field="delta",
        index=index,
        errors=errors,
        expected_keys=tuple(spec.metric for spec in KEY_METRICS),
    )
    for spec in KEY_METRICS:
        measured_value = _metric_value(
            measured,
            spec.metric,
            field="measured",
            index=index,
            errors=errors,
        )
        locked_value = _metric_value(
            locked,
            spec.threshold,
            field="locked",
            index=index,
            errors=errors,
        )
        delta_value = _metric_value(
            delta,
            spec.metric,
            field="delta",
            index=index,
            errors=errors,
            require_sign=True,
        )
        if measured_value is None or locked_value is None or delta_value is None:
            continue
        expected_delta = measured_value - locked_value
        if abs(delta_value - expected_delta) > 0.011:
            errors.append(f"entry[{index}].delta.{spec.metric}.mismatch")
        if spec.direction == "min" and measured_value < locked_value:
            failures.append(spec.metric)
        if spec.direction == "max" and measured_value > locked_value:
            failures.append(spec.metric)
    return errors, failures


def _metric_value(
    values: dict[str, str],
    key: str,
    *,
    field: str,
    index: int,
    errors: list[str],
    require_sign: bool = False,
) -> float | None:
    raw = values.get(key)
    if raw is None:
        errors.append(f"entry[{index}].{field}.{key}")
        return None
    pattern = SIGNED_NUMBER_RE if require_sign else NUMBER_RE
    if pattern.match(raw) is None:
        errors.append(f"entry[{index}].{field}.{key}.numeric")
        return None
    return float(raw)


def _entry_fields(lines: list[str], *, index: int, errors: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        if not line.startswith("- ") or ": " not in line:
            errors.append(f"entry[{index}].line")
            continue
        key, value = line[2:].split(": ", maxsplit=1)
        if key in fields:
            errors.append(f"entry[{index}].duplicate:{key}")
        fields[key] = value
    return fields


def _lock_field_digest(value: str) -> str | None:
    digest = (
        value[len(LOCK_FIELD_PREFIX) : -1]
        if value.startswith(LOCK_FIELD_PREFIX) and value.endswith(")")
        else ""
    )
    return digest if digest and SHA_RE.match(digest) is not None else None


def _run_id_valid(value: str, timestamp: str) -> bool:
    match = RUN_ID_RE.match(value)
    if match is None:
        return False
    return match.group("date") == timestamp[:10].replace("-", "")


def _validate_report_bindings(fields: dict[str, str], *, index: int, verdict: str) -> list[str]:
    errors: list[str] = []
    reports = _parse_key_values(
        fields.get("reports", ""),
        field="reports",
        index=index,
        errors=errors,
        expected_keys=REPORT_HASH_KEYS,
    )
    hashes = _parse_key_values(
        fields.get("report_hashes", ""),
        field="report_hashes",
        index=index,
        errors=errors,
        expected_keys=REPORT_HASH_KEYS,
    )
    for key in REPORT_HASH_KEYS:
        report = reports.get(key)
        digest = hashes.get(key)
        if report not in {"private:redacted", "null"}:
            errors.append(f"entry[{index}].reports.{key}")
        if digest is None:
            errors.append(f"entry[{index}].report_hashes.{key}")
        elif digest != "null" and SHA_RE.match(digest) is None:
            errors.append(f"entry[{index}].report_hashes.{key}")
        if report == "null" and digest != "null":
            errors.append(f"entry[{index}].report_binding.{key}")
        if report == "private:redacted" and (digest is None or digest == "null"):
            errors.append(f"entry[{index}].report_binding.{key}")
    required_hashes = list(ALWAYS_REQUIRED_REPORT_HASHES)
    if verdict == "release_promoted":
        required_hashes.append("gate")
    for key in required_hashes:
        if reports.get(key) != "private:redacted":
            errors.append(f"entry[{index}].reports.{key}.required")
        if SHA_RE.match(hashes.get(key, "")) is None:
            errors.append(f"entry[{index}].report_hashes.{key}.required")
    return errors


def _parse_key_values(
    value: str,
    *,
    field: str,
    index: int,
    errors: list[str],
    expected_keys: tuple[str, ...],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in value.split():
        if "=" not in part:
            errors.append(f"entry[{index}].{field}.token")
            continue
        key, raw = part.split("=", maxsplit=1)
        if not key or raw == "":
            errors.append(f"entry[{index}].{field}.token")
            continue
        if key not in expected_keys:
            errors.append(f"entry[{index}].{field}.unknown:{key}")
            continue
        if key in out:
            errors.append(f"entry[{index}].{field}.duplicate:{key}")
            continue
        out[key] = raw
    return out


def _privacy_errors(text: str) -> list[str]:
    return [
        f"private_payload_present:{pattern.pattern}"
        for pattern in FORBIDDEN_PRIVATE_PATTERNS
        if pattern.search(text)
    ]


def _expected_lock_hash(lock_path: Path | None, errors: list[str]) -> str | None:
    if lock_path is None:
        return None
    try:
        return "sha256:" + hashlib.sha256(lock_path.read_bytes()).hexdigest()
    except OSError:
        errors.append(f"threshold_lock_unreadable:{_safe_path_label(lock_path)}")
        return None


def _report(
    path: Path,
    entries: int,
    errors: list[str],
    *,
    threshold_lock: Path | None,
    threshold_lock_hash: str | None,
) -> LogValidationReport:
    return LogValidationReport(
        valid=not errors,
        errors=tuple(errors),
        summary={
            "schema": "intel_recalibration_log_validation_v1",
            "path": _safe_path_label(path),
            "entry_count": entries,
            "threshold_lock": _safe_path_label(threshold_lock) if threshold_lock else None,
            "threshold_lock_hash": threshold_lock_hash,
        },
    )


def _safe_path_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--threshold-lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = validate_recalibration_log(args.log, threshold_lock=args.threshold_lock)
    payload = {
        **report.summary,
        "valid": report.valid,
        "errors": list(report.errors),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif report.valid:
        print(
            "INTEL recalibration log valid: "
            f"{report.summary['path']} ({report.summary['entry_count']} entries)"
        )
    else:
        for error in report.errors:
            print(f"[intel-recalibration-log] {error}", file=sys.stderr)
    return 0 if report.valid else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
