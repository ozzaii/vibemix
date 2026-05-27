# SPDX-License-Identifier: Apache-2.0
"""Validate the public INTEL threshold recalibration log."""

from __future__ import annotations

import argparse
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
    EVIDENCE_TIERS,
    FORBIDDEN_PRIVATE_PATTERNS,
    KEY_METRICS,
)

DEFAULT_LOG = ROOT / "eval" / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"

ENTRY_RE = re.compile(
    r"^### (?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"- verdict=(?P<verdict>[a-z_]+)$"
)
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
SIGNED_NUMBER_RE = re.compile(r"^[+-]\d+(?:\.\d+)?$")
REPORT_HASH_KEYS = ("gold_report", "scorecard", "taste_scorecard", "gate")
ALWAYS_REQUIRED_REPORT_HASHES = ("gold_report", "scorecard")
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


def validate_recalibration_log(path: Path | str = DEFAULT_LOG) -> LogValidationReport:
    """Validate schema, privacy, and report-hash bindings in the public log."""
    log_path = Path(path)
    text = log_path.read_text(encoding="utf-8")
    errors = _privacy_errors(text)
    if APPEND_MARKER not in text:
        errors.append("append_marker_missing")
        return _report(path=log_path, entries=0, errors=errors)

    real_tail = text.split(APPEND_MARKER, maxsplit=1)[1].strip()
    entries = _parse_entries(real_tail)
    for index, entry in enumerate(entries, start=1):
        errors.extend(_validate_entry(entry, index=index))
    return _report(path=log_path, entries=len(entries), errors=errors)


def _parse_entries(text: str) -> list[str]:
    if not text:
        return []
    return [
        (chunk.strip() if chunk.startswith("### ") else "### " + chunk.strip())
        for chunk in text.split("\n### ")
        if chunk.strip()
    ]


def _validate_entry(entry: str, *, index: int) -> list[str]:
    lines = [line.rstrip() for line in entry.splitlines() if line.strip()]
    errors: list[str] = []
    if not lines:
        return [f"entry[{index}].empty"]

    header = ENTRY_RE.match(lines[0])
    if header is None:
        errors.append(f"entry[{index}].header")
        header_verdict = ""
    else:
        header_verdict = header.group("verdict")
        if header_verdict not in ALLOWED_VERDICTS:
            errors.append(f"entry[{index}].header.verdict")

    fields = _entry_fields(lines[1:], index=index, errors=errors)
    for field in REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"entry[{index}].missing:{field}")

    if not str(fields.get("run_id", "")).startswith("intel_private_"):
        errors.append(f"entry[{index}].run_id")
    if not _lock_field_valid(fields.get("lock", "")):
        errors.append(f"entry[{index}].lock")
    if fields.get("evidence_tier") not in EVIDENCE_TIERS:
        errors.append(f"entry[{index}].evidence_tier")

    splits = _parse_key_values(fields.get("splits", ""))
    for split in ("calibration", "holdout", "canary"):
        if split not in splits or not splits[split].isdigit():
            errors.append(f"entry[{index}].splits.{split}")
    if (
        fields.get("evidence_tier") == "tier2_private_holdout_canary"
        or header_verdict == "release_promoted"
    ):
        for split in ("calibration", "holdout", "canary"):
            if int(splits.get(split, "0")) <= 0:
                errors.append(f"entry[{index}].splits.{split}.empty")

    label_kinds = _parse_key_values(fields.get("label_kinds", ""))
    for kind in ("section", "transition", "cue", "live_pill", "representation", "taste"):
        if kind not in label_kinds or not label_kinds[kind].isdigit():
            errors.append(f"entry[{index}].label_kinds.{kind}")

    errors.extend(_validate_report_bindings(fields, index=index, verdict=header_verdict))
    metric_errors, metric_failures = _validate_metric_lines(fields, index=index)
    errors.extend(metric_errors)

    privacy = _parse_key_values(fields.get("privacy", ""))
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


def _validate_metric_lines(fields: dict[str, str], *, index: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    failures: list[str] = []
    measured = _parse_key_values(fields.get("measured", ""))
    locked = _parse_key_values(fields.get("locked", ""))
    delta = _parse_key_values(fields.get("delta", ""))
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


def _lock_field_valid(value: str) -> bool:
    prefix = "eval/INTEL-THRESHOLD-LOCK.md ("
    digest = value[len(prefix) : -1] if value.startswith(prefix) and value.endswith(")") else ""
    return bool(digest and SHA_RE.match(digest))


def _validate_report_bindings(fields: dict[str, str], *, index: int, verdict: str) -> list[str]:
    errors: list[str] = []
    reports = _parse_key_values(fields.get("reports", ""))
    hashes = _parse_key_values(fields.get("report_hashes", ""))
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


def _parse_key_values(value: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in value.split():
        if "=" not in part:
            continue
        key, raw = part.split("=", maxsplit=1)
        out[key] = raw
    return out


def _privacy_errors(text: str) -> list[str]:
    return [
        f"private_payload_present:{pattern.pattern}"
        for pattern in FORBIDDEN_PRIVATE_PATTERNS
        if pattern.search(text)
    ]


def _report(path: Path, entries: int, errors: list[str]) -> LogValidationReport:
    return LogValidationReport(
        valid=not errors,
        errors=tuple(errors),
        summary={
            "schema": "intel_recalibration_log_validation_v1",
            "path": _safe_path_label(path),
            "entry_count": entries,
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = validate_recalibration_log(args.log)
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
