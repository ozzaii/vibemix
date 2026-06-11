# SPDX-License-Identifier: Apache-2.0
"""Pool bench judge runs into the campaign bar table.

The cadence campaign's measurement-statistics finding (2026-06-11,
CADENCE-LEVER-CONTRACT.md): per-run should_NOT% at n=2-6 spoken lines judges
generation noise — one bad render in a 3-line run reads as 33%, and
same-build sibling runs measured 0%↔100%. Verdicts must pool n>=10 lines.
This tool is that discipline made durable: it walks ``judge.json`` files,
prints per-line OK/NOT with the judge's why, and pools the six bars per
lane so nobody re-derives the table in /tmp each session.

Usage:
    python scripts/eval/judge_pool.py <run_dir_or_glob> [...]
    python scripts/eval/judge_pool.py ".planning/eval-runs/lever3-cadence-*"
    python scripts/eval/judge_pool.py --quiet ...   # pooled table only
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sys

# (score key, display name, pass bar) — the campaign contract bars.
DIMS: list[tuple[str, str, float]] = [
    ("friend_not_narrator", "friend", 2.0),
    ("grounded_not_fabricated", "grounded", 2.4),
    ("earned_not_constant", "earned", 2.0),
    ("move_specific_not_spectrum", "move", 2.0),
    ("voice_no_slop", "no_slop", 2.0),
]
SHOULD_NOT_BAR_PCT = 20.0
POOL_FLOOR = 10  # below this pooled n, the table is noise — say so.


def load_rows(run_dir: pathlib.Path) -> list[dict] | None:
    jp = run_dir / "judge.json"
    if not jp.exists():
        return None
    try:
        return json.loads(jp.read_text()).get("rows", [])
    except (OSError, json.JSONDecodeError):
        return None


def lane_of(name: str) -> str:
    return "midi" if "midi" in name else "audio"


def walk_run(run_dir: pathlib.Path, *, quiet: bool) -> tuple[dict, int, int] | None:
    rows = load_rows(run_dir)
    if rows is None:
        print(f"== {run_dir.name}: no judge.json")
        return None
    judged = [r for r in rows if r.get("status") == 200 and r.get("scores")]
    skipped = len(rows) - len(judged)
    if not quiet:
        print(f"\n== {run_dir.name} ({len(judged)} judged" +
              (f", {skipped} unscored" if skipped else "") + ")")
    stats: dict[str, list[float]] = {k: [] for k, _, _ in DIMS}
    nots = 0
    for r in judged:
        s = r["scores"]
        ok = s.get("should_speak", True)
        if not ok:
            nots += 1
        if not quiet:
            print(f"[{'OK ' if ok else 'NOT'}] {r.get('event', '?'):<12} "
                  f"F{s.get('friend_not_narrator')}/G{s.get('grounded_not_fabricated')}")
            print(f"      {(r.get('line') or '')[:150]}")
            print(f"      why: {(s.get('why') or '')[:140]}")
        for k, _, _ in DIMS:
            v = s.get(k)
            if isinstance(v, (int, float)):
                stats[k].append(float(v))
    return stats, nots, len(judged)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("targets", nargs="+", help="run dirs or globs containing judge.json")
    ap.add_argument("--quiet", action="store_true", help="pooled table only, no line walk")
    args = ap.parse_args(argv)

    dirs: list[pathlib.Path] = []
    for t in args.targets:
        hits = sorted(glob.glob(t)) or [t]
        dirs.extend(pathlib.Path(h) for h in hits)
    dirs = [d for d in dirs if d.is_dir()]
    if not dirs:
        print("no run dirs matched", file=sys.stderr)
        return 2

    lanes: dict[str, dict] = {}
    for d in dirs:
        res = walk_run(d, quiet=args.quiet)
        if res is None:
            continue
        stats, nots, n = res
        lane = lanes.setdefault(
            lane_of(d.name),
            {"stats": {k: [] for k, _, _ in DIMS}, "runs": [], "nots": 0, "n": 0},
        )
        for k in stats:
            lane["stats"][k].extend(stats[k])
        lane["runs"].append((d.name, nots, n))
        lane["nots"] += nots
        lane["n"] += n

    for name, lane in lanes.items():
        n = lane["n"]
        print(f"\n#### POOLED {name} (n={n})" +
              ("  ⚠ n<%d: NOISE, do not verdict" % POOL_FLOOR if n < POOL_FLOOR else ""))
        for k, disp, bar in DIMS:
            vals = lane["stats"][k]
            if not vals:
                continue
            m = sum(vals) / len(vals)
            print(f"  {disp:<8} {m:.2f} {'✓' if m >= bar else '✗'} (bar {bar})")
        pooled_pct = 100.0 * lane["nots"] / n if n else 0.0
        print(f"  should_NOT pooled: {lane['nots']}/{n} = {pooled_pct:.1f}% "
              f"{'✓' if pooled_pct <= SHOULD_NOT_BAR_PCT else '✗'} (bar ≤{SHOULD_NOT_BAR_PCT:.0f}%)")
        for rn, nots, rn_n in lane["runs"]:
            pct = 100.0 * nots / rn_n if rn_n else 0.0
            print(f"    per-run {rn}: {nots}/{rn_n} = {pct:.0f}%  (per-run is noise at n<{POOL_FLOOR})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
