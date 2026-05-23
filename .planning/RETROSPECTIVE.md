# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v6.0 — The Memory Turn

**Shipped:** 2026-05-23 (tech_debt accepted)
**Phases:** 4 (63–66) | **Plans:** 12 | **Sessions:** ~6 (3 days, 2026-05-22 → 2026-05-23)

### What Was Built

- **Memory Store (P63)** — Local per-install `memory.db` (sqlite-vec primary, NumpyStore fallback) + ~50-line `MemoryStore` wrapper, cloned from shipped `library/` primitives with **zero net-new dependencies**. Mac/Win bit-identical `cosine_topk` parity. Path-traversal-defended atomic `delete_session` cascade + oldest-session-first whole-session retention sweep + boot `reconcile_orphans`.
- **Session Ingest (P64)** — Off-hot-path post-session batch + boot sweep turning each session's existing `events.jsonl`+evidence+`ai_text` into deterministic TEXT "reaction moment" records. ONE v1 kind: `coach_line` (emitted ai_text + preceding-event context). NO audio embedding, NO LLM-extraction — both CI-guarded. Idempotent re-ingest via signature-keyed embed cache + `memory_ingested` marker.
- **Memory Retrieval Seam (P65) — ANTI-SLOP RELEASE GATE** — New existence-only `recall` evidence source flows through the existing `CitationLinter` with **zero new linter code** (à la P59 `key:`). Gated PAST-tense `recall[…]` block in `evidence_line` — cold/empty-memory golden **byte-identical** to v5.0 baseline. Anti-poisoning by construction: ~0.7 similarity floor, top-k 2–3 cap, event-gated, current-session excluded, fabricated `[recall:<id>]` strips the whole turn (register-before-snapshot at `dj_cohost.py:892`).
- **Visible Copilot Move (P66)** — Linter-grounded transition-shape callback + vocabulary/register callback. Recall chip rides existing `cohost-reaction` IPC envelope (no new socket). 120s cooldown discipline with arm-on-emit at both bus + bus-less paths. Static anti-feature gate (`tests/repo/test_no_recall_antifeatures.py`) catches 20 forbidden phrases. Ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass.

### What Worked

- **Convergent multi-agent research.** 4 parallel researchers independently produced the same four-phase spine (STORE → INGEST → RETRIEVE → COPILOT MOVE) and the same "WIRING/REUSE not greenfield" framing. Unanimous convergence meant zero replan churn — the dependency-correct critical path was clear before P63 started.
- **Schema-mirror lockstep tests.** RECALL-01's silent-poisoning-hole was caught by a lockstep test that pinned sites 1+2 of the `EVIDENCE_SOURCES` schema mirror — the bug would have been invisible without the pinning, since fabricated `[recall:<id>]` would parse fine but never reach the linter.
- **Zero net-new dependencies as the design constraint.** Forcing the milestone into the existing `library/` primitives (sqlite-vec, cosine_topk, embed-cache, grounding pattern) made it impossible to drift into a managed-memory framework (Mem0/Letta/Zep/Cognee all stayed rejected). The product hard line held by structural impossibility, not by prompt-plea.
- **Cold-empty-memory golden byte-identity.** The "when memory is empty, prompt is byte-identical to v5.0" invariant turned out to be the load-bearing regression floor — every plan checked against it, every wave preserved it. This let the live-path P65 land without risk to the v5.0 reaction shape.
- **RED-first contract waves.** All 4 phases opened with a RED Wave 0 (test scaffold pinning the contract BEFORE implementation). The headline RED — "fabricated `[recall:<unregistered>]` strips whole turn" — landed as a single test that future regressions cannot pass through.
- **`gsd-autonomous fully` discipline.** Defer-to-KAAN-ACTION pattern (introduced v3.0, validated v4.0+v5.0) absorbed all the §RECALL-EAR felt-quality items + the live-embed round-trip + doc drifts without pausing. v6.0 closed in 3 days with engineering green.

### What Was Inefficient

- **Auto-generated MILESTONES.md entry pulled accomplishments from all `.planning/phases/` directories** (v4.0 + v5.0 + v6.0 phases all present because v4.0 is kept OPEN and v5.0 wasn't phase-archived). Required manual rewrite of the v6.0 entry. Suggests the SDK should scope to the milestone's phase numbers when `--name` is provided.
- **Empty `requirements-completed` frontmatter in some SUMMARY.md files** (Phase 64 + 66 plans). VERIFICATION.md must-have tables stayed authoritative, but the 3-source cross-reference matrix in audit-milestone showed "partial" rows that required manual verification. Fix: every plan SUMMARY's frontmatter should list its REQ-IDs explicitly.
- **CR-01 cross-turn poisoning hole found in code review (P66 iter-3).** The bus-less arm path called raw `parse_citations` instead of the registry-validated `_build_citation_strip`, which would have leaked superset `recall` registrations across turns. Caught and fixed, but should have been caught in Wave-0 RED — the test only covered the bus arm. Lesson: critical-invariant tests need coverage parity across all code paths to that invariant.
- **REQUIREMENTS.md doc-drift items** (RECALL-02 + KAAN-ACTION-LEGAL §RECALL-EAR bus-less arm description). The code was correct; the docs lagged. Suggests a doc-verifier should run as part of phase verification, not just code verification.

### Patterns Established

- **Existence-only evidence sources for retrieval-time citations.** Generalized from P59 `key:` to P65 `recall`. Pattern: add to `EVIDENCE_SOURCES` + `_SOURCE_ALT` regex + `CITATION_GRAMMAR_BLOCK` (3 schema-mirror sites, lockstep) + exclude from `_TIME_KEYED_SOURCES`. **Zero new linter code** for any future retrieval seam.
- **Off-hot-path with hard deadline + clear-then-register on every turn.** For any retrieval that touches the live reaction path: dispatch via `run_in_executor` with `wait_for(deadline)`, then `clear_source(name)` UNCONDITIONALLY at the top of every turn, then register survivors BEFORE the snapshot. Cross-turn leakage is structurally impossible.
- **PAST-tense fence as the prompt-shape anti-poisoning gate.** Retrieval-time evidence ALWAYS fenced as "FROM A PAST SESSION (not happening now)" — never co-mingled with live evidence. Live evidence renders BEFORE retrieved evidence in `evidence_line` source order.
- **Cold/empty/below-floor → byte-identical golden.** When a new feature ships behind a flag or a similarity floor, the cold-path prompt MUST be byte-identical to the prior baseline. Pinning tests pre-empt the "I don't remember anything" filler class of failure.
- **Static anti-feature gate as the runtime drift catcher.** `tests/repo/test_no_recall_antifeatures.py` style — a list of forbidden phrases × allowed files (after string + comment strip + negative-control). Catches LLM-template drift in source; human ear catches Gemini runtime drift.

### Key Lessons

1. **"Does retrieving this close a hallucination class OR unlock a copilot move?"** — the acid test that kept the moment taxonomy at exactly one kind (`coach_line`). `moment` (re-derivable live) got CUT; `audio_moment` got DEFERRED. Acid test before scope expansion.
2. **Anti-poisoning is structural, not a prompt plea.** A poisoned memory footer is existential for an anti-slop product — the mitigation is the citation-grounding chain (existence-only source + register-before-snapshot + linter strips on fabrication), not a "please be careful" sentence in the prompt.
3. **Personalization is emergent from retrieval grounding, not a settings screen.** No "user preferences" UI, no LLM-extracted "tendencies" panel. The DJ's voice surfaces via vocabulary callback because retrieval grounds the prompt in past DJ phrasing. This kept the entire managed-memory-framework class out of the design.
4. **WIRING/REUSE milestones are faster + safer than greenfield.** v6.0 shipped in 3 days because every primitive (sqlite-vec, cosine_topk, embed-cache, grounding pattern, EVIDENCE_SOURCES schema) already existed and was already proven. Look for the wiring shape before reaching for new dependencies.
5. **Kaan-ear veto + default-OFF flag = ship engineering on dev velocity, ship product on Kaan's ear velocity.** Mirrors P60 harmonic veto. The engineering close and the felt-quality close are different events on different clocks; coupling them slows both.

### Cost Observations

- Model mix: ~100% Opus 4.7 (1M context) on all GSD agents per `quality` profile
- Sessions: ~6 across 2026-05-22 → 2026-05-23
- Notable: Zero phase-replan cycles. 4-agent convergent research (P63 + later phases' RESEARCH passes) front-loaded the cost but absorbed all the dependency-ordering risk. Total token budget came in significantly under v5.0 (which had wider scope) despite v6.0 touching the live reaction path.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v6.0 | ~6 | 4 | RED-first contract waves + lockstep schema-mirror tests + zero-net-new-dep constraint |
| v5.0 | ~8 | 4 | Default-OFF Kaan-ear veto pattern (P60) for any quality-gated feature |
| v4.0 | ~14 | 8 | Real-hardware bring-up split into three input seams (boot/audio/controller) |
| v3.1 | ~10 | 5 | One-click installer chain + e2e matrix as the distribution-readiness floor |
| v3.0 | ~12 | 6 | `gsd-autonomous fully` pattern formalized — KAAN-ACTION carry-forward as shipping-OK state |

### Cumulative Quality

| Milestone | Tests (added/total) | Coverage | Zero-Dep Additions |
|-----------|---------------------|----------|--------------------|
| v6.0 | +247 surface / 4152 full | full GREEN at v6.0 surface + 8 baseline WIP failures | **0 net-new deps** (WIRING/REUSE milestone) |
| v5.0 | +~75 | full GREEN | 0 (deck-state + Camelot + pill all reuse) |
| v4.0 | +~120 (live bring-up) | full GREEN | 0 (bring-up + polish only) |

### Top Lessons (Verified Across Milestones)

1. **Defer to KAAN-ACTION instead of pausing.** First formalized v3.0, validated through v3.1 / v4.0 / v5.0 / v6.0. Defer-don't-pause is the productivity-vs-judgment compromise that lets engineering ship on dev velocity.
2. **Default-OFF flag + Kaan-ear veto for any felt-quality feature.** P60 harmonic veto pattern → P65 recall veto. Engineering greens and product greens are different events on different clocks.
3. **Zero net-new dependencies as a design constraint forces creative reuse and prevents drift.** v6.0 codified what v5.0 demonstrated — when the constraint is "use what's already proven", the resulting architecture is automatically resistant to framework-drift failure modes.
4. **Existence-only citation sources for retrieval-time evidence.** P59 `key:` → P65 `recall`. The pattern generalizes; future retrieval seams should start from this shape.
5. **Cold/empty/below-floor goldens are the regression floor.** New flagged features must preserve byte-identical prior-version prompt shape when the flag is cold. Pinned tests prevent prompt-shape drift.
