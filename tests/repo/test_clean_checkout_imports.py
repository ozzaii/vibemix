# SPDX-License-Identifier: Apache-2.0
"""Clean-checkout integrity gate (2026-05-29).

The release-blocker bug class: a COMMITTED ``src/vibemix`` module imports another
``vibemix`` module at the TOP LEVEL, but that imported module is UNTRACKED. A
fresh ``git clone`` (and the PyInstaller sidecar, which is built from committed
files) then ``ModuleNotFoundError``s at import time — the brand-new user's app
does not start at all.

This actually shipped: ``__main__.py`` and ``runtime/suggestion.py`` imported
``vibemix.library.prepared_pool`` while the file was untracked, so
``import vibemix.__main__`` raised on a clean checkout (fixed by tracking the
module). Concurrent sessions had ~4 more of these queued in their working trees.

The gate is STATIC and tests the COMMITTED state only (it parses ``git show
HEAD:<file>`` content, not the working tree), so it is immune to in-progress
dirty edits and never imports anything (no flakiness, no editable-install leak).
It fires the moment a commit lands a top-level import of an on-disk-but-untracked
vibemix module.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _tracked_py() -> set[str]:
    """Paths (repo-relative, posix) of all tracked .py files under src/vibemix."""
    out = _git("ls-files", "src/vibemix/*.py")
    return {line.strip() for line in out.splitlines() if line.strip().endswith(".py")}


def _committed_source(path: str) -> str:
    """Committed (HEAD) content of a tracked file — NOT the working tree, so an
    in-progress uncommitted edit can never make this gate flap."""
    return _git("show", f"HEAD:{path}")


def _module_paths(dotted: str) -> list[str]:
    """``vibemix.a.b`` -> the two repo-relative paths it could resolve to."""
    rel = dotted.replace(".", "/")
    return [f"src/{rel}.py", f"src/{rel}/__init__.py"]


def _toplevel_imports(tree: ast.Module):
    """Yield module-level Import/ImportFrom nodes only.

    Only top-level imports execute at ``import`` time and so can break a clean
    checkout. Lazy in-function imports (the codebase's deliberate pattern for
    optional/heavy deps) are intentionally NOT flagged.
    """
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node


def test_no_committed_module_imports_an_untracked_vibemix_module() -> None:
    tracked = _tracked_py()
    on_disk = {
        str(p.relative_to(REPO_ROOT).as_posix())
        for p in (SRC / "vibemix").rglob("*.py")
    }
    violations: list[str] = []

    def _check(dotted: str, importer: str) -> None:
        # Only a real .py module matters. If the dotted name resolves to a file
        # that EXISTS on disk but is NOT tracked, committing this importer breaks
        # the clean checkout. If no file exists on disk, it's a symbol import (a
        # name from a package) or a genuinely-missing module — not our concern.
        candidates = _module_paths(dotted)
        if any(c in tracked for c in candidates):
            return  # resolves to a tracked module/package — fine
        untracked_hit = next((c for c in candidates if c in on_disk), None)
        if untracked_hit is not None:
            violations.append(f"{importer} imports {dotted!r} -> {untracked_hit} is UNTRACKED")

    for rel in sorted(tracked):
        try:
            tree = ast.parse(_committed_source(rel))
        except SyntaxError:
            continue  # not our gate to enforce
        for node in _toplevel_imports(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("vibemix."):
                        _check(alias.name, rel)
            else:  # ImportFrom
                if node.level:  # relative import — resolves within a tracked pkg
                    continue
                mod = node.module or ""
                if not mod.startswith("vibemix."):
                    continue
                _check(mod, rel)
                # `from vibemix.pkg import name` where name is itself a submodule.
                for alias in node.names:
                    _check(f"{mod}.{alias.name}", rel)

    assert not violations, (
        "Committed code imports untracked vibemix module(s) — a clean `git clone` "
        "/ packaged sidecar build will ModuleNotFoundError at import time (the "
        "prepared_pool.py release-blocker class). Track the module(s) or make the "
        "import lazy:\n  " + "\n  ".join(violations)
    )


def test_entry_point_static_import_closure_is_tracked() -> None:
    """Focused guard on the app entry point: every top-level vibemix module that
    ``__main__.py`` imports must be tracked (this is the exact import that broke
    on the prepared_pool regression)."""
    tracked = _tracked_py()
    rel = "src/vibemix/__main__.py"
    if rel not in tracked:
        pytest.skip("__main__.py not tracked (unexpected)")
    tree = ast.parse(_committed_source(rel))
    missing: list[str] = []
    for node in _toplevel_imports(tree):
        names = (
            [a.name for a in node.names]
            if isinstance(node, ast.Import)
            else ([node.module] if (node.module and not node.level) else [])
        )
        for dotted in names:
            if dotted and dotted.startswith("vibemix."):
                if not any(c in tracked for c in _module_paths(dotted)):
                    # tolerate symbol-from-package (no .py on disk for the dotted name)
                    if any(
                        (REPO_ROOT / c).exists() for c in _module_paths(dotted)
                    ):
                        missing.append(dotted)
    assert not missing, f"__main__.py top-level-imports untracked vibemix modules: {missing}"
