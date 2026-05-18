# DEP-OPP-01 — Adopt OBS browser-source as docs-only mascot integration

**Status:** Accepted
**Date:** 2026-05-18
**Phase:** 48 — New-Dep + Integration Opportunity Scan
**Requirement:** OPP-06
**Scan row:** `docs/dep-opportunities/2026-05-scan.md` § DEP-OPP-01
**YAML row:** `scripts/audit/dep_ratings.yaml::opportunity_evaluations[id=DEP-OPP-01]`

## Context

The v3.1 opportunity scan (Phase 48) identified one candidate that lands in v3.1 as a Green-adopt outcome: routing the existing Tauri webview mascot canvas into OBS Studio via its built-in browser-source plugin. Streamers and content creators commonly composite a virtual avatar overlay on top of camera feeds and screen captures — vibemix already renders that mascot, and OBS already knows how to capture a local webview. The integration is a documentation problem, not an engineering problem.

The v3.0 baseline ships:

- A Tauri webview hosting the mascot scene (Three.js + GLB clips), served alongside the main app surface.
- A local WebSocket server bound to `127.0.0.1:8765` (the mascot bus) that broadcasts music / voice / mic levels at 30 Hz.
- A four-layer additive state machine driving 23 Mixamo-retargeted GLB clips per Phase 47.

OBS Studio's browser-source plugin loads a URL inside a Chromium Embedded Framework instance and renders the page as an overlay layer in any OBS scene. Pointing it at the existing mascot route lets the captured canvas land in the OBS scene without any vibemix-side code.

## Decision

Adopt OBS browser-source as a **documentation-only** integration path. No new runtime code, no new IPC wrappers, no new Tauri webview routes. Ship two documents:

- `docs/integrations/obs-browser-source.md` — step-by-step OBS Studio setup with troubleshooting.
- A cross-link in `README.md` under the Streaming integrations anchor so streamers discover the path during first-run scan.

The mascot WS bus stays bound to `127.0.0.1` — the OBS integration does NOT expose the bus to the network. OBS Studio and vibemix are expected to run on the same machine.

## Rationale

1. **Zero install-time cost.** No new package dependency, no new bundle weight, no new permission prompt at first launch. Phase 49's installer companion already pulls BlackHole / VB-CABLE; this adoption adds nothing to that chain.
2. **Zero runtime risk.** The mascot bus + Tauri webview are already on the stable production path per v3.0 ship. Adding documentation cannot regress that surface.
3. **High audience value.** vibemix's mascot is the visual personality surface per memory `project_mascot_as_vtuber_personality_surface`; making it landable in OBS scenes is exactly the kind of multiplier streamers ask for.
4. **No new IPC wrappers.** The 38-wrapper IPC schema is frozen per v3.1 invariants; an integration that needs zero IPC fits cleanly.
5. **Reversible.** Removing this adoption means deleting two markdown files plus a README paragraph — no code revert, no migration.

## Integration plan

1. Streamer installs vibemix per Phase 49 installer chain.
2. vibemix's webview surfaces the mascot scene at the v3.0 baseline route (the same route the standalone app uses internally).
3. Streamer adds a new OBS source of type "Browser" with the URL pointing to the local mascot route and a transparent background.
4. The mascot canvas renders inside the OBS scene as an alpha-compositable overlay.
5. Audio cue routing into vibemix continues to drive the same mascot per the existing mascot-bus contract.

## Rollback path

Remove three artifacts:

- Delete `docs/integrations/obs-browser-source.md`.
- Delete the OBS cross-link paragraph in `README.md`.
- Delete this ADR file.

Optionally flip the YAML row's `rating` from `green-adopt` to `yellow-defer` and add a `rejected_constraints[]` entry citing the rollback rationale. No code revert is needed.

## Consequences

Positive:

- Streamers gain a first-class avatar-in-OBS path with zero install friction.
- vibemix's mascot becomes the canonical visual hook for vibemix screencasts and tutorials.

Negative / accepted risk:

- First-time OBS users may need extra guidance on browser-source aspect ratio + alpha channel. The integration doc covers the common pitfalls.
- If OBS Studio changes the browser-source plugin's URL scheme or revokes localhost access, the doc needs an update; this is upstream-OBS risk, not vibemix risk.

## References

- `.planning/REQUIREMENTS.md` § OPP-06
- `.planning/ROADMAP.md` § Phase 48
- `.planning/phases/48-new-dep-integration-opportunity-scan/48-CONTEXT.md` § Decision 6
- `docs/dep-opportunities/2026-05-scan.md` § DEP-OPP-01
- `docs/integrations/obs-browser-source.md`
- Memory: `project_mascot_as_vtuber_personality_surface`
