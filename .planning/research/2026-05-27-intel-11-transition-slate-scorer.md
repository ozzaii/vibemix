# INTEL-11: deterministic section-transition slate scorer

**Date:** 2026-05-27
**Lane:** musical intelligence / transition scoring / grounded recommendations
**Depends on:** INTEL-02, INTEL-07, INTEL-09, INTEL-10
**Status:** build-prep spec; no product code touched

## Why this exists

INTEL-10 gives us searchable sections. INTEL-09 gives us a bounded agent context
contract. The missing middle is the deterministic engine that turns a current
section plus candidate destination sections into a ranked transition slate.

This scorer is the musical intelligence core. It should answer:

```text
Given the section that is playing or planned now,
which section of which track should enter next,
where should it enter,
how risky is it,
and why?
```

The agent should not search the whole library or improvise mix logic. It should
receive a small slate of already-scored candidates and either select, hold,
suppress, or explain.

## Current repo anchors

### `next_suggestion.py`

Current behavior:

- seed vector -> mean-centered track-level search;
- skip seed and played tracks;
- resolve every candidate through `RekordboxLibrary.lookup_by_id`;
- optional Camelot/BPM refinement;
- honest `None` when no grounded candidate qualifies.

Keep:

- grounding and honest silence;
- overfetch to survive seed/played/skew drops;
- metadata missing means degrade, not fabricate.

Upgrade:

- track vector -> section vector;
- one candidate track -> transition slate;
- simple `why` string -> structured reasons/risk flags.

### `sequencer.py`

Current behavior:

- pure-compute set ordering;
- energy curve presets;
- Camelot/BPM technical gates;
- beam search;
- relaxation ladder;
- cue-structure warning tags;
- missing metadata passes instead of collapsing the graph.

Keep:

- Python cosine ranking as the deterministic math path;
- strict-vs-relaxed distinction;
- risk tags instead of hidden flaws;
- "return partial rather than fabricate" posture.

Upgrade:

- track-to-track edge -> section-to-section edge;
- binary transition validity -> graded scoring;
- set-level cost -> live/prep transition slate.

### `harmonics.py`

Current behavior:

- `to_camelot()` normalizes safely;
- `compatible()` is conservative and suited to long melodic overlap;
- `is_clash()` flags only unambiguous same-letter clash bands;
- unknown key returns false for compatibility, but callers decide whether that
  becomes a pass, a penalty, or silence.

Keep:

- LLM never computes keys or intervals;
- deterministic code decides harmonic facts.

Upgrade:

- transition scorer should produce a graded `harmonic_score`, not only
  compatible/incompatible.

## Scope

Add a pure-compute module later:

```text
src/vibemix/intel/transition_scorer.py
tests/intel/test_transition_scorer.py
```

No model clients, no audio capture, no Tauri, no LiveKit, no filesystem writes.
The scorer consumes already-built data objects:

- current or planned source section;
- candidate destination sections from `SectionStore`;
- track metadata/features;
- role grammar from INTEL-07;
- optional taste weights from INTEL-05;
- optional live awareness from INTEL-06.

It emits deterministic `TransitionCandidate` rows for INTEL-09.

## Core data objects

### `TransitionScoringInput`

```python
@dataclass(frozen=True, slots=True)
class TransitionScoringInput:
    source: SectionRecord
    destinations: tuple[SectionRecord, ...]
    source_vector: np.ndarray | None
    destination_vectors: dict[str, np.ndarray]
    played_track_ids: frozenset[str]
    candidate_pool_track_ids: frozenset[str] | None
    genre_profile: str | None
    live_position: SectionPosition | None
    taste: TasteModelSnapshot | None
    mode: Literal["prep", "live"]
```

Rules:

- `destinations` must already be grounded section records from the section
  index or current set candidate pool.
- `candidate_pool_track_ids` is optional; when present, drop destinations
  outside the pool.
- `source_vector` can be absent. The scorer must still work from role/key/BPM.
- `destination_vectors` may be sparse. Missing vector means semantic score is
  neutral/unknown, not fabricated.

### `TransitionCandidate`

Use the INTEL-02 shape, but make score components explicit.

```python
@dataclass(frozen=True, slots=True)
class TransitionCandidate:
    candidate_id: str
    from_section_id: str
    to_section_id: str
    from_track_id: str
    to_track_id: str
    cue_slot: str | None
    start_in_bars: int | None
    score: float
    confidence: float
    components: TransitionScoreComponents
    risk_flags: tuple[str, ...]
    reasons: tuple[str, ...]
```

### `TransitionScoreComponents`

```python
@dataclass(frozen=True, slots=True)
class TransitionScoreComponents:
    semantic: float
    harmonic: float
    bpm: float
    energy_shape: float
    role: float
    phrase_alignment: float
    cue_operability: float
    taste: float
    novelty: float
    risk_penalty: float
```

All components except `risk_penalty` are normalized to `[0, 1]`. `risk_penalty`
is also `[0, 1]`, subtracted after weighted sum.

## Candidate generation

### Prep mode

Flow:

```text
track-level discovery pool
  -> load sections for pool tracks
  -> generate allowed source role -> destination role pairs
  -> score all section pairs
  -> return top N with diversity
```

Prep mode may generate many pairs, but it should cap before the agent:

- score over up to 300 pairs per current step;
- return top 12 to INTEL-09 context compiler;
- enforce diversity: no more than 3 candidates from the same destination track.

### Live mode

Flow:

```text
current live source section
  -> target roles from transition grammar
  -> section search over destination roles
  -> score top results
  -> return top 5 to context compiler
```

Live mode must not run at 10 Hz.

Recompute only when:

- active track changes;
- current section changes;
- next section changes;
- candidate pool/taste profile changes;
- user explicitly asks for a new suggestion.

## Hard filters

Apply before scoring.

Drop destination if:

- same `section_id` as source;
- same track and mode is live, unless explicit same-track loop/rescue mode is on;
- destination track is in `played_track_ids` and repeat mode is off;
- destination outside `candidate_pool_track_ids` when pool is supplied;
- destination duration/window is below minimum usable threshold;
- destination role is `unknown` and mode is live;
- destination source confidence is below mode floor;
- live blend suppression says "no recommendation."

Suggested floors:

```text
prep section confidence floor: 0.35
live section confidence floor: 0.55
live select confidence floor: 0.62
exact timing floor: 0.80
```

These mirror INTEL-06/09 and can be tuned after replay.

## Score formula

Start with the INTEL-02 weights, adding cue operability:

```text
base_score =
  0.24 * semantic
  0.16 * harmonic
  0.12 * bpm
  0.12 * energy_shape
  0.13 * role
  0.09 * phrase_alignment
  0.07 * cue_operability
  0.05 * taste
  0.02 * novelty
  - risk_penalty
```

Why this shape:

- semantic section similarity is important but not sovereign;
- harmonic/BPM matter enough to block weird jumps from looking good;
- role/phrase/cue make it a DJ transition instead of a playlist neighbor;
- taste/novelty are small nudges, not truth sources.

Normalize to:

```python
score = max(0.0, min(1.0, base_score))
```

Do not let any single component hard-dominate except hard filters and severe
risk flags.

## Component definitions

### Semantic score

If both source and destination vectors exist:

```text
semantic = clamp01((cosine + 1.0) / 2.0)
```

But section vectors are usually already positive in practice. After first audit,
calibrate by percentile:

```text
semantic = percentile_rank(cosine within candidate slate)
```

V1 recommendation:

- use raw normalized cosine first;
- log cosine distribution;
- switch to percentile only if the slate compresses too tightly.

If either vector is missing:

```text
semantic = 0.50
risk += "semantic_unknown"
confidence downweight
```

### Harmonic score

Use deterministic Camelot logic.

```text
unknown key on either side: 0.55
same key: 1.00
relative major/minor: 0.92
same-letter adjacent +/-1: 0.88
same-letter +/-2 energy move: 0.78
exact cross-letter diagonal +/-1: 0.72
neither/drift zone: 0.42
unambiguous clash: 0.12
```

Risk flags:

```text
key_unknown
harmonic_drift
harmonic_clash
```

Mode behavior:

- prep can keep `harmonic_drift` if other scores are strong;
- live should suppress `harmonic_clash` unless section roles are percussive and
  harmonic salience is low;
- harmonic score weight can drop for `intro/outro/groove` sections with sparse
  melodic content, but only when that sparseness is measured.

### BPM score

Use percent delta.

```text
delta = abs(dst_bpm - src_bpm) / src_bpm

<= 1.5%  -> 1.00
<= 3.0%  -> 0.90
<= 6.0%  -> 0.78
<= 8.0%  -> 0.58
<= 12.0% -> 0.35
else     -> 0.10
```

If either BPM is missing:

```text
bpm = 0.55
risk += "bpm_unknown"
```

Risk flags:

```text
tempo_push
tempo_jump
bpm_unknown
```

Never ask the model to compute BPM deltas.

### Energy shape score

Use both absolute energy and shape.

Inputs when available:

- source section energy start/mean/end;
- destination section energy start/mean/end;
- set curve target for prep;
- live current energy and next-section trajectory for live.

V1 fallback if only mean energy exists:

```text
energy_delta = dst_mean - src_mean
desired_delta = role_pair_desired_delta(from_role, to_role, curve_position)
energy_shape = 1.0 - clamp01(abs(energy_delta - desired_delta) / 60.0)
```

Examples:

```text
outro -> intro: desired delta -10 to +10
groove -> build: desired delta +5 to +25
build -> drop: desired delta +15 to +45
drop -> breakdown: desired delta -35 to -5
drop -> drop: desired delta -5 to +15 but fatigue risk rises
```

If energy is unknown:

```text
energy_shape = 0.50
risk += "energy_unknown"
```

### Role score

Lookup from INTEL-07 transition role matrix plus genre modifiers.

Implementation:

```python
role = base_role_matrix[(from_role, to_role)]
role += genre_modifier(genre_profile, from_role, to_role)
role += mode_modifier(mode, from_role, to_role)
role = clamp01(role)
```

Unknown roles:

- live: hard filter if destination role is unknown;
- prep: score 0.35, keep only if other scores are strong.

### Phrase alignment score

Use beat/bar metadata.

Inputs:

- source section remaining bars;
- destination section start beat;
- cue slot position;
- phrase length estimate;
- live playhead confidence.

Scoring:

```text
exact 16/32-bar alignment: 1.00
8-bar alignment: 0.82
4-bar alignment: 0.62
off-phrase but downbeat: 0.42
unknown: 0.50
off-beat: 0.10
```

Live mode:

- if playhead confidence below exact floor, do not emit exact timing;
- score can still use phrase structure, but candidate must carry
  `start_in_bars=None`.

Risk flags:

```text
phrase_unknown
phrase_short
off_phrase
timing_low_confidence
```

### Cue operability score

A candidate can be musically good but operationally annoying.

Score:

```text
DJ-authored cue at destination: 1.00
ANLZ-derived cue/section boundary: 0.82
auto ML/DSP cue: 0.65
section boundary but no cue slot: 0.52
fallback whole-track: 0.25
```

Modifiers:

- cue within first 64s for mix-in: +0.08;
- cue too close to end: -0.20;
- cue window shorter than 16 bars: -0.15;
- cue source confidence below 0.5: -0.20.

Risk flags:

```text
no_cue_slot
short_entry_window
auto_cue_review
fallback_entry
```

### Taste score

Taste is a nudge from INTEL-05, not a truth source.

Inputs:

- accepted/rejected similar role pairs;
- user edits to exported cue slots;
- repeated genre/context preferences;
- skip/accept history.

Score:

```text
0.50 neutral when no consent or no relevant taste
0.35 disliked pattern
0.65 liked pattern
0.80 strongly reinforced pattern
```

Do not feed raw feedback history to the scorer. Use deterministic aggregates.

### Novelty score

Avoid boring repeats without forcing chaos.

Inputs:

- played/recent tracks;
- recently suggested destination IDs;
- repeated artist/title similarity;
- same role pair repetition.

Score:

```text
0.50 neutral
0.20 repeated candidate shown recently
0.35 same artist/title cluster repeated
0.70 fresh but in-pool candidate
```

Novelty is a small weight. It should never rescue a bad transition.

### Risk penalty

Risk penalty is accumulated from flags.

Suggested v1:

```text
harmonic_clash:        0.30
tempo_jump:            0.24
off_phrase:            0.20
timing_low_confidence: 0.18
short_entry_window:    0.15
fallback_entry:        0.14
energy_cliff:          0.12
semantic_unknown:      0.08
bpm_unknown:           0.06
key_unknown:           0.06
energy_unknown:        0.05
```

Cap:

```text
risk_penalty = min(0.55, sum(flag_penalties))
```

Severe suppressors:

```text
live + harmonic_clash + melodic sections -> suppress
live + tempo_jump > 12% -> suppress
live + off_beat -> suppress
live + timing_low_confidence + exact timing requested -> suppress timing
```

## Confidence formula

Score answers "how good is it?" Confidence answers "how much can we trust the
facts behind the score?"

```text
confidence =
  0.22 * source_confidence_min
  0.18 * section_role_confidence_min
  0.16 * vector_presence_confidence
  0.14 * metadata_confidence
  0.14 * phrase_confidence
  0.10 * live_position_confidence
  0.06 * cue_confidence
```

Prep mode:

- if no live position, replace `live_position_confidence` with `1.0`.

Metadata confidence:

```text
both key and bpm known: 1.0
one missing: 0.7
both missing: 0.45
```

Vector presence:

```text
both section vectors: 1.0
destination only: 0.65
neither/source missing: 0.50
```

Live action floors:

```text
confidence < 0.50 -> suppress/hold
0.50..0.62 -> prep-only/quiet candidate
0.62..0.80 -> suggest without exact timing
>= 0.80 -> exact bars allowed if phrase score supports it
```

## Candidate ID generation

Use deterministic internal keys and short run-scoped public aliases.

```text
transition_key = sha256(strategy_version | mode | from_section_id | to_section_id | cue_slot)[:16]
candidate_id = tr_001, tr_002, ...
```

Why: canonical section IDs contain `#`, and future citation/tool grammars should
not depend on parsing nested delimiters. The stable key is for replay/debug; the
public `candidate_id` is a run-scoped holder alias.

For prompt/UI compactness, expose only aliases:

```text
tr_001, tr_002, ...
```

Rules:

- internal candidate stores `transition_key`;
- agent envelope exposes `candidate_id`;
- validator maps `candidate_id` back to the issued candidate object;
- never accept model-created IDs.

## Reason generation

Reasons should be deterministic snippets from components. The model may
paraphrase only after validator approval.

Reason templates:

```text
semantic >= 0.78:
  "section texture is close"

harmonic >= 0.88:
  "Camelot relationship is clean"

bpm >= 0.78:
  "tempo delta is workable"

role >= 0.80:
  "<from_role> into <to_role> is a strong role pair"

phrase_alignment >= 0.82:
  "entry lands on a phrase boundary"

cue_operability >= 0.82:
  "destination has a reliable cue"
```

Risk reason templates:

```text
harmonic_clash:
  "keys clash if both melodic layers overlap"

tempo_jump:
  "tempo jump needs a bridge or quick cut"

off_phrase:
  "entry is not phrase-clean"

no_cue_slot:
  "good section, but no exported cue slot yet"
```

Each candidate should carry:

- at most 2 positive reasons;
- at most 2 risk reasons;
- no prose paragraph.

## Diversity rules

After scoring, select top candidates with diversity:

- max 3 candidates per destination track in prep;
- max 1 candidate per destination track in live pill;
- prefer different cue slots when same track appears in prep;
- prefer different role pairs when scores are close;
- never show two candidates whose `to_section_id` is identical.

Tie-breaks:

```text
1. higher confidence
2. lower risk_penalty
3. higher score
4. earlier destination cue for live
5. stable candidate_id lexicographic order
```

Stable tie-breaks are important for replay tests and trust.

## Degradation policy

### Missing vectors

Keep candidate if role/key/BPM/phrase are strong, but flag:

```text
semantic_unknown
```

Do not claim "texture matches."

### Missing key

Keep with harmonic neutral score and flag:

```text
key_unknown
```

Do not claim harmonic fit.

### Missing BPM

Keep with BPM neutral score and flag:

```text
bpm_unknown
```

Do not claim tempo fit.

### No reliable cue

Prep:

- keep as smart-cue review candidate;
- `cue_slot=None`;
- reason: "needs cue export."

Live:

- suppress if no actionable cue and timing is weak;
- otherwise show track/section without cue slot only if UI supports it.

### Weak live playhead

Keep slate in background, but context compiler must withhold exact timing.

## API sketch

```python
def score_transition_slate(
    input: TransitionScoringInput,
    *,
    max_candidates: int,
    strategy_version: str = "v1-section-transition-score",
) -> tuple[TransitionCandidate, ...]:
    ...
```

Supporting pure functions:

```python
def harmonic_score(src: str | None, dst: str | None) -> tuple[float, tuple[str, ...]]
def bpm_score(src: float | None, dst: float | None) -> tuple[float, tuple[str, ...]]
def role_score(src_role: str, dst_role: str, genre: str | None) -> float
def phrase_alignment_score(...) -> tuple[float, tuple[str, ...]]
def cue_operability_score(section: SectionRecord) -> tuple[float, tuple[str, ...]]
def transition_confidence(...) -> float
```

All helpers should be import-light and deterministic.

## Test plan

### Component tests

- `test_harmonic_score_same_key_high`
- `test_harmonic_score_relative_high`
- `test_harmonic_score_clash_low_and_flagged`
- `test_harmonic_score_unknown_neutral_flagged`
- `test_bpm_score_within_three_percent_high`
- `test_bpm_score_tempo_jump_low_and_flagged`
- `test_role_score_uses_genre_modifier`
- `test_phrase_alignment_exact_sixteen_bars_high`
- `test_cue_operability_dj_cue_highest`

### Slate tests

- `test_scorer_drops_same_section`
- `test_live_drops_unknown_destination_role`
- `test_prep_keeps_unknown_role_low_score`
- `test_scorer_excludes_played_tracks`
- `test_scorer_respects_candidate_pool`
- `test_scorer_caps_live_one_candidate_per_track`
- `test_scorer_generates_stable_candidate_ids`
- `test_scorer_tie_breaks_are_stable`
- `test_missing_vector_does_not_crash_or_claim_texture`
- `test_harmonic_clash_live_melodic_suppresses`
- `test_low_playhead_confidence_removes_start_in_bars`

### Integration tests

- `test_section_store_results_feed_transition_scorer`
- `test_transition_slate_feeds_context_compiler`
- `test_context_validator_rejects_candidate_not_in_slate`
- `test_live_pill_never_recomputes_at_10hz`

### Eval gates

Use INTEL-03 scorecards:

- section retrieval beats track-only baseline on manually judged transitions;
- top-5 slate includes Kaan-approved transition >= target recall;
- live low-confidence suppressions outnumber unsafe timing claims;
- explanations mention only facts present in components/risk flags.

## Implementation order

1. Land pure component scorers with tests.
2. Land `TransitionCandidate` and slate scoring over synthetic `SectionRecord`.
3. Add diversity selection and stable tie-breaks.
4. Feed a fake `SectionStore` result into scorer.
5. Wire scorer to context compiler in prep mode only.
6. Add live mode after `LiveAwarenessSnapshot` exists.
7. Add eval scripts before using the live pill as a default surface.

## Anti-patterns

- Letting the LLM choose weights.
- Asking the LLM whether keys are compatible.
- Treating semantic cosine as proof of mixability.
- Dropping every candidate with missing metadata.
- Hiding relaxed/risky transitions from the UI.
- Returning five entries from the same destination track in live mode.
- Emitting exact bars when playhead confidence is low.
- Recomputing section search on every state tick.
- Expanding to ANN/KNN backend tricks before parity tests prove the need.

## Recommendation

Ship the scorer as deterministic, conservative, and inspectable:

- section search proposes candidates;
- scorer grades them;
- context compiler bounds what the agent sees;
- validator enforces what the agent may output;
- UI shows score/risk/reason in human DJ language.

This is the center of "intelligence excellence": musical judgment expressed as
auditable data, with the agent as a grounded explainer rather than a guessing
engine.
