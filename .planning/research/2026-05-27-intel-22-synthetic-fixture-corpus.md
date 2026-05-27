# INTEL-22: synthetic intelligence fixture corpus

**Date:** 2026-05-27
**Lane:** data excellence / testability / privacy-safe fixtures / implementation enablement
**Depends on:** INTEL-01 through INTEL-21
**Status:** implemented PR-0 fixture corpus plus audit contract
**Code posture:** product runtime untouched; synthetic fixtures, generator, audit,
and focused tests added

## Goal

Create a public, deterministic fixture corpus that can prove the intelligence
contracts without Kaan's private tracks, local Rekordbox paths, audio files, or
raw CLAP vectors.

The corpus should exercise:

```text
ANLZ-like sections
section vectors
transition scoring
smart cue proposals
context packets
claim ledgers
agent decisions
decision runtime traces
gold-label schemas
baseline cue comparison
privacy/redaction gates
```

This is the implementation bridge between the INTEL specs and real tests.

## Why this exists

The intelligence architecture is now broad enough that every PR needs stable
evidence. Private library probes are necessary for product truth, but they are
bad as committed tests:

- they leak local paths and private track identities;
- they are hard to reproduce in CI;
- they make failures hard for another builder to debug;
- they tempt code to depend on Kaan's local library shape.

The synthetic corpus gives builders a small musical universe where every edge
case is intentional and every expected answer is known.

## Existing scattered fixture mentions

Current docs already mention:

- `tests/library/fixtures/intel_sections.json`
- `tests/library/fixtures/intel_transition_pairs.json`
- `tests/library/fixtures/intel_context_packets.json`
- synthetic cue baseline XML fixtures
- synthetic `SectionRecord` tests
- private `eval/private/intel/*` files

INTEL-22 is the canonical version of that idea.

## Design principles

### Public fixtures are not fake product claims

Synthetic fixtures prove contracts, not musical truth.

They can prove:

- IDs are stable;
- scoring components combine correctly;
- validators reject invented facts;
- privacy scanners catch bad data;
- fallback/degrade behavior is deterministic.

They cannot prove:

- ANLZ quality on Kaan's real library;
- CLAP section embedding quality;
- transition taste;
- live timing accuracy.

Those need private/local evals from INTEL-15/17/19.

### Small but complete

Target size:

```text
8 synthetic tracks
~80 sections
~24 transition candidates
~12 smart cue proposals
~12 context packets
~40 musical claims
~20 model decisions
~10 decision traces
```

Enough to hit every branch, small enough to review by eye.

### Deterministic generation

If fixtures are generated, generation must be deterministic:

```text
seed = "vibemix-intel-fixtures-v1"
```

Generated vectors must be clearly marked as synthetic. They are not CLAP facts.

### No private data by construction

Allowed path forms:

```text
fixture://tracks/fx-hard-001.wav
fixture://rekordbox/fx_collection.xml
```

Forbidden:

```text
/Users/
/Volumes/
file://localhost/
real artist names
private track titles
raw audio
full local XML exports
raw 512D vectors in prompts or context packets
```

## Fixture layout

Recommended committed layout:

```text
tests/intel/fixtures/
  README.md
  dataset_card.json
  tracks.json
  sections.json
  section_vectors_8d.json
  section_vectors_512d.npy
  transition_pairs.json
  transition_slates.json
  smart_cue_proposals.json
  cue_baseline_before.xml
  cue_baseline_after.xml
  context_packets.json
  claim_ledgers.json
  agent_decisions.jsonl
  decision_traces.jsonl
  live_awareness_snapshots.jsonl
  gold_labels_redacted.jsonl
  privacy_bad_examples/
    local_path.json
    raw_vector_packet.json
```

Why both vector files:

- `section_vectors_8d.json` is for pure scorer/unit tests where numbers are easy
  to inspect.
- `section_vectors_512d.npy` is for store/parity tests that must preserve the
  real embedding dimensional contract without using real embeddings.

## Synthetic track set

Use track IDs that clearly cannot be real library IDs:

| Track ID | Genre profile | Purpose |
|----------|---------------|---------|
| `fx-hard-001` | hardtechno | clean high-mood ANLZ happy path |
| `fx-hard-002` | hardtechno | no intro, strong groove/drop/outro |
| `fx-tech-003` | techno | long tool groove and loop utility cue |
| `fx-house-004` | house | harmonic A/F mix-window case |
| `fx-dnb-005` | drum_and_bass | double-drop/dense exact-timing case |
| `fx-pop-006` | pop | vocal/hook risk and short sections |
| `fx-amb-007` | ambient/unknown | no drop, fallback/suppress behavior |
| `fx-bad-008` | unknown | malformed/missing facts edge cases |

Track record:

```json
{
  "track_id": "fx-hard-001",
  "title": "Fixture Hard One",
  "artist": "Fixture Artist",
  "genre": "hardtechno",
  "bpm": 180.0,
  "camelot": "8A",
  "duration_s": 300.0,
  "location": "fixture://tracks/fx-hard-001.wav",
  "is_synthetic": true
}
```

Rules:

- title/artist must start with `Fixture`.
- location must use `fixture://`.
- no track should resemble a real private library item.

## Section fixtures

`sections.json`

Use canonical section IDs:

```text
fx-hard-001#s000
fx-hard-001#s001
```

Section record:

```json
{
  "section_id": "fx-hard-001#s003",
  "track_id": "fx-hard-001",
  "ordinal": 3,
  "role": "drop",
  "start_s": 96.0,
  "end_s": 128.0,
  "start_beat": 289,
  "end_beat": 384,
  "source": "anlz",
  "source_detail": "pssi",
  "confidence": 0.86,
  "bpm": 180.0,
  "camelot": "8A",
  "energy_mean": 82.0,
  "density": 0.88,
  "vector_ref": "vec8:fx-hard-001#s003"
}
```

Required cases:

- high-confidence intro/build/breakdown/drop/outro;
- mid-confidence bridge mapped to review-only claim;
- unknown role section;
- too-short section;
- long outro;
- no beatgrid section;
- ambiguous source section;
- missing key/BPM section.

## ANLZ-like fixture objects

Do not commit binary ANLZ files in v1.

Use plain parsed objects:

```text
tests/intel/fixtures/anlz_bundles.json
```

Shape:

```json
{
  "track_id": "fx-hard-001",
  "ppth_path": "fixture://tracks/fx-hard-001.wav",
  "pqtz": {
    "times_s": [0.0, 0.333, 0.667],
    "bpms": [180.0, 180.0, 180.0],
    "beat_in_bar": [1, 2, 3]
  },
  "pssi": [
    {
      "mood": 1,
      "kind": 1,
      "raw_label": "Intro 1",
      "start_beat": 1,
      "end_beat": 96
    }
  ]
}
```

Purpose:

- unit-test ANLZ mapping without pyrekordbox binary fixtures;
- avoid local paths;
- keep parser tests pure and readable.

Future optional binary fixtures may be added only if:

- they are generated synthetic files;
- file provenance is documented;
- privacy scanner passes.

## Vector fixtures

### 8D vectors

Use hand-readable vectors where expected similarities are obvious.

Example:

```json
{
  "vec8:fx-hard-001#s003": [0.90, 0.70, 0.10, 0.00, 0.15, 0.20, 0.00, 0.00],
  "vec8:fx-hard-002#s001": [0.88, 0.72, 0.12, 0.00, 0.18, 0.18, 0.00, 0.00]
}
```

Use cases:

- transition scorer similarity;
- section search ranking;
- ablation tests;
- missing vector behavior.

### 512D synthetic vectors

Generate deterministic normalized vectors for storage/parity tests:

```text
vector = normalize(hash(seed + section_id) -> 512 floats)
```

Rules:

- never claim these are CLAP embeddings;
- never put 512D arrays in context packets;
- keep the `.npy` small and generated from documented seed.

## Transition fixtures

`transition_pairs.json`

Each item encodes a judged pair:

```json
{
  "pair_id": "tp_001",
  "from_section_id": "fx-hard-001#s006",
  "to_section_id": "fx-hard-002#s000",
  "intent": "rolling_blend",
  "expected_label": "good",
  "expected_risks": [],
  "notes": "outro to intro, compatible tempo and texture"
}
```

Required cases:

- good outro -> intro/groove;
- build -> drop;
- drop -> drop fatigue;
- harmonic clash with melodic sections;
- key unknown;
- BPM unknown;
- no cue slot;
- same-section reject;
- played-track leakage reject;
- high semantic match but bad phrase alignment.

## Smart cue fixtures

`smart_cue_proposals.json`

Must include:

- A/D/F happy path;
- human cue occupied slot;
- review-only mid-mood cue;
- suppressed duplicate;
- missing required D for ambient;
- loop utility G;
- export-ready vs review vs suppressed thresholds.

Proposal record should match INTEL-18:

```json
{
  "proposal_id": "cueprop_001",
  "track_id": "fx-hard-001",
  "policy_version": "smart_cue_policy_v1",
  "cues": [
    {
      "cue_id": "cueprop_001:A",
      "slot": "A",
      "role": "mix_in",
      "start_s": 0.0,
      "source": "anlz",
      "source_section_id": "fx-hard-001#s000",
      "confidence": 0.84,
      "review_status": "export_ready",
      "export_label": "VM A IN"
    }
  ]
}
```

## Cue baseline XML fixtures

Keep the INTEL-19 before/after XML synthetic:

```text
cue_baseline_before.xml
cue_baseline_after.xml
```

Must test:

- added hot cue;
- added memory cue;
- changed hot cue;
- removed cue;
- cue with `Num=-1`;
- cue with `Num=0..7`;
- no local file locations, only `fixture://` or safe relative fixture URIs.

## Context packet fixtures

`context_packets.json`

Required packets:

- prep packet with 8 candidates;
- live packet with 5 candidates and exact timing allowed;
- live packet with timing suppressed;
- live packet during blend;
- packet with taste consent off;
- packet with missing key/BPM;
- packet with claim ledger refs.

Must not contain:

- raw vectors;
- local paths;
- raw audio references;
- private taste ledger rows.

## Claim ledger fixtures

`claim_ledgers.json`

Include at least:

- valid harmonic claim;
- valid tempo claim;
- valid exact timing claim;
- valid cue slot claim;
- review-only cue claim;
- export success claim;
- internal-only claim;
- missing key -> no harmonic claim;
- forbidden phrase case.

This fixture is the core proof for INTEL-21.

## Agent decision fixtures

`agent_decisions.jsonl`

Include:

- valid select;
- hold;
- suppress;
- prep ask;
- live ask invalid;
- unknown candidate invalid;
- wrong cue invalid;
- exact timing below floor invalid;
- unsupported harmonic phrase invalid;
- export success claim without action invalid.

Each row:

```json
{
  "case_id": "dec_valid_select_001",
  "packet_id": "ctx_001",
  "decision": {
    "schema_version": "intel_decision_v1",
    "action": "select",
    "candidate_id": "tr_001",
    "cue_slot": "A",
    "spoken_text": "Next good entry: Fixture Hard Two cue A in 16 bars.",
    "cited_claim_ids": ["clm_ctx_001_000", "clm_ctx_001_001"]
  },
  "expected_validation": "ok"
}
```

## Decision trace fixtures

`decision_traces.jsonl`

Required:

- deterministic live select;
- model validated prep select;
- model degraded to deterministic copy;
- model rejected hold;
- model rejected suppress;
- model unavailable fallback;
- timing floor suppress;
- privacy redaction proof.

This fixture drives INTEL-20 replay tests.

## Gold-label redacted fixtures

`gold_labels_redacted.jsonl`

Public examples only:

- no private track IDs;
- no local paths;
- no private notes;
- use fixture IDs only.

Include one example per review type:

- section review;
- transition review;
- cue review;
- cue baseline comparison;
- live pill review;
- representation review.

## Privacy scanner

Add:

```text
scripts/eval/intel_fixture_audit.py
tests/eval/test_intel_fixture_audit.py
```

Scanner rejects:

```text
/Users/
/Volumes/
file://localhost
Music/
Pioneer/rekordbox
.mp3/.wav paths outside fixture:// or tests/audio/fixtures
real-looking absolute paths
raw vectors inside context packets
track title not starting with Fixture in public corpus
```

Scanner allows:

```text
fixture://...
tests/audio/fixtures/test_lookahead_track.mp3  # existing non-private tiny audio fixture
8D synthetic vector JSON
512D synthetic .npy only in vector fixture file
```

The scanner should run in CI once implemented.

## Dataset card

`dataset_card.json`

```json
{
  "dataset_card_id": "dataset_intel_synthetic_v1",
  "scope": "public deterministic test fixtures",
  "contains_private_data": false,
  "contains_audio": false,
  "contains_local_paths": false,
  "synthetic": true,
  "recommended_uses": [
    "unit tests",
    "schema validation",
    "privacy redaction tests",
    "deterministic scorer regression tests"
  ],
  "not_recommended_uses": [
    "claiming musical quality",
    "calibrating taste",
    "benchmarking CLAP quality"
  ]
}
```

## Implementation handoff

Add:

```text
tests/intel/fixtures/README.md
tests/intel/fixtures/dataset_card.json
tests/intel/fixtures/tracks.json
tests/intel/fixtures/sections.json
tests/intel/fixtures/anlz_bundles.json
tests/intel/fixtures/section_vectors_8d.json
tests/intel/fixtures/section_vectors_512d.npy
tests/intel/fixtures/transition_pairs.json
tests/intel/fixtures/transition_slates.json
tests/intel/fixtures/smart_cue_proposals.json
tests/intel/fixtures/cue_baseline_before.xml
tests/intel/fixtures/cue_baseline_after.xml
tests/intel/fixtures/context_packets.json
tests/intel/fixtures/claim_ledgers.json
tests/intel/fixtures/agent_decisions.jsonl
tests/intel/fixtures/decision_traces.jsonl
tests/intel/fixtures/live_awareness_snapshots.jsonl
tests/intel/fixtures/gold_labels_redacted.jsonl
scripts/dev/generate_intel_fixtures.py
scripts/eval/intel_fixture_audit.py
tests/eval/test_intel_fixture_audit.py
```

Generation script rules:

- deterministic seed;
- no network;
- no local library reads;
- can overwrite only files under `tests/intel/fixtures/`;
- emits a manifest hash.

## Fixture manifest

Add:

```text
tests/intel/fixtures/MANIFEST.json
```

Shape:

```json
{
  "fixture_version": "intel_fixture_v1",
  "generated_by": "scripts/dev/generate_intel_fixtures.py",
  "seed": "vibemix-intel-fixtures-v1",
  "files": {
    "tracks.json": "sha256:...",
    "sections.json": "sha256:..."
  }
}
```

Tests should fail if generated fixture hashes drift without an intentional
manifest update.

## Acceptance gates

Before first intelligence implementation PR:

```text
fixture corpus exists
fixture audit passes
schema load tests pass
no privacy scanner violations
fixtures cover every PR 1-8 readiness branch from INTEL-16
```

Focused command once implemented:

```bash
uv run pytest -q tests/eval/test_intel_fixture_audit.py tests/intel/test_fixture_loaders.py
```

## Open questions

1. Do we need temporary compatibility shims under `tests/library/fixtures/`, or
   can all new INTEL tests read `tests/intel/fixtures/` directly?
2. Should `section_vectors_512d.npy` be generated in-repo, or generated during
   tests to avoid binary churn?
3. Do fixture IDs need additional genre prefixes beyond the locked `fx-` prefix,
   or is `fx-<genre>-NNN` enough?
4. Should privacy scanner be a repo-wide test or only cover INTEL fixture paths?

## Success definition

The synthetic corpus is successful when a builder can implement the first
intelligence PRs and prove the contracts locally without:

```text
Kaan's private library
real audio
Rekordbox ANLZ binaries
network calls
model calls
local paths
```

That is what turns the intelligence architecture from a beautiful map into a
buildable system.
