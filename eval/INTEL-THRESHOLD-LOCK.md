---
schema: intel_threshold_lock_v1
status: fixture_locked
locked_at: "2026-05-27"
scope: musical-intelligence synthetic fixture scorecard
intel_thresholds:
  anlz_complete_rate_min: 0.70
  anlz_parse_error_rate_max: 0.00
  cue_exact_or_near_rate_min: 0.40
  section_role_hit_at_5_delta_min: 0.15
  section_mixable_window_hit_at_5_delta_min: 0.10
  section_low_confidence_result_rate_max: 0.15
  transition_accept_at_3_min: 0.80
  transition_pairwise_accuracy_min: 0.80
  transition_unknown_candidate_label_count_max: 0.00
  decision_validator_fallback_rate_max: 0.20
  decision_exact_timing_floor_violation_rate_max: 0.00
  gold_validation_error_count_max: 0.00
  taste_accepted_suggestion_lift_min: 0.10
  taste_consent_off_long_term_write_rate_max: 0.00
  taste_single_session_hard_negative_rate_max: 0.00
  taste_technical_bad_candidate_rescued_count_max: 0.00
  taste_profile_projection_privacy_leak_count_max: 0.00
  taste_unknown_preference_claim_rate_max: 0.00
---

# INTEL Threshold Lock

This lock is the executable threshold contract for the musical-intelligence
fixture gate:

```bash
uv run python scripts/eval/intel_gate.py \
  --fixture-dir tests/intel/fixtures \
  --threshold-lock eval/INTEL-THRESHOLD-LOCK.md \
  --output .planning/eval-runs/intel-gate.json \
  --summary-markdown .planning/eval-runs/intel-gate.md \
  --json
```

The gate runs fixture audit, locked scorecard, and provenance validation. The
persisted gate artifact includes metric values, gate statuses, artifact statuses,
and provenance hashes. The scorecard can still be run directly for metric
inspection; it exits non-zero when artifacts or gates fail:

```bash
uv run python scripts/eval/intel_scorecard.py \
  --fixture-dir tests/intel/fixtures \
  --threshold-lock eval/INTEL-THRESHOLD-LOCK.md \
  --json
```

It does **not** retune or replace `eval/THRESHOLD-LOCK.md`, which remains the
signed hallucination-gate lock for replay-harness metrics. This file exists so
INTEL gates can be enforced without editing the older signed lock or pretending
that fixture evidence is release-grade human calibration.

## Gate Groups

| Group | Thresholds |
|-------|------------|
| ANLZ structure | `anlz_complete_rate_min`, `anlz_parse_error_rate_max` |
| Smart cues | `cue_exact_or_near_rate_min` |
| Section retrieval | `section_role_hit_at_5_delta_min`, `section_mixable_window_hit_at_5_delta_min`, `section_low_confidence_result_rate_max` |
| Transition ranking | `transition_accept_at_3_min`, `transition_pairwise_accuracy_min`, `transition_unknown_candidate_label_count_max` |
| Decision runtime | `decision_validator_fallback_rate_max`, `decision_exact_timing_floor_violation_rate_max` |
| Gold labels | `gold_validation_error_count_max` |
| Taste learning | `taste_accepted_suggestion_lift_min`, consent/privacy/poisoning zero-tolerance counters |

## Calibration Status

These values are locked for the public synthetic fixture corpus only. They prove
that the INTEL eval machinery is wired, deterministic, privacy-safe, and capable
of catching regressions.

Release-grade thresholds still need private Kaan-reviewed evidence:

- section queries against real hardtechno/hard-tek library moments;
- transition pairs labeled `would_play`, `maybe`, and `no`;
- live/debrief decisions replayed with timing confidence;
- taste labels captured from actual accepted/rejected suggestions.

## Retuning Protocol

Changing any `intel_thresholds` value requires:

1. Re-run the gate command above and record the before/after scorecard metrics.
2. State whether the change is a fixture calibration, private-label calibration,
   or release-gate promotion.
3. For private-label calibration or release-gate promotion, append a redacted
   entry to `eval/INTEL-THRESHOLD-RECALIBRATION-LOG.md` with calibration,
   holdout, and canary split counts plus the measured/locked/delta values.
4. Keep zero-tolerance privacy and grounding counters at `0.00` unless the
   underlying contract changes in the corresponding INTEL spec.
5. Update `.planning/research/2026-05-27-intel-03-data-eval-excellence-spec.md`
   and `.planning/research/2026-05-27-intel-16-implementation-readiness-checklist.md`
   in the same PR.

Lowering thresholds to make a demo pass is not allowed.

## Audit Trail

- 2026-05-27: Created fixture-level INTEL threshold lock for the scorecard and
  `scripts/eval/intel_gate.py`; legacy `eval/THRESHOLD-LOCK.md` left untouched.
