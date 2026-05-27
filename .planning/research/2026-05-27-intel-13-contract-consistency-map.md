# INTEL-13: contract consistency map

**Date:** 2026-05-27
**Lane:** intelligence architecture / implementation guardrails
**Covers:** INTEL-01 through INTEL-23
**Status:** canonical contract map; resolves cross-spec drift

## Why this exists

The intelligence specs now cover ANLZ ingest, section storage, transition
scoring, context compilation, taste, live awareness, tool grounding, model
benchmarks, private gold labels, implementation readiness checks,
provenance/replay manifests, smart-cue policy, cue baseline comparison,
decision runtime traces, musical claim validation, synthetic fixture IDs, and
research-backed bet labels.
That is enough surface area for small naming drifts to become real
implementation bugs.

This file is the one-page contract map. If a future implementation PR conflicts
with this map, either the PR is wrong or this file needs an explicit update in
the same change.

## Canonical ID shapes

### Track IDs

```text
track_id = whatever the current Rekordbox/folder library uses
```

Rules:

- must resolve through `RekordboxLibrary.lookup_by_id()` before any action;
- introduced by `search_vibe` / `discover_pool` / `search_sections`;
- held in existing `LibraryToolset.seen`.

### Section IDs

```text
section_id = "<track_id>#s<zero_padded_ordinal>"
```

Example:

```text
t001#s000
rb-123#s014
```

Rules:

- public/runtime ID only;
- stable for the active canonical section map of one track;
- ordinal is sorted by start time/beat;
- no file path, source name, role, or beat number in the public ID;
- provenance lives in metadata.

Metadata must carry:

```text
source: dj | anlz | auto | fallback
source_detail: hotcue | pssi | cue_detr | dsp | all_in_one | whole_track | null
```

If future debug/audit mode exposes competing analyses for the same track, add a
separate `analysis_id`; do not fork the public `section_id` shape.

### Transition candidates

Internal stable key:

```text
transition_key = sha256(strategy_version | mode | from_section_id | to_section_id | cue_slot)[:16]
```

Public run-scoped alias:

```text
candidate_id = "tr_001"
```

Rules:

- the scorer creates deterministic candidates;
- the tool/context layer assigns aliases in ranked order;
- the model only sees aliases;
- validators map aliases back to issued candidate objects;
- no action tool accepts a model-created candidate ID.

### Smart-cue proposals

```text
proposal_id = "cueprop_001"
cue_id = "cueprop_001:A"
```

Rules:

- proposal IDs are run-scoped;
- cue IDs are derived from proposal ID plus slot;
- export tools accept proposal/cue IDs, not raw model-authored cue payloads.
- slot semantics and review/export policy come from INTEL-18;
- A-H slot numbers must be preserved during smart-cue export.

### Context packets

```text
packet_id = "ctx_001"
schema_version = "intel_context_v1"
```

Rules:

- packet IDs are run-scoped;
- validator checks model decisions against the packet;
- packet contents are bounded and redacted.

### Musical claims

```text
claim_id = "clm_ctx_001_000"
```

Rules:

- claim IDs are packet-scoped, not reusable action IDs;
- claim IDs are created by deterministic context/claim code, never by the model;
- every model-written musical explanation should map to allowed claim IDs;
- claim taxonomy and evidence requirements come from INTEL-21.

### Eval / gold-label IDs

```text
review_session_id = "rs_YYYYMMDD_NNN"
review_item_id = "rev_001"
label_id = "lbl_001"
```

Rules:

- eval IDs are private/replay IDs, not tool/action IDs;
- labels may reference canonical track/section/candidate/proposal IDs;
- no action tool accepts `review_session_id`, `review_item_id`, or `label_id`;
- public reports hash/redact private track IDs and never expose local paths.

### Synthetic fixture IDs

```text
track_id = "fx-hard-001"
section_id = "fx-hard-001#s000"
vector_ref = "vec8:fx-hard-001#s000"
```

Rules:

- synthetic fixture IDs use the `fx-` prefix;
- fixture locations use `fixture://`;
- fixture titles/artists start with `Fixture`;
- fixture ID semantics come from INTEL-22.

### Provenance / replay run IDs

```text
analysis_run_id = "anrun_YYYYMMDD_HHMMSS_<short_hash>"
representation_run_id = "repr_YYYYMMDD_HHMMSS_<strategy>_<short_hash>"
transition_run_id = "transrun_YYYYMMDD_HHMMSS_<strategy>_<short_hash>"
context_run_id = "ctxrun_YYYYMMDD_HHMMSS_<short_hash>"
eval_run_id = "eval_YYYYMMDD_HHMMSS_<suite>_<short_hash>"
```

Rules:

- run IDs are provenance IDs, not action IDs;
- private manifests may reference canonical object IDs;
- public reports redact private track identifiers;
- release claims require enough lineage to replay or explicitly mark the claim
  as non-replayable.

## Canonical source enums

### Cue source

`CueAnchor.source`:

```python
Literal["dj", "anlz", "auto"]
```

Meaning:

- `dj`: human-authored cue/loop in a DJ library;
- `anlz`: Rekordbox ANLZ PSSI-derived structure;
- `auto`: ML/DSP fallback produced by vibemix.

No `fallback` here because `CueAnchor` means "we have a structural cue." A
whole-track fallback is not a cue.

### Section source

`SectionRecord.source`:

```python
Literal["dj", "anlz", "auto", "fallback"]
```

Meaning:

- `dj`: section map came from human cue/loop structure;
- `anlz`: section map came from Rekordbox ANLZ;
- `auto`: section map came from ML/DSP fallback;
- `fallback`: one coarse whole-track section because no structure was reliable.

Use `source_detail` for engine details:

```text
hotcue, memory_cue, pssi, cue_detr, dsp, all_in_one, whole_track
```

## Run-scoped grounding holders

Extend `LibraryToolset` with these holders when implementation begins:

```python
seen: set[str]  # existing track IDs
seen_sections: dict[str, SectionRecord]
issued_transition_candidates: dict[str, TransitionCandidate]
issued_cue_proposals: dict[str, SmartCueProposal]
issued_context_packets: dict[str, AgentContextEnvelope]
```

Do not use older shorter holder aliases in new code. Existing docs that mention
pre-INTEL-13 holder names should be treated as historical text unless patched.

## Tool grounding ladder

```text
search_vibe / discover_pool
  -> seen track_ids

get_track_sections / search_sections
  -> seen_sections

transition_slate
  -> issued_transition_candidates

smart_hot_cues
  -> issued_cue_proposals

compile_musical_context
  -> issued_context_packets

export_set / create_playlist / export_smart_cues
  -> write only after holder + library revalidation
```

The model never gets to manufacture the final write payload.

## Research bet labels

INTEL-23 uses bet labels for strategy and PR evidence:

```text
Bet A: ANLZ structure floor
Bet B: section-level embeddings with current CLAP
Bet C: deterministic transition slate scorer
Bet D: set-aware smart cueing
Bet E: live pill with audio-derived playhead
Bet F: model-assisted explanations
```

Rules:

- bet labels are documentation/evidence labels, not runtime IDs;
- do not put bet labels in tool payloads or persisted user data;
- PR evidence may name an INTEL-23 bet to justify why a change belongs in the
  intelligence lane;
- runtime grounding still uses concrete IDs: tracks, sections, candidates, cue
  proposals, packets, claims, and traces.

## Citation policy

Do not add new `EvidenceRegistry` citation sources in the first implementation
cut.

Use:

- existing `track` citations for track identity;
- existing `key`, `mix`, `aud`, `midi`, and `ev` citations for live facts;
- structured candidate/section/proposal IDs for internal validation.

Future citation sources may be useful:

```text
section
trans
cue
packet
```

But adding one requires a coordinated schema migration across:

- `state/evidence_registry.py`
- `prompts/matrix.py::CITATION_GRAMMAR_BLOCK`
- `coach/citation_linter.py`
- `agent/dj_cohost.py::_build_citation_strip`
- tests that mirror source lists.

## Canonical module targets

First implementation should prefer these module names:

```text
src/vibemix/library/anlz_ingest.py
src/vibemix/library/section_types.py
src/vibemix/library/section_store.py
src/vibemix/library/section_index_numpy.py
src/vibemix/library/section_index_sqlite_vec.py
src/vibemix/library/section_ingest.py
src/vibemix/intel/musical_ontology.py
src/vibemix/intel/transition_scorer.py
src/vibemix/intel/context_compiler.py
src/vibemix/intel/decision_validator.py
```

Keep pure-compute intelligence under `vibemix.intel`. Keep library persistence
and ingest under `vibemix.library`.

## Canonical scoring weights

Transition scorer v1:

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

If implementation changes these, update INTEL-11 and this file together.

## Canonical first PR order

1. `CueSource="anlz"` and ANLZ parser.
2. ANLZ audit script.
3. Section types and section extraction.
4. Section store/index.
5. Transition scorer pure functions.
6. Grounded intelligence tools.
7. Context compiler and decision validator.
8. Prep-only agent wiring.
9. Live-aware pill wiring.

This order keeps the current app stable while moving toward the full
section-aware intelligence system.

## Non-negotiable invariants

- Existing track-level search remains stable.
- No raw vectors in prompts or tool outputs.
- No raw local file paths in autonomous agent outputs.
- No model-computed keys, BPM, timing, cue slots, or section roles.
- No action tool accepts IDs not issued or seen in the current run.
- Missing metadata degrades confidence; it does not fabricate facts.
- Live exact timing is forbidden below the INTEL-06 timing floor.
- Smart cue export is proposal-based, not raw cue-payload based.
- Product code does not read or mutate Rekordbox `master.db`.
