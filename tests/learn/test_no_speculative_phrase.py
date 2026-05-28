# SPDX-License-Identifier: Apache-2.0
"""Phase 96 Plan 01 — Invariant #3 (trust the audio) static AST gate.

The ``src/vibemix/learn/`` package MUST NOT import phrase-guessing FFT /
onset / beat-tracking primitives. Phrase structure is consumed from
``state/refresh.py`` + ``CueAnchor`` — the learn package never computes
its own. Computing fresh FFT / onset / beat data inside the lesson
runtime would let the proactive tutor lens (Course 3) invent "breakdown
in 16 beats" structure the audio never showed — exactly the Invariant #3
"trust the audio" failure mode this gate exists to prevent.

The gate is structural (static AST grep). It lands BEFORE any Gemini
wiring (per CONTEXT.md §Decisions §order-of-operations step 1) so a
future planner cannot inadvertently bypass it by writing the tutor
narration before the gate.

REQ-ID: CURR-3.07 + Invariant #3 binding.

Detection forms covered (all three syntactic shapes redden the gate):
  1. ``import numpy.fft`` / ``import numpy.fft as nfft``
  2. ``from numpy import fft`` / ``from numpy import fft as nfft``
  3. ``from numpy.fft import rfft`` / ``from numpy.fft import *``

Sampling: per-task commit (~50 ms — file walk + ``ast.parse``).
"""
from __future__ import annotations

import ast
import pathlib
from typing import Iterable


# Phrase-guessing primitives forbidden in src/vibemix/learn/.
# The learn/ package consumes already-grounded phrase data via
# state/refresh.py + CueAnchor; computing its own would let the tutor
# invent a "breakdown in 16 beats" the user's deck never saw — exactly
# the failure mode the Invariant #3 pin exists to prevent.
#
# Each entry is a tuple of (top, sub) — the AST gate checks:
#   - ``import numpy.fft`` (Import node with name "numpy.fft")
#   - ``from numpy import fft`` (ImportFrom with module="numpy", alias "fft")
#   - ``from numpy.fft import rfft`` (ImportFrom with module="numpy.fft")
# All three forms must red the gate.
_FORBIDDEN_MODULES: tuple[tuple[str, str], ...] = (
    ("numpy", "fft"),
    ("scipy", "signal"),
    ("scipy", "fft"),
    ("librosa", "beat"),
    ("librosa", "onset"),
)


def _repo_root() -> pathlib.Path:
    # tests/learn/test_no_speculative_phrase.py → ../../
    return pathlib.Path(__file__).resolve().parent.parent.parent


def _default_learn_dir() -> pathlib.Path:
    return _repo_root() / "src" / "vibemix" / "learn"


def _walk_python_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    if not root.exists():
        return
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _detect_forbidden_imports(
    path: pathlib.Path,
) -> list[tuple[int, str]]:
    """Return list of (line_no, offending import statement) for the file.

    Detects all three syntactic forms:
      1. ``import numpy.fft`` / ``import numpy.fft as nfft``
      2. ``from numpy import fft`` / ``from numpy import fft as nfft``
      3. ``from numpy.fft import rfft`` / ``from numpy.fft import *``
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        # A malformed learn/ module is a different failure class;
        # surface it as a gate-fail too so it doesn't ride through.
        return [(getattr(exc, "lineno", 0) or 0, f"SyntaxError: {exc}")]
    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # ``import numpy.fft`` / ``import scipy.signal as sps``
            for alias in node.names:
                name = alias.name  # full dotted, e.g. "numpy.fft"
                for top, sub in _FORBIDDEN_MODULES:
                    if name == f"{top}.{sub}" or name.startswith(
                        f"{top}.{sub}."
                    ):
                        offenders.append(
                            (node.lineno, f"import {name}")
                        )
        elif isinstance(node, ast.ImportFrom):
            # ``from numpy import fft`` (module="numpy", names=["fft"])
            # ``from numpy.fft import rfft`` (module="numpy.fft", names=["rfft"])
            module = node.module or ""
            for top, sub in _FORBIDDEN_MODULES:
                # Form 3: ``from numpy.fft import rfft`` (or any name)
                if module == f"{top}.{sub}" or module.startswith(
                    f"{top}.{sub}."
                ):
                    names = ", ".join(a.name for a in node.names)
                    offenders.append(
                        (node.lineno, f"from {module} import {names}")
                    )
                    break  # one offender hit per node is enough
                # Form 2: ``from numpy import fft``
                if module == top:
                    for alias in node.names:
                        if alias.name == sub:
                            offenders.append(
                                (node.lineno, f"from {top} import {sub}")
                            )
                            break
    return offenders


def test_learn_package_imports_no_phrase_guessing_primitives() -> None:
    """CURR-3.07 + Invariant #3 — learn/ never computes phrase structure.

    The Course 3 proactive tutor lens MUST consume already-grounded
    phrase data via state/refresh.py + CueAnchor. Computing its own
    FFT / onset / beat-tracking would let the tutor invent structure
    the audio never showed (exactly the Invariant #3 'trust the audio'
    failure mode). This gate lands BEFORE any Gemini wiring per
    CONTEXT.md §Decisions §order-of-operations step 1.
    """
    learn_dir = _default_learn_dir()
    all_offenders: list[str] = []
    for path in _walk_python_files(learn_dir):
        for line_no, stmt in _detect_forbidden_imports(path):
            all_offenders.append(f"{path}:{line_no}: {stmt}")
    assert not all_offenders, (
        "Invariant #3 violation — ``src/vibemix/learn/`` imports "
        "phrase-guessing primitives. Trust the audio means consume "
        "state/refresh.py + CueAnchor for phrase structure; never "
        "compute it. Move FFT/onset/beat-tracking to state/ if "
        "genuinely needed.\n\nOffenders:\n  "
        + "\n  ".join(all_offenders)
    )


def test_gate_fires_red_on_synthetic_offender(tmp_path: pathlib.Path) -> None:
    """Negative-control proof. Plant a synthetic offender + verify the
    gate catches it.
    """
    offender = tmp_path / "fake_module.py"
    offender.write_text("from scipy import signal\n", encoding="utf-8")
    offenders = _detect_forbidden_imports(offender)
    assert offenders, "gate failed to detect a known-bad import"
    assert any(
        "from scipy import signal" in o[1] for o in offenders
    ), f"unexpected diagnostic shape: {offenders}"


def test_gate_detects_all_three_syntactic_forms(
    tmp_path: pathlib.Path,
) -> None:
    """Importing numpy.fft / scipy.signal / etc. comes in three syntactic
    forms; all three must red the gate.
    """
    cases = [
        ("import_dotted.py", "import numpy.fft\n", "import numpy.fft"),
        ("from_top.py", "from numpy import fft\n", "from numpy import fft"),
        (
            "from_dotted.py",
            "from numpy.fft import rfft\n",
            "from numpy.fft import rfft",
        ),
    ]
    for filename, source, expected_substr in cases:
        path = tmp_path / filename
        path.write_text(source, encoding="utf-8")
        offenders = _detect_forbidden_imports(path)
        assert offenders, f"missed offender shape in {filename!r}"
        assert any(
            expected_substr in o[1] for o in offenders
        ), (
            f"diagnostic for {filename!r} did not name the offender: "
            f"{offenders}"
        )


def test_gate_ignores_pycache_and_non_python(
    tmp_path: pathlib.Path,
) -> None:
    """``__pycache__`` files + non-``.py`` files must NOT be scanned."""
    cache = tmp_path / "__pycache__" / "foo.cpython-312.pyc"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(b"\x03\xf3")  # garbage byte content
    readme = tmp_path / "README.md"
    readme.write_text("from scipy import signal\n", encoding="utf-8")
    files = list(_walk_python_files(tmp_path))
    assert all(
        "__pycache__" not in p.parts for p in files
    ), f"walker leaked __pycache__: {files}"
    assert not any(
        p.suffix == ".md" for p in files
    ), f"walker leaked non-Python file: {files}"
