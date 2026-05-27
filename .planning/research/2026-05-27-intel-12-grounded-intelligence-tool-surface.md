# INTEL-12: grounded intelligence tool and action surface

**Date:** 2026-05-27
**Lane:** agentic engine / tool grounding / smart-cue and transition actions
**Depends on:** INTEL-01 through INTEL-11
**Status:** partially implemented; `smart_hot_cues` and `export_smart_cues` now
live in `LibraryToolset`/MCP with run-scoped proposal grounding. `search_sections`
and `explain_transition` remain future cuts.

## Why this exists

The current agent tool system has the right safety pattern:

```text
search_vibe / discover_pool
  -> records real track_ids in this run's seen set
sequence_set / export_set / create_playlist / quote_moment
  -> reject track_ids not seen in this run
```

That pattern is the app's anti-invention contract. The new intelligence engine
must extend the same idea to musical objects below the track level:

```text
track_ids -> section_ids -> transition_candidate_ids -> cue_proposal_ids
```

The model should never be able to invent a section, transition, or cue export
payload. It should only operate on objects the deterministic engine issued in
the current run.

INTEL-20 consumes these issued objects at runtime. This file defines the tool
surface; INTEL-20 defines when deterministic or model-assisted decisions may use
that surface and how unsafe output degrades.
INTEL-21 adds the claim layer over the same issued objects, so explanations can
be validated as facts, not just prose.

## Current tool surfaces

### Shared core

`src/vibemix/library/toolset.py`

- `LibraryToolset` is the single grounded implementation.
- `self.seen` stores track IDs surfaced by discovery.
- `dispatch()` hard-times every handler.
- Handlers return error dicts instead of raising.

### MCP server

`src/vibemix/library/mcp_server.py`

- exposes the same `LibraryToolset` over FastMCP.
- one STDIO server per Codex run means one `seen` lifetime per run.
- no prompt/persona lives in MCP; grounding lives at the tool boundary.

### Removed Gemini legacy harness

The removed Gemini library harness is not a product path. Do not add new tool
declarations there. Future intelligence tools should land in
`LibraryToolset`, the MCP server, and the Codex-backed prompt/output schema.

### Codex harness

`src/vibemix/library/codex_curate.py`

- uses strict output schema for final JSON.
- uses the same MCP tools and post-run revalidation.

## Core principle

Every autonomous action must be issued-object based.

Bad:

```text
model sends arbitrary track_path + arbitrary cue JSON to export_cues
```

Good:

```text
model calls smart_hot_cues(track_id)
  -> tool returns cue_proposal_id and cue IDs
model calls export_smart_cues(cue_proposal_id, selected_cue_ids)
  -> tool validates proposal exists and cue IDs came from it
```

The LLM may ask for candidates, select among candidates, and explain candidates.
It may not author the final action payload from scratch.

## Run-scoped grounding holder

Extend `LibraryToolset` later with more run-scoped holders:

```python
class LibraryToolset:
    seen: set[str]                         # existing track IDs
    seen_sections: dict[str, SectionRecord]
    issued_transition_candidates: dict[str, TransitionCandidate]
    issued_cue_proposals: dict[str, SmartCueProposal]
    issued_context_packets: dict[str, AgentContextEnvelope]
```

Rules:

- one toolset instance == one run;
- no holder is shared across users or runs;
- action tools only accept IDs from the relevant holder;
- holders store deterministic objects, not model prose;
- holders are bounded with caps to prevent runaway memory.

Suggested caps:

```text
seen track IDs:                   500
seen section IDs:                2000
transition candidates issued:     200
cue proposals issued:             100
context packets issued:            50
```

Evict oldest entries if a cap is exceeded, and return a clear error when an
evicted ID is used.

## Tool taxonomy

### Discovery tools

Discovery tools introduce grounded IDs into a run.

Existing:

- `search_vibe`
- `discover_pool`

New:

- `get_track_sections`
- `search_sections`

Discovery tools may populate:

- `seen`
- `seen_sections`

### Planning tools

Planning tools generate bounded derived objects from grounded IDs.

Existing:

- `sequence_set`

New:

- `transition_slate`
- `smart_hot_cues`
- `compile_musical_context`

Planning tools may populate:

- `issued_transition_candidates`
- `issued_cue_proposals`
- `issued_context_packets`

### Explanation tools

Explanation tools read issued objects and produce deterministic summaries.

New:

- `explain_transition`
- `explain_smart_cues`
- `compare_transition_candidates`

Explanation tools should never introduce new IDs.

### Action tools

Action tools write files, export data, or create durable user-visible output.

Existing:

- `create_playlist`
- `export_set`
- `export_cues`

New:

- `export_smart_cues`
- `export_transition_plan`

Action tools must validate:

- every track ID is in `seen` or comes from an issued candidate/proposal;
- every section/candidate/proposal ID exists in the run holder;
- every write path is generated or inside an approved output directory;
- every library item still resolves in `RekordboxLibrary`;
- no raw model-authored cue payload is trusted as final truth.

## Proposed new tools

### `get_track_sections`

Purpose:

Return deterministic sections for one grounded track.

Input:

```json
{
  "track_id": "t001",
  "include_vectors": false
}
```

Output:

```json
{
  "track_id": "t001",
  "sections": [
    {
      "section_id": "t001#s000",
      "role": "intro",
      "start_s": 0.0,
      "end_s": 32.0,
      "source": "anlz",
      "confidence": 0.86,
      "cue_slot": "A"
    }
  ]
}
```

Grounding:

- `track_id` must be known in the live library;
- in autonomous set-prep mode, require `track_id in seen`;
- returned `section_id`s are added to `seen_sections`;
- never return raw vectors;
- never return local file paths.

Why the mode distinction:

- `get_track_features` today is a deterministic read and does not require
  `seen`, but prompts still tell the model not to invent IDs.
- For new action-oriented section tools, keep the stricter rule by default:
  action flows should start from discovery.

### `search_sections`

Purpose:

Find specific entry/mix-out/drop/breakdown sections, not whole tracks.

Input:

```json
{
  "query": "rolling industrial intro groove",
  "role_filter": ["intro", "groove"],
  "candidate_track_ids": ["t001", "t002"],
  "exclude_track_ids": ["t000"],
  "k": 20
}
```

Output:

```json
{
  "sections": [
    {
      "section_id": "t002#s001",
      "track_id": "t002",
      "title": "Example",
      "artist": "Artist",
      "role": "groove",
      "start_s": 32.0,
      "end_s": 96.0,
      "similarity": 0.81,
      "source": "anlz",
      "confidence": 0.78
    }
  ]
}
```

Grounding:

- candidate pool, when supplied, must be subset of `seen`;
- returned track IDs are added to `seen`;
- returned section IDs are added to `seen_sections`;
- role filters must be canonical INTEL-07 roles;
- result count capped.

### `transition_slate`

Purpose:

Generate deterministic section-to-section transition candidates.

Input:

```json
{
  "source_section_id": "t000#s012",
  "candidate_section_ids": ["t002#s001", "t003#s000"],
  "mode": "prep",
  "max_candidates": 8
}
```

Alternative live input:

```json
{
  "current_track_id": "t000",
  "mode": "live",
  "max_candidates": 5
}
```

Output:

```json
{
  "candidates": [
    {
      "candidate_id": "tr_001",
      "from_section_id": "t000#s012",
      "to_section_id": "t002#s001",
      "to_track_id": "t002",
      "cue_slot": "B",
      "score": 0.82,
      "confidence": 0.76,
      "risk_flags": ["tempo_push"],
      "reasons": [
        "section texture is close",
        "Camelot relationship is clean"
      ]
    }
  ]
}
```

Grounding:

- every input section ID must be in `seen_sections`;
- if `current_track_id` live path is used, the live awareness service resolves
  source section; the model does not invent it;
- every output `candidate_id` is stored in `issued_transition_candidates`;
- candidates are aliases over deterministic long IDs;
- action/explanation tools accept only issued candidate IDs.

### `smart_hot_cues`

Purpose:

Generate a reviewable cue proposal for one or more tracks.
The proposal must follow INTEL-18 slot policy and issue cue IDs; the model may
select issued IDs but never raw cue payloads.

Input:

```json
{
  "track_ids": ["t001", "t002"],
  "policy": "standard_8_slot"
}
```

Output:

```json
{
  "proposal_id": "cueprop_001",
  "track_id": "t001",
  "cues": [
    {
      "cue_id": "cueprop_001:A",
      "slot": "A",
      "label": "intro",
      "start_s": 0.0,
      "end_s": 32.0,
      "source": "anlz",
      "confidence": 0.86,
      "review_required": false
    }
  ],
  "warnings": []
}
```

Grounding:

- each `track_id` must be in `seen` unless the user explicitly selected the
  track in UI and the UI passes a trusted local selection context;
- proposal stored in `issued_cue_proposals`;
- `source` must be one of `dj`, `anlz`, `auto`, `fallback`;
- slot/review/export status follows INTEL-18;
- cues are generated by deterministic code, not the model.

### `export_smart_cues`

Purpose:

Write a Rekordbox-importable XML from an issued cue proposal.
Unlike generic `export_cues`, this tool must preserve the proposal's A-H slot
numbers and reject any cue ID outside the issued proposal.

Input:

```json
{
  "proposal_id": "cueprop_001",
  "selected_cue_ids": ["cueprop_001:A", "cueprop_001:B"],
  "out_path": null
}
```

Output:

```json
{
  "exported": true,
  "path": "/Users/.../.cache/vibemix/cues/t001-smart-cues.xml",
  "cue_count": 2,
  "dropped": []
}
```

Grounding:

- `proposal_id` must exist in `issued_cue_proposals`;
- every selected cue ID must belong to that proposal;
- proposal track must still resolve in library;
- output path defaults to app cache;
- arbitrary `track_path` is not accepted from the model.

This should be the preferred smart-cue write path. The existing raw
`export_cues(track_path, cues, ...)` can stay for CLI/manual/debug use, but it
should not be the autonomous agent's smart-cue action surface.

### `explain_transition`

Purpose:

Return deterministic explanation data for one issued candidate.

Input:

```json
{
  "candidate_id": "tr_001"
}
```

Output:

```json
{
  "candidate_id": "tr_001",
  "summary": "Cue B works because the intro groove matches the current outro and the keys are compatible.",
  "facts": [
    "semantic=0.81",
    "harmonic=0.88",
    "bpm=0.78"
  ],
  "risks": ["tempo_push"]
}
```

Grounding:

- candidate must exist in `issued_transition_candidates`;
- explanation only uses stored score components and risk flags;
- no model-written new facts.

### `compile_musical_context`

Purpose:

Build an INTEL-09 `AgentContextEnvelope` from issued objects.

Input:

```json
{
  "intent": "live_next_pill",
  "candidate_ids": ["tr_001", "tr_002"],
  "mode": "live"
}
```

Output:

```json
{
  "packet_id": "ctx_001",
  "schema_version": "intel_context_v1",
  "candidate_count": 2,
  "exact_timing_allowed": false,
  "allowed_actions": ["select", "hold", "suppress"]
}
```

Grounding:

- candidate IDs must be issued;
- packet stored in `issued_context_packets`;
- model decision validator later checks against this packet.

This tool may be internal-only in v1. It does not have to be exposed to Codex if
the app itself compiles packets before calling the model.

## Prompt and schema updates

### Codex/MCP tool exposure

Add the intelligence tools only in set-prep / intelligence modes. Do not expose
them to the simple one-shot playlist curator until tests prove the prompt does
not overuse them.

Suggested declaration groups:

```text
base: search_vibe, get_track_features, create_playlist
set_prep: discover_pool, get_track_energy, sequence_set, export_set
intel_prep: get_track_sections, search_sections, transition_slate,
            smart_hot_cues, explain_transition, export_smart_cues
chat: quote_moment, retrieve_dj_knowledge, web_search, fetch_url,
      plus selected intel tools
```

### MCP tools

Expose the same tools through `mcp_server.py`, backed by the same toolset.

MCP docstrings must say:

- which prior tool grounds the IDs;
- whether the tool introduces IDs;
- whether the tool writes output;
- what is approximate vs exact.

### Codex output schema

Do not let Codex final JSON contain raw cue payloads as an action. Prefer:

```json
{
  "reply": "...",
  "selected_candidate_id": "tr_001",
  "cue_proposal_id": "cueprop_001",
  "export_path": "...",
  "tools_used": [...]
}
```

The actual write must have happened through `export_smart_cues` or `export_set`.

## Action validation matrix

| Tool | Introduces tracks? | Introduces sections? | Introduces candidates? | Writes? | Required grounding |
|------|--------------------|----------------------|------------------------|---------|--------------------|
| `search_vibe` | yes | no | no | no | library/store lookup |
| `discover_pool` | yes | no | no | no | library/store lookup |
| `get_track_sections` | no | yes | no | no | track known; normally `seen` |
| `search_sections` | yes | yes | no | no | section store + library |
| `transition_slate` | no | no | yes | no | seen sections |
| `smart_hot_cues` | no | no | cue proposal | no | seen tracks |
| `explain_transition` | no | no | no | no | issued candidate |
| `compile_musical_context` | no | no | no | no | issued candidates |
| `export_smart_cues` | no | no | no | yes | issued cue proposal |
| `export_set` | no | no | no | yes | seen tracks + library revalidation |
| `create_playlist` | no | no | no | yes | seen tracks + library revalidation |

## Testing plan

### Toolset tests

- `test_get_track_sections_requires_seen_track_in_agent_mode`
- `test_get_track_sections_adds_seen_sections`
- `test_search_sections_adds_seen_track_ids_and_sections`
- `test_transition_slate_rejects_unseen_source_section`
- `test_transition_slate_rejects_unseen_candidate_section`
- `test_transition_slate_records_issued_candidate_ids`
- `test_explain_transition_rejects_unissued_candidate`
- `test_smart_hot_cues_rejects_unseen_track`
- `test_smart_hot_cues_records_proposal`
- `test_export_smart_cues_rejects_unissued_proposal`
- `test_export_smart_cues_rejects_cue_id_outside_proposal`
- `test_export_smart_cues_revalidates_track_against_library`
- `test_export_smart_cues_rejects_raw_model_payload`

### MCP parity tests

- every new MCP tool delegates to the shared toolset;
- MCP docstring mentions grounding requirement;
- no intelligence tool writes without proposal/candidate validation;
- one server instance keeps holder state across tool calls.

### Gemini declaration tests

- base curator declarations unchanged;
- intel tools appear only in `intel_prep`/chat modes;
- tool descriptions forbid invented IDs;
- output schema does not permit raw cue exports.

### Codex tests

- final JSON can reference issued IDs;
- post-run revalidation drops/export-fails ungrounded IDs;
- tool trace records intelligence calls;
- raw cue payload in final JSON is ignored unless an export tool succeeded.

## Rollout order

1. Add run-scoped holder fields to `LibraryToolset`.
2. Add `get_track_sections` over fake/static section records.
3. Add `search_sections` once `SectionStore` exists.
4. Add `transition_slate` using INTEL-11 scorer.
5. Add `smart_hot_cues` using INTEL-01/07 structure and INTEL-18 cue policy. DONE
6. Add `export_smart_cues` proposal-based writer. DONE
7. Expose MCP tools. DONE
8. Add Gemini/Codex declarations only after toolset tests pass.
9. Wire context compiler / validator.

## Security and privacy notes

- Do not expose raw local file paths to the model when a track ID can stand in.
- Do not accept arbitrary output paths unless they are normalized and approved.
- Do not export cues by raw `track_path` in autonomous mode.
- Do not include raw vectors in tool outputs.
- Do not write long-term taste or feedback data from tool calls unless consent
  gates from INTEL-05 are satisfied.

## Recommendation

Treat intelligence objects exactly like tracks:

```text
discovery creates grounded IDs;
planning creates issued IDs;
actions accept only issued IDs;
validators reject everything else.
```

That lets smart hot cueing and set-aware transition suggestions feel agentic
without letting the model author ungrounded music data. It is the same product
philosophy as the existing playlist toolset, extended down to the level where DJ
intelligence actually lives: sections, cues, and transitions.
