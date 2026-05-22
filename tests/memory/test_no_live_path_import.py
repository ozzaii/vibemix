# SPDX-License-Identifier: Apache-2.0
"""Phase 63 Plan 63-01 (Wave 0) — no-live-path import-boundary gate.

The milestone invariant: ``src/vibemix/memory/`` is a pure storage spine. It
must NEVER import the live reaction path — no coach loop, no MusicState, no
EventDetector, no agent, no prompts, no ws_bus. Memory grounds the coach
DOWNSTREAM (Phase 65 retrieval seam); it never reaches into the live ears.

Two enforcement tiers (precedent: tests/repo/test_repo_scrub.py):

    * test_memory_does_not_import_live_path_statically — a static AST walk over
      ``src/vibemix/memory/*.py`` asserting no import targets a forbidden live
      module and no imported NAME is a forbidden live class.
    * test_importing_memory_loads_no_coach_loop — the subprocess ``sys.modules``
      dormancy idiom: a fresh interpreter imports ``vibemix.memory.store`` and
      asserts no live-path module leaked transitively into ``sys.modules``.

RED-first: ``vibemix.memory`` does not exist yet. The static test passes
vacuously (no files to scan) and the subprocess test fails on the import error
— both flip to a real guarantee once Plans 02/03 land the package. The gate is
in place from the first commit so a Wave-1/2 author cannot introduce a live
import unnoticed.

T-63-01 (Tampering): future memory/ imports the live reaction path — mitigated
by this gate (the build fails if violated).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MEM = REPO / "src" / "vibemix" / "memory"

# The live reaction path + state surfaces memory must never import.
FORBIDDEN_IMPORTS: tuple[str, ...] = (
    "vibemix.state.coach",
    "vibemix.state.refresh",
    "vibemix.agent",
    "vibemix.prompts",
    "vibemix.runtime.ws_bus",
)
# Live-path class names that must never be imported into memory/.
FORBIDDEN_NAMES: tuple[str, ...] = ("MusicState", "EventDetector")


def _memory_py_files() -> list[Path]:
    if not MEM.exists():
        return []
    return sorted(MEM.rglob("*.py"))


def test_memory_does_not_import_live_path_statically() -> None:
    """Static AST gate — no memory/ module imports a live-path surface.

    Walks every ``import``/``from ... import`` in ``src/vibemix/memory/*.py``
    and asserts the module is not (a prefix of) a forbidden live module and no
    imported name is a forbidden live class. Vacuously true until the package
    exists; a real guarantee thereafter.
    """
    offenders: list[tuple[str, str]] = []
    for py in _memory_py_files():
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(
                    mod == f or mod.startswith(f + ".") for f in FORBIDDEN_IMPORTS
                ):
                    offenders.append((str(py.relative_to(REPO)), f"from {mod}"))
                for alias in node.names:
                    if alias.name in FORBIDDEN_NAMES:
                        offenders.append(
                            (str(py.relative_to(REPO)), f"name {alias.name}")
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    if any(
                        mod == f or mod.startswith(f + ".") for f in FORBIDDEN_IMPORTS
                    ):
                        offenders.append((str(py.relative_to(REPO)), f"import {mod}"))
    assert not offenders, (
        "vibemix.memory imports a live reaction-path surface (no-live-path "
        f"invariant VIOLATED): {offenders}. Memory is a storage spine; it must "
        "not import the coach loop, MusicState, EventDetector, agent, prompts, "
        "or ws_bus."
    )


def test_importing_memory_loads_no_coach_loop() -> None:
    """Runtime dormancy gate — importing memory leaks no live-path module.

    A fresh interpreter imports ``vibemix.memory.store`` and inspects
    ``sys.modules`` for any transitively-loaded live-path module. Clones the
    subprocess ``sys.modules`` dormancy idiom from
    ``tests/repo/test_repo_scrub.py::test_deck_path_sqlcipher_dormant``.

    RED-first: until the package exists the import raises and the subprocess
    exits non-zero — the gate becomes a true ``CLEAN`` assertion once
    ``vibemix.memory.store`` is importable.
    """
    script = (
        "import sys\n"
        "import vibemix.memory.store  # noqa: F401\n"
        "leak = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m.startswith('vibemix.state.coach')\n"
        "    or m.startswith('vibemix.state.refresh')\n"
        "    or m.startswith('vibemix.agent')\n"
        "    or m.startswith('vibemix.prompts')\n"
        "    or 'ws_bus' in m\n"
        ")\n"
        "print('LEAKED:' + ','.join(leak) if leak else 'CLEAN')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    # RED-first: the package does not exist yet, so the import fails (non-zero
    # exit) and stdout is NOT "CLEAN" — that pins the contract. Once the
    # package lands, the import succeeds and stdout must be exactly "CLEAN".
    assert result.stdout.strip() == "CLEAN", (
        "memory import leaked a live-path module (or vibemix.memory.store is "
        f"not importable yet — expected once Plans 02/03 land). stdout="
        f"{result.stdout!r}; stderr={result.stderr!r}"
    )


def test_importing_ingest_loads_no_coach_loop() -> None:
    """Runtime dormancy gate (Phase 64) — importing the ingest module leaks no
    live-path module.

    Closes the PATTERNS-flagged gap (64-PATTERNS.md §No-live-path import
    boundary): the store-side dormancy test above imports only
    ``vibemix.memory.store``; the ingest module needs the same runtime-dormancy
    proof. A fresh interpreter imports ``vibemix.memory.ingest`` and inspects
    ``sys.modules`` for any transitively-loaded live-path module — using the
    identical leak predicate as the store version.

    RED-first: until Plan 64-02 lands ``vibemix.memory.ingest`` the import
    raises and the subprocess exits non-zero — the gate becomes a true
    ``CLEAN`` assertion once the module is importable. (The static AST gate
    above already auto-covers ``ingest.py`` via the ``memory/*.py`` glob; this
    adds the runtime-dormancy parity, not a duplicate of the static scan.)

    T-64-02 (Tampering): future ingest imports the live reaction path —
    mitigated by this gate (the build fails if violated).
    """
    script = (
        "import sys\n"
        "import vibemix.memory.ingest  # noqa: F401\n"
        "leak = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m.startswith('vibemix.state.coach')\n"
        "    or m.startswith('vibemix.state.refresh')\n"
        "    or m.startswith('vibemix.agent')\n"
        "    or m.startswith('vibemix.prompts')\n"
        "    or 'ws_bus' in m\n"
        ")\n"
        "print('LEAKED:' + ','.join(leak) if leak else 'CLEAN')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    # RED-first: the module does not exist yet, so the import fails (non-zero
    # exit) and stdout is NOT "CLEAN" — that pins the contract. Once 64-02 lands
    # the import succeeds and stdout must be exactly "CLEAN".
    assert result.stdout.strip() == "CLEAN", (
        "ingest import leaked a live-path module (or vibemix.memory.ingest is "
        f"not importable yet — expected once Plan 64-02 lands). stdout="
        f"{result.stdout!r}; stderr={result.stderr!r}"
    )
