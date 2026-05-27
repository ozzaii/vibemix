# INTEL-21: musical claim and evidence contract

**Date:** 2026-05-27
**Lane:** grounding / claim validation / musical context / agent safety
**Depends on:** INTEL-03, INTEL-06, INTEL-09, INTEL-11, INTEL-17, INTEL-20
**Status:** first claim-ledger/validator slice implemented
**Code posture:** pure intelligence modules implemented in
`src/vibemix/intel/claims.py` and `src/vibemix/intel/claim_validator.py`, with
context-envelope integration and focused tests. No model client, audio, DB, or
Rekordbox integration changed.

## Goal

Make every musical claim the agent can make explicit, typed, and evidence-bound.

We already have:

- `EvidenceRegistry` for citable live observations;
- `CitationLinter` for bracket citation validity;
- INTEL-09 context envelopes and decision validation;
- INTEL-20 decision runtime and replay traces.

But those pieces still need a middle layer:

```text
What kind of musical fact is this?
Which evidence type is strong enough to say it?
How confident must it be?
Which language is allowed?
What should the validator reject?
```

INTEL-21 defines that contract.

## Thesis

The agent should not reason from raw musical prose. It should reason from
typed claims:

```text
track_identity
section_role
cue_slot
timing
harmonic_fit
tempo_fit
energy_shape
semantic_match
transition_fit
taste_fit
action_result
```

Each claim carries:

- value;
- evidence reference;
- confidence;
- scope;
- allowed language;
- validator rules.

The model may paraphrase approved claims. It may not create new claims.

## Why this exists

Prompt instructions like "do not invent BPM" are necessary but insufficient.
The app needs machine-readable enforcement:

- If a section role came from mid-mood ANLZ with low confidence, the agent may
  say "section boundary" but not "main drop."
- If a candidate has `key_unknown`, the agent may not say "keys work."
- If playhead confidence is low, the agent may suggest a cue but not exact bars.
- If a smart-cue proposal is review-only, the agent may not call it
  export-ready.
- If taste consent is off, the agent may not cite a user preference.

This is claim validation, not just citation validation.

## Existing grounding is not enough

### `EvidenceRegistry`

Good for:

- live event citations;
- track existence citations;
- time-keyed controller/audio observations;
- current prompt/linter path.

Not enough for:

- section-to-section transition facts;
- internal candidate score components;
- cue proposal status;
- exact permission to say "drop", "neighbor key", or "16 bars";
- model output validation against structured candidate records.

### `CitationLinter`

Good for:

- checking whether bracket citations resolve.

Not enough for:

- proving that a spoken sentence only used allowed musical claims;
- checking whether exact timing was allowed;
- checking whether "harmonic fit" was present or invented;
- checking whether a cue was export-ready.

### INTEL-21 answer

Keep `EvidenceRegistry` and `CitationLinter` stable. Add a structured
`MusicClaimLedger` inside the intelligence runtime:

```text
deterministic engines create claims
context compiler includes approved claims
model selects/paraphrases claims
validator checks model output against claim IDs/types
decision trace records emitted claims
```

## Core data contract

```python
@dataclass(frozen=True, slots=True)
class MusicClaim:
    claim_id: str
    claim_type: MusicClaimType
    subject_id: str
    value: str | float | int | bool | None
    unit: str | None
    scope: ClaimScope
    evidence_refs: tuple[str, ...]
    confidence: float
    claim_status: Literal["allowed", "hedged", "internal_only", "rejected"]
    allowed_phrases: tuple[str, ...]
    forbidden_phrases: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance_ref: str
```

`claim_id` shape:

```text
clm_<packet_id>_<zero_padded_ordinal>
```

Examples:

```text
clm_ctx_001_000
clm_ctx_001_014
```

Rules:

- claim IDs are packet-scoped;
- claims are not long-term action IDs;
- public action tools still use track/section/candidate/proposal IDs;
- model output may cite claim IDs in structured fields;
- validator maps claim IDs back to ledger rows.

## Claim scopes

```text
track
section
cue
transition
live_timing
taste
action
system
```

Scope controls which subjects and evidence are valid.

## Claim types

### Identity claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `track_identity` | this track ID/title is the target | library resolution or live identity source |
| `deck_identity` | this deck is audible/current | deck state or live awareness snapshot |
| `library_membership` | track exists in local library | library lookup |

Allowed language:

- "this track"
- track title/artist when library resolution exists
- "current deck" only when live awareness supports it

Rejected:

- naming tracks outside the issued slate;
- title/artist from model memory.

### Structural claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `section_boundary` | a boundary exists at time/beat | ANLZ/DJ/ML/DSP section source |
| `section_role` | intro/groove/build/breakdown/drop/outro/etc. | section record with role confidence |
| `section_duration` | section length in bars/seconds | beatgrid + section boundary |
| `phrase_alignment` | section/cue lands on phrase/downbeat | beatgrid/downbeat evidence |

Allowed language by confidence:

```text
>= 0.78  "drop", "breakdown", "mix-in", role-specific language
0.55-0.77 "likely drop", "works like a breakdown", hedged language
0.35-0.54 "section boundary", no strong role claim
< 0.35   internal only
```

Rejected:

- "main drop" from `unknown` role;
- exact bar counts without beatgrid;
- role claims from fallback whole-track windows.

### Cue claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `cue_slot` | cue A-H exists or is proposed | DJ cue or issued SmartCueProposal |
| `cue_role` | cue's DJ function | INTEL-18 policy result |
| `cue_export_status` | export-ready/review/suppressed/missing | SmartCueProposal status |
| `cue_overwrite_safety` | export will not overwrite human cue | export validator/proposal analysis |

Allowed language:

- "cue B is a good entry" when cue exists in selected candidate/proposal;
- "review-only cue" when status is `review`;
- "export-ready" only when status is `export_ready`.

Rejected:

- saying a cue exists when it is only a suppressed candidate;
- telling the DJ to press a cue slot not in the issued candidate;
- claiming export success without `export_smart_cues` result.

### Technical transition claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `harmonic_fit` | keys compatible/clash/unknown | Camelot/key resolver and scorer |
| `tempo_fit` | BPM delta acceptable/risky | BPM facts and scorer |
| `phrase_fit` | phrase lengths align | beatgrid/section length |
| `cue_operability` | transition has usable cue handles | cue proposal/cue slot scoring |

Allowed language:

- "neighboring key" only when harmonic relation is computed;
- "tempo is close" only when BPM delta is known;
- "phraseable" only when beatgrid/section length supports it;
- "usable cue handle" only when cue slot exists and confidence passes.

Rejected:

- harmonic claims when `key_unknown`;
- tempo claims when either BPM is missing;
- "smooth" without supporting score components.

### Musical character claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `energy_shape` | rise/drop/hold/reset | energy features or deterministic section role policy |
| `density_match` | sparse/dense/holds pressure | section features or scorer component |
| `semantic_match` | vibe/timbre similarity | section embedding similarity and query/source text |
| `vocal_risk` | vocal/hook overlap risk | vocal analysis or metadata/source flag |

Allowed language:

- "energy holds" when energy or role policy supports it;
- "texture matches" when section vectors exist;
- "percussive entry" when density/source supports it.

Rejected:

- "texture matches" when vector is missing;
- "vocal clash" without vocal evidence;
- genre/persona color masquerading as fact.

### Timing claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `current_position` | current playhead/section position | live awareness snapshot |
| `bars_until_event` | exact/rounded bars to cue/section | playhead confidence + beatgrid |
| `blend_suppression` | timing should be withheld | live blend state |

Allowed language:

```text
playhead_confidence >= 0.80:
  exact bars allowed

0.70 <= playhead_confidence < 0.80:
  rounded/soon language only

0.50 <= playhead_confidence < 0.70:
  cue/track suggestion only, no timing

< 0.50 or blend active:
  suppress timing claim
```

Rejected:

- exact seconds/bars under threshold;
- timing during blend suppression;
- "now" calls without current-position confidence.

### Taste claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `taste_preference` | user generally prefers a pattern | consented taste profile |
| `taste_fit` | candidate matches current taste model | deterministic taste projection |
| `taste_uncertain` | not enough taste evidence | missing/low-confidence profile |

Allowed language:

- "this matches your recent preference for tooly intros" only when the taste
  profile exposes that aggregate and consent allows it;
- "I am not sure yet" when taste confidence is low.

Rejected:

- model-created preferences;
- private named track examples unless explicitly allowed;
- long-term taste writes from chat prose.

### Action claims

| Claim type | Meaning | Minimum evidence |
|------------|---------|------------------|
| `export_result` | file was written | action tool success |
| `playlist_created` | playlist/M3U/JSON exists | action tool success |
| `proposal_issued` | cue/transition proposal exists | holder entry |
| `decision_suppressed` | runtime intentionally stayed quiet | INTEL-20 trace |

Allowed language:

- "exported" only after successful tool result;
- "I stayed quiet because playhead confidence was low" only when trace has that
  reason.

Rejected:

- claiming a write happened from final JSON alone;
- hiding failed export as "prepared."

## Evidence reference taxonomy

```text
evreg:<source>:<body>          # existing EvidenceRegistry atom
track:<track_id>               # library-resolved track
section:<section_id>           # SectionRecord
candidate:<candidate_id>       # TransitionCandidate
cue:<cue_id>                   # SmartCue
proposal:<proposal_id>         # SmartCueProposal
packet:<packet_id>             # AgentContextEnvelope
decision:<decision_id>         # AgentDecision/RuntimeDecision
score:<candidate_id>:<component>
taste:<taste_snapshot_id>
action:<tool_name>:<result_id>
run:<provenance_run_id>
```

These are internal evidence refs, not necessarily text citations. Only add new
`EvidenceRegistry` citation sources when INTEL-09 phase 3 is intentionally
implemented.

## MusicClaimLedger

Implementation target:

```python
@dataclass(slots=True)
class MusicClaimLedger:
    packet_id: str
    claims: dict[str, MusicClaim]

    def add(...): ...
    def allowed_for_model(self) -> tuple[MusicClaim, ...]: ...
    def validate_claim_ids(self, ids: Sequence[str]) -> ValidationResult: ...
```

Rules:

- created during context compilation;
- belongs to one packet;
- stored with `issued_context_packets` or adjacent holder;
- exported to decision trace as redacted structured facts;
- never sent as an unbounded dump to the model.

Current implementation:

- `MusicClaimLedger` mints packet-scoped `clm_<packet_id>_<ordinal>` IDs;
- public summaries expose claim type, subject, value, confidence, status, and
  phrase allowances, but not raw evidence blobs;
- unsafe evidence refs such as local paths, `file://` URLs, raw audio refs, and
  raw vector refs are redacted and force the claim to `rejected`;
- `compile_transition_context()` now attaches `claim_ids`, `claim_summary`, and
  `citation_scope["claim"]`;
- `validate_agent_decision()` calls `validate_decision_claims()` so strict
  context packets reject cue/timing/harmonic/tempo/export/taste copy unless the
  decision cites matching claim IDs.

## Context packet integration

Add to `AgentContextEnvelope`:

```python
claim_ids: tuple[str, ...]
claim_summary: tuple[dict[str, Any], ...]
```

`claim_summary` is compact:

```json
{
  "claim_id": "clm_ctx_001_004",
  "type": "harmonic_fit",
  "subject_id": "tr_002",
  "value": "neighbor",
  "confidence": 0.92,
  "allowed_phrases": ["neighboring key", "harmonically close"]
}
```

Do not include:

- raw vectors;
- local paths;
- full ANLZ dumps;
- private taste ledger rows.

## AgentDecision integration

Add:

```python
cited_claim_ids: tuple[str, ...]
```

Rules:

- every nontrivial musical sentence in model-written `spoken_text` must be
  backed by at least one claim ID;
- deterministic live copy can skip textual claim IDs if it uses only one
  selected candidate and the trace records the source claims;
- prep/chat explanations should include claim IDs internally even if UI hides
  them.

## Validator rules

Reject or degrade when:

- decision references unknown claim ID;
- claim ID is not in packet ledger;
- claim status is `internal_only` or `rejected`;
- spoken text contains a forbidden phrase for the claim;
- spoken text implies a claim type that is absent;
- exact timing phrase appears without timing claim;
- cue-slot phrase appears without cue claim;
- harmonic phrase appears without harmonic claim;
- taste phrase appears without taste claim and consent.

The first implementation can use conservative phrase detectors. It does not
need full natural-language understanding.

Suggested detectors:

```text
timing phrase: /\b(in|after) \d+ (bar|bars|beat|beats|second|seconds)\b/
cue phrase: /\bcue [A-H]\b|\bhot cue\b/i
harmonic phrase: /\bkey|harmonic|camelot|neighbor\b/i
tempo phrase: /\bbpm|tempo|pitch\b/i
drop phrase: /\bdrop|breakdown|build|outro|intro\b/i
export phrase: /\bexported|wrote|saved\b/i
taste phrase: /\byou usually|your preference|you like\b/i
```

False positives should degrade to deterministic copy in live mode, not crash.

## Deterministic copy integration

INTEL-20 deterministic templates should be generated from claims:

```text
"Next good entry: {track_short} cue {slot} in {bars} bars."
```

requires:

- `track_identity`
- `cue_slot`
- `bars_until_event`

If `bars_until_event` is missing:

```text
"Next good entry: {track_short} cue {slot}."
```

If `cue_slot` is missing:

```text
"Next good entry: {track_short}."
```

If `track_identity` is missing:

```text
suppress
```

## Eval metrics

Add to INTEL-03 scorecards:

```text
unsupported_claim_rate
missing_claim_id_rate
forbidden_phrase_rate
claim_status_violation_rate
claim_confidence_calibration
deterministic_copy_claim_coverage
model_copy_claim_coverage
```

Gates for agentic surfaces:

```text
unsupported_claim_rate = 0
missing_claim_id_rate = 0
claim_status_violation_rate = 0
timing_claim_without_timing_evidence = 0
export_claim_without_tool_success = 0
```

## Implementation handoff

Add:

```text
src/vibemix/intel/claims.py
src/vibemix/intel/claim_validator.py
tests/intel/test_claims.py
tests/intel/test_claim_validator.py
tests/eval/test_intel_claim_grounding.py
```

Wire into:

```text
context_compiler.py
decision_validator.py
decision_runtime.py
scripts/eval/intel_agent_grounding.py
```

Import posture:

- pure dataclasses/enums/regex;
- no audio decode;
- no model client;
- no Rekordbox DB;
- no file system access except eval scripts.

## Acceptance tests

- `test_claim_id_shape_is_packet_scoped`
- `test_harmonic_claim_requires_computed_relation`
- `test_tempo_phrase_rejected_without_bpm_claim`
- `test_exact_timing_phrase_rejected_without_timing_claim`
- `test_review_only_cue_cannot_be_called_export_ready`
- `test_exported_phrase_requires_action_success_claim`
- `test_taste_phrase_rejected_without_consent_claim`
- `test_internal_only_claim_not_visible_to_model`
- `test_live_validator_degrades_for_forbidden_phrase`
- `test_deterministic_copy_drops_bars_when_timing_claim_missing`
- `test_claim_ledger_redacts_paths_and_vectors`

## No-go checks

Reject implementation if:

- model can introduce claim IDs;
- model-written text is emitted before claim validation;
- claim validation depends on another LLM;
- missing claim evidence is treated as a warning only;
- taste claims can be created from free-form chat;
- export claims can be made from planned actions instead of tool results;
- exact timing can bypass INTEL-06 playhead floors.

## Open questions

1. Should claim IDs be hidden entirely from model text and used only in JSON, or
   should prep explanations expose them for debug mode?
2. Should future `EvidenceRegistry` sources (`section`, `trans`, `cue`) mirror
   claim IDs, or remain separate for simpler live citation grammar?
3. How strict should phrase detectors be before we have a labeled corpus of
   model overclaims?
4. Should deterministic copy always include claim IDs in the UI payload for
   debrief inspection?

## Recommendation

Implement this before enabling model-written live copy.

For v1:

```text
live_pill:
  deterministic templates from claims

prep_plan/prep_chat:
  model may write explanations, but every musical sentence must map to claims

eval:
  score unsupported claims separately from bad taste/ranking
```

This makes grounding legible at the exact level users notice: not "the agent
used a tool," but "the agent was allowed to say that."
