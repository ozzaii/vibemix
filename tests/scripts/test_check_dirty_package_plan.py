# SPDX-License-Identifier: Apache-2.0
"""Tests for the dirty-tree package checklist guard."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_dirty_package_plan.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("check_dirty_package_plan", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dirty_paths_include_staged_unstaged_and_untracked(monkeypatch) -> None:
    checker = _load_script_module()
    calls: list[tuple[str, ...]] = []

    def fake_git_lines(*args: str) -> list[str]:
        calls.append(args)
        if args == ("diff", "--cached", "--name-only"):
            return ["src/vibemix/state/drop_predict.py", "shared.py"]
        if args == ("diff", "--name-only"):
            return ["src/vibemix/state/refresh.py", "shared.py"]
        if args == ("ls-files", "--others", "--exclude-standard"):
            return ["tests/state/test_drop_predict.py"]
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(checker, "_git_lines", fake_git_lines)

    assert checker._dirty_paths() == [
        "shared.py",
        "src/vibemix/state/drop_predict.py",
        "src/vibemix/state/refresh.py",
        "tests/state/test_drop_predict.py",
    ]
    assert calls == [
        ("diff", "--cached", "--name-only"),
        ("diff", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ]


def test_paths_by_section_reports_dirty_paths_once_per_section() -> None:
    checker = _load_script_module()
    checklist = """
`docs/elsewhere.md`
## Package 0 - Docs

Include:

- `scripts/check_dirty_package_plan.py`
- `tests/scripts/test_check_dirty_package_plan.py`
- `tests/scripts/test_check_dirty_package_plan.py`

## Package 1 - Tooling

Include:

- `src/vibemix/runtime/dev_mcp_server.py`
- `not-dirty.md`
"""

    sections, shared, outside_assignment = checker._paths_by_section(
        checklist,
        {
            "scripts/check_dirty_package_plan.py",
            "src/vibemix/runtime/dev_mcp_server.py",
            "tests/scripts/test_check_dirty_package_plan.py",
        },
    )

    assert sections == {
        "Package 0 - Docs": [
            "scripts/check_dirty_package_plan.py",
            "tests/scripts/test_check_dirty_package_plan.py",
        ],
        "Package 1 - Tooling": ["src/vibemix/runtime/dev_mcp_server.py"],
    }
    assert shared == {}
    assert outside_assignment == []


def test_paths_by_section_reports_shared_dirty_paths() -> None:
    checker = _load_script_module()
    checklist = """
## Package 2 - Session IPC

Include:

- `src/vibemix/ui_bus/messages.py`

## Package 3 - IPC Contract Cleanup

Include:

- `src/vibemix/ui_bus/messages.py`
"""

    sections, shared, outside_assignment = checker._paths_by_section(
        checklist,
        {"src/vibemix/ui_bus/messages.py"},
    )

    assert sections == {
        "Package 2 - Session IPC": ["src/vibemix/ui_bus/messages.py"],
        "Package 3 - IPC Contract Cleanup": ["src/vibemix/ui_bus/messages.py"],
    }
    assert shared == {
        "src/vibemix/ui_bus/messages.py": [
            "Package 2 - Session IPC",
            "Package 3 - IPC Contract Cleanup",
        ]
    }
    assert outside_assignment == []


def test_paths_by_section_keeps_keep_out_mentions_out_of_assignments() -> None:
    checker = _load_script_module()
    checklist = """
## Package 10 - Live Stack Cost And Pricing Model

Include:

- `src/vibemix/__main__.py`

Keep out:

- `tests/test_main_smoke.py`
"""

    sections, shared, outside_assignment = checker._paths_by_section(
        checklist,
        {"src/vibemix/__main__.py", "tests/test_main_smoke.py"},
    )

    assert sections == {
        "Package 10 - Live Stack Cost And Pricing Model": ["src/vibemix/__main__.py"],
    }
    assert shared == {}
    assert outside_assignment == ["tests/test_main_smoke.py"]


def test_strict_assignment_gaps_require_include_or_hold() -> None:
    checker = _load_script_module()
    checklist = """
## Package 10 - Live Stack Cost And Pricing Model

Include:

- `src/vibemix/__main__.py`

Keep out:

- `tests/test_main_smoke.py`

## Hold Lane - Launch Screenshot Alternates

Hold:

- `docs/launch/screenshots/session-mock.png`
"""

    gaps = checker._strict_assignment_gaps(
        checklist,
        [
            "docs/launch/screenshots/session-mock.png",
            "src/vibemix/__main__.py",
            "tests/test_main_smoke.py",
        ],
    )

    assert gaps == ["tests/test_main_smoke.py"]
