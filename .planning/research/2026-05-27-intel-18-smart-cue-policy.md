# INTEL-18: smart hot cue policy

**Date:** 2026-05-27
**Lane:** intelligence / DJ preparation / cue proposals / set-aware mix points
**Depends on:** INTEL-01 through INTEL-17
**Status:** implementation-ready policy for cue proposals, export, and review
**Code posture:** first policy slice implemented in
`src/vibemix/library/smart_cues.py` with focused tests. It produces review-first
`SmartCueProposal`s and slot-preserving `export_set` cue marks. Grounded
`smart_hot_cues`/`export_smart_cues` issuance/export is wired through
`LibraryToolset` and MCP. INTEL-19 baseline comparison has a first executable
eval slice for Rekordbox XML snapshots versus vibemix proposals.

## Goal

Turn grounded track structure into cue maps that a DJ would actually trust.

The product should not merely drop markers at section boundaries. It should
produce a stable, opinionated A-H cue layout with provenance, confidence,
review status, and set-aware usefulness:

```text
ANLZ/DJ/ML sections -> candidate cue moments -> A-H slot assignment
  -> reviewable SmartCueProposal -> Rekordbox XML export
  -> transition_slate can use cue operability
```

This is the policy layer between INTEL-01 section extraction and INTEL-12
grounded tools. It answers:

- what each cue slot means;
- when a section deserves a slot;
- when the system must suppress or review instead of export;
- how to preserve human cues;
- how smart cues become transition-aware instead of isolated track prep.

## Reality check: Rekordbox already has an auto-cue baseline

This matters because the product bar is higher than "automatic hot cues exist."
Rekordbox 7 includes Intelligent Cue Creation:

- Rekordbox's overview says it can automatically set Hot Cues and Memory Cues
  and learn the user's cue point preferences from tracks with cue settings.
- The 7.2.14 manual says CUE Analysis can set Hot Cues or memory cues, supports
  up to 16 Hot Cues and 10 memory cues, and has Auto and Manual modes.
- Rekordbox's FAQ says CUE(auto) uses phrase analysis information and can be
  improved with a personal CUE trend built from a CUE Analysis Playlist; it also
  warns about overwrite behavior and short/unanalysable tracks.

Implication:

```text
vibemix cannot win by cloning "auto cue my tracks."
vibemix wins by making cues set-aware, explainable, provenance-tracked,
reviewable, export-safe, and connected to the next-track suggestion engine.
```

The built-in Rekordbox feature is likely a strong per-track baseline. Our
advantage is the surrounding intelligence:

- section embeddings;
- transition scoring;
- taste feedback;
- agent-grounded explanations;
- run-scoped proposal IDs and safe actions;
- no blind overwrite of the DJ's library.

## External anchors

- Rekordbox 7 overview, Intelligent Cue Creation:
  https://rekordbox.com/en/feature/overview/
- Rekordbox 7.2.14 manual, Intelligent Cue Creation and Hot Cue behavior:
  https://cdn.rekordbox.com/files/20260409151936/rekordbox7.214_manual_EN.pdf
- Rekordbox operation FAQ, CUE(auto) phrase analysis and overwrite caveats:
  https://rekordbox.com/en/support/faq/operation-hints-7/
- Rekordbox XML format list, `POSITION_MARK` `Type` and `Num` semantics:
  https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf
- pyrekordbox XML docs:
  https://pyrekordbox.readthedocs.io/en/latest/formats/xml.html
- pyrekordbox ANLZ docs:
  https://pyrekordbox.readthedocs.io/en/stable/generated/pyrekordbox.anlz.html

## Existing repo anchors

Current code already provides the export and cue seams:

- `src/vibemix/library/cue_types.py`
  - `CueAnchor(label, start_s, end_s, confidence, source)`
  - current `CueSource = "dj" | "auto"`; INTEL-01 adds `"anlz"`.
- `src/vibemix/library/cue_export.py`
  - exports `CueAnchor`s to a fresh Rekordbox XML file;
  - point hot cues, not loops;
  - sorted by timeline and assigned `Num=0,1,2...`;
  - colored by coarse label;
  - non-destructive, no `master.db` writes.
- `src/vibemix/library/export_rekordbox.py`
  - supports `POSITION_MARK` cue/loop export with `num=-1` memory cue and
    `num=0..7` hot cue slots A-H.
- INTEL-01
  - ANLZ PSSI and PQTZ provide offline structure and beat-to-time maps.
- INTEL-07
  - defines canonical section roles and the first rough A-H cue semantics.
- INTEL-12/13
  - define issued cue proposal IDs and action grounding.

## Product stance

Smart cueing has two layers:

```text
Layer 1: per-track cue map
  "For this track, A is the safest mix-in, D is the main drop, F is the exit."

Layer 2: set-aware cue use
  "For this transition, exit track A at F and enter track B at A/B/D."
```

Layer 1 is useful immediately. Layer 2 is the app's moat. Cue slots should be
chosen so transition_slate can reason about them later.

## Non-goals

- Do not mutate `master.db`.
- Do not read Rekordbox process memory.
- Do not overwrite DJ-authored cues by default.
- Do not send raw audio, raw local paths, raw vectors, or raw ANLZ dumps to an
  LLM.
- Do not ask the LLM to invent cue positions.
- Do not export low-confidence cue maps as if they are truth.
- Do not require live playhead confidence for prep-mode cue generation.
- Do not depend on Rekordbox 7 Intelligent Cue Creation. Treat it as a baseline,
  not a required integration.

## Vocabulary

### Cue slot

A visible hot-cue pad slot, normally A-H:

```text
A -> Num 0
B -> Num 1
C -> Num 2
D -> Num 3
E -> Num 4
F -> Num 5
G -> Num 6
H -> Num 7
```

Rekordbox can support more cues in some modes, but v1 uses A-H because:

- the current export path and most controller workflows are naturally eight-pad;
- muscle memory matters;
- more slots increase review cost;
- A-H is enough for the first set-aware transition policy.

Future I-P support should be a second page, not a change to A-H meanings.

### Cue role

The DJ function a slot serves. This is not identical to a section role. A drop
section can produce a `main_drop` cue role; an intro or groove section can
produce a `mix_in` role.

Canonical cue roles:

```text
mix_in
early_groove
breakdown
main_drop
secondary_drop
mix_out
loop_utility
rescue_or_alt
```

### Cue proposal

A reviewable set of slot assignments for one track:

```text
proposal_id = "cueprop_001"
cue_id = "cueprop_001:A"
```

The model may reference proposal and cue IDs, but never authors raw cue payloads.

## Canonical A-H policy

| Slot | Role | Meaning | Required? |
|------|------|---------|-----------|
| A | `mix_in` | first safe mixable downbeat or stable entry | yes |
| B | `early_groove` | first stable groove/build/body section after A | preferred |
| C | `breakdown` | energy reset, bass drop-out, or tension break | optional |
| D | `main_drop` | primary high-impact landing | yes for dance tracks |
| E | `secondary_drop` | second drop, late peak, or alternate impact point | optional |
| F | `mix_out` | clean exit, outro, or late phraseable tail | yes |
| G | `loop_utility` | loop-safe hold, tool section, or phraseable rescue loop | optional |
| H | `rescue_or_alt` | alternate entry, emergency jump, or genre-specific extra | optional |

Required does not mean "invent it." It means: if the track has a credible
candidate, the proposal should try to fill this slot first. Missing required
slots are reported as `missing`, not fabricated.

## Source priority

Cue candidates may come from multiple sources. Preserve all provenance, then
rank by trust:

```text
DJ-authored hot cue
  -> DJ-authored memory cue
  -> ANLZ high-confidence phrase
  -> CUE-DETR / future ML section model
  -> DSP fallback
  -> no cue
```

Rules:

- DJ-authored cue positions are authoritative.
- DJ-authored cue labels are hints, not guaranteed semantics.
- ANLZ PSSI is primary auto structure for Kaan's library.
- CUE-DETR/DSP is fallback when ANLZ is missing or low confidence.
- A cue with no grounded source is invalid.
- A wrong cue is worse than a missing cue.

## SmartCueProposal contract

Implementation target:

```python
@dataclass(frozen=True, slots=True)
class SmartCue:
    cue_id: str
    track_id: str
    slot: Literal["A", "B", "C", "D", "E", "F", "G", "H"]
    role: SmartCueRole
    start_s: float
    start_beat: int | None
    end_s: float | None
    source: Literal["dj", "anlz", "auto", "fallback"]
    source_detail: str
    source_section_id: str | None
    confidence: float
    review_status: Literal["export_ready", "review", "suppressed", "missing"]
    export_label: str
    reason_codes: tuple[str, ...]
    provenance_ref: str

@dataclass(frozen=True, slots=True)
class SmartCueProposal:
    proposal_id: str
    track_id: str
    policy_version: str
    cues: tuple[SmartCue, ...]
    missing_slots: tuple[str, ...]
    suppressed_candidates: tuple[SuppressedCueCandidate, ...]
    summary: SmartCueProposalSummary
```

`CueAnchor` remains the compatibility/export primitive. `SmartCue` is the richer
policy object used before export. The export adapter converts selected
`SmartCue`s into point `CueAnchor`s or direct `POSITION_MARK` payloads.

## Slot assignment pipeline

### 1. Build candidate moments

Candidate inputs:

- DJ cue points from Rekordbox XML/imported library;
- ANLZ PSSI phrases with beat-to-time from PQTZ;
- auto-cue fallback `CueAnchor`s;
- future section records from INTEL-10.

For every candidate, compute:

```text
track-relative seconds
beat index / bar index when known
section role
raw source label
source confidence
duration in bars
distance from previous/next boundary
energy at/after boundary when available
density/sub/brightness/harmonic confidence when available
```

### 2. Normalize to cue-role evidence

Map section roles to slot-role evidence:

| Section role | Candidate cue roles |
|--------------|---------------------|
| intro | `mix_in`, `rescue_or_alt` |
| groove | `early_groove`, `mix_in`, `loop_utility` |
| build | `early_groove`, `main_drop` if boundary lands into drop |
| breakdown | `breakdown`, `rescue_or_alt` |
| drop | `main_drop`, `secondary_drop`, `rescue_or_alt` |
| outro | `mix_out`, `loop_utility` |
| bridge | `breakdown`, `loop_utility`, `rescue_or_alt` |
| unknown | review-only boundary evidence |

Important nuance:

- A build section's **start** is usually B; the **next boundary** into a drop is
  usually D.
- An outro section's start may be F, but if the useful mix-out point is 16 or 32
  bars before the final end, candidate generation should include a back-timed
  phraseable point when the beatgrid supports it.
- A loop utility cue should not be created just because a section exists. It
  needs stable density and enough bars to loop safely.

### 3. Apply hard gates

Reject or suppress a candidate before scoring when:

- no grounded source;
- no valid `start_s`;
- `start_s` is outside track duration;
- source-track match is ambiguous;
- source confidence below `0.45`;
- cue is closer than 4 bars to another stronger cue unless it is a DJ-authored
  cue;
- phrase duration is under 4 bars for A/B/F/G;
- track is shorter than the minimum useful prep threshold;
- candidate is inside a transition-blend uncertainty window in live mode;
- export would overwrite an existing DJ-authored hot cue slot without explicit
  user approval.

Suppressed candidates are still useful for debugging and review, but not for
export.

### 4. Score slot fitness

Score each candidate for each slot:

```text
slot_fit =
    0.30 * role_match
  + 0.18 * source_confidence
  + 0.12 * downbeat_snap
  + 0.10 * phrase_length_fit
  + 0.10 * operability
  + 0.08 * energy_shape_fit
  + 0.07 * genre_policy_fit
  + 0.05 * spacing_fit
```

Definitions:

- `role_match`: ontology role fits slot semantics.
- `source_confidence`: DJ/ANLZ/ML/DSP trust after calibration.
- `downbeat_snap`: beatgrid says the cue lands on a strong beat/bar.
- `phrase_length_fit`: enough bars before/after for the role.
- `operability`: practical DJ action is plausible.
- `energy_shape_fit`: drop rises, breakdown resets, outro drains, etc.
- `genre_policy_fit`: genre-specific priority.
- `spacing_fit`: avoids duplicate pads.

All components must be finite and in `[0, 1]`.

### 5. Assign slots deterministically

Assignment order:

```text
1. Preserve occupied DJ hot-cue slots.
2. Fill A, D, F if credible.
3. Fill B.
4. Fill C and E.
5. Fill G and H.
6. Sort final export by slot, not by timeline, when using direct slot export.
```

Conflict rules:

- A candidate may occupy only one slot.
- If two slots want the same candidate, higher-priority slot wins.
- If a DJ cue already occupies a slot, the proposal either preserves it or
  creates a shadow suggestion for review. It does not overwrite.
- If no unoccupied slot is available, suppress the lowest-value optional cue.
- If time order and slot order disagree, keep slot semantics. The DJ's hands
  care more about pad meaning than strict timeline order.

This requires updating the current `cue_export.export_cues` behavior or adding
a policy-specific export path, because current export sorts by `start_s` and
assigns slots sequentially. Smart-cue export must preserve requested A-H slots.

## Export policy

Default export mode:

```text
review XML layer, never direct library mutation
```

Export labels:

| Slot | Label |
|------|-------|
| A | `VM A IN` |
| B | `VM B GROOVE` |
| C | `VM C BREAK` |
| D | `VM D DROP` |
| E | `VM E DROP2` |
| F | `VM F OUT` |
| G | `VM G LOOP` |
| H | `VM H ALT` |

Rules:

- Prefix labels with `VM` so imported cues are identifiable.
- Preserve human labels when exporting existing DJ-authored cues.
- Use point hot cues by default.
- Export loops only when a future explicit loop proposal exists.
- Keep memory cues separate from hot cues unless the user explicitly asks for
  memory-cue export.
- Do not export hidden local paths to the model; path resolution happens inside
  the tool.
- Revalidate track IDs against the library at export time.

## Review status thresholds

Suggested initial thresholds:

| Status | Condition |
|--------|-----------|
| `export_ready` | confidence >= 0.78 and no hard risk |
| `review` | 0.55 <= confidence < 0.78 or mild risk |
| `suppressed` | confidence < 0.55, hard gate, duplicate, or overwrite risk |
| `missing` | no credible candidate for required slot |

Default product behavior:

```text
prep chat may show export_ready + review cues;
autonomous export only exports export_ready cues unless the user selected review cues;
live pill may mention only export_ready/currently issued cue IDs.
```

This can loosen only through INTEL-03/15 evaluation evidence.

## Genre policies

### Techno / hardtechno / hardtek

Priorities:

```text
A, B, F, D, G, C, E, H
```

Interpretation:

- B and F are often more valuable than D because long blends and tool sections
  matter.
- D should be the strongest landing, not every chorus-like boundary.
- G is valuable when a stable percussive loop can hold pressure.
- Harmonic uncertainty matters less for percussive sections.

### House / disco

Priorities:

```text
A, F, D, C, B, E, G, H
```

Interpretation:

- A/F mix windows and harmonic compatibility are high value.
- Vocal or hook overlap is a risk.
- Breakdown cue C is useful for phrase-aware reset transitions.

### Drum and bass

Priorities:

```text
A, D, C, E, F, B, G, H
```

Interpretation:

- D/E support drop and double-drop preparation.
- Exact bar/downbeat placement matters more.
- F remains useful but some transitions happen before classical outro.

### Pop / vocal / open format

Priorities:

```text
A, D, C, H, F, B, E, G
```

Interpretation:

- Hooks and vocal boundaries matter more than long mix windows.
- Cue labels should avoid overclaiming "drop" when the structure is chorus/hook.
- H can be a chorus/clean-entry alternate.

### Unknown genre

Priorities:

```text
A, D, F, C, B, E, G, H
```

Use conservative confidence and review more cues.

## Set-aware use

Smart cues become powerful when transition_slate scores them as operable
handles.

For every transition candidate, compute:

```text
from_operable_slot: F | C | D tail | G | None
to_operable_slot: A | B | D | H | None
cue_operability_score
bars_from_current_playhead_to_from_slot
bars_from_to_slot_to_target_landing
```

Examples:

- Outgoing `F` -> incoming `A`: clean blend.
- Outgoing `C` -> incoming `D`: reset into impact.
- Outgoing `D tail` -> incoming `B`: sustain energy without stacking drops.
- Outgoing `G loop` -> incoming `A/B`: hold pressure while searching.

The live pill should prefer candidates with usable cue slots. A candidate with
great semantic similarity but no practical cue handle should rank lower in live
mode than in prep mode.

## Agent behavior

The agent may say:

- "I found an export-ready A/B/D/F map for this track."
- "D is the main drop because ANLZ marked a high-confidence chorus/drop boundary
  on a downbeat."
- "C is review-only because the source was mid-mood bridge and the confidence is
  low."
- "I preserved your existing hot cue B and proposed a shadow alternative."

The agent must not say:

- exact bars unless beatgrid/provenance supports it;
- "Rekordbox says" unless the source is actually ANLZ/Rekordbox-derived;
- "best drop" when the candidate is just the first high-energy point;
- "exported" unless `export_smart_cues` succeeded;
- "overwrote" unless the user explicitly approved overwrite and the export path
  actually supports it.

## Data excellence and evaluation

INTEL-19 defines and now implements the first baseline comparison harness for
this policy. The minimum claim is not "vibemix generated cues"; it is "vibemix
matched or beat the relevant baseline on reviewed usefulness or transition
utility."

Gold labels from INTEL-15 should include cue-specific review actions:

```json
{
  "review_item_type": "smart_cue_proposal",
  "track_id": "track_001",
  "proposal_id": "cueprop_001",
  "slot_reviews": [
    {
      "slot": "D",
      "action": "keep",
      "moved_to_s": null,
      "reason": "main drop landed correctly"
    }
  ]
}
```

Metrics:

- slot keep rate;
- slot maybe/review rate;
- delete rate;
- move distance in beats;
- role confusion matrix;
- overwrite attempts, target zero;
- XML import success;
- transition_slate lift when cue operability is included;
- per-genre cue acceptance;
- per-source acceptance: DJ, ANLZ, ML, DSP;
- confidence calibration: export_ready cues should be kept much more often than
  review cues.

Minimum local gate before enabling broad export:

```text
20-track manual review
>= 70% keep/maybe across A, D, F
0 accidental overwrite risks
0 invalid XML exports
all missing required slots explained
```

Better gate before live pill cue recommendations:

```text
50-track review
>= 80% keep/maybe for A/F in techno/hardtechno
>= 75% keep/maybe for D in high-mood ANLZ tracks
< 10% large move rate (>8 bars)
cue_operability improves transition review score in INTEL-03C
```

## Failure taxonomy

Record these reason codes:

```text
no_structure
ambiguous_track_match
low_source_confidence
missing_required_role
too_short_phrase
off_downbeat
duplicate_near_existing
human_slot_occupied
would_overwrite_human_cue
genre_policy_low_fit
energy_shape_mismatch
vocal_overlap_risk
outro_too_empty
drop_too_early
loop_not_stable
exporter_slot_limit
xml_export_failed
```

Reason codes feed explanations, scorecards, and debugging. They should be
structured data, not prose.

## Implementation handoff

Add:

```text
src/vibemix/library/smart_cues.py
tests/library/test_smart_cues.py
scripts/eval/intel_smart_cue_scorecard.py
```

Current partial implementation:

```text
done: src/vibemix/library/smart_cues.py
done: tests/library/test_smart_cues.py
done: propose_smart_cues(track, sections, ...)
done: smart_cue_to_anchor(cue)
done: proposal_to_export_marks(proposal, include_review=False, include_preserved=False)
done: export marks round-trip through export_set with explicit A-H nums
done: smart_hot_cues issues proposal/cue IDs for grounded tracks
done: export_smart_cues rejects raw cue payloads and exports only issued cue IDs
pending: scripts/eval/intel_smart_cue_scorecard.py
```

Likely public functions:

```python
def propose_smart_cues(
    track: TrackEntry,
    sections: Sequence[SectionRecord],
    *,
    genre: str | None = None,
    existing_cues: Sequence[CuePoint] = (),
    policy: SmartCuePolicy | None = None,
) -> SmartCueProposal: ...

def smart_cue_to_anchor(cue: SmartCue) -> CueAnchor: ...

def proposal_to_export_marks(proposal: SmartCueProposal) -> list[dict[str, Any]]: ...
```

Exporter implication:

- `cue_export.export_cues` is fine for simple timeline-sorted `CueAnchor`s.
- `export_smart_cues` needs slot-preserving export, because A-H semantics are
  policy, not timeline order.
- It may use `export_rekordbox._add_cues`-style payloads with explicit `num`.

## Test plan

Pure unit tests:

- `test_preserves_existing_human_hot_cue_slot`
- `test_missing_required_slot_is_reported_not_fabricated`
- `test_fills_a_d_f_from_high_mood_anlz_sections`
- `test_mid_mood_bridge_to_c_is_review_not_export_ready`
- `test_duplicate_candidates_are_merged`
- `test_confidence_thresholds_assign_review_status`
- `test_genre_policy_prioritizes_b_and_f_for_techno`
- `test_export_marks_preserve_slot_nums`
- `test_proposal_ids_and_cue_ids_are_stable_within_run`
- `test_no_candidate_without_grounded_source`

Tool tests:

- `test_smart_hot_cues_requires_seen_track`
- `test_smart_hot_cues_records_issued_proposal`
- `test_export_smart_cues_rejects_unissued_proposal`
- `test_export_smart_cues_rejects_cue_id_outside_proposal`
- `test_export_smart_cues_revalidates_track_at_write_time`
- `test_export_smart_cues_never_accepts_raw_model_payload`

Eval tests:

- scorecard loads private review JSONL;
- missing labels do not count as failures;
- confidence bins are reported;
- source/genre breakdowns are reported;
- thresholds are versioned.

## Open questions

1. Should v1 export only A-H, or optionally use I-P when Rekordbox/controller
   support is detected?
2. Should `G` create point hot cues only, or should it produce explicit loop
   proposals once loop stability exists?
3. Should built-in Rekordbox Intelligent Cue Creation output be imported as
   `source="dj"` or a separate `source_detail="rekordbox_auto_cue"` when we can
   detect it?
4. Should the default review UI show suppressed candidates, or only the final
   proposal plus reason counts?
5. Does Kaan prefer A/B/F-first for hardtechno prep, or D-first because he uses
   pads as jump points more than mix handles?

## Success definition

INTEL-18 is ready to implement when a builder can answer, for every proposed cue:

```text
Which slot is this?
What DJ action does that slot support?
Which grounded source produced it?
Why was it assigned over nearby candidates?
Can it be exported without overwriting a human cue?
How will we know later whether Kaan kept, moved, or deleted it?
How does this cue help transition_slate pick the next track?
```

That is the difference between "markers that exist" and musical intelligence a
DJ can lean on.
