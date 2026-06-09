#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""bench_breakdown.py — per-event-type breakdown of a bench_gemini_judge verdict.

Reads the ``{verdict, rows}`` json a ``bench_gemini_judge`` run wrote and prints,
PER EVENT TYPE: count, dim means (friend/grounded/earned/move/voice), and the
fraction of lines the judge said should NOT have been spoken. This localizes the
narrator hole — which event types collapse friend (idle HEARTBEAT vs real moves).

    uv run --no-sync python scripts/eval/bench_breakdown.py <verdict.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIMS = [
    "friend_not_narrator",
    "grounded_not_fabricated",
    "earned_not_constant",
    "move_specific_not_spectrum",
    "voice_no_slop",
]


def _num(v):
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: bench_breakdown.py <verdict.json>", file=sys.stderr)
        return 2
    data = json.loads(Path(sys.argv[1]).read_text())
    rows = data.get("rows") or []
    by_event: dict[str, list[dict]] = {}
    for r in rows:
        sc = r.get("scores")
        if not isinstance(sc, dict) or _num(sc.get("friend_not_narrator")) is None:
            continue
        by_event.setdefault(r.get("event") or "?", []).append(sc)

    def means(scores_list):
        out = {}
        for d in DIMS:
            vals = [_num(s.get(d)) for s in scores_list]
            vals = [v for v in vals if v is not None]
            out[d] = round(sum(vals) / len(vals), 2) if vals else None
        sn = sum(1 for s in scores_list if s.get("should_speak") is False)
        out["n"] = len(scores_list)
        out["should_NOT_pct"] = round(100 * sn / len(scores_list), 0) if scores_list else None
        return out

    # Overall + per-event, sorted by friend ascending (worst first)
    rows_out = []
    allscores = [s for lst in by_event.values() for s in lst]
    rows_out.append(("ALL", means(allscores)))
    for ev, lst in sorted(by_event.items(), key=lambda kv: means(kv[1])["friend_not_narrator"] or 0):
        rows_out.append((ev, means(lst)))

    hdr = f"{'event':<22} {'n':>4} {'friend':>7} {'ground':>7} {'earned':>7} {'move':>6} {'voice':>7} {'shdNOT%':>8}"
    print(hdr)
    print("-" * len(hdr))
    for ev, m in rows_out:
        print(f"{ev:<22} {m['n']:>4} "
              f"{(m['friend_not_narrator'] or 0):>7.2f} "
              f"{(m['grounded_not_fabricated'] or 0):>7.2f} "
              f"{(m['earned_not_constant'] or 0):>7.2f} "
              f"{(m['move_specific_not_spectrum'] or 0):>6.2f} "
              f"{(m['voice_no_slop'] or 0):>7.2f} "
              f"{(m['should_NOT_pct'] if m['should_NOT_pct'] is not None else 0):>7.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
