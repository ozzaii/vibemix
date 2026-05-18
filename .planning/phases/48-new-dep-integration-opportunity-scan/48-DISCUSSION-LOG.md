# Phase 48 Discussion Log

**Phase:** 48 — New-Dep + Integration Opportunity Scan
**Mode:** `--auto` (gsd-autonomous fully)
**Date:** 2026-05-18

## Context

All requirements locked by `.planning/REQUIREMENTS.md` § OPP (OPP-01..06) and roadmap success criteria. Discussion is implementation-mechanics only — WHAT to build is fully spec-locked.

Research baseline is unusually thorough: `.planning/research/STACK.md` § Bucket 3 already contains a candidate-by-candidate verdict table. The discussion mostly RATIFIES the research-shipped verdict structure and decides the schema-extension + sibling-script + ADR mechanics around it.

## Areas Auto-Selected (all)

Per `--auto` mode, all gray areas were auto-selected. 10 decisions captured covering: scan artifact location, schema extension shape, auto-Red enforcement engine, anti-slop sibling-script mechanic, OBS browser-source ADR plan, Yellow-defer carry-forward pattern, expected Red set, Phase 49 hand-off contract.

## Auto-Selected Decisions

1. **Single scan artifact** `docs/dep-opportunities/2026-05-scan.md` (per ARCHITECTURE.md § 6 contract) — NOT a multi-file dir tree.
2. **`dep_ratings.yaml` `opportunity_evaluations` block** appended as new top-level key — Phase 46 ecosystem maps untouched; backward-compatible additive.
3. **Schema extension** adds `opportunity_evaluations` to `required`; new enums for `rating` (4-color) + `category` + `integration_surface`.
4. **Sibling anti-slop checker** at `scripts/audit/check_no_slop_opp.py` (imports `AI_SLOP_BLOCKLIST` from `scripts.launch.check_no_ai_slop`) — does NOT widen the contract-pinned shared script's target paths. Phase 47-resume sibling-script pattern.
5. **`scripts/audit/scan_opportunities.py` is validator, NOT generator** — auto-Red enforcement + md↔yaml parity gate. Scan markdown itself is human-curated from research baseline.
6. **OBS browser-source is the one expected Green-adopt** — ADR `DEP-OPP-01-obs-browser-source.md` + `docs/integrations/obs-browser-source.md` + README cross-link. Zero new runtime code (Tauri webview port 8765 already serves).
7. **Yellow-defer stubs** at `.planning/research/v3-buckets/v3.x-<slug>.md` per Yellow row — 8 expected (Mixxx OSC / controller transpiler / pyrekordbox depth / Beat This! / Voicemeeter Banana / controller library expansion / macOS 26+ / Win11 24H2 WASAPI).
8. **Auto-Red set** explicit + verbatim memory quotes per row (CLAP / MERT / OpenL3 / OpenAI direct / Anthropic / Demucs / Spleeter / DAW APIs / Linux-only / ProDJ Link / Dante Via / Loopback / Soundflower / Auto-Rig Pro).
9. **Phase 49 hand-off** — `opportunity_evaluations` is the canonical green-set. Companion driver fetch (BlackHole / VB-CABLE) is Phase 49-internal; Phase 48 explicitly does NOT pre-rate driver-level deps.
10. **CI surface** — extend `dep-audit.yml` (or sibling `opp-audit.yml`) with a new job; planner picks per Phase 46 workflow shape.

## Deferred Ideas

All v3.x candidates (Mixxx OSC, Beat This!, controller library expansion, etc.) carry forward to `.planning/research/v3-buckets/` as Yellow-defer stubs per OPP-05. None escalated to v3.1 scope.

## Notes

- Discussion completed in single auto-mode pass per `workflows/discuss-phase/modes/auto.md` MAX_PASSES discipline.
- No AskUserQuestion calls (auto mode replaces user prompts with recommended-default selection).
- Anti-stall discipline pre-baked into CONTEXT.md `implementation_constraints` — sibling-script for shared-CI extensions, per-plan stall budget, worktree Step-0 invariant.
