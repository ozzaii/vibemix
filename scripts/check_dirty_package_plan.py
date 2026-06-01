#!/usr/bin/env python3
"""Verify the dirty-tree package checklist covers every dirty path.

The shipping inventory is intentionally human-readable Markdown, but it should
still be hard to forget a file while staging. This checker asks git for staged
changes, unstaged tracked modifications, and untracked non-ignored paths, then
verifies each path is named in the current package checklist.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / ".planning/handoffs/2026-05-31-package-checklist.md"
IGNORED_GENERATED = (
    "docs/launch/.partner-capabilities.html",
    "docs/launch/.partner-capabilities-short.html",
    "docs/launch/.vibemix-konusan.html",
)

BACKTICK_TOKEN_RE = re.compile(r"`([^`\n]+)`")
SECTION_HEADING_RE = re.compile(r"^## (?P<title>.+)$")


def _git_lines(*args: str) -> list[str]:
    proc = subprocess.run(
        ("git", *args),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line for line in proc.stdout.splitlines() if line]


def _dirty_paths() -> list[str]:
    return sorted(
        {
            *_git_lines("diff", "--cached", "--name-only"),
            *_git_lines("diff", "--name-only"),
            *_git_lines("ls-files", "--others", "--exclude-standard"),
        }
    )


def _check_generated_ignores() -> list[str]:
    missing: list[str] = []
    for rel in IGNORED_GENERATED:
        proc = subprocess.run(
            ("git", "check-ignore", "-q", rel),
            cwd=ROOT,
            text=True,
        )
        if proc.returncode != 0:
            missing.append(rel)
    return missing


def _checklist_tokens(text: str) -> set[str]:
    return {match.group(1) for match in BACKTICK_TOKEN_RE.finditer(text)}


def _matches_token(token: str, dirty_paths: set[str]) -> list[str]:
    if token in dirty_paths:
        return [token]
    if token.endswith("/"):
        return sorted(path for path in dirty_paths if path.startswith(token))
    return []


def _path_is_covered(path: str, tokens: set[str]) -> bool:
    if path in tokens:
        return True
    return any(token.endswith("/") and path.startswith(token) for token in tokens)


def _paths_by_section(
    text: str,
    dirty_paths: set[str],
) -> tuple[dict[str, list[str]], dict[str, list[str]], list[str]]:
    section_paths: dict[str, list[str]] = {}
    path_sections: dict[str, list[str]] = {}
    mentioned_paths: set[str] = set()
    current_section: str | None = None
    current_mode: str | None = None

    for line in text.splitlines():
        heading = SECTION_HEADING_RE.match(line)
        if heading:
            current_section = heading.group("title")
            current_mode = None
            section_paths.setdefault(current_section, [])
            continue

        if current_section is None:
            continue

        stripped = line.strip()
        if stripped in {"Include:", "Hold:"}:
            current_mode = "assign"
            continue
        if stripped.endswith(":") and not stripped.startswith("-"):
            current_mode = None
            continue

        for token in BACKTICK_TOKEN_RE.findall(line):
            matched_paths = _matches_token(token, dirty_paths)
            if not matched_paths:
                continue
            for path in matched_paths:
                mentioned_paths.add(path)
                if current_mode != "assign" or path in section_paths[current_section]:
                    continue
                section_paths[current_section].append(path)
                path_sections.setdefault(path, []).append(current_section)

    active_sections = {
        section: paths for section, paths in section_paths.items() if paths
    }
    shared_paths = {
        path: sections for path, sections in path_sections.items() if len(sections) > 1
    }
    assigned_paths = set(path_sections)
    represented_outside_assignment = sorted(mentioned_paths - assigned_paths)
    return active_sections, shared_paths, represented_outside_assignment


def _print_summary(checklist: str, dirty: list[str]) -> None:
    section_paths, shared_paths, outside_assignment = _paths_by_section(checklist, set(dirty))
    print("\nPackage summary (Include/Hold assignments):")
    for section, paths in section_paths.items():
        print(f"  - {section}: {len(paths)} dirty paths")
    if shared_paths:
        print("\nShared dirty-path assignments:")
        for path, sections in sorted(shared_paths.items()):
            print(f"  - {path}: {', '.join(sections)}")
    if outside_assignment:
        print("\nDirty paths represented outside Include/Hold:")
        for path in outside_assignment:
            print(f"  - {path}")


def _strict_assignment_gaps(checklist: str, dirty: list[str]) -> list[str]:
    section_paths, _, _ = _paths_by_section(checklist, set(dirty))
    assigned = {path for paths in section_paths.values() for path in paths}
    return [path for path in dirty if path not in assigned]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print dirty-path counts by package section after validation.",
    )
    parser.add_argument(
        "--strict-assignments",
        action="store_true",
        help="Fail unless every dirty path appears under an Include or Hold section.",
    )
    args = parser.parse_args(argv)

    checklist = CHECKLIST.read_text(encoding="utf-8")
    checklist_tokens = _checklist_tokens(checklist)
    dirty = _dirty_paths()
    missing = [path for path in dirty if not _path_is_covered(path, checklist_tokens)]
    ignored_missing = _check_generated_ignores()

    if missing or ignored_missing:
        if missing:
            print("Dirty paths missing from package checklist:", file=sys.stderr)
            for path in missing:
                print(f"  - {path}", file=sys.stderr)
        if ignored_missing:
            print("Generated launch previews not ignored:", file=sys.stderr)
            for path in ignored_missing:
                print(f"  - {path}", file=sys.stderr)
        return 1

    assignment_gaps = _strict_assignment_gaps(checklist, dirty) if args.strict_assignments else []
    if assignment_gaps:
        print("Dirty paths not assigned to an Include/Hold lane:", file=sys.stderr)
        for path in assignment_gaps:
            print(f"  - {path}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(dirty)} dirty paths covered by "
        f"{CHECKLIST.relative_to(ROOT)}; "
        f"{len(IGNORED_GENERATED)} generated launch previews ignored."
    )
    if args.strict_assignments:
        print("OK: every dirty path is assigned to an Include/Hold lane.")
    if args.summary:
        _print_summary(checklist, dirty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
