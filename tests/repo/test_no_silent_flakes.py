# SPDX-License-Identifier: Apache-2.0
"""Phase 67 Plan 67P03 — Static gate against silent flaky decorators.

TEST-03 invariant: every ``@pytest.mark.flaky`` decorator in the test tree
must carry an adjacent GitHub-issue link in a ``# issue: https://github.com/.../issues/N``
comment within 3 lines above (or on) the decorator line.

The repo today has ZERO ``@pytest.mark.flaky`` decorators (Wave 0 of Phase 67
registered the marker under ``--strict-markers``; the Wave 4 flake-hunt is
the surface where flake decorators may be added if a non-deterministic test
surfaces). This gate is therefore vacuously-green at landing — but the
moment a contributor adds a flaky decorator without an issue link, CI turns
red.

The scan uses ``ast.parse`` + walk (not regex on text) so multi-line
flaky decorators (e.g. ``@pytest.mark.flaky(reruns=3, reruns_delay=1)``
split across lines) are handled correctly.

Follows the static-gate idiom of ``tests/repo/test_repo_scrub.py`` and the
sibling shape of ``tests/repo/test_no_silent_skips.py``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# The issue-link comment shape: ``# issue: https://github.com/<owner>/<repo>/issues/<N>``
# Allow any whitespace around the colon and the URL; require the github.com
# host and the ``/issues/<digits>`` tail so a generic GitHub repo URL won't
# satisfy the gate (it must point at a real issue).
_ISSUE_LINK_PATTERN: re.Pattern[str] = re.compile(
    r"#\s*issue\s*:\s*https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+",
    re.IGNORECASE,
)

# This file's own filename — exclude from the scan so the regex source
# string ``@pytest\.mark\.flaky`` (if it appeared) wouldn't self-trip the
# gate. We don't actually carry that string here, but the defensive
# exclusion mirrors the sibling convention.
_SELF_FILENAME = "test_no_silent_flakes.py"


def _is_flaky_decorator(node: ast.expr) -> bool:
    """True if the AST node is a ``@pytest.mark.flaky`` decorator (call or bare)."""
    target = node.func if isinstance(node, ast.Call) else node
    if not isinstance(target, ast.Attribute) or target.attr != "flaky":
        return False
    inner = target.value
    if not isinstance(inner, ast.Attribute) or inner.attr != "mark":
        return False
    outer = inner.value
    if not isinstance(outer, ast.Name) or outer.id != "pytest":
        return False
    return True


def _has_issue_link_nearby(source_lines: list[str], lineno: int) -> bool:
    """True if a ``# issue: https://github.com/.../issues/N`` link lives within
    3 lines above (or on) the decorator at ``lineno`` (1-indexed).

    Window: lines ``[lineno-3, lineno-2, lineno-1, lineno]`` — i.e. up to 3
    lines above OR on the decorator line itself.
    """
    start = max(0, lineno - 4)  # lineno-3 → 0-indexed lineno-4
    end = lineno  # exclusive — covers up to 0-indexed lineno-1 (line ``lineno``)
    for raw in source_lines[start:end]:
        if _ISSUE_LINK_PATTERN.search(raw):
            return True
    return False


def _iter_test_files() -> list[Path]:
    """Every ``*.py`` file under ``tests/``, excluding this gate file."""
    return [
        p
        for p in TESTS_DIR.rglob("*.py")
        if p.name != _SELF_FILENAME
    ]


def test_no_silent_flakes() -> None:
    """Every ``@pytest.mark.flaky`` decorator carries a GitHub-issue link.

    Required shape (anywhere in the 3-line window above or on the decorator
    line): ``# issue: https://github.com/<owner>/<repo>/issues/<N>``.

    Vacuously-green at landing (Wave 2 of Phase 67) — zero flaky decorators
    exist in the repo. The gate is the anti-drift surface for Wave 4 and
    beyond: if a flake-hunt iteration adds an undocumented flaky decorator,
    the failure message lists every offender with file + line.
    """
    offenders: list[str] = []
    for py in _iter_test_files():
        text = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(py))
        except SyntaxError as exc:
            offenders.append(f"{py.relative_to(REPO_ROOT)}: parse error — {exc}")
            continue
        source_lines = text.splitlines()
        for node in ast.walk(tree):
            decorators = getattr(node, "decorator_list", None)
            if not decorators:
                continue
            for deco in decorators:
                if not _is_flaky_decorator(deco):
                    continue
                if _has_issue_link_nearby(source_lines, deco.lineno):
                    continue
                rel = py.relative_to(REPO_ROOT)
                offenders.append(
                    f"{rel}:{deco.lineno}: @pytest.mark.flaky without "
                    f"`# issue: https://github.com/.../issues/N` comment "
                    f"within 3 lines above"
                )
    assert not offenders, (
        "Silent @pytest.mark.flaky decorators detected — every flaky marker "
        "must carry an adjacent `# issue: https://github.com/.../issues/N` "
        "comment within 3 lines above (TEST-03 invariant). Offenders:\n  "
        + "\n  ".join(offenders)
    )
