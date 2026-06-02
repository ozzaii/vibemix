# SPDX-License-Identifier: Apache-2.0
"""Live-App Reality PINS for Learn beatmatch Mastered credit.

Beatmatching used to be capped at Competent because the recognizer branch existed
but no production code could emit ``BEATMATCH_GRADED``. The reality changed when
``learn.practice_loop`` landed: one owned-deck producer now calls the Beatmatch
Judge, writes the matching evidence receipt, and hands the event to the normal
recognizer credit path.

These pins guard both sides of that truth:

* the consumer branch still exists, so a cited grade can be recognized;
* there is exactly one production producer, and it lives in the Learn-owned deck
  loop, not the live co-host observer or a proxy detector.
"""

from __future__ import annotations

import ast
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
_SRC = _REPO / "src" / "vibemix"
_PRODUCER = str(_SRC / "learn" / "practice_loop.py")
_RUNTIME = str(_SRC / "learn" / "runtime.py")
_EMITTER_FNS = frozenset({"grade_beatmatch", "grade_to_event_extra"})
_PRACTICE_PRODUCER_FNS = frozenset(
    {"grade_owned_beatmatch_attempt", "grade_minideck_beatmatch_attempt"}
)
_GRADED_EVENT_KIND = "BEATMATCH_GRADED"


def _src_py_files() -> list[pathlib.Path]:
    return [
        p
        for p in sorted(_SRC.rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _emitter_call_sites() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in _src_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name in _EMITTER_FNS:
                    hits.append((str(path), node.lineno, name))
    return hits


def _practice_producer_call_sites() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in _src_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name in _PRACTICE_PRODUCER_FNS:
                    hits.append((str(path), node.lineno, name))
    return hits


def _src_files_importing_judge() -> list[str]:
    found: list[str] = []
    for path in _src_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.endswith("beatmatch_judge") or mod == "beatmatch_judge":
                    found.append(str(path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.endswith("beatmatch_judge"):
                        found.append(str(path))
    return sorted({f for f in found if not f.endswith("beatmatch_judge.py")})


def test_beatmatch_judge_has_one_owned_deck_production_emitter() -> None:
    call_sites = _emitter_call_sites()
    assert {path for path, _lineno, _name in call_sites} == {_PRODUCER}
    assert {name for _path, _lineno, name in call_sites} == _EMITTER_FNS


def test_beatmatch_judge_import_is_limited_to_practice_loop() -> None:
    assert _src_files_importing_judge() == [_PRODUCER]


def test_beatmatch_practice_producer_has_a_runtime_caller() -> None:
    call_sites = _practice_producer_call_sites()
    runtime_callers = {
        (path, name)
        for path, _lineno, name in call_sites
        if path != _PRODUCER
    }
    assert (_RUNTIME, "grade_owned_beatmatch_attempt") in runtime_callers


def test_beatmatch_credit_consumer_is_wired_to_the_producer_event() -> None:
    recognizer = (_SRC / "learn" / "skill_recognizer.py").read_text(encoding="utf-8")
    producer = (_SRC / "learn" / "practice_loop.py").read_text(encoding="utf-8")
    assert f'== "{_GRADED_EVENT_KIND}"' in recognizer
    assert f'BEATMATCH_GRADED_EVENT = "{_GRADED_EVENT_KIND}"' in producer
    assert '"beatmatching"' in recognizer


def test_pin_is_non_vacuous_emitter_signal_is_detectable() -> None:
    sample = "x = grade_to_event_extra(grade)\ny = grade_beatmatch(a, b, s)\n"
    tree = ast.parse(sample)
    names = {
        _call_name(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node) in _EMITTER_FNS
    }
    assert names == _EMITTER_FNS
