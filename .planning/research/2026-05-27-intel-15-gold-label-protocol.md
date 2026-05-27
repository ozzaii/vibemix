# INTEL-15: gold-label protocol for musical intelligence

**Date:** 2026-05-27
**Lane:** data excellence / human eval / taste-safe learning
**Depends on:** INTEL-03, INTEL-05, INTEL-11, INTEL-12, INTEL-14
**Status:** canonical private-label schema and sampling protocol

## Why this exists

The intelligence stack now has a clear architecture:

```text
ANLZ structure
  -> section vectors
  -> transition scorer
  -> grounded context packet
  -> agent explanation
  -> taste feedback
```

The missing excellence layer is the judgement loop. Without a clean local gold
set, every model or scoring change is judged by vibes in the moment. That is how
an app drifts into "cool demo, no taste."

This spec defines how to collect Kaan's musical judgements as structured,
replayable, privacy-safe evidence.

Important language:

- **Gold** means "gold for this product and this DJ's library," not universal
  musical truth.
- **Calibration** means labels may tune weights or thresholds.
- **Holdout** means labels are used only to measure whether changes improved.
- **Taste** means personal ranking preference, never a license to override
  grounding, BPM/key/phrase confidence, or safety floors.

## External evaluation anchors

Primary sources behind this protocol:

- ITU-R BS.1534 (MUSHRA) is a standard for subjective audio assessment with
  trained listeners, references, and anchors. We are not running a MUSHRA test,
  but we should borrow the discipline: short comparison tasks, known anchors,
  and explicit rubrics instead of vague "sounds good?"
  Source: https://www.itu.int/rec/r-rec-bs.1534/en
- Music similarity and structure labels have limited inter-rater agreement; that
  ceiling should be respected instead of pretending there is one objective
  ranking of all transitions.
  Source: https://www.tandfonline.com/doi/abs/10.1080/09298215.2016.1200631
- Active learning is useful when unlabeled data is abundant but labels are
  expensive: choose the examples that teach the model most.
  Source: https://minds.wisconsin.edu/handle/1793/60660
- Information-retrieval evaluation uses pooled judgements because judging every
  item is too expensive; our transition-review pool should combine candidates
  from multiple strategies before judging.
  Source: https://arxiv.org/abs/1709.01709

Applied to vibemix:

- Do not ask Kaan to label a thousand tracks.
- Do not judge one candidate in isolation when the real task is choosing among
  alternatives.
- Do not treat disagreement or "maybe" as noise; it is musical ambiguity.
- Do not use the same labels to both tune and claim victory.

## Private eval layout

All local labels stay private by default:

```text
eval/private/intel/gold/
  README.md
  review_sessions.jsonl
  section_reviews.jsonl
  transition_reviews.jsonl
  cue_reviews.jsonl
  live_pill_reviews.jsonl
  representation_reviews.jsonl
  frozen_holdout_manifest.json
```

No committed private audio. No local file paths in exported reports. Track IDs
and section IDs are allowed in private files because they are needed for replay,
but public reports must hash/redact them.

## Canonical IDs

These IDs are eval-only. Action tools must never accept them.

```text
review_session_id = "rs_YYYYMMDD_NNN"
review_item_id    = "rev_001"
label_id          = "lbl_001"
rubric_version    = "kaan_gold_v1"
```

Rules:

- `review_item_id` is run-scoped inside one review session.
- `label_id` is stable inside one JSONL file and points to the reviewed object.
- Track/section/candidate/proposal IDs must already follow INTEL-13.
- If a label references a transition candidate, store both public
  `candidate_id` and internal `transition_key` when available.
- Labels are evidence, not commands.

## Review session record

`review_sessions.jsonl`

```json
{
  "review_session_id": "rs_20260527_001",
  "created_at": "2026-05-27T22:10:00Z",
  "rubric_version": "kaan_gold_v1",
  "operator": "kaan",
  "mode": "prep_review",
  "source_pool": "local_rekordbox",
  "sampling_policy": "stratified_active_v1",
  "strategy_versions": {
    "section_extraction": "anlz_pssi_v1",
    "embedding": "clap_section_head_tail_v1",
    "transition_scorer": "transition_scorer_v1"
  },
  "notes": ""
}
```

Modes:

```text
section_review
transition_review
cue_review
live_replay
representation_bakeoff
debrief
```

## Section review schema

`section_reviews.jsonl`

```json
{
  "label_id": "lbl_001",
  "review_session_id": "rs_20260527_001",
  "review_item_id": "rev_001",
  "split": "calibration",
  "track_id": "rb-123",
  "section_id": "rb-123#s004",
  "role": "breakdown",
  "source": "anlz",
  "source_detail": "pssi",
  "start_s": 133.7,
  "end_s": 143.0,
  "start_beat": 402,
  "end_beat": 430,
  "confidence": 0.74,
  "label": "small_nudge",
  "boundary_delta_beats": 4,
  "role_correct": true,
  "mixable": true,
  "reason": "late",
  "note": ""
}
```

Allowed labels:

```text
good
small_nudge
wrong_boundary
wrong_role
not_mixable
unusable
unclear
```

Allowed reasons:

```text
early
late
too_short
wrong_energy
wrong_role
no_clear_change
bad_audio
duplicate
other
```

Rubric:

- `good`: usable as-is.
- `small_nudge`: usable after moving by <=8 bars.
- `wrong_boundary`: musically meaningful section, but boundary is off by >8 bars.
- `wrong_role`: boundary is useful, role is wrong.
- `not_mixable`: musically real section, but bad cue/mix point.
- `unusable`: do not use for cues or transition scoring.
- `unclear`: ambiguity; keep for analysis, do not punish the model harshly.

## Transition review schema

`transition_reviews.jsonl`

```json
{
  "label_id": "lbl_010",
  "review_session_id": "rs_20260527_001",
  "review_item_id": "rev_010",
  "split": "calibration",
  "candidate_id": "tr_001",
  "transition_key": "ab12cd34ef56aa00",
  "from_track_id": "rb-123",
  "from_section_id": "rb-123#s010",
  "to_track_id": "rb-456",
  "to_section_id": "rb-456#s002",
  "intent": "smooth_lift",
  "score_total": 0.81,
  "score_components": {
    "semantic": 0.84,
    "harmonic": 1.0,
    "bpm": 0.92,
    "energy_shape": 0.71,
    "role": 0.88,
    "phrase_alignment": 0.83,
    "cue_operability": 0.75,
    "taste": 0.0,
    "novelty": 0.4,
    "risk_penalty": 0.04
  },
  "warnings": ["energy_lift"],
  "label": "would_play",
  "reject_reason": null,
  "preferred_over": [],
  "note": ""
}
```

Allowed labels:

```text
would_play
maybe
no
```

Allowed reject reasons:

```text
technical_no
vibe_no
timing_no
energy_no
key_bpm_no
too_obvious
too_surprising
duplicate_feel
bad_cue
unsafe_unknown
other
```

Rubric:

- `would_play`: this transition is plausible enough to try in a real set.
- `maybe`: musically plausible but context-dependent.
- `no`: do not recommend under the shown intent/context.

Do not overload `no`. Always choose a reject reason when possible. A `technical_no`
teaches the scorer differently from a `vibe_no`.

## Pairwise transition review

Absolute labels are useful, but pairwise preference is often easier and more
stable for music.

When two candidates are close, ask:

```text
For this outgoing section and intent, which entry would you pick?
```

Record inside `transition_reviews.jsonl`:

```json
{
  "label_id": "lbl_011",
  "review_session_id": "rs_20260527_001",
  "review_item_id": "rev_011",
  "split": "calibration",
  "pairwise_group_id": "pair_001",
  "candidate_id": "tr_002",
  "transition_key": "cd34ef56aa00ab12",
  "label": "maybe",
  "pairwise_choice": "loses",
  "preferred_over": [],
  "note": "A is smoother; this one is too vocal"
}
```

Allowed `pairwise_choice`:

```text
wins
loses
tie
neither
```

Use pairwise labels to compute preference accuracy and tune score components.
Do not force pairwise questions for obvious bad candidates.

## Cue review schema

`cue_reviews.jsonl`

```json
{
  "label_id": "lbl_020",
  "review_session_id": "rs_20260527_001",
  "review_item_id": "rev_020",
  "split": "calibration",
  "proposal_id": "cueprop_001",
  "cue_id": "cueprop_001:C",
  "track_id": "rb-123",
  "section_id": "rb-123#s006",
  "slot": "C",
  "role": "breakdown",
  "proposed_start_s": 133.7,
  "proposed_start_beat": 402,
  "source": "anlz",
  "source_detail": "pssi",
  "confidence": 0.74,
  "label": "move",
  "corrected_start_s": 141.7,
  "corrected_start_beat": 426,
  "corrected_role": "breakdown",
  "note": ""
}
```

Allowed labels:

```text
keep
move
delete
relabel
add_missing
unclear
```

Cue edit rules:

- `move` with <=8 bars is a calibration nudge.
- `move` with >8 bars is a boundary failure.
- `delete` is negative for cue usefulness, not necessarily for the section.
- `relabel` is negative for role mapping.
- `add_missing` identifies a structural blind spot.

## Live pill review schema

`live_pill_reviews.jsonl`

```json
{
  "label_id": "lbl_030",
  "review_session_id": "rs_20260527_001",
  "review_item_id": "rev_030",
  "split": "canary",
  "packet_id": "ctx_001",
  "candidate_id": "tr_001",
  "track_id": "rb-123",
  "section_id": "rb-123#s010",
  "playhead_confidence": 0.82,
  "bars_to_boundary": 16,
  "message_kind": "exact_timing",
  "label": "helpful",
  "timing_error_bars": 0,
  "action_taken": "played_suggested",
  "note": ""
}
```

Allowed labels:

```text
helpful
not_now
wrong_timing
too_late
too_early
distracting
suppression_correct
suppression_wrong
unclear
```

Rules:

- `wrong_timing`, `too_late`, and `too_early` are hard negatives for live timing.
- `not_now` is weak taste/context negative, not a permanent track rejection.
- `suppression_correct` is positive evidence for confidence gating.
- `suppression_wrong` means the engine was too timid.

## Representation review schema

`representation_reviews.jsonl`

Use this only for INTEL-14 bake-offs.

```json
{
  "label_id": "lbl_040",
  "review_session_id": "rs_20260527_001",
  "review_item_id": "rev_040",
  "split": "holdout",
  "query": "tooly outro, percussive, mixable for 32 bars",
  "representation_run_id": "repr_clap_head_tail_20260527",
  "result_rank": 1,
  "track_id": "rb-123",
  "section_id": "rb-123#s011",
  "role": "outro",
  "label": "relevant_mixable",
  "note": ""
}
```

Allowed labels:

```text
relevant_mixable
relevant_not_mixable
wrong_role
wrong_vibe
duplicate
unsafe_low_confidence
unclear
```

## Splits

Every label has one split:

```text
calibration
holdout
canary
```

Meaning:

- `calibration`: may tune score weights, confidence thresholds, role mapping,
  cue policy, and representation choices.
- `holdout`: used only to evaluate whether a change improved. Do not tune on it.
- `canary`: recent labels from live/debrief used to detect regressions after
  the model/scorer changes.

Initial split policy:

```text
60% calibration
25% holdout
15% canary
```

Rules:

- Holdout labels are frozen once created.
- If a holdout label is wrong, append a correction record with `supersedes`, do
  not silently edit history.
- Calibration data can be refreshed more freely, but keep old records for drift
  analysis.

## Sampling strategy

Do not sample only top-ranked suggestions. That creates a flattering test.

Use a pooled review set from multiple sources:

```text
top scorer candidates
near-threshold candidates
high-score/high-risk candidates
section CLAP candidates
whole-track baseline candidates
random same-BPM/key candidates
known bad or low-confidence candidates
manual Kaan picks
```

### Section sampling

Stratify by:

- source: `dj`, `anlz`, `auto`, `fallback`;
- source detail: `hotcue`, `pssi`, `cue_detr`, `dsp`, `all_in_one`;
- role: intro/groove/build/breakdown/drop/outro/unknown;
- ANLZ mood: high/mid/low;
- confidence bucket: high/medium/low;
- phrase length bucket: too_short/normal/long/weird;
- genre/vibe cluster.

First gold slice:

```text
20 hardtechno tracks
10 broader-vibe tracks
5-8 sections per track
```

### Transition sampling

Stratify by:

- intent: smooth, lift, reset, harder, deeper, surprise;
- role pair;
- harmonic relation;
- BPM delta bucket;
- energy delta bucket;
- risk flags;
- score bucket.

First gold slice:

```text
30 absolute transition labels
20 pairwise transition choices
at least 10 clear negatives
at least 10 near-threshold candidates
```

### Cue sampling

Stratify by:

- slot A-F;
- source;
- role;
- confidence bucket;
- short/long phrase;
- tracks with no previous cues.

First gold slice:

```text
50 proposed cues
at least 10 deleted/moved examples if available
```

### Live sampling

Use replay first:

```text
10 exact-timing suggestions
10 medium-confidence suggestions
10 suppressed suggestions
10 blend-window cases
```

Only after replay looks sane should live pill labels tune behavior.

## Active selection policy

After the first gold slice, ask for labels that maximize learning:

1. **Uncertainty:** score near decision threshold.
2. **Disagreement:** two strategies rank candidates differently.
3. **High-impact risk:** high score plus strong warning.
4. **Coverage gap:** under-labeled role/source/genre bucket.
5. **Recent failure:** user rejected, edited, or contradicted a suggestion.
6. **Regression sentry:** known good examples that must stay good.

Keep the human ask tiny:

```text
max 5 section/cue labels in one prep review
max 5 transition labels in one prep review
max 3 debrief prompts after a session
```

Respect fatigue. Bad labels from a tired DJ are worse than no labels.

## Label quality controls

### Repeat sentries

Repeat about 10% of review items across sessions.

Use them to detect:

- rubric drift;
- mood/context drift;
- UI confusion;
- labels that are inherently ambiguous.

Do not shame the user with "inconsistency." Music taste shifts.

### Anchor examples

Each review session should include:

- one obvious good transition;
- one obvious bad transition;
- one low-confidence section;
- one known useful cue.

These calibrate the reviewer's ear for that session, like anchors in subjective
audio evaluation.

### Maybe is data

`maybe` means:

- context-dependent;
- weak positive for retrieval;
- weak/neutral for taste;
- should not be used as hard negative.

### Unclear is not failure

`unclear` means:

- do not train strongly;
- inspect bucket later;
- maybe split the role ontology or improve the UI preview.

## How labels feed systems

### Eval scorecards

Use all splits appropriately:

- calibration for tuning;
- holdout for release claims;
- canary for recent regression alerts.

Primary metrics:

```text
section_good_or_small_nudge_rate
section_wrong_role_rate
cue_keep_or_small_move_rate
transition_accept_at_3
transition_mrr
pairwise_preference_accuracy
high_confidence_bad_rate
timing_wrong_rate
suppression_correct_rate
```

### Transition scorer

Use labels to adjust:

- score weights only after enough calibration labels;
- risk penalties by reject reason;
- role-pair weights;
- confidence floors.

Never allow taste/calibration to rescue:

- unknown IDs;
- invalid cue slots;
- incompatible hard technical gates;
- below-floor live timing claims.

### Taste model

Only explicit user labels should become durable taste by default.

Mapping:

```text
would_play -> positive
maybe -> weak positive or neutral
no + vibe_no -> taste negative
no + technical_no -> scorer/risk negative, not taste
wrong_timing -> live timing negative, not track taste
cue move/delete -> cue policy/structure calibration
```

Consent:

- if long-term profile consent is off, store no durable taste ledger;
- session-only feedback may still influence the current run;
- private eval files are a separate explicit research artifact, not prompt
  profile memory.

### Representation benchmark

Use representation labels to compare:

- section CLAP head/tail vs full section;
- section CLAP vs whole-track CLAP;
- future MuQ/MERT/T-CLAP candidates;
- structure fallback models.

The benchmark winner must improve holdout labels, not only calibration labels.

## Redaction policy

Private raw rows may contain:

- track IDs;
- section IDs;
- candidate IDs;
- timestamps;
- score components;
- concise notes.

Private rows must not contain:

- local file paths;
- raw audio;
- private recordings;
- API keys/secrets;
- full chat transcripts.

Public/redacted reports may contain:

```text
hashed_track_id = sha256(track_id | report_salt)[:12]
role/source/score/label aggregates
example rows only after track/title redaction
```

Do not publish notes unless manually reviewed.

## Commands to implement later

These are build targets, not work for this research pass:

```text
uv run python -m vibemix eval intel-gold init \
  --out eval/private/intel/gold

uv run python -m vibemix eval intel-gold sample \
  --kind transition \
  --policy stratified_active_v1 \
  --n 30 \
  --out eval/private/intel/gold/review_sessions/rs_YYYYMMDD_NNN.json

uv run python -m vibemix eval intel-gold validate \
  eval/private/intel/gold

uv run python -m vibemix eval intel-gold report \
  --split holdout \
  --redacted \
  --out .planning/eval/reports/intel-gold-YYYYMMDD.md
```

Validation rules:

- every ID resolves to a known issued or stored object;
- every row has `rubric_version`;
- every release-claim label has full INTEL-17 lineage or an explicit
  `lineage_status="partial"` exclusion;
- every label is in enum;
- every holdout correction uses `supersedes`;
- no local path pattern appears;
- no unknown candidate/proposal IDs;
- no action payload is reconstructed from label rows.

## Proposed implementation files

```text
src/vibemix/intel/gold_labels.py
src/vibemix/intel/gold_sampling.py
src/vibemix/intel/gold_validation.py
scripts/eval/intel_gold.py
tests/intel/test_gold_labels.py
tests/intel/test_gold_sampling.py
tests/eval/test_intel_gold_validation.py
```

No model dependency. These are schema, sampling, and validation utilities.

## First review packet

When the implementation exists, the first human review should be:

```text
20 hardtechno tracks:
  5-8 ANLZ sections each
30 transition candidates:
  10 top-ranked
  10 near-threshold
  5 baseline whole-track suggestions
  5 deliberately risky/high-warning
50 smart cue proposals:
  slots A-F, source/confidence-stratified
20 cue baseline comparisons:
  vibemix INTEL-18 vs Rekordbox auto when available, plus naive ANLZ baseline
10 replay pill moments:
  timing and suppression only
```

Goal:

- confirm ANLZ boundaries are good enough;
- prove section retrieval beats track retrieval;
- detect which score components are lying;
- compare vibemix smart cues against Rekordbox auto-cue and naive ANLZ baselines;
- seed taste without poisoning it.

## Success definition

The gold-label loop is ready when:

```text
private schema validates;
first gold slice exists;
holdout split is frozen;
scorecards can replay labels;
transition/cue/timing metrics are computed from labels;
reports can be redacted;
TasteModel consumes only consent-allowed labels;
no action tool accepts eval-only IDs.
```

This is the data moat. The app gets smarter only because the labels are precise,
scarce, protected, and connected to grounded musical objects.
