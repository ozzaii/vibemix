#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""bench_gemini_judge.py — the "bench until perfection" judge on GEMINI-DIRECT transport.

The product judge (``respan_sven_heartbeat_judge.py``) is the canonical 5-dim
blind judge, but its transport is hard-pinned to the Respan gateway
(``api.respan.ai``), whose configured model id (``gemini/...:nitro``) currently
404s — so the whole friend/grounded bench is dark. This driver reuses that
judge's rubric + row-loader + scoring VERBATIM (imported, never re-implemented —
the rubric IS the instrument) and only swaps the dead transport for the live
google-genai SDK (Gemini direct, the path proven working today).

It judges Sven's ACTUAL spoken lines from a recorded session on the 5 product
dims + the ``should_speak`` verdict, producing the decision-grade numbers:
- ``dim_means`` incl. ``friend_not_narrator`` (the narrator-hole metric), and
- ``should_NOT_have_spoken`` = fraction of spoken lines that should've been silence.

Per-cell fail-safe (mirrors ``bench/run.py``): each judge call runs under a hard
wall-clock timeout with a 503-retry; on any error the row parks (``error`` set,
no scores) and the run CONTINUES — never abort, never fabricate a score.

Usage:
    # baseline the canonical 137-line session:
    uv run --no-sync python scripts/eval/bench_gemini_judge.py \
        --session-name 20260602-075843 --events ALL --out .planning/eval-runs/bench-baseline.json

    # any session dir, only HEARTBEAT lines, capped:
    uv run --no-sync python scripts/eval/bench_gemini_judge.py \
        --session "<recordings dir>" --events HEARTBEAT --limit 40 --concurrency 6
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load .env into os.environ (manual — avoids find_dotenv frame issues). Never print values."""
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _load_judge_module():
    """Import the canonical judge module by path (reuse its rubric + loaders verbatim)."""
    path = REPO / "scripts" / "eval" / "respan_sven_heartbeat_judge.py"
    spec = importlib.util.spec_from_file_location("hbj", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CALL_TIMEOUT_S = 60.0
_RETRIES = 3


def _judge_one_gemini(client, model: str, hbj, row: dict) -> dict:
    """Judge ONE row through Gemini direct, reusing the canonical JUDGE_SYSTEM rubric.

    Returns the same row shape the Respan judge produces (id/event/line/status/scores),
    or an ``error`` field on a parked failure (never a fabricated score).
    """
    from google.genai import types

    user = f"EVIDENCE:\n{row['digest']}\n\nLINE SVEN SPOKE:\n\"{row['line']}\""
    cfg = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json",
        system_instruction=hbj.JUDGE_SYSTEM,
        max_output_tokens=900,
    )
    out = {"id": row["id"], "event": row["event"], "line": row["line"], "status": 0}
    last_err = ""
    for attempt in range(_RETRIES):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    client.models.generate_content,
                    model=model,
                    contents=[user],
                    config=cfg,
                )
                resp = fut.result(timeout=_CALL_TIMEOUT_S)
            content = resp.text or ""
            if not content:
                last_err = "blocked: no text candidate"
                break
            try:
                scores = json.loads(content)
            except Exception:
                s, e = content.find("{"), content.rfind("}")
                scores = json.loads(content[s:e + 1]) if s >= 0 and e > s else {}
            out["status"] = 200
            out["scores"] = scores
            return out
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)[:160]
            # 503 / transient overload → back off and retry; other errors park immediately.
            if "503" in last_err or "UNAVAILABLE" in last_err or "TimeoutError" in last_err:
                time.sleep(2.0 * (attempt + 1))
                continue
            break
    out["status"] = -1
    out["error"] = last_err
    return out


def _worst_lines(results: list, hbj, dim: str, n: int = 6) -> list[dict]:
    """The n lowest-scoring lines on ``dim`` (for the next-goal evidence)."""
    scored = [
        r for r in results
        if isinstance(r.get("scores"), dict)
        and hbj._score_value(r["scores"], dim) is not None
    ]
    scored.sort(key=lambda r: hbj._score_value(r["scores"], dim) or 0.0)
    return [
        {
            "event": r["event"],
            dim: hbj._score_value(r["scores"], dim),
            "should_speak": r["scores"].get("should_speak"),
            "line": r["line"][:160],
            "why": r["scores"].get("why", ""),
        }
        for r in scored[:n]
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--session", help="captured recordings session dir")
    g.add_argument("--session-name", help="basename under ~/Library/Application Support/vibemix/recordings")
    ap.add_argument("--events", default="ALL", help="comma list or ALL (HEARTBEAT,PHASE,MIX_MOVE,...)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--model-alias", default="live_coach", help="router alias for the judge model")
    ap.add_argument("--out", default=None, help="write the full verdict json here")
    ap.add_argument("--label", default="bench", help="label echoed into the verdict")
    args = ap.parse_args()

    _load_dotenv()
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("FAIL: GEMINI_API_KEY absent", file=sys.stderr)
        return 2

    if args.session_name:
        session = Path.home() / "Library/Application Support/vibemix/recordings" / args.session_name
    else:
        session = Path(os.path.expanduser(args.session))
    if not (session / "invocations").is_dir():
        print(f"FAIL: no invocations/ under {session}", file=sys.stderr)
        return 2

    hbj = _load_judge_module()
    probe_status = hbj.probe_capture_status(session)
    _caveat = hbj.probe_caveat(probe_status)
    if _caveat:
        print(_caveat, file=sys.stderr)
    from google import genai
    from vibemix.llm import model_router

    res = model_router.resolve(args.model_alias)
    model = res[0] if isinstance(res, (tuple, list)) else res
    client = genai.Client(api_key=key)

    events = set() if args.events.strip().upper() == "ALL" else {
        e.strip() for e in args.events.split(",") if e.strip()
    }
    rows = hbj.load_rows(session, events, args.limit)
    if not rows:
        print("FAIL: 0 spoken lines to judge", file=sys.stderr)
        return 1

    print(f"-> judging {len(rows)} lines on {model} (concurrency={args.concurrency})", file=sys.stderr)
    results: list[dict] = [None] * len(rows)  # type: ignore[list-item]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_judge_one_gemini, client, model, hbj, row): i for i, row in enumerate(rows)}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            i = futs[fut]
            results[i] = fut.result()
            done += 1
            if done % 20 == 0:
                print(f"   {done}/{len(rows)}", file=sys.stderr)

    scored = hbj._scored_results(results)
    means = hbj._dim_means(results)
    parsed = len(scored)
    errored = sum(1 for r in results if r.get("error"))
    should_not = sum(
        1 for r in scored if r["scores"].get("should_speak") is False
    )
    verdict = {
        "schema": "vibemix_bench_gemini_v1",
        "label": args.label,
        "session": str(session),
        "probe_capture": probe_status,
        "model": model,
        "events": sorted(events) or "ALL",
        "n_judged": parsed,
        "n_errored": errored,
        "dim_means": means,
        "thresholds": hbj.QUALITY_MEAN_THRESHOLDS,
        "should_NOT_have_spoken": should_not,
        "should_NOT_have_spoken_pct": round(100 * should_not / parsed, 1) if parsed else None,
        "worst_friend": _worst_lines(results, hbj, "friend_not_narrator"),
        "worst_grounded": _worst_lines(results, hbj, "grounded_not_fabricated"),
    }
    if args.out:
        outp = Path(os.path.expanduser(args.out))
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps({"verdict": verdict, "rows": results}, indent=2, ensure_ascii=False))
        print(f"-> wrote {outp}", file=sys.stderr)

    # Compact human summary
    print(json.dumps({
        "label": args.label,
        "n_judged": parsed,
        "n_errored": errored,
        "dim_means": means,
        "should_NOT_have_spoken": should_not,
        "should_NOT_have_spoken_pct": verdict["should_NOT_have_spoken_pct"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
