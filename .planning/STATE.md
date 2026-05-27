---
gsd_state_version: 1.0
milestone: product-sweep
milestone_name: Product Sweep / Package Readiness
status: active
last_updated: "2026-05-27T13:56:00+03:00"
last_activity: "2026-05-27 - product sweep verified first-run CLAP setup, local Codex/Viber truth, and archived stale v7/v8.1/v8.2 phase detail"
progress:
  mode: sweep
  product_truth: current
  release_closed: false
---

# vibemix - State

## Current Position

v8.2 "Set Builder" is code-shipped: energy, discovery, sequencing, Rekordbox export,
Viber set-prep/build-set, and the Library UI surface are wired. The active work is no
longer feature planning; it is product sweep, packaging rehearsal, stale-doc cleanup,
and release-gate discharge.

Phase 88 (UI) is now wired into the Vibe Engine Library surface.
Next: packaged fresh-install/updater rehearsal, signed/notarized package proof,
Windows install proof, and human signoff gates.

Do not claim the release is friend-ready until signed/notarized macOS artifacts,
Windows fresh-machine install proof, real Discord invite/link cleanup, and the remaining
human signoff gates are complete.

## Current Product Truth

- Library search, ingest, curation, and retrieval embeddings use local CLAP ONNX through
  the current embedder factory. Full-precision fp32 ONNX is the default quality path;
  fp16/q8 are optimization candidates only after parity checks.
- Viber set-prep/chat/build-set uses local Codex for the current demo/test path. The
  removed Gemini library agent is not a product fallback.
- Gemini remains scoped to the separate live co-host/TTS brain where configuration
  resolves it through the model router. Do not hardcode model names.
- The live UI socket is `127.0.0.1:8765`; debrief uses `127.0.0.1:8766`.
- Only state refresh writes `MusicState`. AI reactions must resolve through
  `EvidenceRegistry`; live audio is authoritative.

## Verified In This Sweep

- `AGENTS.md` exists as the concise contributor guide and matches the current
  `uv`, `npm --prefix`, and Cargo-manifest workflow.
- Library/Viber Gemini agent code and YouTube ingest tooling were removed from the
  product path; Codex chat smoke returned valid local JSON with no Gemini/proxy env.
- The Library UI opens chat-first and the Tauri bridge routes `library chat` through the
  Codex backend. Desktop and mobile Playwright screenshots completed without page or
  console errors.
- Fresh CLAP model setup was proven from source and from the frozen PyInstaller sidecar:
  all six fp32 ONNX assets verified by size/SHA and produced finite 512d normalized text
  and audio embeddings.
- Local unsigned macOS DMG/updater packaging smoke passed. Pretag still reports release
  blockers listed below.

## Release Blockers

- Phase 16 / Phase 17 human gates are not closed.
- README Discord placeholder/link and real invite remain unresolved.
- GitHub Actions signing/upload secrets are incomplete.
- macOS signed/notarized DMG and signed updater rehearsal are not closed.
- Windows fresh-machine install proof is not closed.

## Active Sources

- `.planning/research/CODEX-full-product-sweep-map.md` - live sweep evidence and
  package/DSP verdict.
- `.planning/ROADMAP.md` and `.planning/PROJECT.md` - current milestone/product view.
- `.planning/phases/v8.2-STATUS.md` - compact v8.2 shipped status.
- `docs/clap-engine.md` and `docs/codex-agent.md` - current local model/agent paths.
- `CLAUDE.md` - repository operating constraints for agent sessions.

## Archived This Sweep

- Stale active notes: `.planning/archive/2026-05-27-stale-active-notes/`.
- Historical v7/v8.0/v8.1 phase detail:
  `.planning/archive/2026-05-27-v7-v8-1-phase-detail/`.
- v8.2 detailed phase folders and Phase 89/90 stale in-flight notes:
  `.planning/archive/2026-05-27-v8-2-active-phase-detail/`.
- Pre-sweep state snapshot:
  `.planning/archive/2026-05-27-state-snapshot/STATE-pre-product-sweep.md`.

## Audit Trail

- **Phase 16 ear-test memory override - RETIRED.** The v2.1 P85 autonomous-only
  override is retired; see `.planning/decisions/P85-OVERRIDE-RETIRED.md`. The current
  replacement is the hybrid hallucination gate plus human ear-test lane.
- Historical pre-CLAP embedding docs are retained only in archived research and
  phase-detail folders. Current library intelligence is local CLAP ONNX.
