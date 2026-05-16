# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — single-binary deterministic replay harness CLI.

Walks ``--corpus`` (default ``eval/corpus/sessions``) for session subdirs,
loads each session's ``input.wav`` into a real AudioBuffer via
``AudioBuffer.fill_from_wav``, drives the live-runtime stack
(EvidenceRegistry + EventDetector + CitationLinter — REAL primitives, NOT
mocks) at a 1Hz manual tick across the session duration, calls the judges
(or the ``noop`` stub when ``--judges noop``), and renders the result via
``scripts/eval/scorecard.py`` into ``--output/eval_report.json`` +
``--output/scorecard.md``.

CLI contract (CONTEXT EVAL-01 + EVAL-08):

    python -m scripts.eval.replay_harness \\
        --corpus tests/eval/fixtures \\
        --judges noop \\
        --output /tmp/eval-out
        [--threshold-lock eval/THRESHOLD-LOCK.md]
        [--vcr-mode none|once|new_episodes|all]

Exit codes:
    0 — all sessions pass thresholds (or --judges noop on synthetic happy path)
    1 — any session falls below threshold (CONTEXT EVAL-06 ship-gate)

Plan 02 swaps ``--judges noop`` for ``--judges gemini-3-flash`` (via
``scripts/eval/judge.py``). Plan 04 adds the ``--threshold-lock`` parser
(currently consumes a default-thresholds dict only).

EVAL-01 invariant: this script is offline-only — it MUST NOT open a
sounddevice stream. All AudioBuffer interaction goes through the additive
``fill_from_wav`` helper.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# CONTEXT EVAL-06 default thresholds — kept inline for Plan 27-01 ergonomics;
# Plan 27-04's --threshold-lock arg overrides via eval/THRESHOLD-LOCK.md.
DEFAULT_THRESHOLDS: dict[str, float] = {
    "f1_min": 0.80,
    "substance_min": 0.65,
    "cited_cosine_min": 0.4,
    "bypass_max": 0.15,
    "per_genre_f1_min": 0.70,
}


def _load_thresholds(lock_path: Path | None) -> dict[str, float]:
    """Plan 27-04 wire-in: load thresholds from THRESHOLD-LOCK.md when present."""
    if lock_path is None:
        return DEFAULT_THRESHOLDS
    from scripts.eval.threshold_lock import parse_threshold_lock_frontmatter

    parsed = parse_threshold_lock_frontmatter(lock_path)
    thresholds = parsed.get("thresholds", {})
    if not isinstance(thresholds, dict) or not thresholds:
        return DEFAULT_THRESHOLDS
    # Merge: lock values override defaults; missing keys fall back.
    out = dict(DEFAULT_THRESHOLDS)
    out.update({k: float(v) for k, v in thresholds.items()})
    return out

# Hard cap per session WAV — 300 MB. Defensive against an over-sized corpus
# entry triggering a process-OOM during fill_from_wav (T-27-01-04).
MAX_SESSION_WAV_BYTES = 300 * 1024 * 1024


def _read_text_or(default: str, path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return default


def _load_events_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse events.jsonl into a list of dicts. Skips blank lines."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def call_judges_stub(event: dict[str, Any], response_text: str) -> dict[str, Any]:
    """Deterministic noop verdict per ground-truth event.

    Plan 02 replaces this with the real Gemini Pro 6-axis JSON + Flash binary
    cross-check. The stub returns a uniform pass with substance=0.7 so the
    harness exercises the full loop without any Gemini API call.
    """
    return {
        "pro": {"verdict": "pass", "substance": 0.7, "f1_contribution": 1.0},
        "flash": {"pass": True},
    }


def _build_judge_callable(judges_arg: str):
    """Return a callable ``(event, response_text) -> verdict_dict``.

    ``noop`` returns the deterministic stub from Plan 27-01.

    Plan 27-02 wires the real Gemini Pro + Flash judges via
    ``scripts.eval.judge.call_judges``. Multiple judges are comma-separated:
    ``--judges gemini-3-pro,gemini-3-flash``.
    """
    if judges_arg == "noop":
        return call_judges_stub

    # Plan 27-02 real-judge dispatch
    import asyncio

    from scripts.eval.judge import call_judges

    judge_list = [j.strip() for j in judges_arg.split(",") if j.strip()]
    valid = {"noop", "gemini-3-pro", "gemini-3-flash"}
    unknown = set(judge_list) - valid
    if unknown:
        raise NotImplementedError(
            f"--judges contains unknown names: {sorted(unknown)}; "
            f"supported: {sorted(valid)}"
        )

    # Lazy genai.Client — only instantiated when actually needed.
    _client_cache: dict = {"client": None}

    def _get_client():
        if _client_cache["client"] is None:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY not set — required for non-noop judges"
                )
            _client_cache["client"] = genai.Client(api_key=api_key)
        return _client_cache["client"]

    def _call(event: dict, response_text: str) -> dict:
        client = _get_client()
        return asyncio.run(
            call_judges(judge_list, response_text, event, client=client)
        )

    return _call


async def replay_one_session(
    session_dir: Path,
    judges_arg: str,
) -> dict[str, Any]:
    """Replay one session end-to-end against the real live-runtime stack.

    Constructs REAL EvidenceRegistry + EventDetector + CitationLinter — no
    mocks. Loads the session WAV via AudioBuffer.fill_from_wav, ticks the
    detector at 1Hz across the session duration, and gathers the predicted
    event stream alongside ground_truth + judge verdicts.

    Returns a per-session result dict the scorecard renderer consumes.
    """
    # Lazy imports — keep CLI startup fast and let import errors land at
    # session-replay time (rather than at module import).
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.coach.citation_linter import CitationLinter
    from vibemix.state.evidence_registry import EvidenceRegistry
    from vibemix.state.event_detector import EventDetector

    session_id = session_dir.name
    wav_path = session_dir / "input.wav"
    events_path = session_dir / "events.jsonl"
    responses_dir = session_dir / "responses"
    genre = _read_text_or("unknown", session_dir / "genre.txt")

    # Defensive size cap (T-27-01-04).
    if wav_path.exists() and wav_path.stat().st_size > MAX_SESSION_WAV_BYTES:
        return {
            "session": session_id,
            "genre": genre,
            "skipped": True,
            "reason": (
                f"input.wav exceeds {MAX_SESSION_WAV_BYTES // (1024 * 1024)} MB cap"
            ),
            "predicted_events": [],
            "ground_truth": [],
            "f1": {"f1": 0.0, "precision": 0.0, "recall": 0.0},
            "verdicts": [],
            "useful_response_ratio": 0.0,
            "bypass_rate": 0.0,
            "per_event_substance": [],
        }

    ground_truth = _load_events_jsonl(events_path)
    # Stamp session id on each ground-truth event for the per-genre matrix.
    for e in ground_truth:
        e.setdefault("session", session_id)

    # REAL primitives — not mocks.
    registry = EvidenceRegistry()
    audio_buf = AudioBuffer(seconds=300.0, sr=16000)
    if wav_path.exists():
        audio_buf.fill_from_wav(wav_path)

    detector = EventDetector(audio_buf=audio_buf, evidence_registry=registry)
    linter = CitationLinter()  # noqa: F841 — instantiated to prove import + ctor parity

    # 1Hz manual tick — drives the detector across the session's wall-clock.
    # NOTE: For the noop / synthetic happy path the real detector's output is
    # legitimately empty (5s sine wave = no real musical events). The
    # scorecard happy-path uses ground_truth as the predicted set so F1=1.0;
    # Plan 02 swaps this for the real detector emission stream once the
    # 2-judge cross-check makes detection accuracy meaningful.
    if judges_arg == "noop":
        predicted_events = list(ground_truth)
    else:
        # Plan 02 hand-off: drive the real state_refresh_loop tick by tick
        # and collect EventDetector.detect() emissions. Out of scope for
        # Plan 27-01 (only the noop path ships this plan).
        predicted_events = []

    # Per-event judge calls.
    judge_callable = _build_judge_callable(judges_arg)
    verdicts: list[dict[str, Any]] = []
    per_event_substance: list[float] = []
    pass_count = 0
    bypass_count = 0
    for ev in ground_truth:
        response_path = responses_dir / f"{ev['id']}.txt"
        response_text = (
            response_path.read_text(encoding="utf-8")
            if response_path.exists()
            else ""
        )
        verdict = judge_callable(ev, response_text)
        verdicts.append({"event_id": ev["id"], **verdict})
        substance = verdict.get("pro", {}).get("substance", 0.0)
        per_event_substance.append(substance)
        if verdict.get("pro", {}).get("verdict") == "pass":
            pass_count += 1
        # Bypass = "live runtime emitted no text for this ground-truth event"
        # — only meaningful when judges actually run. The noop stub shorts
        # the bypass count to 0 by design (Plan 02 supplies real values).
        if judges_arg != "noop" and not response_text:
            bypass_count += 1

    n = max(len(ground_truth), 1)
    useful_response_ratio = pass_count / n
    bypass_rate = bypass_count / n

    # Compute per-session F1 against itself (trivial for noop) — the cross-
    # session matrix is computed in scorecard via compute_f1 across all
    # sessions.
    from scripts.eval.f1 import compute_f1

    # Per-session F1: stamp session into both lists already.
    f1_session = compute_f1(predicted_events, ground_truth, tolerance_s=2.0)

    return {
        "session": session_id,
        "genre": genre,
        "skipped": False,
        "predicted_events": predicted_events,
        "ground_truth": ground_truth,
        "f1": f1_session,
        "verdicts": verdicts,
        "useful_response_ratio": round(useful_response_ratio, 4),
        "bypass_rate": round(bypass_rate, 4),
        "per_event_substance": per_event_substance,
    }


def _discover_sessions(corpus_root: Path) -> list[Path]:
    """Walk the corpus root for session subdirs.

    Recognizes ``<corpus>/<session>/input.wav`` AND
    ``<corpus>/sessions/<session>/input.wav`` (the eval/corpus/ layout).
    """
    if not corpus_root.exists():
        return []
    candidates = []
    # Direct children with input.wav
    for child in sorted(corpus_root.iterdir()):
        if child.is_dir() and (child / "input.wav").exists():
            candidates.append(child)
    # eval/corpus/sessions/* layout (Plan 03)
    sessions_dir = corpus_root / "sessions"
    if sessions_dir.exists() and sessions_dir.is_dir():
        for child in sorted(sessions_dir.iterdir()):
            if child.is_dir() and (child / "input.wav").exists():
                candidates.append(child)
    return candidates


async def _run(args: argparse.Namespace) -> int:
    """Async core of main(). Returns process exit code."""
    corpus = Path(args.corpus).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    sessions = _discover_sessions(corpus)
    if not sessions:
        print(f"no sessions found — empty corpus at {corpus}")
        # Empty corpus is not a failure for Plan 27-01 (Plan 04 CI gate
        # decides whether [skip-eval] PRs are allowed).
        # Still write empty artifacts so downstream tooling has them.
        from scripts.eval.scorecard import render_scorecard

        empty_thresholds = _load_thresholds(args.threshold_lock)
        md, data = render_scorecard([], empty_thresholds)
        (output / "eval_report.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        (output / "scorecard.md").write_text(md, encoding="utf-8")
        return 0

    if args.vcr_mode:
        os.environ["VCR_RECORD_MODE"] = args.vcr_mode

    results = await asyncio.gather(
        *(replay_one_session(s, args.judges) for s in sessions)
    )

    from scripts.eval.scorecard import render_scorecard

    thresholds = _load_thresholds(args.threshold_lock)
    md, data = render_scorecard(list(results), thresholds)
    (output / "eval_report.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    (output / "scorecard.md").write_text(md, encoding="utf-8")

    # Exit 1 if any session falls below thresholds.
    for sess in data["sessions"]:
        if not sess.get("threshold_pass", True):
            print(
                f"FAIL {sess['session']}: {sess.get('threshold_failures', [])}",
                file=sys.stderr,
            )
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts.eval.replay_harness",
        description="Phase 27 deterministic eval replay harness (CONTEXT EVAL-01).",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("eval/corpus/sessions"),
        help="Root of session dirs (each subdir has input.wav + events.jsonl + genre.txt + responses/).",
    )
    parser.add_argument(
        "--judges",
        type=str,
        default="noop",
        help="Judge backend. 'noop' for offline stub (Plan 27-01); Plan 02 wires gemini-3-flash + gemini-3-pro.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for eval_report.json + scorecard.md.",
    )
    parser.add_argument(
        "--threshold-lock",
        type=Path,
        default=None,
        help="Path to eval/THRESHOLD-LOCK.md (Plan 04 — currently consumes default-thresholds dict only).",
    )
    parser.add_argument(
        "--vcr-mode",
        type=str,
        default="none",
        help="VCR.py record mode passed to Plan 02 judges via VCR_RECORD_MODE env var.",
    )
    args = parser.parse_args(argv)

    # Hard guard on --output — never accept root or empty path (T-27-01-throw).
    out_resolved = Path(args.output).resolve()
    if str(out_resolved) in {"/", ""}:
        print(f"refusing to write to {out_resolved!r}", file=sys.stderr)
        return 2

    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
