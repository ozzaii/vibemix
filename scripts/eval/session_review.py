#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""session_review.py — whole-SESSION persona review of a recorded vibemix session.

The per-line judges (bench_gemini_judge / bench_openrouter_judge) score one
spoken line at a time and structurally cannot see the failures real users
actually report: cold-start silence, dead-air stretches, repetition across the
set, late lines. This reviewer loads ONE recorded session dir, deterministically
assembles a whole-session digest (musical-event timeline, every spoken line with
timestamp + latency, gate silences, silence gaps, repetition stats), then asks a
role-played DJ persona for qualitative product feedback in ONE call.

Data flow: events.jsonl + session.json -> digest (pure python, dep-free) ->
one OpenRouter call (model via model_router, never inlined) -> review JSON with
a FIXED complaint-category enum so feedback_aggregate.py can rank failure modes
across N sessions without an LLM.

Park-never-fabricate: the deterministic ``stats`` block is always written; on
any transport error the ``review`` half parks with ``error`` set and the run
exits 0 so fleet harvests continue.

Usage:
    uv run --no-sync python scripts/eval/session_review.py \
        --session "<recording dir>" --persona-preset beginner \
        --out .planning/eval-runs/review.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]

# Complaint categories are a FIXED enum so cross-session aggregation is
# deterministic string-matching, not LLM clustering.
COMPLAINT_CATEGORIES = (
    "silence",      # said nothing when something deserved a reaction / long dead air
    "late",         # reaction landed after the moment had passed
    "repetition",   # same phrasing or observation again and again
    "ungrounded",   # claimed something that didn't happen in the audio
    "generic",      # could have been said about any set (AI-slop filler)
    "timing",       # spoke over the wrong moment (drop, vocal, tight blend)
    "tone",         # wrong register for me (too gentle / too harsh / cringe)
    "other",
)

PERSONA_PRESETS = {
    "beginner": (
        "a 19-year-old beginner DJ at their third-ever house-party set, nervous, "
        "still counting bars out loud, wants encouragement and ONE concrete tip at a time"
    ),
    "intermediate": (
        "a 27-year-old intermediate DJ who plays monthly bar gigs, comfortable "
        "beatmatching, wants honest feedback on transitions and track choice, hates filler"
    ),
    "pro": (
        "a 35-year-old professional club DJ with 12 years behind decks, zero patience "
        "for narration or flattery, only values observations a real peer in the booth would make"
    ),
}

_CALL_TIMEOUT_S = 90.0
_RETRIES = 3
_MAX_TIMELINE_ROWS = 160
_NO_REACTION_WINDOW_S = 30.0

REVIEW_SYSTEM_TEMPLATE = """You are {persona_desc}.

You just finished a DJ set with an AI co-host ("Sven") in your ear. Below is the
full honest record of your session: every musical event the app detected, every
line Sven actually spoke (with how late it arrived), and every moment it chose
silence. React as YOURSELF — a DJ giving product feedback after a real session,
not an evaluator filling a rubric. Be concrete; quote Sven's lines back when they
annoyed or delighted you. Silence and lateness are part of the experience: if
Sven said nothing for minutes during your set, that IS feedback.

Reply with ONLY a JSON object:
{{
  "overall_feeling": "<2-3 sentences, in your own voice>",
  "would_use_again_0_10": <int 0-10>,
  "top_annoyances": [
    {{"category": "<one of: {categories}>",
      "what": "<1-2 sentences, specific, cite t= timestamps or quoted lines>",
      "evidence_t": <approx session-seconds this happened, or null>}}
  ],
  "top_likes": [
    {{"what": "<1 sentence, specific>", "evidence_t": <seconds or null>}}
  ],
  "change_one_thing": "<the single change that would most improve the next session>"
}}
Give at most 4 annoyances and 3 likes. Every annoyance MUST use a category from
the list exactly. If the session gave you almost nothing to react to, say so in
overall_feeling and complain via category "silence"."""


def _load_dotenv() -> None:
    """Load repo-root .env into os.environ. Never print values."""
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _normalize_line(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def assemble_digest(session_dir: Path) -> dict[str, Any]:
    """Pure deterministic half: timeline + stats from events.jsonl/session.json."""
    events = _load_jsonl(session_dir / "events.jsonl")
    try:
        session_meta = json.loads((session_dir / "session.json").read_text())
    except (OSError, json.JSONDecodeError):
        session_meta = {}

    musical = [r for r in events if r.get("kind") == "event"]
    spoken = [
        r
        for r in events
        if r.get("kind") == "ai_message"
        and isinstance(r.get("message"), str)
        and r["message"].strip()
        and not r.get("suppression")
    ]
    gated = [r for r in events if r.get("kind") == "speak_gate" and r.get("verdict") == "silent"]

    times = [float(r["t"]) for r in events if isinstance(r.get("t"), (int, float))]
    duration_s = max(times) if times else 0.0

    # Silence gaps between consecutive spoken lines (plus lead-in and tail).
    spoken_ts = sorted(float(r["t"]) for r in spoken if isinstance(r.get("t"), (int, float)))
    edges = [0.0, *spoken_ts, duration_s]
    gaps = [round(b - a, 1) for a, b in zip(edges, edges[1:], strict=False)]
    longest_silence_s = max(gaps) if gaps else duration_s

    # Musical events that never produced a spoken line within the window.
    unreacted = [
        r
        for r in musical
        if isinstance(r.get("t"), (int, float))
        and not any(0.0 <= ts - float(r["t"]) <= _NO_REACTION_WINDOW_S for ts in spoken_ts)
    ]

    latencies = [
        float(r["latency_s"]) for r in spoken if isinstance(r.get("latency_s"), (int, float))
    ]
    dupes = Counter(_normalize_line(r["message"]) for r in spoken)
    repeated = {line: n for line, n in dupes.items() if n > 1 and line}

    probe_raw = session_meta.get("sven_probe_mode")
    probe = "probe" if probe_raw is True else "shipped" if probe_raw is False else "unknown"

    stats = {
        "duration_s": round(duration_s, 1),
        "musical_events": len(musical),
        "spoken_lines": len(spoken),
        "gated_silent": len(gated),
        "gate_reasons": dict(Counter(str(r.get("reason")) for r in gated).most_common(6)),
        "time_to_first_line_s": round(spoken_ts[0], 1) if spoken_ts else None,
        "longest_silence_s": round(longest_silence_s, 1),
        "unreacted_events": len(unreacted),
        "max_latency_s": round(max(latencies), 2) if latencies else None,
        "mean_latency_s": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "repeated_lines": dict(sorted(repeated.items(), key=lambda kv: -kv[1])[:5]),
        "probe_capture": probe,
        "crashed": session_meta.get("crashed"),
    }

    timeline: list[tuple[float, str]] = []
    for r in musical:
        t = float(r.get("t", 0.0))
        kind = str(r.get("type", "EVENT"))
        extra = f" ({r['phase']})" if r.get("phase") else ""
        mark = "" if any(0.0 <= ts - t <= _NO_REACTION_WINDOW_S for ts in spoken_ts) else " — no reaction"
        timeline.append((t, f"[t={t:.0f}s] EVENT {kind}{extra}{mark}"))
    for r in gated:
        t = float(r.get("t", 0.0))
        timeline.append(
            (
                t,
                f"[t={t:.0f}s] MOMENT {r.get('type')} detected — Sven chose silence"
                f" ({r.get('reason')})",
            )
        )
    for r in spoken:
        t = float(r.get("t", 0.0))
        lat = r.get("latency_s")
        lat_txt = f", arrived {float(lat):.1f}s later" if isinstance(lat, (int, float)) else ""
        cit = (r.get("citation") or {}).get("count")
        timeline.append(
            (t, f'[t={t:.0f}s] SVEN (on {r.get("event")}{lat_txt}, citations={cit}): "{r["message"].strip()}"')
        )
    timeline.sort(key=lambda pair: pair[0])
    lines = [text for _, text in timeline]
    if len(lines) > _MAX_TIMELINE_ROWS:
        omitted = len(lines) - _MAX_TIMELINE_ROWS
        lines = lines[:_MAX_TIMELINE_ROWS] + [f"... ({omitted} more rows omitted)"]

    return {"stats": stats, "timeline": lines}


def render_digest_text(session_name: str, digest: dict[str, Any]) -> str:
    s = digest["stats"]
    first_line = (
        f"{s['time_to_first_line_s']}s" if s["time_to_first_line_s"] is not None else "NEVER"
    )
    head = (
        f"SESSION {session_name} — duration {s['duration_s']}s, "
        f"{s['musical_events']} musical events detected, {s['spoken_lines']} lines spoken, "
        f"{s['gated_silent']} reactions gated to silence.\n"
        f"First spoken line at: {first_line}. "
        f"Longest stretch with no voice: {s['longest_silence_s']}s. "
        f"Events that got no reaction: {s['unreacted_events']}.\n"
    )
    if s["repeated_lines"]:
        head += f"Lines repeated verbatim: {json.dumps(s['repeated_lines'], ensure_ascii=False)}\n"
    body = "\n".join(digest["timeline"]) if digest["timeline"] else "(no events, no speech — silence)"
    return head + "\nTIMELINE:\n" + body


def salvage_json(content: str) -> dict[str, Any] | None:
    """Recover a JSON object from model output with trailing garbage.

    Observed failure shape: a fully valid object whose closing brace is
    preceded by junk lines (``."`` / ``"``) the model appended. Strategy:
    plain parse, then raw_decode (ignores trailing junk AFTER a complete
    object), then drop trailing lines one at a time and re-close whatever
    brackets remain open. Deterministic, never invents content.
    """
    start = content.find("{")
    if start < 0:
        return None
    body = content[start:]
    try:
        doc = json.loads(body)
        return doc if isinstance(doc, dict) else None
    except json.JSONDecodeError:
        pass
    try:
        doc = json.JSONDecoder().raw_decode(body)[0]
        return doc if isinstance(doc, dict) else None
    except json.JSONDecodeError:
        pass
    lines = body.splitlines()
    for cut in range(len(lines) - 1, max(len(lines) - 40, 0), -1):
        prefix = "\n".join(lines[:cut]).rstrip().rstrip(",")
        stack: list[str] = []
        in_str = False
        esc = False
        for ch in prefix:
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = in_str
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch in "{[":
                stack.append(ch)
            elif ch in "}]" and stack:
                stack.pop()
        if in_str:
            prefix += '"'
        candidate = prefix + "".join("}" if b == "{" else "]" for b in reversed(stack))
        try:
            doc = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict):
            return doc
    return None


def review_once(client: Any, model: str, system: str, digest_text: str) -> dict[str, Any]:
    """One persona review call; parks (error dict) rather than fabricating."""
    last_err = ""
    for attempt in range(_RETRIES):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": digest_text},
                    ],
                    temperature=0.3,
                    max_tokens=1200,
                    response_format={"type": "json_object"},
                    # OpenRouter quirk (see openrouter_llm.py): with a tight budget
                    # the model spends it all on hidden reasoning — keep it low.
                    extra_body={"reasoning": {"effort": "low"}},
                )
                resp = fut.result(timeout=_CALL_TIMEOUT_S)
            content = (resp.choices[0].message.content or "") if resp.choices else ""
            if not content:
                last_err = "blocked: no text candidate"
                break
            doc = salvage_json(content)
            if doc is not None:
                return doc
            return {"error": "unparseable response", "raw_head": content[:400]}
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)[:160]
            transient = any(t in last_err for t in ("429", "502", "503", "UNAVAILABLE", "TimeoutError"))
            if transient:
                time.sleep(2.0 * (attempt + 1))
                continue
            break
    return {"error": last_err}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session", required=True, help="recorded session dir (events.jsonl inside)")
    ap.add_argument("--persona-preset", choices=sorted(PERSONA_PRESETS), default=None)
    ap.add_argument("--persona-desc", default=None, help="free-text persona (overrides preset)")
    ap.add_argument("--persona-label", default=None, help="label echoed into the output JSON")
    ap.add_argument("--model-alias", default="live_coach_openrouter")
    ap.add_argument("--out", default=None, help="write the review JSON here")
    ap.add_argument("--dry-run", action="store_true", help="print digest, skip the LLM call")
    args = ap.parse_args()

    session_dir = Path(os.path.expanduser(args.session))
    if not (session_dir / "events.jsonl").exists():
        print(f"FAIL: no events.jsonl under {session_dir}", file=sys.stderr)
        return 2

    persona_desc = args.persona_desc or PERSONA_PRESETS.get(args.persona_preset or "", "")
    if not persona_desc:
        print("FAIL: provide --persona-preset or --persona-desc", file=sys.stderr)
        return 2
    persona_label = args.persona_label or args.persona_preset or "custom"

    digest = assemble_digest(session_dir)
    digest_text = render_digest_text(session_dir.name, digest)
    if args.dry_run:
        print(digest_text)
        return 0

    _load_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        print("FAIL: OPENROUTER_API_KEY absent", file=sys.stderr)
        return 2

    sys.path.insert(0, str(REPO / "src"))
    from openai import OpenAI

    from vibemix.agent.openrouter_llm import OPENROUTER_BASE_URL
    from vibemix.llm import model_router

    res = model_router.resolve(args.model_alias)
    model = res[0] if isinstance(res, (tuple, list)) else res
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)

    system = REVIEW_SYSTEM_TEMPLATE.format(
        persona_desc=persona_desc, categories=", ".join(COMPLAINT_CATEGORIES)
    )
    review = review_once(client, model, system, digest_text)

    out_doc = {
        "schema": "vibemix_session_review_v1",
        "session": str(session_dir),
        "session_name": session_dir.name,
        "persona": persona_label,
        "persona_desc": persona_desc,
        "model": model,
        "transport": "openrouter",
        "stats": digest["stats"],
        "review": review,
    }
    if args.out:
        outp = Path(os.path.expanduser(args.out))
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(out_doc, indent=2, ensure_ascii=False))
        print(f"-> wrote {outp}", file=sys.stderr)
    print(json.dumps(out_doc, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
