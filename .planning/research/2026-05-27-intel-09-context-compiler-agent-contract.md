# INTEL-09: musical context compiler and agent output contract

**Date:** 2026-05-27
**Lane:** intelligence / grounding / agentic engine
**Depends on:** INTEL-01 through INTEL-08
**Status:** build-prep spec; no product code touched

**Runtime continuation:** INTEL-20 defines how these envelopes, decisions, and
validators are orchestrated into deterministic/model-assisted product decisions.
**Claim continuation:** INTEL-21 defines the typed musical claims that populate
`allowed_claims` and make model-written explanations validateable.

## Why this exists

The current app already has a strong anti-hallucination spine:

- `EvidenceRegistry` is the source of citable live facts.
- `AICoach.evidence_line()` compacts current state into a bounded prompt line.
- `CitationLinter` strips unsupported live claims.
- `LibraryToolset` enforces the seen-set gate for library tools.
- Codex/Gemini curator prompts have strict "never invent track_id/BPM/key" rules.
- Output schemas already exist on the Codex set-prep/chat surfaces.

That is the right foundation, but the new musical-intelligence layer adds richer
objects: sections, phrase maps, transition slates, taste weights, playhead
confidence, risk flags, and cue recommendations. If those are dumped directly
into prompts, the model will overfit to noise and invent connective tissue.

So the next intelligence primitive is not "a bigger prompt." It is a compiler:

```text
deterministic musical state
    -> bounded context envelope
    -> structured agent decision
    -> validator
    -> UI / spoken explanation
```

The model should choose and explain among grounded options. It should not create
new musical facts.

## Existing seams to reuse

### Live co-host seam

`src/vibemix/state/coach.py`

- `AICoach.evidence_line()` renders a single live evidence line.
- It is additive and heavily gated: empty new state must produce zero new bytes.
- It avoids reintroducing `phase=` because that primed hallucinated drops.
- It can append deck state, genre, trajectory, registry counts, and recall
  without changing the cold path.

`src/vibemix/prompts/matrix.py`

- `CITATION_GRAMMAR_BLOCK` teaches the source grammar.
- `build_system_instruction()` adds citation, fail-soft, and delivery rules.
- `build_lens_instruction()` maps product lenses onto fixed prompt cells.

`src/vibemix/agent/dj_cohost.py`

- `_build_citation_strip()` turns grounded citations into UI chips.
- `set_next_event()` pre-dispatches expensive retrieval/grounding off-loop.
- The agent pulls latched context at turn time, then snapshots the registry.

`src/vibemix/coach/citation_linter.py`

- Response-level binary gate.
- Time-keyed sources: `ev`, `aud`, `midi`.
- Existence-only sources: `track`, `screen`, `mix`, `tend`, `key`, `recall`.

### Library / prep seam

`src/vibemix/library/toolset.py`

- Shared grounded tool core.
- Discovery populates `seen`.
- Write/order/export surfaces reject un-seen IDs and revalidate against the
  library.

`src/vibemix/library/codex_curate.py`

- Curator voice is shared through `build_curator_instruction()`.
- The hard grounding rules are local to the backend prompts.
- Codex set-prep/chat surfaces already return strict JSON.

### Suggestion seam

`src/vibemix/runtime/suggestion.py`

- Current pill-like suggestion service already lives outside `MusicState`.
- This is the right pattern: suggestions are derived state, not authoritative
  refresh state.

`src/vibemix/library/next_suggestion.py`

- Current implementation is track-level nearest-neighbor.
- The upgrade target is section-level transition slate generation.

## Proposed module boundary

Add a small, import-light package:

```text
src/vibemix/intel/context_compiler.py
src/vibemix/intel/agent_contract.py
src/vibemix/intel/decision_validator.py
tests/intel/test_context_compiler.py
tests/intel/test_agent_contract.py
tests/intel/test_decision_validator.py
```

This package should not import audio capture, Tauri, LiveKit, or model clients.
It is pure Python data shaping and validation.

## Data contracts

### `AgentContextEnvelope`

The bounded packet the LLM sees.

```python
@dataclass(frozen=True, slots=True)
class AgentContextEnvelope:
    schema_version: str
    mode: Literal["prep", "live"]
    intent: Literal[
        "smart_hot_cues",
        "transition_slate",
        "live_next_pill",
        "explain_transition",
        "chat",
    ]
    current: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]
    constraints: dict[str, Any]
    allowed_actions: tuple[str, ...]
    allowed_claims: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    citation_scope: dict[str, tuple[str, ...]]
    confidence_policy: dict[str, float | bool]
```

Rules:

- `schema_version` starts at `"intel_context_v1"`.
- `current` is one compact object, not the whole live state.
- `candidates` is a deterministic slate, capped before the prompt.
- `constraints` are machine-readable facts: max candidates, exact timing gate,
  blend suppression flag, genre modifiers, selected lens.
- `allowed_actions` names what the model may output.
- `allowed_claims` names the only classes of musical claims it may make.
- `forbidden_claims` is explicit and short: no invented track IDs, no invented
  cue slots, no exact bars below confidence, no unsupported key/BPM/energy.
- `citation_scope` lists the IDs registered or otherwise groundable this turn.
- `confidence_policy` carries the exact thresholds from INTEL-06.

### `TransitionCandidateForAgent`

The candidate should already be scored before the model sees it.

```python
@dataclass(frozen=True, slots=True)
class TransitionCandidateForAgent:
    candidate_id: str
    from_track_id: str
    from_section_id: str
    to_track_id: str
    to_section_id: str
    recommended_cue_slot: str | None
    start_in_bars: int | None
    scores: dict[str, float]
    facts: dict[str, str | float | int | bool | None]
    risk_flags: tuple[str, ...]
    deterministic_reason: str
```

Rules:

- `candidate_id` is minted by the transition engine, not the model.
- `recommended_cue_slot` must come from cue generation or a deterministic cue
  slot mapping.
- `start_in_bars` is `None` unless live timing confidence permits it.
- `deterministic_reason` is one short reason generated by code. The model can
  paraphrase it, but cannot add new evidence.
- `scores` should expose components, not a black-box score only.

### `AgentDecision`

The structured output the model returns.

```python
@dataclass(frozen=True, slots=True)
class AgentDecision:
    schema_version: str
    action: Literal["select", "hold", "suppress", "ask"]
    candidate_id: str | None
    cue_slot: str | None
    timing_text: str | None
    spoken_text: str
    cited_claims: tuple[str, ...]
    confidence: float
```

Rules:

- `select` requires a known `candidate_id`.
- `hold` means "good candidates exist, but timing/context is not right."
- `suppress` means "do not surface a pill or spoken call."
- `ask` is for prep/chat only, never live low-latency pill mode.
- `cue_slot` must match the selected candidate.
- `timing_text` must be absent if exact timing is forbidden.
- `spoken_text` is display/TTS copy, but only after validator approval.

## Compiler responsibilities

### 1. Slice the world

The compiler chooses only what the agent needs for this turn.

Live mode:

- current track identity and confidence;
- audible deck and transport confidence;
- current section and next section, if known;
- playhead estimate tier;
- blend suppression state;
- at most five transition candidates;
- taste hints that are allowed by consent and relevant to this turn.

Prep mode:

- the set brief;
- candidate pool summary;
- current ordered sequence if any;
- at most twelve transition candidates;
- smart-cue review candidates;
- taste projection if consent allows it.

Never include:

- raw file paths;
- raw vectors;
- raw waveform excerpts;
- full library dumps;
- full ANLZ phrase lists for every track;
- unbounded chat history;
- private long-term ledger events.

### 2. Normalize musical facts

Convert internal values into stable DJ-facing terms before the model sees them.

Examples:

- ANLZ `high mood` phrase labels -> ontology roles from INTEL-07.
- `bridge/down/chorus` -> `breakdown/drop/build` where genre rules support it.
- numeric BPM delta -> `tight`, `needs pitch`, `tempo bridge`, or `unsafe`.
- Camelot relation -> `same key`, `neighbor`, `relative`, `clash`, `unknown`.
- live position confidence -> `exact bars allowed`, `rounded timing only`,
  `no timing claim`.

The LLM should not be asked to infer these categories from numbers.

### 3. Cap and rank

The transition engine can produce many section pairs. The compiler must make the
prompt small and sharp.

Caps:

- live next-pill: top 5 candidates;
- prep transition explanation: top 8;
- set planning: top 12;
- smart-cue review: top 16 cue anchors;
- chat: only the objects directly referenced by the user.

Ranking should prefer:

- higher confidence;
- lower risk;
- higher transition score;
- candidate diversity across destination tracks;
- taste fit when consent allows it.

### 4. Register citations / groundable IDs

First implementation should not expand `EVIDENCE_SOURCES` unless the codebase
owner explicitly chooses that. The safer first step is:

- use existing `track` citations for track identity;
- keep section and transition IDs inside structured `candidate_id` fields;
- validate `candidate_id` by output validator, not `CitationLinter`;
- add `section` / `transition` citation sources only later, in one coordinated
  change across `EvidenceRegistry`, prompt grammar, linter, tests, and UI chips.

This avoids the current schema-mirror trap in `EvidenceRegistry`: every new
source requires synchronized edits in multiple places.

Future source candidates:

```text
[section:<track_id>:<section_id>]
[trans:<candidate_id>]
[cue:<track_id>:<slot>]
```

Do not add them casually.

### 5. Enforce mode-specific language

The compiler should expose an `allowed_claims` list, and the validator should
enforce it. INTEL-21 is the canonical claim taxonomy and evidence contract.

Live high confidence:

- may say exact or rounded timing;
- may say the cue slot;
- may say key/BPM/energy risk facts;
- may say why a selected transition works.

Live medium confidence:

- may suggest the cue or next track;
- must avoid exact bars/seconds;
- should use "next workable entry" language.

Live low confidence or blend:

- no timing claim;
- normally suppress the pill;
- can show prep-only candidate in UI if the product wants a quiet state.

Prep:

- may reason more fully;
- may ask one clarification;
- may return a structured set/cue plan;
- still cannot invent IDs or facts.

## Prompt arrangement

Use a stable, boring order. This matters more than style.

```text
1. Task contract
2. Grounding rules
3. Current context packet
4. Candidate slate
5. Taste/context constraints
6. Allowed actions
7. Output schema
```

### Task contract

Example:

```text
You are choosing among precomputed DJ transition candidates.
You may select one candidate_id, hold, suppress, or ask.
Do not invent a track, cue, section, key, BPM, timing, or score.
```

### Grounding rules

Keep these as rules, not prose:

```text
- Only choose a candidate_id from the slate.
- Only name tracks in the slate.
- Only mention cue slots present in the selected candidate.
- Only mention exact bars when exact_timing_allowed=true.
- If confidence is below the mode floor, action must be hold or suppress.
- If blend_suppressed=true, do not make a timing claim.
```

### Candidate slate

Use compact records:

```json
{
  "candidate_id": "tr_004",
  "to": "t123#sec_02",
  "cue": "B",
  "entry": "intro_groove",
  "compatibility": 0.82,
  "risk": ["tempo_push"],
  "facts": {
    "key": "neighbor",
    "bpm_delta_pct": 2.1,
    "energy_delta": 0.08,
    "semantic_match": "industrial rolling groove"
  },
  "reason": "intro groove matches current outro density; Camelot neighbor"
}
```

### Output schema

For live pill mode, prefer strict JSON:

```json
{
  "schema_version": "intel_decision_v1",
  "action": "select",
  "candidate_id": "tr_004",
  "cue_slot": "B",
  "timing_text": "start in 16 bars",
  "spoken_text": "Bring track B from cue B in 16 bars; key is neighboring and the intro groove matches this outro.",
  "cited_claims": ["candidate:tr_004"],
  "confidence": 0.78
}
```

The UI may render `spoken_text`, but only after validator approval.

## Validator responsibilities

`decision_validator.py` should be deterministic and mean.

Reject if:

- schema version is unknown;
- action is not allowed in this envelope;
- `candidate_id` is unknown;
- `candidate_id` is present on `hold` or `suppress`;
- selected candidate has lower confidence than the mode floor;
- cue slot differs from the selected candidate;
- `timing_text` exists when exact/rounded timing is forbidden;
- `spoken_text` names a track outside the selected candidate;
- `spoken_text` names a key/BPM/energy fact not present in the selected record;
- `spoken_text` includes a forbidden claim phrase;
- candidate risk requires suppression and action is `select`;
- prep-only `ask` appears in live mode.

Validator outcomes:

```python
@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    reason: str
    safe_decision: AgentDecision | None
```

If validation fails in live mode, degrade to:

- `suppress` for timing/safety failures;
- `hold` for low-confidence but otherwise useful candidate failures;
- no spoken text unless the fallback is deterministic.

## Integration path

### Phase 1: prep-only context compiler

Connect set-prep / smart hot cue prep first.

- Inputs: `SectionIntelligence`, `TransitionCandidate`, optional taste model.
- Output: `AgentContextEnvelope(mode="prep")`.
- Agent returns strict JSON.
- Validator rejects unknown candidate IDs.
- No live `EvidenceRegistry` changes.

Acceptance:

- existing curator cold path unchanged;
- ungrounded candidate ID rejected;
- candidate cap enforced;
- file paths and raw vectors redacted;
- profile consent off yields no taste block.

### Phase 2: live quiet pill compiler

Connect to `SuggestionService` or a sibling `LivePillService`.

- Inputs: `LiveAwarenessSnapshot`, transition slate, taste projection.
- Output: `AgentContextEnvelope(mode="live", intent="live_next_pill")`.
- No `MusicState` writes.
- UI state is derived and replaceable.

Acceptance:

- no exact timing below INTEL-06 threshold;
- blend suppression blocks timing;
- unknown candidate rejected;
- low confidence suppresses spoken output;
- track/cue suggestions still possible when timing is withheld.

### Phase 3: optional citation source expansion

Only after the compiler/validator path is stable:

- add `section`, `transition`, and/or `cue` sources to `EvidenceRegistry`;
- update `CITATION_GRAMMAR_BLOCK`;
- update `CitationLinter`;
- update `_build_citation_strip()` if UI chips should show them;
- update tests that mirror source sets;
- register current envelope IDs before model dispatch.

This is a coordinated schema migration, not a drive-by prompt edit.

## Test plan

### Compiler tests

- `test_live_envelope_caps_candidates_at_five`
- `test_prep_envelope_caps_candidates_at_twelve`
- `test_context_compiler_redacts_file_paths`
- `test_context_compiler_redacts_raw_vectors`
- `test_context_compiler_omits_taste_when_consent_off`
- `test_context_compiler_normalizes_anlz_roles`
- `test_context_compiler_disallows_exact_timing_under_floor`
- `test_context_compiler_suppresses_timing_in_blend`

### Validator tests

- `test_select_unknown_candidate_rejected`
- `test_select_wrong_cue_rejected`
- `test_hold_with_candidate_id_rejected`
- `test_live_ask_rejected`
- `test_timing_text_rejected_when_not_allowed`
- `test_spoken_text_with_out_of_slate_track_rejected`
- `test_low_confidence_live_selection_degrades_to_hold`
- `test_blend_timing_failure_degrades_to_suppress`

### Prompt compatibility tests

- existing `build_system_instruction()` byte-identity tests stay green;
- existing curator grounding rule tests stay green;
- no new citation source appears in `CITATION_GRAMMAR_BLOCK` until the schema
  migration phase;
- `AICoach.evidence_line(MusicState())` remains byte-identical on cold state.

### Replay/eval tests

- replay a saved transition slate and assert deterministic envelope output;
- replay a validator failure and assert deterministic fallback;
- compare agent-selected candidate against top deterministic candidate;
- score whether agent explanation mentions only allowed facts.

## Anti-patterns

- Feeding the LLM raw ANLZ dumps and asking it to find cues.
- Asking the LLM to compute Camelot compatibility from key strings.
- Letting the LLM choose arbitrary track IDs from the whole library.
- Treating confidence as prose instead of a gate.
- Expanding citation sources without updating all schema mirrors.
- Letting live pill suggestions write `MusicState`.
- Using "best effort" output parsing in live mode.
- Keeping taste as free-form prompt memory instead of a deterministic projection.
- Showing exact bars during a blend.

## Open decisions

1. Should live pill mode call an LLM at all, or should v1 render the top
   deterministic candidate directly and use the LLM only for prep explanations?
   Product answer may depend on latency and trust.
2. Should `AgentDecision.spoken_text` be model-written, or should the model only
   select a candidate and a deterministic template writes the final copy?
   The deterministic-template version is less magical but safer.
3. Should section/transition citations become first-class `EvidenceRegistry`
   sources, or are structured candidate IDs enough for v1?
4. What is the maximum acceptable live-pill latency budget after a track change
   or phrase-approach event?

## Recommendation

Ship v1 as:

- deterministic transition slate;
- deterministic context compiler;
- strict structured agent output for prep;
- deterministic live pill copy from selected candidates;
- LLM explanation only in prep/chat surfaces;
- no new citation sources yet.

Then graduate to model-written live pill copy only after replay eval proves that
the validator catches every overclaim and latency stays below the product budget.
INTEL-20 is the canonical runtime policy for that graduation.
INTEL-21 is the claim-level precondition for model-written live copy.
