---
phase: 22-mascot-anticipation-layer-beat-coupled-hip-bob
artifact: spike-verdict
status: pending_kaan_measurement
created: 2026-05-14
spike_script: scripts/spike_gemini_text_ordering.py
spike_data: .planning/phases/22-mascot-anticipation-layer-beat-coupled-hip-bob/spike-data.csv
pitfall_ref: PITFALLS.md#21
gate: v2.0 anticipation does NOT depend on this verdict; verdict only gates v2.1 inline-emote-tag follow-up
---

verdict: pending_kaan_measurement

# Phase 22 Plan-01 — Gemini text-vs-audio channel-ordering spike

Per CONTEXT D-LOCKED (Pitfall 21): the v2.1 inline emote-tag direction
(`<lean_in/>`, `<surprise/>`) is viable only if Gemini's text channel
arrives BEFORE the TTS audio chunks via `livekit-plugins-google`. This
plan ships the instrumentation harness; the measurement step requires
Kaan running the script during a Phase 16 DJ ear-test session.

## How to run (Kaan-action-required)

1. Start djay Pro with a normal techno set audible (BlackHole routed).
2. `export GEMINI_API_KEY=...` (already in `.env`).
3. From repo root: `.venv/bin/python scripts/spike_gemini_text_ordering.py --turns 10`
4. Let the script complete ≥10 reaction turns (~3-5 min wall clock).
5. Confirm `spike-data.csv` has ≥10 rows with non-empty
   `text_first_emit_at` + `audio_first_chunk_at`.
6. Inspect median `text_minus_audio_ms`. Negative = text first.
7. Update the `verdict:` header above to one of:
   - `verdict: text-first +<delta>ms`
   - `verdict: audio-first +<delta>ms`
   - `verdict: inconclusive`
8. Flip `status: pending_kaan_measurement` → `status: measured`.

> The real-run path in `scripts/spike_gemini_text_ordering.py` is
> intentionally a stub — the LiveKit listener attachment must match the
> `livekit-plugins-google` version pinned at run time. The contract is
> documented in the script's `_run_real()` docstring; Kaan completes the
> wiring against the live session at measurement time.

## Result (fill after measurement)

| Stat | Value |
| ---- | ----- |
| Turns recorded / p25 / p50 / p75 / p95 ms | TBD |
| text_first_rate | TBD |
| Audible sample rate | TBD |
| Net jitter observed | TBD |

Evidence: `spike-data.csv` (committed alongside post-measurement).

## Verdict thresholds (locked in spike script)

- `text_first_rate ≥ 0.8` → **verdict: text-first**. v2.1 inline emote-tag
  vocab path opens. One-paragraph design sketch: extend the AICoach
  system-instruction grammar slot in `src/vibemix/agent/persona.py` to
  declare a tag vocabulary (`<lean_in/>`, `<surprise/>`, `<settle/>`)
  emitted in the model text channel; the sidecar parses tags from the
  `conversation_item_added` stream and fires `ipc.mascot.anticipate`
  ahead of the playout queue's first audio frame.
- `text_first_rate ≤ 0.2` → **verdict: audio-first** (Pitfall 21 confirmed).
  Inline emote-tag path **DEFERRED indefinitely**. Anticipation stays
  event-detector-driven only (`EventDetector.detect()` → `ipc.mascot.anticipate`
  at T+50ms).
- otherwise → **verdict: inconclusive**. Treat as audio-first for shipping
  purposes. Inline emote-tag path **DEFERRED indefinitely** pending a
  re-run on a future Gemini Live build.

## Recommendation for downstream plans (regardless of verdict)

**v2.0 ships event-detector-driven anticipation only** — per CONTEXT D-LOCKED,
Plans 22-02 and 22-03 (the anticipation fire-path + crossfade scenarios)
do NOT depend on this verdict. The verdict only gates whether the v2.1
inline-tag follow-up is on the roadmap.

Memory cross-ref: `feedback_no_scope_creep_clean_utility` — inline emote-tags
are a v2.1 polish; v2.0 hits the "minimum useful surface" bar without them.
