# Claude Workflow Dispatch - 2026-05-31

Purpose: use Claude Code's workflow fanout as a controlled rebuild machine,
not a swarm of unrelated edits. This dispatch gives the controller and every
sub-agent the same read order, slice boundaries, output format, and verifier
handoff contract.

## Controller Prompt

```text
You are the Claude Code workflow controller for the vibemix whole rebuild.

Repo:
/Users/ozai/projects/dj-set-ai

Read first, in this order:
1. AGENTS.md
2. CLAUDE.md
3. .planning/handoffs/2026-05-31-rebuild-brief.md
4. .planning/handoffs/2026-05-31-capability-integration-ledger.md
5. .planning/handoffs/2026-05-31-package-checklist.md
6. .planning/handoffs/2026-05-31-maintainability-map.md
7. .planning/handoffs/2026-05-31-future-ai-routing.md

Mission:
Finish the rebuilt app with all planned capabilities either integrated,
explicitly deferred with evidence, or deleted intentionally. Nothing should be
left behind as an unreviewed loose file, stale mock, demo-only claim, or
uncited capability.

Rules:
- Treat the old dirty tree as evidence and carry-forward inventory, not the
  final architecture.
- Fan out read-only scouts first. Do not let sub-agents write code until their
  slice, files, and proof gates are assigned.
- Every new or dirty file must be classified in
  .planning/handoffs/2026-05-31-package-checklist.md.
- Every planned capability must be represented in
  .planning/handoffs/2026-05-31-capability-integration-ledger.md.
- Do not use git add -A.
- Do not mix slices in one commit.
- Do not call a feature live without runtime proof.
- Do not call a model/cue claim safe without real-model or fixture proof.
- When a slice is done, produce a Codex verifier packet with files, tests,
  live proof, residual risks, and package-checker output.
```

## Fanout Phases

## Coordinated Operating Loop

Use this loop for the rebuild:

1. Claude workflow controller fans out scouts or builders.
2. Claude workers finish one bounded milestone.
3. Claude controller updates the capability ledger and package checklist.
4. Claude hands Codex the verifier packet.
5. Codex independently checks the files, tests, runtime evidence, package lanes,
   and claims.
6. If Codex accepts, the milestone can move forward.
7. If Codex rejects or marks partial, Claude gets a narrow fix packet.

This keeps Claude optimized for speed and breadth while Codex acts as the
integration brake, evidence checker, and "nothing left behind" auditor.

### Phase 1 - Read-Only Recon

Spawn scouts with no write permission or with an explicit "do not edit" task.
Each scout answers in the report format below.

Recommended scouts:

- Runtime core: audio capture, MusicState refresh, event detector, deck context,
  deck vision, drop timing, evidence registry.
- AI co-host: prompt compiler, model router, citation lint, response filter,
  TTS chain, AI-message observability, Vibe Judge voice.
- UI bus and desktop bridge: IPC schema, generated TS, validators, Rust bridge,
  mock-transfer, Tauri sidecar lifecycle.
- Library/cue/Viber: CLAP search, smart cues, ANLZ/Rekordbox, cue folder,
  Serato/Mixxx, cue agreement, Viber tools.
- Learn and skill tree: curriculum, operator bridge, judge events, earned wall,
  Learn tutor observability, beatmatch producer gap, and live-runtime evidence
  reuse. This scout must also read runtime/evidence/cue/judge slices; Learn is
  not allowed to remain a silo.
- Release and packaging: sidecar freshness, binary verification, signing,
  notarization, installer/update path.
- Eval and proof: package checker, IPC checker, real CLAP eval, missing real
  ONNX gate, live websocket probes, visual proof, reality pins.
- Dependencies and weight: Python/npm/Cargo rings, audit findings, bundle size,
  optional extras, local model/license boundaries.
- UX/polish: session shell, pill, settings, library UI, launch collateral,
  screenshots and mockup-transfer status.

### Phase 2 - Capability Ledger Merge

The controller merges scout reports into the capability ledger. No feature work
starts until the ledger has:

- status for the capability;
- source files to carry forward or drop;
- target rebuild slice;
- proof gate;
- owner/team;
- current risk.

### Phase 3 - Build Slices

Assign one slice per implementation team. A team may edit only its assigned
files and must update the package checklist if new files appear.

Suggested first implementation slices:

1. Runtime spine plus UI bus skeleton.
2. AI co-host core plus AI-message observability.
3. Library/cue export core: XML/M3U8/Serato/Mixxx, cue provenance, real CLAP
   eval.
4. Learn/earned-wall core plus real beatmatch producer decision.
5. Desktop/release spine: sidecar freshness, binary verification, signing path.
6. Visual/session UI once the bus is stable.
7. Dependency modernization after the spine is green.

### Phase 4 - Verification Fanout

Spawn independent read-only verifiers after each slice:

- Contract verifier: checks files match the assigned slice and no unrelated
  paths are staged.
- Test verifier: reruns focused tests and confirms they cover the claim.
- Runtime verifier: runs source-mode / websocket / log proof when live behavior
  is claimed.
- Claim verifier: checks docs, UI copy, launch copy, and public claims against
  evidence.
- Dependency verifier: checks lockfiles, audit, pip/cargo/npm conflicts, and
  optional extras.
- Cleanup verifier: searches for stale mocks, dead adapters, orphan tests, and
  duplicate old-tree code.

### Phase 5 - Codex Verification Handoff

When Claude says a slice or the whole rebuild is done, hand Codex this packet:

```text
Codex verifier packet

Scope:
- Slice name:
- Goal:
- Claimed status:

Files changed:
- ...

Checklist lane:
- ...

Capability ledger rows changed:
- ...

Commands run:
- command -> exact result

Live/runtime proof:
- command/session:
- ws evidence:
- ui.log/events.jsonl evidence:
- screenshots/recordings if UI-visible:

Claims made:
- ...

Known deferrals:
- ...

Residual risks:
- ...

Current package checker:
- exact output or pasted summary

Request:
Codex, verify this independently. Do not trust the narrative. Inspect files,
rerun relevant checks, confirm package/checklist boundaries, and tell us whether
this is accepted, rejected, or needs another pass.
```

## Learn Is Not Leftover

The Learn module should benefit from the same shared engineering spine as the
live app:

- live deck/cue/judge evidence should be available to Learn when teaching or
  crediting a skill;
- Learn tutor speech should use the shared AI-message observability stream;
- debrief drills should be able to feed Learn practice suggestions;
- earned mastery should require a real live producer, not only a UI/fixture
  consumer;
- Learn UI must follow the same IPC/schema discipline as the session UI.

Any Claude sub-agent assigned to Learn must read the runtime, evidence,
cue/judge, observability, and UI-bus notes too. A narrow curriculum-only pass is
not enough for the rebuild.

## Sub-Agent Report Format

Every scout or verifier returns:

```text
Agent:
Slice:
Read files:
Current capability status:
Carry forward:
Drop/defer:
Missing proof:
Conflicts/shared paths:
Suggested package/checklist lane:
Tests or commands to prove it:
Risks:
One-line recommendation:
```

## Completion Rule

The rebuild is not complete until:

- package checker is green;
- capability ledger has no "unknown" rows;
- all claimed live features have runtime proof;
- all model/cue claims have real eval or explicit deferral;
- all launch/public claims cite evidence;
- every dirty file is integrated, deferred, or intentionally removed;
- Codex verifier accepts the final packet.
