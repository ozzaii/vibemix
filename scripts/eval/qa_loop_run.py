#!/usr/bin/env python3
"""qa_loop_run.py — the autonomous QA loop's closing seam (GATE-0 / 0c).

Fans out the EXISTING judges over a captured session and merges them into ONE
machine-readable verdict (`vibemix_qa_verdict_v1`) that a Codex lane reads to know
whether to commit + what to do next. NO new judge logic — this is glue.

What it wires (all pre-existing, file:line in qa-loop-map/MAP-judge.md):
  - respan_sven_heartbeat_judge.py  → 5-dim Sven prose + should_speak, exit-code gate
  - (--dry-run --describe-bank-census) → keyless deterministic gate FLOOR (no network)
  - replay_harness.py (optional)     → offline citation-F1 grounding gate

Design rules (from REDTEAM-closeloop.md, the false-pass guards):
  - Propagate EVERY exit code; never swallow a 401 as "0 failures".
  - Enforce a --min-judged floor; zero lines judged is a hard FAIL, not a vacuous pass.
  - Keyless deterministic floor always runs (the no-network truth when the key is dead).
  - The verdict's next_goal routes the lowest-passing dim to a lane with worst-evidence
    rows + a copy-paste `verify` command, so "done" means "by-ear gate reproduced".

Usage:
  # judge an already-captured session (fast path; what works tonight):
  python scripts/eval/qa_loop_run.py --session "<recordings dir>" --out <verdict.json>
  # keyless floor only (no network, no key):
  python scripts/eval/qa_loop_run.py --session "<dir>" --no-network --out <verdict.json>

Exit code: 0 iff overall_pass, else 1. (So a lane's self-QA can branch on it.)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HEARTBEAT = REPO / "scripts" / "eval" / "respan_sven_heartbeat_judge.py"

# dim -> lane routing (Kaan's lanes + sven). Lowest-passing dim picks the lane.
DIM_LANE = {
    "friend_not_narrator": "sven",
    "earned_not_constant": "sven",
    "move_specific_not_spectrum": "sven",
    "voice_no_slop": "sven",
    "grounded_not_fabricated": "sven",
    "citation_f1": "engine",
}
# the heartbeat --require-quality thresholds (mirrored so the verdict is self-describing)
THRESHOLDS = {
    "friend_not_narrator": 2.0,
    "earned_not_constant": 2.0,
    "voice_no_slop": 2.0,
    "move_specific_not_spectrum": 2.0,
    "grounded_not_fabricated": 2.4,
}
WHERE_HINT = {
    "friend_not_narrator": "src/vibemix/runtime/coach.py + src/vibemix/prompts/matrix.py",
    "earned_not_constant": "src/vibemix/runtime/speak_gate.py",
    "voice_no_slop": "src/vibemix/prompts/matrix.py + src/vibemix/prompts/negative_dict.py",
    "move_specific_not_spectrum": "src/vibemix/runtime/transition_verdict_voice.py + runtime/coach.py:880-901",
    "grounded_not_fabricated": "src/vibemix/state/evidence_registry.py + state/deck_context.py",
}


def _load_dotenv() -> None:
    """Load .env into os.environ so the heartbeat judge sees RESPAN_API_KEY.

    The judge reads the key from the process env ONLY (it does not load .env itself).
    Never print the value.
    """
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _run_heartbeat(session: str, out: Path, min_judged: int, network: bool) -> dict:
    """Run the heartbeat judge, return its parsed report. Propagate, never swallow."""
    cmd = [
        sys.executable, str(HEARTBEAT),
        "--session", session,
        "--events", "ALL",
        "--min-judged", str(min_judged),
        "--no-log",
        "--out", str(out),
    ]
    if not network:
        cmd += ["--dry-run", "--describe-bank-census"]
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    report: dict = {}
    if out.exists():
        try:
            report = json.load(open(out)).get("report", {})
        except Exception as e:  # noqa: BLE001
            report = {"_parse_error": str(e)}
    report["_exit_code"] = proc.returncode
    if proc.returncode != 0 and not report:
        # No report written AND non-zero exit = real failure (e.g. key 401, no rows).
        report["_stderr_tail"] = proc.stderr.strip().splitlines()[-5:]
    return report


def _quality_pass(dim_means: dict, should_not: int, judged: int, min_judged: int, errors: int) -> bool:
    """Authoritative quality gate, computed HERE — not trusted from a subprocess exit code.

    (The heartbeat judge without --require-quality exits 0 on "judged successfully", which is
    NOT "quality passed". Conflating them is the red-team's false-pass #4. Compute it.)
    """
    if judged < min_judged or errors > 0:
        return False
    if should_not > 0:  # any line that should have been silence = fail (Kaan's rare+earned bar)
        return False
    for dim, threshold in THRESHOLDS.items():
        if dim_means.get(dim, 0.0) < threshold:
            return False
    return True


def _build_next_goal(dim_means: dict, worst_lines: list, should_not_speak: int) -> dict:
    """Lowest-passing dim -> routed lane goal with worst evidence + verify command."""
    # rank dims by how far below threshold they are
    ranked = sorted(
        ((d, dim_means.get(d, 0.0), THRESHOLDS[d]) for d in THRESHOLDS),
        key=lambda x: (x[1] - x[2]),
    )
    worst_dim, measured, target = ranked[0]
    return {
        "lane": DIM_LANE.get(worst_dim, "sven"),
        "priority": "blocker" if measured < target - 0.5 else "improve",
        "title": f"Raise {worst_dim} from {measured} to >= {target}"
        + (f"; cut the {should_not_speak} should-NOT-have-spoken lines" if should_not_speak else ""),
        "evidence": {
            "failing_dim": worst_dim,
            "measured": measured,
            "target": target,
            "should_NOT_have_spoken": should_not_speak,
            "worst_lines": worst_lines[:6],
        },
        "where": WHERE_HINT.get(worst_dim, ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session", required=True, help="captured recordings session dir")
    ap.add_argument("--out", required=True, help="path to write the merged verdict json")
    ap.add_argument("--min-judged", type=int, default=20)
    ap.add_argument("--no-network", action="store_true", help="keyless deterministic floor only")
    args = ap.parse_args()

    session = os.path.expanduser(args.session)
    if not Path(session, "invocations").is_dir():
        print(f"FAIL: no invocations/ under {session}", file=sys.stderr)
        return 1

    out_dir = Path(args.out).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.no_network:
        _load_dotenv()
        if not os.environ.get("RESPAN_API_KEY"):
            print("WARN: RESPAN_API_KEY absent; falling back to keyless floor", file=sys.stderr)
            args.no_network = True

    hb_out = out_dir / "heartbeat-report.json"
    hb = _run_heartbeat(session, hb_out, args.min_judged, network=not args.no_network)

    judged = hb.get("judged") or 0
    errors = hb.get("errors") or 0
    dim_means = hb.get("dim_means") or {}
    should_not = hb.get("should_NOT_have_spoken") or 0
    worst = hb.get("worst_lines") or []

    # Gate computed HERE from dim_means vs thresholds (NOT the subprocess exit code, which
    # only means "judged successfully" — trusting it is the red-team false-pass #4).
    sven_pass = (not args.no_network) and _quality_pass(
        dim_means, should_not, judged, args.min_judged, errors
    )

    verdict = {
        "schema": "vibemix_qa_verdict_v1",
        "session_dir": session,
        "mode": "keyless_floor" if args.no_network else "keyed",
        "overall_pass": bool(sven_pass),
        "gates": {
            "sven_prose": {
                "pass": bool(sven_pass),
                "judged": judged,
                "errors": errors,
                "min_judged": args.min_judged,
                "dim_means": dim_means,
                "should_NOT_have_spoken": should_not,
                "heartbeat_exit": hb.get("_exit_code"),
            },
        },
        "next_goal": _build_next_goal(dim_means, worst, should_not) if dim_means else None,
        "verify": (
            f'set -a; . ./.env; set +a; uv run python scripts/eval/respan_sven_heartbeat_judge.py '
            f'--session "{session}" --events ALL --require-quality --min-judged {args.min_judged}'
        ),
    }
    if hb.get("_stderr_tail"):
        verdict["gates"]["sven_prose"]["stderr_tail"] = hb["_stderr_tail"]

    Path(args.out).write_text(json.dumps(verdict, indent=2))
    print(json.dumps({
        "overall_pass": verdict["overall_pass"],
        "mode": verdict["mode"],
        "judged": judged,
        "dim_means": dim_means,
        "should_NOT_have_spoken": should_not,
        "next_goal_lane": (verdict["next_goal"] or {}).get("lane"),
        "out": str(args.out),
    }, indent=2))
    return 0 if verdict["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
