#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Sven SIMULATION engine — controlled deck-move scenarios, no live set needed.

Kaan's original idea: simulate knob-twists / the drop / mix-moves, spam them,
and check the co-host's behaviour via observability — WITHOUT having to DJ a
real set. The live ws bus is client-only (Invariant #4) so we cannot inject a
fake move into the RUNNING app; instead this drives the SAME product logic
offline:

  synthetic scenario  →  REAL `decide_speak_gate` (today's build)  →
  REAL coach persona (`build_system_instruction`)  →  model (Respan gateway)  →
  5-dim Respan judge.

It tests exactly what the live set can't give on demand: does the gate route
each event right (idle silent, real move speaks), and does the current persona
COACH a move instead of describing it? Validity boundary: the evidence text is
authored per scenario (faithful to the real bundle format), and there is no
audio Part — so this tests the GATE + PERSONA + move-coaching LOGIC (the things
the fix changed), NOT audio-vibe grounding. For audio grounding, judge real
recorded lines (see respan_sven_heartbeat_judge.py).

Usage:
    export RESPAN_API_KEY=...
    uv run python scripts/eval/respan_sven_sim.py            # gate + generate + judge
    uv run python scripts/eval/respan_sven_sim.py --gate-only # deterministic, no model
    uv run python scripts/eval/respan_sven_sim.py --no-log    # don't log to Respan
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from vibemix.agent.dj_cohost import repair_finished_headphone_line
from vibemix.bench.fixtures import fixture_state_for
from vibemix.llm.model_router import resolve_model
from vibemix.prompts.matrix import build_system_instruction
from vibemix.runtime.speak_gate import decide_speak_gate
from vibemix.runtime.suggestion_voice import build_next_suggestion_voice_line
from vibemix.state import Event, EvidenceRegistry

RESPAN_BASE = "https://api.respan.ai/api"
GATEWAY = f"{RESPAN_BASE}/chat/completions"
LOG_ENDPOINT = f"{RESPAN_BASE}/request-logs/create"


def _respan_gateway_model() -> str:
    """Return the Respan model id derived from the central live-coach route."""

    routed = resolve_model("live_coach_openrouter")
    return routed.replace("google/", "gemini/", 1)


MODEL = _respan_gateway_model()

JUDGE_SYSTEM = """You are a blind judge grading ONE line spoken by Sven, an AI DJ co-host riding in the booth with a DJ during a live set. You see the EVIDENCE Sven had and the LINE he spoke. Grade only the line.

Sven should COACH, not narrate: every time he speaks he should hand the DJ one move, one read, or one forward-nudge. Describing the sound back ("a metallic synth dominated the high end") is the core failure (describe-bank) — the DJ already hears it. Silence is valid: on an idle tick with no move and nothing actionable, the right move is to say NOTHING.

Score each dimension 0-3. USE THE FULL RANGE — a line that buries a real point under narration is a 1-2, not a 0; reserve 0 for nothing of that dimension.
- friend_not_narrator: 0=pure sound-narration. 1=mostly narration, weak/buried point. 2=usable move/read but mixed with narration. 3=clean coaching, one move/read/nudge.
- grounded_not_fabricated: 0=invents a move/deck/track not in evidence. 1=partly unsupported. 2=mostly backed. 3=every specific backed (a cited real recent_moves entry IS grounded).
- earned_not_constant: 0=filler. 1=marginal. 2=worth saying. 3=clearly worth interrupting for.
- move_specific_not_spectrum: 0=vague spectrum. 1=sound specifics only. 2=names a real move/direction. 3=specific actionable next step.
- voice_no_slop: 0=generic AI slop. 1=stiff. 2=mostly natural. 3=real DJ friend in the ear.

Return ONLY compact JSON: {"friend_not_narrator":N,"grounded_not_fabricated":N,"earned_not_constant":N,"move_specific_not_spectrum":N,"voice_no_slop":N,"should_speak":true|false,"why":"<=12 words"}"""

DIMS = [
    "friend_not_narrator", "grounded_not_fabricated", "earned_not_constant",
    "move_specific_not_spectrum", "voice_no_slop",
]

# Controlled scenarios — authored faithful to the real evidence-bundle format.
# `expect` = the gate verdict we expect from today's build.
_HEAR = "hearing[rms=0.16 sub=0.62 low=0.24 mid=0.10 high=0.04 bpm=150]"
_CUE_HEAR = "hearing[rms=0.16 sub=0.62 low=0.24 mid=0.10 high=0.04 bpm=120]"
_CUE_STATE = {
    "set_seconds": 100.0,
    "phrase_position_confidence": 0.9,
    "next_phrase_at": 108.0,
    "next_phrase_cue_id": "phrase_boundary@108.0",
    "bpm": 120.0,
    "bpm_confidence": 0.95,
}
SCENARIOS = [
    {
        "name": "idle_heartbeat", "event": "HEARTBEAT", "extra": {}, "expect": "silent",
        "evidence": f"{_HEAR} | track=unknown | deck=mix | recent_moves[8s]: NONE | grounding_refs[[mix:deck_audio_support=no_deck_route]]",
        "task": "Steady stretch, no controller move. If there's a sound read worth one sharp line, say it; otherwise a single space to stay silent.",
    },
    {
        "name": "phase_with_cue_lookahead", "event": "PHASE", "extra": {},
        "state": _CUE_STATE, "cue_lookahead": True, "expect": "speak",
        "evidence": f"{_CUE_HEAR} | track=unknown | deck=mix | phase=groove->build | recent_moves[8s]: NONE | cue_anchor=phrase_boundary@108.0 | next_phrase_at=108.0",
        "task": "The phase shifted groove->build with no controller move, and the packet carries a grounded phrase-boundary lookahead. Hand one forward timing nudge.",
    },
    {
        "name": "heartbeat_with_grounded_payload", "event": "HEARTBEAT",
        "extra": {"next_suggestion_voice_line": "Forward read: a darker rolling 9A track pairs next - keeps the build."},
        "expect": "speak",
        "evidence": f"{_HEAR} | track=unknown | deck=A | recent_moves[8s]: NONE | next_track_ready=true",
        "task": "You have a grounded next-track suggestion (see payload). Hand it to Kaan as one forward nudge.",
    },
    {
        "name": "filter_cut_move", "event": "MIX_MOVE", "extra": {}, "expect": "speak",
        "evidence": f"{_HEAR} | track=unknown | deck=A | recent_moves[8s]: 0.6s ago A_filter: flat->cut (big twist) | grounding_refs[[midi:A_filter:_flat_to_cut_big_twist@612.4]] | move_effect_context[moves=1 deltas=high energy fell 31% (notable) rule=dsp_delta_not_causal_proof]",
        "task": "You just twisted the filter to a hard cut on deck A (recent_moves). Read what it did to the sound and hand one next-time nudge.",
    },
    {
        "name": "low_kill_move", "event": "MIX_MOVE", "extra": {}, "expect": "speak",
        "evidence": f"{_HEAR} | track=\"Raik - Trio d'Acid\" | deck=A | recent_moves[8s]: 0.5s ago A_low: flat->kill (big twist) | grounding_refs[[midi:A_low:_flat_to_kill_big_twist@880.1]] | move_effect_context[moves=1 deltas=low energy fell 44% (notable) rule=dsp_delta_not_causal_proof] | mixer_context[A(low=killed mid=flat hi=flat filter=flat)]",
        "task": "You just killed the lows on deck A (recent_moves). Read what that did and hand one next-time nudge.",
    },
    {
        "name": "drop_hit", "event": "DROP", "extra": {}, "expect": "speak",
        "evidence": "hearing[rms=0.28 sub=0.81 low=0.30 mid=0.12 high=0.06 bpm=150] | track=unknown | deck=A | phase=build->drop | recent_moves[8s]: NONE | drop_anchor=on_beat",
        "task": "The drop just landed. One short forward call.",
    },
    {
        "name": "layer_arrival_idle", "event": "LAYER_ARRIVAL", "extra": {}, "expect": "silent",
        "evidence": f"{_HEAR} | track=unknown | deck=A | recent_moves[8s]: NONE | layer=new_top_synth",
        "task": "A new top-end layer came in with no move from Kaan. Coach the direction if worth it, else stay silent.",
    },
    {
        "name": "track_change_with_cue_lookahead", "event": "TRACK_CHANGE", "extra": {},
        "state": _CUE_STATE, "cue_lookahead": True, "expect": "speak",
        "evidence": f"{_CUE_HEAR} | track=\"Valence - Infinite\"->\"Raik - Trio d'Acid\" | deck=A | recent_moves[8s]: NONE | cue_anchor=phrase_boundary@108.0 | next_phrase_at=108.0 | transition_block=no_resolved_decks",
        "task": "The track changed with no controller move or next-track candidate, and the packet carries a grounded phrase-boundary lookahead. Hand one forward timing nudge.",
    },
    {
        "name": "track_change_with_next", "event": "TRACK_CHANGE",
        "extra": {"next_suggestion_voice_line": "Forward read: a darker rolling 9A track pairs next - keeps the build."},
        "expect": "speak",
        "evidence": f"{_HEAR} | track=\"Valence - Infinite\"->\"Raik - Trio d'Acid\" | deck=A | recent_moves[8s]: NONE | next_track_ready=true camelot=9A bpm=128",
        "task": "The track just changed and the packet carries a grounded next-track receipt. Hand one forward nudge.",
    },
]


def _state_for_scenario(sc: dict) -> object:
    state, _ = fixture_state_for("snapshot", "plain")
    for key, value in (sc.get("state") or {}).items():
        if key == "set_seconds":
            state.set_start_at = time.time() - float(value)
        else:
            setattr(state, key, value)
    return state


def _extra_for_scenario(sc: dict, state: object) -> dict:
    extra = dict(sc["extra"])
    if sc.get("cue_lookahead"):
        registry = EvidenceRegistry()
        line = build_next_suggestion_voice_line(
            None,
            event_type=sc["event"],
            evidence_registry=registry,
            state=state,
        )
        if line:
            extra["next_suggestion_voice_line"] = line
    return extra


def _run_heartbeat_judge(
    *,
    session: str,
    out: str | None,
    dry_run: bool,
    no_log: bool,
) -> int:
    judge_script = Path(__file__).with_name("respan_sven_heartbeat_judge.py")
    cmd = [
        sys.executable,
        str(judge_script),
        "--session",
        session,
        "--events",
        "ALL",
        "--apply-current-gate",
        "--concurrency",
        "4",
    ]
    if dry_run:
        cmd.append("--dry-run")
    if no_log:
        cmd.append("--no-log")
    if out:
        cmd.extend(["--out", out])
    print("\nRecorded-set current-gate judge:", flush=True)
    return subprocess.call(cmd)


def _post(url: str, payload: dict, key: str, timeout: float = 60.0) -> tuple[int, dict | str]:
    if not url.startswith(f"{RESPAN_BASE}/"):
        raise ValueError(f"refusing non-Respan URL: {url!r}")
    try:
        r = httpx.post(url, json=payload, timeout=timeout,
                       headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text[:300]
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def _chat(system: str, user: str, key: str, max_tokens: int = 500) -> tuple[int, str]:
    status, resp = _post(GATEWAY, {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 1.0, "max_tokens": max_tokens,
    }, key)
    if status != 200 or not isinstance(resp, dict):
        return status, str(resp)
    return status, ((resp.get("choices") or [{}])[0].get("message", {}) or {}).get("content") or ""


def _judge(evidence: str, line: str, key: str) -> dict:
    status, resp = _post(GATEWAY, {
        "model": MODEL,
        "messages": [{"role": "system", "content": JUDGE_SYSTEM},
                     {"role": "user", "content": f"EVIDENCE:\n{evidence}\n\nLINE SVEN SPOKE:\n\"{line}\""}],
        "temperature": 0, "max_tokens": 900, "response_format": {"type": "json_object"},
    }, key)
    if status != 200 or not isinstance(resp, dict):
        return {}
    content = ((resp.get("choices") or [{}])[0].get("message", {}) or {}).get("content") or ""
    # The judge may fence the JSON or append extra prose; parse the first object only.
    start = content.find("{")
    if start < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(content[start:])
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-only", action="store_true", help="deterministic gate routing, no model")
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--heartbeat-session",
        default=None,
        help="also run respan_sven_heartbeat_judge.py --apply-current-gate on this recording",
    )
    ap.add_argument("--heartbeat-out", default=None)
    args = ap.parse_args()

    # The live coach persona (the current build): intermediate/hype cell = SVEN_COACH_IDENTITY.
    persona = build_system_instruction(
        "intermediate", "hype", include_tag_dsl=False, include_citation_grammar=False,
    )

    key = None
    if not args.gate_only:
        key = os.environ.get("RESPAN_API_KEY")
        if not key:
            print("RESPAN_API_KEY not set (env only); use --gate-only for the deterministic pass", file=sys.stderr)
            return 2

    results = []
    print(f"{'scenario':<32} {'event':<16} {'gate':<8} {'ok?':<4} friend/grnd/earn/move/voice")
    for sc in SCENARIOS:
        state = _state_for_scenario(sc)
        ev = Event(type=sc["event"], state=state, extra=_extra_for_scenario(sc, state))
        gate = decide_speak_gate(ev)
        ok = "ok" if gate.verdict == sc["expect"] else "!!"
        row = {"name": sc["name"], "event": sc["event"], "gate": gate.verdict,
               "gate_reason": gate.reason, "expect": sc["expect"], "gate_ok": gate.verdict == sc["expect"]}
        if args.gate_only or gate.verdict != "speak":
            print(f"{sc['name']:<32} {sc['event']:<16} {gate.verdict:<8} {ok:<4} (no generation)")
            results.append(row)
            continue
        user = f"{sc['evidence']}\n\n{sc['task']}"
        _st, line = _chat(persona, user, key)
        raw_line = (line or "").strip()
        line = repair_finished_headphone_line(raw_line) or ""
        if line:
            scores = _judge(sc["evidence"], line, key)
        elif raw_line:
            scores = {
                **{dim: 0 for dim in DIMS},
                "should_speak": False,
                "why": "runtime suppressed scaffold or packet fragment",
            }
        else:
            scores = {}
        row.update({"line": line, "raw_line": raw_line, "scores": scores})
        sd = "/".join(str(scores.get(d, "-")) for d in DIMS)
        print(f"{sc['name']:<32} {sc['event']:<16} {gate.verdict:<8} {ok:<4} {sd}")
        print(f"    -> {line[:140]}")
        if not args.no_log and key and line:
            _post(LOG_ENDPOINT, {
                "model": MODEL,
                "prompt_messages": [{"role": "user", "content": user}],
                "completion_message": {"role": "assistant", "content": line},
                "category": "sven-sim-20260603", "custom_identifier": sc["name"],
                "metadata": {"event": sc["event"], "gate": gate.verdict, **{d: scores.get(d) for d in DIMS}},
            }, key)
        results.append(row)

    scored = [r for r in results if isinstance(r.get("scores"), dict) and "friend_not_narrator" in r["scores"]]
    if scored:
        means = {d: round(sum(float(r["scores"].get(d, 0) or 0) for r in scored) / len(scored), 2) for d in DIMS}
        print(f"\nGENERATED-line dim means (n={len(scored)}):", json.dumps(means))
    gate_ok = sum(1 for r in results if r["gate_ok"])
    print(f"gate routing: {gate_ok}/{len(results)} matched expectation")
    if args.out:
        with open(args.out, "w") as f:
            json.dump({"results": results}, f, indent=2, ensure_ascii=False)
        print(f"-> wrote {args.out}", file=sys.stderr)
    if args.heartbeat_session:
        return _run_heartbeat_judge(
            session=args.heartbeat_session,
            out=args.heartbeat_out,
            dry_run=args.gate_only,
            no_log=args.no_log,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
