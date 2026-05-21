# SPDX-License-Identifier: Apache-2.0
"""The Kaan-ear veto scorer — the HARMONIC-03 KAAN-ACTION ship gate.

This is the runnable surface Kaan uses to clear the harmonic clash detector for
release. It loads the disagreed-pairs corpus, runs the shipped ``is_clash``
predicate over every pair, and reports per-pair PASS/FAIL plus a summary — exiting
0 ONLY when every pair matches its declared verdict.

WHY THIS GATE EXISTS
--------------------
Over-flagging is the release-tripping failure: a false clash on a pair Kaan would
happily mix (e.g. an adjacent fifth 8A→9A, or a +2 energy move 8A→10A) reaches the
audience and the co-host sounds wrong. So the runtime ``harmonic_clash_enabled``
flag (Plan 60-02) ships **False** — the detector is QUIET by default. It flips to
True ONLY after Kaan:
  1. Adds his real disagreed pairs to ``tests/fixtures/kaan_disagreed_pairs.json``
     ("safe" verdict = pairs he rides cleanly),
  2. Runs this scorer and confirms ZERO false clashes (exit 0),
  3. Sign-off recorded as the KAAN-ACTION item.

Below that bar — any "safe" pair flagging, or the corpus going vacuous (a "clash"
control not flagging) — the scorer exits non-zero and the flag stays False. The
conservative default (detector OFF) is the SAFE state, NOT a failure: no false clash
can reach the audience while the gate is open. Mirrors the Phase-59 deck-vision eval
precedent (``eval/deck_vision/run_eval.py``: a documented floor + a default-off flag
that flips only on sign-off).

THE CORPUS
----------
``tests/fixtures/kaan_disagreed_pairs.json`` — a JSON array of
``{"a", "b", "verdict": "safe"|"clash", "note"}`` objects. "safe" = MUST NOT flag
(the veto); "clash" = SHOULD flag (the non-vacuous control). Kaan edits this file to
add the pairs his ear disagrees with.

INVOCATION
----------
    PYTHONPATH=src python3 eval/harmonic/run_veto.py
    PYTHONPATH=src python3 eval/harmonic/run_veto.py --json report.json
    PYTHONPATH=src python3 eval/harmonic/run_veto.py --corpus path/to/corpus.json

No new dependencies — stdlib ``json`` + the shipped ``vibemix.state.harmonics``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Default corpus location, resolved relative to THIS file (repo-portable).
_DEFAULT_CORPUS = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "kaan_disagreed_pairs.json"
)


@dataclass
class PairResult:
    a: str
    b: str
    verdict: str  # declared: "safe" | "clash"
    flagged: bool  # what is_clash actually returned
    note: str

    @property
    def passed(self) -> bool:
        """A "safe" pair must NOT flag; a "clash" pair MUST flag."""
        if self.verdict == "safe":
            return self.flagged is False
        if self.verdict == "clash":
            return self.flagged is True
        return False  # unknown verdict is a corpus authoring error → FAIL

    @property
    def fail_reason(self) -> str:
        if self.passed:
            return ""
        if self.verdict == "safe":
            return "FALSE CLASH — a pair Kaan would mix flagged (release-tripping)"
        if self.verdict == "clash":
            return "VACUOUS GATE — a true clash failed to flag"
        return f"unknown verdict {self.verdict!r}"


def load_corpus(path: Path) -> list[dict]:
    """Load the disagreed-pairs corpus (the editable Kaan-ear record)."""
    return json.loads(path.read_text())


def score_corpus(corpus: list[dict]) -> list[PairResult]:
    """Run ``is_clash`` over every pair and pair it with its declared verdict."""
    # Late import keeps the module importable for --help without src on the path.
    from vibemix.state.harmonics import is_clash

    results: list[PairResult] = []
    for entry in corpus:
        a, b = entry.get("a"), entry.get("b")
        results.append(
            PairResult(
                a=str(a),
                b=str(b),
                verdict=str(entry.get("verdict", "")),
                flagged=bool(is_clash(a, b)),
                note=str(entry.get("note", "")),
            )
        )
    return results


def format_report(results: list[PairResult]) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("Kaan-ear veto — harmonic clash ship gate (HARMONIC-03)")
    lines.append("rule: every pair must match its declared verdict (safe=quiet, clash=flag)")
    lines.append("=" * 72)
    lines.append(f"{'pair':<12}{'declared':>10}{'is_clash':>10}{'result':>9}  note")
    lines.append("-" * 72)

    n_safe = n_clash = n_fail = 0
    for r in results:
        if r.verdict == "safe":
            n_safe += 1
        elif r.verdict == "clash":
            n_clash += 1
        if not r.passed:
            n_fail += 1
        result = "PASS" if r.passed else "FAIL"
        lines.append(
            f"{r.a + '/' + r.b:<12}{r.verdict:>10}{str(r.flagged):>10}{result:>9}  {r.note}"
        )
        if not r.passed:
            lines.append(f"    [FAIL] {r.fail_reason}")

    lines.append("-" * 72)
    total = len(results)
    lines.append(
        f"{total} pairs — {n_safe} safe (must-not-flag) / {n_clash} clash (must-flag) — "
        f"{total - n_fail} pass / {n_fail} fail"
    )
    lines.append("=" * 72)
    if n_fail == 0:
        lines.append(
            "GATE PASS: zero false clashes, controls flag. This run is the evidence "
            "Kaan signs off on before flipping harmonic_clash_enabled to True. Until "
            "then the detector stays OFF — the conservative default."
        )
    else:
        lines.append(
            "GATE FAIL: harmonic_clash_enabled MUST stay False. The detector remains "
            "OFF (the conservative default = the SAFE state, NOT a crash). Fix the "
            "predicate or correct the corpus, then re-run."
        )
    return "\n".join(lines)


def _results_to_dict(results: list[PairResult]) -> dict:
    n_fail = sum(1 for r in results if not r.passed)
    return {
        "gate": "HARMONIC-03 Kaan-ear veto",
        "total": len(results),
        "failures": n_fail,
        "all_pass": n_fail == 0,
        "pairs": [
            {
                "a": r.a,
                "b": r.b,
                "verdict": r.verdict,
                "flagged": r.flagged,
                "passed": r.passed,
                "fail_reason": r.fail_reason,
                "note": r.note,
            }
            for r in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Kaan-ear veto — harmonic clash ship gate (HARMONIC-03)"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=_DEFAULT_CORPUS,
        help="path to the disagreed-pairs corpus JSON (default: tests/fixtures/kaan_disagreed_pairs.json)",
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="also write a machine-readable JSON report"
    )
    args = parser.parse_args(argv)

    if not args.corpus.exists():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 2

    corpus = load_corpus(args.corpus)
    results = score_corpus(corpus)
    print(format_report(results))

    if args.json is not None:
        args.json.write_text(json.dumps(_results_to_dict(results), indent=2))
        print(f"\n[json] wrote {args.json}")

    # Exit 0 ONLY when every pair matches its declared verdict. A non-zero exit
    # surfaces the KAAN-ACTION review — the flag stays False until this clears.
    all_pass = all(r.passed for r in results) if results else False
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
