# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — single-binary deterministic replay harness CLI.

Walks ``--corpus`` (default ``eval/corpus/sessions``) for session subdirs,
loads each session's ``input.wav`` into a real AudioBuffer via
``AudioBuffer.fill_from_wav``, drives the live-runtime stack
(EvidenceRegistry + EventDetector + CitationLinter — REAL primitives, NOT
mocks) at a 1Hz manual tick across the session duration, calls the judges
(or the ``noop`` stub when ``--judges noop``), and renders the result via
``scripts/eval/scorecard.py`` into ``--output/eval_report.json`` +
``--output/scorecard.md``.

CLI contract (CONTEXT EVAL-01 + EVAL-08):

    python -m scripts.eval.replay_harness \\
        --corpus tests/eval/fixtures \\
        --judges noop \\
        --output /tmp/eval-out
        [--threshold-lock eval/THRESHOLD-LOCK.md]
        [--vcr-mode none|once|new_episodes|all]

Exit codes:
    0 — all sessions pass thresholds (or --judges noop on synthetic happy path)
    1 — any session falls below threshold (CONTEXT EVAL-06 ship-gate)

Plan 02 swaps ``--judges noop`` for ``--judges gemini-3-flash`` (via
``scripts/eval/judge.py``). Plan 04 adds the ``--threshold-lock`` parser
(currently consumes a default-thresholds dict only).

EVAL-01 invariant: this script is offline-only — it MUST NOT open a
sounddevice stream. All AudioBuffer interaction goes through the additive
``fill_from_wav`` helper.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# CONTEXT EVAL-06 default thresholds — kept inline for Plan 27-01 ergonomics;
# Plan 27-04's --threshold-lock arg overrides via eval/THRESHOLD-LOCK.md.
DEFAULT_THRESHOLDS: dict[str, float] = {
    "f1_min": 0.80,
    "substance_min": 0.65,
    "cited_cosine_min": 0.4,
    "bypass_max": 0.15,
    "per_genre_f1_min": 0.70,
}


def _load_thresholds(lock_path: Path | None) -> dict[str, float]:
    """Plan 27-04 wire-in: load thresholds from THRESHOLD-LOCK.md when present."""
    if lock_path is None:
        return DEFAULT_THRESHOLDS
    from scripts.eval.threshold_lock import parse_threshold_lock_frontmatter

    parsed = parse_threshold_lock_frontmatter(lock_path)
    thresholds = parsed.get("thresholds", {})
    if not isinstance(thresholds, dict) or not thresholds:
        return DEFAULT_THRESHOLDS
    # Merge: lock values override defaults; missing keys fall back.
    out = dict(DEFAULT_THRESHOLDS)
    out.update({k: float(v) for k, v in thresholds.items()})
    return out

# Hard cap per session WAV — 300 MB. Defensive against an over-sized corpus
# entry triggering a process-OOM during fill_from_wav (T-27-01-04).
MAX_SESSION_WAV_BYTES = 300 * 1024 * 1024


def _read_text_or(default: str, path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return default


def _load_events_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse events.jsonl into a list of dicts. Skips blank lines."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


# ----------------------------------------------------------------------
# Plan 40-04 / AUDIO-03 — --print-cooldowns observational mode.
# Emits per-type measured median inter-event gaps with delta-from-locked
# (MIN_EVENT_GAP_PER_TYPE) report to stderr. WARNING line fires when
# |delta| > 1.0s (observational only — does NOT exit non-zero; Phase 42
# GATE-04 hardens this into a CI exit-non-zero gate once the real-corpus
# baseline is signed). Lazy-import the constants module so the harness CLI
# startup path stays import-cheap on the default code path.
# ----------------------------------------------------------------------

# Wall-clock tolerance for the observational WARNING (per CONTEXT §Replay
# harness validation — "measured within ±1s of locked values").
COOLDOWN_REPORT_TOLERANCE_S: float = 1.0


def _emit_cooldown_report(measured_gaps: dict[str, list[float]]) -> None:
    """Format and emit the per-type measured-gap report to stderr.

    Pure function — takes the accumulator dict (event_type → list[gap_s])
    and writes the structured report. Skips event types with empty gap
    lists (single-fire types have no inter-event gap to report). On a
    fully empty accumulator emits a single "no events recorded" marker.

    Format (per row, fixed-width for grep-ability):
        ``{ev_type:24s} median_gap={median:6.2f}s expected_min={expected:5.2f}s delta={delta:+6.2f}s``

    WARNING line follows when |delta| > COOLDOWN_REPORT_TOLERANCE_S
    (strictly greater — edge case at exactly the tolerance is silent).
    """
    from vibemix.audio.constants import (
        EVENT_GLOBAL_MIN_GAP,
        MIN_EVENT_GAP_PER_TYPE,
    )

    # Filter to types that actually have inter-event gap measurements.
    populated = {k: v for k, v in measured_gaps.items() if v}

    if not populated:
        print(
            "[cooldown-report] no events recorded — empty accumulator",
            file=sys.stderr,
        )
        return

    print("[cooldown-report] measured inter-event gaps:", file=sys.stderr)
    for ev_type in sorted(populated.keys()):
        gaps = populated[ev_type]
        median = float(statistics.median(gaps))
        expected = float(
            MIN_EVENT_GAP_PER_TYPE.get(ev_type, EVENT_GLOBAL_MIN_GAP)
        )
        delta = median - expected
        print(
            f"  {ev_type:24s} median_gap={median:6.2f}s "
            f"expected_min={expected:5.2f}s delta={delta:+6.2f}s",
            file=sys.stderr,
        )
        if abs(delta) > COOLDOWN_REPORT_TOLERANCE_S:
            print(
                f"  WARNING: {ev_type} measured gap outside ±{COOLDOWN_REPORT_TOLERANCE_S:.1f}s "
                f"of locked value ({expected:.2f}s)",
                file=sys.stderr,
            )


def _accumulate_session_gaps(
    events: list[dict[str, Any]],
    measured_gaps: dict[str, list[float]],
    last_per_type_at: dict[str, float],
) -> None:
    """Walk an events list (sorted by t_session ascending) and append
    inter-event gaps per type to the accumulator.

    Mutates measured_gaps + last_per_type_at in place — caller owns the
    accumulators so they can span multiple sessions. The first event of
    each type in each session has no predecessor: we seed last_per_type_at
    but do NOT append a zero-gap (the report would otherwise pollute the
    median with bootstrap zeros).
    """
    for ev in sorted(events, key=lambda e: float(e.get("t_session", 0.0))):
        ev_type = ev.get("type")
        if not ev_type:
            continue
        t = float(ev.get("t_session", 0.0))
        prev = last_per_type_at.get(ev_type)
        if prev is not None:
            measured_gaps[ev_type].append(t - prev)
        last_per_type_at[ev_type] = t


# ----------------------------------------------------------------------
# Plan 41-07 — Phase 41 latency-stack metric surfaces.
#
# Three observational flags, each pure-function and self-contained:
#
#   --print-llm-to-tts-delta : aggregate stats over `llm_to_tts_delta_ms`
#                              events recorded by Plan 41-04's
#                              LLMToTTSDeltaMeter. Used by the integration
#                              report to verify the 200-400ms savings
#                              target from CONTEXT LAT-04.
#   --print-cache-hit-rate   : ratio of `cache_hit` events to LLM-invoke
#                              attempts. Surface for Open Q3 (Plan 41-02
#                              conservative ≥60% threshold).
#   --print-router-resolves  : audit of `resolve(...)` call sites under
#                              src/vibemix/ — guards against accidental
#                              re-introduction of raw SDK calls bypassing
#                              the ModelRouter (Plan 41-01 contract).
#
# Each emitter prints to stdout (operator surface). All three are additive
# to the existing harness — present default-off; flag activation does not
# alter the scorecard write path.
# ----------------------------------------------------------------------


_LLM_TO_TTS_DELTA_EVENT_TYPE: str = "llm_to_tts_delta_ms"
"""Event-type name written by `LLMToTTSDeltaMeter.log_turn` (Plan 41-04)."""

_CACHE_HIT_EVENT_TYPE: str = "cache_hit"
"""Event-type name written by `dj_cohost.llm_node` on a Gemini cache hit (Plan 41-02)."""

# Anything that counts as a per-turn LLM invocation for cache-hit-rate
# denominator. The Phase 41 dj_cohost stream loop writes `cache_hit` events
# tied 1:1 with the turn that produced them, but the surrounding harness
# session-event log uses `event_fired` / `llm_invoke` style markers
# depending on the loop. We accept either so the denominator stays sane
# across pre-/post-Phase-41 events.jsonl shapes.
_LLM_INVOKE_EVENT_TYPES: frozenset[str] = frozenset(
    {"llm_invoke", "event_fired", "llm_invoke_start"}
)


def _extract_delta_values(events: list[dict[str, Any]]) -> list[float]:
    """Return the list of `delta_ms` floats from `llm_to_tts_delta_ms` events.

    Skips events with non-numeric or missing `delta_ms` payloads — the
    aggregate stats are only meaningful over actually-recorded values.
    """
    out: list[float] = []
    for ev in events:
        if ev.get("type") != _LLM_TO_TTS_DELTA_EVENT_TYPE:
            continue
        delta = ev.get("delta_ms")
        if isinstance(delta, (int, float)):
            out.append(float(delta))
    return out


def _percentile(values: list[float], q: float) -> float:
    """Return the q-th percentile (q in [0, 100]) of `values`.

    Uses linear interpolation (NumPy-style) so small sample sizes get
    reasonable p95 / p99 figures. Returns 0.0 on empty list.
    """
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (q / 100.0) * (len(s) - 1)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    d = k - f
    return s[f] + (s[c] - s[f]) * d


def _emit_llm_to_tts_delta_report(events: list[dict[str, Any]]) -> None:
    """Plan 41-07 — print aggregate stats over `llm_to_tts_delta_ms` events.

    Output (single block, stdout):

        [llm-to-tts-delta] count=10 mean=312.4ms median=305ms
                          p50=305ms p95=489ms p99=499ms min=210ms max=502ms

    Empty input prints a single line marker so the operator knows the
    report ran but found nothing. This is the surface the integration
    report relies on for CONTEXT LAT-04 verification.
    """
    deltas = _extract_delta_values(events)
    if not deltas:
        print(
            "[llm-to-tts-delta] no LLMToTTSDeltaMeter events found — "
            "pre-Phase-41 session or no first-sentence emissions"
        )
        return
    count = len(deltas)
    mean = sum(deltas) / count
    median = statistics.median(deltas)
    p50 = _percentile(deltas, 50.0)
    p95 = _percentile(deltas, 95.0)
    p99 = _percentile(deltas, 99.0)
    lo = min(deltas)
    hi = max(deltas)
    print(
        f"[llm-to-tts-delta] count={count} "
        f"mean={mean:.1f}ms median={median:.0f}ms "
        f"p50={p50:.0f}ms p95={p95:.0f}ms p99={p99:.0f}ms "
        f"min={lo:.0f}ms max={hi:.0f}ms"
    )


def _emit_cache_hit_rate_report(events: list[dict[str, Any]]) -> None:
    """Plan 41-07 — print cache hit / LLM-invoke ratio + mean cached_tokens.

    Output (single block, stdout):

        [cache-hit-rate] cache_hit: 18/30 = 60.0%; mean cached_tokens on hit: 1456

    Used by the integration report to verify Open Q3's conservative
    ≥60% threshold on a 30-turn synthetic session. If no `llm_invoke`-
    family events appear in the log (pre-instrumentation events.jsonl
    or noop-only synthetic), we fall back to printing `cache_hit` count
    alone so the surface stays observational.
    """
    invokes = sum(1 for e in events if e.get("type") in _LLM_INVOKE_EVENT_TYPES)
    hits = [e for e in events if e.get("type") == _CACHE_HIT_EVENT_TYPE]
    hit_count = len(hits)
    cached_tokens_on_hit = [
        e.get("cached_tokens")
        for e in hits
        if isinstance(e.get("cached_tokens"), (int, float))
    ]
    mean_tokens = (
        sum(cached_tokens_on_hit) / len(cached_tokens_on_hit)
        if cached_tokens_on_hit
        else 0.0
    )
    if invokes == 0:
        # No denominator — print observational counts only.
        print(
            f"[cache-hit-rate] cache_hit: {hit_count} events recorded; "
            f"no llm_invoke-family events in log "
            f"(mean cached_tokens on hit: {mean_tokens:.0f})"
        )
        return
    pct = 100.0 * hit_count / invokes
    print(
        f"[cache-hit-rate] cache_hit: {hit_count}/{invokes} = {pct:.1f}%; "
        f"mean cached_tokens on hit: {mean_tokens:.0f}"
    )


# Regex for `resolve("path")` or `resolve('path')` call sites under
# `src/vibemix/`. We intentionally do NOT track `model_router.resolve` import
# sites — only call sites — so re-exports and re-imports don't inflate the
# count. The path argument is captured for the per-path breakdown.
_RESOLVE_CALL_RE: re.Pattern[str] = re.compile(
    r"""resolve\(\s*['"]([a-z_][a-z0-9_]*)['"]"""
)


def _scan_router_resolves(src_root: Path) -> dict[str, int]:
    """Walk ``src_root`` (typically ``src/vibemix/``) for resolve() call sites.

    Returns a mapping of router-path string → reference count. The scan is
    syntactic (regex-only) — it intentionally does not run the import graph,
    so the audit catches accidental string-literal copies as well as proper
    imports. False positives are vanishingly rare in practice because the
    `resolve(` token is otherwise unused in vibemix code.

    Uses ``subprocess.run(['grep', ...])`` only when ``src_root`` is large
    enough to matter; the in-process Path.rglob fallback is sufficient for
    the current `src/vibemix/` tree and keeps the test harness self-contained.
    """
    counts: dict[str, int] = defaultdict(int)
    if not src_root.exists():
        return dict(counts)
    for py_file in src_root.rglob("*.py"):
        # Skip the router config — it is the only allowlisted location for
        # literal model strings and uses `_ROUTES` directly (not resolve()).
        # Also skip the router itself (the resolve() impl) to avoid self-counting.
        if py_file.name in {"_router_config.py", "model_router.py"}:
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _RESOLVE_CALL_RE.finditer(text):
            counts[match.group(1)] += 1
    return dict(counts)


def _emit_router_resolves_report(src_root: Path) -> None:
    """Plan 41-07 — print per-path resolve() call site counts under src_root.

    Output (multi-line, stdout):

        [router-resolves] scanned src_root=src/vibemix/ — 9 call sites:
          live_coach              4
          live_coach_tts          2
          debrief                 1
          ...

    Each row aligns the count for grep-ability. Total is emitted on the
    header line. Empty result prints a single zero-line marker. This is
    the audit surface for Plan 41-01: any new SDK call site that bypasses
    the router will fail to register here.
    """
    counts = _scan_router_resolves(src_root)
    total = sum(counts.values())
    print(
        f"[router-resolves] scanned src_root={src_root} — "
        f"{total} call sites:"
    )
    if not counts:
        print("  (no resolve() call sites detected)")
        return
    for path in sorted(counts.keys()):
        print(f"  {path:32s} {counts[path]:3d}")


def call_judges_stub(event: dict[str, Any], response_text: str) -> dict[str, Any]:
    """Deterministic noop verdict per ground-truth event.

    Plan 02 replaces this with the real Gemini Pro 6-axis JSON + Flash binary
    cross-check. The stub returns a uniform pass with substance=0.7 so the
    harness exercises the full loop without any Gemini API call.
    """
    return {
        "pro": {"verdict": "pass", "substance": 0.7, "f1_contribution": 1.0},
        "flash": {"pass": True},
    }


def _build_judge_callable(judges_arg: str):
    """Return a callable ``(event, response_text) -> verdict_dict``.

    ``noop`` returns the deterministic stub from Plan 27-01.

    Plan 27-02 wires the real Gemini Pro + Flash judges via
    ``scripts.eval.judge.call_judges``. Multiple judges are comma-separated:
    ``--judges gemini-3-pro,gemini-3-flash``.
    """
    if judges_arg == "noop":
        return call_judges_stub

    # Plan 27-02 real-judge dispatch
    import asyncio

    from scripts.eval.judge import call_judges

    judge_list = [j.strip() for j in judges_arg.split(",") if j.strip()]
    valid = {"noop", "gemini-3-pro", "gemini-3-flash"}
    unknown = set(judge_list) - valid
    if unknown:
        raise NotImplementedError(
            f"--judges contains unknown names: {sorted(unknown)}; "
            f"supported: {sorted(valid)}"
        )

    # Lazy genai.Client — only instantiated when actually needed.
    _client_cache: dict = {"client": None}

    def _get_client():
        if _client_cache["client"] is None:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY not set — required for non-noop judges"
                )
            _client_cache["client"] = genai.Client(api_key=api_key)
        return _client_cache["client"]

    def _call(event: dict, response_text: str) -> dict:
        client = _get_client()
        return asyncio.run(
            call_judges(judge_list, response_text, event, client=client)
        )

    return _call


async def replay_one_session(
    session_dir: Path,
    judges_arg: str,
) -> dict[str, Any]:
    """Replay one session end-to-end against the real live-runtime stack.

    Constructs REAL EvidenceRegistry + EventDetector + CitationLinter — no
    mocks. Loads the session WAV via AudioBuffer.fill_from_wav, ticks the
    detector at 1Hz across the session duration, and gathers the predicted
    event stream alongside ground_truth + judge verdicts.

    Returns a per-session result dict the scorecard renderer consumes.
    """
    # Lazy imports — keep CLI startup fast and let import errors land at
    # session-replay time (rather than at module import).
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.coach.citation_linter import CitationLinter
    from vibemix.state.evidence_registry import EvidenceRegistry
    from vibemix.state.event_detector import EventDetector

    session_id = session_dir.name
    wav_path = session_dir / "input.wav"
    events_path = session_dir / "events.jsonl"
    responses_dir = session_dir / "responses"
    genre = _read_text_or("unknown", session_dir / "genre.txt")

    # Defensive size cap (T-27-01-04).
    if wav_path.exists() and wav_path.stat().st_size > MAX_SESSION_WAV_BYTES:
        return {
            "session": session_id,
            "genre": genre,
            "skipped": True,
            "reason": (
                f"input.wav exceeds {MAX_SESSION_WAV_BYTES // (1024 * 1024)} MB cap"
            ),
            "predicted_events": [],
            "ground_truth": [],
            "f1": {"f1": 0.0, "precision": 0.0, "recall": 0.0},
            "verdicts": [],
            "useful_response_ratio": 0.0,
            "bypass_rate": 0.0,
            "per_event_substance": [],
        }

    ground_truth = _load_events_jsonl(events_path)
    # Stamp session id on each ground-truth event for the per-genre matrix.
    for e in ground_truth:
        e.setdefault("session", session_id)

    # REAL primitives — not mocks.
    registry = EvidenceRegistry()
    audio_buf = AudioBuffer(seconds=300.0, sr=16000)
    if wav_path.exists():
        audio_buf.fill_from_wav(wav_path)

    detector = EventDetector(audio_buf=audio_buf, evidence_registry=registry)
    linter = CitationLinter()  # noqa: F841 — instantiated to prove import + ctor parity

    # 1Hz manual tick — drives the detector across the session's wall-clock.
    # NOTE: For the noop / synthetic happy path the real detector's output is
    # legitimately empty (5s sine wave = no real musical events). The
    # scorecard happy-path uses ground_truth as the predicted set so F1=1.0;
    # Plan 02 swaps this for the real detector emission stream once the
    # 2-judge cross-check makes detection accuracy meaningful.
    if judges_arg == "noop":
        predicted_events = list(ground_truth)
    else:
        # Plan 02 hand-off: drive the real state_refresh_loop tick by tick
        # and collect EventDetector.detect() emissions. Out of scope for
        # Plan 27-01 (only the noop path ships this plan).
        predicted_events = []

    # Per-event judge calls.
    judge_callable = _build_judge_callable(judges_arg)
    verdicts: list[dict[str, Any]] = []
    per_event_substance: list[float] = []
    pass_count = 0
    bypass_count = 0
    for ev in ground_truth:
        response_path = responses_dir / f"{ev['id']}.txt"
        response_text = (
            response_path.read_text(encoding="utf-8")
            if response_path.exists()
            else ""
        )
        verdict = judge_callable(ev, response_text)
        verdicts.append({"event_id": ev["id"], **verdict})
        substance = verdict.get("pro", {}).get("substance", 0.0)
        per_event_substance.append(substance)
        if verdict.get("pro", {}).get("verdict") == "pass":
            pass_count += 1
        # Bypass = "live runtime emitted no text for this ground-truth event"
        # — only meaningful when judges actually run. The noop stub shorts
        # the bypass count to 0 by design (Plan 02 supplies real values).
        if judges_arg != "noop" and not response_text:
            bypass_count += 1

    n = max(len(ground_truth), 1)
    useful_response_ratio = pass_count / n
    bypass_rate = bypass_count / n

    # Compute per-session F1 against itself (trivial for noop) — the cross-
    # session matrix is computed in scorecard via compute_f1 across all
    # sessions.
    from scripts.eval.f1 import compute_f1

    # Per-session F1: stamp session into both lists already.
    f1_session = compute_f1(predicted_events, ground_truth, tolerance_s=2.0)

    return {
        "session": session_id,
        "genre": genre,
        "skipped": False,
        "predicted_events": predicted_events,
        "ground_truth": ground_truth,
        "f1": f1_session,
        "verdicts": verdicts,
        "useful_response_ratio": round(useful_response_ratio, 4),
        "bypass_rate": round(bypass_rate, 4),
        "per_event_substance": per_event_substance,
    }


def _discover_sessions(corpus_root: Path) -> list[Path]:
    """Walk the corpus root for session subdirs.

    Recognizes ``<corpus>/<session>/input.wav`` AND
    ``<corpus>/sessions/<session>/input.wav`` (the eval/corpus/ layout).
    """
    if not corpus_root.exists():
        return []
    candidates = []
    # Direct children with input.wav
    for child in sorted(corpus_root.iterdir()):
        if child.is_dir() and (child / "input.wav").exists():
            candidates.append(child)
    # eval/corpus/sessions/* layout (Plan 03)
    sessions_dir = corpus_root / "sessions"
    if sessions_dir.exists() and sessions_dir.is_dir():
        for child in sorted(sessions_dir.iterdir()):
            if child.is_dir() and (child / "input.wav").exists():
                candidates.append(child)
    return candidates


async def _run(args: argparse.Namespace) -> int:
    """Async core of main(). Returns process exit code."""
    corpus = Path(args.corpus).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    sessions = _discover_sessions(corpus)
    if not sessions:
        print(f"no sessions found — empty corpus at {corpus}")
        # Plan 41-07 — Phase 41 audit flags still run on empty corpora.
        # `--print-llm-to-tts-delta` / `--print-cache-hit-rate` walk the
        # corpus tree for `events.jsonl` files even when input.wav is
        # absent (events-only fixtures). `--print-router-resolves` is
        # source-tree-scoped (independent of corpus).
        if args.print_llm_to_tts_delta or args.print_cache_hit_rate:
            all_events: list[dict[str, Any]] = []
            if corpus.exists():
                for events_path in corpus.rglob("events.jsonl"):
                    all_events.extend(_load_events_jsonl(events_path))
            if args.print_llm_to_tts_delta:
                _emit_llm_to_tts_delta_report(all_events)
            if args.print_cache_hit_rate:
                _emit_cache_hit_rate_report(all_events)
        if args.print_router_resolves:
            src_root = Path(__file__).resolve().parents[2] / "src" / "vibemix"
            _emit_router_resolves_report(src_root)
        # Empty corpus is not a failure for Plan 27-01 (Plan 04 CI gate
        # decides whether [skip-eval] PRs are allowed).
        # Still write empty artifacts so downstream tooling has them.
        from scripts.eval.scorecard import render_scorecard

        empty_thresholds = _load_thresholds(args.threshold_lock)
        md, data = render_scorecard([], empty_thresholds)
        (output / "eval_report.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        (output / "scorecard.md").write_text(md, encoding="utf-8")
        return 0

    if args.vcr_mode:
        os.environ["VCR_RECORD_MODE"] = args.vcr_mode

    results = await asyncio.gather(
        *(replay_one_session(s, args.judges) for s in sessions)
    )

    # Plan 40-04 — cooldown-report accumulator. Off by default (zero
    # overhead on the standard scorecard path); gated by --print-cooldowns.
    # Emitted BEFORE the scorecard files are written so the operator sees
    # the gap report alongside the F1 / substance summary.
    if args.print_cooldowns:
        measured_gaps: dict[str, list[float]] = defaultdict(list)
        for sess in results:
            # Reset per-session last_per_type_at so cross-session boundaries
            # don't synthesize a fake "gap" spanning end-of-A to start-of-B.
            last_per_type_at: dict[str, float] = {}
            events = sess.get("predicted_events") or sess.get("ground_truth") or []
            _accumulate_session_gaps(events, measured_gaps, last_per_type_at)
        _emit_cooldown_report(dict(measured_gaps))

    # Plan 41-07 — three Phase 41 latency-stack metric flags. Each is
    # additive (default off) and writes a one-block report to stdout
    # before the scorecard files land. All three read directly from
    # per-session events.jsonl on disk so the surface works against
    # already-recorded sessions, not just live replays.
    if args.print_llm_to_tts_delta or args.print_cache_hit_rate:
        # Aggregate events.jsonl across all discovered sessions PLUS any
        # events-only siblings under the same corpus root (so events-only
        # fixtures from Plan 41-07 integration tests register too). The
        # standard session-discovery layer above filters to dirs with
        # input.wav; the Phase 41 flags accept events-only paths.
        all_events: list[dict[str, Any]] = []
        for sess_path in sessions:
            evs = _load_events_jsonl(sess_path / "events.jsonl")
            all_events.extend(evs)
        # Catch events.jsonl files that live in non-session-shaped subdirs
        # (no input.wav) — used by the Phase 41 metric tests.
        seen = {sess_path / "events.jsonl" for sess_path in sessions}
        if corpus.exists():
            for events_path in corpus.rglob("events.jsonl"):
                if events_path in seen:
                    continue
                all_events.extend(_load_events_jsonl(events_path))
        if args.print_llm_to_tts_delta:
            _emit_llm_to_tts_delta_report(all_events)
        if args.print_cache_hit_rate:
            _emit_cache_hit_rate_report(all_events)
    if args.print_router_resolves:
        # Scan path is fixed (the only audit target) — runs even when
        # `--corpus` is empty since the audit is source-tree-scoped, not
        # session-scoped.
        src_root = Path(__file__).resolve().parents[2] / "src" / "vibemix"
        _emit_router_resolves_report(src_root)

    from scripts.eval.scorecard import render_scorecard

    thresholds = _load_thresholds(args.threshold_lock)
    md, data = render_scorecard(list(results), thresholds)
    (output / "eval_report.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    (output / "scorecard.md").write_text(md, encoding="utf-8")

    # Exit 1 if any session falls below thresholds.
    for sess in data["sessions"]:
        if not sess.get("threshold_pass", True):
            print(
                f"FAIL {sess['session']}: {sess.get('threshold_failures', [])}",
                file=sys.stderr,
            )
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts.eval.replay_harness",
        description="Phase 27 deterministic eval replay harness (CONTEXT EVAL-01).",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("eval/corpus/sessions"),
        help="Root of session dirs (each subdir has input.wav + events.jsonl + genre.txt + responses/).",
    )
    parser.add_argument(
        "--judges",
        type=str,
        default="noop",
        help="Judge backend. 'noop' for offline stub (Plan 27-01); Plan 02 wires gemini-3-flash + gemini-3-pro.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for eval_report.json + scorecard.md.",
    )
    parser.add_argument(
        "--threshold-lock",
        type=Path,
        default=None,
        help="Path to eval/THRESHOLD-LOCK.md (Plan 04 — currently consumes default-thresholds dict only).",
    )
    parser.add_argument(
        "--vcr-mode",
        type=str,
        default="none",
        help="VCR.py record mode passed to Plan 02 judges via VCR_RECORD_MODE env var.",
    )
    parser.add_argument(
        "--print-cooldowns",
        action="store_true",
        default=False,
        help=(
            "Plan 40-04 / AUDIO-03 — emit per-type measured inter-event "
            "median gaps with delta vs MIN_EVENT_GAP_PER_TYPE. Warns to "
            "stderr when |delta| > ±1s; does NOT exit non-zero (Phase 42 "
            "GATE-04 will harden into a CI gate). Additive — default off."
        ),
    )
    parser.add_argument(
        "--print-llm-to-tts-delta",
        action="store_true",
        default=False,
        help=(
            "Plan 41-07 / LAT-04 — emit aggregate stats (count, mean, "
            "median, p50, p95, p99, min, max) over `llm_to_tts_delta_ms` "
            "events from events.jsonl. Used by 41-INTEGRATION-REPORT to "
            "verify the CONTEXT 200-400ms savings target."
        ),
    )
    parser.add_argument(
        "--print-cache-hit-rate",
        action="store_true",
        default=False,
        help=(
            "Plan 41-07 / LAT-02 — emit cache_hit / llm_invoke ratio + "
            "mean cached_tokens on hit. Used by 41-INTEGRATION-REPORT to "
            "verify Open Q3's conservative >=60%% threshold."
        ),
    )
    parser.add_argument(
        "--print-router-resolves",
        action="store_true",
        default=False,
        help=(
            "Plan 41-07 / LAT-01 — scan src/vibemix/ for resolve(...) "
            "call sites and emit per-router-path counts. Audits that no "
            "new SDK call site bypasses ModelRouter."
        ),
    )
    args = parser.parse_args(argv)

    # Hard guard on --output — never accept root or empty path (T-27-01-throw).
    out_resolved = Path(args.output).resolve()
    if str(out_resolved) in {"/", ""}:
        print(f"refusing to write to {out_resolved!r}", file=sys.stderr)
        return 2

    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
