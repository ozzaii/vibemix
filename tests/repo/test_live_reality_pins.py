# SPDX-License-Identifier: Apache-2.0
"""Live-App Reality PINS — guard the v11 "Earned" skill-tree against a false
"Mastered" claim that the production code cannot actually back.

This is a PIN, not new functionality. It locks the CURRENTLY-TRUE reality
(verified against HEAD this session) so a future refactor that flips it fails
LOUDLY here instead of shipping a silent dead feature.

REALITY VERIFIED (HEAD, 2026-05-31)
-----------------------------------
The v11.0 "Earned" tree treats ``beatmatching`` as a masterable competency, and
the credit CONSUMER is wired: ``src/vibemix/learn/skill_recognizer.py`` has a
``if ev_type == "BEATMATCH_GRADED":`` branch (skill_recognizer.py:158) that
credits beatmatching only on a cited, non-abstain, LOCKED grade.

But the credit PRODUCER is ORPHANED. ``src/vibemix/learn/beatmatch_judge.py``
defines the owned-deck grader (``grade_beatmatch`` :83 / ``grade_to_event_extra``
:145) and its docstring claims "The live practice loop fires a
``BEATMATCH_GRADED`` event …" (beatmatch_judge.py:151) — but NO production file
under ``src/vibemix`` calls the grader or constructs that event:

  * AST scan: zero ``grade_beatmatch`` / ``grade_to_event_extra`` call-sites in
    ``src/vibemix`` (the only call-sites are in ``tests/learn/`` stubs).
  * No ``src/vibemix`` module imports ``beatmatch_judge`` at all — the engine is
    import-orphaned in production; only tests reach it.

CONSEQUENCE: with no production emitter, a ``BEATMATCH_GRADED`` event can never
fire live, so ``beatmatching`` can never be live-demonstrated, so any
credit/UI that reports it "Mastered" (e.g. a "6/6 Mastered" v11 claim) would be
FALSE — it cites a demonstration the app is incapable of observing. Invariant #3
(trust the audio / never invent) forbids that claim.

WHAT THIS PIN ENFORCES
----------------------
The pin asserts the ORPHANED reality and is MEANINGFUL: the moment a real
practice loop wires the grader (a production call to ``grade_beatmatch`` /
``grade_to_event_extra``, or a production construction of the
``BEATMATCH_GRADED`` event type), ``test_beatmatch_judge_has_no_production_emitter``
FLIPS to failing — which is the desired signal to DELETE this pin and let the
"Mastered" claim stand. Until then it guards against a false-expertise ship.

No re-implementation, no genai.Client, no API key — a filesystem/AST scan over
the existing source surface (mirrors ``test_wire_regression_pins.py``'s
assert-only, public-surface posture but inverted: it pins an ABSENCE).
"""

from __future__ import annotations

import ast
import pathlib

# Repo-root-relative source tree (this file lives at tests/repo/).
_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "vibemix"

# The owned-deck Beatmatch Judge: the ONLY way to emit a real, grounded
# BEATMATCH_GRADED grade is to call one of these. A production call-site is the
# unambiguous fingerprint of a live emitter (AST sees calls, not comments or
# docstrings — the prose claims in beatmatch_judge.py do not match).
_EMITTER_FNS = frozenset({"grade_beatmatch", "grade_to_event_extra"})

# The graded event kind the skill recognizer credits beatmatching on.
_GRADED_EVENT_KIND = "BEATMATCH_GRADED"


def _src_py_files() -> list[pathlib.Path]:
    """Every production ``.py`` under ``src/vibemix`` (excludes caches)."""
    return [
        p
        for p in sorted(_SRC.rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


def _call_name(node: ast.Call) -> str | None:
    """The bare callee name of a call node (``f(...)`` or ``mod.f(...)``)."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _emitter_call_sites() -> list[tuple[str, int, str]]:
    """Production call-sites of the Beatmatch-Judge grader, via AST.

    AST parsing ignores comments and docstrings, so the engine's aspirational
    "the live practice loop fires …" docstring and the recognizer's explanatory
    comments do NOT register — only a genuine ``grade_beatmatch(...)`` /
    ``grade_to_event_extra(...)`` call does.
    """
    hits: list[tuple[str, int, str]] = []
    for path in _src_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name in _EMITTER_FNS:
                    hits.append((str(path), node.lineno, name))
    return hits


def _src_files_importing_judge() -> list[str]:
    """Production modules that import ``beatmatch_judge`` (any import form)."""
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
    # The engine file imports nothing of itself; exclude it defensively.
    return sorted({f for f in found if not f.endswith("beatmatch_judge.py")})


# ---------------------------------------------------------------------------
# PIN — beatmatch is masterable but has NO production emitter (orphaned engine)
# ---------------------------------------------------------------------------


def test_beatmatch_judge_has_no_production_emitter() -> None:
    """No production ``src/vibemix`` file calls the Beatmatch-Judge grader.

    THE load-bearing pin. While this holds, a ``BEATMATCH_GRADED`` event can
    never fire live → beatmatching can never be live-demonstrated → any
    "Mastered" credit for it is false (Invariant #3). The instant a real
    practice loop wires the grader, this assertion FAILS — the intended signal
    to retire the pin and let the "Mastered" claim stand.
    """
    call_sites = _emitter_call_sites()
    assert call_sites == [], (
        "A production beatmatch grader call-site appeared: "
        f"{call_sites}. Beatmatch is now (or may be) live-emittable — re-verify "
        "the end-to-end live-demonstration path and DELETE this pin; the v11 "
        '"Mastered" claim for beatmatching is no longer necessarily false.'
    )


def test_beatmatch_judge_is_import_orphaned_in_production() -> None:
    """No production module imports ``beatmatch_judge`` — the engine is orphaned.

    A second, independent fingerprint of the same dead feature: you cannot emit
    a grade from a module that never imports the grader. Fails the moment a live
    module wires it in (corroborates the call-site pin above).
    """
    importers = _src_files_importing_judge()
    assert importers == [], (
        "A production module now imports beatmatch_judge "
        f"({importers}) — the orphan may be getting wired live. Re-verify the "
        "live-demonstration path and update/retire these reality pins."
    )


def test_beatmatch_credit_consumer_is_wired_but_starved() -> None:
    """The CONSUMER branch exists, proving the asymmetry that makes this a trap.

    ``skill_recognizer`` is READY to credit a ``BEATMATCH_GRADED`` grade — so the
    only thing standing between the current code and a (false) "Mastered" credit
    is the missing emitter the two pins above guard. This asserts the consumer is
    present so a future refactor that ALSO removes the consumer (closing the trap
    from the other side) forces a deliberate re-read of these pins rather than
    silently making them vacuous.
    """
    recognizer = (_SRC / "learn" / "skill_recognizer.py").read_text(encoding="utf-8")
    # The branch that credits beatmatching off the graded event.
    assert f'== "{_GRADED_EVENT_KIND}"' in recognizer, (
        "the BEATMATCH_GRADED consumer branch in skill_recognizer.py is gone — "
        "the credit asymmetry these pins describe has changed; re-verify."
    )
    assert '"beatmatching"' in recognizer, (
        "skill_recognizer no longer references the beatmatching skill id — "
        "the credit path changed; re-verify these reality pins."
    )


def test_pin_is_non_vacuous_emitter_signal_is_detectable() -> None:
    """Guard the guard: prove the emitter-detection logic actually fires.

    A pin that asserts an empty list is only meaningful if the detector CAN
    produce a non-empty list. Parse a synthetic in-memory module that DOES call
    the grader and confirm the same AST logic flags it — so the green of
    ``test_beatmatch_judge_has_no_production_emitter`` reflects real absence, not
    a detector that never matches.
    """
    sample = "x = grade_to_event_extra(grade)\ny = grade_beatmatch(a, b, s)\n"
    tree = ast.parse(sample)
    names = {
        _call_name(n)
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _call_name(n) in _EMITTER_FNS
    }
    assert names == _EMITTER_FNS, (
        "the emitter-call detector failed to flag a synthetic grader call — the "
        "absence pin would be vacuously green; fix the detector"
    )
