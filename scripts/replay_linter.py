# SPDX-License-Identifier: Apache-2.0
"""replay_linter.py — Phase 20-03 offline citation-lint replay harness.

Replays a recorded session dir through CitationLinter offline — no Gemini
API call, no LiveKit, no PlaybackQueue. Pure in-memory pass that
reconstructs an EvidenceRegistry from ``events.jsonl`` and lints every
recorded ``response.txt`` per invocation, writing a per-response CSV to
``<session_dir>/linter_report.csv`` and printing a summary line.

Closes GROUND-05 + GROUND-06 (CONTEXT replay-validation gate). Phase 16
ear-test feeds this real Kaan sessions; the synthetic fixture under
``tests/scripts/fixtures/synthetic_session/`` pins the contract today.

## CLI

    .venv/bin/python scripts/replay_linter.py \\
        --session <PATH> \\
        [--mode live|debrief] \\
        [--out <CSV_PATH>] \\
        [--print-rate]

``--session`` is required and must contain ``events.jsonl`` + a
``responses/`` subdir. ``--mode`` defaults to ``live`` (±1.0s tolerance);
``debrief`` widens to ±2.0s per Phase 25 architectural slot. ``--out``
defaults to ``<session_dir>/linter_report.csv``. ``--print-rate`` adds a
single ``STRIPPED_RATE=<float:.4f>`` line to stdout for shell-pipe
consumption (used by Phase 16 audit scripts).

## CSV schema

    response_id,t_session,citations_found,valid,reason,missing_atoms

- ``response_id`` — invocation dir name (lex-sorted, ``NNNN_HHMMSS_<EVENT>``).
- ``t_session`` — float seconds since the FIRST response's HHMMSS prefix
  (first row is always ``0.0``).
- ``citations_found`` — int count of parsed citation atoms in the response.
- ``valid`` — ``True``/``False`` from the binary linter decision.
- ``reason`` — one of ``valid`` / ``no_citations`` / ``invalid_atoms`` /
  ``malformed_atom`` (matches ``LintResult.reason``).
- ``missing_atoms`` — semicolon-joined ``source:body`` pairs for misses
  (empty string for valid responses).

## Replay invariant

The CitationLinter class used by replay is the SAME instance type used by
the live agent — same constants, same code path. Replay results are byte-
for-byte the live decision; the threshold gate (``stripped_rate < 0.15``)
holds across both surfaces.

## Threat surface (T-20-03-01..04 — see PLAN frontmatter)

Replay reads ``events.jsonl`` linearly (no whole-file load) so a 50MB
recorded session is well within budget. The CSV output stays inside the
session dir (no traversal risk) and contains only the missing-atoms
projection — raw response text stays in ``response.txt``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Allow direct invocation from repo root without an editable install — the
# repo is pre-package per CLAUDE.md, so prepend ``src/`` to sys.path.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vibemix.coach import CitationLinter  # noqa: E402
from vibemix.state.evidence_registry import EvidenceRegistry  # noqa: E402


def _hhmmss_to_seconds(hhmmss: str) -> int:
    """Parse a 6-digit ``HHMMSS`` string into total seconds since midnight.

    The dir-name format is ``NNNN_HHMMSS_<EVENT>`` per
    ``DJCoHostAgent.llm_node`` (line ~270). Replay subtracts the first
    response's value to produce a session-relative ``t_session``.
    """
    if len(hhmmss) != 6 or not hhmmss.isdigit():
        raise ValueError(
            f"expected 6-digit HHMMSS, got {hhmmss!r}"
        )
    h = int(hhmmss[0:2])
    m = int(hhmmss[2:4])
    s = int(hhmmss[4:6])
    return h * 3600 + m * 60 + s


def _load_registry(events_path: Path) -> EvidenceRegistry:
    """Replay ``events.jsonl`` observation rows into a fresh registry.

    Only rows with ``kind == "evidence_observation"`` are written. Other
    rows (``ai_text``, ``turn_error``, etc.) are silently skipped — replay
    cares only about the observation corpus.

    Reads the file linearly (T-20-03-03 mitigation) — does NOT load the
    whole file into memory.
    """
    registry = EvidenceRegistry()
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("kind") != "evidence_observation":
                continue
            registry.write(
                row["source"],
                row["key"],
                float(row["t_session"]),
            )
    return registry


def _list_response_dirs(responses_root: Path) -> list[Path]:
    """Return invocation dirs sorted lexicographically.

    The ``NNNN_HHMMSS_<EVENT>`` prefix means lex sort == invocation order.
    """
    return sorted(
        (p for p in responses_root.iterdir() if p.is_dir()),
        key=lambda p: p.name,
    )


def _read_response_text(invoke_dir: Path) -> str:
    """Read ``response.txt`` from the invocation dir.

    Missing file → empty string (will lint as ``no_citations`` and count
    toward the stripped_rate). Never crashes the replay.
    """
    response_path = invoke_dir / "response.txt"
    try:
        return response_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="replay_linter",
        description=(
            "Replay a recorded session through CitationLinter offline. "
            "Produces a per-response CSV report and prints a summary."
        ),
    )
    parser.add_argument(
        "--session",
        type=Path,
        required=True,
        help="Path to a session dir (must contain events.jsonl + responses/).",
    )
    parser.add_argument(
        "--mode",
        choices=("live", "debrief"),
        default="live",
        help="Linter tolerance band — live=±1.0s, debrief=±2.0s. Default: live.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="CSV output path. Default: <session_dir>/linter_report.csv.",
    )
    parser.add_argument(
        "--print-rate",
        action="store_true",
        help=(
            "Print an additional STRIPPED_RATE=<float:.4f> line to stdout "
            "for shell-pipe consumption (Phase 16 audit scripts)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)

    session_dir: Path = args.session
    if not session_dir.exists():
        raise FileNotFoundError(f"--session path does not exist: {session_dir}")
    events_path = session_dir / "events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(f"missing events.jsonl in session dir: {events_path}")
    responses_root = session_dir / "responses"
    if not responses_root.exists():
        raise FileNotFoundError(
            f"missing responses/ subdir in session dir: {responses_root}"
        )

    out_path: Path = args.out if args.out is not None else session_dir / "linter_report.csv"

    # Step 1: registry replay.
    registry = _load_registry(events_path)

    # Step 2: list response dirs lex-sorted.
    invoke_dirs = _list_response_dirs(responses_root)

    # Step 3+4: lint each response, accumulate rows.
    linter = CitationLinter()
    rows: list[tuple[str, float, int, bool, str, str]] = []
    baseline_seconds: int | None = None
    stripped_count = 0

    for invoke_dir in invoke_dirs:
        # Per-response snapshot — the API contract is per-call even though
        # the corpus is frozen by the pre-load.
        snapshot = registry.snapshot()
        text = _read_response_text(invoke_dir)
        result = linter.check(text, snapshot, mode=args.mode)

        # Parse t_session from the dir name's HHMMSS column.
        parts = invoke_dir.name.split("_")
        # parts: ["0001", "120000", "KAAN", "SPOKE"] — HHMMSS is parts[1].
        hhmmss_seconds = _hhmmss_to_seconds(parts[1])
        if baseline_seconds is None:
            baseline_seconds = hhmmss_seconds
        t_session = float(hhmmss_seconds - baseline_seconds)

        missing_atoms = ";".join(f"{src}:{body}" for (src, body) in result.missing)
        rows.append(
            (
                invoke_dir.name,
                t_session,
                result.citations_found,
                result.valid,
                result.reason,
                missing_atoms,
            )
        )
        if not result.valid:
            stripped_count += 1

    # Step 5: write CSV.
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            (
                "response_id",
                "t_session",
                "citations_found",
                "valid",
                "reason",
                "missing_atoms",
            )
        )
        writer.writerows(rows)

    # Step 6: summary line + optional STRIPPED_RATE line.
    total = len(rows)
    rate = (stripped_count / total) if total else 0.0
    print(
        f"total={total} stripped={stripped_count} "
        f"stripped_rate={rate:.3f} mode={args.mode} out={out_path}"
    )
    if args.print_rate:
        print(f"STRIPPED_RATE={rate:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
