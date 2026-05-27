# SPDX-License-Identifier: Apache-2.0
"""Run the public INTEL fixture gate end to end."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"
DEFAULT_THRESHOLD_LOCK = ROOT / "eval" / "INTEL-THRESHOLD-LOCK.md"


def run_intel_gate(
    *,
    fixture_dir: Path | str = DEFAULT_FIXTURE_DIR,
    threshold_lock: Path | str = DEFAULT_THRESHOLD_LOCK,
) -> dict[str, Any]:
    from scripts.eval.intel_fixture_audit import validate_fixture_dir
    from scripts.eval.intel_provenance_report import validate_scorecard_provenance
    from scripts.eval.intel_scorecard import load_intel_thresholds_from_lock, score_fixture_dir

    fixture_path = Path(fixture_dir)
    lock_path = Path(threshold_lock)
    errors: list[str] = []

    fixture_audit = validate_fixture_dir(fixture_path)
    fixture_result = {
        "valid": fixture_audit.valid,
        "errors": list(fixture_audit.errors),
        "files_checked": fixture_audit.files_checked,
        "manifest_hash": fixture_audit.manifest_hash,
    }
    if not fixture_audit.valid:
        errors.extend(f"fixture_audit: {error}" for error in fixture_audit.errors)

    scorecard: dict[str, Any] | None = None
    try:
        thresholds = load_intel_thresholds_from_lock(lock_path)
        scorecard = score_fixture_dir(
            fixture_path,
            thresholds=thresholds,
            threshold_lock_path=lock_path,
        )
        scorecard_errors = _scorecard_errors(scorecard)
        errors.extend(scorecard_errors)
        scorecard_provenance = scorecard.get("provenance") or {}
        threshold_lock_provenance = (
            scorecard_provenance.get("threshold_lock")
            if isinstance(scorecard_provenance, dict)
            else {}
        )
        if not isinstance(threshold_lock_provenance, dict):
            threshold_lock_provenance = {}
        scorecard_result = {
            "valid": bool(scorecard.get("valid")),
            "passed": bool(scorecard.get("passed")),
            "errors": scorecard_errors,
            "eval_run_id": scorecard.get("provenance", {}).get("eval_run_id"),
            "artifact_status": scorecard.get("artifact_status", {}),
            "metrics": scorecard.get("metrics", {}),
            "gates": scorecard.get("gates", ()),
            "provenance": {
                "dataset_card_id": scorecard_provenance.get("dataset_card_id"),
                "fixture_version": scorecard_provenance.get("fixture_version"),
                "fixture_manifest_hash": scorecard_provenance.get("fixture_manifest_hash"),
                "thresholds_hash": scorecard_provenance.get("thresholds_hash"),
                "threshold_lock_path": threshold_lock_provenance.get("path"),
                "threshold_lock_hash": threshold_lock_provenance.get("hash"),
                "replay_tier": scorecard_provenance.get("replay_tier"),
            },
        }
    except Exception as exc:
        errors.append(f"scorecard: {type(exc).__name__}: {exc}")
        scorecard_result = {
            "valid": False,
            "passed": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "eval_run_id": None,
        }

    if scorecard is None:
        provenance_result = {
            "valid": False,
            "errors": ["provenance: scorecard unavailable"],
            "eval_run_id": None,
        }
        errors.append("provenance: scorecard unavailable")
    else:
        provenance = validate_scorecard_provenance(
            scorecard,
            fixture_dir=fixture_path,
            threshold_lock=lock_path,
        )
        provenance_result = {
            **provenance.summary,
            "valid": provenance.valid,
            "errors": list(provenance.errors),
        }
        if not provenance.valid:
            errors.extend(f"provenance: {error}" for error in provenance.errors)

    consistency_errors = _cross_stage_consistency_errors(
        fixture_result,
        scorecard_result,
        provenance_result,
    )
    if consistency_errors:
        errors.extend(consistency_errors)
        scorecard_result["errors"] = [*scorecard_result.get("errors", []), *consistency_errors]
        provenance_result["errors"] = [
            *provenance_result.get("errors", []),
            *consistency_errors,
        ]

    return {
        "schema": "intel_gate_v1",
        "valid": not errors,
        "fixture_dir": _safe_path_label(fixture_path),
        "threshold_lock": _safe_path_label(lock_path),
        "errors": errors,
        "stages": {
            "fixture_audit": fixture_result,
            "scorecard": scorecard_result,
            "provenance": provenance_result,
        },
    }


def _scorecard_errors(scorecard: dict[str, Any]) -> list[str]:
    errors = []
    if scorecard.get("valid") is not True:
        failing = sorted(
            name
            for name, status in dict(scorecard.get("artifact_status") or {}).items()
            if not status
        )
        errors.append(f"scorecard: invalid artifacts {failing}")
    if scorecard.get("passed") is not True:
        failing_gates = [
            str(gate.get("metric"))
            for gate in scorecard.get("gates", ())
            if isinstance(gate, dict) and gate.get("status") != "PASS"
        ]
        errors.append(f"scorecard: failing gates {failing_gates}")
    return errors


def _cross_stage_consistency_errors(
    fixture_result: dict[str, Any],
    scorecard_result: dict[str, Any],
    provenance_result: dict[str, Any],
) -> list[str]:
    scorecard_provenance = (
        scorecard_result.get("provenance")
        if isinstance(scorecard_result.get("provenance"), dict)
        else {}
    )
    errors = []
    _require_equal(
        errors,
        "fixture_audit.manifest_hash",
        fixture_result.get("manifest_hash"),
        "scorecard.provenance.fixture_manifest_hash",
        scorecard_provenance.get("fixture_manifest_hash"),
    )
    for key in (
        "dataset_card_id",
        "fixture_version",
        "fixture_manifest_hash",
        "thresholds_hash",
        "replay_tier",
    ):
        _require_equal(
            errors,
            f"scorecard.provenance.{key}",
            scorecard_provenance.get(key),
            f"provenance.{key}",
            provenance_result.get(key),
        )
    _require_equal(
        errors,
        "scorecard.provenance.threshold_lock_hash",
        scorecard_provenance.get("threshold_lock_hash"),
        "provenance.threshold_lock.hash",
        (
            provenance_result.get("threshold_lock", {}).get("hash")
            if isinstance(provenance_result.get("threshold_lock"), dict)
            else None
        ),
    )
    return errors


def _require_equal(
    errors: list[str],
    left_label: str,
    left: Any,
    right_label: str,
    right: Any,
) -> None:
    if not left or not right:
        errors.append(f"provenance_consistency: {left_label} or {right_label} missing")
    elif left != right:
        errors.append(f"provenance_consistency: {left_label} != {right_label}")


def render_markdown_summary(result: dict[str, Any]) -> str:
    status = "PASS" if result.get("valid") else "FAIL"
    stages = result.get("stages", {})
    scorecard = stages.get("scorecard", {}) if isinstance(stages, dict) else {}
    lines = [
        "# INTEL Fixture Gate",
        "",
        f"**Status:** {status}",
        f"**Fixture:** `{result.get('fixture_dir')}`",
        f"**Threshold lock:** `{result.get('threshold_lock')}`",
        f"**Eval run:** `{scorecard.get('eval_run_id')}`",
        "",
        "| Stage | Status |",
        "|-------|--------|",
    ]
    for name in ("fixture_audit", "scorecard", "provenance"):
        stage = stages.get(name, {}) if isinstance(stages, dict) else {}
        stage_ok = bool(stage.get("valid")) and bool(stage.get("passed", True))
        lines.append(f"| `{name}` | {'PASS' if stage_ok else 'FAIL'} |")

    errors = list(result.get("errors") or ())
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend(f"- `{error}`" for error in errors)
    return "\n".join(lines) + "\n"


def _safe_path_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--threshold-lock", type=Path, default=DEFAULT_THRESHOLD_LOCK)
    parser.add_argument("--output", type=Path, help="Write the JSON gate report to this path")
    parser.add_argument("--summary-markdown", type=Path, help="Write a markdown gate summary")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable report")
    args = parser.parse_args(argv)

    result = run_intel_gate(fixture_dir=args.fixture_dir, threshold_lock=args.threshold_lock)
    write_errors: list[str] = []
    if args.summary_markdown:
        try:
            _atomic_write_text(args.summary_markdown, render_markdown_summary(result))
        except OSError as exc:
            write_errors.append(f"summary_markdown:{exc}")
    if not write_errors and args.output:
        try:
            _atomic_write_text(args.output, json.dumps(result, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            write_errors.append(f"output:{exc}")
    if write_errors:
        result = {
            **result,
            "valid": False,
            "errors": [*list(result.get("errors", ())), *write_errors],
        }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["valid"]:
        print(
            "INTEL gate passed "
            f"({result['fixture_dir']}, {result['stages']['scorecard']['eval_run_id']})"
        )
    else:
        for error in result["errors"]:
            print(f"[intel-gate] {error}", file=sys.stderr)
    return 0 if result["valid"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
