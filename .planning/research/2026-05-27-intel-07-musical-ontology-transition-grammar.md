# INTEL-07 spec - musical ontology and transition grammar

**Date:** 2026-05-27
**Scope:** section roles, genre-aware transition rules, cue semantics, and risk flags
**Depends on:** `.planning/research/2026-05-27-intel-06-live-musical-awareness-spec.md`
**Code posture:** no product code changed in this research pass

## Goal

Give section-aware intelligence a musical rulebook.

INTEL-01 can recover sections. INTEL-02 can score section-to-section candidates.
INTEL-06 can map the live playhead to a current section. But the app still needs
an explicit ontology:

- what a role means;
- which role pairs are useful DJ transitions;
- which role pairs are risky;
- how genre changes the rule;
- what cue slots should mean;
- what the agent is allowed to say about each role.

Without this layer, the system has data but not enough musical context.

## Existing repo facts

Current code has:

- `src/vibemix/state/genre/profiles/*.json`
  - signal profiles for disco, drum_and_bass, house, pop, psytrance, techno;
  - techno profile label currently covers "Techno / Hard Tek / Acidcore";
  - profiles tune BPM range, band signature, vocal likelihood, phase thresholds.
- `src/vibemix/library/sequencer.py`
  - track-level set ordering with energy curves, Camelot/BPM gates, coherence,
    relaxed transitions, and cue-structure warnings.
- `CueAnchor`
  - coarse dance labels: intro, build, breakdown, drop, outro.
- INTEL specs
  - proposed `SectionIntelligence.role` expands to intro, build, breakdown,
    drop, outro, groove, bridge, unknown.

Missing:

- a canonical role vocabulary;
- role-pair matrix;
- genre-specific transition weights/risk flags;
- deterministic explanations derived from the matrix.

## Canonical role vocabulary

### Core roles

```text
intro
groove
build
breakdown
drop
outro
bridge
unknown
```

`CueAnchor` may stay at its five-label vocabulary for compatibility. Full
section intelligence should use the expanded role vocabulary.

### Role definitions

#### `intro`

Function:

- first mixable region;
- low/medium density;
- often percussion, noise, or partial groove;
- good target for incoming cue.

Agent may say:

- "mix-in point";
- "intro";
- "clean entry" only when density/energy supports it.

Risks:

- vocal intro may be undesirable in hardtechno/techno;
- too short for long blends;
- harmonic content may be sparse, so key score should be de-emphasized.

#### `groove`

Function:

- stable body section without strong rise/fall;
- usable for long blends and texture matching;
- common in techno/hardtechno where "verse" labels are not meaningful.

Agent may say:

- "groove";
- "stable section";
- "tooly entry" when energy/density supports it.

Risks:

- can feel flat after a peak unless energy plan wants a hold;
- may not create enough lift for festival/peak-time curve.

#### `build`

Function:

- rising tension;
- should usually resolve into drop or breakdown;
- useful as incoming tension layer or outgoing handoff.

Agent may say:

- "build";
- "tension section";
- "rising section" when energy slope supports it.

Risks:

- build into build can stack tension without payoff;
- build into breakdown can feel like a fake-out unless intentional.

#### `breakdown`

Function:

- energy/bass reduction;
- tension reset;
- atmosphere/vocal/melodic focus;
- useful for breathers and key/mood pivots.

Agent may say:

- "breakdown";
- "reset";
- "bass drop-out" only when sub/low features support it.

Risks:

- breakdown into intro may drain floor energy;
- harmonic clashes matter more if breakdown is melodic.

#### `drop`

Function:

- full-energy landing;
- high-density payoff;
- main crowd-impact anchor.

Agent may say:

- "drop";
- "landing";
- "full-energy section" when energy/confidence supports it.

Risks:

- drop-to-drop can be exciting but fatiguing;
- exact timing matters;
- key clashes are more audible when both drops are tonal/melodic.

#### `outro`

Function:

- outgoing mix region;
- lower novelty;
- percussion/tail cleanup;
- strong source section for transitions.

Agent may say:

- "mix-out";
- "outro";
- "tail" when section is near end.

Risks:

- too short or too empty can create a dead handoff;
- if outro is melodic, harmony still matters.

#### `bridge`

Function:

- ambiguous connector;
- may be fill, pre-drop, post-drop, or short reset.

Agent may say:

- "bridge";
- "connector";
- avoid strong claims unless confidence is high.

Risks:

- role ambiguity;
- treat as low-confidence build/breakdown depending on features.

#### `unknown`

Function:

- boundary exists but semantic role is not reliable.

Agent may say:

- nothing role-specific;
- "section boundary" if confidence permits.

Risks:

- never use as the reason for an exact cue recommendation.

## ANLZ role mapping refinement

Keep INTEL-01 mappings, but for section intelligence add these refinements:

### Mood 1 high

```text
Intro -> intro
Up    -> build
Down  -> breakdown
Chorus -> drop
Outro -> outro
unknown kinds -> unknown
```

If an `Up` phrase is long and energy slope is flat, role may be downgraded to
`groove` with source label preserved.

### Mood 2/3 mid-low

```text
Intro  -> intro
Verse  -> groove by default, build only if energy slope rises
Bridge -> bridge/breakdown depending on sub/energy drop
Chorus -> drop only if energy/density rises; else groove
Outro  -> outro
```

This matters for techno: "verse" is often just a groove section, not a pop verse.

## Transition role matrix

Base score values before genre/taste modifiers:

| From -> To | Base | Notes |
|------------|------|-------|
| outro -> intro | 0.95 | safest classic blend |
| outro -> groove | 0.88 | good for rolling techno/tool sets |
| groove -> intro | 0.78 | live loop/long blend entry |
| groove -> groove | 0.72 | texture continuation; can be too flat |
| groove -> build | 0.76 | energy lift |
| build -> drop | 0.84 | tension payoff if phrase-aligned |
| build -> intro | 0.58 | resets tension; usually prep, not peak live |
| build -> breakdown | 0.52 | fake-out; genre/taste dependent |
| breakdown -> intro | 0.68 | reset/pivot; avoid overuse |
| breakdown -> build | 0.74 | rebuild from a reset |
| breakdown -> drop | 0.82 | impact cut; timing-sensitive |
| drop -> intro | 0.64 | energy drop; useful if planned |
| drop -> groove | 0.70 | rolling handoff |
| drop -> drop | 0.62 | high impact but high fatigue/risk |
| drop -> breakdown | 0.56 | dramatic reset; context-dependent |
| intro -> intro | 0.45 | usually too empty unless layering |
| intro -> drop | 0.50 | quick slam; must be intentional |
| unknown -> any | 0.35 | only if other scores are strong |
| any -> unknown | 0.35 | never a primary live recommendation |

Use as `role_score`, not as a hard gate. Hard gates still come from grounding,
confidence, and technical impossibility.

## Genre-aware modifiers

### Techno / hardtek / acidcore

Current repo profile: `techno.json`.

Biases:

```text
outro -> groove +0.08
groove -> groove +0.08
groove -> build +0.04
drop -> groove +0.05
drop -> drop -0.04 unless taste prefers slams
breakdown -> intro -0.04 in peak contexts
vocal_intro risk +0.10
harmonic_fit weight slightly lower for percussive sections
phrase_alignment weight high
```

Rationale:

- long, rolling, tool-like blends are normal;
- percussive sections often matter more than harmonic detail;
- phrase errors are very audible in locked 4/4 music;
- hardtek can tolerate energy pressure but not sloppy timing.

Recommended separate future profile:

```text
hard_tek
```

The current `techno` profile spans too wide a BPM/energy range for fine
transition policy. Split only after local eval proves enough examples.

### House / tech house / deep house

Biases:

```text
outro -> intro +0.05
breakdown -> build +0.05
build -> drop +0.06
drop -> drop -0.08
harmonic_fit weight higher for melodic/vocal sections
vocal_intro risk lower than techno
```

Rationale:

- classic phrase/harmonic blends work well;
- vocals and hooks matter more;
- drop stacking can feel messy unless carefully keyed.

### Drum and bass / jungle / neurofunk

Biases:

```text
breakdown -> drop +0.08
build -> drop +0.08
drop -> drop +0.04 only if BPM compatible and phrase locked
outro -> intro +0.04
phrase_alignment weight very high
bpm_fit weight high
```

Rationale:

- double drops and fast transitions are idiomatic but timing-sensitive;
- tempo range is narrow, so BPM mismatch is less acceptable;
- breakdown/drop grammar is central.

### Psytrance / goa / full-on

Biases:

```text
groove -> groove +0.06
build -> drop +0.05
breakdown -> build +0.06
drop -> drop -0.06
long_phrase_blend preferred
harmonic_fit lower than phrase/energy unless section is melodic
```

Rationale:

- long hypnotic evolution matters;
- too many abrupt jumps break trance flow;
- phase/phrase continuity is central.

### Disco / nu-disco / funk

Biases:

```text
outro -> intro +0.08
groove -> groove +0.04
breakdown -> intro +0.03
drop -> drop -0.10
vocal/hook collisions risk high
harmonic_fit weight high
```

Rationale:

- phrased, melodic, vocal/hook-aware transitions matter;
- key/hook clashes are more salient than in sparse techno.

### Pop / mainstream

Biases:

```text
intro -> drop +0.05 for quick-cut mode
breakdown -> drop +0.08
outro -> intro +0.04
drop -> drop -0.12
vocal_overlap risk high
hook_collision risk high
```

Rationale:

- recognizable hooks/vocals dominate;
- long blends can sound messy;
- quick cuts may beat long blends depending on taste.

## Risk flags

Canonical risk flags:

```text
role_unknown
role_low_confidence
phrase_length_short
phrase_length_long
phrase_alignment_weak
bpm_delta_large
harmonic_clash
harmonic_unknown
energy_drop_unplanned
energy_jump_large
drop_stack_fatigue
vocal_intro
vocal_overlap
hook_collision
melodic_breakdown_harmony_sensitive
percussive_section_key_deemphasized
cue_window_too_short
blend_window_active
playhead_uncertain
recently_played
same_artist_cluster
```

Risk flags are data. The agent can mention them, but should not invent them.

## Cue slot semantics

Smart hot cue slots should be stable enough that the DJ builds muscle memory.
INTEL-18 is the canonical detailed policy; this section defines the ontology
summary.

Default:

```text
A = first mixable intro/downbeat
B = first stable groove/build entry
C = breakdown/reset
D = main drop/landing
E = second drop or late high-energy landing
F = mix-out/outro
G = loop-safe utility anchor
H = rescue/alternate entry
```

Genre modifiers:

- techno/hardtek: B and F are often more important than D;
- DnB: C/D are high-value for double-drop prep;
- house/disco: A/F and harmonic cueing matter more;
- pop: D/hook timing may matter more than long mix windows.

Do not overwrite DJ-authored cues by default. Export a review XML layer.

## Explanation templates

Explanations must be short and grounded.

Allowed templates:

```text
role: "outro -> intro is the safest blend shape"
phrase: "32-bar phrase alignment"
energy: "incoming intro holds the outgoing energy instead of spiking it"
harmony: "Camelot move 8A -> 9A is compatible"
risk: "risk: vocal intro over a dense outgoing drop"
uncertainty: "timing is not locked, so use this as a prep cue"
```

Disallowed:

```text
"perfect transition"
"the crowd will love this"
"this drop is massive" unless energy/role evidence supports it
"you always prefer..." unless INTEL-05 profile projection supports it
```

## Data model additions

Add:

```python
@dataclass(frozen=True, slots=True)
class RoleSemantics:
    role: str
    mix_in_score: float
    mix_out_score: float
    energy_expectation: str
    tonal_sensitivity: str
    language_floor: float
```

```python
@dataclass(frozen=True, slots=True)
class TransitionGrammarRule:
    from_role: str
    to_role: str
    base_score: float
    risk_flags: tuple[str, ...]
    explanation_bits: tuple[str, ...]
```

```python
@dataclass(frozen=True, slots=True)
class GenreTransitionProfile:
    genre: str
    role_pair_adjustments: dict[tuple[str, str], float]
    score_weight_adjustments: dict[str, float]
    risk_adjustments: dict[str, float]
    cue_slot_priorities: tuple[str, ...]
```

## Proposed files

Add:

```text
src/vibemix/intel/musical_ontology.py
src/vibemix/intel/transition_grammar.py
src/vibemix/intel/genre_transition_profiles.py
tests/intel/test_musical_ontology.py
tests/intel/test_transition_grammar.py
```

If `intel/` package is deferred:

```text
src/vibemix/library/musical_ontology.py
src/vibemix/library/transition_grammar.py
```

Longer term data files:

```text
src/vibemix/intel/profiles/techno.json
src/vibemix/intel/profiles/house.json
...
```

Keep separate from `state/genre/profiles`: those profiles tune DSP detection;
these profiles tune transition policy. They may share names but not schema.

## Integration into scoring

INTEL-02 `role_score` should become:

```text
base role-pair score
+ genre role-pair adjustment
+ taste role-pair adjustment
- role confidence penalty
- risk penalties
```

Weight changes:

```text
techno/hardtek: phrase_alignment + role + semantic > harmony for percussive sections
house/disco: harmony + phrase + role > raw semantic
dnb: bpm + phrase + role > harmony
psytrance: phrase + energy_shape + semantic > quick energy jumps
pop: hook/vocal risk > long-blend defaults
```

## Evaluation

Add to INTEL-03:

```text
role_pair_accuracy
genre_modifier_ablation
risk_flag_precision_by_genre
explanation_grounding_rate
cue_slot_acceptance_by_role
```

Tests:

- role matrix returns expected base values;
- unknown roles never score as high-confidence live candidates;
- genre profile only adjusts, never fabricates facts;
- risk flags are deterministic for known inputs;
- explanation bits are drawn from score components/risk flags only;
- hardtechno/techno long-blend cases rank above pop-style drop stacking.

## Build order

### INTEL-07A: pure ontology

- Add role definitions and role-pair matrix.
- Tests only.
- No integration.

### INTEL-07B: genre transition profiles

- Add genre policy profiles separate from DSP profiles.
- Tests for schema and modifiers.

### INTEL-07C: scoring integration

- Feed role grammar into `transition_slate`.
- Emit risk flags and explanation bits.

### INTEL-07D: cue export integration

- Use INTEL-18 cue slot semantics when producing smart hot cue maps.
- Add genre-aware slot priority.

### INTEL-07E: eval and calibration

- Label local transition pairs by genre.
- Run role/genre ablations.
- Update thresholds only through INTEL-03 recalibration policy.

## Success definition

The transition engine is musically grounded when it can say:

```text
outro -> intro is technically safe, but for this hardtek context
outro -> groove is more useful because it preserves rolling pressure.
Timing is phrase-locked, key is compatible, and the incoming section has a
mixable 32-bar groove.
```

and every part of that explanation comes from:

- section roles;
- genre transition profile;
- BPM/key/phrase facts;
- risk flags;
- score components;
- taste model if available.

That is the musical context layer the agent was missing.
