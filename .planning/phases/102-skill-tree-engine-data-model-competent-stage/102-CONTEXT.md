# Phase 102: Skill-Tree Engine + Data Model + Competent Stage - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — design pre-locked in brainstorm; grey-area recommendations auto-accepted per `gsd-autonomous` default-YES (Kaan "yasla aşk"). One architecture choice (GA3-Q3 derived-vs-stored) flagged for plan-phase refinement under Claude's discretion.

<domain>
## Phase Boundary

A pure-logic skill-tree engine (`src/vibemix/learn/skill_tree.py`) maps the existing 36 lessons / 3 courses onto ~6 named DJ skills, each with a two-stage bar (Locked → Competent → Mastered). This phase delivers ONLY the **Competent stage** + the data model + persistence/migration — NO live "Mastered" grounding (Phase 103) and NO UI (Phase 104). Every behavior is offline-unit-testable on synthetic lesson/recital outcomes; standalone-verifiable with zero UI. Lands the Invariant #1 AST gate (skill_tree never mutates `MusicState`) + the Invariant #4 no-new-port gate.

DELIVERS: SKILL-01 (6-skill two-stage model), SKILL-02 (`SkillTree`/`SkillProgress` sole-writer engine), SKILL-03 (readable manifest), COMP-01 (quality-weighted Competent fill), COMP-02 (recital honest-score gate to reach Competent), DATA-01 (`skills` block on `learn-progress.json`, never `profile.json`), DATA-02 (v1→v2 deterministic back-fill + corrupt recovery), DATA-03 (reset path).

NOT IN THIS PHASE: live event→credit recognition, the locked-until-Competent Mastered segment mechanics beyond the schema fields (Phase 103); any panel, animation, or co-host vocal (Phase 104).
</domain>

<decisions>
## Implementation Decisions

### Skill set & lesson→skill mapping (GA1)
- Exactly 6 skills (REQ-locked): `deck_control` (C1), `beatmatching` (C2), `eq_mixing` (C2), `harmonic_mixing` (C2), `transitions` (C2), `phrasing_performance` (C3).
- The skill→lesson→gating-recital mapping is a single readable module-level constant (`SKILL_MANIFEST`) in `skill_tree.py`, referencing canonical lesson IDs from `learn/curriculum.py::CURRICULUM` (no string drift — assert each referenced lesson ID exists at import/test time).
- A lesson may feed ≥1 skill (some lessons teach multiple competencies); the manifest is skill→{lesson IDs}. A lesson feeding no skill (e.g. "don't touch the master fader" hygiene) is a valid no-op for skill fill.
- Each skill declares its gating recital (`deck_control`→Course 1 recital L1.16; the four C2 skills→Course 2 recital L2.14; `phrasing_performance`→Course 3 completion gate). Stored in the manifest, not hard-coded in the engine.

### Competent fill math (GA2)
- Per-skill Competent fill is a normalized fraction in [0.0, 1.0] = (weighted points earned from that skill's lessons) / (total weighted points available for that skill).
- Quality weighting: a first-try (0-strikes) lesson completion contributes full weight; a completion that used strikes contributes a reduced weight (concrete weights are Claude's discretion in plan-phase; first-try > with-strikes > incomplete). Click-through with no demonstrated outcome contributes the floor.
- COMP-02 HARD GATE: a skill reaches "Competent" only when `lesson_fill >= COMPETENT_THRESHOLD` AND that skill's gating recital has been passed (honest-score gate, read from `LearnProgress.course_N_unlocked` / recital outcomes). 100% lesson fill without the recital pass is NOT Competent.
- Fill is monotonic for display (never decreases on reload) but is recomputed deterministically from source — see persistence decision.

### Persistence & migration (GA3)
- The **learn-portion** of skill state (lesson fill + competent bool) is DERIVED by recomputing from the authoritative `LearnProgress` on each load — single source of truth, zero dual-write drift. The **live-portion** (`live_proof_count`, `mastered`, `first_mastered_at`) is STORED in a new `skills` block on `learn-progress.json` because it cannot be recomputed (Phase 103 writes it; Phase 102 only creates the schema with safe defaults: count 0, mastered false, first_mastered_at null).
- `skills` block lives ONLY in `~/.cache/vibemix/learn-progress.json` via the existing atomic `tmp.write_text`→`os.replace` pattern. NEVER `profile.json` (the 5-field `additionalProperties:false` privacy contract stays intact — test-pinned).
- Schema migrates `schema_version` v1→v2: a v1 file (no `skills` block) loads, the live-portion defaults are injected for all 6 skills, the learn-portion is recomputed (= deterministic back-fill from existing lesson/course completions), and the v2 file is written. Corrupt/older read recovers gracefully via the existing `load_progress` catch→fresh-empty path (extended to seed an empty v2 `skills` block).
- DATA-03 reset: a reset path clears the live-portion ledger (mirrors the existing lesson-progress reset CLI in `progress.py`); the derived learn-portion follows whatever `LearnProgress` holds.

### Engine API & invariant gates (GA4)
- `SkillProgress` = a per-skill dataclass (skill id, stage Locked/Competent/Mastered, learn_fill float, competent bool, live_proof_count int, mastered bool, first_mastered_at str|None). `SkillTree` = the manifest + `compute(progress: LearnProgress, live_ledger) -> dict[str, SkillProgress]` pure function. (Phase 103 adds `record_live_demo`.)
- `skill_tree.py` is pure-logic and the sole writer of skill state. Persistence of the live ledger goes through a thin atomic-write helper (extend `progress.py` or a sibling) — `skill_tree` itself does no I/O of `MusicState`.
- Any timestamp (`first_mastered_at`) is injected (parameter / clock callable, mirroring `progress.py` UTC usage) so tests are deterministic.
- Invariant pins land here (mirror v9.0 `tests/learn/test_runtime_invariants.py`): `test_skill_tree_never_mutates_musicstate` (AST/import gate — `skill_tree` must not import or write `MusicState`), `test_no_new_ws_port` (static grep — zero `websockets.serve` in the new module), `test_skills_never_in_profile_json` (privacy contract pin).

### Claude's Discretion
- Concrete numeric weights for first-try vs with-strikes vs floor, and the `COMPETENT_THRESHOLD` value — plan-phase chooses, defended by the fill-math unit tests.
- The exact derived-vs-stored split mechanics (GA3-Q3) — recommended derived-learn/stored-live; plan-phase research may refine while preserving single-source-of-truth + the no-`profile.json` rule.
- Exact module placement of the live-ledger atomic-write helper (in `progress.py` vs a new `skill_store.py`).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `learn/progress.py` — `LearnProgress` dataclass + atomic JSON persistence (`tmp.write_text`→`os.replace`), `load_progress`/`save_progress`, `progress_path()` (monkeypatchable), corrupt-read recovery, `schema_version`/`from_dict` migration precedent. The skills block extends THIS file's schema; the live-ledger helper mirrors its atomic-write pattern.
- `learn/recital.py` — `RecitalRuntime` writes `course_N_unlocked` on honest-score pass (score≥5, +distinct-type floor for C2). The Competent recital-gate reads these unlock flags / recital outcomes.
- `learn/curriculum.py` — `CURRICULUM` is the canonical lesson-ID source the `SKILL_MANIFEST` references.
- v9.0 `tests/learn/test_runtime_invariants.py` — the AST/static-gate pattern to mirror for the #1/#4 pins.
- `profile/schema.py` — the `additionalProperties:false` 5-field privacy contract that the `test_skills_never_in_profile_json` pin protects.

### Established Patterns
- Single-writer (#1): lesson/learn state lives under `learn/`, never in `MusicState`; sole-writer is the runtime. Skill state follows — `skill_tree` is the sole writer, derived from `LearnProgress`.
- Atomic JSON persistence with schema_version + graceful corrupt recovery (`progress.py`).
- Offline-unit-testable engine modules (no API key, no audio capture) — the v9.0 learn-engine convention.

### Integration Points
- Reads `LearnProgress` (lessons completed, strikes_used, course_N_unlocked) — already persisted by the lesson runtime.
- Persists the live-portion `skills` block inside the SAME `learn-progress.json` (no new file, no new path).
- Phase 103 consumes `SkillTree.compute` + adds `record_live_demo`; Phase 104 consumes the computed `dict[str, SkillProgress]` for display over existing `learn.*` IPC (no IPC change in Phase 102).
</code_context>

<specifics>
## Specific Ideas

- "Nothing is given; every notch is earned" — the Competent gate must be a real recital pass, never a click-through. The fill-math unit tests must include a "100% click-through, no recital → NOT Competent" case as a headline assertion.
- Schema forward-compat: create the live-portion fields in Phase 102 (defaulted) so Phase 103 writes into an existing shape with zero second migration.
</specifics>

<deferred>
## Deferred Ideas

- Live event→skill credit recognition + the N-demo Mastered flip → Phase 103.
- Skill-tree panel, Competent-fill cue, the grounded "Mastered" co-host vocal → Phase 104.
- Per-skill sub-skills, Intermediate/Pro branches, skill-state feeding the live persona/lens → Future (v11.x / Bravoh) per REQUIREMENTS.
</deferred>
