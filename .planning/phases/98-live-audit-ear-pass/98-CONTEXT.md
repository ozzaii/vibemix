# Phase 98: Live Audit + Ear-Pass + rc1 Regression Smoke — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted per `/gsd-autonomous fully`); ~80% KAAN-ACTION discharge per ROADMAP.

<domain>
## Phase Boundary

P98 ships the v9.0 milestone audit + ear-pass hand-off. Mostly KAAN-ACTION discharge — Kaan walks all 3 courses on real DDJ-FLX4 hardware, records the walk, signs off (or surfaces real-hardware regressions). Plus a hard engineering gate: rc1 standalone sidecar smoke MUST PASS unregressed.

**4 deliverables:**
1. **AUDIT-01** — 3 Kaan-walk session recordings (one per course); ≥90 min total; saved to `docs/learn/2026-XX-kaan-walk.webm`.
2. **AUDIT-02** — `.planning/milestones/v9.0-MILESTONE-AUDIT.md` doc: 72-REQ-ID satisfaction matrix · 4 cardinal-invariant pin re-runs · KAAN-ACTION queue · Pitfalls §P1-P17 coverage · acid-test per-phase self-check.
3. **AUDIT-03** — Francesco/lawyer sight-check on rendered controllers + disclaimer + Mixxx-precedent posture. KAAN-ACTION `§LEARN-LEGAL-DISCLAIMER`.
4. **AUDIT-04** — rc1 standalone sidecar smoke regression check (`scripts/smoke/sidecar_bundle_smoke.sh` or equivalent — write if missing). Includes mascot envelope namespace audit (`learn.*` additions don't break mascot bus).

**REQ-IDs:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04.

</domain>

<decisions>
## Implementation Decisions

### AUDIT-01: Kaan walk recordings

- **KAAN-ACTION** — can't self-verify. Engineering side: ensure the Learn window + main app are stable end-to-end so Kaan's walk runs clean.
- Recording host: Kaan's own screencast tool (QuickTime / OBS / etc.). Engineering NOT building a recording infrastructure.
- Save targets: `docs/learn/2026-XX-kaan-walk-course-1.webm`, `-course-2.webm`, `-course-3.webm`.

### AUDIT-02: v9.0-MILESTONE-AUDIT.md doc

- **Engineering CAN draft this autonomously** — read all 8 phase SUMMARY.md files + REQUIREMENTS.md + ROADMAP.md + research/SUMMARY.md + KAAN-ACTION queue + Pitfalls list.
- **Doc structure:**
  - 72-REQ-ID satisfaction matrix (table per category: RENDER / LESSON / TONE / CURR-1.x / CURR-2.x / CURR-3.x / EXEMPLAR / ONBOARD / AUDIT)
  - 4 cardinal invariants — pin status per phase
  - KAAN-ACTION queue — every parked item across all phases
  - Pitfalls §P1-P17 — coverage status (CI gate? doc-only? defer?)
  - Acid test per phase: "Does P9X deliver a working slice of the BEGINNER module WITHOUT adding new AI provider / ws port / IPC envelope family / DSP library / content beyond 36 lessons / community surface?"
  - Final disposition: PASS (engineering complete; ear-pass + lawyer-pass pending) OR FAIL with specific blockers.

### AUDIT-03: Francesco/lawyer sight-check

- **KAAN-ACTION** — Kaan/Francesco's external lawyer review. Engineering ensures:
  - All 11 controller SVGs are stylized schematics (no Pioneer logo / orange / faceplate photos — CI gates from P91 + P93 stay green)
  - Disclaimer copy present in app footer + repo README (P97 RENDER-08)
  - Mixxx-precedent posture documented
- Surface as `§LEARN-LEGAL-DISCLAIMER` KAAN-ACTION.

### AUDIT-04: rc1 standalone sidecar smoke

- **Engineering responsibility.**
- Write or update `scripts/smoke/sidecar_bundle_smoke.sh` (if missing): builds the rc1 bundle + verifies standalone launchd-spawn of `vibemix-core --session` and `vibemix-core --wizard` works.
- Includes envelope namespace audit: `learn.*` additions don't break mascot bus (existing test `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` from P92 stays green).
- Pin: `patch_livekit_agents_init.py` + `sidecar.rs` std::process + spec blocklist still working.
- Optional: opportunistically fix `tests/sidecar/test_build_sidecar_rename.py` failures from P93 (flagged as pre-existing baseline drift) if they block the smoke test.

### Claude's Discretion

- Whether to draft the milestone audit doc immediately (engineering CAN) or wait for Kaan ear-passes (so the doc reflects PASS status).
- Whether to write the sidecar smoke script from scratch or extend existing infrastructure.
- How comprehensive the 72-REQ-ID matrix needs to be (every ID listed vs categorical summary).

</decisions>

<code_context>
## Existing Code Insights

- `.planning/phases/91..97/91-SUMMARY.md..` — engineering provenance for the audit doc
- `.planning/REQUIREMENTS.md` — 72 REQ-IDs to enumerate
- `.planning/research/SUMMARY.md` — 14 LOCKED axes for acid test
- `.planning/research/PITFALLS.md` — §P1-P17 to enumerate
- `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` — exists from P92
- `tests/sidecar/test_build_sidecar_rename.py` — pre-existing baseline drift from P93 SUMMARY

</code_context>

<deferred>
## Deferred Ideas

- Kaan-walk recordings (KAAN-ACTION)
- Francesco/lawyer sight-check (KAAN-ACTION)
- Public ship (post-milestone-audit)

</deferred>
