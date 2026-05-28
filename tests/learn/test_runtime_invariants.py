# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — Invariant #1 (single-writer) static-grep gate.

The ``learn/`` package never WRITES to :class:`MusicState` or
:class:`ControllerState`. Both are owned by the live deck (the
state-refresh loop is the sole writer of MusicState; the MIDI listener
is the sole writer of ControllerState). LessonRuntime READS from
``ControllerState.deck_snapshot()`` + ``MidiMirror.snapshot()`` and
writes ONLY to ``LearnState`` (the new dataclass shipped by Plan 92-03).

Two test functions — both LIVE day-one (the AST greps target a
directory that exists from Plan 91-02). The second function exempts
``runtime.py`` (the sole writer of LearnState) and ``state.py`` (the
LearnState dataclass definition with ``field(default_factory=...)``
defaults that look like writes to a regex).

REQ-ID: LESSON-01 (single-writer guarantee for LearnState).

Sampling: per-task commit (~10 ms — file walk + line-oriented regex).
"""
from __future__ import annotations

import pathlib
import re


def _repo_root() -> pathlib.Path:
    # tests/learn/test_runtime_invariants.py → ../../
    return pathlib.Path(__file__).resolve().parent.parent.parent


LEARN_DIR = _repo_root() / "src" / "vibemix" / "learn"


# Patterns that look like writes to forbidden objects. We match common
# instance names (`music_state`, `controller_state`, plus the canonical
# CamelCase class names) followed by a field assignment.
FORBIDDEN_WRITES = (
    re.compile(r"\b(music_state|MusicState)\.\w+\s*=\s*"),
    re.compile(r"\b(controller_state|ControllerState)\.\w+\s*=\s*"),
)


def _walk_python_files(root: pathlib.Path):
    """Yield ``*.py`` files under ``root`` (recursive), skipping pycache.

    Trivially yields nothing when ``root`` does not exist (Plan 92-03
    hasn't landed the runtime/state modules yet — but Plan 91-03
    already shipped ``midi_mirror.py`` so this directory exists).
    """
    if not root.exists():
        return
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def test_learn_package_never_writes_music_state_or_controller_state() -> None:
    """Walk ``src/vibemix/learn/**/*.py`` and assert zero ``MusicState`` or
    ``ControllerState`` field writes.

    Currently PASSES because Plan 91-03 shipped ``midi_mirror.py`` as a
    pure reader. Stays green as Plans 92-03..05 add ``runtime.py`` /
    ``state.py`` / ``prompts.py`` — they must read, not write, those
    live-deck owned objects.
    """
    offenders: list[str] = []
    for path in _walk_python_files(LEARN_DIR):
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            for pat in FORBIDDEN_WRITES:
                if pat.search(line):
                    offenders.append(f"{path}:{line_no}: {line.strip()}")

    assert not offenders, (
        "Invariant #1 violation — ``learn/`` wrote to MusicState or "
        "ControllerState. Both are live-deck owned; LessonRuntime reads "
        "only.\n" + "\n".join(offenders)
    )


def test_learn_state_writes_are_only_inside_runtime_py() -> None:
    """LessonRuntime is the sole writer of LearnState. Outside
    ``runtime.py`` / ``state.py``, no ``learn/`` module should write
    LearnState fields.

    Currently PASSES trivially (no ``learn_state`` references exist yet
    in ``learn/``). After Plan 92-03 lands ``runtime.py`` (sole writer,
    exempted) + ``state.py`` (dataclass definition with
    ``field(default_factory=...)`` defaults that look like writes to a
    regex — also exempted), this gate continues to bind.
    """
    pat = re.compile(r"\b(learn_state|self\._learn)\.\w+\s*=\s*")
    offenders: list[str] = []
    for path in _walk_python_files(LEARN_DIR):
        if path.name == "runtime.py":
            continue  # sole-writer file
        if path.name == "state.py":
            continue  # dataclass DEFINITION — default_factory etc. allowed
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if pat.search(line):
                offenders.append(f"{path}:{line_no}: {line.strip()}")

    assert not offenders, (
        "Invariant #1 violation — non-runtime ``learn/`` module wrote to "
        "LearnState. LessonRuntime is the sole writer.\n"
        + "\n".join(offenders)
    )
