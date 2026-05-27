# INTEL-16: implementation readiness checklist

**Date:** 2026-05-27
**Lane:** intelligence implementation governance / acceptance evidence
**Depends on:** INTEL-01 through INTEL-23
**Status:** builder-facing checklist for the first implementation sequence

## Purpose

The INTEL specs are now deep enough that a builder could accidentally implement
the right idea through the wrong seam. This checklist is the guardrail for the
first coding sequence.

Use it before opening each implementation PR. A PR is not "done" because code
exists; it is done when it ships the intended intelligence capability without
weakening grounding, privacy, or current product behavior.

## Entry conditions before coding

Do this once after the cleanup/debloat branch settles:

```bash
git status --short
git diff -- src/vibemix/library/cue_types.py src/vibemix/library/excerpt.py src/vibemix/library/ingest.py src/vibemix/library/toolset.py src/vibemix/runtime/suggestion.py
```

Required facts:

- unrelated cleanup changes are understood and not overwritten;
- all INTEL docs are present in `.planning/research/`;
- INTEL-13 is the naming source of truth;
- INTEL-22 synthetic fixtures exist or the PR explicitly adds the subset it
  needs;
- INTEL-23 has been checked if the PR adds/swaps a model, live analyzer, cue
  feature, or model-written explanation path;
- product code still uses local CLAP ONNX/512 as the default embedding path;
- no implementation PR starts by changing model dimensions or store semantics.

## Universal PR evidence bundle

Every INTEL PR should include:

```text
Capability shipped:
Files touched:
Grounding invariant checked:
Privacy invariant checked:
Compatibility invariant checked:
Commands run:
Known gaps:
Next cut:
INTEL-23 bet advanced:
INTEL-23 kill/graduate evidence:
```

Minimum checks for every PR:

```bash
uv run ruff check <changed-python-files>
uv run ruff format <changed-python-files> --check
uv run pytest -q <focused-tests>
```

If a PR changes UI-visible payloads, also run the relevant UI tests. If a PR
changes Rust sidecar wiring, run `cargo check --manifest-path
tauri/src-tauri/Cargo.toml`.

## Universal no-go checks

Reject the PR if it does any of these:

- reads or mutates Rekordbox `master.db`;
- reads Rekordbox process memory;
- reintroduces screen vision as a ground-truth ingest path;
- sends private audio, local paths, or raw vectors to a language model;
- lets the LLM create track IDs, section IDs, cue payloads, BPM, key, or timing;
- accepts action IDs that were not issued/seen in the current run;
- silently loosens eval thresholds;
- changes product embedding dimension without a migration plan;
- breaks existing track-level library search or old `next_suggestion` payloads.

## PR 0 readiness: synthetic fixture corpus

Capability:

```text
The first intelligence implementation tests can run without private tracks,
local paths, real ANLZ binaries, network calls, or model calls.
```

Files:

```text
tests/intel/fixtures/...
scripts/dev/generate_intel_fixtures.py
scripts/eval/intel_fixture_audit.py
tests/eval/test_intel_fixture_audit.py
```

Acceptance evidence:

- INTEL-22 fixture manifest exists;
- fixture audit rejects local paths and raw vectors in packets;
- fixture IDs use `fx-` and `fixture://`;
- fixtures cover sections, transitions, cue proposals, context packets, claim
  ledgers, decisions, traces, and redacted labels;
- generated fixture hashes are deterministic.

Focused command:

```bash
uv run pytest -q tests/eval/test_intel_fixture_audit.py tests/intel/test_fixture_loaders.py
```

## PR 1 readiness: ANLZ parser and excerpt priority

Current status:

```text
parser/mapper slice exists
focused parser tests exist
excerpt priority integration exists
fixture/audit tests exist
caller-injected ingest wiring exists
ANLZ audit CLI exists
product orchestration index construction exists
```

Capability:

```text
Rekordbox ANLZ phrase/beatgrid data becomes a first-class structure source.
```

Files:

```text
src/vibemix/library/anlz_ingest.py
src/vibemix/library/cue_types.py
src/vibemix/library/excerpt.py
tests/library/test_anlz_ingest.py
tests/library/test_excerpt.py
```

Acceptance evidence:

- `CueSource` includes `"anlz"`;
- `anlz_ingest` top-level import does not import SQLCipher, CLAP, torch, audio
  decode, or Rekordbox DB readers;
- `.EXT` `PSSI` provides phrase entries;
- sibling `.DAT` `PQTZ` provides beat-to-time conversion;
- `PPTH` path matching is unique or returns no match;
- priority is `DJ -> ANLZ -> auto -> empty`;
- missing or ambiguous ANLZ degrades honestly;
- DJ-authored cues still win.
- ingest accepts a caller-built ANLZ index without changing the track-vector store
  contract;
- ANLZ-matched cache keys cannot reuse stale no-ANLZ fallback vectors.
- `scripts/eval/intel_anlz_audit.py` emits redacted PSSI/PQTZ/PPTH coverage,
  parse error rate, path collision hashes, role distribution, and confidence
  buckets.
- `_cmd_library_ingest` builds/passes the ANLZ index once per run and falls back
  to DJ/auto cues when the index is empty or unavailable.

Focused command:

```bash
uv run pytest -q tests/library/test_ingest_cli_anlz.py tests/library/test_ingest.py tests/library/test_anlz_ingest.py tests/library/test_excerpt.py tests/eval/test_intel_anlz_audit.py
```

Do not include:

- section vector storage;
- live pill changes;
- `master.db` access;
- model swaps.

## PR 2 readiness: ANLZ audit and smart cue prep

Capability:

```text
The app can prove ANLZ coverage and propose reviewable smart cues.
```

Files:

```text
scripts/eval/intel_anlz_audit.py
src/vibemix/library/smart_cues.py
tests/eval/test_intel_anlz_audit.py
tests/library/test_smart_cues.py
```

Current partial implementation:

```text
done: scripts/eval/intel_anlz_audit.py
done: tests/eval/test_intel_anlz_audit.py
done: src/vibemix/library/smart_cues.py
done: tests/library/test_smart_cues.py
done: proposal_to_export_marks() produces slot-preserving export_set cue marks
done: grounded tool surface for issuing/exporting proposals
done: INTEL-19 baseline comparison harness first slice
```

Acceptance evidence:

- audit emits PSSI coverage, parse error rate, PQTZ coverage, path collisions,
  role distribution, and confidence buckets;
- private/local audit outputs do not contain raw local paths in committed files;
- smart cues map roles to stable slots A-H;
- smart cues follow INTEL-18 source priority, thresholds, and genre policy;
- smart-cue export preserves explicit A-H slot numbers;
- INTEL-19 comparison harness can compare vibemix proposals with Rekordbox
  auto-cue XML snapshots when available and report redacted comparative lift;
- exported cue proposals are review-first;
- existing DJ cues are not overwritten by default;
- no direct Rekordbox DB writes.

Focused command:

```bash
uv run pytest -q tests/eval/test_intel_anlz_audit.py tests/eval/test_intel_cue_baseline_compare.py tests/library/test_smart_cues.py tests/library/test_toolset.py
```

Human evidence before turning this into default product behavior:

```text
20 reviewed tracks
>=70% cue slots keep/maybe
0 overwritten DJ cues
```

## PR 3 readiness: section store and section index

Capability:

```text
The data unit becomes a searchable musical section while whole-track search
remains stable.
```

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

Acceptance evidence:

- section IDs are `<track_id>#sNNN`;
- section metadata carries `source` and `source_detail`;
- section vectors are stored separately from product track vectors;
- product `EMBEDDING_DIM = 512` remains intact;
- section vector dim mismatch fails loudly;
- section extraction can run without embedding;
- embedding can be skipped or resumed;
- whole-track search tests still pass.

Focused command:

```bash
uv run pytest -q tests/library/test_section_types.py tests/library/test_section_store.py tests/library/test_section_index_numpy.py tests/library/test_section_ingest.py tests/library/test_search.py tests/library/test_next_suggestion.py
```

Do not include:

- transition scoring weights;
- agent tool changes;
- model bake-offs beyond current CLAP section windows.

## PR 4 readiness: transition scorer

Capability:

```text
The app ranks section-to-section moves with deterministic score components.
```

Files:

```text
src/vibemix/intel/musical_ontology.py
src/vibemix/intel/transition_scorer.py
tests/intel/test_musical_ontology.py
tests/intel/test_transition_scorer.py
```

Acceptance evidence:

- canonical INTEL-11 weights are used;
- missing facts lower confidence without inventing data;
- harmonic/BPM risks only fire when facts are known enough;
- risk flags are structured;
- no NaN/inf scores;
- tie-breaks are deterministic;
- taste defaults to neutral;
- scorer is pure and import-light.

Focused command:

```bash
uv run pytest -q tests/intel/test_musical_ontology.py tests/intel/test_transition_scorer.py
```

Do not include:

- model-authored explanations;
- tool export;
- live timing claims.

## PR 5 readiness: grounded intelligence tools

Capability:

```text
The agent can ask for sections, transition slates, cue proposals, and
explanations through run-scoped holders.
```

Files:

```text
src/vibemix/library/toolset.py
src/vibemix/library/mcp_server.py
src/vibemix/library/codex_curate.py
tests/library/test_toolset.py
tests/library/test_setprep_tools.py
```

Acceptance evidence:

- `seen_sections` exists;
- `issued_transition_candidates` exists;
- `issued_cue_proposals` exists;
- `issued_context_packets` exists if context compiler is included;
- `smart_hot_cues` issues cue proposal/cue IDs from grounded tracks;
- `export_smart_cues` accepts only issued proposal/cue IDs, not raw cue payloads;
- invented section IDs are rejected;
- invented candidate IDs are rejected;
- proposals are revalidated before export;
- existing `search_vibe`, `discover_pool`, `export_set`, and `create_playlist`
  behavior stays compatible.

Focused command:

```bash
uv run pytest -q tests/library/test_toolset.py tests/library/test_setprep_tools.py tests/library/test_codex_curate.py
```

Do not include:

- permanent taste writes from tool calls;
- raw cue-payload export from the model;
- new EvidenceRegistry sources unless the full citation migration is in scope.

## PR 6 readiness: context compiler and validator

Capability:

```text
The LLM receives a bounded musical context packet and can only select/ask/explain
inside that packet.
```

Files:

```text
src/vibemix/intel/context_compiler.py
src/vibemix/intel/decision_validator.py
tests/intel/test_context_compiler.py
tests/intel/test_decision_validator.py
tests/eval/test_intel_decision_runtime_replay.py
```

Acceptance evidence:

- packet IDs are `ctx_NNN`;
- schema version is `intel_context_v1`;
- context is bounded and redacted;
- validator rejects unknown candidates, sections, cue proposals, and timing
  overclaims;
- context packets now carry compact INTEL-21 `claim_ids` and `claim_summary`;
- no raw vectors in packet;
- no raw local paths in packet;
- old agent surfaces degrade to no-op if no packet exists.

Focused command:

```bash
uv run pytest -q tests/intel/test_context_compiler.py tests/intel/test_decision_validator.py
```

## PR 7 readiness: musical claim validation

Capability:

```text
Every model-visible musical fact is represented as a typed, evidence-bound
claim before the agent can say it.
```

Files:

```text
src/vibemix/intel/claims.py
src/vibemix/intel/claim_validator.py
tests/intel/test_claims.py
tests/intel/test_claim_validator.py
```

Acceptance evidence:

- claim IDs are packet-scoped;
- unsupported timing/cue/harmonic/tempo/taste/export phrases are rejected;
- review-only cues cannot be called export-ready;
- exported/saved language requires an action-success claim;
- missing claim evidence degrades live output;
- claim ledger redacts local paths, vectors, and audio.

Focused command:

```bash
uv run pytest -q tests/intel/test_claims.py tests/intel/test_claim_validator.py tests/intel/test_context_compiler.py tests/intel/test_decision_validator.py
```

Do not include:

- new EvidenceRegistry citation sources;
- LLM-based claim validation;
- model-written live copy as the default.

## PR 8 readiness: agentic decision runtime

Capability:

```text
The app turns validated packets into deterministic/model-assisted decisions and
degrades unsafe model output to hold/suppress/deterministic fallback.
```

Files:

```text
src/vibemix/intel/decision_runtime.py
src/vibemix/intel/decision_trace.py
tests/intel/test_decision_runtime.py
tests/intel/test_decision_trace.py
scripts/eval/intel_decision_runtime_replay.py
tests/eval/test_intel_decision_runtime_replay.py
```

Acceptance evidence:

- live pill uses deterministic path by default;
- model backend is injected and optional;
- validator failure never emits model-written copy;
- live exact timing is blocked below floor or during blend;
- unsupported musical claims degrade before emission;
- `DecisionSource` is recorded;
- traces redact local paths, vectors, and audio;
- old `next_suggestion` payload remains compatible until UI migration.

Current implementation:

```text
done: src/vibemix/intel/decision_runtime.py
done: src/vibemix/intel/decision_trace.py
done: tests/intel/test_decision_runtime.py
done: tests/intel/test_decision_trace.py
done: scripts/eval/intel_decision_runtime_replay.py
done: tests/eval/test_intel_decision_runtime_replay.py
pending: product UI/backend default wiring to consume RuntimeDecisionResult
pending: real private replay report and release threshold lock
```

Focused command:

```bash
uv run pytest -q tests/intel/test_decision_runtime.py tests/intel/test_decision_trace.py tests/eval/test_intel_decision_runtime_replay.py tests/runtime/test_suggestion.py
```

Do not include:

- UI migration;
- model-written live copy as the default;
- permanent preference writes;
- new citation sources.

## PR 9 readiness: gold-label validation and eval gates

Capability:

```text
Private human judgements become replayable evidence, not loose notes.
```

Files:

```text
src/vibemix/intel/gold_labels.py
src/vibemix/intel/gold_sampling.py
src/vibemix/intel/gold_validation.py
scripts/eval/intel_gold.py
tests/intel/test_gold_labels.py
tests/intel/test_gold_sampling.py
tests/eval/test_intel_gold_validation.py
```

Acceptance evidence:

- INTEL-15 JSONL schemas validate;
- calibration/holdout/canary splits exist;
- holdout correction uses `supersedes`;
- redacted reports hash track IDs and omit local paths;
- labels cannot be used as action IDs;
- validation catches unknown candidate/proposal IDs.

Current implementation:

```text
done: src/vibemix/intel/gold_labels.py
done: src/vibemix/intel/gold_sampling.py
done: src/vibemix/intel/gold_validation.py
done: scripts/eval/intel_gold.py
done: tests/intel/test_gold_labels.py
done: tests/intel/test_gold_sampling.py
done: tests/eval/test_intel_gold_validation.py
done: eval/INTEL-THRESHOLD-RECALIBRATION-LOG.md defines the redacted
      private-label calibration/holdout/canary note format for future threshold
      movement
done: scripts/eval/intel_recalibration_note.py renders that note from redacted
      private scorecard/gold/taste reports and blocks release promotion without
      holdout/canary coverage
pending: first private gold slice
pending: release threshold lock fed by holdout/canary labels
pending: durable taste-consent ingestion from labels
```

Focused command:

```bash
uv run pytest -q tests/intel/test_gold_labels.py tests/intel/test_gold_sampling.py tests/eval/test_intel_gold_validation.py
```

## Release/eval gate readiness

The intelligence milestone cannot be called complete until evidence proves:

```text
ANLZ coverage is healthy.
Section retrieval beats whole-track retrieval on transition queries.
Transition slates rank playable moves above bad moves.
Agent decisions stay inside issued packets.
Smart cue export is proposal-based and reviewable.
Live timing never overclaims below confidence floors.
Taste improves ranking without privacy leaks or scorer poisoning.
Scorecard/threshold lock enforce the above.
Provenance manifests can replay or explain the evidence above.
```

Current implementation:

```text
done: scripts/eval/intel_scorecard.py
done: tests/eval/test_intel_scorecard.py
done: aggregate fixture scorecard covers ANLZ audit, cue baseline comparison,
      section retrieval delta, transition scorecard, decision replay, and
      gold-label validation, plus taste privacy/poisoning gates
done: scripts/eval/intel_section_retrieval.py
done: tests/eval/test_intel_section_retrieval.py
done: tests/intel/fixtures/section_queries.jsonl
done: scripts/eval/intel_transition_scorecard.py
done: tests/eval/test_intel_transition_scorecard.py
done: fixture decision replay hydrates candidate/claim ledgers and passes
      fallback/timing gates
done: taste privacy/poisoning fixture gate
done: src/vibemix/intel/feedback.py
done: src/vibemix/intel/taste_model.py
done: src/vibemix/intel/profile_projection.py
done: scripts/eval/intel_taste_scorecard.py
done: tests/intel/test_feedback.py
done: tests/intel/test_taste_model.py
done: tests/intel/test_profile_projection.py
done: tests/eval/test_intel_taste_scorecard.py
pending: transition scorecard over real private reviewed labels
pending: durable taste storage and product feedback capture surfaces
done: eval/INTEL-THRESHOLD-LOCK.md fixture thresholds and scorecard CLI wiring
done: scorecard emits Tier 0 fixture replay provenance with manifest/threshold
      hashes and safe replay command
done: scripts/eval/intel_provenance_report.py validates scorecard provenance,
      manifest/threshold hashes, replay command, and privacy flags
done: scripts/eval/intel_gate.py runs fixture audit + locked scorecard +
      provenance validation as one CI-ready command
done: intel gate CLI supports `--output` for persisted JSON evidence artifacts
done: persisted intel gate artifacts include scorecard metrics, gate statuses,
      artifact statuses, and provenance hashes for release review
done: `.github/workflows/eval.yml` runs the INTEL fixture gate and writes
      `.planning/eval-runs/<sha>/intel_gate.json`
done: workflow threshold-edit warning covers both `eval/THRESHOLD-LOCK.md` and
      `eval/INTEL-THRESHOLD-LOCK.md`
done: `scripts/release/check_gate.sh` requires recent `intel_gate.json` artifacts
      to report `valid=true` and carry scorecard metrics, gates, artifact
      statuses, Tier 0 replay provenance, and provenance hashes
done: `scripts/release/check_gate.sh` rejects stale INTEL artifacts whose
      threshold-lock hash does not match the current `eval/INTEL-THRESHOLD-LOCK.md`
done: `scripts/release/check_gate.sh` rejects stale INTEL artifacts whose
      fixture-manifest hash does not match the current `tests/intel/fixtures/MANIFEST.json`
done: `scripts/release/check_gate.sh` rejects inconsistent INTEL artifacts whose
      fixture-audit manifest hash disagrees with scorecard provenance
done: `scripts/release/check_gate.sh` rejects stale INTEL artifacts whose
      thresholds hash does not match the current parsed `intel_thresholds`
done: `scripts/eval/intel_gate.py` marks cross-stage fixture-manifest
      mismatches invalid before release-gate consumption
done: `scripts/eval/intel_gate.py` marks scorecard/provenance-stage mismatches
      invalid for dataset id, fixture version, manifest hash, thresholds hash,
      replay tier, and threshold-lock hash
done: `scripts/release/check_gate.sh` rejects INTEL artifacts whose dataset card
      id or fixture version does not match the current fixture manifest
done: `scripts/release/check_gate.sh` validates provenance-stage replay tier,
      fixture manifest hash, thresholds hash, and threshold-lock hash against
      the current release evidence, not only the scorecard provenance copy
done: release-gate tests feed `scripts/release/check_gate.sh` a real
      `scripts.eval.intel_gate.run_intel_gate()` artifact, pinning producer /
      consumer compatibility instead of only handcrafted JSON fixtures
done: `.github/workflows/eval.yml` DCO-signs nightly `.planning/eval-runs/`
      evidence commits with `git commit -s`, and workflow tests pin the
      `vibemix-eval-bot` identity + signoff flag
done: private-label release threshold recalibration note exists at
      `eval/INTEL-THRESHOLD-RECALIBRATION-LOG.md` and is referenced by the
      INTEL threshold lock/public eval docs
done: `scripts/eval/intel_recalibration_note.py` is the reproducible producer
      for the private-label note, including privacy and split-coverage gates
done: `scripts/eval/intel_recalibration_note.py` rejects malformed
      timestamp/run-id identity fields before writing output or appending logs
done: `scripts/eval/intel_recalibration_note.py --append-log` appends only
      valid entries to the public recalibration log and refuses invalid evidence
done: `scripts/eval/intel_recalibration_note.py --append-log` validates the
      candidate whole log before writing, so duplicate run IDs and out-of-order
      timestamps cannot be appended
done: `scripts/eval/intel_recalibration_note.py` writes `--output` only after
      candidate append-log validation succeeds when both flags are supplied
done: private-label recalibration notes carry canonical SHA-256 hashes for the
      exact redacted scorecard/gold/taste/gate reports used to render the entry
done: `scripts/eval/intel_recalibration_log_validate.py` validates the public
      INTEL recalibration log schema, report-hash bindings, and privacy markers
done: `scripts/eval/intel_recalibration_log_validate.py` rejects stale public
      recalibration entries whose lock digest does not match the current
      `eval/INTEL-THRESHOLD-LOCK.md`
done: `scripts/eval/intel_recalibration_log_validate.py` rejects duplicate,
      unknown, and malformed key-value tokens in machine-audited public
      recalibration entries
done: `scripts/eval/intel_recalibration_log_validate.py` rejects duplicate
      private recalibration `run_id` values and entries whose timestamps move
      backwards in the append-only public audit trail
done: `.github/workflows/eval.yml` runs the recalibration-log validator before
      generating INTEL fixture-gate artifacts, catching audit-log drift on PRs
      and nightly canaries
done: `scripts/release/check_gate.sh` blocks release when the public INTEL
      recalibration log is missing, malformed, hashless, or privacy-leaking
done: release-promotion notes require a valid `intel_gate.py` artifact whose
      scorecard/provenance lock hashes match the promoted INTEL threshold lock
done: release-promotion notes reject failed scorecards and gate/scorecard
      threshold-hash disagreement before the lock can be promoted
```

The docs are not the milestone. The scorecard is.

## Review questions for every PR

Ask these in review:

1. What user-visible intelligence got more true?
2. What deterministic data object did we add or improve?
3. What can the model no longer hallucinate because of this change?
4. What fallback happens when the new data is missing?
5. What private data could leak, and how did the PR prevent it?
6. Which existing behavior proves compatibility?
7. Which future cut did this unblock?

If those answers are vague, the PR is not ready.

## First-session operating mode

When coding begins, keep the first implementation session narrow:

```text
PR 1 only: ANLZ parser + CueSource + excerpt priority.
```

Reason:

- it unlocks the data floor;
- it does not alter stores;
- it does not require UI;
- it can be verified with focused tests and a local audit;
- it gives every later cut real structure to consume.

This is the safest first step from research excellence into product excellence.
