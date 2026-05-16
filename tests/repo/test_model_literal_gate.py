# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 3 — CI grep gate mirror + clean-tree assertion.

Two parallel implementations of the same gate:

1. ``scripts/release/check_no_hardcoded_model.sh`` — GitHub Actions truth
   (Bash; runs in the workflow).
2. ``_python_gate_check()`` below — cross-platform pytest mirror for
   local dev-loop fast feedback (Windows runners lack a guaranteed bash).

Both implementations enforce the same rule: any Gemini model literal in
``src/vibemix/`` outside ``src/vibemix/llm/_router_config.py`` is a
violation.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# Repo root (test file is at tests/repo/test_model_literal_gate.py).
REPO_ROOT = Path(__file__).resolve().parents[2]

# Bash gate script — installed by Task 3 of Plan 41-01.
GATE_SCRIPT = REPO_ROOT / "scripts" / "release" / "check_no_hardcoded_model.sh"

# Pattern: every Gemini model literal we ban anywhere in src/vibemix/
# except the allowlisted _router_config.py path. Kept in lockstep with
# the bash script's regex.
_MODEL_LITERAL_RE = re.compile(
    r"gemini-3-flash|gemini-3-pro|gemini-embedding-|gemini-3\.1-flash|"
    r"gemini-2\.5-flash|gemini-3\.1-flash-live"
)

# Allowlist — these paths are permitted to carry literals. NOTE
# model_router.py is NOT on the list — only the config table file.
_ALLOWLIST = {Path("src/vibemix/llm/_router_config.py")}

# Scope — only this subtree is enforced. Tests / scripts / docs are out
# of scope (per Plan 41-01 Open Question 4).
_SCOPE_DIR = Path("src/vibemix")


def _python_gate_check(repo_root: Path) -> list[tuple[Path, int, str]]:
    """Walk ``src/vibemix/`` and return ``(path, lineno, line)`` for every
    violation. Empty list ⇒ gate passes.

    This mirrors the bash script behavior exactly so the two stay in sync.
    """
    violations: list[tuple[Path, int, str]] = []
    scope = repo_root / _SCOPE_DIR
    if not scope.exists():  # pragma: no cover — repo always has src/vibemix
        return violations
    for py_path in sorted(scope.rglob("*.py")):
        rel = py_path.relative_to(repo_root)
        if rel in _ALLOWLIST:
            continue
        text = py_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _MODEL_LITERAL_RE.search(line):
                violations.append((rel, lineno, line))
    return violations


# ---------------------------------------------------------------------------
# Bash + Python parity assertions
# ---------------------------------------------------------------------------


def test_gate_passes_clean_tree() -> None:
    """Post-Task-2 migrated tree has 0 violations (sanity)."""
    assert _python_gate_check(REPO_ROOT) == []


def test_gate_allowlists_router_config() -> None:
    """_router_config.py literals do NOT trip the gate (it's the source
    of truth — the single allowlisted file)."""
    config = REPO_ROOT / "src" / "vibemix" / "llm" / "_router_config.py"
    text = config.read_text(encoding="utf-8")
    # Sanity: the file actually contains a literal we'd otherwise ban.
    assert _MODEL_LITERAL_RE.search(text) is not None
    # And yet the gate is clean.
    assert _python_gate_check(REPO_ROOT) == []


def test_gate_fails_on_synthetic_violation_in_src(tmp_path: Path) -> None:
    """Injecting a literal under src/vibemix/ trips the gate."""
    target = REPO_ROOT / "src" / "vibemix" / "agent" / "_canary_violation.py"
    try:
        target.write_text(
            '# SPDX-License-Identifier: Apache-2.0\n'
            'CANARY = "gemini-3-flash-preview"\n',
            encoding="utf-8",
        )
        violations = _python_gate_check(REPO_ROOT)
        assert len(violations) == 1
        rel, lineno, line = violations[0]
        assert rel == Path("src/vibemix/agent/_canary_violation.py")
        assert "gemini-3-flash-preview" in line
    finally:
        if target.exists():
            target.unlink()


def test_gate_fails_on_legacy_embedding_001(tmp_path: Path) -> None:
    """Defensive — the legacy ``gemini-embedding-001`` id never appears in
    vibemix, but the gate catches accidental introduction."""
    target = REPO_ROOT / "src" / "vibemix" / "library" / "_canary_legacy.py"
    try:
        target.write_text(
            '# SPDX-License-Identifier: Apache-2.0\n'
            'LEGACY = "gemini-embedding-001"\n',
            encoding="utf-8",
        )
        violations = _python_gate_check(REPO_ROOT)
        assert any("gemini-embedding-001" in line for _, _, line in violations)
    finally:
        if target.exists():
            target.unlink()


def test_gate_does_not_scan_tests_dir() -> None:
    """tests/ are out of scope — tests can keep literals as contract
    canaries (e.g. test_config's pre-migration assertions)."""
    # Sanity: tests/ contains literals (this very file references them).
    self_path = Path(__file__)
    assert _MODEL_LITERAL_RE.search(self_path.read_text(encoding="utf-8")) is not None
    # Yet the gate stays clean.
    assert _python_gate_check(REPO_ROOT) == []


def test_gate_does_not_scan_scripts_dir() -> None:
    """scripts/eval/judge.py keeps its own model dispatch (Open Q 4) —
    the gate must not flag it."""
    # _python_gate_check only walks src/vibemix/ — verify by passing a
    # tmp root that contains a scripts/ literal.
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "src" / "vibemix").mkdir(parents=True)
        (root / "src" / "vibemix" / "ok.py").write_text("OK = 1\n")
        (root / "scripts" / "eval").mkdir(parents=True)
        (root / "scripts" / "eval" / "judge.py").write_text(
            'M = "gemini-3-flash-preview"\n'
        )
        assert _python_gate_check(root) == []


# ---------------------------------------------------------------------------
# Bash-script subprocess parity (skipped on hosts without bash)
# ---------------------------------------------------------------------------


_BASH = shutil.which("bash")


@pytest.mark.skipif(_BASH is None, reason="bash not available on this host")
def test_bash_gate_exists_and_executable() -> None:
    """The bash gate script exists and is marked executable."""
    assert GATE_SCRIPT.exists(), f"missing gate script: {GATE_SCRIPT}"
    assert GATE_SCRIPT.stat().st_mode & 0o111, "gate script not executable"


@pytest.mark.skipif(_BASH is None, reason="bash not available on this host")
def test_bash_gate_exits_zero_on_clean_tree() -> None:
    """Bash gate behavior matches the Python mirror on the current tree."""
    proc = subprocess.run(
        [str(GATE_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"bash gate failed on clean tree (rc={proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )


@pytest.mark.skipif(_BASH is None, reason="bash not available on this host")
def test_bash_gate_fails_on_synthetic_violation() -> None:
    """Bash gate exits != 0 and names the offending file."""
    target = REPO_ROOT / "src" / "vibemix" / "agent" / "_canary_bash_violation.py"
    try:
        target.write_text(
            '# SPDX-License-Identifier: Apache-2.0\n'
            'CANARY = "gemini-3-pro-preview"\n',
            encoding="utf-8",
        )
        proc = subprocess.run(
            [str(GATE_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, "gate must fail on injected literal"
        # Output must name the offending file so the contributor can find it.
        combined = proc.stdout + proc.stderr
        assert "_canary_bash_violation.py" in combined, (
            f"gate output didn't name the offending file:\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    finally:
        if target.exists():
            target.unlink()


# ---------------------------------------------------------------------------
# GitHub Actions workflow file is well-formed
# ---------------------------------------------------------------------------


def test_github_workflow_exists() -> None:
    """The workflow file is present and parses as YAML."""
    wf = REPO_ROOT / ".github" / "workflows" / "model-literal-check.yml"
    assert wf.exists(), f"missing workflow: {wf}"
    # Best-effort YAML parse — skip if PyYAML isn't a project dep.
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("PyYAML not installed; structural assertion skipped")
    parsed = yaml.safe_load(wf.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    # The `on` key may parse to the Python `True` bool because YAML 1.1 treats
    # `on`, `yes`, `off`, `no` as booleans. Accept either form.
    on_key = parsed.get("on", parsed.get(True))
    assert on_key is not None, "workflow lacks `on` trigger"
    assert "jobs" in parsed and isinstance(parsed["jobs"], dict)
