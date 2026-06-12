#!/usr/bin/env python3
"""Mechanical judged-pool replay of the working-tree live-claim guards.

The instrument behind the "free Sven" architecture (2026-06-12): for every
judged Sven line in the cadence pools, reconstruct MusicState + guard inputs
from the recorded invocation prompt and run the exact boundary disposition
``dj_cohost`` applies — ``apply_live_claim_guard`` (ladder + event-witness)
with band-intensity as telemetry — then report holds split by judge verdict.

Keeper = the judge liked the line (min(friend, grounded, earned) >= 2);
holding one is the false-positive cost this architecture drives to zero.
Fabrication = judge-flagged; the hard guards must keep catching those.

Reconstruction parses the machine evidence tokens recorded in each
invocation's prompt.txt (hearing[...], mixer_context[...], recent_moves,
move_effect_context, "Live deltas: ..."), cross-checked against the
claim_policy[...] token the live process recorded at prompt time — a
mismatch marks the row low-confidence. Unrecoverable fields (vocal_active,
track_history, audio_capture_context) run as ABSENT.

Usage:
    PYTHONPATH=src python3 scripts/eval/guard_pool_replay.py [--out report.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from vibemix.state.music_state import MusicState  # noqa: E402
from vibemix.state.deck_state import DeckState, DeckTrack  # noqa: E402
from vibemix.state import deck_context as dc  # noqa: E402

POOL_RUNS: tuple[str, ...] = tuple(
    f"{family}-{lane}-r{n}"
    for family in (
        "baseline-cadence",
        "lever-cadence",
        "lever2-cadence",
        "lever3-cadence",
        "replay-iter7",
    )
    for lane in ("audio", "midi")
    for n in (1, 2, 3)
)
EVAL_RUNS_DIR = REPO / ".planning" / "eval-runs"

HEARING_RE = re.compile(
    r"hearing\[rms=([\d.]+) sub=([\d.]+) low=([\d.]+) mid=([\d.]+) high=([\d.]+) bpm=([\d.]+)\]"
)
TRACK_RE = re.compile(r"\| track='([^']*)'")
DECK_RE = re.compile(r"\| deck=(\S+)")
RESOLVED_RE = re.compile(r"resolved=(\S+) unresolved=(\S+)")
CONTROLLER_CONN_RE = re.compile(r"controller_connection=(\w+)")
MIXER_RE = re.compile(
    r"mixer_context\[connected=(\w+) xfader=(\S+).*?decks="
    r"A\(vol=(\S+) low=(\S+) mid=(\S+) hi=(\S+) filter=(\S+) play=(\w+)\) \| "
    r"B\(vol=(\S+) low=(\S+) mid=(\S+) hi=(\S+) filter=(\S+) play=(\w+)\)",
    re.S,
)
RECENT_MOVES_RE = re.compile(r"recent_moves\[8s\]:\s*([^\n|]*)")
MOVE_ITEM_RE = re.compile(r"([\d.]+)s ago\s+(.+)")
MOVE_EFFECT_RE = re.compile(r"move_effect_context\[[^\]]*?deltas=(.*?)\s+(?:license=|rule=)", re.S)
LIVE_DELTAS_RE = re.compile(r"Live deltas:\s*(.*?)(?:\.\s+(?:Energy arc|Phrase read)|\.\")", re.S)
DELTA_ITEM_RE = re.compile(
    r"((?:sub|low|mid|high) energy (?:rose|fell) \d+% \((?:slight|clear|strong)\)"
    r"|brightness share (?:rose|fell) \d+% \((?:slight|clear|strong)\)"
    r"|onset density (?:rose|fell) \d+% \((?:slight|clear|strong)\)"
    r"|RMS (?:rose|fell) \d+% \((?:slight|clear|strong)\)"
    r"|loudness (?:rose|fell) \d+ LU \((?:slight|clear|strong)\))"
)
CLAIM_POLICY_RE = re.compile(r"claim_policy\[policy=(\w+)")

KNOB = {"killed": 4, "deep-cut": 20, "cut": 40, "flat": 64, "boost": 90, "max": 110}
VOL = {"closed": 4, "low": 30, "mid": 64, "open": 100, "full": 120}
XFADER = {"full-A": 8, "A-side": 30, "center": 64, "B-side": 100, "full-B": 120}

CANNED_HELD_REPLIES: tuple[str, ...] = (
    dc.LIVE_TRANSITION_HELD_REPLY,
    dc.LIVE_CANDIDATE_HELD_REPLY,
    dc.LIVE_MOVE_EFFECT_HELD_REPLY,
    dc.LIVE_COACHING_ADVICE_HELD_REPLY,
    dc.LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY,
    dc.LIVE_TRACK_IDENTITY_HELD_REPLY,
    dc.LIVE_JUDGE_OVERPRAISE_HELD_REPLY,
    dc.LIVE_SPECTRAL_CLAIM_HELD_REPLY,
    dc.LIVE_EVENT_WITNESS_HELD_REPLY,
)


def load_pool_rows() -> list[dict]:
    """Build the judged-line pool from the checked-in cadence runs."""
    rows: list[dict] = []
    for run in POOL_RUNS:
        judge_path = EVAL_RUNS_DIR / run / "judge.json"
        if not judge_path.exists():
            continue
        judge = json.loads(judge_path.read_text(encoding="utf-8"))
        prompt_paths = {
            p.parent.name: p
            for p in (EVAL_RUNS_DIR / run).glob(
                "*/home/Library/Application Support/vibemix/recordings/*/invocations/*/prompt.txt"
            )
        }
        for row in judge.get("rows", []):
            scores = row.get("scores") or {}
            triple = (
                scores.get("friend_not_narrator"),
                scores.get("grounded_not_fabricated"),
                scores.get("earned_not_constant"),
            )
            ok = None
            if all(isinstance(v, (int, float)) for v in triple):
                ok = min(triple) >= 2
            prompt_path = prompt_paths.get(row.get("id"))
            rows.append(
                {
                    "run": run,
                    "id": row.get("id"),
                    "event": row.get("event"),
                    "line": row.get("line") or "",
                    "ok": ok,
                    "friend": scores.get("friend_not_narrator"),
                    "why": scores.get("why"),
                    "prompt_path": str(prompt_path) if prompt_path else None,
                }
            )
    return rows


def build_fixture(prompt_text: str):
    """Return (state, moves, audio_delta_items, recorded_policy, notes)."""
    t = prompt_text
    notes: list[str] = []
    st = MusicState()

    m = HEARING_RE.search(t)
    if m:
        rms, sub, low, mid, high, bpm = map(float, m.groups())
        st.rms = rms
        st.bands = {"sub": sub, "low": low, "mid": mid, "high": high}
        st.bpm = bpm
        st.audible = rms >= 0.01
    else:
        notes.append("no_hearing_line")

    m = TRACK_RE.search(t)
    if m:
        st.audible_track = m.group(1)
        st.audible_track_confidence = 0.8
    m = DECK_RE.search(t)
    if m and m.group(1) in ("A", "B", "mix"):
        st.audible_deck = m.group(1)

    m = CONTROLLER_CONN_RE.search(t)
    st.controller_connected = bool(m and m.group(1) == "connected")

    m = MIXER_RE.search(t)
    if m:
        (
            _conn, xf,
            a_vol, a_low, a_mid, a_hi, a_filt, a_play,
            b_vol, b_low, b_mid, b_hi, b_filt, b_play,
        ) = m.groups()
        st.xfader = XFADER.get(xf, 64)
        st.deck_a = {
            "vol": VOL.get(a_vol, 64), "eq_low": KNOB.get(a_low, 64),
            "eq_mid": KNOB.get(a_mid, 64), "eq_hi": KNOB.get(a_hi, 64),
            "filter": KNOB.get(a_filt, 64), "play": a_play == "on",
        }
        st.deck_b = {
            "vol": VOL.get(b_vol, 64), "eq_low": KNOB.get(b_low, 64),
            "eq_mid": KNOB.get(b_mid, 64), "eq_hi": KNOB.get(b_hi, 64),
            "filter": KNOB.get(b_filt, 64), "play": b_play == "on",
        }
    elif st.controller_connected:
        notes.append("controller_connected_but_no_mixer_context")

    # deck_source_context's `unresolved=A+B` is synthesized controller
    # reference, NOT deck_state.decks entries; in these pools resolved=none
    # everywhere and the recorded claim_policy proves decks was empty live.
    decks: dict[str, DeckTrack] = {}
    m = RESOLVED_RE.search(t)
    if m and m.group(1) != "none":
        notes.append(f"resolved_decks_present:{m.group(1)}")
    st.deck_state = DeckState(decks=decks)

    moves: list[str] = []
    m = RECENT_MOVES_RE.search(t)
    if m and not m.group(1).strip().startswith("NONE"):
        for chunk in re.split(r",\s+(?=[\d.]+s ago)", m.group(1).strip()):
            mi = MOVE_ITEM_RE.match(chunk.strip())
            if mi:
                age, label = float(mi.group(1)), mi.group(2).strip()
                moves.append(label)
                st.recent_moves.append((age, label))
    moves = list(reversed(moves))[-3:]
    st.recent_moves = list(st.recent_moves)

    m = MOVE_EFFECT_RE.search(t)
    if m:
        st.move_audio_delta = DELTA_ITEM_RE.findall(m.group(1))

    m = LIVE_DELTAS_RE.search(t)
    if m:
        audio_delta_items = DELTA_ITEM_RE.findall(m.group(1))
    else:
        audio_delta_items = DELTA_ITEM_RE.findall(t)[:4]
    st.audio_delta = list(audio_delta_items)

    m = CLAIM_POLICY_RE.search(t)
    recorded_policy = m.group(1) if m else None

    return st, tuple(moves), audio_delta_items, recorded_policy, notes


def replay(rows: list[dict]) -> dict:
    """Run the boundary disposition over every row; return the report."""
    per_policy: dict[str, dict] = defaultdict(lambda: {
        "keeperHolds": 0, "keeperExamples": [], "fabricationHolds": 0,
        "fabricationExamples": [], "nullHolds": 0, "lowConfidence": 0,
        "emitCorrected": 0, "strip": 0,
    })
    policy_mismatch: list[tuple] = []
    observation_rows = 0
    canned_speakable: list[str] = []
    rows_out: list[dict] = []
    totals = {"keeper": 0, "fabrication": 0, "null": 0}

    for row in rows:
        if not row["prompt_path"]:
            continue
        prompt_text = Path(row["prompt_path"]).read_text(encoding="utf-8", errors="replace")
        st, moves, deltas, recorded_policy, notes = build_fixture(prompt_text)

        computed_policy, _ = dc.live_claim_policy(
            st, moves, audio_capture_context=None,
            audio_delta_items=deltas, deck_audio_parts_attached=False,
        )
        low_conf = bool(notes)
        if recorded_policy and computed_policy != recorded_policy:
            low_conf = True
            policy_mismatch.append((row["run"], row["id"], recorded_policy, computed_policy))

        # The exact boundary disposition (dj_cohost): guard verdict routes on
        # `speakable`; band-intensity and ladder observations are telemetry.
        res = dc.apply_live_claim_guard(
            row["line"], st, moves,
            audio_delta_items=deltas,
            audio_capture_context=None,
            deck_audio_parts_attached=False,
            judge_evidence_line=None,
            event_type=row["event"],
            offered_evidence_text=dc.extract_offered_evidence_text(prompt_text),
        )
        if res.observations:
            observation_rows += 1
        if res.speakable and any(c in res.text for c in CANNED_HELD_REPLIES):
            canned_speakable.append(row["line"])

        held = res.corrected
        action = None
        if held:
            action = "emit_corrected" if res.emit_corrected else "strip"
        ok = row["ok"]
        rows_out.append({
            "run": row["run"], "id": row["id"], "ok": ok,
            "held": held, "policy": res.policy if held else None,
            "reason": res.reason if held else None, "action": action,
            "observations": list(res.observations),
            "low_conf": low_conf, "line": row["line"], "why": row.get("why"),
            "friend": row.get("friend"),
        })
        if not held:
            continue
        bucket = per_policy[res.policy]
        bucket["emitCorrected" if action == "emit_corrected" else "strip"] += 1
        if low_conf:
            bucket["lowConfidence"] += 1
        if ok is True:
            totals["keeper"] += 1
            bucket["keeperHolds"] += 1
            if len(bucket["keeperExamples"]) < 3:
                bucket["keeperExamples"].append(row["line"])
        elif ok is False:
            totals["fabrication"] += 1
            bucket["fabricationHolds"] += 1
            if len(bucket["fabricationExamples"]) < 3:
                bucket["fabricationExamples"].append(row["line"])
        else:
            totals["null"] += 1
            bucket["nullHolds"] += 1

    # A trim (emit_corrected) keeps the model's words and SPEAKS — only
    # terminal silence counts as a silenced keeper.
    silenced_keepers = sum(
        1 for r in rows_out
        if r["held"] and r["action"] == "strip" and r["ok"] is True
    )
    n_keeper = sum(1 for r in rows if r["ok"] is True)
    n_fab = sum(1 for r in rows if r["ok"] is False)
    return {
        "pool": {
            "rows": len(rows), "keepers": n_keeper, "fabrications": n_fab,
            "null": len(rows) - n_keeper - n_fab,
        },
        "policy_mismatches": policy_mismatch,
        "per_policy": {k: dict(v) for k, v in sorted(per_policy.items())},
        "totals": {
            "held": sum(totals.values()),
            "keeperHolds": totals["keeper"],
            "silencedKeepers": silenced_keepers,
            "fabricationHolds": totals["fabrication"],
            "nullHolds": totals["null"],
            "observationRows": observation_rows,
            "cannedSpeakable": canned_speakable,
        },
        "rows": rows_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(EVAL_RUNS_DIR / "guard-pool-replay" / "report.json"),
        help="report JSON path",
    )
    args = parser.parse_args()

    rows = load_pool_rows()
    if not rows:
        print("no judged pool rows found under .planning/eval-runs/", file=sys.stderr)
        return 2
    report = replay(rows)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1), encoding="utf-8")

    t = report["totals"]
    print(f"pool: {report['pool']['rows']} rows "
          f"({report['pool']['keepers']} keepers / {report['pool']['fabrications']} fabrications)")
    print(f"policy cross-check mismatches: {len(report['policy_mismatches'])}")
    print(f"TOTAL HELD: {t['held']}  (keepers {t['keeperHolds']} "
          f"[silenced {t['silencedKeepers']}], fabrications {t['fabricationHolds']}, "
          f"null {t['nullHolds']})  observations on {t['observationRows']} spoken rows")
    fmt = "%-38s %8s %8s %6s %6s"
    print(fmt % ("policy", "keepHold", "fabHold", "emit", "strip"))
    for pol, b in report["per_policy"].items():
        print(fmt % (pol, b["keeperHolds"], b["fabricationHolds"],
                     b["emitCorrected"], b["strip"]))
    for pol, b in report["per_policy"].items():
        for ex in b["keeperExamples"]:
            print(f"  [keeper held by {pol}] {ex[:140]}")
    if t["cannedSpeakable"]:
        print(f"!! CANNED TEXT SPEAKABLE on {len(t['cannedSpeakable'])} rows")
    print(f"report -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
