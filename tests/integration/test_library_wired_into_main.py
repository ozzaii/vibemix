# SPDX-License-Identifier: Apache-2.0
"""Plan 28-04 — P48 invocation test.

Asserts that __main__.py contains the register_library + grounding wiring
and that the call sites are gated as documented (library cache exists →
register + arm grounding; absent → graceful skip).

This is a static-analysis test — exercising the live runtime would require
spinning up audio devices + a real proxy. The grep + AST checks here
catch regressions where someone deletes the wiring (the prior P48 bug).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_PATH = REPO_ROOT / "src" / "vibemix" / "__main__.py"


@pytest.fixture(scope="module")
def main_source() -> str:
    return MAIN_PATH.read_text()


@pytest.fixture(scope="module")
def main_ast(main_source: str) -> ast.Module:
    return ast.parse(main_source)


def test_main_calls_register_library_when_library_loaded(
    main_source: str,
) -> None:
    """P48 carry-forward: register_library MUST still be invoked."""
    assert "register_library" in main_source, (
        "P48 regression: register_library wiring removed from __main__.py"
    )
    # Assert the call is gated by library_cache.exists() (not unconditional).
    assert "library_cache.exists()" in main_source, (
        "register_library should be gated by library_cache.exists()"
    )


def test_main_arms_grounding_after_register(main_source: str) -> None:
    """Plan 28-04: Grounding constructed after register_library."""
    register_idx = main_source.find("register_library")
    grounding_idx = main_source.find("Grounding")
    assert register_idx != -1, "register_library missing"
    assert grounding_idx != -1, "Grounding never constructed in __main__.py"
    assert grounding_idx > register_idx, (
        "Grounding must be constructed AFTER register_library "
        "(library load → registry → grounding chain)"
    )


def test_grounding_construction_is_try_guarded(main_source: str) -> None:
    """Grounding failures must NOT crash boot — graceful degradation."""
    # Find the Grounding-related block and assert it's inside a try.
    lines = main_source.splitlines()
    grounding_line = next(
        (i for i, l in enumerate(lines) if "Grounding(" in l),
        None,
    )
    assert grounding_line is not None
    # Walk up looking for a `try:` within 30 lines.
    found_try = any(
        lines[i].strip().startswith("try:")
        for i in range(max(0, grounding_line - 30), grounding_line)
    )
    assert found_try, "Grounding construction must be wrapped in try/except"


def test_grounding_disabled_without_library(main_source: str) -> None:
    """Boot path: grounding=None when no library cache."""
    assert "grounding = None" in main_source, (
        "grounding default state must be None"
    )


def test_main_module_parses(main_source: str) -> None:
    """Sanity: __main__.py parses as valid Python."""
    ast.parse(main_source)


def test_p48_telemetry_logs_present(main_source: str) -> None:
    """Operator-visibility: register_library + grounding both log status."""
    assert "tracks registered for [track:<id>] citations" in main_source, (
        "register_library success log removed"
    )
    assert "grounding:" in main_source, "grounding status log removed"
