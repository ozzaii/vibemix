# INTEL-04 handoff - execution plan for musical intelligence build

**Date:** 2026-05-27
**Scope:** concrete implementation bridge for INTEL-01/02/03
**Code posture:** implementation has begun. ANLZ ingest, caller/product ingest
orchestration, ANLZ audit, smart-cue policy/export, baseline comparison,
context packets, transition scoring, musical claim validation, and the first
agentic decision runtime are now present. Section retrieval, gold-label
validation/sampling, feedback/taste/profile primitives, taste privacy gates,
and the aggregate INTEL scorecard are also present with focused tests. Product
wiring, durable taste storage, and broader eval thresholding remain future cuts.

## Purpose

This is the build handoff for the intelligence lane.

The target is not "add more AI." The target is a verified local intelligence
stack:

```text
Rekordbox ANLZ sections
  -> section vectors and quality ledger
  -> section-to-section transition slates
  -> grounded agent/context packet
  -> INTEL-21 musical claims
  -> smart cue proposal policy (INTEL-18), export, and live pill behavior
```

Another session is cleaning the codebase, so product edits should remain narrow
and collision-aware.

## Current repo facts to preserve

Read these first before implementing:

- `src/vibemix/library/cue_types.py`
  - Current `CueAnchor` is minimal and frozen.
  - Current `CueSource = Literal["dj", "auto"]`; INTEL-01 needs `"anlz"`.
- `src/vibemix/library/excerpt.py`
  - Current priority: DJ cue -> auto-cue engine -> empty/whole-track fallback.
  - INTEL-01 changes this to: DJ cue -> ANLZ -> auto-cue -> whole-track fallback.
- `src/vibemix/library/ingest.py`
  - Current cue-anchored CLAP path embeds windows then mean-pools to one track
    vector.
  - INTEL-02 needs per-section vectors without breaking the existing track
    vector contract.
- `src/vibemix/library/next_suggestion.py`
  - Current pill engine is track-level: seed vector -> one next track.
  - It already handles grounding, played IDs, key/BPM refine, and honest silence.
- `src/vibemix/runtime/suggestion.py`
  - Current `SuggestionService` owns derived pill state outside `MusicState`.
  - Keep that pattern. Do not make `MusicState` the writer of suggestions.
- `src/vibemix/library/toolset.py`
  - Current `seen` set is the grounding gate for track IDs.
  - INTEL-02 should add analogous holders for sections and transition candidates.
- `src/vibemix/state/evidence_registry.py`
  - Citation sources are mirrored in regexes, prompts, and linter logic.
  - Do not casually add `section` / `trans` sources without a locked multi-file
    schema update.
- `scripts/eval/*`
  - Existing eval spine already has replay, scorecard, cited relevance, and
    threshold lock. INTEL evals should extend it.

## Branch hygiene / collision note

The current worktree is very dirty and includes other-session edits across
`src/vibemix/library`, tests, docs, scripts, and Tauri. Implementation should
start only after the codebase-cleanup session lands or hands off its branch.

When implementing, first run:

```bash
git status --short
git diff -- src/vibemix/library/cue_types.py src/vibemix/library/excerpt.py src/vibemix/library/ingest.py src/vibemix/library/toolset.py src/vibemix/runtime/suggestion.py
```

Do not overwrite unrelated changes.

## Phase 0 - lock docs and fixtures

Artifacts to add/keep:

```text
.planning/research/2026-05-27-intelligence-excellence-direction.md
.planning/research/2026-05-27-intel-01-anlz-structure-spec.md through
.planning/research/2026-05-27-intel-23-research-backed-musical-intelligence-map.md
```

Public synthetic fixtures:

```text
tests/intel/fixtures/...
```

INTEL-22 is the canonical fixture contract. Phase 0 should add or verify that
corpus before broad intelligence implementation starts.

INTEL-23 is the source-backed decision filter. If a PR adds or swaps a model,
live analyzer, cue feature, or model-written explanation, its evidence should
state which INTEL-23 bet it advances and which kill/graduate criteria apply.

No private Rekordbox paths or local audio in git.

## Phase 1 - INTEL-01 ANLZ ingest

Current partial implementation:

```text
done: src/vibemix/library/anlz_ingest.py
done: tests/library/test_anlz_ingest.py
done: CueSource="anlz" typing update
done: excerpt.py priority integration
done: tests/library/test_excerpt.py ANLZ branch
done: ingest.py receives caller-built ANLZ index
done: tests/library/test_ingest.py ANLZ window + cache separation coverage
done: scripts/eval/intel_anlz_audit.py
done: tests/eval/test_intel_anlz_audit.py
done: product CLI/orchestration builds/passes an ANLZ index when available
done: tests/library/test_ingest_cli_anlz.py covers CLI pass-through + fallback
```

The integration remains caller-injected: no hidden global ANLZ scan inside
`excerpt.py`. Product ingest orchestration now constructs/passes the index once
per run and falls back honestly when ANLZ is unavailable.

### Files

Add:

```text
src/vibemix/library/anlz_ingest.py
tests/library/test_anlz_ingest.py
```

Modify:

```text
src/vibemix/library/cue_types.py
src/vibemix/library/excerpt.py
tests/library/test_excerpt.py
```

### Implementation shape

`anlz_ingest.py` should be import-light:

```text
top-level: pathlib, dataclasses, unicodedata, collections
lazy import: pyrekordbox.anlz.AnlzFile inside parser only
no db6 / SQLCipher / master.db / audio / CLAP / torch
```

Public types:

```text
AnlzBeatGrid
AnlzPhrase
AnlzTrackMeta
AnlzIndex
```

Public functions:

```text
iter_anlz_ext_files(root=None)
parse_anlz_bundle(ext_path)
build_anlz_index(root=None)
match_track_to_anlz(track, index)
anchors_from_anlz(track, meta, max_cues=4)
```

Critical parser rules:

- use `.EXT` `PSSI` for phrase entries;
- use sibling `.DAT` `PQTZ` for per-beat timing;
- use `.EXT` `PPTH` for source path;
- do not use `.EXT` `PQT2` as the primary beat-to-time source;
- return `None` honestly on missing structure;
- never raise for ordinary missing analysis.

### Excerpt integration

Prefer an injected index over hidden global scanning:

```python
def anchors_for_track(track, *, anlz_index=None, max_cues=4, window_s=80.0):
    ...
```

Priority:

```text
DJ structural cues
  -> ANLZ anchors if index supplied and match is unique
  -> detect_cues_auto
  -> []
```

`CueSource` must become:

```python
CueSource = Literal["dj", "anlz", "auto"]
```

### Tests

Minimum tests:

- PSSI high mood maps Intro/Up/Down/Chorus/Outro to cue labels.
- Mid/low mood labels keep lower confidence.
- beat numbers convert through PQTZ one-indexed times.
- end beyond PQTZ extrapolates only with a valid last BPM.
- basename collisions return no match.
- `anchors_for_track` keeps DJ cues before ANLZ.
- `anchors_for_track` tries ANLZ before auto fallback.
- `anlz_ingest` top-level import does not import `pyrekordbox.db6`, CLAP, torch,
  or audio decode.

### Verification

```bash
uv run pytest -q tests/library/test_anlz_ingest.py tests/library/test_excerpt.py
uv run ruff check src/vibemix/library/anlz_ingest.py tests/library/test_anlz_ingest.py
uv run ruff format src/vibemix/library/anlz_ingest.py tests/library/test_anlz_ingest.py --check
```

## Phase 2 - wire ANLZ into ingest without changing track-vector contract

Current partial implementation:

```text
done: ingest_source(..., anlz_index=...) caller-injected seam
done: _embed_track_cue_anchored(..., anlz_index=...) passes ANLZ into excerpt priority
done: ANLZ-matched tracks use an ANLZ-fingerprinted cache key
done: focused ingest tests prove no-ANLZ cache rows do not mask later ANLZ windows
done: intel_anlz_audit.py emits redacted coverage/collision/role/confidence evidence
done: CLI/orchestration constructs the ANLZ index once per ingest run when available
done: CLI warning path keeps ingest alive when ANLZ index construction fails
```

### Files

Modify:

```text
src/vibemix/library/ingest.py
tests/library/test_ingest.py
```

Optional:

```text
scripts/eval/intel_anlz_audit.py
tests/eval/test_intel_anlz_audit.py
```

### Implementation shape

Build the ANLZ index once per ingest run when available:

```text
source detects Rekordbox/folder tracks
  -> build_anlz_index(default root) best-effort
  -> anchors_for_track(track, anlz_index=index)
  -> cut windows
  -> existing mean-pooled track vector storage
```

Do not change the existing `LibraryStore` track-vector schema in this phase.
The output should remain compatible with current search and pill behavior.

### Acceptance evidence

- Existing ingest tests pass.
- Tracks with ANLZ use ANLZ windows when no DJ cues exist.
- Tracks with DJ cues still use DJ windows.
- Tracks without structure still whole-track fallback.
- Cache strategy version changes only if cue window selection changes enough to
  invalidate stored vectors.

## Phase 3 - section intelligence store

### Files

Add:

```text
src/vibemix/library/section_types.py
src/vibemix/library/section_store.py
src/vibemix/library/section_index_numpy.py
src/vibemix/library/section_index_sqlite_vec.py
src/vibemix/library/section_ingest.py
tests/library/test_section_types.py
tests/library/test_section_store.py
tests/library/test_section_index_numpy.py
tests/library/test_section_index_sqlite_vec.py
tests/library/test_section_ingest.py
```

### Design choice

Use a separate section store instead of overloading the track-vector store.

Reason:

- track vector index has one vector per track;
- section vector index has many vectors per track;
- section embeddings may later use a different model/version;
- separate schema avoids mixing dimensions or invalidating current library search.

Suggested cache:

```text
~/.cache/vibemix/section-intelligence.db
```

Tables:

```text
sections(section_id primary key, track_id, role, source, confidence,
         start_s, end_s, start_beat, end_beat, bar_count,
         bpm, camelot, energy_mean, density, brightness, sub_weight,
         vector_ref, analysis_version, generated_at)

section_vectors(section_id primary key, dim, vector_blob, model_id,
                content_hash, generated_at)
```

Keep model IDs explicit. Do not hardcode model names in live logic; use existing
embedding backend seams/config where possible.

### Tests

- stable canonical `section_id` generation (`<track_id>#sNNN`);
- section rows round-trip;
- vector dimension mismatch fails loudly;
- query filters by role/source/confidence;
- duplicate sections do not corrupt track search.

## Phase 4 - transition slate engine

### Files

Add:

```text
src/vibemix/intel/transition_scorer.py
tests/intel/test_transition_scorer.py
```

Optional later:

```text
src/vibemix/library/context_packet.py
tests/library/test_context_packet.py
```

### Public API

```text
TransitionCandidate
TransitionWeights
TransitionConstraints
score_transition(from_section, to_section, weights, constraints)
rank_transition_slate(from_section, candidate_sections, constraints, k)
```

Scoring v1:

```text
0.24 semantic_section_similarity
0.16 harmonic_fit
0.12 bpm_fit
0.12 energy_shape_fit
0.13 role_fit
0.09 phrase_alignment_fit
0.07 cue_operability
0.05 taste_fit
0.02 novelty
- risk_penalty
```

Hard rules:

- no NaN scores;
- both-known harmonic/BPM degrade, matching current `next_suggestion` posture;
- missing facts reduce confidence but do not fabricate;
- risk flags are data, not prose.

### Tests

- harmonic clash lowers/drops candidate only when both keys known;
- unknown key is honest degrade, not hard reject;
- BPM large delta adds risk;
- role intro/outro and drop/drop shape scores as expected;
- candidates sorted descending;
- no candidate can reference unknown sections.

## Phase 5 - grounded tools

### Files

Modify:

```text
src/vibemix/library/toolset.py
src/vibemix/library/mcp_server.py
src/vibemix/library/codex_curate.py
tests/library/test_toolset.py
tests/library/test_codex_curate.py
tests/library/test_setprep_tools.py
```

### Tool additions

```text
get_track_sections(track_id)
search_sections(query, role=None, bpm_min=None, bpm_max=None, k=20)
transition_slate(from_track_id, from_section_id, candidate_section_ids, k=5, mode="prep")
explain_transition(candidate_id)
smart_hot_cues(track_id=None, track_ids=None, genre=None)
export_smart_cues(proposal_id, selected_cue_ids=None, out_path=None)
```

### Grounding holders

Extend `LibraryToolset` instance state:

```python
self.seen_sections: dict[str, SectionRecord] = {}
self.issued_transition_candidates: dict[str, TransitionCandidate] = {}
self.issued_cue_proposals: dict[str, SmartCueProposal] = {}
self.issued_context_packets: dict[str, AgentContextEnvelope] = {}
```

Gates:

- `get_track_sections`: track must resolve in library; adds returned sections to
  `seen_sections`.
- `search_sections`: adds returned track IDs to `seen` and sections to
  `seen_sections`.
- `transition_slate`: every candidate section must be in `seen_sections`, except
  the current live section resolved internally from `MusicState`.
- `explain_transition`: candidate ID must be in `issued_transition_candidates`.
- `smart_hot_cues`: track IDs must be in `seen`; proposals and cue IDs are issued
  by deterministic code and recorded in `issued_cue_proposals`.
- `export_smart_cues`: proposal ID must be issued, selected cue IDs must belong
  to that proposal, and the proposal track must still resolve and still be in
  `seen`. Preserve A-H slot numbers from INTEL-18; do not reuse the generic
  timeline-sorted cue export path for smart-cue proposals.

### Tests

- invented section ID rejected;
- invented candidate ID rejected;
- candidate issued in one run not valid in another run;
- smart cue proposal cannot be created for unseen tracks;
- smart cue export rejects unissued proposals, cue IDs outside the proposal, raw
  cue payloads, and missing library tracks;
- tool timeout behavior still returns error dict, never raises.

## Phase 6 - live/prep context packet and pill

### Files

Add:

```text
src/vibemix/library/context_packet.py
tests/library/test_context_packet.py
```

Modify:

```text
src/vibemix/runtime/suggestion.py
src/vibemix/library/next_suggestion.py
tauri/ui/src/pill/next-suggestion.ts
tauri/ui/src/pill/next-suggestion.test.ts
```

Implementation note: UI work may be owned by the codebase/UI session. The
backend should preserve the old `next_suggestion` dict until the UI can render
the richer payload.

### Backend behavior

Add a richer payload beside the old one:

```text
next_suggestion       # old track-level compatibility field
next_transition       # new section-level candidate/decision field
```

Live mode:

```text
MusicState snapshot
  -> resolve active track through current deck state
  -> estimate current section if playhead available
  -> build MusicalContextPacket
  -> rank transition slate
  -> INTEL-20 decision runtime produces PillDecision or hold/suppress
```

If playhead confidence is weak, never emit exact bar timing.

### Tests

- no active track -> current suggestion unchanged or honest `None`;
- weak playhead -> no "in N bars" timing claim;
- blend window -> suppress exact timing;
- old `next_suggestion` payload remains parseable;
- new payload validates against schema.

## Phase 7 - eval gates

### Files

Current implemented eval artifacts:

```text
scripts/eval/intel_anlz_audit.py
scripts/eval/intel_cue_baseline_compare.py
scripts/eval/intel_decision_runtime_replay.py
scripts/eval/intel_fixture_audit.py
scripts/eval/intel_section_retrieval.py
scripts/eval/intel_transition_scorecard.py
scripts/eval/intel_gold.py
scripts/eval/intel_taste_scorecard.py
scripts/eval/intel_scorecard.py
scripts/eval/intel_provenance_report.py
scripts/eval/intel_gate.py
tests/eval/test_intel_anlz_audit.py
tests/eval/test_intel_cue_baseline_compare.py
tests/eval/test_intel_decision_runtime_replay.py
tests/eval/test_intel_fixture_audit.py
tests/eval/test_intel_section_retrieval.py
tests/eval/test_intel_transition_scorecard.py
tests/eval/test_intel_gold_validation.py
tests/eval/test_intel_taste_scorecard.py
tests/eval/test_intel_scorecard.py
tests/eval/test_intel_provenance_report.py
tests/eval/test_intel_gate.py
tests/intel/fixtures/section_queries.jsonl
tests/intel/fixtures/taste_feedback.jsonl
```

Implemented fixture threshold-lock integration:

```text
eval/INTEL-THRESHOLD-LOCK.md
scripts/eval/intel_gate.py --threshold-lock eval/INTEL-THRESHOLD-LOCK.md
scripts/eval/intel_scorecard.py --threshold-lock eval/INTEL-THRESHOLD-LOCK.md
```

Minimum gates:

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

Optional external benchmark:

- Raveform adapter under optional eval path only;
- not default CI;
- no runtime dependency.

## Exact implementation order

Recommended sequence:

```text
1. Commit/land docs.
2. Add `anlz_ingest.py` with pure parser unit tests.
3. Add `CueSource="anlz"` and excerpt priority integration.
4. Wire ANLZ index into ingest while preserving track-vector behavior.
5. Add ANLZ audit eval script and local stats output.
6. Add section store and section search.
7. Add transition slate engine.
8. Add grounded section/transition tools.
9. Add context packet and decision validator.
10. Add INTEL-21 musical claim ledger and claim validator.
11. Add INTEL-20 decision runtime and backend `next_transition` payload.
12. Add smart cue proposal policy using INTEL-18 slot semantics.
13. Add smart cue export over issued proposals using slot-preserving export.
14. Add gold-label schema validation and private review sampling.
15. Add INTEL-22 fixture corpus and privacy audit if not already present.
16. Add structured feedback, deterministic taste aggregation, profile
    projection, and taste/privacy scorecard gates.
17. Check INTEL-23 before adding model swaps, live analyzers, or cue features
    outside the no-regret build order.
18. Done for public fixtures: add eval gates to scorecard/INTEL threshold lock.
    Remaining release cut: recalibrate against private labels and promote the
    threshold policy deliberately.
```

This order creates value after step 4 and keeps every later step testable.

## Acceptance matrix

| Capability | Proof |
|------------|-------|
| ANLZ parser | `tests/library/test_anlz_ingest.py` plus local audit JSON |
| Excerpt priority | `tests/library/test_excerpt.py` shows DJ -> ANLZ -> auto |
| Ingest compatibility | existing ingest/search/pill tests still pass |
| Section store | round-trip and query tests |
| Transition slate | pairwise scoring tests and no-NaN property tests |
| Tool grounding | invented track/section/candidate rejection tests |
| Pill grounding | schema tests plus timing-floor tests |
| Musical claims | `tests/intel/test_claims.py` + `tests/intel/test_claim_validator.py` prove typed claim gates |
| Decision runtime | `tests/intel/test_decision_runtime.py` + replay eval prove degrade/trace behavior |
| Smart cue policy | `tests/library/test_smart_cues.py` proves A-H policy + slot export marks |
| Smart cue baseline compare | `tests/eval/test_intel_cue_baseline_compare.py` proves XML diff + comparative lift |
| Gold labels | `tests/intel/test_gold_labels.py` + `tests/eval/test_intel_gold_validation.py` prove schema/redaction gates |
| Taste learning | `tests/intel/test_feedback.py`, `tests/intel/test_taste_model.py`, `tests/intel/test_profile_projection.py`, and `tests/eval/test_intel_taste_scorecard.py` prove conservative learning/privacy gates |
| Transition scorecard | `tests/eval/test_intel_transition_scorecard.py` proves playable-vs-bad ranking metrics |
| Eval gates | `tests/eval/test_intel_scorecard.py` proves INTEL artifact aggregation + threshold gates |
| Privacy | no committed local audio or private Rekordbox paths |

## Do not do

- Do not read Rekordbox process memory.
- Do not write `master.db`.
- Do not add screen vision back.
- Do not put raw vectors into prompts.
- Do not ask the LLM to generate keys, BPM, cue positions, or section facts.
- Do not overload the existing track-vector store with many section vectors
  unless there is a migration plan.
- Do not loosen eval thresholds to make a demo pass.

## First coding slice

The first coding slice should be small and decisive:

```text
src/vibemix/library/anlz_ingest.py
tests/library/test_anlz_ingest.py
src/vibemix/library/cue_types.py       # add "anlz"
src/vibemix/library/excerpt.py         # optional index + priority order
tests/library/test_excerpt.py
```

Target command:

```bash
uv run pytest -q tests/library/test_anlz_ingest.py tests/library/test_excerpt.py
```

Success means: vibemix can turn Rekordbox's local ANLZ phrase data into the same
`CueAnchor` contract the rest of the app already consumes, without SQLCipher,
process memory, screen vision, or a new runtime dependency.

That is the door into the whole intelligence upgrade.
