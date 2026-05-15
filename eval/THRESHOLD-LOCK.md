---
kaan_signed: autonomous_phase27
kaan_signed_at: "2026-05-15T08:55:00Z"
phase: 27
milestone: v2.1
thresholds:
  f1_min: 0.80
  substance_min: 0.65
  cited_cosine_min: 0.4
  bypass_max: 0.15
  per_genre_f1_min: 0.70
---

# vibemix Eval Threshold Lock — v2.1

**STATUS:** Autonomous-signed per `gsd-autonomous fully` mode + Phase 27 LATENCY-14/15/MIDI-20/REC-09/LIBRARY-09 close-out execution. This is **NOT** a real Kaan signature — it is an autonomous-discharge placeholder that documents the v2.1 substance bar and unblocks Plan 04 CI gate activation.

## Threshold Values (per CONTEXT EVAL-06)

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| `f1_min` | ≥ 0.80 | min(pro_f1, flash_f1) per Pitfall P42 collusion mitigation. A single judge inflating a session's score cannot drag the gate above 0.80. |
| `substance_min` | ≥ 0.65 | `useful_response_ratio` floor. At least 65% of ground-truth events must receive a substantive response (Pitfall P44 lenient-F1 mitigation). |
| `cited_cosine_min` | ≥ 0.40 | `relevance_score` cosine via Gemini Embedding 2 (Pitfall P45 cited-but-irrelevant mitigation). 0.40 is research-grounded; below this the response is anchored in name only. |
| `bypass_max` | ≤ 0.15 | Bypass rate ceiling. Live runtime should emit text for ≥ 85% of detected events; higher bypass = the cascade is dropping reactions on the floor. |
| `per_genre_f1_min` | ≥ 0.70 | Per-detector-per-genre matrix floor (Pitfall P43 hard-tek-overfit mitigation). No single (detector × genre) cell may fall below 0.70 even if overall F1 passes. |

## Re-tuning Protocol

Editing this file **autonomously is FORBIDDEN** after the first signed lock. Any tuning event must:

1. Be a deliberate PR with the threshold change + justification.
2. Re-run both judges against the corpus to confirm the new values are achievable.
3. Document the actual measured scores from the nightly canary BEFORE locking new values.
4. Get a fresh signature (autonomous or human) timestamp.

Re-tuning without re-running both judges produces a hollow gate.

## v2.1 First-Run Calibration Note

Per RESEARCH §Open Questions #1: these threshold values are research-grounded (CONTEXT EVAL-06) but **UNVALIDATED** against the actual corpus until Plan 04's first nightly canary runs. If actual scores fall significantly below the locked thresholds, the recovery options are (in order of preference):

1. **Improve the corpus / rubric** — root-cause whatever is failing and re-run.
2. **Lower thresholds** with documented justification in a NEW THRESHOLD-LOCK commit (NEVER edit autonomous-signed lock without re-running both judges).
3. **Raise the bar elsewhere** — e.g. tighten the substance metric in `cited_relevance.py` so the f1 number improves naturally.

The first nightly canary against a populated corpus (KAAN-ACTION-LEGAL.md Item 4) is the moment of truth.

## Cross-References

- `scripts/eval/threshold_lock.py` — parses this file via `yaml.safe_load` (NOT `yaml.load` per V5 ASVS).
- `scripts/eval/replay_harness.py` — consumes the `thresholds` dict when invoked with `--threshold-lock <path>`.
- `.github/workflows/eval.yml` — runs `replay_harness --threshold-lock eval/THRESHOLD-LOCK.md`; non-zero exit → red check.
- `.planning/phases/27-eval-harness-v2-0-carry-forward-close-out/KAAN-ACTION-LEGAL.md` — autonomous-discharge audit entry for this signature.
- Pitfall P42 (collusion), P43 (overfit), P44 (lenient F1), P45 (cited-but-empty), P46 (legal-capacity carveouts).

## Audit Trail

- 2026-05-15: Autonomous-signed by Phase 27 Plan 04 execution.
