"""check_60s_gate.py — install rehearsal timing gate.

Computes median + p95 of install_ms across the install_vm_matrix rows.
Returns JSON + exits 0 (pass) / 1 (fail) based on whether median ≤ budget.

CLI:
    python -m scripts.dist.check_60s_gate <run.json> [--budget 600000]

run.json shape (produced by install_vm_matrix.sh --simulate or --real):
    {
      "rows": [
        {"name": "macos-12.3", "install_ms": 420000, ...},
        ...
      ]
    }

OR (legacy / simulated_runs from install_vm_matrix.json):
    {
      "simulated_runs": {
        "macos-12.3": {"install_ms": 420000, ...},
        ...
      }
    }

Output (stdout single-line JSON):
    {
      "median_ms": 390000,
      "p95_ms": 450000,
      "budget_ms": 600000,
      "pass": true,
      "rows": [...],
      "slowest_row": "windows-10",
      "fastest_row": "macos-15"
    }
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def _normalize_rows(payload: dict) -> list[dict]:
    """Accept several payload shapes.

    Shape A — concrete run output (from install_vm_matrix.sh --real or
    --simulate): top-level `rows` array with install_ms per row.

    Shape B — matrix declaration (install_vm_matrix.json itself): top-level
    `rows` is the OS row inventory WITHOUT timing, and `simulated_runs` is
    a parallel dict with per-row stub timings. We join them by row name.
    """
    # First, prefer rows[].install_ms / onboarding_ms when present.
    if "rows" in payload and isinstance(payload["rows"], list):
        rows_with_ms = []
        for r in payload["rows"]:
            ms = r.get("install_ms", r.get("onboarding_ms"))
            if ms is None:
                continue
            rows_with_ms.append(
                {
                    **r,
                    "name": r.get("name") or f"{r.get('os')}-{r.get('version')}",
                    "install_ms": ms,
                    "onboarding_ms": ms,
                }
            )
        if rows_with_ms:
            return rows_with_ms
    # Second, fall back to simulated_runs dict (matrix-declaration shape).
    if "simulated_runs" in payload and isinstance(payload["simulated_runs"], dict):
        out = []
        for name, row in payload["simulated_runs"].items():
            if not isinstance(row, dict) or name == "_doc":
                continue
            ms = row.get("install_ms", row.get("onboarding_ms"))
            if ms is None:
                continue
            out.append({**row, "name": name, "install_ms": ms, "onboarding_ms": ms})
        return out
    return []


def _p95(values: list[float]) -> float:
    """Nearest-rank p95 (works for n=5 deterministically)."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    # Nearest-rank: ceil(0.95 * n) - 1 index (0-indexed)
    import math
    idx = max(0, min(len(sorted_v) - 1, math.ceil(0.95 * len(sorted_v)) - 1))
    return float(sorted_v[idx])


def check_gate(rows: list[dict], budget_ms: int = 600000) -> dict:
    """Compute median + p95 + pass/fail across rows."""
    if not rows:
        return {
            "median_ms": 0,
            "p95_ms": 0,
            "budget_ms": budget_ms,
            "pass": False,
            "rows": [],
            "reason": "no_rows",
        }
    ms_values = [r.get("install_ms", r.get("onboarding_ms")) for r in rows]
    median = statistics.median(ms_values)
    p95 = _p95(ms_values)
    slowest = max(rows, key=lambda r: r.get("install_ms", r.get("onboarding_ms")))
    fastest = min(rows, key=lambda r: r.get("install_ms", r.get("onboarding_ms")))
    return {
        "median_ms": int(median),
        "p95_ms": int(p95),
        "budget_ms": budget_ms,
        "pass": median <= budget_ms,
        "rows": rows,
        "slowest_row": slowest.get("name"),
        "fastest_row": fastest.get("name"),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_json", type=Path, help="Path to run output JSON")
    p.add_argument("--budget", type=int, default=None, help="Budget ms (default 600000)")
    args = p.parse_args(argv)

    if not args.run_json.exists():
        print(json.dumps({"error": f"file_not_found: {args.run_json}"}), file=sys.stderr)
        return 2
    payload = json.loads(args.run_json.read_text())
    rows = _normalize_rows(payload)
    # Use the file's own budget if it declares one + no --budget override.
    budget = (
        args.budget
        if args.budget is not None
        else int(payload.get("install_ms_budget", payload.get("onboarding_ms_budget", 600000)))
    )
    result = check_gate(rows, budget)
    print(json.dumps(result))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
