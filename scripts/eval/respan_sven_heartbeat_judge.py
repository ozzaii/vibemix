#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Respan-powered Sven LIVE-line judge — measures the bench's BLIND SPOT.

The offline blind-judge bench (`src/vibemix/bench/`) is a generate-and-score
harness: it forces a line every tick, so it STRUCTURALLY cannot measure the #1
remaining voice failure — "should Sven have spoken at all?" (idle-HEARTBEAT
describe-bank filler). This tool judges Sven's ACTUAL spoken lines from a real
recorded session, on the live model via the Respan gateway, on the 5 product
dims PLUS a `should_speak` verdict — producing a decision-grade number:
*what fraction of real spoken lines should have been silence.*

This is the "make Sven good" gradient on real data (NOT a slop-blocker): it
tells us which dim is starved and quantifies the speak-gate's value. It is the
Respan **Lane A** deliverable (offline/recorded data, no privacy gate) and the
template for **Lane B** (the same judge run online on live text-only spans).

INPUT: a vibemix recordings session's `invocations/<NNNN_TS_EVENT>/` dirs, each
with `meta.json` (event/deck/track/phase/rms/bpm/...) + `response.txt` (the
spoken line). We build the evidence digest from `meta.json` ONLY (no persona /
prompt leakage into the judge) and judge the line blind.

Respan: generation+judge go through the gateway `POST /api/chat/completions`
using the model derived from the central live-coach router, each judge call
logged to `/api/request-logs/create` with a dataset tag. Key is read from
`RESPAN_API_KEY` (env ONLY — never written).

Usage:
    export RESPAN_API_KEY=...   # env only
    python3 scripts/eval/respan_sven_heartbeat_judge.py \
        --session "/Users/ozai/Library/Application Support/vibemix/recordings/20260602-075843" \
        --events HEARTBEAT --limit 40 --concurrency 4

    # offline (no network) — assemble + print the judge rows, prove the pairing:
    python3 scripts/eval/respan_sven_heartbeat_judge.py --session <dir> --dry-run

    # local no-payload describe-bank census — event type only, no event.extra replay:
    python3 scripts/eval/respan_sven_heartbeat_judge.py \
        --session <dir> --events ALL --describe-bank-census --dry-run
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
from pathlib import Path

import httpx  # vibemix core dep; run via `uv run python …`

from vibemix.agent.tts_sanitizer import model_text_for_tts
from vibemix.llm.model_router import resolve_model
from vibemix.runtime.speak_gate import decide_speak_gate
from vibemix.state import Event, MusicState
from vibemix.state.deck_context import (
    LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY,
    LIVE_CANDIDATE_HELD_REPLY,
    LIVE_COACHING_ADVICE_HELD_REPLY,
    LIVE_JUDGE_OVERPRAISE_HELD_REPLY,
    LIVE_MOVE_EFFECT_HELD_REPLY,
    LIVE_TRACK_IDENTITY_HELD_REPLY,
    LIVE_TRANSITION_HELD_REPLY,
)

# The live-claim guard replaces an unproven outcome claim with one of these
# deterministic held replies and leaves emit_corrected=False (the shipped
# default), so the runtime SILENCES them — they never reach TTS. But the recorded
# `response.txt` still carries the substituted text, so a naive loader would grade
# a silenced safety substitution as a friend-0 "spoken" line and tank the score.
# Corpus-verified 2026-06-08: of 144 such guard events, 140 stripped (silenced),
# only 4 emitted. We import the canonical constants (not copies) so this set can
# never drift out of sync with the runtime's held replies.
SILENCED_GUARD_SUBSTITUTIONS = frozenset(
    {
        LIVE_TRANSITION_HELD_REPLY,
        LIVE_CANDIDATE_HELD_REPLY,
        LIVE_MOVE_EFFECT_HELD_REPLY,
        LIVE_COACHING_ADVICE_HELD_REPLY,
        LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY,
        LIVE_TRACK_IDENTITY_HELD_REPLY,
        LIVE_JUDGE_OVERPRAISE_HELD_REPLY,
    }
)


def is_silenced_guard_substitution(line: str) -> bool:
    """True when a recorded response is a guard-silenced held reply, not a spoken line."""
    return line.strip() in SILENCED_GUARD_SUBSTITUTIONS


def is_wordless_after_tts_strip(line: str) -> bool:
    """True when the runtime's TTS sanitizer reduces a recorded response to nothing.

    Measured 2026-06-10 (baseline-cadence-midi-r2): the model replied with a bare
    citation atom plus a period. The runtime strips citations before TTS and the
    wordless residue hits the <empty> (skip TTS) branch — the user never hears
    it — but ``response.txt`` still records the raw text, so a naive loader
    grades a silence as a friend-0 "spoken" line. Calls the canonical sanitizer
    (not a copy) so this can never drift from what the runtime actually speaks.
    """
    return not model_text_for_tts(line).strip()


def probe_capture_status(session: Path) -> str:
    """Return 'probe' | 'shipped' | 'unknown' for a recorded session.

    Probe / QA-set mode (``VIBEMIX_SVEN_PROBE_MODE`` / ``VIBEMIX_SVEN_QA_SET``)
    FORCES gated and guard-held lines to emit so an evaluator can score them — so
    a probe capture's spoken set is NOT the shipped spoken set, and friend /
    should-NOT over it reflect FORCED output, not what ships. ``session.json``
    self-declares this via ``sven_probe_mode`` (recorder >= 2026-06-08); older
    recordings predate the field and read 'unknown' (treat as probe-suspect — the
    whole pre-gate corpus was forced).
    """
    try:
        meta = json.loads((session / "session.json").read_text())
    except Exception:
        return "unknown"
    flag = meta.get("sven_probe_mode")
    if flag is True:
        return "probe"
    if flag is False:
        return "shipped"
    return "unknown"


def probe_caveat(status: str) -> str | None:
    """A loud one-line caveat when a capture's lines are not shipped speech."""
    if status == "shipped":
        return None
    what = "PROBE CAPTURE" if status == "probe" else "PROBE-STATUS UNKNOWN (legacy recording)"
    return (
        f"!! {what}: forced/held lines were recorded as spoken. friend / "
        "should_NOT here reflect FORCED output, NOT the shipped spoken set — do "
        "not read these as shipped quality. Use bench_sim_gemini.py for shipped reality."
    )


RESPAN_BASE = "https://api.respan.ai/api"
GATEWAY = f"{RESPAN_BASE}/chat/completions"
LOG_ENDPOINT = f"{RESPAN_BASE}/request-logs/create"  # SDK base_url bug → call directly via httpx


def _respan_gateway_model() -> str:
    """Return the Respan model id derived from the central live-coach route."""

    routed = resolve_model("live_coach_openrouter")
    return routed.replace("google/", "gemini/", 1)


JUDGE_MODEL = _respan_gateway_model()

# The 5 product dims (verbatim intent from CODEX_READY-SVEN-PROMPT-BENCH-MEASURED)
# + a should_speak verdict (the bench's structural blind spot). Positive framing.
JUDGE_SYSTEM = """You are a blind judge grading ONE line spoken by Sven, an AI DJ co-host that rides in the booth with a DJ during a live set. You see the EVIDENCE Sven had and the LINE he spoke. Grade only the line.

Sven's job is to COACH, not narrate: every time he speaks he should hand the DJ one move, one read, or one forward-nudge. The DJ is the one playing the music — he already hears it, so describing the sound back to him ("a metallic synth dominated the high end") is the core failure (describe-bank). Silence is a valid and often correct output: on an idle tick with no real move and nothing actionable, the right move is to say NOTHING.

Score each dimension 0-3. USE THE FULL RANGE — a line that buries a real coaching point under narration is NOT a 0, it's a 1 or 2. Reserve 0 for lines with truly nothing of that dimension.
- friend_not_narrator: 0=pure sound-narration, no takeaway. 1=mostly narration with a weak/buried point. 2=gives a usable move/read but leads with or mixes in narration. 3=clean coaching, hands one move/read/nudge, no narration.
- grounded_not_fabricated: 0=invents a move/deck/track the evidence doesn't show. 1=partly unsupported. 2=mostly backed. 3=every specific backed (a cited real recent_moves entry IS grounded).
- earned_not_constant: 0=filler, tells him nothing he doesn't already hear. 1=marginal. 2=worth saying. 3=clearly worth interrupting for.
- move_specific_not_spectrum: 0=vague spectrum/sound only. 1=names sound specifics only. 2=names a real move or a concrete direction. 3=a specific, actionable next step.
- voice_no_slop: 0=generic AI narration/slop. 1=stiff. 2=mostly natural. 3=sounds like a real DJ friend in the ear.

Also judge:
- should_speak (true/false): given the evidence, would a sharp DJ friend have said THIS at all, or stayed silent? Describe-bank with no actionable point = false.

Return ONLY compact JSON, no prose:
{"friend_not_narrator":N,"grounded_not_fabricated":N,"earned_not_constant":N,"move_specific_not_spectrum":N,"voice_no_slop":N,"should_speak":true|false,"why":"<=12 words"}"""

DIMS = [
    "friend_not_narrator",
    "grounded_not_fabricated",
    "earned_not_constant",
    "move_specific_not_spectrum",
    "voice_no_slop",
]

QUALITY_MEAN_THRESHOLDS = {
    "friend_not_narrator": 2.0,
    "grounded_not_fabricated": 2.4,
    "earned_not_constant": 2.0,
    "voice_no_slop": 2.0,
}


DESCRIBE_BANK_CENSUS_CAVEAT = (
    "No recorded event.extra payloads are reconstructed; this is a no-payload "
    "describe-bank census, not a full live gate replay."
)


def describe_bank_census(rows: list[dict]) -> tuple[list[dict], dict]:
    """Filter recorded spoken rows through the no-payload describe-bank gate.

    This replays the event type from recorded invocation metadata. It does not
    reconstruct old ``event.extra`` payloads, so it is intentionally best for
    no-payload describe-bank burns where the event type itself was the failure.
    """

    kept: list[dict] = []
    silenced: list[dict] = []
    silenced_by_event: dict[str, int] = {}
    for row in rows:
        event_type = str(row.get("event") or "")
        decision = decide_speak_gate(Event(event_type, MusicState(), extra={}))
        row["describe_bank_census"] = {
            "verdict": decision.verdict,
            "reason": decision.reason,
            "caveat": DESCRIBE_BANK_CENSUS_CAVEAT,
        }
        if decision.verdict == "speak":
            kept.append(row)
        else:
            silenced.append(row)
            silenced_by_event[event_type] = silenced_by_event.get(event_type, 0) + 1
    summary = {
        "input_spoken_rows": len(rows),
        "kept_for_judge": len(kept),
        "silenced_by_describe_bank_census": len(silenced),
        "silenced_by_event": dict(sorted(silenced_by_event.items())),
        "payload_caveat": DESCRIBE_BANK_CENSUS_CAVEAT,
    }
    return kept, summary


def census_silence_summary(report: dict, *, min_rows: int) -> dict:
    """Return a no-network gate summary for replay rows that should not hit TTS."""

    input_rows = int(report.get("input_spoken_rows") or 0)
    kept = int(report.get("kept_for_judge") or 0)
    silenced = int(report.get("silenced_by_describe_bank_census") or 0)
    failures: list[str] = []
    if input_rows < min_rows:
        failures.append(f"input spoken rows {input_rows} below minimum {min_rows}")
    if kept:
        failures.append(f"kept_for_judge {kept} > 0")
    if silenced != input_rows:
        failures.append(f"silenced {silenced} != input spoken rows {input_rows}")
    return {
        "pass": not failures,
        "input_spoken_rows": input_rows,
        "kept_for_judge": kept,
        "silenced_by_describe_bank_census": silenced,
        "min_rows": min_rows,
        "failures": failures,
    }


# The evidence Sven ACTUALLY had is the leading bracket bundle in prompt.txt
# line 1 (hearing/track/deck/recent_moves/grounding_refs). meta.json omits
# recent_moves, so a meta-only digest would mis-score a line that cites a REAL
# move as fabricated. Parse the real bundle; fall back to meta if no prompt.
_HEARING_RE = re.compile(r"hearing\[[^\]]*\]")
_RECENT_MOVES_RE = re.compile(r"recent_moves\[8s\]:[^|]*")
_TRACK_RE = re.compile(r"[\s|]track=([^\s|]+)")
_DECK_RE = re.compile(r"[\s|]deck=([^\s|]+)")


def evidence_digest(meta: dict, prompt_text: str | None = None) -> str:
    """Faithful digest of what Sven was actually fed (no persona leakage).

    Prefers the real evidence bundle (prompt.txt line 1) so a line citing a
    genuine ``recent_moves`` entry is judged grounded, not fabricated. Falls
    back to meta.json fields (move-state then unknown) if prompt.txt is absent.
    """
    ev = meta.get("event", "?")
    if prompt_text and prompt_text.strip():
        line = prompt_text.lstrip().splitlines()[0]
        hearing = _HEARING_RE.search(line)
        moves = _RECENT_MOVES_RE.search(line)
        track_m = _TRACK_RE.search(line)
        deck_m = _DECK_RE.search(line)
        bits = [f"Event: {ev}."]
        if hearing:
            bits.append(hearing.group(0) + ".")
        bits.append(
            f"track={track_m.group(1) if track_m else 'unknown'}, "
            f"deck={deck_m.group(1) if deck_m else 'none'}."
        )
        bits.append(
            (moves.group(0).strip().rstrip("|").strip() + ".")
            if moves
            else "recent_moves[8s]: none."
        )
        bits.append("Sven's ears = 6s master mix (global, not deck stems).")
        return " ".join(bits)
    # Fallback: meta fields only; do NOT assert move-state we cannot see.
    deck = meta.get("deck") or "none"
    track = meta.get("track") or "unknown"
    phase = meta.get("phase") or "?"
    rms, bpm = meta.get("rms"), meta.get("bpm")
    return (
        f"Event: {ev}. deck={deck}, track={track}, phase={phase}, "
        f"rms={rms}, bpm={bpm}. recent_moves unknown (no prompt). "
        "Ears = 6s master mix."
    )


def load_rows(session: Path, events: set[str], limit: int | None) -> list[dict]:
    inv = session / "invocations"
    rows: list[dict] = []
    silent = 0
    for d in sorted(inv.iterdir()):
        if not d.is_dir():
            continue
        meta_p, resp_p = d / "meta.json", d / "response.txt"
        if not meta_p.exists() or not resp_p.exists():
            continue
        try:
            meta = json.loads(meta_p.read_text())
        except Exception:
            continue
        if events and meta.get("event") not in events:
            continue
        line = resp_p.read_text().strip()
        if not line:
            silent += 1  # already-silent: the system chose silence here
            continue
        if is_silenced_guard_substitution(line):
            # Guard-silenced held reply: the shipped runtime substituted this
            # deterministic safety line and did NOT speak it (emit_corrected=False).
            # Judging it as a spoken line scores a silence as friend-0 slop.
            silent += 1
            continue
        if is_wordless_after_tts_strip(line):
            # Bare-citation reply: TTS strips it to nothing, never spoken.
            silent += 1
            continue
        if meta.get("suppression") and not meta.get("head_yielded"):
            # The runtime recorded its own suppression decision (slop /
            # silence / stale / non_english) — the dump keeps the original
            # text, but the turn never reached TTS (2026-06-11 panel,
            # instrument-honesty finding). head_yielded turns stay judged:
            # a speculative head that already reached TTS was partially
            # HEARD, and the instrument must never hide a heard line.
            silent += 1
            continue
        prompt_p = d / "prompt.txt"
        prompt_text = prompt_p.read_text(errors="ignore") if prompt_p.exists() else None
        rows.append(
            {
                "id": d.name,
                "event": meta.get("event"),
                "line": line,
                "digest": evidence_digest(meta, prompt_text),
                "citation_action": meta.get("citation_action"),
                "diet": meta.get("diet"),
            }
        )
    print(f"-> {len(rows)} spoken lines to judge; {silent} already-silent (skipped) "
          f"for events={sorted(events) or 'ALL'}", file=sys.stderr)
    if limit:
        rows = rows[:limit]
    return rows


def _post(url: str, payload: dict, key: str, timeout: float = 60.0) -> tuple[int, dict | str]:
    # Pin scheme+host so a dynamic/hijacked url can never reach the client
    # (the endpoints are module constants today); httpx is https here.
    if not url.startswith(f"{RESPAN_BASE}/"):
        raise ValueError(f"refusing non-Respan URL: {url!r}")
    try:
        r = httpx.post(
            url, json=payload, timeout=timeout,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text[:300]
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def judge_one(row: dict, key: str, dataset_tag: str, do_log: bool) -> dict:
    user = f"EVIDENCE:\n{row['digest']}\n\nLINE SVEN SPOKE:\n\"{row['line']}\""
    status, resp = _post(
        GATEWAY,
        {
            "model": JUDGE_MODEL,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": 900,  # leave room for the judge JSON after thinking budget
            "response_format": {"type": "json_object"},
        },
        key,
    )
    out = {"id": row["id"], "event": row["event"], "line": row["line"], "status": status}
    if status != 200 or not isinstance(resp, dict):
        out["error"] = resp if not isinstance(resp, dict) else "non-200"
        return out
    content = ((resp.get("choices") or [{}])[0].get("message", {}) or {}).get("content") or ""
    try:
        scores = json.loads(content)
    except Exception:
        # tolerate code-fenced / trailing text
        s, e = content.find("{"), content.rfind("}")
        scores = json.loads(content[s:e + 1]) if s >= 0 and e > s else {}
    out["scores"] = scores
    if do_log:
        _post(
            LOG_ENDPOINT,
            {
                "model": JUDGE_MODEL,
                "prompt_messages": [{"role": "user", "content": user}],
                "completion_message": {"role": "assistant", "content": content},
                "category": dataset_tag,
                "custom_identifier": row["id"],
                "metadata": {
                    "event": row["event"],
                    "should_speak": scores.get("should_speak"),
                    "citation_action": row.get("citation_action"),
                    **{d: scores.get(d) for d in DIMS},
                },
            },
            key,
        )
    return out


def _score_value(scores: dict, dim: str) -> float | None:
    value = scores.get(dim)
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:
        return None
    return parsed


def _scored_results(results: list[dict]) -> list[dict]:
    return [
        row
        for row in results
        if isinstance(row.get("scores"), dict)
        and _score_value(row["scores"], "friend_not_narrator") is not None
    ]


def _dim_means(results: list[dict]) -> dict[str, float]:
    scored = _scored_results(results)
    if not scored:
        return {}
    return {
        dim: round(
            sum(_score_value(row["scores"], dim) or 0.0 for row in scored) / len(scored),
            2,
        )
        for dim in DIMS
    }


def quality_summary(
    results: list[dict],
    *,
    min_judged: int,
    errors: int | None = None,
) -> dict:
    scored = _scored_results(results)
    means = _dim_means(results)
    should_not_speak = sum(
        1 for row in scored if row.get("scores", {}).get("should_speak") is False
    )
    failures = quality_failures(
        results,
        means=means,
        min_judged=min_judged,
        errors=errors,
        should_not_speak=should_not_speak,
    )
    return {
        "judged": len(scored),
        "min_judged": min_judged,
        "errors": errors,
        "dim_means": means,
        "should_NOT_have_spoken": should_not_speak,
        "failures": failures,
    }


def quality_failures(
    results: list[dict],
    *,
    means: dict[str, float] | None = None,
    min_judged: int = 1,
    errors: int | None = None,
    should_not_speak: int | None = None,
) -> list[str]:
    failures: list[str] = []
    scored = _scored_results(results)
    if len(scored) < min_judged:
        failures.append(f"judged rows {len(scored)} below minimum {min_judged}")
    if errors:
        failures.append(f"judge errors {errors} > 0")
    means = means if means is not None else _dim_means(results)
    if not means:
        failures.append("no judged dim means")
    else:
        for dim, threshold in QUALITY_MEAN_THRESHOLDS.items():
            value = means.get(dim)
            if value is None or value < threshold:
                failures.append(f"mean {dim} {value!r} below {threshold:g}")
    if should_not_speak is None:
        should_not_speak = sum(
            1 for row in scored if row.get("scores", {}).get("should_speak") is False
        )
    if should_not_speak:
        failures.append(f"should_NOT_have_spoken {should_not_speak} > 0")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, type=Path)
    ap.add_argument("--events", default="HEARTBEAT", help="comma list or ALL")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dataset-tag", default="sven-heartbeat-real-set")
    ap.add_argument(
        "--require-quality",
        action="store_true",
        help=(
            "exit nonzero unless judged real lines clear friend/earned/voice >= 2, "
            "grounded >= 2.4, no judge errors, and no should_speak=false rows"
        ),
    )
    ap.add_argument(
        "--min-judged",
        type=int,
        default=1,
        help="minimum judged rows required when --require-quality is set",
    )
    ap.add_argument(
        "--describe-bank-census",
        action="store_true",
        help=(
            "score only rows the no-payload describe-bank census would still allow; "
            "does not reconstruct event.extra payloads"
        ),
    )
    ap.add_argument(
        "--require-census-silence",
        action="store_true",
        help=(
            "with --describe-bank-census, exit nonzero unless every input spoken "
            "row is suppressed before TTS; no network required"
        ),
    )
    ap.add_argument(
        "--min-census-rows",
        type=int,
        default=1,
        help="minimum input spoken rows required for --require-census-silence",
    )
    ap.add_argument("--dry-run", action="store_true", help="assemble rows, no network")
    ap.add_argument("--no-log", action="store_true", help="judge but do not log to Respan")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    events = set() if args.events.upper() == "ALL" else {e.strip() for e in args.events.split(",")}
    rows = load_rows(args.session, events, args.limit)
    if not rows:
        print("no rows", file=sys.stderr)
        return 1
    describe_bank_report = None
    if args.describe_bank_census:
        rows, describe_bank_report = describe_bank_census(rows)
        if args.require_census_silence:
            describe_bank_report["census_silence"] = census_silence_summary(
                describe_bank_report,
                min_rows=args.min_census_rows,
            )
        print(
            "-> describe-bank census (no event.extra payload replay): "
            f"{describe_bank_report['silenced_by_describe_bank_census']} silenced, "
            f"{describe_bank_report['kept_for_judge']} kept",
            file=sys.stderr,
        )
        print(
            f"-> caveat: {describe_bank_report['payload_caveat']}",
            file=sys.stderr,
        )
        if not rows:
            print(json.dumps({"describe_bank_census": describe_bank_report}, indent=2))
            if args.out:
                args.out.write_text(
                    json.dumps(
                        {"report": {"describe_bank_census": describe_bank_report}, "rows": []},
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                print(f"-> wrote {args.out}", file=sys.stderr)
            if args.require_census_silence:
                failures = describe_bank_report["census_silence"]["failures"]
                if failures:
                    print("census silence gate: FAIL", file=sys.stderr)
                    for failure in failures:
                        print(f"  - {failure}", file=sys.stderr)
                    return 1
                print("census silence gate: PASS")
                return 0
            if args.require_quality and args.min_judged > 0:
                print("quality gate: FAIL", file=sys.stderr)
                print(f"  - judged rows 0 below minimum {args.min_judged}", file=sys.stderr)
                return 1
            return 0

    if args.dry_run:
        for r in rows[:8]:
            print(f"\n[{r['id']}] ({r['event']})\n  EVIDENCE: {r['digest']}\n  LINE: {r['line']}")
        if describe_bank_report is not None:
            print(json.dumps({"describe_bank_census": describe_bank_report}, indent=2))
        print(f"\n(dry-run) {len(rows)} rows ready; no network.", file=sys.stderr)
        if args.require_census_silence and describe_bank_report is not None:
            failures = describe_bank_report["census_silence"]["failures"]
            if failures:
                print("census silence gate: FAIL", file=sys.stderr)
                for failure in failures:
                    print(f"  - {failure}", file=sys.stderr)
                return 1
            print("census silence gate: PASS")
            return 0
        if args.require_quality:
            print("--require-quality needs judged rows; dry-run cannot prove quality", file=sys.stderr)
            return 1
        return 0

    key = os.environ.get("RESPAN_API_KEY")
    if not key:
        print("RESPAN_API_KEY not set (env only)", file=sys.stderr)
        return 2

    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(judge_one, r, key, args.dataset_tag, not args.no_log) for r in rows]
        for i, f in enumerate(concurrent.futures.as_completed(futs), 1):
            results.append(f.result())
            if i % 10 == 0:
                print(f"  judged {i}/{len(rows)}", file=sys.stderr)

    ok = [r for r in results if isinstance(r.get("scores"), dict) and "friend_not_narrator" in r["scores"]]
    no_parse = [r for r in results if isinstance(r.get("scores"), dict) and "friend_not_narrator" not in r["scores"]]
    errs = [r for r in results if "scores" not in r] + no_parse
    n = len(ok)
    if n:
        means = {d: round(sum(float(r["scores"].get(d, 0) or 0) for r in ok) / n, 2) for d in DIMS}
        should_speak_false = sum(1 for r in ok if r["scores"].get("should_speak") is False)
        report = {
            "session": str(args.session),
            "events": sorted(events) or "ALL",
            "judged": n,
            "errors": len(errs),
            "judge_no_parse": len(no_parse),
            "dim_means": means,
            "should_NOT_have_spoken": should_speak_false,
            "should_NOT_have_spoken_pct": round(100 * should_speak_false / n, 1),
            "worst_lines": sorted(
                ({"id": r["id"], "line": r["line"], "why": r["scores"].get("why"),
                  "friend": r["scores"].get("friend_not_narrator")} for r in ok),
                key=lambda x: (x["friend"] if isinstance(x["friend"], (int, float)) else 9),
            )[:8],
        }
        if describe_bank_report is not None:
            report["describe_bank_census"] = describe_bank_report
        report["quality"] = quality_summary(results, min_judged=args.min_judged, errors=len(errs))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if args.out:
            args.out.write_text(json.dumps({"report": report, "rows": ok}, indent=2, ensure_ascii=False))
            print(f"-> wrote {args.out}", file=sys.stderr)
        if args.require_quality:
            failures = list(report["quality"].get("failures") or [])
            if failures:
                print("quality gate: FAIL", file=sys.stderr)
                for failure in failures:
                    print(f"  - {failure}", file=sys.stderr)
                return 1
            print("quality gate: PASS")
    else:
        print(json.dumps({"judged": 0, "errors": len(errs), "sample_err": errs[:2]}, indent=2))
        if args.require_quality:
            print("quality gate: FAIL", file=sys.stderr)
            print("  - no judged rows", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
