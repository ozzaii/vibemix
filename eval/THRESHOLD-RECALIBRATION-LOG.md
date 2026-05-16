# vibemix Threshold Recalibration Audit Trail

> Append-only log of every `scripts/eval/recalibrate_thresholds.py` run.
> See `.planning/phases/42-hallucination-gate-v3-hybrid/42-02-PLAN.md` for the
> contract; CONTEXT D-GATE-04 for the ±0.10 tolerance band rationale; and the
> Phase 27 re-tuning protocol for why this script **never** auto-edits
> `eval/THRESHOLD-LOCK.md`.

## Purpose

This log is the audit trail for every recalibration run against the real
corpus at `eval/corpus/sessions/`. The script records what was measured,
what the locked thresholds were at the time of measurement, and the
per-metric delta against the lock.

- **In-tolerance** (`|delta| ≤ 0.10`): an audit entry is appended; no
  further action. The locked thresholds remain valid.
- **Out-of-tolerance** (`|delta| > 0.10`): an audit entry is appended AND
  the script exits non-zero with a `RECALIBRATION_REQUIRED` flag. Re-locking
  is a deliberate human action — re-signing `eval/THRESHOLD-LOCK.md`
  autonomously is **FORBIDDEN** by the Phase 27-04 re-tuning protocol.

The CI nightly workflow (`.github/workflows/eval.yml --check-real-corpus`)
fails when this log carries no entry inside the last 30 days OR when
`eval/corpus/sessions/` has fewer than 6 populated sessions.

## Cross-References

- `scripts/eval/recalibrate_thresholds.py` — the driver that writes here.
- `eval/THRESHOLD-LOCK.md` — the locked values measured against.
- `scripts/eval/threshold_lock.py` — read-only parser of the lock frontmatter.
- `.planning/phases/42-hallucination-gate-v3-hybrid/42-02-PLAN.md` — the
  contract this file implements.
- Phase 27-04 re-tuning protocol (forbidding autonomous re-signing).

## Entry Schema

Every entry follows this shape exactly. The block header carries the
ISO8601-UTC timestamp and the corpus-level verdict; the bullets carry the
structured per-metric data.

```
### YYYY-MM-DDTHH:MM:SSZ — verdict={in_tolerance|out_of_tolerance}
- corpus: eval/corpus/sessions/ (N sessions, M genres)
- judges: gemini-3-flash, gemini-3-pro
- measured: f1=X.XX  substance=X.XX  cited_cosine=X.XX  bypass=X.XX
- locked:   f1=0.80  substance=0.65  cited_cosine=0.40  bypass=0.15
- delta:    f1=±X.XX substance=±X.XX cited_cosine=±X.XX bypass=±X.XX
- per-genre: hard_tek f1=X.XX  techno f1=X.XX  house f1=X.XX
- verdict: <in_tolerance | out_of_tolerance>
- action:  <none | RECALIBRATION_REQUIRED — re-sign THRESHOLD-LOCK.md after re-run>
```

## Audit Trail

### 1970-01-01T00:00:00Z — verdict=schema_example
- corpus: eval/corpus/sessions/ (0 sessions, 0 genres)
- judges: gemini-3-flash, gemini-3-pro
- measured: f1=0.00  substance=0.00  cited_cosine=0.00  bypass=0.00
- locked:   f1=0.80  substance=0.65  cited_cosine=0.40  bypass=0.15
- delta:    f1=+0.00 substance=+0.00 cited_cosine=+0.00 bypass=+0.00
- per-genre: (schema example — replace with real per-genre data)
- verdict: schema_example
- action:  none (this is a documentation placeholder, not a real run)

<!-- Real audit entries appended below by recalibrate_thresholds.py. -->
