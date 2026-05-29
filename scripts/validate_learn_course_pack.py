#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate a draft Learn course-pack manifest without mutating the app."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from vibemix.learn.course_pack import (
    validate_course_pack_manifest,
    write_course_pack_template,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_learn_course_pack",
        description=(
            "Validate a JSON Learn course-pack draft against curriculum, "
            "transcript, flow, capability, and progress-field contracts."
        ),
    )
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        help="Path to course-pack.json.",
    )
    parser.add_argument(
        "--init-template",
        type=Path,
        default=None,
        help="Write a canonical starter course pack into this directory, then validate it.",
    )
    parser.add_argument(
        "--course-number",
        type=int,
        default=4,
        help="Course number used by --init-template (default: 4).",
    )
    parser.add_argument(
        "--slug",
        default="new_course",
        help="Lowercase course slug used by --init-template (default: new_course).",
    )
    parser.add_argument(
        "--lesson-count",
        type=int,
        default=1,
        help="Number of starter lessons written by --init-template (default: 1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow --init-template to overwrite existing generated files.",
    )
    parser.add_argument(
        "--transcript-root",
        type=Path,
        default=None,
        help=(
            "Directory used to resolve transcript_path values. Defaults to the "
            "manifest directory."
        ),
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.init_template is not None:
        try:
            report = write_course_pack_template(
                args.init_template,
                course_number=args.course_number,
                slug=args.slug,
                lesson_count=args.lesson_count,
                overwrite=args.force,
            )
        except (FileExistsError, ValueError) as exc:
            report = {
                "ok": False,
                "error": str(exc),
            }
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0 if report.get("ok") is True else 4

    if args.manifest is None:
        parser.error("manifest is required unless --init-template is used")
    validation = validate_course_pack_manifest(
        args.manifest,
        transcript_root=args.transcript_root,
    )
    report = validation.to_dict()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if validation.ok else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
