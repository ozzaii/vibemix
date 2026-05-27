# INTEL-19: smart cue baseline comparison

**Date:** 2026-05-27
**Lane:** intelligence eval / product moat / cue quality evidence
**Depends on:** INTEL-15 and INTEL-18
**Status:** executable first harness for proving cue quality against Rekordbox baseline
**Code posture:** eval-only harness implemented in
`scripts/eval/intel_cue_baseline_compare.py` with focused tests. No product
runtime behavior changed.

## Goal

Make smart cue quality measurable.

Rekordbox 7 already ships Intelligent Cue Creation, so vibemix needs evidence
that its cue proposals are useful in a different and better way:

```text
not "we can auto-place hot cues too"
but "our cue map is set-aware, explainable, reviewable, and improves transition choices"
```

INTEL-18 defines the cue policy. INTEL-19 defines how to evaluate that policy
against baselines.

## Baselines

### Baseline A: Rekordbox Intelligent Cue Creation

Use a local Rekordbox-generated cue snapshot as the primary competitive
baseline.

Relevant external facts:

- Rekordbox 7 overview says Intelligent Cue Creation can automatically set Hot
  Cues and Memory Cues and learn cue-point preferences.
- Rekordbox 7.2.14 manual says CUE Analysis can set Hot Cues or memory cues, up
  to 16 Hot Cues and 10 memory cues, and supports Auto and Manual modes.
- Rekordbox FAQ says CUE(auto) uses phrase analysis and can improve with
  personal CUE trend information from a CUE Analysis Playlist.

Evaluation implication:

```text
Rekordbox auto-cue is not an enemy. It is the "competent default" baseline.
vibemix must prove lift where it claims differentiation.
```

### Baseline B: DJ-authored cues

When user cues exist, they are the strongest supervision.

Important nuance:

- A human cue may be a prep marker, performance jump, memory reminder, or loop
  habit.
- Do not assume every human cue maps cleanly to INTEL-18 A-H semantics.
- Use human cues as labels only after review or when the slot/label is clear.

### Baseline C: naive ANLZ phrase policy

A simple policy:

```text
A = first intro
B = first build/groove
C = first breakdown
D = first drop
F = first outro
```

This isolates whether INTEL-18's scoring, genre policy, confidence gates, and
slot preservation actually improve over "map labels to pads."

### Baseline D: current CUE-DETR/DSP fallback

Use the current auto-cue engine when ANLZ is unavailable or deliberately masked.
This proves whether Rekordbox ANLZ is carrying the expected value.

## Snapshot protocol

Never evaluate on an uncontrolled live library mutation.

Recommended local protocol:

```text
1. Export a Rekordbox XML snapshot before cue analysis.
2. Copy a small evaluation playlist/crate.
3. In Rekordbox, use settings that prohibit overwriting existing CUEs when
   generating auto cues, unless the test is explicitly measuring overwrite.
4. Run CUE(auto) on the copied eval playlist.
5. Export a second Rekordbox XML snapshot.
6. Diff POSITION_MARK records by stable track identity.
7. Store only redacted cue facts in private eval JSONL.
```

Do not commit:

- audio;
- raw local paths;
- full exported collection XML;
- private track names if the eval artifact leaves the machine.

## Parsed baseline object

Represent each baseline cue as:

```python
@dataclass(frozen=True, slots=True)
class BaselineCue:
    baseline: Literal["rekordbox_auto", "dj", "naive_anlz", "vibemix", "fallback"]
    track_id: str
    slot: str | None
    type: Literal["hot_cue", "memory_cue", "loop", "load", "unknown"]
    start_s: float
    end_s: float | None
    label: str
    source_xml_snapshot_id: str | None
    source_section_id: str | None
    confidence: float | None
```

Use `slot=None` for memory cues or unknown marks.

## Matching cue sets

Cue-set comparison needs beat-aware matching, not raw seconds only.

### Time distance

When beatgrid exists:

```text
distance_beats = abs(candidate_start_beat - reference_start_beat)
```

When beatgrid is missing:

```text
distance_s = abs(candidate_start_s - reference_start_s)
```

Suggested equivalence bands:

```text
exact:       <= 1 beat
near:        <= 4 beats
phrase-near: <= 16 beats
different:  > 16 beats
```

For hardtechno, phrase-near is not good enough for jump pads, but it may be
acceptable for review suggestions.

### Slot distance

Do not compare only "there is a cue near here." Compare role/slot intent:

```text
same_slot
compatible_role
different_role
extra_candidate
missing_candidate
```

Example:

- Rekordbox puts a cue at first drop in slot A.
- vibemix puts first mix-in at A and first drop at D.
- Time overlap may look worse, but role/slot semantics are better for our
  product.

This is why INTEL-18 review labels are the final source of truth.

## Scorecards

### Per-track cue map score

Report:

```text
track_id
genre
anlz_mood
anlz_phrase_count
baseline_cue_count
vibemix_cue_count
required_slots_filled
review_required_count
suppressed_count
human_overwrite_risk_count
xml_export_ok
```

### Per-slot quality score

For A, D, F first:

```text
slot_keep
slot_maybe
slot_move
slot_delete
move_distance_beats
source
confidence_bin
reason_codes
```

### Comparative lift score

Against each baseline:

```text
vibemix_kept_and_baseline_missing
baseline_kept_and_vibemix_missing
both_kept_same_or_near
both_present_vibemix_preferred
both_present_baseline_preferred
both_deleted
```

### Transition utility score

This is the moat metric:

```text
transition_slate_without_cue_operability
transition_slate_with_vibemix_cues
transition_slate_with_rekordbox_auto_cues
```

Measure:

- top-1 accepted transition;
- top-3 contains accepted transition;
- selected cue pair accepted;
- cue pair changed after human review;
- live-mode suppressions due no operable cue.

If Rekordbox auto-cues place good per-track markers but do not improve
transition_slate, vibemix still wins on set-aware value.

## Evaluation slices

Always report by slice:

```text
genre: techno/hardtechno, house, dnb, pop/open, unknown
ANLZ mood: high, mid, low, none
source path: ANLZ, fallback, DJ, mixed
track length bucket
phrase count bucket
streaming/local availability
human-cued vs uncued
```

Kaan's library-specific first slice:

```text
hardtechno / techno
ANLZ high mood
ANLZ mid mood
no human cues
```

## Private label schema extension

INTEL-15 should include baseline preference:

```json
{
  "review_item_type": "cue_baseline_comparison",
  "track_id": "track_001",
  "section_snapshot_id": "sec_snap_001",
  "baseline_a": "rekordbox_auto",
  "baseline_b": "vibemix_intel18",
  "slot": "D",
  "preference": "b",
  "distance_beats": 0,
  "reason": "vibemix put the main drop on D; rekordbox used A for the same jump"
}
```

Allowed `preference`:

```text
a
b
tie
neither
unclear
```

## Data artifacts

Private, not committed:

```text
.local/eval/cues/YYYYMMDD/before.collection.xml
.local/eval/cues/YYYYMMDD/after_rekordbox_auto.collection.xml
.local/eval/cues/YYYYMMDD/vibemix_proposals.jsonl
.local/eval/cues/YYYYMMDD/reviews.jsonl
.local/eval/cues/YYYYMMDD/scorecard.json
```

Committed test fixtures should be synthetic:

```text
tests/intel/fixtures/cue_baseline_before.xml
tests/intel/fixtures/cue_baseline_after.xml
tests/intel/fixtures/smart_cue_proposals.json
```

## Implementation handoff

Add:

```text
scripts/eval/intel_cue_baseline_compare.py
tests/eval/test_intel_cue_baseline_compare.py
```

Responsibilities:

- parse two Rekordbox XML snapshots;
- detect added/changed/removed `POSITION_MARK`s;
- normalize hot cue `Num` to A-H/I-P where present;
- convert memory cues to `slot=None`;
- align marks to beatgrid when available;
- load vibemix `SmartCueProposal` JSONL;
- compute per-track/per-slot/comparative scorecards;
- write redacted JSON output.

Current implementation:

- fixture mode compares the synthetic before/after XML snapshots against
  committed smart-cue proposal fixtures;
- private mode accepts explicit `--before`, `--after`, `--proposals`, and
  `--tracks` paths and emits only redacted cue facts;
- scorecard reports per-track counts, per-slot distance bands, snapshot diffs,
  and comparative lift (`vibemix_kept_and_baseline_missing`,
  `baseline_kept_and_vibemix_missing`, `both_kept_same_or_near`);
- this first slice uses BPM-derived beat distance when track metadata has BPM.
  Full beatgrid-index alignment remains the next quality increment for private
  real-library evals.

Do not include:

- calls into Rekordbox UI;
- process-memory reading;
- `master.db` access;
- private XML outputs in repo;
- automatic threshold changes.

## Acceptance gates

Before claiming smart-cue quality:

```text
uv run pytest -q tests/eval/test_intel_cue_baseline_compare.py
uv run pytest -q tests/library/test_smart_cues.py
```

Before broad product default:

```text
20 manually reviewed tracks
Rekordbox auto baseline imported for the same tracks when feasible
vibemix >= Rekordbox auto on A/F keep-or-maybe rate
vibemix improves transition utility in at least one tested crate
0 accidental overwrite risks
0 invalid XML exports
```

Before live cue pill:

```text
50 reviewed tracks
confidence calibration checked by slot/source/genre
cue_operability improves transition top-3 accepted rate
all exact timing claims remain gated by INTEL-06 playhead confidence
```

## Product interpretation rules

If Rekordbox auto wins:

- do not fight the data;
- use Rekordbox auto cues as imported DJ/baseline evidence where safe;
- focus vibemix on transition_slate, explanations, and set-aware cue pairing.

If vibemix wins on A/F but loses on D:

- keep mix-in/mix-out automation;
- make drop cues review-first;
- adjust genre policy only through INTEL-15 labels.

If vibemix wins only on high-mood ANLZ:

- gate export-ready cues to high-mood ANLZ first;
- keep mid/low mood review-only.

If both systems fail:

- the issue is likely source structure, not slot policy;
- prioritize better section labels, gold labels, or model benchmark work.

## Open questions

1. Can we reliably detect which cues were generated by Rekordbox CUE(auto), or
   only infer them from before/after XML diff?
2. Should Kaan run Rekordbox's personal CUE trend training on at least 30
   reviewed tracks before treating it as the strongest baseline?
3. Should memory cues count in the same scorecard as hot cues, or only as
   navigation/reference markers?
4. Should a baseline comparison UI show anonymous A/B proposals to reduce bias?

## Success definition

Smart cue excellence is real only when we can say:

```text
Against Rekordbox auto-cues and naive ANLZ cues, vibemix's cue policy improved
reviewed cue usefulness and/or transition utility, with no overwrite risk and
replayable provenance.
```

That is the standard. Anything softer is vibes pretending to be evidence.
