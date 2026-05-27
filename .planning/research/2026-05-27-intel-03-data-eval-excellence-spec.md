# INTEL-03 spec - data and evaluation excellence for musical intelligence

**Date:** 2026-05-27
**Scope:** evaluation, data quality, and acceptance gates for INTEL-01/02
**Depends on:** `.planning/research/2026-05-27-intel-02-agentic-musical-context-spec.md`
**Code posture:** first eval utilities now exist for ANLZ audit, cue-baseline
comparison, section retrieval, transition scoring, decision-runtime replay,
INTEL-15 gold-label validation/sampling/reporting, and INTEL-05 taste/privacy
gates. Fixture-level INTEL thresholds are locked in
`eval/INTEL-THRESHOLD-LOCK.md`; private release threshold locking remains
future work.
`scripts/eval/intel_scorecard.py` now aggregates the first INTEL gates across
ANLZ audit, cue-baseline comparison, section retrieval, transition scoring,
decision-runtime replay, gold-label validation, and taste learning.

## Goal

Make intelligence excellence measurable.

The product should not ship "smarter suggestions" because the architecture feels
right. It should ship them because local evidence proves:

- section extraction is grounded and stable;
- section embeddings improve transition tasks over whole-track embeddings;
- transition slates rank playable moves above bad moves;
- the agent never acts outside the grounded slate;
- the live pill degrades honestly when timing/confidence is weak.

This spec extends the existing eval spine instead of creating a separate research
lab. The current repo already has:

- `scripts/eval/replay_harness.py`
- `scripts/eval/scorecard.py`
- `scripts/eval/cited_relevance.py`
- `eval/THRESHOLD-LOCK.md`
- `eval/INTEL-THRESHOLD-LOCK.md`
- `eval/corpus/MANIFEST.md`
- genre/session fixture layout under `eval/corpus/sessions/`

INTEL evals should dock into that structure.

## Product claims that must become tests

### Claim 1: ANLZ gives reliable section structure

Evidence required:

- coverage rate on the local library;
- parse error rate;
- role distribution by mood;
- phrase duration sanity;
- path match/collision rate;
- DJ ear-check acceptance on a small review set.

Initial Kaan-rig baselines from INTEL-01:

```text
ANLZ .EXT files:             493
ANLZ .EXT with PSSI:         449
ANLZ parse errors:           0
PSSI moods:                  high=346, mid=101, low=2
phrase count min/med/max:    1 / 19 / 158
.DAT with PQTZ beatgrid:     493
PPTH basenames matched:      476 / 477
```

Product gate:

```text
parse_error_rate <= 1%
pssi_coverage >= 80% on Rekordbox-analyzed local tracks
pqtz_for_pssi >= 98%
unique_path_match >= 90%
wrong_match_known = 0
```

Wrong match known must be zero because a wrong cue map is worse than no cue map.

### Claim 2: section search beats track search for transition tasks

Evidence required:

- curated query set where target is a section role, not a track;
- compare whole-track vector retrieval vs section-vector retrieval;
- measure whether top-k includes a playable section of the requested role;
- measure whether returned section timing is usable as a cue.

Example eval queries:

```text
dark rolling hardtechno intro with no vocal
industrial drop tail that can go into a 170 bpm groove
breakdown with low-end removed, tension but no melody
tooly outro, percussive, mixable for 32 bars
acid line enters after a stripped intro
```

Metrics:

```text
role_hit@5
role_hit@10
section_relevance@5
mixable_window_hit@5
track_duplicate_rate@10
low_confidence_result_rate
```

Initial gate:

```text
section_role_hit@5 >= track_role_hit@5 + 0.15
mixable_window_hit@5 >= 0.65
low_confidence_result_rate <= 0.20 for live mode
```

The exact values should be recalibrated after the first human-labeled review
set, but the relative improvement over whole-track retrieval is non-negotiable.

Implementation status (2026-05-27):

- `scripts/eval/intel_section_retrieval.py` compares section candidates against
  pooled whole-track candidates.
- `tests/intel/fixtures/section_queries.jsonl` is the public synthetic query
  fixture.
- Fixture result: section `role_hit@5=1.0`, whole-track `role_hit@5=0.5`,
  delta `0.5`; section `low_confidence_result_rate=0.033333`.
- `scripts/eval/intel_scorecard.py` now gates
  `section_role_hit_at_5_delta`,
  `section_mixable_window_hit_at_5_delta`, and
  `section_low_confidence_result_rate`.

### Claim 3: transition slate ranks playable moves above bad moves

Evidence required:

- positive/negative transition pairs;
- score component breakdowns;
- risk flags on negatives;
- ablation of semantic, harmonic, BPM, energy, role, phrase alignment.

Metrics:

```text
pairwise_accuracy
ndcg@5
accepted_transition_rate@3
risk_flag_precision
hard_reject_recall
same-track/played-track leakage
```

Initial gate:

```text
pairwise_accuracy >= 0.75 on labeled local pairs
ndcg@5 >= 0.80
accepted_transition_rate@3 >= 0.60
invented_or_unseen_candidate_rate = 0
played_track_leakage_rate = 0
```

### Claim 4: grounded agent behavior stays inside the slate

Evidence required:

- schema validation of every `PillDecision`;
- candidate IDs checked against issued candidates;
- no cue/section claims unless issued by the engine;
- citations resolve through existing or planned EvidenceRegistry sources;
- timing claims gated by playhead confidence.

Metrics:

```text
invalid_schema_rate
unknown_candidate_id_rate
unsupported_track_claim_rate
unsupported_section_claim_rate
unsupported_musical_claim_rate
missing_claim_id_rate
timing_claim_below_floor_rate
empty_or_vague_response_rate
```

Gate:

```text
invalid_schema_rate = 0
unknown_candidate_id_rate = 0
unsupported_track_claim_rate = 0
unsupported_section_claim_rate = 0
unsupported_musical_claim_rate = 0
missing_claim_id_rate = 0
timing_claim_below_floor_rate = 0
useful_response_ratio >= existing threshold-lock value
```

Grounding failures are correctness bugs, not taste issues.

### Claim 5: live pill is useful without overclaiming

Evidence required:

- replay sessions with known track changes and transitions;
- simulated playhead confidence buckets;
- blend-window cases;
- no-suggestion cases;
- acceptance/rejection logs from Kaan.

Metrics:

```text
timely_suggestion_rate
late_suggestion_rate
wrong_timing_rate
correct_suppression_rate
annoying_repeat_rate
accepted_live_suggestion_rate
```

Gate:

```text
wrong_timing_rate <= 0.05
correct_suppression_rate >= 0.85
annoying_repeat_rate <= 0.10
accepted_live_suggestion_rate >= baseline_track_pill + 0.20
```

The pill should be allowed to say nothing. Silence protects trust.

### Claim 6: taste improves ranking without privacy leaks or scorer poisoning

Evidence required:

- structured feedback events with explicit consent posture;
- deterministic taste aggregation from feedback, not LLM-written memories;
- proof that consent-off feedback does not create long-term writes;
- proof that one session cannot create durable hard negatives;
- proof that taste cannot rescue technically bad transitions;
- prompt-facing profile projection contains only allowlisted aggregate tags.

Metrics:

```text
accepted_suggestion_lift
consent_off_long_term_write_rate
single_session_hard_negative_rate
technical_bad_candidate_rescued_by_taste
profile_projection_privacy_leak_count
unknown_preference_claim_rate
```

Gate:

```text
accepted_suggestion_lift >= 0.10 on labeled or synthetic calibration events
consent_off_long_term_write_rate = 0
single_session_hard_negative_rate = 0
technical_bad_candidate_rescued_by_taste = 0
profile_projection_privacy_leak_count = 0
unknown_preference_claim_rate = 0
```

Implementation status (2026-05-27):

- `src/vibemix/intel/feedback.py` defines structured feedback events and
  consent-aware persistence posture.
- `src/vibemix/intel/taste_model.py` builds conservative deterministic taste
  aggregates with minimum-evidence and single-session poisoning guards.
- `src/vibemix/intel/profile_projection.py` emits an allowlisted prompt-facing
  projection without track IDs, section IDs, local paths, or detailed history.
- `scripts/eval/intel_taste_scorecard.py` gates the public synthetic taste
  fixture.
- Fixture result: accepted suggestion lift `0.18`; all privacy/poisoning
  counters `0`.

## Eval assets

### Local private assets

Private local assets should stay out of git:

```text
eval/private/intel/local_library_stats.json
eval/private/intel/anlz_review_set.jsonl
eval/private/intel/transition_pairs.jsonl
eval/private/intel/live_replay_decisions.jsonl
```

These can reference local track IDs and timestamps, but not commit sensitive
audio or private recordings.

### Public synthetic assets

Commit small fixtures:

```text
tests/library/fixtures/intel_sections.json
tests/library/fixtures/intel_transition_pairs.json
tests/library/fixtures/intel_context_packets.json
```

INTEL-22 replaces this minimal list with the canonical synthetic intelligence
fixture corpus. Keep these legacy paths only as compatibility shims if needed;
new INTEL implementation tests should prefer `tests/intel/fixtures/`.

Purpose:

- deterministic unit tests for IDs, scoring, gates, and schema;
- no real audio;
- no private library paths.

### External benchmark assets

Use external datasets as optional eval inputs, not product dependencies:

- **Raveform**: EDM/DJ-mix structure benchmark. The 2026 TISMIR article reports
  4,902 DJ mix links, 56,873 track links, and 1,423 tracks with expert structure
  annotations. Its public dataset includes beat-level DTW alignments between DJ
  mixes and tracks, plus segment labels and beat/downbeat files.
  Sources:
  - https://reference-global.com/article/10.5334/tismir.288
  - https://mir-aidj.github.io/raveform/
- **MIREX music structure analysis**: useful metric vocabulary and leaderboard
  context for structure analysis; 2025 results report ACC / hit-rate metrics.
  Source:
  - https://music-ir.org/mirex/wiki/2025:Music_Structure_Analysis_Results
- **Temporal audio-language research**: useful for embedding model bake-offs, not
  immediate product dependency. T-CLAP, TACOS, and CoLLAP all exist because
  global clip-level audio-text training is weak at temporal alignment.
  Sources:
  - https://arxiv.org/abs/2404.17806
  - https://arxiv.org/abs/2505.07609
  - https://arxiv.org/abs/2410.02271

## Proposed eval modules

### `scripts/eval/intel_anlz_audit.py`

Inputs:

```text
--rekordbox-root ~/Library/Pioneer/rekordbox
--library-cache <path>
--json-out eval/private/intel/local_library_stats.json
```

Outputs:

```json
{
  "ext_files": 493,
  "pssi_files": 449,
  "parse_errors": 0,
  "moods": {"1": 346, "2": 101, "3": 2},
  "phrase_count": {"min": 1, "median": 19, "max": 158},
  "pqtz_for_pssi": 449,
  "path_matches": 476,
  "path_collisions": 12,
  "unmatched": ["feel futuristic.mp3"]
}
```

Current implementation:

```text
scripts/eval/intel_transition_scorecard.py
tests/eval/test_intel_transition_scorecard.py
```

It validates transition labels against issued candidates and reports
`pairwise_accuracy`, `ndcg_at_5`, `accepted_transition_rate_at_3`,
`risk_flag_precision`, `leakage_rate`, unknown label candidates, and NaN scores.

Test coverage:

- parser missing-file cases;
- collision accounting;
- no private paths in public output mode;
- JSON schema stability.

### `scripts/eval/intel_section_retrieval.py`

Inputs:

```text
--queries eval/private/intel/section_queries.jsonl
--mode compare|whole-track|section
--k 10
```

Outputs:

```json
{
  "role_hit_at_5": 0.74,
  "role_hit_at_10": 0.82,
  "mixable_window_hit_at_5": 0.68,
  "low_confidence_result_rate": 0.12
}
```

Compare modes in scorecard:

```text
section - whole_track deltas
```

Current fixture command:

```bash
uv run python scripts/eval/intel_section_retrieval.py --fixture-dir tests/intel/fixtures --json
```

### `scripts/eval/intel_transition_scorecard.py`

Inputs:

```text
--pairs eval/private/intel/transition_pairs.jsonl
--ablate none|semantic|harmony|bpm|energy|role|phrase
```

Outputs:

```json
{
  "pairwise_accuracy": 0.78,
  "ndcg_at_5": 0.82,
  "accepted_transition_rate_at_3": 0.63,
  "risk_flag_precision": 0.71,
  "leakage_rate": 0.0
}
```

Hard failures:

- unknown track;
- unknown section;
- generated candidate not in issued slate;
- played-track leakage;
- NaN score.

### `scripts/eval/intel_decision_runtime_replay.py`

Inputs:

```text
--fixture-dir tests/intel/fixtures
--contexts tests/intel/fixtures/context_packets.json
--decisions tests/intel/fixtures/agent_decisions.jsonl
```

Validates:

- `AgentDecision` / `PillDecision` schema;
- `candidate_id` in packet slate;
- timing text suppressed below confidence floor;
- no unsupported cue/section claims;
- no unsupported musical claims outside INTEL-21 claim ledger;
- citations parse and resolve through available sources.

The current replay hydrates redacted context packets from `transition_pairs.json`
and `claim_ledgers.json`, then reports fallback, grounding, claim, and timing
floor metrics.

### `scripts/eval/intel_live_replay.py`

Extends the replay harness:

```text
recording/session -> MusicState snapshots -> MusicalContextPacket -> slate -> PillDecision
```

Outputs:

- decision timing;
- suppress/emit behavior;
- accepted/rejected labels if available;
- wrong timing incidents;
- repeated suggestion incidents.

## Human labeling protocol

Kaan should not label everything. Label only the examples that teach the engine.
INTEL-15 is the canonical detailed schema/sampling protocol for these labels;
this section is the short eval-facing summary.

### Section review

For each reviewed track, show 5-8 candidate anchors:

```text
track_id
title / artist
section role
start_s / end_s
confidence
source
audio jump command or Rekordbox timestamp
```

Labels:

```text
good
early
late
wrong_role
not_mixable
unclear
```

### Transition review

For each candidate:

```text
from section -> to section
score components
risk flags
suggested cue slot
```

Labels:

```text
would_play
maybe
no
technical_no
vibe_no
timing_no
```

One optional note field is enough. Do not make labeling feel like a spreadsheet
prison.

## Data quality ledger

Every intelligence build should emit a short ledger:

```text
tracks indexed
sections indexed
sections by source
sections by role
sections below confidence floor
tracks with no usable sections
tracks with path collisions
embedding model id
embedding dimensions
embedding cache version
transition score version
generated_at
```

This ledger is the first thing to inspect when the agent feels "dumb." Many
agent failures will really be data coverage failures.

## Threshold policy

Use the existing threshold-lock discipline:

- initial gates live in the INTEL spec;
- fixture-level INTEL gates live in `eval/INTEL-THRESHOLD-LOCK.md`;
- `eval/THRESHOLD-LOCK.md` remains the signed legacy hallucination-gate lock;
- any threshold change needs a recalibration note;
- never silently loosen a threshold to make a demo pass.

Locked synthetic-fixture threshold block:

```text
anlz_complete_rate_min=0.70
anlz_parse_error_rate_max=0.00
cue_exact_or_near_rate_min=0.40
section_role_hit_at_5_delta_min=0.15
section_mixable_window_hit_at_5_delta_min=0.10
section_low_confidence_result_rate_max=0.15
transition_accept_at_3_min=0.80
transition_pairwise_accuracy_min=0.80
transition_unknown_candidate_label_count_max=0.00
decision_validator_fallback_rate_max=0.20
decision_exact_timing_floor_violation_rate_max=0.00
gold_validation_error_count_max=0.00
taste_accepted_suggestion_lift_min=0.10
taste_consent_off_long_term_write_rate_max=0.00
taste_single_session_hard_negative_rate_max=0.00
taste_technical_bad_candidate_rescued_count_max=0.00
taste_profile_projection_privacy_leak_count_max=0.00
taste_unknown_preference_claim_rate_max=0.00
```

## Build order

### INTEL-03A: audit-only gate

- Add ANLZ audit script.
- Emit local private JSON.
- Add public synthetic tests.
- No model dependency.

### INTEL-03B: section retrieval bake-off

- Done: build tiny query fixture.
- Done: compare whole-track vs section retrieval.
- Done: add scorecard output and aggregate gates.

### INTEL-03C: transition pair scorecard

- Create 30-50 local labeled transition pairs.
- Implement pairwise and nDCG metrics.
- Add ablation modes.

### INTEL-03D: agent grounding validator

- Validate `PillDecision` against packets.
- Fail unknown candidate IDs and timing overclaims.
- Connect to cited relevance/substance.

### INTEL-03E: Raveform optional benchmark

- Add optional downloader/adapter outside default CI.
- Map Raveform labels to vibemix roles:

```text
intro -> intro
buildup -> build
breakdown/cooldown -> breakdown
drop -> drop
outro -> outro
```

- Use it to test structure/transition assumptions, not as a replacement for
  Kaan's ear on his own library.

### INTEL-03F: taste/privacy gate

- Done: add structured feedback event parsing and validation.
- Done: add deterministic taste aggregation with minimum-evidence guards.
- Done: add profile projection privacy checks.
- Done: add `scripts/eval/intel_taste_scorecard.py`.
- Done: aggregate taste gates into `scripts/eval/intel_scorecard.py`.
- Pending: real private feedback labels and durable product capture surfaces.

## Non-goals

- No committed private audio.
- No public leakage of local Rekordbox paths.
- No dependence on Raveform/MIREX for normal app runtime.
- No subjective LLM judge as the only gate for musical correctness.
- No threshold loosening without recalibration.

## Success definition

The intelligence lane is ready to ship when the scorecard can prove:

```text
ANLZ coverage is healthy.
Section retrieval beats track retrieval on transition queries.
Transition slates rank playable moves above bad moves.
The agent never chooses unknown candidates.
The pill never makes exact timing claims below confidence floor.
Kaan accepts materially more live/prep suggestions than the track-level baseline.
Taste improves close-call ranking without privacy leaks or technical rescues.
```

That is how we keep the app from becoming impressive theater. The product should
feel magical because the data underneath it is boringly solid.
