# Phase 1 Plan Check

**Reviewer:** gsd-plan-checker
**Date:** 2026-05-11
**Verdict:** PASS (with non-blocking improvements)

---

## Goal Coverage

| # | Goal item                                                                 | Status | Evidence |
|---|---------------------------------------------------------------------------|--------|----------|
| 1 | `uv sync` succeeds + `uv run python -c "import vibemix"` works            | ✅ covered | Task 1.3 runs `rm -rf .venv && uv python install 3.12 && uv sync`, then `uv run python -c "import vibemix; print(vibemix.__version__)"`. Task 4.1 check 10 re-runs `rm -rf .venv && uv sync --frozen` from scratch as a capstone. |
| 2 | Protocol firewall — `from vibemix.platform import AudioBackend` works     | ✅ covered | Task 2.1 creates all four Protocol files + `platform/__init__.py` re-export hub. `<interfaces>` block in plan locks the exact method shapes verbatim from PATTERNS.md so Phase 2's `_audio_macos.AudioMacOS` can satisfy `AudioBackend` structurally. Verify line: `uv run python -c "from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend"`. |
| 3 | `uv.lock` exists, committed, pins all transitive deps                     | ✅ covered | Task 1.3 generates lockfile; Task 4.1 check 2 runs `uv lock --check` for drift; Task 4.1 check 10 runs `uv sync --frozen` for true reproducibility. `uv.lock` is listed in `files_modified`. Task 4.3 explicitly stages `uv.lock` in the atomic commit. |
| 4 | SignPath OSS application filed on day 1 — prefilled checklist + Kaan submits | ✅ covered | Task 3.2 produces `.planning/signpath-application.md` with all 9 sections + KAAN-ONLY banner. Task 4.2 is a blocking `checkpoint:human-verify` task where Kaan submits. Step B in `<how-to-verify>` lists the exact submission flow. |
| 5 | Public repo at `github.com/ozzaii/vibemix` with LICENSE + commits         | ✅ covered | Task 3.2 produces `docs/setup-github-repo.md` with the exact `gh repo create ozzaii/vibemix --public --source=. --remote=origin --push` command. Task 4.2 step A is Kaan running it. LICENSE (Apache 2.0) is created in Task 1.1. All Phase 1 commits are pushed via `--push`. |
| 6 | POC files untouched                                                       | ✅ covered | `<key_corrections>` explicitly lists every off-limits file. Task 4.1 check 8 runs `git diff --name-only` filtered against the off-limits set. must_haves.truth #8 enforces it. `[tool.ruff.lint.per-file-ignores]` exempts POC files from lint churn — they aren't touched. |

**Coverage verdict:** All 6 goal items are addressed with explicit tasks AND verification checks. No silent scope reduction detected.

---

## Risk Findings

| Risk | Status | Evidence |
|------|--------|----------|
| **R1 — Protocol shape divergence from PATTERNS.md** | ✅ covered | Plan's `<interfaces>` block is lifted verbatim from PATTERNS.md (line 162-234). Method signatures match exactly: `AudioBackend.find_device/open_capture/open_passthrough_output/open_voice_output`, `ScreenBackend.is_available/find_window_bounds/capture`, `MidiBackend.list_input_ports/open_input`, `TrackInfoBackend.is_available/poll`. Task 2.1 explicitly instructs "do not paraphrase the method names or argument order." Task 3.1 adds `test_protocol_surface` which asserts the exact method-name sets are present on each Backend. **Note:** RESEARCH.md (P1-6) contains an EARLIER, divergent shape (`async def start/stop`, `enumerate_inputs`, `on_master_pcm`, `TrackSnapshot` instead of `NowPlayingSnapshot`) — the plan correctly elects PATTERNS.md as load-bearing and explicitly states so in the interfaces block comment ("PATTERNS.md is the load-bearing reference"). |
| **R2 — Python 3.12 wheel coverage for pinned deps** | ✅ covered | Task 1.3 has explicit fallback path: "If `uv sync` fails with a wheel-availability error on any pinned dep, capture the failing package + version from stderr, note it in the SUMMARY draft for Kaan, and bump the pin to the closest version that has a Python 3.12 wheel (RESEARCH.md Assumption A4/A5 flagged this risk for `pyobjc-framework-Quartz>=12.1` and `livekit-agents>=1.5.8`)." Task 4.3 SUMMARY's "Anything weird / surprising" field captures the bumps. |
| **R3 — `.env` leak risk** | ✅ covered, ORDERING CORRECT | Task 1.1 writes the comprehensive `.gitignore` (with `.env`, `.env.*`, `!.env.example`) BEFORE the repo is published. Repo push (Task 4.2 step A) happens in Wave 4 — three waves AFTER `.gitignore` is committed in Wave 1's atomic commit. The Wave-1 commit-message header in plan ("`feat(01): wave 1 — package skeleton + uv lockfile + license`") implies `.gitignore` lands with that first commit. Threat T-01-01 explicitly tracks this. Task 4.3 also re-confirms `git status` is clean before final commit (no `.env` accidentally staged). |
| **R4 — Bravoh repo decision drift** | ✅ covered | `<key_corrections>` block at top of plan explicitly states: "Repo URL is `https://github.com/ozzaii/vibemix` (Kaan's personal account). RESEARCH.md and CONTEXT.md reference `bravoh/vibemix` in places — that is stale ... Every artifact (signpath checklist, README, pyproject `[project.urls]`, docs/setup-github-repo.md) MUST use `ozzaii/vibemix`." Task 1.1 pins `[project.urls]` to ozzaii. Task 3.2 sets the SignPath URL to ozzaii. Task 3.1's `test_signpath_checklist` greps for `ozzaii/vibemix` (would catch a stale `bravoh` reference). Verify line on Task 1.1 includes `grep -q "ozzaii/vibemix" pyproject.toml`. **No stale `bravoh` reference can survive — three independent checks.** |
| **R5 — Verification realism** | ✅ covered | Task 3.1's `test_runtime_checkable` asserts `runtime_checkable(Backend) is Backend` AND `isinstance(object(), Backend) is False` for all four Protocols. Task 2.1's verify command goes further: imports all 12 names + runs the same runtime_checkable assertion inline. Task 3.1's `test_protocol_surface` AST-introspects each Backend's method set. Task 3.1's `test_no_os_leaks` AST-scans every `src/vibemix/platform/*.py` for forbidden imports (sounddevice/mss/Quartz/mido/numpy/scipy/etc.). This is the strongest verification stance possible for a typing-only phase. |
| **R6 — Kaan-only task framing** | ✅ covered | Task 4.2 is typed `checkpoint:human-verify` with `gate="blocking"`. Both Kaan-only artifacts carry a `KAAN-ONLY` banner enforced by `grep -q "KAAN-ONLY"` in Task 3.2's verify line. The frontmatter `user_setup` block lists both services (github + signpath-foundation) with explicit `why` and dashboard-config tasks. Task 4.2's action block explicitly says: "Do NOT skip ahead. Do NOT attempt to create the repo or submit the SignPath form yourself." The resume signal is "approved" — executor can't autonomously proceed. |

**Risk verdict:** All six risks have explicit, multi-layered coverage. No risk is left to executor discretion.

---

## Pitfall Mitigations

| Pitfall | Status | Evidence |
|---------|--------|----------|
| **P3 — API key leakage via .env** | ✅ confirmed mitigated | Task 1.1 writes `.gitignore` with `.env`, `.env.*` exclusions + `!.env.example` carve-out, committed in Wave 1 BEFORE the public push in Wave 4. Verify line: `grep -qE "^\.env$" .gitignore && grep -q "^!\.env\.example" .gitignore`. Threat T-01-01 logs the mitigation. Task 4.1 check 8 confirms POC `.env` not in any Phase 1 commit. **Note:** the current `.env` (55 bytes, `GEMINI_API_KEY=...`) already exists on disk — Wave-1 `.gitignore` prevents its push. The plan does NOT instruct removal of `.env` from disk (correct — Kaan still needs it locally for POC runs). |
| **P11 — PyInstaller / Python drift** | ✅ confirmed mitigated | Task 1.1 sets `requires-python = ">=3.12,<3.13"` exact. `.python-version` pins `3.12` for uv-managed toolchain. Task 1.3 runs `uv python install 3.12` to materialise the exact interpreter. Both prevent the drift where a contributor uses 3.13 or 3.14 and breaks PyInstaller wheels later. Verify line on Task 1.1 includes `grep -q "^3.12" .python-version`. |
| **P14 — Apache 2.0 + DCO** | ✅ partially mitigated (license correct, DCO deferred per CONTEXT) | LICENSE is Apache 2.0 (Task 1.1 step 2 specifies "verbatim Apache License 2.0 text" + `Copyright 2026 Bravoh / Kaan Özkan` appendix). `tests/test_license.py::test_license_apache_2_0` asserts "Apache License" + "Version 2.0" in LICENSE text. SPDX header `# SPDX-License-Identifier: Apache-2.0` is the first line of every `src/vibemix/*.py` and is asserted by `test_spdx_header_in_init`. **DCO / CONTRIBUTING.md is explicitly deferred to Phase 19 per CONTEXT decision** — surfaced in SUMMARY's "open items" + RESEARCH.md Open Question 3 recommends a placeholder. The plan does NOT add the placeholder CONTRIBUTING.md from RESEARCH's Q3 recommendation — see "Recommended improvements" below. License-pillar of P14 is rock-solid; CLA/DCO-pillar is deliberately deferred. |

**Pitfall verdict:** P3 and P11 are fully mitigated. P14's license half is rock-solid; the DCO half is deferred per locked CONTEXT decision (not a blocker).

---

## Required Changes (BLOCKERS)

**None.** No blockers identified. Plan can proceed to execution.

---

## Recommended Improvements (non-blocking)

1. **RESEARCH.md `## Open Questions for Planner` is missing the `(RESOLVED)` suffix.** Dimension 11 (Research Resolution) wants the heading to read `## Open Questions for Planner (RESOLVED)` (or each item marked `RESOLVED:`). All five open questions ARE substantively resolved in CONTEXT.md decisions + the plan's `<key_corrections>` block:
   - Q1 (bravoh org) → resolved: `ozzaii/vibemix`, deferred org transfer.
   - Q2 (SignPath Section 3 release-gate) → resolved: file anyway with candor framing (Task 3.2 explicit).
   - Q3 (DCO placeholder) → resolved: deferred to Phase 19 per CONTEXT.
   - Q4 (README depth) → resolved: terse per Task 1.1 step 4.
   - Q5 (Python 3.12 install) → resolved: `uv python install 3.12` per Task 1.3.
   - **Recommendation:** Update RESEARCH.md heading to `## Open Questions for Planner (RESOLVED)` and annotate each item — keeps the GSD audit trail tidy. Non-blocking because the resolutions are already applied in the plan.

2. **Add the one-line `CONTRIBUTING.md` placeholder from RESEARCH Q3.** Drop-in cost is ~5 minutes; benefit is closing the P14 DCO ambiguity window between Phase 1 and Phase 19 if an external contributor opens a PR during the Phase 2-18 build. The placeholder reads: "vibemix is currently in pre-release; we are not yet accepting external PRs. CONTRIBUTING with DCO arrives at Phase 19 / launch." This was the researcher's recommendation; CONTEXT defers full CONTRIBUTING but does not preclude a placeholder.

3. **Task 4.1 check 8 baseline-comparison fragility.** Check 8 says `git diff --name-only main..HEAD` — but Phase 1 is the very first feature work on `main`, so `main..HEAD` may be empty (HEAD == main pre-Wave-4-commit) or include only the WIP commits. The check has a parenthetical disclaimer ("adapt to compare against the pre-Phase-1 baseline"). **Suggested fix:** capture the pre-Phase-1 SHA in a Task 1.0 prelude or use a tag like `git tag pre-phase-01` at Wave-1 entry, then compare `git diff --name-only pre-phase-01..HEAD`. Non-blocking because the AST OS-leak test (check 7) is the load-bearing POC-untouched protection — but the git-diff check is the explicit truth #8 enforcement.

4. **Wave-3 ordering — `docs/` directory creation.** Task 3.2 creates `docs/setup-github-repo.md` but Task 1.1 doesn't `mkdir docs/`. `Write` tool implicitly creates parents, so this works in practice — flag is cosmetic only.

5. **Task 4.3 commit grouping.** The plan stages all Phase 1 work in one atomic commit at Task 4.3 (after Kaan's manual steps). The wave headers (`Atomic commit at end: 'feat(01): wave 1 ...'`) suggest per-wave commits, but the actual `git add ... git commit` only appears in Task 4.3. **Suggested clarification:** Either commit per wave AND the final SUMMARY commit, OR drop the per-wave commit prose from the wave headers. Current state is ambiguous but not wrong — non-blocking.

---

## Bottom Line

The plan is **execution-ready**. All six goal-backward truths have explicit tasks + verify commands. All six caller-flagged risks (R1-R6) have multi-layered coverage with no scope reduction. The three pitfalls (P3, P11, P14) are mitigated within the bounds locked by CONTEXT (P14's DCO half is deliberately deferred to Phase 19, which is a CONTEXT-locked decision, not a plan miss).

The `<key_corrections>` block at the top of the plan is the load-bearing reconciliation: it binds `ozzaii/vibemix` against stale `bravoh/vibemix` references in RESEARCH.md/CONTEXT.md and binds PATTERNS.md as the authoritative Protocol-shape source (not RESEARCH.md's earlier draft in P1-6). Both bindings are enforced by greps and tests downstream, so the executor cannot accidentally drift back to the stale forms.

Five non-blocking improvements are recommended for code hygiene + audit-trail tidiness (research-questions marker, CONTRIBUTING placeholder, git-diff baseline, docs mkdir, commit grouping prose). None of them gate execution.

**Proceed to `/gsd-execute-phase 01`.**
