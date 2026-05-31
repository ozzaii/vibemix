# Whole Rebuild Brief - 2026-05-31

Purpose: reset the planning posture now that the project is moving toward a
whole rebuild. The existing package map is still valuable, but its job changes:
it becomes source-of-truth extraction, migration evidence, and risk control for
what the rebuild should preserve or reject.

## Posture Change

Do not treat the current dirty tree as the final shape to polish.

Do treat it as:

- a proven-behavior inventory;
- an evidence ledger for product claims;
- a list of carry-forward candidates;
- a warning map for what not to rebuild blindly;
- a source of tests, fixtures, and runtime proof patterns.

The rebuild should not be a file shuffle of the current repo. It should be a
smaller architecture that carries forward the real contracts and drops demo-only
or unproven wiring.

## Current State

Fresh checkpoint:

- `git diff --shortstat` reports 120 tracked files changed, 6859 insertions,
  and 2256 deletions.
- Before this packet, the package checker was red because new Claude/team files
  appeared after the previous green checkpoint.
- Those paths are now classified in the package checklist as rebuild-intake docs
  plus candidate carry-forward modules: AI observability, bench/Learn
  observability, Serato cue export, binary verification, deck vision, debrief
  summaries/drills, Codex curation, judge voice evidence, and demo-source-run
  notes.

This is expected during the rebuild handoff. The immediate integration duty is
to keep new paths classified as they appear, not to force them into the old
package lanes.

## Carry Forward

Preserve these contracts in the rebuild:

- Live audio/state remains authoritative. The app must not infer deck truth from
  model prose alone.
- AI claims resolve through evidence, citations, or explicit uncertainty.
- The websocket/UI bus keeps strict schemas, generated TypeScript, and parity
  checks.
- Product-facing live proof means source/runtime evidence, not only unit tests.
- Library/cue tools must preserve provenance: cue source, cue number, risk, and
  export path.
- Dependency upgrades happen in rings, not mixed with feature ports.
- Signing/release packaging is a separate release lane, not a runtime feature.

## Do Not Carry Forward Blindly

Do not rebuild these patterns as-is:

- Giant orchestrator files that hide multiple ownership boundaries.
- Demo-only CLI paths presented as live-app behavior.
- Static mockups or screenshots treated as product proof.
- Broad IPC schemas with no real producer/consumer.
- Model-quality claims without real-model evaluation.
- Launch/pricing copy that outruns verified cost and runtime evidence.
- Local runtime experiments that lack license, model-source, install, and bundle
  proof.

## Rebuild Architecture Slices

Use these slices as the first rebuild boundaries:

1. Runtime core: live audio capture, music state refresh, event detection, and
   the evidence registry.
2. AI co-host core: prompt compiler, model router, citation lint, response
   filter, TTS chain, and AI-message observability.
3. UI bus: canonical IPC schema, generated TS/validator, Rust bridge, and
   mock-transfer contract.
4. Library/cue core: CLAP search, cue detection, cue provenance, Rekordbox/XML,
   Serato/Markers2, Viber tools, and set-prep exports.
5. Learn/skill core: practice loops, judge events, earned credit, and cited
   mastery state.
6. Desktop shell/release: Tauri sidecar lifecycle, bundle freshness, binary
   verification, signing/notarization, and update path.
7. Eval/proof: real-CLAP retrieval, real ONNX coverage, live websocket probes,
   visual proof, and public-claim gates.

## Migration Order

1. Freeze the contracts: copy the package checklist, dependency packet, IPC
   packet, and this rebuild brief into the new build's planning root.
2. Build the skeletal runtime and UI bus first. No product feature can be called
   live until this spine exists.
3. Port verification tools before porting feature code:
   `check_dirty_package_plan.py`, IPC schema checks, IPC wiring checker,
   websocket probe, and grounding-review checklist.
4. Port the AI co-host with observability and citation lint in place from day
   one.
5. Port library/cue exports as isolated carriers: XML/M3U8/Serato first, then
   app integrations.
6. Port Learn and visual polish only after the runtime evidence spine works.
7. Modernize dependencies ring by ring after the spine is green.
8. Rebuild release packaging last, with binary verification and signing proof.

## Evidence Gates

Minimum proof for a rebuild milestone:

- Unit tests prove pure contracts.
- IPC schema/codegen/parity checks prove bus shape.
- Source-mode websocket proof reaches `127.0.0.1:8765`.
- UI proof shows the renderer consuming the bus.
- Live proof records `events.jsonl` and `ui.log`.
- Model/cue claims have real-model or fixture eval coverage.
- Release claims have sidecar freshness, binary verification, and signing gates.

If a claim cannot be proven by one of these, phrase it as a candidate, not a
done feature.

## What The Current Planning Docs Become

- `2026-05-31-package-checklist.md`: carry-forward inventory and collision map.
- `2026-05-31-maintainability-map.md`: architecture debt and risk ledger.
- `2026-05-31-dirty-tree-shipping-inventory.md`: raw old-tree evidence.
- `2026-05-31-future-ai-routing.md`: old-tree routing doorway.
- `2026-05-31-refactor-wiring-session-handoff.md`: useful only if landing in
  the old tree; for the rebuild, treat it as IPC contract evidence.
- `2026-05-31-ipc-staging-packet.md`: canonical IPC contract extraction source.
- `2026-05-31-dependency-modernization-packet.md`: dependency ring plan.
- `2026-05-31-DEMO-SHIP-PLAN.md`: demo-source-run plan, not rebuild truth.

## Next Integration Move

Classify all new Claude/team files into rebuild carry-forward lanes, then get
the package checker green again. After that, build a small integration dispatch
board that tracks which teams own which rebuild slices and which old-tree files
are evidence-only.
