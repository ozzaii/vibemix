# INTEL-14: representation benchmark strategy

**Date:** 2026-05-27
**Lane:** intelligence architecture / musical representations / eval discipline
**Depends on:** INTEL-02, INTEL-03, INTEL-10, INTEL-11, INTEL-13
**Status:** benchmark/governance spec; no product model swap approved

## Why this exists

The app's intelligence ceiling is no longer "can we embed tracks?" It is:

> Can we represent musical moments well enough to choose the next section and cue
> like a useful DJ partner?

That is a different problem from ordinary vibe search. Track-level embeddings
answer "what tracks live near this vibe?" Section-aware DJing needs:

- this 32-bar outro feels compatible with that incoming groove;
- this breakdown can reset tension before a harder drop;
- this cue is mixable now, but only if the energy cliff is acceptable;
- this suggestion is grounded in facts, not the language model pretending it
  heard a full arrangement.

The representation layer must therefore be evaluated on DJ tasks, not generic
audio benchmarks. This spec defines how to benchmark CLAP, section-level CLAP,
music foundation models, temporal audio-language models, and structure models
without destabilizing the current product.

## Current product truth

Local code already makes a strong conservative choice:

- `src/vibemix/library/embed_factory.py` always returns `ClapEmbedder`.
- `src/vibemix/library/embed_clap.py` wraps local `ClapEngine` as the product
  embedding surface.
- `src/vibemix/library/clap_engine.py` uses local ONNX CLAP, 512 dimensions,
  lazy loading, 10-second audio chunks, mean pooling, and L2 normalization.
- `src/vibemix/library/_cosine.py` centralizes cosine top-k and assumes
  `EMBEDDING_DIM = 512` for product search parity.
- `src/vibemix/library/embed_config.py` already names strategies:
  `mean_excerpt` and `cue_anchored`.
- `src/vibemix/library/ingest.py::_embed_track_cue_anchored()` already shows the
  natural extension point: cue/section windows are embedded separately, then
  currently collapsed back to one track vector.

Conclusion:

**Do not replace product CLAP first. Stop collapsing the musical moments first.**

The next excellent move is a section index using the existing local CLAP model.
Only after the section-aware pipeline has evals should heavier representations
compete.

## External anchor map

Primary sources read/used for this spec:

- CLAP learns a joint audio/text space and supports flexible zero-shot retrieval
  and classification, which matches vibe-query and explanation needs.
  Source: https://arxiv.org/abs/2206.04769
- The current shipped checkpoint is a LAION CLAP model trained on music and
  speech; the Hugging Face card exposes 512-dimensional audio/text embeddings.
  Sources: https://huggingface.co/laion/larger_clap_music_and_speech,
  https://huggingface.co/Xenova/larger_clap_music_and_speech
- T-CLAP exists because ordinary CLAP has weak temporal understanding; it adds
  temporal contrastive supervision.
  Source: https://arxiv.org/abs/2404.17806
- TACOS makes the same point from the dataset side: CLAP-like models trained on
  global captions lack temporal supervision, so segment-linked text/audio pairs
  help frame-level alignment.
  Source: https://arxiv.org/abs/2505.07609
- CoLLAP extends language-audio pretraining to long-form music with explicit
  temporal structure augmentation.
  Source: https://arxiv.org/abs/2410.02271
- MERT and MuQ are music-specific self-supervised representations. MuQ-MuLan adds
  a music-text contrastive variant.
  Sources: https://arxiv.org/abs/2306.00107,
  https://arxiv.org/abs/2501.01108,
  https://github.com/tencent-ailab/MuQ
- CUE-DETR frames DJ cue point estimation as object detection and provides a
  cue dataset/model; this supports our cue fallback layer, not a general
  semantic retrieval layer.
  Source: https://arxiv.org/abs/2407.06823
- All-In-One jointly predicts beats, downbeats, segment boundaries, labels, and
  exposes frame embeddings; useful as fallback/eval/reference, but too heavy for
  first product cut.
  Sources: https://arxiv.org/abs/2307.16425,
  https://github.com/mir-aidj/all-in-one
- BeatNet is an online beat/downbeat tracker; useful for live playhead alignment,
  not semantic retrieval.
  Source: https://arxiv.org/abs/2108.03576
- Raveform provides EDM/DJ-mix structure annotations, beats, alignments, and
  expert segment labels, making it the strongest external eval target for our
  section/transition claims.
  Sources: https://reference-global.com/article/10.5334/tismir.288,
  https://mir-aidj.github.io/raveform/
- Real-world DJ mix alignment work validates mix-to-track subsequence alignment
  as a way to recover cue points, transition lengths, segmentation, and musical
  performance changes.
  Source: https://arxiv.org/abs/2008.10267

## Representation taxonomy

Do not collapse all model outputs into "embeddings." We need four different
families of musical evidence.

### 1. Semantic/timbral retrieval representations

Purpose:

- text vibe query -> audio section;
- section -> similar section;
- current section -> candidate entry section.

Product v1:

- existing local CLAP ONNX/512, but one vector per section/window instead of one
  vector per track.

Future bench:

- MuQ-MuLan for music-text retrieval;
- T-CLAP / CoLLAP / TACOS-style models for temporal text-audio alignment;
- MERT/MuQ hidden states pooled over sections for audio-audio similarity.

### 2. Structural boundary and role representations

Purpose:

- where phrases begin/end;
- whether a region behaves as intro, groove, build, breakdown, drop, or outro.

Product v1:

- DJ-authored cues first;
- Rekordbox ANLZ PSSI first auto source;
- CUE-DETR/DSP fallback;
- whole-track fallback when no structure is reliable.

Future bench:

- All-In-One segment labels and embeddings;
- Raveform-trained or Raveform-calibrated role mapper.

### 3. Technical mixability features

Purpose:

- BPM fit;
- key/Camelot fit;
- beatgrid/downbeat/phrase alignment;
- bar count and cue operability.

Product v1:

- existing library BPM/key;
- ANLZ beatgrid and phrase beats;
- deterministic Camelot/BPM/phrase scoring.

Future bench:

- BeatNet only for live playhead/downbeat confirmation;
- audio-DTW only as fallback when direct position is unavailable.

### 4. Taste and set-flow state

Purpose:

- avoid repeated colors;
- learn Kaan's preferred transitions and cue edits;
- adapt weights by genre/set intent.

Product v1:

- INTEL-05 feedback ledger and deterministic taste projection;
- no model fine-tuning until enough accepted/rejected decisions exist.

## Candidate matrix

| Candidate | Best use | V1 role | Why not immediately replace CLAP |
|-----------|----------|---------|----------------------------------|
| Current CLAP ONNX/512 | Text/audio and audio/audio retrieval | **Ship** for section vectors | Already packaged, local, cache-namespaced, deterministic enough |
| Section CLAP windows | Moment-level similarity | **Ship first** | Uses existing model; changes the data unit, not the dependency surface |
| Cue-anchored CLAP | Track summary improved by mix points | Keep as compatibility/pooled track strategy | Still collapses moments; less useful than section rows |
| T-CLAP | Temporal text/audio retrieval | Bench-only | Needs model availability, packaging, parity, and DJ-task proof |
| TACOS-style frame alignment | Text linked to temporal regions | Research/eval inspiration | Dataset/method more than a drop-in product model |
| CoLLAP | Long-form music/text context | Bench-only | Promising for whole-song context, but heavier and not product-integrated |
| MERT | Music SSL hidden states | Bench-only for audio/audio similarity/tagging | No text space; needs pooling, dimensionality, and packaging decisions |
| MuQ | Music SSL; MuQ-MuLan for text/music | Bench-only | Promising, but new dependency/cache namespace and unknown DJ-task lift |
| CUE-DETR | Cue point estimation | Fallback/auxiliary structure source | Cue model, not general transition retrieval |
| All-In-One | Beats/downbeats/segments/labels | Fallback/eval/reference | PyTorch/NATTEN/Demucs footprint; timing offset cautions for MP3 |
| BeatNet | Online beat/downbeat tracking | Later live alignment spike | Solves playhead rhythm, not next-track semantics |

## Benchmark principle

Every representation candidate must answer the same product questions:

1. Does it retrieve better **sections**, not just better tracks?
2. Does it rank better **transitions**, not just high cosine neighbors?
3. Does it improve **cue usefulness**, not just boundary detection metrics?
4. Does it preserve local/offline install reliability?
5. Does it keep the agent grounded enough that every claim can be validated?

No product swap without a measurable win on these questions.

## Benchmark datasets

### A. Kaan library silver set

Source:

- local Rekordbox ANLZ PSSI;
- existing library metadata;
- current CLAP store;
- future section index.

Labels:

- `source="anlz"` sections as silver boundaries;
- role mapping from INTEL-07;
- top transition suggestions judged by Kaan;
- accepted/rejected smart cues from INTEL-05.

Why it matters:

- This is the real product corpus and the real taste surface.

### B. Kaan ear-check gold slice

Minimum:

- 20 hardtechno tracks;
- 10 broader-vibe tracks;
- 30 proposed transition pairs;
- 50 proposed smart cues.

Labels:

- section boundary acceptable: yes/no/small-nudge/bad;
- role acceptable: yes/no;
- transition playable: accept/maybe/reject;
- cue slot useful: accept/edit/delete.

Why it matters:

- This is the quickest way to detect "paper-good, DJ-bad."

### C. Raveform external eval

Use for:

- section role mapping;
- beat/downbeat/segment timing;
- EDM-specific structure vocabulary;
- transition timing priors.

Not for:

- direct taste learning;
- exact Kaan-library ranking;
- claiming universal hardtechno truth.

### D. Synthetic transition fixtures

Use for:

- deterministic scorer tests;
- risk penalties;
- scoring-weight regressions;
- grounding validator behavior.

These are not musical quality tests. They are software contract tests.

## Benchmark tasks

### T1. Section text retrieval

Question:

> Given a DJ phrase query, does the model retrieve the right section type?

Example queries:

- "dark rolling intro, low kick pressure"
- "first breakdown before main drop"
- "tooly outro with room to blend"
- "peak-time drop, aggressive synth"
- "low-density bridge for energy reset"

Metrics:

- Recall@5 / Recall@10 by role;
- nDCG@10 where accepted Kaan labels outrank maybe/reject labels;
- source-stratified coverage: dj/anlz/auto/fallback;
- false-positive rate for low-confidence or unknown sections.

Acceptance floor for product CLAP v1:

- Section-level CLAP must beat current track-level CLAP on Kaan gold-slice
  retrieval by a visible margin before replacing any suggestion surface.

### T2. Section-to-section continuation

Question:

> Given the current outgoing section, does the representation find incoming
> sections that feel like a plausible musical continuation?

Inputs:

- `from_section`;
- candidate `to_sections`;
- optional intent: smooth, lift, reset, harder, deeper.

Metrics:

- top-5 contains an accepted transition;
- pairwise preference accuracy against Kaan labels;
- energy/role error buckets;
- diversity after artist/near-duplicate suppression.

Important:

- This is the core engine for "next track and which cue."

### T3. Transition scorecard lift

Question:

> Does a new representation improve the deterministic INTEL-11 slate?

Method:

- keep all non-semantic score components fixed;
- swap only `semantic_similarity`;
- evaluate transition slate ranking.

Metrics:

- MRR of first accepted candidate;
- accept@3;
- reject@3 lower-is-better;
- calibration: score bins should map to accept rates;
- warning correctness: top rejected candidates should have plausible warnings.

Decision rule:

- A new representation can only replace product CLAP if it improves accept@3 or
  MRR materially while preserving latency/install constraints.

### T4. Smart hot cue usefulness

Question:

> Do section boundaries and role mappings create cue slots a DJ actually wants?

Inputs:

- TrackIntelligence;
- role ontology;
- cue policy.

Metrics:

- cue accept/edit/delete;
- edit distance in seconds and beats;
- slot correctness for A/B/C/D/E/F;
- confidence calibration: low-confidence proposals should be edited more often.

Note:

- CUE-DETR and All-In-One compete here as structure sources, not as semantic
  retrieval models.

### T5. Live-context robustness

Question:

> Can the representation support live suggestions without overclaiming timing?

Metrics:

- no exact timing claims below INTEL-06 confidence floor;
- suppression during blend windows;
- playhead/section agreement when offline ground truth is available;
- latency on local machine.

BeatNet/audio-DTW belongs here, not in semantic retrieval.

### T6. Agent grounding

Question:

> Does the model output remain valid when routed through the grounded tool
> surface?

Metrics:

- 0 invented track IDs;
- 0 invented section IDs;
- 0 model-authored cue payloads exported directly;
- 0 timing claims without playhead confidence;
- validator reject reasons are useful and logged.

This catches a dangerous failure mode: a better embedding can still produce a
worse product if the agent is allowed to narrate beyond evidence.

## Storage and versioning rules

Product search remains 512-dimensional CLAP until a migration is explicitly
approved.

For benchmarks, do not mutate the product vector store. Create a parallel bench
store:

```text
representation_run
  run_id
  model_id
  model_family
  dim
  pooling
  window_policy
  source_revision
  created_at

section_vector_bench
  run_id
  section_id
  vector_blob
  vector_norm
  content_hash
  strategy_version
```

Rules:

- Every representation has a `strategy_version`.
- Every product or benchmark vector build has a `representation_run_id` and
  model card record as defined by INTEL-17.
- Every cache/store namespace includes model family, model ID, dim, pooling, and
  window policy.
- Never compare scores across representation families without normalization and
  an eval task.
- Never mix benchmark vectors into product `library-clap` stores.
- Do not change `EMBEDDING_DIM = 512` for product search in a benchmark PR.
- If a future product model has a different dimension, implement a separate
  section index/backend and migration plan instead of weakening current parity
  assertions.

## Section window policy

The same section can be represented in multiple ways. Benchmark them explicitly.

### `section_full`

Embed `[start_s, end_s]` capped at 80 seconds.

Best for:

- intro/groove/outro similarity;
- mixable region retrieval.

Risk:

- long drops or breakdowns may lose internal evolution when capped.

### `section_head`

Embed first 16 or 32 bars of the section.

Best for:

- "what does it sound like when I enter?"

Risk:

- misses late payoff.

### `section_tail`

Embed last 16 or 32 bars.

Best for:

- outgoing sections and mix-out planning.

Risk:

- less useful for incoming cue choice.

### `section_multi`

Store head/mid/tail vectors as separate rows under one section.

Best for:

- high-quality transition search.

Risk:

- more storage and more ranking complexity.

Recommendation:

- Product v1 uses `section_head` for incoming candidates and `section_tail` for
  outgoing context when the section is long enough; short sections fall back to
  `section_full`.
- Store `window_role = head | tail | full` in metadata.
- Transition scorer consumes the correct window by direction instead of asking
  one pooled vector to do two jobs.

## Pooling rules

Do not mean-pool away the decision surface by default.

Allowed:

- pooled track vector for legacy track-level search;
- pooled section vector only when a section is short or a model requires fixed
  clip aggregation;
- direction-aware windows for transition search.

Avoid:

- one vector per track as the only representation;
- one mean of all cues as the only cue-aware representation;
- using a drop vector to represent an intro because both came from one track.

This is the exact mistake that makes a "smart" set builder feel strangely
generic.

## Scoring isolation

When benchmarking a representation, hold the rest of the transition scorer fixed.

Fixed components:

- harmonic compatibility;
- BPM fit;
- energy shape;
- role compatibility;
- phrase alignment;
- cue operability;
- taste;
- novelty;
- risk penalties.

Swappable component:

- `semantic_similarity`.

Why:

- Otherwise a better score might come from different weight tuning rather than a
  better representation.

Canonical INTEL-11 weights stay:

```text
0.24 semantic
0.16 harmonic
0.12 bpm
0.12 energy_shape
0.13 role
0.09 phrase_alignment
0.07 cue_operability
0.05 taste
0.02 novelty
- risk_penalty
```

## Human eval packet

For each candidate transition shown to Kaan, preserve:

```text
from_section_id
to_section_id
candidate_id
representation_run_id
score_components
warnings
agent_explanation
accepted: yes | maybe | no
cue_edit: none | moved | deleted | added
notes
```

Rules:

- The UI can be casual; the logged payload must be structured.
- Free-text notes are allowed but never the only label.
- Every Kaan judgement becomes future eval data and taste data.
- INTEL-15 is canonical for the exact JSONL schemas, splits, rubrics, active
  sampling policy, and redaction rules.

## Model governance gates

A new representation can move from bench to product only if all gates pass:

### Quality gate

- improves transition accept@3 or MRR over section CLAP;
- does not regress section text retrieval;
- does not increase high-confidence bad cue proposals;
- has at least one Kaan gold-slice win, not only an external-dataset win.

### Grounding gate

- all outputs still resolve through INTEL-12 holders;
- no raw vectors in prompts;
- no hidden model facts exposed as truth;
- validator rejects invalid IDs/actions.

### Runtime gate

- local/offline path exists;
- lazy imports preserve cheap app startup;
- install size and first-run setup are acceptable;
- macOS arm64 works on the target machine;
- no live path blocks on heavy model load.

### Data gate

- separate cache namespace;
- separate strategy version;
- replayable benchmark run metadata;
- deterministic top-k ordering within each representation backend.

### Rollback gate

- product CLAP store remains intact;
- feature flag or strategy selector can return to CLAP;
- old section records remain readable or are migrated explicitly.

## Recommended product path

### Ship next

1. Build section extraction and section store from INTEL-10.
2. Use current local CLAP ONNX/512 for section windows.
3. Add direction-aware `section_head` and `section_tail` vectors.
4. Feed those vectors into INTEL-11 transition scorer.
5. Log every transition/cue judgement into INTEL-05.

This is high leverage because it improves the data unit while preserving the
known model/install/runtime surface.

### Benchmark after the section pipeline exists

1. MuQ-MuLan vs CLAP for text-to-section retrieval.
2. MERT/MuQ hidden states vs CLAP for audio-to-audio section continuation.
3. T-CLAP/CoLLAP-style models for temporal query phrasing if packaging exists.
4. All-In-One as a fallback role/boundary source for tracks with no ANLZ.
5. BeatNet only in the live playhead confidence lane.

### Do not do yet

- Do not rewrite product search to variable-dim embeddings.
- Do not add PyTorch/NATTEN/Demucs to the main runtime just to try All-In-One.
- Do not ask Gemini/Codex to listen to long raw audio and decide transitions.
- Do not expose benchmark candidates to action tools before they pass grounding.

## The answer to "how do we make Gemini music-aware?"

Not by giving it more waveform and hoping.

Make a musical context object that says:

- current section role, timing, confidence, and provenance;
- top transition candidates with score components;
- cue options with slots and source;
- warnings and uncertainty;
- allowed actions.

Then let the model choose/explain within that object.

The intelligence comes from:

```text
grounded section data
  + section-level representations
  + deterministic transition scoring
  + taste feedback
  + bounded agent decisions
```

The language model becomes excellent because the context is excellent.

## First implementation hooks

This spec does not require immediate product code changes, but the future PR
sequence should expose these hooks:

- `SectionEmbeddingStrategy` enum:
  - `clap_section_head_tail_v1`
  - `clap_section_full_v1`
  - `clap_cue_pooled_track_v1` (compatibility)
- `RepresentationRun` bench metadata.
- `section_vector_bench` separate from product store.
- eval command:

```text
uv run python -m vibemix eval representations \
  --library local \
  --gold .planning/eval/kaan-section-gold.jsonl \
  --candidate clap_section_head_tail_v1 \
  --candidate clap_section_full_v1 \
  --report .planning/eval/reports/representation-YYYYMMDD.md
```

Initial test targets:

- section window selection is deterministic;
- product `EMBEDDING_DIM` remains 512;
- bench stores can hold non-512 dims without touching product search;
- transition scorer receives one semantic score regardless of representation;
- benchmark output is replayable from run metadata.

## Decision

For the next intelligence build:

**Use local CLAP for section-level vectors. Benchmark alternatives later.**

The excellence move is not a model swap. It is a data-shape upgrade:

```text
one track vector
  -> many section/window vectors
  -> transition-aware scoring
  -> grounded agent context
  -> taste feedback
```

That path gives the app a DJ-native brain while keeping the product shippable.
