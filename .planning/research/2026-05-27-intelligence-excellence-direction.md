# Direction: intelligence excellence - data-grounded musical context engine

**Date:** 2026-05-27
**Lane:** intelligence / data / agentic engine / grounding / musical context
**Status:** pre-roadmap research and build-prep; intentionally avoids codebase cleanup work

## Spec ledger

- INTEL-01: `.planning/research/2026-05-27-intel-01-anlz-structure-spec.md` -
  Rekordbox ANLZ as the primary offline structure source.
- INTEL-02: `.planning/research/2026-05-27-intel-02-agentic-musical-context-spec.md` -
  section objects, transition slates, musical context packets, and grounded
  agent decisions.
- INTEL-03: `.planning/research/2026-05-27-intel-03-data-eval-excellence-spec.md` -
  data quality gates, section-retrieval evals, transition scorecards, and
  agent-grounding validation.
- INTEL-04: `.planning/research/2026-05-27-intel-04-implementation-handoff.md` -
  file-by-file execution plan, test gates, build order, and collision notes.
- INTEL-05: `.planning/research/2026-05-27-intel-05-taste-learning-flywheel-spec.md` -
  structured feedback ledger, deterministic taste model, profile projection,
  and privacy/consent gates.
- INTEL-06: `.planning/research/2026-05-27-intel-06-live-musical-awareness-spec.md` -
  playhead estimates, section position, blend suppression, and live timing
  confidence without Rekordbox memory reads or vision.
- INTEL-07: `.planning/research/2026-05-27-intel-07-musical-ontology-transition-grammar.md` -
  section-role ontology, genre-aware transition grammar, cue semantics, and
  deterministic explanation/risk rules.
- INTEL-08: `.planning/research/2026-05-27-intel-08-roadmap-execution-map.md` -
  dependency graph, shippable cuts, acceptance gates, and first implementation
  PR sequence.
- INTEL-09: `.planning/research/2026-05-27-intel-09-context-compiler-agent-contract.md` -
  musical context compiler, bounded agent envelope, structured decision schema,
  and deterministic validator for section-aware intelligence.
- INTEL-10: `.planning/research/2026-05-27-intel-10-section-index-data-excellence.md` -
  section-level vector/metadata store, ingest/cache strategy, audit gates, and
  migration plan for searchable musical moments.
- INTEL-11: `.planning/research/2026-05-27-intel-11-transition-slate-scorer.md` -
  deterministic section-transition scoring, component weights, risk penalties,
  confidence gates, diversity rules, and test plan.
- INTEL-12: `.planning/research/2026-05-27-intel-12-grounded-intelligence-tool-surface.md` -
  run-scoped grounding holders and tool/action API for track sections,
  transition slates, smart-cue proposals, explanations, and safe exports.
- INTEL-13: `.planning/research/2026-05-27-intel-13-contract-consistency-map.md` -
  canonical IDs, source enums, holder names, module targets, scoring weights,
  and invariants to prevent cross-spec drift during implementation.
- INTEL-14: `.planning/research/2026-05-27-intel-14-representation-benchmark-strategy.md` -
  representation benchmark strategy for section-level CLAP, future music
  foundation models, temporal audio-language models, and product model
  governance.
- INTEL-15: `.planning/research/2026-05-27-intel-15-gold-label-protocol.md` -
  private gold-label schema, active sampling protocol, splits, rubrics,
  redaction rules, and evaluation/taste handoff for Kaan's musical judgements.
- INTEL-16: `.planning/research/2026-05-27-intel-16-implementation-readiness-checklist.md` -
  builder-facing PR evidence bundle, entry conditions, no-go checks, and
  acceptance checklists for the first intelligence implementation sequence.
- INTEL-17: `.planning/research/2026-05-27-intel-17-provenance-replay-contract.md` -
  provenance/run-manifest contract for sections, vectors, transitions, context
  packets, decisions, labels, scorecards, redaction, and replay tiers.
- INTEL-18: `.planning/research/2026-05-27-intel-18-smart-cue-policy.md` -
  smart hot cue slot policy, proposal contract, Rekordbox Intelligent Cue
  Creation baseline, review/export thresholds, and set-aware cue operability.
- INTEL-19: `.planning/research/2026-05-27-intel-19-cue-baseline-comparison.md` -
  smart-cue evaluation harness for comparing vibemix proposals against
  Rekordbox Intelligent Cue Creation, naive ANLZ, DJ cues, and transition
  utility.
- INTEL-20: `.planning/research/2026-05-27-intel-20-agentic-decision-runtime.md` -
  runtime state machine for deterministic/model-assisted decisions, validation
  degradation, live-pill silence policy, latency budgets, and replay traces.
- INTEL-21: `.planning/research/2026-05-27-intel-21-musical-claim-evidence-contract.md` -
  typed musical claim ledger, evidence requirements, allowed language,
  validator rules, and claim-level eval gates.
- INTEL-22: `.planning/research/2026-05-27-intel-22-synthetic-fixture-corpus.md` -
  privacy-safe synthetic fixture corpus for sections, vectors, transitions,
  cues, claims, decisions, traces, labels, and redaction tests.
- INTEL-23: `.planning/research/2026-05-27-intel-23-research-backed-musical-intelligence-map.md` -
  source-backed bet map for ANLZ, section embeddings, transition scoring,
  set-aware cueing, live awareness, model explanations, and differentiation
  against rekordbox Intelligent Cue Creation.

## Thesis

vibemix should not try to make the LLM "hear harder." The excellent product is a
grounded musical intelligence system where deterministic/local analyzers build a
rich graph of musical objects, and the agent reasons over those objects.

The leap is:

> track-level vibe search -> section-level, transition-aware musical planning.

The unit of intelligence becomes the **section**:

- this 16/32-bar phrase is an intro / build / breakdown / drop / outro;
- it has a beatgrid, downbeat phase, BPM, key, energy, timbral/semantic embedding,
  and confidence/provenance;
- it can mix into or out of another section with a scored reason.

The LLM is then a conductor and explainer, not the source of truth. It can choose
among grounded candidates, ask taste questions, explain risks, and write DJ-facing
language. It must not invent musical facts.

INTEL-20 sharpens that into a runtime rule: live pressure defaults to
deterministic, validator-gated decisions; model assistance is optional,
discardable, and mainly valuable in prep/chat.

INTEL-21 sharpens "grounded" further: the agent is allowed to speak only claims
that deterministic code issued with evidence, confidence, and language bounds.

## Current evidence in this repo / Kaan's rig

### Grounded data already exists

- `CueAnchor` is the cross-session cue contract:
  `label/start_s/end_s/confidence/source` in `src/vibemix/library/cue_types.py`.
- `LibraryToolset` already provides the grounded set-prep tool spine:
  `discover_pool`, `get_track_energy`, `sequence_set`, `export_set`,
  `quote_moment`, `retrieve_dj_knowledge`, with a per-run `seen` gate.
- `SuggestionService` / `next_suggestion` exist, but are still **track-level**:
  stored seed vector -> nearest next track with optional Camelot/BPM refinement.
- `ingest.py` already supports cue-anchored CLAP embedding over <=80s windows,
  but today it still collapses the windows back to one track vector.
- `sequencer.py` already solves set-level ordering with energy curves,
  Camelot/BPM gates, coherence, and honest relaxed transitions.
- `EvidenceRegistry` is the right anti-hallucination spine for live claims.

### Rekordbox data is the floor

Local probe on this machine, 2026-05-27:

```text
ANLZ .EXT files:          493
with PSSI phrase data:    449
parse errors:             0
mood distribution:        high=346, mid=101, low=2
phrase count min/med/max: 1 / 19 / 158
```

Interpretation:

- Phrase coverage is ~91%.
- 77% of parsed tracks are Rekordbox "high mood", whose phrase vocabulary maps
  cleanly to dance functions: intro / up / down / chorus / outro.
- Kaan's library is therefore already rich enough for section-aware intelligence.
- This data beats a handcrafted hardtechno DSP cue heuristic. Use the heuristic
  only when Rekordbox has no phrase data.

## External research anchors

These sources reinforce the architecture:

- Rekordbox ANLZ `.EXT` files contain `PSSI` song-structure tags, `PPTH` path tags,
  `PQT2` beatgrid, and cue tags; pyrekordbox documents the format and the PSSI
  mood vocabularies.
  Source: https://pyrekordbox.readthedocs.io/en/stable/formats/anlz.html
- Rekordbox XML supports `TEMPO` beatgrid and `POSITION_MARK` cue/loop records,
  with start/end in seconds and hot-cue numbering.
  Sources: https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf,
  https://pyrekordbox.readthedocs.io/en/latest/generated/pyrekordbox.rbxml.html
- CLAP is correct for language/audio retrieval, but not for temporal ordering by
  itself. Standard CLAP struggles with temporal information; T-CLAP exists
  specifically to improve that gap.
  Sources: https://arxiv.org/abs/2206.04769,
  https://arxiv.org/abs/2404.17806
- Newer music representations (MERT, MuQ / MuQ-MuLan) are promising future
  candidates for music-specific embeddings, but should be evaluated before any
  product swap.
  Sources: https://arxiv.org/abs/2306.00107,
  https://arxiv.org/abs/2501.01108,
  https://github.com/tencent-ailab/MuQ
- Real DJ-mix analysis shows DJs usually keep pitch/tempo changes modest,
  transitions cluster around phrase structure, and cue choices show shared
  rules. This validates beat/phrase-aware transition scoring.
  Sources: https://arxiv.org/abs/2008.10267,
  https://mir-aidj.github.io/djmix-analysis/
- Raveform is a new EDM/DJ-mix structure dataset with beats, alignments, and
  expert structural annotations. It is ideal for future evaluation of section
  labels and transition timing.
  Sources: https://reference-global.com/article/10.5334/tismir.288,
  https://mir-aidj.github.io/raveform/
- CUE-DETR and earlier cue-point research validate cue estimation as a real MIR
  task, but for Kaan's Rekordbox library ANLZ should be the primary source and
  ML cue detection the fallback.
  Sources: https://arxiv.org/abs/2407.06823,
  https://arxiv.org/abs/2007.08411
- BeatNet is a plausible future online beat/downbeat tracker for live playhead
  alignment when direct Rekordbox transport is unavailable.
  Source: https://huggingface.co/papers/2108.03576
- All-In-One jointly predicts beats, downbeats, segment boundaries, and labels;
  it is useful as a future fallback/reference, but its PyTorch/NATTEN footprint
  makes it a bench candidate, not an immediate product dependency.
  Sources: https://arxiv.org/abs/2307.16425,
  https://github.com/mir-aidj/all-in-one

## Product direction: three intelligence modes

### 1. Smart hot cueing

Per-track preparation. The system places an opinionated cue map:

- A: mix-in / first strong intro phrase
- B: first workable groove or build
- C: breakdown / tension reset
- D: main drop / chorus landing
- E: second drop or late high-energy landing
- F: mix-out / outro
- G/H: optional loop-safe or rescue anchors

Rules:

- DJ-authored cues win.
- Rekordbox ANLZ PSSI phrases are the primary auto source.
- CUE-DETR / `cue_detect` are fallback sources.
- Every cue carries `source` and confidence; low-confidence cues are review
  candidates, not asserted truth.
- Export path is Rekordbox XML first; never mutate `master.db`.

Reality check: Rekordbox 7 already has Intelligent Cue Creation. Our product
bar is not "auto-place cues"; it is set-aware, provenance-tracked, explainable,
reviewable cue maps that feed transition planning. INTEL-18 is the canonical
policy for this; INTEL-19 is the comparison harness that proves whether it
beats the Rekordbox baseline where it claims to.

This is valuable, but it is still the substrate. The larger move is set-aware
mixing.

### 2. Set-aware mix points

For a planned set or candidate next track, score **section -> section** pairs:

```text
current track section i (e.g. outro/build/drop tail)
    -> candidate track section j (e.g. intro/groove/drop)
```

Each transition candidate should carry:

- `from_track_id`, `from_section_id`, `from_role`, `from_start_s`, `from_end_s`
- `to_track_id`, `to_section_id`, `to_role`, `to_start_s`, `to_end_s`
- technical facts: BPM delta, Camelot relation, phrase length, downbeat snap
- musical facts: energy delta, semantic/timbral similarity, density/sub/brightness
- operational facts: recommended cue slot, bars to start, loop option
- scores: compatibility, excitement, risk, confidence
- explanation: one or two grounded reasons, never a paragraph of filler

This changes the pill from:

> play this similar track next

to:

> bring `Track B` from cue B in 16 bars; its intro groove matches the current
> outro energy, key is compatible, and the drop lands after one phrase.

### 3. Live suggestion pill

Live mode is the same engine with a live state source:

- identity: now-playing + deck inference;
- transport: MIDI in/out state when available;
- playhead: best available estimate;
- structure: ANLZ section map;
- current musical context: current/next section plus confidence.

If playhead confidence is weak, the pill should degrade:

- high confidence: "in 16 bars, start cue B";
- medium confidence: "next workable entry is cue B";
- low confidence / blend: suppress timing claim, show prep-only suggestion.

The live pill must be confident enough to be useful and humble enough not to
break trust.

## The core data model we need

### `TrackIntelligence`

One row per track:

```text
track_id
audio_path
duration_s
bpm / beatgrid / downbeat anchors
key / camelot
energy_summary
sections: list[SectionIntelligence]
source_coverage: {dj, anlz, auto, fallback}
version / content_hash / generated_at
```

### `SectionIntelligence`

One row per phrase/section:

```text
section_id
track_id
role: intro | build | breakdown | drop | outro | groove | bridge | unknown
start_s / end_s
start_beat / end_beat
bar_count
confidence
source: dj | anlz | auto | fallback
source_detail: hotcue | pssi | cue_detr | dsp | all_in_one | whole_track
energy_features
semantic_embedding
mix_in_score
mix_out_score
recommended_hotcue_slot?
```

### `TransitionCandidate`

One row per possible section-pair:

```text
from_section_id
to_section_id
score_total
score_components:
  semantic_similarity
  harmonic_compatibility
  bpm_fit
  energy_shape_fit
  role_compatibility
  phrase_alignment
  novelty_or_taste
  risk_penalty
confidence
warnings
```

### `MusicalContextPacket`

The compact object handed to the agent:

```text
now:
  deck, track_id, current_section, next_section, bars_to_boundary, confidence
candidate_slate:
  top transition candidates with facts + warnings
constraints:
  desired vibe, energy direction, user taste, played_ids, avoid_ids
allowed_actions:
  suggest_next, place_cues, build_set, ask_question, explain
citations/provenance:
  every track/section/fact source
```

This is the bridge between audio + metadata and language.

## Scoring model for section-aware suggestions

Use deterministic scoring first. The agent can choose among the slate, but it
should not free-rank raw tracks.

Suggested score:

```text
score =
  0.24 * semantic_section_similarity
  0.16 * harmonic_fit
  0.12 * bpm_fit
  0.12 * energy_shape_fit
  0.13 * role_fit
  0.09 * phrase_alignment_fit
  0.07 * cue_operability
  0.05 * taste_fit
  0.02 * novelty
  - risk_penalty
```

Initial role-fit matrix:

| From | To | Fit |
|------|----|-----|
| outro | intro/groove | high |
| breakdown | intro/groove/drop-build | medium/high |
| build | drop | high for impact, risky for smoothness |
| drop | intro | medium, depends on energy drop |
| peak/drop | peak/drop | high intensity, high fatigue risk |
| unknown | known | allowed but lower confidence |

Risk penalties:

- both keys known and incompatible;
- BPM delta outside configured tolerance;
- section too short for 16/32-bar blend;
- current playhead confidence low;
- candidate has only DSP fallback structure;
- repeated artist/near-duplicate;
- energy cliff when the stated intent is "keep pressure."

## Embedding posture

Current CLAP is good enough for **semantic/timbral section similarity**:

- keep local CLAP ONNX as product default;
- embed each section/window separately;
- store both section vectors and a pooled track vector;
- mean-center section queries just like track queries;
- never let CLAP own BPM/key/temporal ordering.

Future bench candidates:

- MuQ-MuLan: music-text embeddings with stronger music-specific claims;
- MERT/MuQ hidden states: audio-only section similarity and tagging;
- T-CLAP/CoLLAP family: temporal/context-aware retrieval;
- All-In-One: fallback structure labels when no DJ-software structure exists.

Rule: no model swap without a bench that measures top-k transition acceptance,
cue timing, latency, install size, and local CPU performance.

## Agentic engine contract

The agent should run a planner loop over grounded tools:

```text
understand brief
  -> discover candidates
  -> build / fetch TrackIntelligence
  -> generate transition slate
  -> choose and explain
  -> export cues/set or ask a taste question
```

Non-negotiables:

- The agent may only name tracks surfaced by grounded discovery tools.
- The agent may only name sections/cues from `TrackIntelligence`.
- The agent may explain score components, but not invent hidden musical facts.
- The agent should be allowed to say "I don't have enough confidence for timing."
- The final UI language should be terse: what to play, when to enter, why it works.

The right tool additions after ANLZ ingest:

- `get_track_structure(track_id)` -> beatgrid + sections + cue slots
- `embed_sections(track_id | track_ids)` -> cached section vectors
- `rank_transition_from(track_id, section_id?, candidates, constraints)` -> slate
- `place_hot_cues(track_id, policy)` -> proposed/exportable cues
- `build_transition_plan(track_ids, curve, style)` -> ordered set + cue points

## Evaluation gates

### Offline metrics

- ANLZ coverage and parse success by library.
- Section-role coverage by source: DJ / ANLZ / CUE-DETR / DSP.
- Cue timing agreement:
  - compare proposed cues to DJ-authored cues when present;
  - compare against CUE-DETR and Raveform/DJ Mix Dataset where usable.
- Transition ranking:
  - top-k candidate contains known DJ-mix transition pair / compatible cue region;
  - transition warnings match actual relaxed edges.
- Grounding:
  - 0 invented track ids;
  - 0 invented sections;
  - no timing claim when playhead confidence is below floor.

### Human gates

- Kaan ear-check on 20 hardtechno tracks:
  - do ANLZ boundaries feel right?
  - do auto hot cues need only small nudges?
  - does the suggested next cue feel DJ-useful?
- Set-prep A/B:
  - current track-level sequencer vs section-aware sequencer;
  - judge flow, surprise, mixability, and trust.

### Live gates

- Pill suppresses timing during blends.
- Pill never says "16 bars" unless playhead confidence proves it.
- Pill remains useful in prep-only fallback.

## Roadmap shape

### INTEL-01 - ANLZ as primary structure source

Implement `anlz_ingest.py` and insert it into `excerpt.py`:

```text
DJ cues -> ANLZ PSSI -> CUE-DETR -> DSP fallback -> whole-track fallback
```

Deliverables:

- `source="anlz"` in `CueSource`;
- PSSI -> `CueAnchor` mapping;
- PPTH/path index with duplicate handling;
- tests with fixture ANLZ tags or parsed fixture objects;
- coverage report command.

### INTEL-02 - section vector index

Stop collapsing everything to one track vector. Persist section vectors:

```text
section_id = <track_id>#s<zero_padded_ordinal>
embedding = CLAP(window)
metadata = source/confidence/role/energy/key/bpm
```

Keep pooled track vectors for existing search, but power transition matching
from section vectors.

### INTEL-03 - transition slate engine

Pure deterministic `rank_transition_candidates(...)`:

- inputs: current section context + candidate pool + constraints;
- output: `TransitionCandidate[]`;
- no LLM;
- unit-test with synthetic sections and known scoring behavior.

### INTEL-04 - smart hot cue export

Turn section anchors into a hot-cue policy and export to Rekordbox XML:

- stable slot assignment;
- confidence/provenance naming;
- no DB mutation;
- review-first when confidence is low.

### INTEL-05 - agent context packet

Add a compact musical-context tool/output shape so Codex/Gemini receive:

- current state;
- transition slate;
- score components;
- warnings;
- allowed actions.

This is where "Gemini becomes music-aware" without relying on raw audio hearing.

### INTEL-06 - live playhead confidence

Only after prep and section scoring work:

- now-playing + deck inference baseline;
- MIDI transport;
- optional BeatNet/downbeat + ANLZ beatgrid alignment;
- transition confidence gate.

## Strong recommendation

Build in this order:

1. **ANLZ structure ingest** - biggest immediate intelligence win, low risk.
2. **Section vector index** - the real unlock for set-aware matching.
3. **Transition slate engine** - makes the pill and set builder excellent.
4. **Smart hot cue export** - visible DJ utility and data feedback loop.
5. **Agent musical context packet** - lets the LLM explain and choose without hallucinating.
6. **Live playhead alignment** - turns prep intelligence into live magic.

This is the excellent version: a DJ-native intelligence layer built from real
music data, not a chat model pretending it understands a waveform.
