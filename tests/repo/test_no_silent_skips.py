# SPDX-License-Identifier: Apache-2.0
"""Phase 67 Plan 67P03 — Static gate against silent skip/xfail decorators.

TEST-01 invariant: every ``@pytest.mark.skip`` / ``@pytest.mark.skipif`` /
``@pytest.mark.xfail`` decorator in the test tree must carry a reason — either
as a ``reason=`` keyword argument inside the decorator call, OR as a
``# reason:`` comment within 2 lines above the decorator (or on the same line).

The Tier-B fleet introduced in Wave 1 (Phase 67 Plan 67P02) carries BOTH a
``reason=`` kwarg (machine-readable, surfaces in ``pytest --tb=short`` output)
AND a ``# reason:`` comment 2-3 lines above (human-readable, grep-friendly).
This gate accepts either shape — the dual-channel pattern is conservative,
but the static surface only enforces "at least one".

The scan uses ``ast.parse`` + walk (not regex on text) so multi-line
decorators (e.g. ``test_tts_3_1.py``'s 7-line ``@pytest.mark.skipif(...)``
with a wrapped ``reason=`` string) are handled correctly — the AST decorator
node holds every keyword argument regardless of physical line layout.

Follows the static-gate idiom of ``tests/repo/test_repo_scrub.py``:
module constants at top, private helpers prefixed ``_``, a single
``def test_*`` function with an offender-list assertion message.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# The three decorator stems that must carry a reason. ``skip`` and ``xfail``
# accept a reason= kwarg (or carry a comment); ``skipif`` already requires
# a positional condition + reason= per pytest's docs, but we enforce the
# same rule statically so the audit surface is uniform.
_REASON_REQUIRED_STEMS: frozenset[str] = frozenset({"skip", "skipif", "xfail"})

# This file's own filename — exclude from the scan to keep the gate
# self-referential-safe (the stem strings ``"skip"`` / ``"xfail"`` appear
# as string literals here, not as decorators, so AST would not flag them,
# but defensive exclusion mirrors the convention used by
# ``test_no_silent_flakes.py``).
_SELF_FILENAME = "test_no_silent_skips.py"


def _decorator_stem(node: ast.expr) -> str | None:
    """Return the trailing attribute name of a ``pytest.mark.<stem>`` decorator.

    Accepts both call form (``@pytest.mark.skipif(...)``) and bare form
    (``@pytest.mark.skip``). Returns None for anything that isn't a
    ``pytest.mark.<name>`` reference.
    """
    # Unwrap Call(func=Attribute(...)) — the (...) decorator form.
    target = node.func if isinstance(node, ast.Call) else node
    if not isinstance(target, ast.Attribute):
        return None
    # target.value is the ``pytest.mark`` Attribute; its .value is ``pytest`` Name.
    inner = target.value
    if not isinstance(inner, ast.Attribute) or inner.attr != "mark":
        return None
    outer = inner.value
    if not isinstance(outer, ast.Name) or outer.id != "pytest":
        return None
    return target.attr


def _has_reason_kwarg(node: ast.expr) -> bool:
    """True if the decorator call carries a ``reason=`` keyword argument."""
    if not isinstance(node, ast.Call):
        return False
    for kw in node.keywords:
        if kw.arg == "reason":
            return True
    return False


def _has_reason_comment_nearby(source_lines: list[str], lineno: int) -> bool:
    """True if a ``# reason:`` comment lives within 2 lines above or on lineno.

    ``lineno`` is 1-indexed (AST convention). The window covers lines
    ``[lineno-2, lineno-1, lineno]`` (i.e. up to 2 lines above OR on the
    decorator line itself), matching the CONTEXT.md spec.
    """
    # Convert to 0-indexed slice bounds, clamping at 0.
    start = max(0, lineno - 3)  # lineno-2 → 0-indexed lineno-3
    end = lineno  # exclusive — covers 0-indexed up to lineno-1 (i.e. line lineno)
    for raw in source_lines[start:end]:
        # Look for ``# reason:`` (case-insensitive, allow flexible whitespace).
        stripped = raw.strip()
        if "# reason:" in stripped or "#reason:" in stripped:
            return True
    return False


def _iter_test_files() -> list[Path]:
    """Every ``*.py`` file under ``tests/``, excluding this gate file."""
    return [
        p
        for p in TESTS_DIR.rglob("*.py")
        if p.name != _SELF_FILENAME
    ]


def test_no_silent_skips() -> None:
    """Every skip/skipif/xfail decorator carries a reason.

    Accepts either a ``reason=`` keyword argument inside the decorator call
    (e.g. ``@pytest.mark.skipif(cond, reason="...")``) OR a ``# reason:``
    comment within 2 lines above (or on) the decorator line.
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
        # AST walks all defs (function, async function, class) and inspects
        # their decorator_list. Module-level ``pytestmark = ...`` assignments
        # are NOT decorators (they're Assign nodes) and are deliberately not
        # scanned — pytest's own marker validation covers them.
        for node in ast.walk(tree):
            decorators = getattr(node, "decorator_list", None)
            if not decorators:
                continue
            for deco in decorators:
                stem = _decorator_stem(deco)
                if stem not in _REASON_REQUIRED_STEMS:
                    continue
                if _has_reason_kwarg(deco):
                    continue
                if _has_reason_comment_nearby(source_lines, deco.lineno):
                    continue
                rel = py.relative_to(REPO_ROOT)
                offenders.append(
                    f"{rel}:{deco.lineno}: @pytest.mark.{stem} "
                    f"without `reason=` kwarg or `# reason:` comment "
                    f"within 2 lines above"
                )
    assert not offenders, (
        "Silent skip/skipif/xfail decorators detected — every such decorator "
        "must carry EITHER a `reason=` kwarg inside the call OR a `# reason:` "
        "comment within 2 lines above (TEST-01 invariant). Offenders:\n  "
        + "\n  ".join(offenders)
    )
