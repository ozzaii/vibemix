# INTEL-02 spec - agentic musical context and grounded suggestion engine

**Date:** 2026-05-27
**Scope:** implementation-ready research/spec for the intelligence lane after ANLZ ingest
**Depends on:** `.planning/research/2026-05-27-intel-01-anlz-structure-spec.md`
**Code posture:** no product code changed in this research pass

## Goal

Turn vibemix from a track recommender with a chat surface into a grounded musical
planning agent:

```text
track-level vibe search
  -> section-level musical objects
  -> deterministic transition slates
  -> compact context packets
  -> agent chooses/explains only among grounded options
```

The LLM must never be asked to "hear" or infer the raw musical truth by itself.
It should receive a small, verified packet that says:

- what track is active;
- where we probably are in that track;
- what section is current and what section is coming;
- what candidate entries into other tracks are musically/technically compatible;
- why each candidate is compatible or risky;
- what facts are uncertain.

The agent's job is policy and language over facts. The engine's job is truth.

## Why this matters

The earlier product shape had two ceilings:

1. **Track-level embeddings collapse the music.** A single CLAP vector can find a
   vibe, but cannot say "this outro texture matches that intro groove" or "this
   next drop will land too soon."
2. **General audio LLM listening is not reliable enough for DJ timing.** The
   model can discuss music, but we need beat, phrase, key, deck, and cue claims
   to be deterministic or explicitly uncertain.

The new shape solves both:

- ANLZ gives beatgrid + phrase structure for most of Kaan's Rekordbox library.
- Section embeddings describe *parts* of tracks instead of whole tracks.
- Transition scoring generates a small slate of valid section-to-section moves.
- The agent explains, filters, and adapts taste inside that slate.

## Existing repo anchors

Observed seams that should be reused instead of bypassed:

- `MusicState` is single-writer, refreshed at 10Hz. Agent and detectors are
  read-only consumers.
- `EvidenceRegistry` is the live anti-hallucination spine. It currently supports
  `ev`, `aud`, `midi`, `track`, `screen`, `mix`, `tend`, `key`, and `recall`.
- `SuggestionService` already owns the pill's derived "what next" state outside
  `MusicState`.
- `LibraryToolset` already enforces a per-run `seen` set: write tools can only
  use IDs surfaced by grounded discovery.
- `next_suggestion.py` is track-level today: seed vector -> candidate track,
  with optional Camelot/BPM refinement.
- `sequencer.py` already has set-level energy and harmonic reasoning.
- `quote_moment` already gives the product a way to point at a concrete moment.

Keep those invariants. Add intelligence beside them.

## Core principle: enumerate first, reason second

Do not let the agent search all tracks or all sections directly when the answer
will become a product action.

Use this flow:

```text
1. Resolve live/prep context.
2. Deterministic engine generates a bounded candidate slate.
3. Agent selects, rejects, asks taste questions, or explains.
4. Export/action tools validate candidate IDs against the issued slate.
```

This is the same idea as the current playlist grounding gate, but one level
deeper: tracks -> sections -> transitions -> actions.

## Data model

### Section identity

Canonical public/runtime section IDs use the INTEL-10 shape:

```text
section_id = "<track_id>#s<zero_padded_ordinal>"
```

Examples:

```text
rb-123#s007
rb-123#s014
folder-9#s003
```

Properties:

- local-only, not globally meaningful;
- deterministic for the active canonical section map of a track;
- safe to pass through tools as an opaque string;
- source/provenance is metadata, not part of the public ID.

Why source is not embedded in `section_id`: the active section map is already
resolved by priority (DJ -> ANLZ -> auto -> fallback). Keeping IDs short makes
tools, UI, validator output, and future citations easier to read. If a future
debug/audit mode exposes multiple competing analyses for the same track, add a
separate `analysis_id` or `source_key`; do not fork the public section ID shape.

### `SectionIntelligence`

One row per musical section:

```python
@dataclass(frozen=True, slots=True)
class SectionIntelligence:
    section_id: str
    track_id: str
    role: str  # intro | build | breakdown | drop | outro | groove | bridge | unknown
    source: str  # dj | anlz | auto | fallback
    source_detail: str | None  # e.g. hotcue, pssi, cue_detr, dsp, all_in_one
    confidence: float

    start_s: float
    end_s: float
    start_beat: int
    end_beat: int
    bar_count: float

    bpm: float | None
    camelot: str | None
    energy_start: float | None
    energy_end: float | None
    energy_mean: float | None
    density: float | None
    brightness: float | None
    sub_weight: float | None

    semantic_vector_ref: str | None
    timbre_vector_ref: str | None
    tags: tuple[str, ...]
```

Notes:

- Store vector refs, not raw vectors, in agent packets.
- Keep low-confidence/unknown sections for offline indexing, but gate them before
  live action.
- `role` is coarse on purpose. Preserve ANLZ raw labels and auto-engine details
  in source metadata, not in the public source enum.

### `TransitionCandidate`

One row per possible move from one section to another:

```python
@dataclass(frozen=True, slots=True)
class TransitionCandidate:
    candidate_id: str

    from_track_id: str
    from_section_id: str
    from_role: str
    from_start_s: float
    from_end_s: float

    to_track_id: str
    to_section_id: str
    to_role: str
    to_start_s: float
    to_end_s: float

    cue_slot: str | None
    start_in_bars: int | None
    phrase_bars: int | None

    semantic_score: float
    harmonic_score: float
    bpm_score: float
    energy_shape_score: float
    role_score: float
    phrase_alignment_score: float
    taste_score: float
    novelty_score: float
    risk_penalty: float

    score: float
    confidence: float
    risk_flags: tuple[str, ...]
    reasons: tuple[str, ...]
```

`candidate_id` must be generated by the deterministic engine and recorded in the
run holder. Export/action tools may only accept candidate IDs from that holder.

### `MusicalContextPacket`

The compact packet the agent sees:

```python
@dataclass(frozen=True, slots=True)
class MusicalContextPacket:
    packet_id: str
    t_session: float
    mode: str  # prep | live

    active_track_id: str | None
    active_track_title: str | None
    active_deck: str | None
    audible_confidence: float

    playhead_s: float | None
    playhead_confidence: float
    current_section_id: str | None
    current_role: str | None
    next_section_id: str | None
    next_role: str | None
    bars_to_next_section: int | None

    key: str | None
    bpm: float | None
    energy_now: float | None
    live_phase: str | None

    transition_slate: tuple[TransitionCandidate, ...]
    suppress_timing_claims: bool
    suppress_recommendations: bool
    uncertainty_reasons: tuple[str, ...]
```

This packet is the bridge between audio/data and language. It is intentionally
small enough to fit into the live prompt without dumping a library.

## Context arrangement for the LLM

The LLM should see five blocks, always in this order:

1. **Rules block**: invariant prompt, citation grammar, "do not invent musical
   facts", product voice.
2. **Current packet**: one `MusicalContextPacket`, already compacted.
3. **Candidate slate**: top 3-5 transition candidates with score breakdowns and
   short reasons.
4. **Taste/context memory**: Kaan preferences and session arc, only if retrieved
   by grounded memory.
5. **Allowed actions**: a schema-constrained menu of what the model may output.

Do not include:

- raw waveform summaries;
- raw embedding vectors;
- hundreds of track candidates;
- ambiguous facts without confidence;
- full ANLZ dumps.

The agent's output should be a constrained object first, natural language second.

## Agent output contract

For live pill:

```python
@dataclass(frozen=True, slots=True)
class PillDecision:
    decision_id: str
    action: str  # suggest_next | hold | ask | suppress
    candidate_id: str | None
    urgency: str  # now | soon | later | none
    text: str
    citations: tuple[str, ...]
    confidence: float
    suppressed_reasons: tuple[str, ...]
```

Examples:

```json
{
  "action": "suggest_next",
  "candidate_id": "tr_001",
  "urgency": "soon",
  "text": "Bring MA_Warhead from cue B in 16 bars; its intro groove matches the outgoing drop tail and the key move is safe.",
  "citations": ["track:rb-123", "track:rb-456", "mix:audible_deck"],
  "confidence": 0.78,
  "suppressed_reasons": []
}
```

If timing is weak:

```json
{
  "action": "suggest_next",
  "candidate_id": "tr_001",
  "urgency": "later",
  "text": "Next good entry: cue B on MA_Warhead. Timing is not locked, so use it as a prep suggestion.",
  "citations": ["track:rb-123", "track:rb-456"],
  "confidence": 0.62,
  "suppressed_reasons": ["playhead_confidence_below_live_timing_floor"]
}
```

If slate is weak:

```json
{
  "action": "hold",
  "candidate_id": null,
  "urgency": "none",
  "text": "",
  "citations": [],
  "confidence": 0.0,
  "suppressed_reasons": ["no_candidate_above_threshold"]
}
```

Silence is a valid product behavior. Wrong confidence is worse than no pill.

## Grounding rules

### Tool grounding

Extend the current `LibraryToolset` pattern:

- `search_vibe` / `discover_pool` ground track IDs in `seen`.
- `get_track_sections` may only return sections for known library tracks.
- `search_sections` adds returned `section_id`s to `seen_sections`.
- `transition_slate` may only create candidates from seen tracks/sections, or
  from the current live track resolved by `MusicState`.
- `export_smart_cues` may only export cue slots derived from seen sections or
  issued transition candidates.
- `accept_transition` / future live action tools may only accept candidate IDs
  that the engine issued in this run.

Proposed per-run holders:

```python
seen: set[str]  # existing track ID holder
seen_sections: dict[str, SectionIntelligence]
issued_transition_candidates: dict[str, TransitionCandidate]
issued_cue_proposals: dict[str, SmartCueProposal]
issued_context_packets: dict[str, MusicalContextPacket]
```

### EvidenceRegistry extension

Do not casually add citation sources. `EvidenceRegistry` has schema mirrors in
the regex, prompt matrix, and citation linter. If we add sources, land them as a
single locked change.

Future sources worth adding:

```text
section:<section_id>      # section exists in TrackIntelligence
cue:<track_id>:<slot>     # cue exported or proposed
trans:<candidate_id>      # candidate issued by transition_slate
packet:<packet_id>        # context packet issued for a live decision
```

Until then, live text can cite existing `track`, `mix`, `key`, `aud`, and `midi`
sources, while internal tool validation handles `section_id`/`candidate_id`.

### Claim policy

Agent may say:

- a track title/artist only if surfaced by library lookup;
- a key only if deterministic harmonic resolver supplied it;
- a BPM only if library/ANLZ/audio source supplied it with confidence;
- "in N bars" only if playhead confidence passes the live timing floor;
- "cue B" only if cue mapping exists and was generated/exported or proposed;
- "matches" only if a score component supports it.

Agent must not say:

- "drop" / "breakdown" as fact for low-confidence sections;
- exact timing during blends or weak playhead;
- "perfect mix" or other absolute language;
- facts from raw model musical intuition;
- a track/cue not present in the current grounded slate.

## Transition scoring

Initial deterministic score:

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

Suggested floors:

```text
prep_candidate_floor: 0.52
live_candidate_floor: 0.62
live_timing_floor:    0.70 playhead confidence
export_cue_floor:     0.60 section confidence
```

Risk flags:

```text
bpm_delta_large
harmonic_clash
energy_drop_unintended
section_label_low_confidence
phrase_length_awkward
playhead_uncertain
blend_window_active
candidate_recently_played
same_artist_cluster
missing_audio_features
```

The agent may prefer a lower raw score only when it names the tradeoff using
available components, e.g. "riskier harmony but better energy lift."

## Section search and transition tools

Add these tools after INTEL-01 lands:

### `get_track_sections`

Input:

```json
{"track_id": "rb-123"}
```

Output:

```json
{
      "track_id": "rb-123",
      "sections": [
        {
      "section_id": "rb-123#s007",
      "role": "drop",
      "start_s": 91.2,
      "end_s": 132.8,
      "bar_count": 32,
      "confidence": 0.80,
      "source": "anlz"
    }
  ]
}
```

### `search_sections`

Input:

```json
{
  "query": "dark hardtechno rolling intro",
  "role": "intro",
  "bpm_min": 160,
  "bpm_max": 180,
  "k": 20
}
```

Output sections, not tracks. This is how the agent stops thinking in whole
songs when the task is a transition.

### `transition_slate`

Input:

```json
{
  "from_track_id": "rb-123",
  "from_section_id": "rb-123#s014",
  "candidate_section_ids": ["rb-456#s001", "rb-789#s002"],
  "k": 5,
  "mode": "live"
}
```

Output:

```json
{
  "candidates": [
    {
      "candidate_id": "tr_001",
      "to_track_id": "rb-456",
      "to_section_id": "rb-456#s001",
      "cue_slot": "B",
      "start_in_bars": 16,
      "score": 0.74,
      "confidence": 0.78,
      "reasons": [
        "harmonic fit 8A -> 9A",
        "intro energy matches current outro tail",
        "32-bar phrase alignment"
      ],
      "risk_flags": []
    }
  ]
}
```

### `explain_transition`

Takes a `candidate_id` from an issued slate and returns a more detailed
breakdown. This keeps the live packet compact but lets chat dig in.

### `export_smart_cues`

Exports a validated cue map to Rekordbox XML. Never writes `master.db`.

Input must be track IDs or candidate IDs already grounded in the run.

## Smart hot cue policy

INTEL-18 is the canonical smart-cue policy. This section keeps the compact
agent-facing summary.

Default cue slots:

```text
A = first mixable intro/downbeat
B = first stable groove/build entry
C = breakdown/tension reset
D = main drop/chorus landing
E = second drop or late high-energy landing
F = mix-out/outro
G = loop-safe utility anchor
H = rescue/alternate entry
```

Precedence:

```text
DJ-authored hot cue
  -> DJ-authored memory cue
  -> ANLZ high-confidence phrase
  -> CUE-DETR / ML cue
  -> DSP fallback
  -> no cue
```

Do not overwrite DJ cues by default. Generate a review/export XML layer first.

Important implementation note from INTEL-18: `export_smart_cues` must preserve
the requested A-H slot numbers. The older generic cue exporter sorts cues by
timeline, which is fine for plain `CueAnchor` export but wrong for policy slots.

## Live context and degradation

Live suggestion quality depends on playhead confidence:

```text
>= 0.80  may say exact bars and cue timing
0.70-0.79 may say "soon" and rounded bars
0.50-0.69 may suggest next track/cue without timing
< 0.50  suppress timing and maybe suppress pill entirely
```

Blend window:

- if two decks are audibly mixed or crossfader/level evidence indicates a blend,
  suppress exact playhead claims for 10-15 seconds unless direct transport is
  available;
- keep prep suggestion visible if the candidate is still useful;
- do not re-anchor during the noisiest blend unless confidence recovers.

## Agentic loops

### Prep loop

Use case:

```text
"Build me a 90-minute dark rolling hardtechno set and cue it."
```

Flow:

```text
search_vibe / discover_pool
  -> get_track_sections
  -> section vector candidate expansion
  -> transition_slate beam search
  -> sequence_set with section transitions
  -> export_set + export_smart_cues
```

Agent may ask taste questions, but all writes go through grounded export tools.

### Live pill loop

Flow:

```text
MusicState snapshot
  -> resolve active track
  -> resolve current/next section using playhead + ANLZ
  -> generate transition slate from current section and prepared pool/library
  -> agent chooses/suppresses
  -> ws frame carries PillDecision
```

`MusicState` remains single-writer. The suggestion service owns derived state.

### Chat loop

Use case:

```text
"Why this next?"
"Give me something meaner."
"No vocals."
"Keep the energy but get weirder."
```

The chat agent should update constraints/taste and request a fresh deterministic
slate. It should not free-form invent alternatives outside the tool results.

## Evaluation plan

### Offline metrics

Compare new section-aware engine against current track-level baseline:

- top-k semantic relevance for section search;
- harmonic/BPM compatibility distribution;
- risk flag precision on known bad transitions;
- diversity vs repetition in generated sets;
- cue placement coverage and confidence distribution.

### DJ-centered metrics

For Kaan's library:

- thumbs-up/down per suggested transition;
- accepted cue slots after review;
- "would play live" transition rate;
- timing trust: exact bar suggestions that felt right;
- suppression trust: moments where silence felt better than guessing.

### Grounding metrics

- unsupported musical claim rate;
- tool rejection rate for invented IDs;
- candidate-ID validation failures;
- timing claims emitted below confidence floor;
- citation linter strips per 100 turns.

### Research benchmark candidates

Use external datasets only for eval/reference, not as product truth:

- DJ mix analysis datasets for phrase/timing regularities;
- Raveform for EDM structural annotations and beat alignment;
- CUE-DETR / All-In-One as fallback baselines for missing ANLZ.

## Build order

### INTEL-02A: section store and query

- Persist `SectionIntelligence` rows from INTEL-01 ANLZ anchors.
- Add section embedding refs.
- Add `get_track_sections` and `search_sections`.
- Tests: ID stability, grounding gates, role filters, low-confidence handling.

### INTEL-02B: transition slate engine

- Implement `TransitionCandidate` scoring.
- Add `transition_slate` and `explain_transition`.
- Add deterministic score breakdowns and risk flags.
- Tests: harmonic/BPM/role scoring, candidate floors, invented candidate reject.

### INTEL-02C: agent context packet

- Build `MusicalContextPacket` renderer for prep and live modes.
- Keep packet compact and explicit about uncertainty.
- Add prompt/tool contract tests so the agent only selects issued candidates.

### INTEL-02D: pill policy

- Replace current track-level pill payload with `PillDecision`.
- Preserve honest `None`/hold behavior.
- Gate timing by playhead confidence.

### INTEL-02E: smart cue export

- Generate cue maps from sections.
- Export Rekordbox XML.
- Never mutate Rekordbox databases.

## Non-goals

- No process-memory Rekordbox reading.
- No screen vision.
- No direct `master.db` writes.
- No LLM-generated keys/BPM/sections.
- No raw-audio dumping into the prompt as the primary intelligence source.
- No broad dependency swap to MERT/MuQ/T-CLAP until an eval harness proves value.

## Success definition

The feature is successful when vibemix can say, with grounded confidence:

```text
"Start Track B from cue B in 16 bars. It is harmonically safe, its intro section
matches the current outro texture, and the drop will land after one phrase."
```

and every part of that sentence can be traced back to a real local object:

- track IDs from the library;
- cue/section IDs from ANLZ/DJ/ML sources;
- BPM/key from deterministic analyzers;
- timing from live playhead confidence;
- score reasons from the transition engine.

That is the intelligence leap.
