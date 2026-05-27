# Live next-pill contract

Status: implemented slice, 2026-05-27.

This document records the current contract for the set-aware next-track pill:
how live deck state, section evidence, embedding evidence, and validator-safe
claims become an actionable "load this cue next" recommendation.

The feature is not the whole end-state of AI DJing. It is the first stable
runtime slice that makes the pill aware of the current deck, the open target
deck, the source section that is actually playing, and the target cue/section
that should be loaded.

## Purpose

The pill should not merely say "this track is similar." It should answer the
DJ's live question:

> From what is playing now, what track and cue should enter next, when should I
> start it, and why is that musically grounded?

The grounding comes from structured evidence, not from asking a model to
pretend it has perfect ears:

- live deck and playhead state
- track-level CLAP similarity
- section-level vectors where available
- section roles and phrase boundaries
- cue anchors
- BPM and Camelot compatibility
- deterministic transition scores
- a claim ledger that the decision runtime must cite

## Runtime flow

```text
MusicState
  -> runtime/suggestion.py
  -> library/next_suggestion.py
  -> library/section_builder.py + library/section_vectors.py
  -> intel/transition_scorer.py
  -> intel/context_compiler.py
  -> intel/decision_runtime.py
  -> intel/claim_validator.py
  -> next_suggestion wire payload
```

1. `runtime/suggestion.py` reads the current `MusicState` and asks the
   suggestion engine for the best next-track option.
2. `library/next_suggestion.py` starts from the cached embedding shortlist, then
   re-ranks it against the current source section and the open deck.
3. `library/section_builder.py` selects the source section from the current
   playhead. If a stronger upcoming source section is close enough, the engine
   can anchor the recommendation there instead.
4. `library/section_vectors.py` provides section vectors when possible and
   labels the semantic basis honestly when it has to fall back.
5. `intel/transition_scorer.py` scores source/target section pairs for harmonic,
   phrase, energy, tempo, and semantic fit.
6. `intel/context_compiler.py` turns the chosen transition and bounded
   alternatives into an `AgentContextEnvelope` claim ledger.
7. `intel/decision_runtime.py` produces a deterministic action packet such as
   select/hold/suppress with cue, timing text, spoken text, cited claims, and
   confidence.
8. `intel/claim_validator.py` validates the decision against the cited claims.
   Invalid decisions fail soft and are not emitted as trusted guidance.

## Wire payload

The pill payload is attached as `next_suggestion`.

```json
{
  "track_id": "next-track-id",
  "title": "Next Track",
  "artist": "Artist",
  "similarity": 0.82,
  "why": "Similar vibe and compatible transition evidence.",
  "camelot": "8A",
  "bpm": 128.0,
  "transition": {},
  "transition_alternatives": [],
  "decision": {}
}
```

### `transition`

`transition` is the selected, grounded mix-point candidate.

Important fields:

- `source_deck`: the deck currently treated as authoritative source
- `target_deck`: the deck to load next
- `from_track_id` / `to_track_id`
- `from_section_id` / `to_section_id`
- `from_role` / `to_role`
- `from_start_s` / `from_end_s`
- `to_start_s` / `to_end_s`
- `from_bpm` / `to_bpm`
- `from_camelot` / `to_camelot`
- `cue_slot`
- `start_in_bars`
- `score` / `confidence`
- `semantic_basis`
- `timing_basis`
- `timing_anchor`
- `source_anchor_s`
- `source_selection`
- `scores`
- `risk_flags`
- `reasons`

`semantic_basis` must be explicit. Expected values include:

- `section_vector`
- `mixed_section_track`
- `track_vector_fallback`
- `semantic_unknown`

The system must not silently claim section-level semantic certainty when it only
has track-level or unknown evidence.

### `transition_alternatives`

`transition_alternatives` is a bounded ranked list, currently limited to three
items. Each alternative carries:

- a rank-local `candidate_id` such as `tr_001`
- `rank`
- `selected`
- track metadata
- similarity
- the same transition shape as the selected candidate

These IDs are intentionally local to the current payload. The context compiler
normalizes scorer-local duplicates into the current ranked IDs so the decision
runtime can cite the same candidate the UI sees.

The expanded pill renders non-selected alternatives as compact backup rows. The
collapsed hover peek hides backups so the glance stays focused on the selected
action.

### `decision`

`decision` is the validator-checked action packet produced after the claim ledger
is compiled.

Important fields:

- `decision_id`
- `decision_source`
- `emitted`
- `validation_status`
- `validation_errors`
- `action`: usually `select`, `hold`, or `suppress`
- `candidate_id`
- `cue_slot`
- `timing_text`
- `spoken_text`
- `cited_claims`
- `cited_claim_ids`
- `confidence`

The decision runtime should cite claims for musical claims it makes. For
example, if the spoken text mentions cue, timing, section roles, or a semantic
match, the cited claims must support those facts.

## Grounding rules

- Live audio and deck state are authoritative for what is playing.
- Only state refresh writes `MusicState`.
- AI reactions must resolve through `EvidenceRegistry` and claim-ledger
  evidence.
- Model-facing context contains structured facts, not raw audio, local paths, or
  vectors.
- Exact timing is emitted only when the playhead confidence policy allows it.
- Live blend conditions suppress unsafe timing precision.
- Semantic dimension mismatches become unknown evidence, not fabricated matches.
- Missing cue, BPM, Camelot, section, or vector data stays honest-null and must
  lower confidence or add risk flags instead of inventing values.

## Current UI state

The TypeScript pill wire type understands the expanded `transition`,
`transition_alternatives`, and `decision` payloads.

The visible compact line prefers a validator-checked emitted `decision` when it
is an accepted `select` for the same candidate. Rejected, non-emitted,
missing-candidate, stale-candidate, held, or suppressed decisions fall back to
the grounded `transition` text.

The expanded pill renders up to two backup alternatives from
`transition_alternatives`. The collapsed hover peek calls the same renderer with
backups hidden.

## Validation

Focused backend and UI checks used for this slice:

```bash
uv run pytest -q tests/runtime/test_suggestion.py tests/intel/test_context_compiler.py tests/intel/test_decision_runtime.py tests/intel/test_decision_validator.py tests/library/test_next_suggestion.py
npm --prefix tauri/ui test -- next-suggestion
npm --prefix tauri/ui test -- pill/index
```

Broader intelligence/eval checks used before documenting:

```bash
uv run pytest -q tests/intel tests/library/test_next_suggestion.py tests/library/test_setprep_tools.py tests/library/test_toolset.py tests/runtime/test_suggestion.py tests/eval/test_intel_decision_runtime_replay.py tests/eval/test_intel_transition_scorecard.py
npm --prefix tauri/ui run build
```

The Vite build may emit existing chunk-size or dynamic-import warnings; those
warnings are not specific to the live next-pill contract.

## Remaining gaps

- Add real-session replay coverage for live deck changes that cause the source
  section to move while the embedding shortlist remains cached.
- Add richer target-cue operability checks once more CUE-DETR or Rekordbox cue
  data is available.
- Add a DJ command path to actively choose a rendered backup alternative without
  forcing a full rerank.
- Keep improving taste learning and threshold gates so the system learns which
  technically valid transitions the DJ actually accepts.
