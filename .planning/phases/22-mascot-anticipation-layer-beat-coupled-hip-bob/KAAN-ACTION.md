# KAAN-ACTION — Phase 22 Plan-01 measurement step

**Status:** open — blocks `verdict:` line in `WAVE-0-SPIKE.md`.
**Blocks:** nothing in v2.0 (per CONTEXT D-LOCKED — verdict only gates v2.1 inline-emote-tag follow-up).
**Owner:** Kaan (DJ ear-test session — Phase 16 workflow).

## What's deferred

The ≥10-turn real-run measurement against a live Gemini Live session +
djay Pro audible set. The harness + verdict math + report template are
all shipped (commits `2761d3e`, `c95732e`, this commit) — only the
measurement itself requires a human in the loop.

## What Claude shipped

- `scripts/spike_gemini_text_ordering.py` — instrumentation harness with
  `--dry-run` self-test mode + real-run skeleton. CLI: `--turns N`,
  `--out CSV-PATH`, `--timeout-s N`, `--synthetic-mode {text-first|audio-first|inconclusive}`.
- `tests/scripts/test_spike_gemini_text_ordering.py` — 13 unit tests pinning
  the CLI contract, CSV schema, summary stdout line, verdict math.
- `WAVE-0-SPIKE.md` — verdict report template with `status:
  pending_kaan_measurement` frontmatter. Just needs the `verdict:` line
  + stats table filled after the measurement run.

## What Kaan does

1. During the next Phase 16 DJ ear-test session, complete the LiveKit
   listener wiring inside `_run_real()` (the docstring spells the
   contract — three signals: `event_fire_at`, `text_first_emit_at`,
   `audio_first_chunk_at`).
2. Run: `.venv/bin/python scripts/spike_gemini_text_ordering.py --turns 10`
3. Observe ≥10 turns in `spike-data.csv`.
4. Update `WAVE-0-SPIKE.md` `verdict:` line + stats table + flip
   `status: pending_kaan_measurement` → `status: measured`.
5. Commit `spike-data.csv` + updated `WAVE-0-SPIKE.md` alongside.

## Why deferred

The LiveKit listener attachment must match the `livekit-plugins-google`
version pinned at measurement time — wiring it ahead of the session
risks pinning against a version that has since drifted. Per memory
`feedback_autonomous_no_grey_area_pause` this is surfaced as a
Kaan-action-required item, not a workflow block — v2.0 anticipation
work (Plans 22-02 / 22-03) is unblocked and can proceed.
