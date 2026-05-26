# SPDX-License-Identifier: Apache-2.0
"""BENCH-01 — bench-scoped model-literal guard (REAL-GREEN now).

Reuses the ``rglob``-walk literal-scan idiom from
``tests/repo/test_model_literal_gate.py`` (the CI grep mirror), scoped to
``src/vibemix/bench/``. Asserts ZERO Gemini model literals under ``bench/``
(Pitfall 4: every model reference must go through ``model_router.resolve`` —
a literal trips ``scripts/release/check_no_hardcoded_model.sh``).

Today ``src/vibemix/bench/`` does not exist yet, so the scan passes vacuously;
it stays green as Plans 02/03/04 land the harness (which resolves every model
via the router). This guard is REAL-GREEN — never xfail.

IMPORTANT: ``bench/`` is NOT added to the gate's ``_ALLOWLIST`` (only
``src/vibemix/llm/_router_config.py`` is allowlisted). Confirmed below.
"""

from __future__ import annotations

from pathlib import Path

from tests.repo.test_model_literal_gate import (
    _ALLOWLIST,
    _MODEL_LITERAL_RE,
    REPO_ROOT,
)

# The bench subpackage the harness lands in (Plans 02/03/04). Absent today.
_BENCH_DIR = REPO_ROOT / "src" / "vibemix" / "bench"


def _bench_literal_violations() -> list[tuple[Path, int, str]]:
    """Walk ``src/vibemix/bench/`` (if present) and return every Gemini-literal
    violation. Empty list ⇒ the bench is clean (vacuously true while absent)."""
    violations: list[tuple[Path, int, str]] = []
    if not _BENCH_DIR.exists():
        return violations
    for py_path in sorted(_BENCH_DIR.rglob("*.py")):
        rel = py_path.relative_to(REPO_ROOT)
        text = py_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _MODEL_LITERAL_RE.search(line):
                violations.append((rel, lineno, line))
    return violations


def test_no_model_literal_under_bench() -> None:
    """No Gemini model literal anywhere under src/vibemix/bench/ (the model axis
    sweeps router aliases via model_router.resolve, never a literal)."""
    assert _bench_literal_violations() == []


def test_bench_is_not_allowlisted() -> None:
    """bench/ must NOT be in the gate's allowlist — only the router config file
    is permitted to carry literals. A future harness must resolve via the
    router, so the gate stays meaningful over bench/."""
    bench_rel = Path("src/vibemix/bench")
    # No allowlist entry is inside the bench subtree.
    for allowed in _ALLOWLIST:
        assert bench_rel not in allowed.parents
        assert allowed != bench_rel
    # And the only allowlisted file is the router config (the source of truth).
    assert _ALLOWLIST == {Path("src/vibemix/llm/_router_config.py")}
