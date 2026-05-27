# Phase 67 Plan Check — Goal-Backward Verification

**Checked:** 2026-05-23
**Mode:** `gsd-autonomous fully` (only HIGH/BLOCKER concerns block execution)
**Plans verified:** 5 (67P01..67P05)
**Stance:** FORCE adversarial — assumed broken until evidence proved otherwise.

---

## Phase 67 Goal (from ROADMAP)

> Every collected test green across the full marker grid on `macos-13` + `macos-14` + `windows-latest`, flake-hunted, with `.github/workflows/full-test-matrix.yml` running the grid on every push to `main` and every PR.

Four success criteria:
1. `pytest -q` exit 0 + every skip/xfail/xpass carries `# reason:` or routes to `§V7-LIVE`
2. Opt-in grid green on Mac+Win OR Tier-B failures documented in `§V7-LIVE`
3. 10× consecutive `pytest -q` clean OR flakes quarantined behind `@pytest.mark.flaky` + linked GH issue
4. `.github/workflows/full-test-matrix.yml` + README badge

---

## Dimension 1: Goal Coverage

| Goal element | Covered by | Status |
|--------------|------------|--------|
| `pytest -q` exit 0 (8 reds fixed) | 67P01 Task 2 | ✅ |
| `flaky` marker registered in `pyproject.toml` (prerequisite for `@pytest.mark.flaky` under `--strict-markers`) | 67P01 Task 2 | ✅ |
| Reason-tagging static gate (`test_no_silent_skips.py`) | 67P03 Task 1 | ✅ |
| Flake-issue-link static gate (`test_no_silent_flakes.py`) | 67P03 Task 2 | ✅ |
| Opt-in marker triage Tier-A/B/C across 65 tests | 67P02 Task 1 | ✅ |
| `§V7-LIVE` section created in `KAAN-ACTION-LEGAL.md` | 67P02 Task 2 | ✅ |
| Tier-B tests decorated `xfail(strict=False)` + `# reason:` | 67P02 Task 2 | ✅ |
| `full-test-matrix.yml` workflow + SHA-pinned actions + matrix exclude | 67P04 Task 1 | ✅ |
| README badge | 67P04 Task 2 | ✅ |
| 10× consecutive `pytest -q` flake-hunt | 67P05 Task 1 | ✅ |
| Quarantine pattern for any flake found | 67P05 Task 2 | ✅ |
| `docs/flake-hunt.md` contributor protocol | 67P05 Task 1 | ✅ |

**Verdict:** ✅ Every goal element has a covering task. No gaps.

---

## Dimension 2: Requirement Coverage

| Req | Phase plan(s) declaring it | Plans that actually implement | Status |
|-----|---------------------------|------------------------------|--------|
| TEST-01 | 67P01, 67P02, 67P03 | P01 fixes reds; P03 builds reason gate; P02 reason-tags new xfails | ✅ |
| TEST-02 | 67P02, 67P04 | P02 triage + §V7-LIVE; P04 CI per-marker isolation | ✅ |
| TEST-03 | 67P01, 67P03, 67P05 | P01 declares marker; P03 builds flake gate; P05 runs the hunt | ✅ |
| TEST-04 | 67P04 | P04 workflow + badge | ✅ |

**Verdict:** ✅ Every TEST-NN appears in ≥1 plan's `requirements` frontmatter and has implementing tasks.

---

## Dimension 3: Success Criteria Coverage

| SC | Mapped tasks | Verification |
|----|--------------|--------------|
| SC#1 (pytest -q + reason tagging) | P01 Task 2 + P03 Task 1 + P02 Task 2 (`# reason:` adjacent on new xfails) | Static gate enforces; live `pytest -q` exit 0 |
| SC#2 (opt-in grid + §V7-LIVE) | P02 Task 1 (triage) + P02 Task 2 (decorators + section) + P04 (per-marker CI jobs) | `grep '## §V7-LIVE' KAAN-ACTION-LEGAL.md`; per-marker pytest output |
| SC#3 (10× clean OR @flaky+issue) | P05 Task 1 (hunt) + P05 Task 2 (quarantine) + P03 Task 2 (gate) | 10 log files + static gate run |
| SC#4 (`full-test-matrix.yml` + badge) | P04 Task 1 + P04 Task 2 | YAML parse + `grep full-test-matrix.yml README.md` |

**Verdict:** ✅ All 4 SC map to verifiable acceptance criteria.

---

## Dimension 4: Anti-Shallow Execution

Inspected every `<task>` across all 5 plans:

| Plan | Tasks | `<read_first>` present | `<action>` specific | `<verify>` runnable | `<done>` measurable |
|------|-------|------------------------|---------------------|---------------------|---------------------|
| 67P01 | 2 | ✅ | ✅ (per-test diagnosis path) | ✅ (`pytest -q`) | ✅ (0 failures, `git diff src/vibemix/` empty) |
| 67P02 | 2 | ✅ | ✅ (triage table, cluster grouping, decorator placement) | ✅ (grep + per-marker pytest) | ✅ (row counts, xfail counts) |
| 67P03 | 2 | ✅ | ✅ (exact regex, line-window math, negative-control) | ✅ (`pytest tests/repo/`) | ✅ (gate passes, negative-control fires red) |
| 67P04 | 2 | ✅ | ✅ (YAML keys enumerated, SHA-pinned uses, org name resolution) | ✅ (`python3 -c yaml`, grep) | ✅ (matrix shape, badge present) |
| 67P05 | 2 | ✅ | ✅ (5-section doc structure, exact bash loop) | ✅ (file exists + 10 logs) | ✅ (10 logs OR quarantine ledger) |

No vague tasks. Every action names specific files, exact regex/YAML keys, or specific commands. The contract is at the line-and-keyword level, not the prose level.

**Verdict:** ✅ PASS.

---

## Dimension 5: Wave Dependency Soundness

```
P01 (Wave 0) — fix 8 reds + register `flaky` marker
   ↓
P02 (Wave 1) — depends_on [P01] — adds xfail decorators (with both reason= and # reason:)
   ↓
P03 (Wave 2) — depends_on [P01, P02] — static gates must ACCEPT P02's xfails
   ↓
P04 (Wave 3) — depends_on [P01, P02, P03] — CI matrix runs the surface P01-P03 stabilized
   ↓
P05 (Wave 4) — depends_on [P01..P04] — 10× hunt against the post-P04 state
```

**Cross-wave invariant check:**

- **P02→P03 — skip-gate must accept P02's xfail style.** P02 says it adds *both* `reason="…"` kwarg AND a `# reason:` comment. P03's gate accepts `# reason:` within 2 lines above OR `reason=` kwarg within 4 lines. ✅ Compatible by construction.
- **P04 false-fire on P02 xfails?** Per-marker CI jobs run `pytest -q -m "<marker>"`. xfailed tests count as XFAIL (amber/yellow), not FAILED. CI green-band passes. ✅
- **P05 references P04?** P05 frontmatter `depends_on: [P01..P04]`, body references `tests/repo/test_no_silent_flakes.py` from P03. Wave 4 hunt runs AFTER the CI matrix is in place — appropriate for catching local-only flakes that wouldn't surface in CI. ✅
- **No circular dependencies.** Linear 0→1→2→3→4. ✅
- **No forward references.** Each plan references only prior-wave artifacts. ✅

**Verdict:** ✅ PASS.

---

## Dimension 6: Scope Hygiene

| Concern | Evidence |
|---------|----------|
| Zero net-new deps | P01 only declares marker; P05 explicitly rejects `pytest-rerunfailures` + `pytest-repeat`; verification grep `pytest-(repeat\|rerunfailures)` returns 0 | ✅ |
| Zero new product capability | All 5 plans modify only tests/, docs/, `.github/workflows/`, `pyproject.toml` markers, `KAAN-ACTION-LEGAL.md`, README.md | ✅ |
| Zero `src/vibemix/` changes | P01 Task 2 done-criterion: `git diff --stat src/vibemix/ \| wc -l` returns 0. P01 Task 2 explicitly forbids modifying main_wiring.py or other product files | ✅ |
| Reaction-path zero-touch | No plan touches coach/state/agent/runtime/memory/library/grounding | ✅ |
| One-socket invariant | No new ws ports added | ✅ |

**Verdict:** ✅ PASS. Acid test held ("turn existing engineering-green into something a stranger can install/verify/contribute to without growing the surface").

---

## Dimension 7: Autonomous-Mode Discipline

| Scenario | Routing |
|----------|---------|
| Tier-B test can't pass on hosted runner (BlackHole / Win11 desktop SKU / FLX4 USB) | `xfail(strict=False, reason="… §V7-LIVE-NN")` + `# reason:` adjacent + §V7-LIVE entry. NOT a hard pause. | ✅ |
| `windows_only` triage on Kaan's Mac (can't run) | Defaults to Tier-B-pending-Win-VM via Assumption A6, routed to §V7-LIVE-02. | ✅ |
| `gh issue create` unavailable in P05 Task 2 | Routes to KAAN-ACTION-LEGAL.md §V7-LIVE-FLAKE-N as a soft Kaan-discharge item; does NOT block. | ✅ |
| Failure requires product-path change | P01 Task 1 STOP rule: route to §V7-LIVE with xfail + v7.1 issue. Does NOT silently edit `src/vibemix/`. | ✅ |
| 10× hunt time-budget overrun | P05 Task 1 explicitly tolerates backgrounding; SUMMARY records actual elapsed. | ✅ |

**Verdict:** ✅ PASS. Autonomous-mode discipline correct: live-hardware items route to §V7-LIVE (NOT pause); only product-path-touching items are blocked-with-route-to-issue.

---

## Dimension 8: Plan-Level `must_haves` Derivation

| Plan | Truths | Map to SC |
|------|--------|-----------|
| P01 | "Default `pytest -q` exits 0", "`flaky` marker declared and loadable under `--strict-markers`" | SC#1 (exit 0), SC#3 (marker prerequisite) |
| P02 | "Every opt-in test classified Tier A/B/C", "Every Tier-B failure has a §V7-LIVE entry", "No marker is a graveyard" | SC#1 (reason tagging on xfails), SC#2 (opt-in grid + §V7-LIVE) |
| P03 | Static gates fire on bare skip/xfail without reason / @flaky without issue link | SC#1 (anti-drift), SC#3 (anti-drift) |
| P04 | Workflow exists + matrix shape + badge in README + concurrency cancels | SC#4 |
| P05 | 10 consecutive `pytest -q` runs green OR flakes quarantined; protocol doc'd | SC#3 |

Truths are user-observable ("third-party engineer cloning `main` and running `pytest -q` sees exit code 0"), not implementation details. Artifacts have paths + min_lines/contains predicates. key_links connect README→workflow, doc→gate, decorator→issue.

**Verdict:** ✅ PASS.

---

## Architectural Tier Compliance (Dimension 7c)

RESEARCH.md `## Architectural Responsibility Map` assigns:
- Test execution → Local + CI runner ✅ matches all 5 plans
- Marker filter → `pyproject.toml` source-of-truth + `pytest -m` at CI ✅ matches P01 + P04
- Reason tagging → test file + static gate ✅ matches P02 + P03
- Flake quarantine → test file + static gate ✅ matches P05 + P03
- OS-specific routing → skipif + workflow OS matrix ✅ matches P04
- External-clock blockers → §V7-LIVE + xfail(strict=False) ✅ matches P02
- Badge surfacing → README badges row + workflow status URL ✅ matches P04

**Verdict:** ✅ PASS. No tier mismatches.

---

## Cross-Plan Data Contracts (Dimension 9)

Shared data entities across plans:
- `pyproject.toml [tool.pytest.ini_options].markers` — P01 writes (`flaky` line); P03 + P04 read (gate + matrix jobs reference declared markers). One writer, multiple readers. ✅
- `KAAN-ACTION-LEGAL.md §V7-LIVE` — P02 creates section; P05 may append `§V7-LIVE-FLAKE-N` sub-entries. Append-only contract preserved (P02 says "append at end-of-file"). ✅
- Test file decorators — P02 adds xfail; P03's gate reads. P03 gate spec accepts `reason=` kwarg within 4 lines OR `# reason:` within 2 lines — matches what P02 writes. ✅
- `tests/repo/test_no_silent_flakes.py` — P03 creates; P05 references the gate from `docs/flake-hunt.md` AND any P05 quarantine must satisfy the gate. ✅

No conflicting transforms. No incompatible expectations.

**Verdict:** ✅ PASS.

---

## Research Resolution (Dimension 11)

RESEARCH.md `## Open Questions` (lines 616-639) contains 5 questions. Each carries an explicit `Recommendation:` line resolving the question (e.g. "include `default` on all 3 OSes", "`timeout-minutes: 30`", "create both static gates from scratch", "defer triage to plan execution Wave 1", "gate only `@pytest.mark.skip` and `@pytest.mark.xfail`").

Section heading does NOT carry `(RESOLVED)` suffix — but each question is individually resolved with a `Recommendation:` line that the plans implement. Plans cite these recommendations (P04 cites Open Question 1+2; P03 cites Open Question 5).

**Verdict:** ⚠️ LOW concern — RESEARCH.md `## Open Questions` heading lacks `(RESOLVED)` suffix per the dimension 11 contract, but every question has an explicit `Recommendation:` resolution and plans pull from them. Functionally resolved; cosmetic gap only. Not blocking.

---

## CLAUDE.md Compliance (Dimension 10)

Project CLAUDE.md `## Commands` mandates `uv run pytest -q` or `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`. All 5 plans use `uv run pytest -q` consistently. ✅

`## Planning Home` mandates phase planning lives under `.planning/phases/<NN>-<slug>/` — verified all 5 plans + CONTEXT + RESEARCH are correctly located. ✅

`## POC Variants — RETIRED` enforced by `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone` — plans do not touch retired POC paths. ✅

CLAUDE.md `Tech stack` says Python 3.12 — P04 workflow uses `python-version: '3.12'`. ✅

`No managed memory frameworks` rule (Mem0/Letta/Zep/Cognee out) — N/A for P67. ✅

**Verdict:** ✅ PASS.

---

## Pattern Compliance (Dimension 12)

No `PATTERNS.md` in `.planning/phases/67-all-tests-pass/`. RESEARCH.md contains explicit "Architecture Patterns" (Pattern 1 static AST gate, Pattern 2 GH Actions matrix exclude, Pattern 3 §V7-LIVE entry). Plans cite these patterns:
- P03 references Pattern 1 (test_repo_scrub.py prior art) ✅
- P04 references Pattern 2 (eval.yml + release.yml + dep-audit.yml prior art) ✅
- P02 references Pattern 3 (§SHIP-V4 + §RECALL-EAR structural mirror) ✅

**Verdict:** ✅ PASS. (Skipped per dim-12 skip-rule for no PATTERNS.md, but de facto compliant.)

---

## Concerns

### MEDIUM concerns (1)

**M1. P01 Task 2 risks updating tests-as-contracts to match drift without judging whether the drift is real product regression.**

P01 Task 2 instructs: "update kwarg-drift expectation in anti-slop wiring test to match current `_route_to_main` signature WITHOUT changing the main_wiring.py file". If those failing tests exist as drift-detection contracts (they sound like they do — `test_wire13_anti_slop_disabled_path_passes_none_kwargs`, `test_tag_regex_unchanged_in_this_plan`, `test_state_md_phase_16_line_is_annotated_retired`), naively updating them to match current source-of-truth defeats the test's purpose.

**Mitigation already in plan:** Task 1 has an explicit STOP rule — "if any failure actually requires a product-path change, STOP and route it to §V7-LIVE with `xfail(strict=False)` (Tier-B) and a v7.1 fix issue — flag it as 'out of v7.0 scope' per Assumption A1." This routes real regressions to §V7-LIVE rather than silently masking them.

**Recommendation:** Execute as planned. The STOP rule is the safety valve. If any of the 8 fixes turn out to be legitimate regressions (not drift), they route to §V7-LIVE. Under `gsd-autonomous fully`, this is the defensible behavior. Not blocking.

### LOW concerns (3)

**L1. RESEARCH.md `## Open Questions` heading lacks `(RESOLVED)` suffix.** Each question has an explicit `Recommendation:` resolution and plans implement them. Cosmetic only.

**L2. P04 README badge will show gray "no status" for one push-window after merge** until the workflow runs on `main`. Plan explicitly documents this in Pitfall 5 + Task 2 done-criterion. Expected transient state.

**L3. P02 `windows_only` triage can't fully execute on Kaan's Mac.** Plan correctly routes all `windows_only` tests to Tier-B-pending-Win-VM via §V7-LIVE-02 per Assumption A6. Acceptable under `gsd-autonomous fully`; Win-VM confirmation rides forward on Kaan-action clock.

---

## Final Verdict

| Dimension | Status |
|-----------|--------|
| Goal coverage | ✅ |
| Requirement coverage (TEST-01..04) | ✅ |
| Success criteria coverage (4/4) | ✅ |
| Anti-shallow execution | ✅ |
| Wave dependency soundness | ✅ |
| Scope hygiene (zero net-new deps, zero src/vibemix/) | ✅ |
| Autonomous-mode discipline | ✅ |
| `must_haves` derivation | ✅ |
| Architectural tier compliance | ✅ |
| Cross-plan data contracts | ✅ |
| CLAUDE.md compliance | ✅ |
| Pattern compliance | ✅ |

**BLOCKER count:** 0
**HIGH count:** 0
**MEDIUM count:** 1 (with in-plan safety valve)
**LOW count:** 3 (all cosmetic or expected-transient)

Under `gsd-autonomous fully`, MEDIUM/LOW concerns do NOT block. The MEDIUM concern (M1) has an in-plan STOP rule that handles the risk correctly.

---

## PLAN CHECK PASSED

All 5 plans (67P01..67P05) collectively satisfy the Phase 67 goal and all 4 success criteria. Wave dependencies are linear and acyclic. Scope hygiene is held by construction (zero net-new deps, zero `src/vibemix/` changes). Autonomous-mode routing for live-hardware items goes to `§V7-LIVE` with `xfail(strict=False)` — correct behavior, not a concern. Proceed to `/gsd:execute-phase 67`.
