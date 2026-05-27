# INTEL-05 spec - taste learning and feedback data flywheel

**Date:** 2026-05-27
**Scope:** personalization, feedback capture, taste adaptation, and privacy gates
**Depends on:** `.planning/research/2026-05-27-intel-04-implementation-handoff.md`
**Code posture:** deterministic feedback/taste/profile primitives and the first
synthetic taste scorecard now exist. Product UI capture and durable storage are
still future cuts.

## Goal

Make vibemix improve from the DJ's real behavior without turning memory into a
free-form diary or letting the LLM invent taste.

The intelligence stack should learn from:

- suggestions Kaan accepts, ignores, rejects, or edits;
- cue placements he keeps, moves, deletes, or exports;
- tracks he actually plays after a suggestion;
- transition pairs he labels `would_play`, `maybe`, or `no`;
- live timing corrections and post-set debrief labels.

The learned signal should change deterministic ranking weights and candidate
filters. The LLM may explain taste, but it should not be the source of taste
truth.

INTEL-15 defines the private gold-label protocol. Taste should consume only the
label subsets that are consent-allowed and semantically taste-bearing; technical
and timing negatives calibrate the scorer/live stack instead of becoming
personal preference.

## Existing repo seams

### Profile v1

`src/vibemix/profile/schema.py` currently allows only:

```text
preferred_genre
avg_session_duration
mix_style_tags
tempo_preference_bin
event_type_response_preferences
```

It is consent-gated, capped at 2KB, and rejects additional properties. That is
good. Do not put track titles, section IDs, candidate IDs, or transition history
into `profile.json`.

### Profile builder

`src/vibemix/profile/builder.py` is pure and applies a two-citation rule before
changing tendencies. Preserve that spirit:

- no single feedback event should rewrite taste;
- no LLM extraction should create a preference;
- prior values survive weak evidence.

### Curator taste hint

`src/vibemix/library/_curator_seams.py` already reads the profile only when
consent is on, then renders a compact taste hint into curator prompts. Keep this
as the prompt-facing projection, not the full taste database.

### Memory subsystem

`src/vibemix/memory/store.py` is raw-in/raw-out and explicitly avoids generation
models and live-path imports. INTEL taste data should follow the same pattern:
store raw structured events and deterministic aggregates, not model-written
"insights."

## Architecture

Separate the system into three layers:

```text
FeedbackLedger      # private event log, local only, detailed
TasteModel          # deterministic aggregates and scoring weights
ProfileProjection   # tiny consent-gated prompt summary
```

### Why three layers?

- The ledger needs detail: track IDs, section IDs, candidate IDs, score
  components, user action, timestamps.
- The model needs stable aggregate features: "prefers long blends at 160-175",
  "rejects vocal intros in hardtechno", "likes +energy transitions after
  breakdowns."
- The profile needs privacy and prompt compactness: no track history, no private
  library content, no detailed local paths.

Conflating these is how a useful preference system becomes spooky.

## FeedbackLedger

Local private database, not committed, not sent to the LLM.

Suggested path:

```text
app_data_dir() / "taste_feedback.db"
```

Suggested table:

```text
feedback_events(
  event_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  t_session REAL NOT NULL,
  created_at REAL NOT NULL,

  surface TEXT NOT NULL,          -- live_pill | prep_chat | cue_export | debrief
  action TEXT NOT NULL,           -- shown | accepted | ignored | rejected | edited | played | exported
  label TEXT,                     -- would_play | maybe | no | technical_no | vibe_no | timing_no

  track_id TEXT,
  section_id TEXT,
  candidate_id TEXT,
  from_track_id TEXT,
  from_section_id TEXT,
  to_track_id TEXT,
  to_section_id TEXT,

  role_from TEXT,
  role_to TEXT,
  bpm_delta REAL,
  harmonic_relation TEXT,
  energy_delta REAL,

  score REAL,
  score_json TEXT NOT NULL,       -- score components and risk flags
  context_json TEXT NOT NULL,     -- compact packet snapshot, no raw audio
  source_version TEXT NOT NULL
)
```

No audio. No local file paths. No free-form LLM prose required.

### Event types

Capture these first:

```text
suggestion_shown
suggestion_accepted
suggestion_rejected
suggestion_ignored_timeout
suggestion_played_next
cue_exported
cue_edited
cue_deleted
transition_labeled
timing_claim_wrong
timing_claim_helpful
```

### Action inference

Some feedback can be inferred without UI buttons:

- suggestion shown and the suggested track becomes audible soon -> positive;
- suggestion shown and a different track is loaded/played -> weak negative;
- cue exported and not edited after review -> weak positive;
- cue moved by >8 bars -> timing negative for that section role;
- live pill suppressed during blend -> no feedback unless user opens/asks.

Inferred labels must have lower weight than explicit labels.

## TasteModel

Deterministic aggregate built from the ledger.

Suggested output:

```python
@dataclass(frozen=True, slots=True)
class TasteModel:
    version: str
    generated_at: float
    event_count: int

    role_pair_weights: dict[tuple[str, str], float]
    bpm_delta_preference: dict[str, float]
    harmonic_relation_weights: dict[str, float]
    energy_delta_preference: dict[str, float]
    risk_flag_penalties: dict[str, float]
    section_role_confidence_adjustments: dict[str, float]
    negative_constraints: tuple[TasteConstraint, ...]
```

Example learned facts:

```text
("outro", "intro") +0.08
("drop", "drop") -0.05 unless energy_delta <= 0.1
bpm_delta 0-4 +0.04
bpm_delta >10 -0.10
harmonic_relation same/adjacent +0.05
risk_flag vocal_intro -0.12 for hard_tek
risk_flag low_confidence_section -0.08
```

### Cold start

Cold-start taste is neutral:

```text
taste_score = 0
no learned hard negatives
default transition weights from INTEL-02
```

Do not pretend to know Kaan's taste before enough evidence.

### Minimum evidence rules

Use conservative gates:

```text
min_events_for_any_taste = 10
min_positive_pair_events = 3
min_negative_pair_events = 2
min_sessions_for_hard_negative = 2
max_single_session_weight = 0.35
```

This prevents one weird night from poisoning the model.

### Weighting

Suggested label weights:

```text
explicit would_play       +1.00
explicit maybe            +0.35
explicit no               -1.00
technical_no              -0.80
vibe_no                   -0.70
timing_no                 -0.90
played_next inferred      +0.65
ignored_timeout inferred  -0.20
different_track inferred  -0.30
cue_kept inferred         +0.35
cue_edited inferred       -0.45
```

Decay:

```text
half_life_sessions = 20
```

Taste should adapt, not fossilize.

## ProfileProjection

The prompt-facing profile remains small and allowlisted.

Do not extend profile v1 casually. If extension is needed, create profile v2
with explicit privacy review.

Candidate profile v2 fields:

```text
transition_style_tags:
  long_phrase_blends
  drop_swaps
  harmonic_safe
  energy_lifts
  energy_holds
  vocal_avoidant
  tooly_intros
  breakdown_resets

suggestion_cadence:
  quiet | balanced | proactive
```

Still no track titles, section IDs, or detailed history.

## Integration with transition scoring

INTEL-02 base score:

```text
score =
  0.28 semantic_section_similarity
  0.18 harmonic_fit
  0.14 bpm_fit
  0.14 energy_shape_fit
  0.10 role_fit
  0.08 phrase_alignment_fit
  0.05 taste_fit
  0.03 novelty
  - risk_penalty
```

TasteModel feeds only:

```text
taste_fit
risk_flag_penalties
optional constraints
```

It must not override hard grounding:

- unknown candidate is still rejected;
- unsupported cue remains unsupported;
- low playhead confidence still suppresses timing;
- harmonic/BPM facts are still deterministic facts;
- LLM cannot claim a preference not present in the model/profile.

### Ranking behavior

Taste can reorder close candidates:

```text
if abs(score_a - score_b) <= 0.10:
    taste can choose the more Kaan-like move
```

Taste should not rescue a bad technical transition:

```text
if risk_penalty >= 0.25 or confidence < live_floor:
    taste cannot push candidate above live floor
```

## UI/product feedback surfaces

Start tiny. Do not build a labeling dashboard first.

### Live pill

Minimal controls:

```text
accept / keep
not now
wrong timing
```

Implicit:

- if accepted and played, strong positive;
- if "not now", weak negative for current context, not the track forever;
- if wrong timing, timing model negative.

### Prep chat

Commands:

```text
"more like this transition"
"less vocal intros"
"too much energy jump"
"this cue is late"
"I would play this"
```

These should turn into structured labels against issued candidates. The agent
must not convert vague chat into a permanent preference unless it can attach the
utterance to a current candidate/section.

### Smart cue review

Capture:

- cue kept;
- cue moved;
- cue deleted;
- cue label changed;
- export accepted.

Cue edits are excellent supervision for ANLZ/CUE-DETR confidence calibration.

### Debrief

Post-set:

```text
Top accepted suggestions
Skipped suggestions
Wrong-timing moments
Cue edits
```

Ask for at most 3 labels. Respect the DJ's patience.

## Privacy and consent

Default:

```text
feedback ledger local-only
prompt profile opt-in only
no cloud sync
no private audio
no local file paths in exported eval reports
```

If profile consent is off:

- still allow local session behavior to improve within the current run;
- do not write long-term profile projection;
- do not inject taste hints into prompts;
- consider whether durable ledger storage should also be disabled or retained
  only as non-prompt local analytics. This needs a product/privacy decision.

Recommended product decision:

```text
profile_consent off -> no long-term taste ledger writes
session-only ephemeral taste allowed
```

This is simpler to explain.

## Agent rules

Agent may say:

- "You tend to accept longer phrase-locked blends" only if profile projection
  contains that tag or TasteModel has enough events.
- "You rejected this kind of jump before" only if it references a current
  candidate and a grounded aggregate, not a named private past track.
- "I'll bias away from vocal intros" only after an explicit current-session
  command or stored projection.

Agent must not say:

- "You always hate X" from one label;
- private track-history details in chat unless the user is already discussing
  that track;
- permanent preference claims from inferred weak negatives;
- anything sourced only from model intuition.

## Evaluation

Add to INTEL-03:

```text
taste_pairwise_delta
accepted_suggestion_lift
false_negative_rate_after_taste
single_session_poisoning_test
consent_off_persistence_test
profile_projection_privacy_test
```

Gates:

```text
unknown_preference_claim_rate = 0
consent_off_long_term_write_rate = 0
single_session_hard_negative_rate = 0
accepted_suggestion_lift >= 0.10 after 30 labeled events
technical_bad_candidate_rescued_by_taste = 0
```

Implementation status (2026-05-27):

- `src/vibemix/intel/feedback.py` defines structured feedback rows, JSONL
  loading, consent-off persistence filtering, and privacy checks.
- `src/vibemix/intel/taste_model.py` builds deterministic role-pair taste
  weights only after enough events across multiple sessions; technical labels
  calibrate risk penalties instead of becoming role-pair taste.
- `src/vibemix/intel/profile_projection.py` emits a tiny consent-gated,
  allowlisted prompt projection with no action IDs, section IDs, paths, vectors,
  or track history.
- `scripts/eval/intel_taste_scorecard.py` gates accepted suggestion lift,
  consent-off persistence, single-session poisoning, profile projection privacy,
  unknown preference claims, and technical-bad rescue.
- Public fixture result: `accepted_suggestion_lift=0.18`,
  `consent_off_long_term_write_rate=0`,
  `single_session_hard_negative_rate=0`,
  `technical_bad_candidate_rescued_by_taste=0`.

## Proposed files

Add:

```text
src/vibemix/intel/feedback.py
src/vibemix/intel/taste_model.py
src/vibemix/intel/profile_projection.py
tests/intel/test_feedback.py
tests/intel/test_taste_model.py
tests/intel/test_profile_projection.py
scripts/eval/intel_taste_scorecard.py
```

Alternative if `intel/` package is deferred:

```text
src/vibemix/library/taste_feedback.py
src/vibemix/library/taste_model.py
```

Prefer `vibemix/intel/` once INTEL becomes a real subsystem; it avoids bloating
`library/` with live-agent behavior.

## Build order

### INTEL-05A: feedback schema only

- Done: define `FeedbackEvent` dataclass.
- Deferred: durable local store with path traversal/session-id guard.
- Done: add consent-off no-write behavior.
- Tests only; no UI.

### INTEL-05B: deterministic TasteModel

- Done: aggregate explicit labels.
- Done: add min-evidence and multi-session gates.
- Existing transition scorer already accepts `taste_scores`; product wiring
  remains future work.
- Done: tests for poisoning, cold-start, and no technical rescue.

### INTEL-05C: profile projection

- Done: generate coarse tags from TasteModel.
- Done: keep profile v1 unchanged.
- Done: tests for privacy: no track IDs, section IDs, paths, candidate IDs.

### INTEL-05D: feedback capture surfaces

- Live pill accept/reject/wrong-timing events.
- Prep chat labels tied to issued candidates.
- Smart cue edit events.

### INTEL-05E: debrief loop

- Show 3 highest-value labeling prompts.
- Persist labels as `FeedbackEvent`s.
- Update TasteModel after session.

## No-go list

- No LLM-generated long-term preferences.
- No track titles or paths in prompt profile.
- No free-form memory records as ranking facts.
- No one-session hard negatives.
- No cloud sync by default.
- No taste score overriding grounding/confidence floors.

## Success definition

The loop is working when:

```text
Kaan labels or implicitly accepts/rejects suggestions.
The ledger records those actions as structured local events.
TasteModel adjusts transition ranking only after enough evidence.
The prompt sees only a tiny consent-gated profile projection.
The agent can explain taste without exposing private history or inventing facts.
Eval proves accepted suggestion rate improves without more grounding failures.
```

That is the difference between a clever recommender and a co-host that slowly
becomes *Kaan's* co-host.
