#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""bench_sim_gemini.py — the "bench until perfection" ITERATION engine (Gemini-direct).

``respan_sven_sim.py`` is the controlled scenario harness: synthetic deck-move
scenarios → REAL ``decide_speak_gate`` → REAL coach persona → model → 5-dim judge.
Its transport is hard-pinned to the Respan gateway (currently 404). This driver
reuses that sim's SCENARIOS + gate + line-shaping + linter VERBATIM (imported) and
swaps the dead transport for the live google-genai SDK, so a candidate persona can
be measured on fresh generation without touching product code.

Two things it answers that re-judging recorded lines cannot:
  1. how the CURRENT shipped persona scores on fresh generation per scenario, and
  2. how a CANDIDATE persona (``--persona-file``) scores vs. the shipped one —
     the prompt-iteration loop, with the bench as the gate.

Gate routing (silent vs speak) comes from the REAL ``decide_speak_gate`` — so this
ALSO measures the speak-gate (the should-NOT-have-spoken hole) the same way live does.

Usage:
    # shipped persona, all scenarios, judged:
    uv run --no-sync python scripts/eval/bench_sim_gemini.py --out .planning/eval-runs/sim-shipped.json

    # candidate persona override (a full system string in a file):
    uv run --no-sync python scripts/eval/bench_sim_gemini.py \
        --persona-file /tmp/cand_persona.txt --label cand-A --out .planning/eval-runs/sim-candA.json

    # deterministic gate-only (no model, no key) — proves gate routing:
    uv run --no-sync python scripts/eval/bench_sim_gemini.py --gate-only
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env = REPO / ".env"
    if not env.exists():
        return
    for raw in env.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _load_mod(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CALL_TIMEOUT_S = 60.0
_RETRIES = 4


def _gemini_call(client, model, *, system, user, temperature, json_mode):
    """One Gemini-direct call with 503-retry + hard timeout. Returns text ('' on park)."""
    import concurrent.futures

    from google.genai import types

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
        max_output_tokens=900 if json_mode else 500,
        **({"response_mime_type": "application/json"} if json_mode else {}),
    )
    last = ""
    for attempt in range(_RETRIES):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(client.models.generate_content, model=model, contents=[user], config=cfg)
                resp = fut.result(timeout=_CALL_TIMEOUT_S)
            return resp.text or ""
        except Exception as e:  # noqa: BLE001
            last = repr(e)[:140]
            if any(t in last for t in ("503", "UNAVAILABLE", "Timeout", "429", "RESOURCE_EXHAUSTED")):
                time.sleep(2.0 * (attempt + 1))
                continue
            break
    print(f"   [park] {last}", file=sys.stderr)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-only", action="store_true", help="deterministic gate routing only, no model")
    ap.add_argument("--persona-file", default=None, help="candidate persona system string (overrides shipped)")
    ap.add_argument("--match-live-persona", action="store_true", help="include citation grammar (live prompt parity)")
    ap.add_argument("--match-live-linter", action="store_true", help="score only text the live CitationLinter emits")
    ap.add_argument("--include-kick-density-target", action="store_true")
    ap.add_argument("--scenarios-file", default=None,
                    help="JSON list of custom scenarios (replaces SCENARIOS) for A/B failure-mode tests")
    ap.add_argument("--model-alias", default="live_coach")
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--label", default="sim")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    sim = _load_mod("sven_sim", "scripts/eval/respan_sven_sim.py")
    hbj = _load_mod("hbj", "scripts/eval/respan_sven_heartbeat_judge.py")
    from vibemix.prompts.matrix import build_system_instruction
    from vibemix.state import Event

    if args.persona_file:
        persona = Path(os.path.expanduser(args.persona_file)).read_text()
        persona_src = f"candidate:{args.persona_file}"
    else:
        persona = build_system_instruction(
            "intermediate", "hype",
            include_tag_dsl=False,
            include_citation_grammar=bool(args.match_live_persona),
        )
        persona_src = "shipped:SVEN_COACH_IDENTITY"

    client = model = None
    if not args.gate_only:
        _load_dotenv()
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            print("FAIL: GEMINI_API_KEY absent (use --gate-only for the keyless pass)", file=sys.stderr)
            return 2
        from google import genai
        from vibemix.llm import model_router
        res = model_router.resolve(args.model_alias)
        model = res[0] if isinstance(res, (tuple, list)) else res
        client = genai.Client(api_key=key)

    if args.scenarios_file:
        scenarios = json.loads(Path(os.path.expanduser(args.scenarios_file)).read_text())
    else:
        scenarios = list(sim.SCENARIOS)
        if args.include_kick_density_target:
            scenarios.append(sim.KICK_DENSITY_TARGET)

    print(f"persona={persona_src}  model={model}  scenarios={len(scenarios)}", file=sys.stderr)
    print(f"{'scenario':<32} {'event':<16} {'gate':<7} {'ok':<3} friend/grnd/earn/move/voice", file=sys.stderr)

    results = []
    for sc in scenarios:
        state = sim._state_for_scenario(sc)
        ev_extra = sim._extra_for_scenario(sc, state)
        ev = Event(type=sc["event"], state=state, extra=ev_extra)
        gate = sim.decide_speak_gate(ev)
        gate_ok = gate.verdict == sc["expect"]
        row = {"name": sc["name"], "event": sc["event"], "expect": sc["expect"],
               "gate": gate.verdict, "gate_reason": gate.reason, "gate_ok": gate_ok}
        if args.gate_only or gate.verdict != "speak":
            print(f"{sc['name']:<32} {sc['event']:<16} {gate.verdict:<7} {'ok' if gate_ok else '!!':<3} (no gen)", file=sys.stderr)
            results.append(row)
            continue

        user = f"{sc['evidence']}\n\n{sc['task']}"
        raw = _gemini_call(client, model, system=persona, user=user, temperature=args.temperature, json_mode=False).strip()
        line, model_line, suppressed = sim._line_or_silence(raw)
        live_linter = None
        if args.match_live_linter:
            registry = sim._registry_for_sim(sc, ev_extra)
            line, model_line, live_linter = sim._live_linter_checked_line(line, model_line, registry=registry)
            suppressed = bool(raw and not model_line and not line)

        if line:
            jtext = _gemini_call(
                client, model,
                system=hbj.JUDGE_SYSTEM,
                user=f"EVIDENCE:\n{sc['evidence']}\n\nLINE SVEN SPOKE:\n\"{line}\"",
                temperature=0, json_mode=True,
            )
            try:
                scores = json.loads(jtext) if jtext else {}
            except Exception:
                s, e = jtext.find("{"), jtext.rfind("}")
                scores = json.loads(jtext[s:e + 1]) if s >= 0 and e > s else {}
        elif raw and not suppressed:
            scores = {**{d: 0 for d in hbj.DIMS}, "should_speak": False, "why": "runtime suppressed scaffold/fragment"}
        else:
            scores = {}

        row.update({"line": line, "model_line": model_line, "raw_line": raw, "scores": scores})
        if live_linter is not None:
            row["live_linter"] = live_linter
        sd = "/".join(str(scores.get(d, "-")) for d in hbj.DIMS)
        print(f"{sc['name']:<32} {sc['event']:<16} {gate.verdict:<7} {'ok' if gate_ok else '!!':<3} {sd}", file=sys.stderr)
        print(f"    -> {line[:150]}", file=sys.stderr)
        results.append(row)

    # Aggregate
    scored = [r for r in results if isinstance(r.get("scores"), dict)
              and hbj._score_value(r["scores"], "friend_not_narrator") is not None]
    means = {}
    for d in hbj.DIMS:
        vals = [hbj._score_value(r["scores"], d) for r in scored]
        vals = [v for v in vals if v is not None]
        means[d] = round(sum(vals) / len(vals), 2) if vals else None
    gate_ok_n = sum(1 for r in results if r["gate_ok"])
    spoke = [r for r in results if r["gate"] == "speak"]
    should_not = sum(1 for r in scored if r["scores"].get("should_speak") is False)

    verdict = {
        "schema": "vibemix_bench_sim_gemini_v1",
        "label": args.label,
        "persona_src": persona_src,
        "model": model,
        "n_scenarios": len(results),
        "gate_ok": gate_ok_n,
        "gate_ok_pct": round(100 * gate_ok_n / len(results), 0) if results else None,
        "n_spoke": len(spoke),
        "n_judged": len(scored),
        "dim_means": means,
        "thresholds": hbj.QUALITY_MEAN_THRESHOLDS,
        "should_NOT_have_spoken": should_not,
    }
    if args.out:
        outp = Path(os.path.expanduser(args.out))
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps({"verdict": verdict, "rows": results}, indent=2, ensure_ascii=False))
        print(f"-> wrote {outp}", file=sys.stderr)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
