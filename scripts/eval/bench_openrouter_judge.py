#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""bench_openrouter_judge.py — the 5-dim Sven judge on OPENROUTER transport.

Same move ``bench_gemini_judge.py`` made when the Respan gateway 404'd, applied
one ring further out: when the direct ``GEMINI_API_KEY`` is depleted (429
RESOURCE_EXHAUSTED), the bench goes dark even though the LIVE reaction path is
healthy — the product brain runs through OpenRouter in proxy/default mode and
generates real lines that need judging NOW. This driver reuses the canonical
judge's rubric + row-loader + scoring VERBATIM (imported, never re-implemented —
the rubric IS the instrument) and swaps only the transport: the same
router-selected Gemini model served via OpenRouter's OpenAI-compat API.

Transport caveat for the record: scores from this driver are comparable to
``bench_gemini_judge.py`` runs to the extent OpenRouter serves the same model
id; label runs accordingly (the verdict carries ``transport: openrouter``).

Per-cell fail-safe (mirrors ``bench/run.py``): each judge call runs under a
hard wall-clock timeout with transient-retry; on any error the row parks
(``error`` set, no scores) and the run CONTINUES — never abort, never
fabricate a score.

Usage:
    uv run --no-sync python scripts/eval/bench_openrouter_judge.py \
        --session "<recordings dir>" --events ALL --out .planning/eval-runs/or-judge.json
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


def _judge_one_openrouter(client, model: str, hbj, row: dict) -> dict:
    """Judge ONE row through OpenRouter, reusing the canonical JUDGE_SYSTEM rubric.

    Returns the same row shape the Respan/Gemini judges produce
    (id/event/line/status/scores), or an ``error`` field on a parked failure
    (never a fabricated score).
    """
    user = f"EVIDENCE:\n{row['digest']}\n\nLINE SVEN SPOKE:\n\"{row['line']}\""
    out = {"id": row["id"], "event": row["event"], "line": row["line"], "status": 0}
    last_err = ""
    for attempt in range(_RETRIES):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": hbj.JUDGE_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    temperature=0,
                    max_tokens=900,
                    response_format={"type": "json_object"},
                    # Probe finding from the live path (openrouter_llm.py): with a
                    # tight budget the model spends it all on hidden reasoning and
                    # returns empty content — keep reasoning minimal.
                    extra_body={"reasoning": {"effort": "low"}},
                )
                resp = fut.result(timeout=_CALL_TIMEOUT_S)
            content = (resp.choices[0].message.content or "") if resp.choices else ""
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
            # 429/5xx/timeout → back off and retry; other errors park immediately.
            transient = any(t in last_err for t in ("429", "502", "503", "UNAVAILABLE", "TimeoutError"))
            if transient:
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
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--model-alias", default="live_coach_openrouter", help="router alias for the judge model")
    ap.add_argument("--out", default=None, help="write the full verdict json here")
    ap.add_argument("--label", default="bench-openrouter", help="label echoed into the verdict")
    args = ap.parse_args()

    _load_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        print("FAIL: OPENROUTER_API_KEY absent", file=sys.stderr)
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
    from openai import OpenAI

    sys.path.insert(0, str(REPO / "src"))
    from vibemix.agent.openrouter_llm import OPENROUTER_BASE_URL
    from vibemix.llm import model_router

    res = model_router.resolve(args.model_alias)
    model = res[0] if isinstance(res, (tuple, list)) else res
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)

    events = set() if args.events.strip().upper() == "ALL" else {
        e.strip() for e in args.events.split(",") if e.strip()
    }
    rows = hbj.load_rows(session, events, args.limit)
    if not rows:
        print("FAIL: 0 spoken lines to judge", file=sys.stderr)
        return 1

    print(
        f"-> judging {len(rows)} lines on {model} via OpenRouter (concurrency={args.concurrency})",
        file=sys.stderr,
    )
    results: list[dict] = [None] * len(rows)  # type: ignore[list-item]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_judge_one_openrouter, client, model, hbj, row): i for i, row in enumerate(rows)}
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
        "schema": "vibemix_bench_openrouter_v1",
        "label": args.label,
        "transport": "openrouter",
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

    print(json.dumps({
        "label": args.label,
        "transport": "openrouter",
        "n_judged": parsed,
        "n_errored": errored,
        "dim_means": means,
        "should_NOT_have_spoken": should_not,
        "should_NOT_have_spoken_pct": verdict["should_NOT_have_spoken_pct"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
