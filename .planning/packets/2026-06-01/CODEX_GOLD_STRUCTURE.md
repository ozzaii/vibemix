# CODEX Gold Structure

Date: 2026-06-01
Verifier: Codex
Purpose: group the verified packets into product streams so landing can happen
in batches, without losing package boundaries or proof debt.

## Reading Order

Start with:

1. `CODEX_PACKAGE_SWEEP_STATUS.md` - current proof and release reality.
2. `INDEX.md` - durable packet archive and recovered workflow index.
3. This file - grouped landing structure.

Do not use `/tmp/vibemix-codex-inbox/` as source of truth. It was already lost
once. The repo packet archive is the source.

## Gold Streams

### Gold 0 - Control Plane And Product Truth

Packets:

- `CODEX_READY-planning-control-plane.md`
- `CODEX_READY-product-posture-docs-cleanup.md`
- `CODEX_HOLD-open-hold-lanes.md`
- `CODEX_HOLD-flx4-live-acceptance-current.md`
- `viber-capability-CORRECTION.md`

Landing posture: LAND docs and governance first, HOLD proof artifacts separate.

What it buys:

- Every dirty path has an Include/Hold owner.
- Viber/Crate is corrected as wired through Tauri `invoke()`, not entirely dead.
- Product posture is commercial/managed-service aware, not blocked by old
  "fully open source" positioning.
- `/tmp` is demoted to scratch.

Acceptance debt:

- Keep package checker green after every new packet or dirty path.
- Do not promote FLX4/live acceptance until the physical proof window captures
  audible deck audio, direct controller motion, and resolved deck identity.

### Gold 1 - AI Observability And Eval Gate

Packets:

- `CODEX_READY-ai-message-observability-spine.md`
- `CODEX_READY-debrief-test-hygiene.md`
- `CODEX_READY-cohost-viber-release-matrix-wrapper.md`
- `CODEX_READY-cohost-viber-live-rehearsal-wrapper.md`
- `CODEX_READY-cohost-viber-runtime-canaries-wrapper.md`

Landing posture: LAND as the product's black-box recorder and release gate.

What it buys:

- AI messages, prompts, responses, citations, model/provider, latency,
  deck-mixer snapshots, and response artifacts are inspectable.
- Bench, eval, Viber/Codex, live co-host, Learn tutor, deck vision, and debrief
  surfaces are covered by static tests or artifact verifiers.
- Release wrappers can run source-level autopilot, corpus, matrix, rehearsal,
  and runtime-canary gates.

Acceptance debt:

- Final signed-artifact run must generate fresh AI-message rows during a real
  live set, not only from saved/source proof sessions.
- Eval artifacts belong under `.planning/eval-runs/` and should stay HOLD unless
  a specific result is intentionally promoted.

### Gold 2 - Session IPC And Desktop Transport

Packets:

- `CODEX_READY-session-ipc-diagnostics-wiring.md`
- `CODEX_READY-ipc-contract-cleanup.md`
- `CODEX_READY-library-staleness-replay-on-connect.md`

Landing posture: LAND IPC schema, generated TypeScript, validator, bus, and
Tauri command changes together.

What it buys:

- Top-level IPC contract remains 72/72 and both-ended.
- Stale library nudges survive late websocket clients.
- Dead `ipc.library.*` websocket assumptions stay corrected; the real library
  product path is Tauri `invoke()`.

Acceptance debt:

- `npm --prefix tauri/ui run check:ipc` rewrites generated files; stage schema
  and generated outputs together.
- Rebuild/re-sign before claiming packaged replay-on-connect behavior.

### Gold 3 - Library, Viber, Cues, And Set Prep

Packets:

- `CODEX_READY-auto-anlz-hot-cue-pipeline.md`
- `CODEX_READY-library-ui-live-read-context.md`
- `CODEX_READY-compact-pill-polish.md`
- `CODEX_READY-viber-library-request-live-guard.md`
- `CODEX_READY-viber-library-freshness-status.md`
- `CODEX_READY-viber-stale-setprep-tool-guard.md`
- `CODEX_READY-library-freshness-watcher-pulse.md`
- `CODEX_READY-stale-library-refresh-action.md`

Landing posture: LAND as the library/Viber usability core, but keep cue-export
folder bridge and real-CLAP eval in HOLD until their gates are real.

What it buys:

- ANLZ/auto cue provenance survives through ingest, cache, suggestions, and
  Viber sections.
- Viber library requests no longer leak live-transition nonsense when live
  context is merely attached as a guard rail.
- Stale library status is source-aware, visible, fail-closed for set-prep, and
  refreshable from Settings.
- Compact pill remains dense without losing grounded detail.

Acceptance debt:

- Prove a real Viber/Codex turn after a library refresh unblocks only when the
  refreshed index is current.
- Cue-export GUI and folder bridge remain HOLD.
- Real CLAP retrieval eval remains HOLD and should not be silently dropped.

### Gold 4 - Learn And Earned Wall

Packets:

- `CODEX_READY-learn-operator-action-bridge.md`
- `CODEX_READY-beatmatch-judge-honesty-boundary.md`
- `CODEX_READY-earned-wall-live-refresh.md`

Landing posture: LAND setup-action bridge and progress refresh; preserve
beatmatch honesty boundary.

What it buys:

- Learn operator actions can cross websocket/Tauri into the practice booth with
  grounded setup prompts.
- Cited coach events can advance and persist Learn progress.
- Earned Wall can refresh from backend progress state.
- Beatmatch "Mastered" stays masked until a production `BEATMATCH_GRADED`
  producer exists.

Acceptance debt:

- Real desktop Earned Wall repaint from live cited controller/audio evidence.
- Real beatmatch producer if Beatmatch Mastered is ever promoted.

### Gold 5 - Speech Truth, Judge, And Mascot

Packets:

- `CODEX_READY-judge-voice-runtime-wire.md`
- `CODEX_READY-no-spoken-fallbacks-live-guard.md`
- `CODEX_READY-audio-vibe-contract-prompt-guard.md`
- `CODEX_READY-emote-mascot-reaction-bridge.md`

Landing posture: LAND as the spoken-truth spine.

What it buys:

- Vibe Judge verdict evidence can enter prompts without stale transition
  narration.
- Unsafe fallback/live-claim text can be retained for artifacts and eval, but
  not voiced.
- Prompt contract tells the co-host what audio can and cannot prove.
- Mascot reaction intents can be emitted without leaking emote tags into speech.

Acceptance debt:

- Live two-deck judged transition artifact.
- Visible Tauri mascot reaction from a live co-host response.
- Final live proof that the co-host does not claim unsupported EQ/fader/deck
  causality.

### Gold 6 - Runtime, Packaging, Signing, And Audio Boot

Packets:

- `CODEX_READY-runtime-memory-clap-readiness.md`
- `CODEX_READY-tauri-sidecar-bundle-freshness-guard.md`
- `CODEX_READY-macos-signing-notarization-flow.md`
- `CODEX_READY-release-binary-verification-hardening.md`
- `CODEX_READY-live-tts-shutdown-hygiene.md`
- `CODEX_READY-desktop-auto-master-16ch-upgrade.md`

Landing posture: LAND package-input guards and runtime cleanup, then rebuild and
re-sign after all source fixes land.

What it buys:

- CLAP/runtime memory readiness is safer.
- Packaging rejects stale or incomplete sidecars.
- macOS signing/notarization flow is proven.
- Binary verifier avoids noisy false positives while preserving strict scans.
- TTS providers close cleanly.
- Explicit BlackHole 16ch routing is respected.

Acceptance debt:

- Current latest signed artifact must be rebuilt after staleness replay and any
  later runtime fixes.
- Final signed app must prove boot, live sidecar, UI connection, normal Quit,
  audible deck audio, and controller motion in the same acceptance pass.

### Gold 7 - Economics, Posture, And Launch Surface

Packets:

- `CODEX_READY-product-posture-docs-cleanup.md`
- `CODEX_READY-live-stack-cost-pricing-model.md`
- `CODEX_HOLD-launch-collateral.md`

Landing posture: LAND product posture and internal cost model; HOLD public
launch collateral until rewritten.

What it buys:

- Public/current docs are closer to monetized reality.
- `vibemix library budget --stack live` gives a reproducible internal bill.
- Unverified vendor rows stay visibly marked.
- Launch collateral is prevented from shipping stale overclaims.

Acceptance debt:

- Rewrite partner/public launch copy against current product truth.
- Do not use the budget model as external pricing copy until billing confirms
  unverified rows.

## Current Landing Shape

Recommended landing batches:

1. Governance and proof docs: Gold 0, plus this map.
2. Observability/eval: Gold 1.
3. IPC/runtime transport: Gold 2.
4. Viber/library/cue/pill: Gold 3.
5. Learn/Earned: Gold 4.
6. Speech truth/Judge/mascot: Gold 5.
7. Runtime/package/signing/audio: Gold 6.
8. Product posture and cost model: Gold 7 LAND pieces only.

Do not land HOLD lanes inside these batches. HOLD lanes are useful evidence or
future product direction, not product-ready source.

## Hard Holds That Must Not Disappear

- FLX4 live acceptance proof artifacts and eval archives.
- Real CLAP retrieval eval gate.
- Eval judge cross-check gate.
- Cue export folder bridge and Serato/cue carrier until dependencies and UI are
  cleanly bundled.
- Mix timing oracle / live drop timing.
- Deck audio controller-weighted master context.
- Local MOSS TTS ONNX runtime spike.
- Launch collateral until copy is product-honest.

## Done Means

The rebuild is not done when packets are written. It is done when:

1. LAND batches are surgically staged and committed with no HOLD bleed.
2. IPC/generated artifacts match their schemas.
3. Python, UI, Rust, package, and release gates pass on the settled tree.
4. Latest source is rebuilt into the signed/notarized artifact.
5. Signed app passes live acceptance with FLX4/audio/controller evidence.
6. Launch collateral either matches truth or remains held.
