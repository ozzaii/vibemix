# INTEL-20: agentic decision runtime

**Date:** 2026-05-27
**Lane:** agentic engine / decision loop / grounding / live-prep orchestration
**Depends on:** INTEL-02, INTEL-09, INTEL-12, INTEL-17, INTEL-18, INTEL-19, INTEL-21
**Status:** first deterministic/model-degrade runtime slice implemented
**Code posture:** pure runtime orchestration, redacted traces, and replay eval
are now present under `src/vibemix/intel/` and `scripts/eval/` with focused
tests. Product UI migration/default wiring remains a future cut.

## Goal

Define the runtime loop that turns grounded musical objects into product
decisions.

Existing specs already cover:

- INTEL-02: section-aware musical context and pill objects;
- INTEL-09: context compiler, strict agent output, and validator;
- INTEL-12: grounded tool/action holders;
- INTEL-17: provenance and replay;
- INTEL-18/19: smart cue policy and baseline comparison.

The missing piece is orchestration:

```text
When do we trust deterministic scoring?
When is an LLM allowed to choose or explain?
What happens when the LLM overclaims?
How does live mode stay fast and quiet?
What artifact proves the final decision was grounded?
```

INTEL-20 defines the answer.

INTEL-21 supplies the typed claim ledger used by the context compiler and
validator. INTEL-20 decides when to emit; INTEL-21 decides what can be said.

## Thesis

The excellent agent is not a free-form recommender. It is a bounded decision
runtime:

```text
sensors + library + ANLZ + embeddings + taste
  -> deterministic candidates
  -> policy gates
  -> optional model selection/explanation
  -> deterministic validator
  -> product decision or honest silence
  -> replayable trace
```

The LLM is useful for language, preference tradeoffs, and prep-time reasoning.
It should not own musical truth, timing, cue placement, or export payloads.

## Existing repo anchors

### Live state and evidence

- `MusicState` has a single-writer invariant.
- `AICoach.evidence_line()` is the current prompt boundary for live claims.
- `EvidenceRegistry` and `CitationLinter` already catch unsupported live claims.
- `DJCoHostAgent` has slop suppression, citation linting, and `<silence/>`
  short-circuit behavior.

### Current pill path

- `src/vibemix/runtime/suggestion.py`
  - `SuggestionService` holds derived UI state outside `MusicState`;
  - computes off-loop;
  - returns `None` for honest silence.
- `src/vibemix/library/next_suggestion.py`
  - grounded track-level next suggestion;
  - only returns library-resolved tracks;
  - never runs cue detection in the real-time path.

This is the right architecture. INTEL-20 keeps the same holder pattern and
replaces the ranking core with section-level, cue-aware candidates.

### Prep/tool path

- `LibraryToolset` already has run-scoped `seen` grounding for tracks.
- INTEL-12 extends that to sections, transition candidates, cue proposals, and
  context packets.
- Codex/Gemini set-prep already expects strict JSON and tool traces.

## Runtime modes

### `prep_plan`

User asks for a set, transition plan, or smart cue prep.

Traits:

- latency budget is seconds;
- LLM may ask one clarifying question;
- LLM may choose among issued candidates;
- explanations may be richer;
- exports still require issued IDs and deterministic tool validation.

### `prep_chat`

User asks "why this track?" or "how should I mix these?"

Traits:

- explanation-first;
- no writes unless an action tool succeeds;
- may show multiple alternatives;
- may surface uncertainty and ask for taste.

### `live_pill`

The app surfaces a next-entry suggestion during a set.

Traits:

- latency budget is tight;
- silence is often correct;
- no clarification questions;
- exact timing only above INTEL-06 floor;
- deterministic copy is preferred for v1;
- LLM output, if used, is optional and fully discardable.

### `live_chat`

The DJ explicitly asks during a set.

Traits:

- can be more conversational than `live_pill`;
- still respects live confidence floors;
- should avoid long answers;
- may say "I cannot call exact bars right now" when playhead is weak.

## Core state machine

```text
IDLE
  -> GATHER
  -> SCORE
  -> GATE
  -> DECIDE_DETERMINISTIC or DECIDE_MODEL
  -> VALIDATE
  -> EMIT or HOLD or SUPPRESS
  -> TRACE
```

### `GATHER`

Collect only grounded inputs:

- current/live track identity;
- live awareness snapshot if available;
- section records;
- transition candidates;
- smart cue proposals;
- taste projection if consent allows it;
- user intent and mode.

Never collect:

- raw local paths for the model;
- raw vectors;
- raw audio;
- full library dumps;
- unbounded chat transcript;
- private taste ledger rows.

### `SCORE`

Run deterministic engines:

- section retrieval;
- transition slate scoring;
- cue operability scoring;
- taste projection;
- risk flags;
- confidence gates.

The output is a bounded slate, not prose.

### `GATE`

Apply product policy before the LLM sees anything.

Hard gates:

```text
no grounded current track -> suppress live pill
no section map -> track-level fallback or suppress
playhead confidence below floor -> no exact timing
blend suppression active -> no exact timing, maybe suppress live pill
candidate below score floor -> hold/suppress
required ID not issued -> reject
export action requested without issued proposal -> reject
human cue overwrite risk -> review only
private data consent off -> omit taste block
```

Soft gates:

```text
missing key/BPM -> lower confidence, do not invent
mid/low ANLZ mood -> review language
high risk but high excitement -> prep-only unless user asks
repeated same artist -> diversity penalty
```

### `DECIDE_DETERMINISTIC`

No LLM call.

Use when:

- mode is `live_pill`;
- top candidate is clearly above threshold;
- explanation can be templated from deterministic reason codes;
- latency matters;
- model budget is exhausted;
- model is unavailable;
- user asked for quiet/productive operation.

Output:

```text
PillDecision or AgentDecision with decision_source="deterministic"
```

### `DECIDE_MODEL`

Bounded LLM choice/explanation.

Use when:

- mode is `prep_plan`, `prep_chat`, or explicit `live_chat`;
- candidate tradeoff is subjective;
- user taste/context needs language;
- multiple valid slates need a human-facing recommendation;
- explanation quality matters more than latency.

Rules:

- model receives only an `AgentContextEnvelope`;
- model returns only strict `AgentDecision`;
- model may select/hold/suppress/ask only from allowed actions;
- model may not invent IDs or facts;
- model-written copy is not emitted before validation.

### `VALIDATE`

Run deterministic validator from INTEL-09/12.
Also run INTEL-21 claim validation before emitting model-written language.

Validation can:

- accept;
- degrade to deterministic fallback;
- hold;
- suppress;
- reject action and ask for user confirmation in prep only.

Live mode degradation must be silent or deterministic. Do not ask the LLM to fix
itself on the live path.

### `EMIT`

Emit only after validation:

- UI pill;
- spoken line;
- set plan;
- cue proposal;
- export result;
- quiet state.

Every emitted decision carries:

```text
decision_id
decision_source
context_packet_id
candidate_id or proposal_id when applicable
validation_status
confidence
suppressed_reasons
provenance_ref
```

### `TRACE`

Write a replayable private trace:

```text
input snapshot IDs
candidate slate IDs
gate outcomes
context packet hash
model request hash if any
raw model decision if any
validator result
final emitted decision
latency breakdown
```

Redact local paths, raw vectors, and private prose before any committed report.

## Decision source policy

```python
DecisionSource = Literal[
    "deterministic",
    "model_validated",
    "model_degraded_to_deterministic",
    "model_rejected_hold",
    "model_rejected_suppress",
]
```

Interpretation:

- `deterministic`: no model call; product acted from scorer/template.
- `model_validated`: model chose/explained and validator accepted.
- `model_degraded_to_deterministic`: model output failed, but deterministic top
  candidate was safe to emit.
- `model_rejected_hold`: useful candidate exists, but model output or context
  confidence prevents emission.
- `model_rejected_suppress`: no safe user-visible output.

Never hide this in logs. It is the fastest way to debug "the agent felt weird."

## Confidence policy

Use separate confidence concepts:

```text
data_confidence       -> source facts are reliable
score_confidence      -> candidate ranking is reliable
playhead_confidence   -> live position/timing is reliable
action_confidence     -> final decision is safe to emit
language_confidence   -> spoken/explanation text is supported
```

Do not collapse these into one scalar in internal code. A candidate can have
high transition score and low playhead confidence; that means "suggest cue,
avoid exact bars," not "bad candidate."

Suggested live policy:

| Condition | Product behavior |
|-----------|------------------|
| no current track | suppress |
| current track known, no playhead | prep-style next cue only, no timing |
| playhead medium | rounded "soon/next phrase" language only |
| playhead high | exact bars allowed |
| blend active | suppress exact timing |
| candidate score weak | hold/suppress |
| validator fails language only | deterministic copy fallback |
| validator fails action grounding | suppress |

## Deterministic copy templates

Live v1 should use deterministic copy whenever possible.

Templates:

```text
select_no_timing:
  "Next good entry: {track_short} from cue {slot}."

select_rounded:
  "Next good entry: {track_short} from cue {slot} soon."

select_exact:
  "Next good entry: {track_short} cue {slot} in {bars} bars."

hold:
  no visible/spoken output, optional quiet UI state

suppress:
  no output
```

Prep explanations can be longer but should still be assembled from reason
codes:

```text
{to_track} cue {slot} works because {reason_1}. Watch {risk_flag}.
```

The LLM may improve tone in prep/chat. In live pill mode, tone is less important
than being right and not annoying.

## Action taxonomy

```text
select_transition
hold
suppress
ask
propose_cues
export_cues
export_set
explain
compare
```

Allowed by mode:

| Action | prep_plan | prep_chat | live_pill | live_chat |
|--------|-----------|-----------|-----------|-----------|
| select_transition | yes | yes | yes | yes |
| hold | yes | yes | yes | yes |
| suppress | yes | yes | yes | yes |
| ask | yes | yes | no | rare |
| propose_cues | yes | yes | no | no |
| export_cues | yes, with confirmation/tool | yes, with confirmation/tool | no | no |
| export_set | yes, with confirmation/tool | yes, with confirmation/tool | no | no |
| explain | yes | yes | no | yes |
| compare | yes | yes | no | yes |

## Runtime artifact contract

```python
@dataclass(frozen=True, slots=True)
class AgentDecisionTrace:
    trace_id: str
    mode: RuntimeMode
    intent: str
    decision_source: DecisionSource
    input_snapshot_id: str
    context_packet_id: str | None
    candidate_ids: tuple[str, ...]
    selected_candidate_id: str | None
    selected_proposal_id: str | None
    gate_results: tuple[GateResult, ...]
    model_call_id: str | None
    validation_result: ValidationResult
    final_action: str
    final_payload_hash: str
    suppressed_reasons: tuple[str, ...]
    latency_ms: dict[str, int]
```

Private trace path:

```text
eval/private/intel/decision_traces/YYYYMMDD.jsonl
```

Redacted aggregate path:

```text
.planning/eval/reports/intel_decision_runtime_YYYYMMDD.md
```

## Latency budget

Suggested initial budgets:

| Segment | live_pill target |
|---------|------------------|
| gather current state | <= 20 ms |
| section/slate lookup | <= 60 ms |
| deterministic gates | <= 10 ms |
| context compile | <= 20 ms |
| model call | not in v1 live default |
| validation | <= 10 ms |
| emit | <= 20 ms |

Live v1 target:

```text
deterministic live pill <= 150 ms after trigger
model-assisted live chat best effort, not a pill dependency
```

Prep can spend seconds if it produces materially better plans.

## Failure handling

### Model unavailable

Prep:

- use deterministic plan;
- say model explanation unavailable if needed.

Live:

- no user-facing error;
- deterministic pill or suppress.

### Validator rejects model text

Prep:

- show deterministic explanation or ask user to retry;
- log `model_rejected_hold`.

Live:

- suppress or deterministic copy;
- no model retry loop.

### Candidate holder expired

All modes:

- reject action;
- ask user to refresh plan in prep/chat;
- suppress in live.

### Library item no longer resolves

All modes:

- drop candidate;
- recompute if cheap;
- otherwise hold/suppress.

### Export fails

Prep/chat only:

- return tool error;
- do not claim export succeeded;
- keep proposal ID available if still valid.

## Evals

### Offline replay

Input:

```text
saved live/prep snapshots
transition slates
context packets
model decisions
```

Metrics:

```text
unknown_id_rejection_rate
unsupported_claim_rate
unsupported_musical_claim_rate
validator_fallback_rate
deterministic_vs_model_selection_delta
correct_suppression_rate
live_latency_p95
exact_timing_floor_violation_rate
action_grounding_violation_rate
```

Current implementation:

- `decision_runtime.decide()` emits deterministic live-pill decisions by
  default and accepts an optional injected model backend for prep or explicit
  live experiments;
- `validate_and_degrade()` rejects unsafe model output and only degrades to
  deterministic copy for language/claim failures, not action-grounding failures;
- `decision_trace.AgentDecisionTrace` records `DecisionSource`, gates,
  validation status, selected IDs, payload hash, suppressed reasons, and redacts
  local paths/vectors/audio refs;
- `scripts/eval/intel_decision_runtime_replay.py` replays saved context packets
  and decisions into the validator and reports grounding/claim/timing metrics.

### A/B modes

Compare:

```text
deterministic_only
model_selects_candidate
model_explains_only
model_selects_and_explains
```

The likely winning product shape:

```text
live_pill: deterministic_only or model_explains_only later
prep_plan: model_selects_and_explains, validator gated
prep_chat: model_explains_only unless user asks for replanning
```

### Human review

Label:

- Was silence better than a suggestion?
- Was the selected candidate useful?
- Was the timing claim acceptable?
- Was the explanation grounded?
- Did the agent ask when it should have acted?
- Did the agent act when it should have asked?

## Implementation handoff

Add:

```text
src/vibemix/intel/decision_runtime.py
src/vibemix/intel/decision_trace.py
tests/intel/test_decision_runtime.py
tests/intel/test_decision_trace.py
scripts/eval/intel_decision_runtime_replay.py
tests/eval/test_intel_decision_runtime_replay.py
```

Core APIs:

```python
def decide(
    mode: RuntimeMode,
    intent: str,
    snapshot: RuntimeInputSnapshot,
    *,
    model_backend: DecisionModel | None = None,
    policy: DecisionRuntimePolicy | None = None,
) -> RuntimeDecisionResult: ...

def validate_and_degrade(
    envelope: AgentContextEnvelope,
    decision: AgentDecision,
    deterministic_fallback: AgentDecision | None,
) -> RuntimeDecisionResult: ...
```

Import posture:

- no audio capture;
- no Tauri;
- no model-router at import time;
- model backend is injected;
- pure deterministic tests require no network.

## Acceptance tests

Runtime tests:

- `test_live_pill_uses_deterministic_path_by_default`
- `test_live_pill_suppresses_when_no_current_track`
- `test_live_pill_blocks_exact_timing_in_blend`
- `test_live_pill_degrades_bad_model_text_to_deterministic_copy`
- `test_live_pill_suppresses_unknown_candidate_action`
- `test_prep_allows_ask_but_live_pill_rejects_ask`
- `test_export_action_requires_issued_proposal`
- `test_decision_source_recorded`
- `test_trace_redacts_paths_and_vectors`
- `test_model_unavailable_uses_deterministic_fallback`

Replay tests:

- `test_replay_reconstructs_same_gate_results`
- `test_replay_flags_unknown_candidate`
- `test_replay_counts_timing_floor_violation`
- `test_replay_reports_validator_fallback_rate`

Compatibility tests:

- existing `tests/runtime/test_suggestion.py` keeps old payload behavior until UI
  migration;
- existing citation linter tests remain unchanged unless INTEL-09 phase 3 adds
  new citation sources;
- old `next_suggestion` may remain as fallback until section slate is default.

## No-go checks

Reject implementation if:

- live pill depends on an LLM call for basic output;
- model output can write files directly;
- model output can introduce candidate/proposal IDs;
- validator failure still emits model-written copy;
- unsupported claim failure still emits model-written copy;
- live mode retries model output in a loop;
- decision trace stores raw file paths, vectors, or audio;
- `MusicState` is written by the decision runtime;
- exact bars appear when playhead confidence is below the floor.

## Open decisions

1. Should live `select_no_timing` show visually, or should low-timing confidence
   suppress the pill entirely unless the DJ opens it?
2. Should model-assisted prep selection be enabled before or after the first
   INTEL-15 gold-label slice?
3. Should deterministic live copy include artist/title, or only cue/action to
   reduce screen clutter?
4. What is the UI affordance for a `hold` state, if any?

## Recommendation

Ship in this order:

```text
1. deterministic runtime wrapper over current next_suggestion
2. trace + validator-degrade harness
3. prep model selection over issued transition slates
4. deterministic live next-transition pill
5. model-written live copy only after replay eval proves safety
```

The important product choice: silence is a first-class successful decision.
That is how vibemix stays trustworthy in a live set.
