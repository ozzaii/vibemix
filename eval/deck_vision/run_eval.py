# SPDX-License-Identifier: Apache-2.0
"""Real-screenshot accuracy eval harness for the Gemini-vision deck-read (DECK-02).

This is the ONLY live-Gemini path for Plan 59-05 — and it is OPT-IN. The default
fast suite (`PYTHONPATH=src python3 -m pytest -q`) does NOT import or run this
harness; it is invoked explicitly by Kaan against his real-rig screenshot corpus
(the KAAN-ACTION checkpoint, Plan 59-05 Task 3).

WHY THIS GATE EXISTS
--------------------
Re-enabling vision un-does a deliberate v4 anti-hallucination killswitch
(`dj_cohost.py: screen_jpeg = None`). A vision-misread key badge is a SILENT
error — the same hallucination class as a wrong library tag. So vision-sourced
keys MUST NOT feed deck-state until the real-screenshot accuracy clears a
documented floor, PER APP. Below the floor, an app degrades to XML-or-unknown —
never a guessed badge. This harness measures that accuracy and emits the
per-app + overall report the gate decision is made on.

CORPUS LAYOUT
-------------
Pass a corpus directory. Each screenshot is a JPEG/PNG named by app, paired with
a ground-truth JSON label (hand-labeled by Kaan):

    <corpus_dir>/
      djay_001.jpg        djay_001.json
      djay_002.jpg        djay_002.json
      serato_001.png      serato_001.json
      traktor_dark_001.jpg traktor_dark_001.json
      ...

The label JSON mirrors the read schema, with the TRUTH the badge actually shows:

    {
      "app": "djay",                    # djay | serato | traktor | engine | ...
      "theme": "dark",                  # light | dark  (optional, for slicing)
      "decks": [
        {"side": "A", "title": "Strobe", "key": "8A", "bpm": 128},
        {"side": "B", "title": null,     "key": null,  "bpm": null}
      ]
    }

A `null` truth field means "not legible on this screenshot" — the read is scored
CORRECT iff it ALSO returns null (rewarding honest abstention, penalizing a guess).

ACCURACY METRIC
---------------
Per deck, two independent sub-scores:
  * title accuracy  — case-insensitive exact match (null↔null counts correct)
  * key accuracy    — Camelot-normalized exact match (null↔null counts correct)
BPM is reported for context but is NOT part of the gate (it is the least
hallucination-sensitive field). Per-app accuracy = mean of per-deck title+key
correctness across that app's screenshots. The gate is on title AND key.

THE GATE
--------
`ACCURACY_FLOOR` is the per-app threshold. An app at or above the floor MAY have
vision-sourced keys enabled (at the below-XML `deck_vision.VISION_CONF`). An app
below the floor stays XML-or-unknown — vision dormant for it. This is the
conservative-by-design path, NOT a failure.

INVOCATION
----------
    PYTHONPATH=src python3 eval/deck_vision/run_eval.py <corpus_dir>
    PYTHONPATH=src python3 eval/deck_vision/run_eval.py <corpus_dir> --json report.json

Requires `GEMINI_API_KEY` in the environment / repo-root `.env` (no new key).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------- #
# The gate constant — the documented accuracy floor                       #
# ---------------------------------------------------------------------- #

# Per-app accuracy floor for ENABLING vision-sourced keys. A misread badge is a
# silent error; the floor must be high enough that an enabled app's reads are
# trustworthy at the (below-XML) vision confidence. 0.90 is the starting bar —
# Kaan tunes/locks it at the eval gate (Task 3) against the measured real-rig
# numbers, mirroring eval/THRESHOLD-LOCK.md discipline. Below this floor an app
# degrades to XML-or-unknown (vision dormant) — the conservative default.
ACCURACY_FLOOR: float = 0.90

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


# ---------------------------------------------------------------------- #
# Result aggregation                                                      #
# ---------------------------------------------------------------------- #


@dataclass
class AppScore:
    app: str
    title_correct: int = 0
    title_total: int = 0
    key_correct: int = 0
    key_total: int = 0
    samples: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def title_accuracy(self) -> float:
        return self.title_correct / self.title_total if self.title_total else 0.0

    @property
    def key_accuracy(self) -> float:
        return self.key_correct / self.key_total if self.key_total else 0.0

    @property
    def overall_accuracy(self) -> float:
        """Combined title+key accuracy — the number the gate is decided on."""
        total = self.title_total + self.key_total
        correct = self.title_correct + self.key_correct
        return correct / total if total else 0.0

    @property
    def passes_floor(self) -> bool:
        return self.overall_accuracy >= ACCURACY_FLOOR


def _norm_title(t: Any) -> str | None:
    if not isinstance(t, str) or not t.strip():
        return None
    return t.strip().casefold()


def _norm_key(k: Any) -> str | None:
    # Late import keeps the module importable for `ast.parse` / `--help` without src on path.
    from vibemix.state.harmonics import to_camelot

    if not isinstance(k, str) or not k.strip():
        return None
    return to_camelot(k)


def _score_decks(truth_decks: list, read_decks: dict, score: AppScore) -> None:
    """Score one screenshot's decks into the running AppScore."""
    read_by_side = {s.upper(): dt for s, dt in read_decks.items()}
    for td in truth_decks:
        if not isinstance(td, dict):
            continue
        side = str(td.get("side", "")).strip().upper()
        if side not in ("A", "B", "C", "D"):
            continue
        truth_title = _norm_title(td.get("title"))
        truth_key = _norm_key(td.get("key"))

        read_dt = read_by_side.get(side)
        read_title = _norm_title(getattr(read_dt, "title", None)) if read_dt else None
        read_key = getattr(read_dt, "camelot", None) if read_dt else None
        read_key = read_key.upper() if isinstance(read_key, str) else None

        # null↔null counts as correct (rewards honest abstention).
        score.title_total += 1
        if read_title == truth_title:
            score.title_correct += 1

        score.key_total += 1
        if read_key == truth_key:
            score.key_correct += 1


# ---------------------------------------------------------------------- #
# Corpus loading + harness                                                #
# ---------------------------------------------------------------------- #


def _load_corpus(corpus_dir: Path) -> list[tuple[Path, dict]]:
    """Pair each image with its `<stem>.json` ground-truth label."""
    pairs: list[tuple[Path, dict]] = []
    for img in sorted(corpus_dir.iterdir()):
        if img.suffix.lower() not in _IMAGE_EXTS:
            continue
        label_path = img.with_suffix(".json")
        if not label_path.exists():
            print(f"[warn] no label for {img.name} — skipping", file=sys.stderr)
            continue
        try:
            label = json.loads(label_path.read_text())
        except (ValueError, OSError) as e:
            print(f"[warn] bad label {label_path.name}: {e} — skipping", file=sys.stderr)
            continue
        pairs.append((img, label))
    return pairs


def run_eval(corpus_dir: Path, *, reader=None) -> dict[str, AppScore]:
    """Run the vision read against every labeled screenshot; return per-app scores.

    ``reader`` is injectable for testing; in production it is a live
    ``DeckVisionReader`` (the ONLY live-Gemini path, opt-in). Each read uses
    ``interval=0`` so the harness is not throttled by the runtime debounce.
    """
    if reader is None:
        reader = _build_live_reader()

    pairs = _load_corpus(corpus_dir)
    if not pairs:
        raise SystemExit(f"no labeled screenshots found under {corpus_dir}")

    scores: dict[str, AppScore] = defaultdict(lambda: AppScore(app="unknown"))
    for img_path, label in pairs:
        app = str(label.get("app", "unknown")).strip().lower() or "unknown"
        sc = scores.setdefault(app, AppScore(app=app))
        sc.samples += 1
        try:
            jpeg = img_path.read_bytes()
            read_decks = reader.read(jpeg)
        except Exception as e:  # one bad screenshot must not abort the run
            sc.errors.append(f"{img_path.name}: {type(e).__name__}: {e}")
            continue
        truth_decks = label.get("decks", [])
        if isinstance(truth_decks, list):
            _score_decks(truth_decks, read_decks, sc)
    return dict(scores)


def _build_live_reader():
    """Construct the live DeckVisionReader (GEMINI_API_KEY required)."""
    import os

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
    from google import genai

    from vibemix.agent.config import LLM_MODEL
    from vibemix.state.deck_vision import DeckVisionReader

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set (repo-root .env or env) — required for the live eval")
    client = genai.Client(api_key=api_key)
    return DeckVisionReader(client=client, model=LLM_MODEL, interval=0.0)


# ---------------------------------------------------------------------- #
# Reporting + gate decision                                               #
# ---------------------------------------------------------------------- #


def format_report(scores: dict[str, AppScore]) -> str:
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append("Gemini-vision deck-read accuracy eval (DECK-02)")
    lines.append(f"accuracy floor (per-app enable gate): {ACCURACY_FLOOR:.2f}")
    lines.append("=" * 64)
    lines.append(
        f"{'app':<12}{'samples':>8}{'title':>9}{'key':>8}{'overall':>9}  gate"
    )
    lines.append("-" * 64)

    total_correct = total_count = 0
    for app in sorted(scores):
        sc = scores[app]
        total_correct += sc.title_correct + sc.key_correct
        total_count += sc.title_total + sc.key_total
        gate = "ENABLE" if sc.passes_floor else "gated (XML-or-unknown)"
        lines.append(
            f"{sc.app:<12}{sc.samples:>8}{sc.title_accuracy:>9.2f}"
            f"{sc.key_accuracy:>8.2f}{sc.overall_accuracy:>9.2f}  {gate}"
        )
        for err in sc.errors:
            lines.append(f"    [error] {err}")

    overall = total_correct / total_count if total_count else 0.0
    lines.append("-" * 64)
    lines.append(f"{'OVERALL':<12}{'':>8}{'':>9}{'':>8}{overall:>9.2f}")
    lines.append("=" * 64)
    lines.append(
        "Decision: ENABLE vision-sourced keys ONLY for apps clearing the floor "
        "(at deck_vision.VISION_CONF, below the XML floor). Below-floor apps stay "
        "XML-or-unknown — vision dormant. Record the per-app outcome in "
        "59-05-SUMMARY.md."
    )
    return "\n".join(lines)


def _scores_to_dict(scores: dict[str, AppScore]) -> dict:
    return {
        "accuracy_floor": ACCURACY_FLOOR,
        "apps": {
            app: {
                "samples": sc.samples,
                "title_accuracy": round(sc.title_accuracy, 4),
                "key_accuracy": round(sc.key_accuracy, 4),
                "overall_accuracy": round(sc.overall_accuracy, 4),
                "passes_floor": sc.passes_floor,
                "errors": sc.errors,
            }
            for app, sc in scores.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gemini-vision deck-read accuracy eval (DECK-02)")
    parser.add_argument("corpus_dir", type=Path, help="dir of <app>_NNN.jpg + <app>_NNN.json labels")
    parser.add_argument("--json", type=Path, default=None, help="also write a machine-readable JSON report")
    args = parser.parse_args(argv)

    scores = run_eval(args.corpus_dir)
    report = format_report(scores)
    print(report)
    if args.json is not None:
        args.json.write_text(json.dumps(_scores_to_dict(scores), indent=2))
        print(f"\n[json] wrote {args.json}")

    # Exit code reflects whether ALL apps in the corpus cleared the floor. A
    # below-floor app is a "gated" outcome, not a crash — but a non-zero exit
    # surfaces it for CI / the KAAN-ACTION review.
    all_pass = all(sc.passes_floor for sc in scores.values()) if scores else False
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
