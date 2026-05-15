# Phase 31: 4-Layer Mascot Full Additive State Machine - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

The mascot reacts on 4 simultaneous channels — base breathing + emotion + anticipation + reaction — with priority-stacked crossfades. ADDITIVE extension of v2.0 Phase 22 simplified anticipation subset; v2.0 mascot tests port verbatim (Pitfall P47).

**Mapped REQ-IDs (8):** MASCOT-20 (priority-stack manager), MASCOT-21 (crossfade 100ms stagger + p99 frame perf), MASCOT-22 (base layer), MASCOT-23 (emotion layer), MASCOT-24 (reaction layer), MASCOT-25 (v2.0 test name port-verbatim), MASCOT-26 (`additive-layer.ts` 3→4 channels), MASCOT-27 (GLB total ≤25 MB CI gate).

**In scope:**
- Priority-stack manager `tauri/ui/src/mascot/priority-stack.ts`: 4 channels (Base 50, Emotion 60, Anticipation 70 [v2.0 verbatim], Reaction 80) + cancel-priority 999.
- Crossfade policy `crossfade-policy.ts`: 100ms stagger across simultaneous transitions; vitest perf p99 < 22ms (Pitfall P62 single-mixer race).
- Base layer: idle breathing + sway loop, priority 50, never canceled.
- Emotion layer: 4-state {neutral, focused, hyped, concerned} driven by MusicState.active_genre + energy_band; ws_bus payload `emotion` field.
- Reaction layer: fires on cited `[emote:*]` tags from Gemini response text; priority 80, cancel-aware; ws_bus payload `reaction_intent` field.
- `additive-layer.ts` extends 3 → 4 channels per v2.0 marker comment; SkeletonHelper visual regression.
- GLB total budget ≤ 25 MB on CI gate (Pitfall P52 sub-budget under 350 MB hard cap).
- v2.0 priority-70 + 2.5s timeout + cancel-aware + linter-strip-aware tests port verbatim (Pitfall P47 evidence).

**Out of scope:**
- Real new GLB animation content (Phase 35 ASSETS-03 owns real-GLB execution — Phase 31 uses placeholders or v2.0-shipped GLBs).
- Mascot model replacement.
- User-generated mascots (`/hatch` v2.2 backlog per memory).
- Mascot interaction with cursor/keyboard.
- Sound effects synced to mascot state.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 31 verbatim success criteria
- REQUIREMENTS.md MASCOT-20..27
- Pitfalls P47 (additive-only, NO clean-slate rewrite), P62 (single-mixer race), P72 (cancel-aware mid-anticipation)
- v2.0 Phase 22 anticipation rig (shipped) — port verbatim
- Phase 30 GenreRouter (just shipped) — emotion layer reads MusicState.active_genre
- Memory `project_mascot_as_vtuber_personality_surface` — single VTuber-style 3D character, mood variation on same rig
- Memory `project_visual_direction_cdj_whisper` — CDJ Whisper, restraint
- Memory `frontend-enforcement` skill — frontend-design discipline

### Priority-stack manager (MASCOT-20)
- Class `PriorityStack` in `tauri/ui/src/mascot/priority-stack.ts`.
- 4 named channels: `base` (50), `emotion` (60), `anticipation` (70), `reaction` (80).
- Cancel-priority sentinel `999` flushes the queue (P72 mitigation).
- API: `play(layer, clip, opts)` / `cancel(layer)` / `cancel_all()` / `resolve()` → returns active clip per channel.
- Internal queue per channel; FIFO.

### Crossfade policy (MASCOT-21 / P62)
- `crossfade-policy.ts` provides `transition(from, to)` returning `{stagger_ms, fade_in_ms, fade_out_ms}`.
- 100ms stagger across simultaneous transitions — prevents Three.js single-mixer race (P62).
- Default crossfade: 200ms fade-in + 150ms fade-out.
- Cancel-priority 999: instant cut, no fade.
- Vitest perf test holds frame budget p99 < 22ms.

### Base layer (MASCOT-22)
- Idle breathing + sway loop. Priority 50. Never canceled by `cancel()`.
- File: `tauri/ui/src/mascot/layers/base.ts`.
- Drives `additive-layer.ts` channel 0.
- Even cancel-priority 999 does NOT stop base (base = always-on heartbeat).

### Emotion layer (MASCOT-23)
- 4 states: `neutral` (default), `focused` (techno/house, energy_band=mid), `hyped` (any genre, energy_band=high), `concerned` (low energy + long phase).
- Driven by ws_bus `emotion` field (new payload extension).
- File: `tauri/ui/src/mascot/layers/emotion.ts`.
- Backend: `src/vibemix/state/emotion_router.py` reads MusicState.active_genre + energy_band → emits emotion.
- State transitions via crossfade policy. Holds state until music state shifts.

### Reaction layer (MASCOT-24)
- Fires on `[emote:*]` tags in Gemini response. Tags like `[emote:wave]`, `[emote:point_left]`, etc.
- Parser: `parse_emote_tags(text) -> list[reaction_intent]` in `src/vibemix/agent/emote_parser.py`.
- ws_bus payload `reaction_intent: str | null`.
- File: `tauri/ui/src/mascot/layers/reaction.ts`.
- Priority 80, cancel-aware (mid-reaction cancellable if higher priority fires).
- 2.5s default timeout (matches v2.0 priority-70 anticipation contract).

### v2.0 test port-verbatim (MASCOT-25 / P47)
- All v2.0 tests in `tauri/ui/src/mascot/__tests__/` keep exact same test names.
- New layer = ADDITIVE EXTENSION. No deletes, no renames.
- Test invariants preserved:
  - priority-70 + 2.5s timeout + cancel-aware + linter-strip-aware
- Pre-flight grep: assert all v2.0 test name strings appear in new test files.

### `additive-layer.ts` 3→4 (MASCOT-26)
- Read v2.0 marker comment in `additive-layer.ts` (placed during Phase 22 — `// PHASE-22: 3-channel today, 4-channel hook in Phase 31`).
- Extend `channels` array length 3 → 4.
- SkeletonHelper visual regression test snapshot rebuilt (Three.js).
- ws_bus `mascot_state` payload extended additively (new fields, no breaking changes).

### GLB budget (MASCOT-27 / P52)
- CI gate: `scripts/check_mascot_glb_size.sh` sums all `.glb` under `tauri/ui/public/mascot/` → asserts ≤ 25 MB.
- Run in CI on every PR.
- Today: v2.0 placeholders + anticipation rig ~ 18 MB. Phase 31 stays within budget (mostly TS code + ws_bus schema, no new GLB).
- Real GLBs land in Phase 35 ASSETS-03 — that phase respects the budget too.

### ws_bus payload schema
- Additive extension to existing mascot schema:
  - `emotion: "neutral" | "focused" | "hyped" | "concerned" | null` (new)
  - `reaction_intent: string | null` (new)
  - Other fields unchanged.
- `messages.schema.json` Draft-07 versioned via `mascot.v2` schema bump (additive-only — Pitfall P82-style).

### Test discipline
- Vitest perf test: simulate 100 simultaneous layer transitions, measure p99 frame time, assert < 22ms.
- Vitest SkeletonHelper regression: snapshot before/after.
- v2.0 test name preservation grep.
- Cancel-mid-anticipation test (P72): start anticipation, fire reaction priority 80, assert anticipation cancels cleanly.

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 22 (shipped):**
  - `tauri/ui/src/mascot/anticipation-layer.ts` — anticipation rig
  - `tauri/ui/src/mascot/additive-layer.ts` — 3-channel multiplexer with PHASE-22 marker
  - `tauri/ui/src/mascot/__tests__/` — verbatim test names to preserve
  - ws_bus mascot schema
- **Phase 30 (just shipped):**
  - `src/vibemix/detectors/genre_router.py` — MappingProxyType immutable mapping
  - MusicState exposes `active_genre` (`hard_tek` | `techno` | `house` | `unknown`).
- **Three.js + AnimationMixer** — v2.0 single-mixer pattern; P62 race risk on simultaneous transitions.
- **Tauri vanilla TS frontend convention** (memory).
- **`frontend-enforcement` skill** — loaded automatically by GSD agents touching UI; enforces 20/80 + textured material + no AI slop.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **Additive ONLY, never clean-slate rewrite** (P47): any clean-slate refactor proposal = automatic reject.
- **Single mascot character** (memory): no `/hatch` user-gen in v2.1; mood/state variation on same rig.
- **CDJ Whisper visual direction** (memory): restraint applies to mascot too — no neon, no over-animation.
- **100ms stagger is the magic number** (P62): empirically validated in v2.0 Phase 22.
- **2.5s timeout** is v2.0-derived (priority-70 contract) — extend to priority-80 too.
- **No GLB content additions in Phase 31** — pure logic/state layer work.

</specifics>

<deferred>
## Deferred Ideas

- **Real anticipation GLBs** — Phase 35 ASSETS-03.
- **User-generated mascots (`/hatch`)** — v2.2 backlog (memory).
- **Mascot interaction with cursor/keyboard** — out of scope.
- **Sound effects synced to mascot state** — out of scope.
- **Multi-mascot ensemble** — out of scope, single character locked.
- **Emotion learned from session data** — Phase 32 DJ profile may inform, but emotion stays rule-based here.

</deferred>
