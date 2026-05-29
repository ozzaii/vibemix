#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Audit the Learn curriculum/course-pack integration contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vibemix.learn.curriculum_audit import audit_curriculum

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRONTEND = ROOT / "tauri" / "ui" / "src" / "learn" / "lesson" / "curriculum-meta.ts"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend-path",
        type=Path,
        default=DEFAULT_FRONTEND,
        help="Generated frontend curriculum projection to verify.",
    )
    parser.add_argument(
        "--no-frontend-check",
        action="store_true",
        help="Skip the checked-in frontend projection freshness check.",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write the JSON report.")
    return parser


def _write_report(report: dict[str, object], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    frontend_path = None if args.no_frontend_check else args.frontend_path
    report = audit_curriculum(frontend_path=frontend_path)
    if args.out is not None:
        _write_report(report, args.out)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
