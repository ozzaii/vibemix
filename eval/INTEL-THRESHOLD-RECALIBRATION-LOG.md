<!-- SPDX-License-Identifier: Apache-2.0 -->

# INTEL Threshold Recalibration Log

> Append-only, redacted audit trail for private-label calibration of
> `eval/INTEL-THRESHOLD-LOCK.md`.

## Purpose

`eval/INTEL-THRESHOLD-LOCK.md` is currently fixture-locked. It proves the
musical-intelligence machinery is wired and regression-sensitive, but it does
not claim release-grade musical taste. Release-grade INTEL thresholds must be
fed by private Kaan-reviewed labels without committing private audio, local
paths, raw vectors, raw label notes, track titles, or session identifiers.

This file is the public, redacted note for that private evidence. It records
which evidence tier was used, which splits were covered, what the locked values
were, what the measured values were, and what action was taken.

## Evidence Tiers

| Tier | Meaning | Can retune fixture thresholds? | Can promote release gate? |
|------|---------|--------------------------------|---------------------------|
| `tier0_fixture_replay` | Public synthetic fixtures under `tests/intel/fixtures/` | Yes | No |
| `tier1_private_calibration` | Redacted reports from private calibration labels | Yes, with caution | No |
| `tier2_private_holdout_canary` | Redacted calibration + holdout + canary evidence | Yes | Yes |

Private evidence reports must be redacted before commit. Allowed public fields
are aggregate counts, hashes, scorecard metrics, threshold hashes, verdicts, and
privacy flags. Forbidden public fields include raw paths, file names, raw audio,
raw vectors, unhashed IDs, deck/session identifiers, and free-form review notes.

## Entry Schema

Every real entry must follow this shape. Use `null` only when a field genuinely
does not exist yet; do not omit the field. Real entries must always bind the
private gold-label report and private scorecard to non-null SHA-256 hashes.
`release_promoted` entries must also bind the gate artifact to a non-null
SHA-256 hash.
The validator recomputes pass/fail from the measured/locked metric lines and
rejects verdict/action pairs that disagree with those numbers. It also rejects
`release_promoted` entries that are not backed by `tier2_private_holdout_canary`
evidence, and rejects entries whose `lock:` digest does not match the current
`eval/INTEL-THRESHOLD-LOCK.md` file. Key-value lines are strict: duplicate keys,
unknown keys, and malformed tokens are invalid rather than silently ignored.
Timestamps must be real UTC instants. Across real entries, `run_id` values must
be unique and timestamps must not move backwards.

```text
### YYYY-MM-DDTHH:MM:SSZ - verdict={private_in_tolerance|private_recalibration_required|release_promoted}
- run_id: intel_private_<YYYYMMDD>_<10-lowercase-hex>
- lock: eval/INTEL-THRESHOLD-LOCK.md (sha256:<lock-hash>)
- evidence_tier: tier1_private_calibration|tier2_private_holdout_canary
- splits: calibration=N holdout=N canary=N
- label_kinds: section=N transition=N cue=N live_pill=N representation=N taste=N
- reports: gold_report=<redacted-report-path> scorecard=<redacted-report-path> taste_scorecard=<redacted-report-path|null> gate=<redacted-report-path|null>
- report_hashes: gold_report=sha256:<hash> scorecard=sha256:<hash> taste_scorecard=sha256:<hash>|null gate=sha256:<hash>|null
- measured: section_role_hit_at_5_delta=X.XX transition_accept_at_3=X.XX decision_exact_timing_floor_violation_rate=X.XX taste_accepted_suggestion_lift=X.XX
- locked:   section_role_hit_at_5_delta_min=X.XX transition_accept_at_3_min=X.XX decision_exact_timing_floor_violation_rate_max=X.XX taste_accepted_suggestion_lift_min=X.XX
- delta:    section_role_hit_at_5_delta=+/-X.XX transition_accept_at_3=+/-X.XX decision_exact_timing_floor_violation_rate=+/-X.XX taste_accepted_suggestion_lift=+/-X.XX
- privacy: local_paths_redacted=true ids_hashed=true raw_audio_committed=false raw_vectors_committed=false free_form_notes_committed=false
- verdict: private_in_tolerance|private_recalibration_required|release_promoted
- action: none|RECALIBRATION_REQUIRED|PROMOTE_LOCK_WITH_PR
```

## Retuning Rules

1. Fixture-only evidence may tune fixture gates, but it must not be described as
   release-grade.
2. Private-label calibration must validate all three splits:
   `calibration`, `holdout`, and `canary`.
3. `release_promoted` requires `tier2_private_holdout_canary` evidence and a
   fresh `scripts/eval/intel_gate.py` artifact generated after the threshold
   change. The gate artifact must appear as `gate=private:redacted` with a
   non-null `gate=sha256:<hash>` entry in `report_hashes`.
4. Zero-tolerance privacy and grounding counters stay at `0.00` unless the
   underlying INTEL contract is deliberately changed in the same PR.
5. Lowering thresholds to make a demo pass is forbidden. A lower value needs
   redacted private-label evidence, an explanation of the failure mode, and an
   explicit follow-up plan.
6. This log is append-only. Corrections supersede earlier entries by adding a
   new entry; do not edit old real entries.

## Producer

Use `scripts/eval/intel_recalibration_note.py` to render the redacted markdown
entry from private scorecard/gold/taste/gate reports. The script validates report
schemas, privacy flags, forbidden private payload markers, holdout/canary split
coverage for release promotion, timestamp/run-id shape, and the key
measured-vs-locked INTEL metrics before emitting an entry. Timestamps must be
real UTC instants, and the `run_id` date must match the entry timestamp date.
Each entry also carries canonical SHA-256
hashes of the redacted private aggregate reports, so the public note is bound
to exact evidence artifacts without exposing paths, track names, labels,
vectors, or audio. Release promotion also requires a passing private scorecard and a valid
`scripts/eval/intel_gate.py` artifact whose scorecard and provenance stages
point at the same threshold-lock/threshold-values hashes. Use `--append-log
eval/INTEL-THRESHOLD-RECALIBRATION-LOG.md` to append a valid entry directly;
invalid evidence or a candidate log that fails whole-log validation exits
non-zero and is not written. When `--output` and `--append-log` are combined,
the output file is written only after append validation succeeds.

Validate the public log with
`scripts/eval/intel_recalibration_log_validate.py`. The validator treats
everything after the append marker as machine-audited evidence and checks entry
schema, real UTC timestamp validity, canonical run-id shape/date binding,
current-lock hash binding, report-hash bindings, release/split consistency,
strict key-value parsing, append-order coherence, and public-redaction markers.

## Audit Trail

### 1970-01-01T00:00:00Z - verdict=schema_example
- run_id: intel_private_schema_example
- lock: eval/INTEL-THRESHOLD-LOCK.md (sha256:example)
- evidence_tier: tier1_private_calibration
- splits: calibration=0 holdout=0 canary=0
- label_kinds: section=0 transition=0 cue=0 live_pill=0 representation=0 taste=0
- reports: gold_report=null scorecard=null taste_scorecard=null gate=null
- report_hashes: gold_report=null scorecard=null taste_scorecard=null gate=null
- measured: section_role_hit_at_5_delta=0.00 transition_accept_at_3=0.00 decision_exact_timing_floor_violation_rate=0.00 taste_accepted_suggestion_lift=0.00
- locked:   section_role_hit_at_5_delta_min=0.15 transition_accept_at_3_min=0.80 decision_exact_timing_floor_violation_rate_max=0.00 taste_accepted_suggestion_lift_min=0.10
- delta:    section_role_hit_at_5_delta=+0.00 transition_accept_at_3=+0.00 decision_exact_timing_floor_violation_rate=+0.00 taste_accepted_suggestion_lift=+0.00
- privacy: local_paths_redacted=true ids_hashed=true raw_audio_committed=false raw_vectors_committed=false free_form_notes_committed=false
- verdict: schema_example
- action: none

<!-- Real redacted private-label entries append below. -->
