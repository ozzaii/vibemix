#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Plan 22-01 Task 1 — Gemini text-vs-audio channel-ordering spike harness.

Purpose
-------
Pitfall 21 mitigation. The Phase 22 mascot anticipation layer wants to lean
forward 400-1200ms BEFORE Gemini voice arrives so the AI feels predictive,
not reactive. The v2.1 inline emote-tag direction (``<lean_in/>``,
``<surprise/>``) is only viable if Gemini's TEXT channel emits before the
TTS audio chunks land in the LiveKit playout queue. This script measures
that ordering across ≥10 real reaction turns.

Modes
-----
``--dry-run``
    Synthetic mode. No Gemini round-trip, no LiveKit session. Emits N rows
    against a deterministic fake session and computes the verdict math
    locally. Used for harness self-tests (see
    ``tests/scripts/test_spike_gemini_text_ordering.py``).

real-run (no flag)
    Boots a minimal LiveKit AgentSession against the production Gemini
    Live RealtimeModel (cohost_v4 cascade settings; no UI, no mascot,
    no recorder side effects). Requires ``GEMINI_API_KEY`` in env +
    djay Pro audible via BlackHole. Kaan-action-required — runs during
    Phase 16 DJ ear-test sessions.

CSV schema
----------
``turn_idx, event_type, event_fire_at, text_first_emit_at,
audio_first_chunk_at, text_minus_audio_ms, sample_audible,
network_jitter_observed``

All timestamps are monotonic ``time.perf_counter()`` values (seconds since
session start). ``text_minus_audio_ms`` is the contract column: negative =
text arrives first (v2.1 emote-tag path opens); positive = audio arrives
first (emote-tag path stays deferred per Pitfall 21).

Verdict math
------------
* ``text_first_rate`` = fraction of rows with negative delta.
* ``text_first_rate ≥ 0.8`` → ``verdict: text-first``.
* ``text_first_rate ≤ 0.2`` → ``verdict: audio-first``.
* otherwise → ``verdict: inconclusive``.

This rule lives in this script and in WAVE-0-SPIKE.md verdict section.
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# 4-event burst spec'd in 22-01-PLAN.md Task 1. Order is deterministic so
# the dry-run rows are reproducible across CI runs.
EVENT_BURST = ("TRACK_CHANGE", "PHASE", "KAAN_SPOKE", "MANUAL")

# Verdict thresholds. Centralised so the dry-run synthetic verifier and the
# WAVE-0-SPIKE.md template stay in sync.
TEXT_FIRST_RATE_HIGH = 0.8  # ≥ this → verdict: text-first
TEXT_FIRST_RATE_LOW = 0.2  # ≤ this → verdict: audio-first

CSV_COLUMNS = [
    "turn_idx",
    "event_type",
    "event_fire_at",
    "text_first_emit_at",
    "audio_first_chunk_at",
    "text_minus_audio_ms",
    "sample_audible",
    "network_jitter_observed",
]


@dataclass
class TurnRecord:
    """One per reaction turn — written to CSV verbatim."""

    turn_idx: int
    event_type: str
    event_fire_at: float
    text_first_emit_at: float
    audio_first_chunk_at: float
    sample_audible: bool
    network_jitter_observed: bool

    @property
    def text_minus_audio_ms(self) -> float:
        return (self.text_first_emit_at - self.audio_first_chunk_at) * 1000.0

    def to_csv_row(self) -> dict[str, str]:
        return {
            "turn_idx": str(self.turn_idx),
            "event_type": self.event_type,
            "event_fire_at": f"{self.event_fire_at:.6f}",
            "text_first_emit_at": f"{self.text_first_emit_at:.6f}",
            "audio_first_chunk_at": f"{self.audio_first_chunk_at:.6f}",
            "text_minus_audio_ms": f"{self.text_minus_audio_ms:.3f}",
            "sample_audible": "true" if self.sample_audible else "false",
            "network_jitter_observed": "true" if self.network_jitter_observed else "false",
        }


def _cycle_events(turns: int) -> Iterator[str]:
    """Cycle the 4-event burst across N turns deterministically."""
    for i in range(turns):
        yield EVENT_BURST[i % len(EVENT_BURST)]


def _synth_turn(turn_idx: int, event_type: str, mode: str) -> TurnRecord:
    """Generate one synthetic turn record for ``--dry-run`` mode.

    The three synthetic modes match the verdict outcomes:
    * ``text-first``: text consistently leads audio by ~120ms.
    * ``audio-first``: audio consistently leads text by ~80ms (Pitfall 21).
    * ``inconclusive``: alternates sign per turn, near-zero median.
    * ``default`` (legacy alias for ``text-first``): used when no mode flag
      is passed — the dry-run default produces a passing verdict so the
      smoke check ``python3 scripts/spike_gemini_text_ordering.py --dry-run
      | grep -E "spike: [0-9]+ turns recorded"`` from 22-01-PLAN.md
      verifies the happy path.
    """
    # Anchor timestamps to a deterministic offset so test assertions on
    # row ordering are stable.
    event_fire_at = 0.500 + turn_idx * 30.0

    if mode == "audio-first":
        # Audio lands ~80ms before text — Pitfall 21 confirmed.
        audio_first_chunk_at = event_fire_at + 0.420
        text_first_emit_at = audio_first_chunk_at + 0.080
    elif mode == "inconclusive":
        # Alternate sign per turn — median near zero, mixed signs.
        if turn_idx % 2 == 0:
            text_first_emit_at = event_fire_at + 0.500
            audio_first_chunk_at = text_first_emit_at + 0.040
        else:
            audio_first_chunk_at = event_fire_at + 0.500
            text_first_emit_at = audio_first_chunk_at + 0.035
    else:
        # text-first (default). Text leads audio by ~120ms.
        text_first_emit_at = event_fire_at + 0.380
        audio_first_chunk_at = text_first_emit_at + 0.120

    return TurnRecord(
        turn_idx=turn_idx,
        event_type=event_type,
        event_fire_at=event_fire_at,
        text_first_emit_at=text_first_emit_at,
        audio_first_chunk_at=audio_first_chunk_at,
        # Synthetic mode does not observe BlackHole; mark false so the CSV
        # explicitly signals "this row did NOT see real audio".
        sample_audible=False,
        network_jitter_observed=False,
    )


def _compute_verdict(records: list[TurnRecord]) -> tuple[str, float, dict[str, float]]:
    """Return (verdict, median_text_minus_audio_ms, stats_dict).

    stats_dict keys: ``p25, p50, p75, p95, text_first_rate``.
    """
    deltas = [r.text_minus_audio_ms for r in records]
    if not deltas:
        return "inconclusive", 0.0, {"p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0, "text_first_rate": 0.0}

    sorted_d = sorted(deltas)

    def _pct(p: float) -> float:
        if len(sorted_d) == 1:
            return sorted_d[0]
        k = (len(sorted_d) - 1) * p
        f = int(k)
        c = min(f + 1, len(sorted_d) - 1)
        return sorted_d[f] + (sorted_d[c] - sorted_d[f]) * (k - f)

    text_first_rate = sum(1 for d in deltas if d < 0) / len(deltas)
    median = statistics.median(deltas)
    stats = {
        "p25": _pct(0.25),
        "p50": median,
        "p75": _pct(0.75),
        "p95": _pct(0.95),
        "text_first_rate": text_first_rate,
    }
    if text_first_rate >= TEXT_FIRST_RATE_HIGH:
        verdict = "text-first"
    elif text_first_rate <= TEXT_FIRST_RATE_LOW:
        verdict = "audio-first"
    else:
        verdict = "inconclusive"
    return verdict, median, stats


def _write_csv(out_path: Path, records: list[TurnRecord]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_csv_row())


def _run_dry(turns: int, mode: str, out_path: Path) -> int:
    records: list[TurnRecord] = []
    for idx, ev in enumerate(_cycle_events(turns)):
        records.append(_synth_turn(idx, ev, mode))
    _write_csv(out_path, records)
    verdict, median, stats = _compute_verdict(records)
    # Contract: 22-01-PLAN.md Task 1 verify-line:
    #   spike: N turns recorded, median text_minus_audio_ms=X.X
    print(
        f"spike: {len(records)} turns recorded, "
        f"median text_minus_audio_ms={median:.1f}"
    )
    print(
        f"verdict: {verdict} "
        f"(text_first_rate={stats['text_first_rate']:.2f}, "
        f"p25={stats['p25']:.1f}ms, p75={stats['p75']:.1f}ms, "
        f"p95={stats['p95']:.1f}ms)"
    )
    print(f"csv: {out_path}")
    return 0


def _run_real(
    turns: int, timeout_s: int, out_path: Path
) -> int:  # pragma: no cover — Kaan-action-required path
    """Real-run mode — boots a LiveKit AgentSession against Gemini Live.

    This path is gated on:
    1. ``GEMINI_API_KEY`` in env.
    2. djay Pro audible via BlackHole 2ch.
    3. ≥10 reaction turns observable (~3-5 min wall clock at 30s avg gap).

    The script reuses ``vibemix.state.EventDetector`` directly — it does NOT
    fork the production trigger pipeline. The instrumentation lives in
    side-channel listeners attached to the same AgentSession passed into
    ``vibemix.runtime.coach.coach_loop``:

    * ``session.on("conversation_item_added", _on_text)`` — records
      ``text_first_emit_at = time.perf_counter()`` on first text item per turn.
    * SpeechHandle audio playout start callback — records
      ``audio_first_chunk_at = time.perf_counter()`` on first audio frame
      hitting the LiveKit playout queue.
    * ``EventDetector.detect()`` return → records ``event_fire_at`` before
      ``session.generate_reply(...)`` is issued.

    Per-turn hard timeout = ``min(timeout_s, 6.0)`` to keep the spike loop
    tight — matches coach.py's 20s ``wait_for_playout`` cap but tighter.

    NOTE: This branch is INTENTIONALLY left as a stub. The full LiveKit
    wiring is out of scope for the spike harness skeleton — it must be
    completed by Kaan at the time of running against a real session so
    the listener attachment matches whatever livekit-plugins-google
    version is pinned at that moment. The skeleton above is the contract
    every implementation must satisfy.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "ERROR: real-run mode requires GEMINI_API_KEY in env. "
            "Re-run with --dry-run for harness self-test, or export "
            "GEMINI_API_KEY=... before running the spike.",
            file=sys.stderr,
        )
        return 2
    print(
        "ERROR: real-run LiveKit wiring is Kaan-action-required (see "
        "WAVE-0-SPIKE.md 'How to run' section). The dry-run harness is "
        "shipped; the real-run path is intentionally left as a stub to "
        "be completed against the live djay Pro + Gemini Live session "
        "(Phase 16 ear-test workflow). Use --dry-run for now.",
        file=sys.stderr,
    )
    # Touch unused args so linters don't flag them — they're contract-level.
    _ = (turns, timeout_s, out_path)
    return 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spike_gemini_text_ordering",
        description=(
            "Phase 22 Task 1 spike — measure whether Gemini text channel "
            "arrives before TTS audio chunks via livekit-plugins-google. "
            "Real-run mode requires GEMINI_API_KEY + djay Pro audible. "
            "Use --dry-run for harness self-test."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Synthetic mode — no Gemini round-trip. Emits N rows against a deterministic fake session.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of reaction turns to record (default: 10; Plan 22-01 requires ≥10).",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=600,
        help="Real-run total wall-clock budget in seconds (default: 600 = 10 min). No-op in --dry-run.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            ".planning/phases/22-mascot-anticipation-layer-beat-coupled-hip-bob/spike-data.csv"
        ),
        help="CSV output path (default: phase-22 spike-data.csv).",
    )
    parser.add_argument(
        "--synthetic-mode",
        choices=("text-first", "audio-first", "inconclusive"),
        default="text-first",
        help="Dry-run-only — which synthetic outcome to emit (default: text-first).",
    )
    args = parser.parse_args(argv)

    if args.turns < 1:
        print("ERROR: --turns must be ≥ 1", file=sys.stderr)
        return 2

    if args.dry_run:
        return _run_dry(args.turns, args.synthetic_mode, args.out)
    return _run_real(args.turns, args.timeout_s, args.out)


if __name__ == "__main__":
    sys.exit(main())
