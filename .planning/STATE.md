---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: 12-Factor Hardening
status: executing
last_updated: "2026-05-28T12:55:23.503Z"
last_activity: 2026-05-28
progress:
  total_phases: 11
  completed_phases: 0
  total_plans: 8
  completed_plans: 2
  percent: 0
---

# vibemix — State

## Current Position

Phase: 99 (HARDEN-RETRY — Viber Tool-Retry Policy (Factor 9)) — EXECUTING
Plan: 3 of 8
Status: Ready to execute
Last activity: 2026-05-28

## Milestone Reference

See: `.planning/PROJECT.md` § Current Milestone: v10.0 "12-Factor Hardening" (locked audit verdict + 3-phase split + acid tests + KAAN-ACTION queue)
See: `.planning/ROADMAP.md` § v10.0 "12-Factor Hardening" — 🔵 PLANNING 2026-05-28 (3 phases P99-P101 · full Phase Details)
See: `.planning/REQUIREMENTS.md` (21 v10.0 REQ-IDs across 3 categories: HARDEN-RETRY · HARDEN-CLARIFY · HARDEN-CONTRACT)

**Goal:** Close three concrete partial-pass items from today's humanlayer/12-factor-agents audit (2026-05-28). vibemix already scores 5 strong-pass + 2 pass + 3 partial + 2 N/A on the 12 factors — the live co-host's streaming pipeline is fundamentally NOT a tool-call loop and stays that way (Factor 10 — don't force the wrong abstraction). This milestone closes the three partials on the **Viber** side + writes the prompt-composition contract for the live side. **No architecture rewrite.**

**Phase numbering:** continues from v9.0's last phase (P98) — milestone runs **P99 → P101** (no reset).

## Phase Spine (P99-P101)

```
P99 (HARDEN-RETRY — Viber Tool-Retry Policy) ──► P100 (HARDEN-CLARIFY — Viber RequestClarification)
                                                          │
                                                          │   shares stop_reason payload seam from P99
                                                          ▼
                                                  (Phase B → C independent; sequential ordering only
                                                   so P101's grep verification sees the
                                                   post-hardening Viber tool surface)
                                                          │
                                                          ▼
                                                  P101 (HARDEN-CONTRACT — Prompt Composition Doc)
                                                  (doc-only, independent, no functional dep)
```

`P99 → P100` strict (P100 consumes the shared `stop_reason` payload seam from P99). `P101` is doc-only and functionally independent; listed sequentially after P99/P100 so its grep verification at write-time sees `tool_starvation` + `clarification_needed` as named sibling stop_reasons on the Viber side.

## Active Sources

- `.planning/PROJECT.md` § Current Milestone — locked audit verdict + 3-phase split + acid tests + KAAN-ACTION queue
- `.planning/ROADMAP.md` § v10.0 — 3 phases (P99-P101) with Phase Details + Success Criteria + file scopes + Cardinal invariants
- `.planning/REQUIREMENTS.md` — 21 v10.0 REQ-IDs (HARDEN-RETRY-01..07 · HARDEN-CLARIFY-01..07 · HARDEN-CONTRACT-01..07) · 100% traceability
- Today's 12-factor-agents audit summary (in PROJECT.md § Current Milestone — IS the research equivalent; no separate research phase)

## Disjointness Contract (parallel-session discipline)

v10.0 island = `src/vibemix/library/` + NEW `docs/PROMPT-COMPOSITION.md` + (one-line) `CLAUDE.md` "Architecture" pointer. **Never touches:**

- `src/vibemix/__main__.py` BEYOND the CLI dispatch lines for `library curate` / `library build-set` exit codes (P99/P100). The live session-loop path and `__main__.py:1353 turn_handling` are owned by the **LiveKit-upgrade handoff** (separate session, not yet committed — see memory `project_streaming_pipe_speedfix_livekit_upgrade_handoff`).
- `src/vibemix/agent/` (live co-host streaming pipeline is fundamentally NOT a tool-call loop — Factor 10 / wrong-abstraction guard).
- `src/vibemix/intel/` (pure musical-intelligence primitives, separate island).
- `tauri/ui/*` (owned by the **frontend wiring handoff** — separate session — see memory `project_frontend_wiring_handoff`).

Surgical commits with named paths, never `git add -A`. Per `feedback_concurrent_sessions_one_tree`.

## Anti-Creep Acid Test (v10.0, LOCKED)

> *"Does this phase close one of the three audit partials (Factor 9 retry policy / Factor 7 clarification / Factor 3 prompt-composition contract) — without growing the surface, introducing a new AI provider / managed-memory framework / ws port / IPC envelope / heavy dep, touching `src/vibemix/__main__.py` / `src/vibemix/agent/` / `src/vibemix/intel/` / `tauri/ui/*`, or relaxing any of the four cardinal invariants? Does it leave the live co-host streaming pipeline untouched?"*

If a phase doesn't pass → defer to HARDEN-FUTURE or out of scope (see REQUIREMENTS.md § Out of Scope + § HARDEN-FUTURE).

## Concurrent Work (other sessions)

Two parallel handoffs active on `live-tuning-or-brain` (this working tree):

1. **LiveKit-upgrade handoff** — `src/vibemix/__main__.py:1353` `turn_handling={"interruption":{"enabled":False,"resume_false_interruption":False}}` override + livekit-agents 1.5.8→1.5.14 bump. Not yet committed. Owns `__main__.py` live session path.
2. **Frontend wiring handoff** — `tauri/ui/*` rocker visual-sync (the real "no buttons work" root cause), status-tick emit, pill hover-peek port. Separate session.

Plus the **Codex sessions on shared rc1 product-sweep** (additive new-file work; named-path commits only).

v10.0 island is disjoint from all three. Commit by named paths only, never `git add -A`. Sibling-session uncommitted edits in the worktree (M-flagged files in git status) belong to other sessions — leave them alone unless they are explicitly in scope.

## Hard Rules (carried)

- **Privacy** — all OZ/Hermes/LM-Studio off-limits paths (see CLAUDE.md) — per-turn permission expires at turn end. No exceptions.
- **Honest green** — every code-touching phase (P99, P100) ships with failing-then-passing tests on CURRENT SOURCE per `feedback_stale_sidecar_verify_current_source` (NEVER the bundled sidecar — that path lags edited `src/`). P101 is doc-only and verified by `grep` resolving file:line references against current source at write-time.
- **Reuse-first** — no new AI provider, no new ws ports, no new IPC envelopes, no new heavy deps, no new managed-memory framework. The `library/` subpackage primitives are all the seams we need.
- **All 4 cardinal invariants hold by ADDITIVE design** — Invariant #1 single-writer (P99 counter confined to `LibraryToolset` instance, AST-gated); Invariant #2 citation-grounding (P99 counter is additive telemetry, never relaxes `seen`-set; P100 `request_clarification` has no `track_id` surface, AST-gated); Invariant #3 N/A (live co-host untouched); Invariant #4 N/A (no new ws traffic — Phase A/B operate on existing CLI + MCP STDIO + Telegram long-poll surfaces).
- **`gsd-autonomous fully`** — default-YES on grey-area; blockers (Kaan's ear-pass on `tool_starvation` copy + clarification-prompt tone in real Codex output) ride forward to KAAN-ACTION queue. Only privacy hard rule + destructive risk pause.

## v10.0 KAAN-ACTION Queue (parked at milestone start, discharged at close)

**BLOCKING (must resolve before v10.0 public ship / GitHub release):**

- `§HARDEN-PHASE-A-EAR-PASS` (P99) — ear-pass on the `tool_starvation` user-facing message. Does it sound like a real friend telling you the library is empty, or like generic error text? Anti-slop release gate.
- `§HARDEN-PHASE-B-CLARIFICATION-TONE` (P100) — ear-pass on Codex's actual clarification prompts in the wild (theme-ambiguity test corpus on funded key). Do the LLM's question framings stay on-brand vs sound like a robot survey?

**NON-BLOCKING (ride forward):**

- none at milestone start; P101 is doc-only, no ear-pass surface.

## Carried-Forward KAAN-ACTION (from prior milestones)

- v9.0 §LEARN-FULL-MILESTONE-EAR-PASS (3-course ear-pass) + §LEARN-LEGAL-DISCLAIMER (Francesco/lawyer sight-check) + §LEARN-EAR-COURSE-{1,2,3} + §LEARN-CONTROLLER-EAR (9 non-FLX4) + §LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE + §LEARN-CLAP-FIRST-RUN-UX + §LEARN-ONBOARD-EAR-PASS
- rc1 ear-pass + signed-release A/B/C decision (`.planning/handoffs/2026-05-27-session-end.md`)
- v8.2 UI-02 funded-key ear-pass (PROJECT.md)
- v8.0 §GH-BILLING / §SHIP-V4 / §V7-LIVE

## Next Action

```
/gsd:plan-phase 99
```

Phase 99 = HARDEN-RETRY — Viber Tool-Retry Policy (Factor 9 closure). Files: `src/vibemix/library/toolset.py` + `src/vibemix/library/codex_curate.py` + CLI dispatch lines in `src/vibemix/__main__.py`. Tests under `tests/library/` only. HIGHEST ROI — go first.

## Operator Next Steps

- `/gsd:plan-phase 99` to decompose P99 into executable plans.
- After P99 lands → `/gsd:plan-phase 100` (depends on P99's `stop_reason` payload seam).
- P101 can be planned in parallel with P99/P100 at any time (doc-only, no functional dependency), but listed sequentially so its grep verification at write-time sees `tool_starvation` + `clarification_needed` as named sibling stop_reasons.
