# INTEL-08 roadmap - execution map for intelligence excellence

**Date:** 2026-05-27
**Scope:** dependency graph, milestone cuts, acceptance gates, and ship order
**Depends on:** INTEL-01 through INTEL-23
**Code posture:** roadmap plus implementation status. Several intelligence
fixture/eval primitives now exist; product wiring and private threshold locking
remain future cuts.

## Purpose

The INTEL specs define the system. This file defines the build order.

INTEL-23 is the research-backed bet map for the order below. Treat it as the
filter before adding model swaps, live analyzers, or cue features that are not in
the first no-regret implementation path.

The goal is to ship intelligence in usable cuts, not to wait for the whole
cathedral. Each cut must produce a product improvement, preserve grounding, and
leave the next layer easier to build.

## North star

```text
The DJ asks for a vibe or plays live.
vibemix knows the track sections, knows where the DJ is, ranks real transition
options, explains only grounded facts, exports useful cues, and learns from
Kaan's choices.
```

The agent never invents musical facts. It receives grounded musical objects and
chooses/explains among them.

## Dependency graph

```text
INTEL-01 ANLZ ingest
  -> INTEL-03A ANLZ audit
  -> INTEL-07 ontology
  -> INTEL-02 section objects + INTEL-10 section index
      -> INTEL-03B section retrieval eval
      -> INTEL-14 representation benchmark
      -> INTEL-11 transition slate
          -> INTEL-03C transition scorecard
          -> INTEL-12 grounded tools
              -> INTEL-18 smart cue policy
                  -> INTEL-19 cue baseline comparison
              -> Smart hot cue export
              -> Prep transition planner
              -> INTEL-09 context compiler
                  -> INTEL-21 musical claim contract
                      -> INTEL-20 agentic decision runtime
              -> INTEL-06 live awareness
                  -> INTEL-21 musical claim contract
                      -> INTEL-20 agentic decision runtime
                      -> Live pill next-transition
          -> INTEL-05 taste flywheel
              -> personalized transition ranking
          -> INTEL-15 gold-label loop
              -> calibration/holdout/canary evidence
```

Parallelizable:

```text
INTEL-03A eval audit can build alongside INTEL-01.
INTEL-07 ontology can build before section embeddings.
INTEL-05 feedback schema can build before live pill UI.
INTEL-06 pure live-awareness mapper can build before audio alignment.
INTEL-22 fixture corpus can build before any product-code intelligence PR.
```

## Ship cuts

### Cut A - ANLZ structure floor

Product win:

```text
vibemix reads Rekordbox's own phrase/beatgrid analysis and uses it as the
primary structure source.
```

Scope:

- `anlz_ingest.py`
- `CueSource="anlz"`
- `anchors_for_track`: DJ -> ANLZ -> auto -> empty
- ANLZ audit script

No section-vector store yet. No live pill changes.

Acceptance gates:

```text
uv run pytest -q tests/library/test_anlz_ingest.py tests/library/test_excerpt.py
uv run pytest -q tests/eval/test_intel_anlz_audit.py
uv run ruff check src/vibemix/library/anlz_ingest.py tests/library/test_anlz_ingest.py
```

Product evidence:

```text
local audit JSON shows PSSI coverage >= 80%
parse_error_rate <= 1%
wrong_match_known = 0
```

Cutline:

- If ANLZ matching is ambiguous, return no ANLZ for that track.
- Wrong structure is worse than fallback.

### Cut B - Smart hot cue prep

Product win:

```text
For a selected track or crate, vibemix proposes mix-in, breakdown, drop, and
mix-out cue points from grounded ANLZ sections and exports Rekordbox XML.
```

Scope:

- cue map builder over ANLZ sections
- INTEL-18 smart cue slot policy A-H
- export review XML
- no direct `master.db` writes

Dependencies:

- Cut A
- INTEL-07 cue semantics
- INTEL-18 slot assignment and review/export policy
- INTEL-19 baseline comparison before default enablement

Acceptance gates:

```text
uv run pytest -q tests/library/test_anlz_ingest.py tests/library/test_cue_export.py tests/library/test_toolset.py
```

Product evidence:

```text
manual review: 20 tracks, >=70% cue slot kept/maybe
baseline comparison: vibemix >= Rekordbox auto on targeted A/F or transition utility
0 overwritten DJ cues by default
0 master.db writes
```

Cutline:

- Start with prep/export only. Do not promise live timing.

### Cut C - Section intelligence index

Product win:

```text
Search and reason over sections, not just whole tracks.
```

Scope:

- `SectionIntelligence`
- `section_store`
- section embeddings over ANLZ windows
- `get_track_sections`
- `search_sections`

Dependencies:

- Cut A

Acceptance gates:

```text
uv run pytest -q tests/library/test_section_types.py tests/library/test_section_store.py tests/library/test_section_index_numpy.py tests/library/test_section_ingest.py
uv run pytest -q tests/library/test_toolset.py
```

Product evidence:

```text
done fixture gate: section_role_hit@5 beats whole-track baseline by >=0.15
done fixture gate: section_mixable_window_hit@5 beats whole-track baseline by >=0.10
done fixture gate: section_low_confidence_result_rate <= 0.15
pending private gate: recalibrate against Kaan-reviewed labeled queries
```

Cutline:

- Keep existing whole-track library search untouched.
- Store section vectors separately from track vectors.

### Cut D - Transition slate engine

Product win:

```text
Given one current/outgoing section, vibemix ranks concrete next-track entry
sections with score breakdowns and risk flags.
```

Scope:

- `vibemix.intel.transition_scorer`
- role grammar integration
- genre transition profiles
- transition candidate IDs
- `transition_slate` and `explain_transition` tools

Dependencies:

- Cut C
- INTEL-07

Acceptance gates:

```text
uv run pytest -q tests/intel/test_transition_scorer.py tests/library/test_toolset.py
uv run pytest -q tests/eval/test_intel_transition_scorecard.py
```

Product evidence:

```text
pairwise_accuracy >= 0.75
ndcg@5 >= 0.80
unknown_candidate_id_rate = 0
played_track_leakage_rate = 0
```

Cutline:

- Agent can explain issued candidates only.
- No free-form "try this random track" path.

### Cut E - Prep agent upgrade

Product win:

```text
Set prep becomes section-aware: it can say which cue/section to use for each
transition, not only which track comes next.
```

Scope:

- `MusicalContextPacket` in prep mode
- section-aware set plan
- transition explanations
- export set + smart cues

Dependencies:

- Cut D
- existing v8.2 set builder

Acceptance gates:

```text
uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_toolset.py tests/library/test_codex_curate.py
uv run pytest -q tests/intel/test_context_compiler.py tests/intel/test_decision_validator.py tests/eval/test_intel_decision_runtime_replay.py
```

Product evidence:

```text
agent chooses only issued candidate IDs
unsupported_section_claim_rate = 0
exported XML imports into Rekordbox
```

Cutline:

- This can ship before live playhead is solved.
- It is the lowest-risk "wow" path.

### Cut F - Live awareness holder

Product win:

```text
The live pill knows current track position and current/next section when
confidence is high enough, and stays quiet when it is not.
```

Scope:

- now-playing position source
- `LiveAwarenessService`
- playhead/section confidence
- blend suppression
- backend `next_transition` payload beside old `next_suggestion`

Dependencies:

- Cut A for ANLZ sections
- Cut D for transition slate if recommending next entry

Acceptance gates:

```text
uv run pytest -q tests/audio/test_nowplaying_position.py tests/intel/test_live_awareness.py tests/runtime/test_suggestion.py
```

Product evidence:

```text
timing_claim_below_floor_rate = 0
blend_exact_timing_claim_rate = 0
wrong_section_claim_rate <= 0.05 on local review
```

Cutline:

- Start with now-playing elapsed and load-clock estimates.
- Audio DTW/BeatNet alignment is a later spike, not required for first live cut.

### Cut G - Live next-transition pill

Product win:

```text
During a set, the pill can say "next good entry: Track B cue B" and only gives
bar timing when playhead confidence allows it.
```

Scope:

- live `MusicalContextPacket`
- `PillDecision`
- timing floor policy
- UI-compatible payload

Dependencies:

- Cut D
- Cut F

Acceptance gates:

```text
uv run pytest -q tests/runtime/test_suggestion.py tests/intel/test_context_packet.py tests/intel/test_live_awareness.py
npm --prefix tauri/ui test
```

Product evidence:

```text
unknown_candidate_id_rate = 0
exact timing only above floor
old next_suggestion payload remains compatible until UI migration completes
```

Cutline:

- If UI is busy, expose backend payload first and keep old pill unchanged.

### Cut H - Taste learning

Product win:

```text
The system improves from accepts, rejects, cue edits, and labels without
inventing or exposing private history.
```

Scope:

- feedback ledger
- deterministic TasteModel
- profile projection
- transition scoring taste term
- consent gates

Dependencies:

- Cut D for candidate IDs
- Cut E/G for feedback surfaces

Acceptance gates:

```text
uv run pytest -q tests/intel/test_feedback.py tests/intel/test_taste_model.py tests/intel/test_profile_projection.py
uv run pytest -q tests/eval/test_intel_taste_scorecard.py
```

Product evidence:

```text
done fixture gate: consent_off_long_term_write_rate = 0
done fixture gate: single_session_hard_negative_rate = 0
done fixture gate: technical_bad_candidate_rescued_by_taste = 0
done fixture gate: accepted_suggestion_lift = 0.18 after 31 calibration events
pending private gate: Kaan-reviewed taste labels and product capture surfaces
```

Cutline:

- Explicit feedback first.
- Inferred feedback lower weight.
- No LLM-written permanent preferences.

### Cut I - Optional audio alignment

Product win:

```text
Rekordbox-independent live playhead confidence improves during local-file sets.
```

Scope:

- offline alignment spike
- beat/chroma/subsequence DTW
- optional BeatNet eval
- no runtime dependency until proven

Dependencies:

- Cut F

Acceptance gates:

```text
position_error_bars_p90 <= 2 for exact-timing tier
no new heavy dependency without eval proof
```

Cutline:

- Optional, after live now-playing elapsed path ships.
- Do not block the product on this.

## First three implementation PRs

### PR 1 - ANLZ parser and excerpt integration

Files:

```text
src/vibemix/library/anlz_ingest.py
src/vibemix/library/cue_types.py
src/vibemix/library/excerpt.py
tests/library/test_anlz_ingest.py
tests/library/test_excerpt.py
```

Goal:

```text
DJ -> ANLZ -> auto structure source order.
```

### PR 2 - ANLZ audit and smart cue prep

Files:

```text
scripts/eval/intel_anlz_audit.py
src/vibemix/library/smart_cues.py
tests/eval/test_intel_anlz_audit.py
tests/library/test_smart_cues.py
```

Goal:

```text
Prove coverage, then export reviewable smart cues with INTEL-18 slot policy.
```

### PR 3 - Section store and section search

Files:

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

Goal:

```text
Section-level retrieval exists while whole-track search stays stable.
```

## Product ordering

Ship order by user-visible value and risk:

```text
1. Smart hot cue prep
2. Section-aware set prep
3. Live next-transition without exact timing
4. Live exact bar timing
5. Taste learning
6. Audio-alignment upgrade
```

Reasoning:

- Smart cue prep is immediately valuable and low live-risk.
- Section-aware prep proves musical intelligence before real-time pressure.
- Live recommendations can start without exact timing.
- Exact timing needs trust, confidence floors, and local review.
- Taste learning needs real candidate IDs and feedback surfaces.
- Audio alignment is powerful but not a prerequisite.

## Global invariants

Every cut must preserve:

```text
MusicState single-writer
EvidenceRegistry citation grounding
live audio/observed data as truth
127.0.0.1:8765 main UI socket
no hardcoded model names
no private paths/audio committed
no Rekordbox master.db writes
no process-memory reads
no screen vision reintroduction
```

## Scorecard expansion

INTEL metrics should appear in one scorecard section:

```text
ANLZ coverage
section retrieval delta (implemented in `scripts/eval/intel_section_retrieval.py`)
transition pairwise/nDCG
agent grounding failures
unsupported musical claim rate
decision runtime validator fallback rate
live timing floor violations
synthetic fixture privacy audit
taste privacy/poisoning gates (implemented in `scripts/eval/intel_taste_scorecard.py`)
```

Current first aggregate scorecard:

```text
scripts/eval/intel_scorecard.py
tests/eval/test_intel_scorecard.py
scripts/eval/intel_gate.py
tests/eval/test_intel_gate.py
```

It currently gates ANLZ complete coverage, parse error rate, cue exact/near
agreement, section retrieval deltas, transition accept@3/pairwise ranking,
transition unknown-label count, decision validator fallback rate, exact-timing
floor violations, gold-label validation errors, and taste privacy/poisoning
counters. The public synthetic fixture scorecard is now fully green; private
Kaan-reviewed labels still decide release-grade thresholds.

Fixture-level INTEL thresholds live in:

```text
eval/INTEL-THRESHOLD-LOCK.md
```

`eval/THRESHOLD-LOCK.md` remains the signed legacy hallucination-gate lock. Any
INTEL threshold change still needs a recalibration note.

## Completion definition for the intelligence milestone

The intelligence milestone is not complete when docs exist. It is complete when
current-state evidence proves:

```text
ANLZ structure is primary and audited.
Section search beats whole-track search for transition queries.
Transition slates rank playable section pairs above bad pairs.
The prep agent exports grounded set/cue plans.
The live pill never overclaims timing.
Feedback improves ranking without privacy leaks.
Scorecard gates enforce all of the above.
```

Until then, the goal remains active.
