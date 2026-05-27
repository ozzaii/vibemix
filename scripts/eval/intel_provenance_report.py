# SPDX-License-Identifier: Apache-2.0
"""Validate public-safe provenance emitted by INTEL scorecards."""

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

LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[^\"'\s]+"),
    re.compile(r"/Volumes/[^\"'\s]+"),
    re.compile(r"[A-Za-z]:\\\\[^\"'\s]+"),
    re.compile(r"file://[^\"'\s]+"),
)


@dataclass(frozen=True, slots=True)
class ProvenanceReport:
    valid: bool
    errors: tuple[str, ...]
    summary: dict[str, Any]


def validate_scorecard_provenance(
    scorecard: dict[str, Any],
    *,
    fixture_dir: Path | str | None = None,
    threshold_lock: Path | str | None = None,
) -> ProvenanceReport:
    errors: list[str] = []
    if scorecard.get("schema") != "intel_scorecard_v1":
        errors.append("scorecard schema must be intel_scorecard_v1")
    if scorecard.get("valid") is not True:
        errors.append("scorecard valid must be true")

    provenance = scorecard.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("missing provenance object")
        provenance = {}

    errors.extend(_validate_no_local_paths(scorecard))
    errors.extend(_validate_required_provenance(provenance))
    errors.extend(_validate_hashes(scorecard, provenance, fixture_dir, threshold_lock))

    summary = {
        "schema": "intel_provenance_report_v1",
        "scorecard_schema": scorecard.get("schema"),
        "eval_run_id": provenance.get("eval_run_id"),
        "suite": provenance.get("suite"),
        "dataset_card_id": provenance.get("dataset_card_id"),
        "fixture_version": provenance.get("fixture_version"),
        "replay_tier": provenance.get("replay_tier"),
        "threshold_lock": provenance.get("threshold_lock"),
        "fixture_manifest_hash": provenance.get("fixture_manifest_hash"),
        "thresholds_hash": provenance.get("thresholds_hash"),
    }
    return ProvenanceReport(valid=not errors, errors=tuple(errors), summary=summary)


def _validate_no_local_paths(value: Any) -> list[str]:
    text = json.dumps(value, sort_keys=True, default=str)
    errors = []
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(text):
            errors.append(
                f"public provenance contains local/private path pattern {pattern.pattern}"
            )
    return errors


def _validate_required_provenance(provenance: dict[str, Any]) -> list[str]:
    errors = []
    required_strings = (
        "eval_run_id",
        "suite",
        "scorecard_schema",
        "dataset_card_id",
        "fixture_version",
        "fixture_manifest_hash",
        "thresholds_hash",
        "replay_tier",
        "replay_command",
    )
    for key in required_strings:
        if not isinstance(provenance.get(key), str) or not provenance.get(key):
            errors.append(f"provenance.{key} must be a non-empty string")

    if not str(provenance.get("eval_run_id", "")).startswith("eval_intel_scorecard_"):
        errors.append("provenance.eval_run_id must start with eval_intel_scorecard_")
    if provenance.get("suite") != "intel_scorecard":
        errors.append("provenance.suite must be intel_scorecard")
    if provenance.get("scorecard_schema") != "intel_scorecard_v1":
        errors.append("provenance.scorecard_schema must be intel_scorecard_v1")
    if provenance.get("replay_tier") != "tier0_fixture_replay":
        errors.append("provenance.replay_tier must be tier0_fixture_replay")

    for key in ("fixture_manifest_hash", "thresholds_hash"):
        if not str(provenance.get(key, "")).startswith("sha256:"):
            errors.append(f"provenance.{key} must be a sha256: hash")

    replay_command = str(provenance.get("replay_command", ""))
    if "--threshold-lock" not in replay_command:
        errors.append("provenance.replay_command must include --threshold-lock")
    if "--fixture-dir" not in replay_command:
        errors.append("provenance.replay_command must include --fixture-dir")

    threshold_lock = provenance.get("threshold_lock")
    if not isinstance(threshold_lock, dict):
        errors.append("provenance.threshold_lock must be an object")
    else:
        if threshold_lock.get("source") != "threshold_lock":
            errors.append("provenance.threshold_lock.source must be threshold_lock")
        if threshold_lock.get("namespace") != "intel_thresholds":
            errors.append("provenance.threshold_lock.namespace must be intel_thresholds")
        path = threshold_lock.get("path")
        if not isinstance(path, str) or not path:
            errors.append("provenance.threshold_lock.path must be a non-empty string")
        elif Path(path).is_absolute():
            errors.append("provenance.threshold_lock.path must be project-relative")
        if not str(threshold_lock.get("hash", "")).startswith("sha256:"):
            errors.append("provenance.threshold_lock.hash must be a sha256: hash")

    privacy = provenance.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("provenance.privacy must be an object")
    else:
        expected_privacy = {
            "local_paths_redacted": True,
            "contains_raw_audio": False,
            "contains_raw_vectors": False,
        }
        for key, expected in expected_privacy.items():
            if privacy.get(key) is not expected:
                errors.append(f"provenance.privacy.{key} must be {expected!r}")

    return errors


def _validate_hashes(
    scorecard: dict[str, Any],
    provenance: dict[str, Any],
    fixture_dir: Path | str | None,
    threshold_lock: Path | str | None,
) -> list[str]:
    errors = []
    thresholds_hash = _mapping_hash(scorecard.get("thresholds", {}))
    if provenance.get("thresholds_hash") != thresholds_hash:
        errors.append("provenance.thresholds_hash does not match scorecard thresholds")

    if fixture_dir is not None:
        manifest = Path(fixture_dir) / "MANIFEST.json"
        if not manifest.exists():
            errors.append(f"fixture MANIFEST.json missing: {_safe_path_label(manifest)}")
        else:
            actual = _file_sha256(manifest)
            if provenance.get("fixture_manifest_hash") != actual:
                errors.append("provenance.fixture_manifest_hash does not match fixture manifest")

    if threshold_lock is not None:
        lock_path = Path(threshold_lock)
        lock = provenance.get("threshold_lock") if isinstance(provenance, dict) else None
        if not lock_path.exists():
            errors.append(f"threshold lock missing: {_safe_path_label(lock_path)}")
        elif not isinstance(lock, dict):
            errors.append("cannot verify threshold lock hash without threshold_lock object")
        else:
            actual = _file_sha256(lock_path)
            if lock.get("hash") != actual:
                errors.append("provenance.threshold_lock.hash does not match threshold lock file")
            if lock.get("path") != _safe_path_label(lock_path):
                errors.append("provenance.threshold_lock.path does not match threshold lock file")

    return errors


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _safe_path_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _load_scorecard(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"scorecard must be a JSON object: {path}")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a scorecard provenance block")
    validate.add_argument("scorecard", type=Path)
    validate.add_argument("--fixture-dir", type=Path)
    validate.add_argument("--threshold-lock", type=Path)
    validate.add_argument("--json", action="store_true", help="Emit machine-readable report")

    args = parser.parse_args(argv)
    scorecard = _load_scorecard(args.scorecard)
    report = validate_scorecard_provenance(
        scorecard,
        fixture_dir=args.fixture_dir,
        threshold_lock=args.threshold_lock,
    )
    payload = {
        **report.summary,
        "valid": report.valid,
        "errors": list(report.errors),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif report.valid:
        print(f"INTEL provenance valid: {report.summary.get('eval_run_id')}")
    else:
        for error in report.errors:
            print(f"[intel-provenance] {error}", file=sys.stderr)
    return 0 if report.valid else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
