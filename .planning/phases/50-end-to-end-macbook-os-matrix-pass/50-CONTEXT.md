# Phase 50 Context: End-to-End MacBook + OS-Matrix Pass

**Created:** 2026-05-18
**Mode:** `/gsd-autonomous fully` — auto-accept grey-area; defer blockers to Kaan-action; no AskUserQuestion pauses.

<domain>
Validate the SHIPPED `.dmg` end-to-end across functional + visual + aesthetic + usability + hallucination dimensions. Pass deliberately split per Pitfall 3:

- **50a Kaan-ear (subjective)** — Kaan's MacBook walk with real DJ-set audio per memory `project_phase_16_kaan_dj_testing` (NOT a formal 30-session replay harness). Engineering ships the harness scaffold + checklist + screencast capture rig; Kaan discharges the walk at §E2E-50A-WALK.
- **50b OS-matrix smoke (objective)** — automated install / launch / first-event / shutdown on ≥ 2 of {macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11}. Engineering scaffolds the harness wired into `tart` matrix; real-VM run is downstream of §INSTALL-VM-RUN + §INSTALL-COMPANION-SIGN from Phase 49.

Both 50a + 50b required for v3.1 milestone close. Closes v3.0 INSTALL-VM-RUN gap and confirms zero regression of the v3.0 engineering surface.

This is the FINAL phase of the v3.1 Distribution-Ready Pass milestone — gate 6b operational, anti-slop passes on report.html, privacy fixture asserts zero off-limits writes.
</domain>

<canonical_refs>
MANDATORY reads for downstream agents (researcher / planner / executor):

- `.planning/ROADMAP.md` § Phase 50 — full success-criteria text (lines 116–132)
- `.planning/REQUIREMENTS.md` § E2E (E2E-01..E2E-10, lines 67–78) — 10 REQ-IDs
- `.planning/research/STACK.md` § Bucket 4 — e2e tooling (`tauri-plugin-playwright==0.1.0`, `@playwright/test==1.50.x`, `pixelmatch==7.1.0`, `pytest-playwright==0.5.x`)
- `.planning/research/FEATURES.md` § TEST — table-stakes / differentiator / anti-feature framework
- `.planning/research/ARCHITECTURE.md` § 4 — `tests/e2e/macbook/` placement, `__snapshots__/` in-repo (~2.5 MB total, not LFS), `dist/e2e-macbook-runs/<UTC>/report.html`, Gate 6b alongside Gate 2b
- `.planning/research/PITFALLS.md` § 3 (single-machine MacBook trap), § 8 (`tauri-plugin-playwright` maturity), § 19 (audio-loopback bootstrap paradox), § 26 (VCR cassette invalidation)
- `.planning/phases/47-mascot-real-glb-land-full-emotion-coverage/47-VERIFICATION.md` — Phase 47 placeholder GLBs at `tauri/ui/assets/mascot/animations/`, EVENT_LAYER_PRIORITY_MAP, persona-smoke harness, mascot.html grep-gate
- `.planning/phases/49-win-mac-one-click-installer-chain/49-VERIFICATION.md` — Phase 49 companion driver, `installer/companion/`, `tauri/ui/src/wizard/`, `scripts/dist/install_vm_matrix.{sh,json}`, onboarding stopwatch at 41s median / 52s p95
- `scripts/launch/cut_release.sh` — existing 6-gate pre-flight; Gate 2b at line 92–93 (Phase 42 hallucination gate); add Gate 6b alongside without duplicating
- `scripts/release/check_gate.sh` — Gate 2b runner (7-day nightly proxy + ear-test, Phase 42 / GATE-06)
- `scripts/launch/check_no_ai_slop.py` — existing 15-token + `\bdeeply\s+\w+` regex blocklist; extend grep target paths via sibling-script pattern
- `scripts/mascot/check_no_ai_slop_phase47.py` — sibling-script reference precedent (Phase 47)
- `scripts/audit/check_no_slop_opp.py` — sibling-script reference precedent (Phase 48)
- `tauri/ui/assets/mascot/animations/` — 23 placeholder GLBs from Phase 47; visual-diff baselines run against these until §VIS-04 lands real assets
- Memory anchors: `project_phase_16_kaan_dj_testing`, `feedback_privacy_scope_narrow`, `project_anti_slop_grounded_gemini_thesis`, `feedback_worktree_must_sync_main_first`, `project_v4_canonical_baseline`, `project_one_click_install_hard_req`, `feedback_no_scope_creep_clean_utility`
</canonical_refs>

<prior_decisions>
**From v3.0 Phase 40 (worktree learning):** Every subagent prompt MUST include Step-0 `git fetch origin main && git merge origin/main --no-edit` invariant per memory `feedback_worktree_must_sync_main_first`. Plan-checker rejects any Phase 46–50 plan missing this block.

**From Phase 42 (hallucination gate v3):** Gate 2b at `scripts/release/check_gate.sh` runs 7-day nightly proxy + ear-test. Phase 50 wires Gate 6b alongside — NEVER duplicates Gate 2b logic.

**From Phase 47 (mascot real GLB land):** 23 placeholder GLBs at `tauri/ui/assets/mascot/animations/` exist NOW. Real GLBs ship via §VIS-04 Kaan-action (Mixamo Adobe-account walk). Phase 50 visual-diff baselines run against placeholders; baselines re-shoot at §VIS-04 discharge.

**From Phase 48 (new-dep scan):** Sibling-script pattern locked. `check_no_slop_opp.py` (a sibling of `check_no_ai_slop.py`) established as the precedent — extend anti-slop coverage to new artifact paths via a NEW sibling, NOT by editing the canonical script.

**From Phase 49 (installer chain):** `installer/companion/`, `tauri/ui/src/wizard/`, `scripts/dist/install_vm_matrix.sh` exist. Onboarding stopwatch at 41s median / 52s p95 (within 60s gate). §INSTALL-VM-RUN + §INSTALL-COMPANION-SIGN deferred to Kaan-action — Phase 50 50b harness assumes both land before real-VM execution.

**Auto-accepted grey-area answers (autonomous mode):**
- **VCR cassette identity:** pin to v3.0 GATE-02 baseline (zero new live Gemini calls; reuse existing cassette artifacts). Re-record only if cassette drift detected.
- **Visual-diff baseline policy:** baseline against Phase 47 placeholder GLBs NOW; re-baseline once §VIS-04 lands real assets. Document the re-baseline trigger in CONTEXT/PLAN.
- **`tauri-plugin-playwright` maturity:** ship Playwright + WebView2 path. If `tauri-plugin-playwright==0.1.0` blocks on macOS WKWebView, fall back to WebView2-only Win e2e + manual Mac walk (50a) per PITFALLS § 8 — do NOT block Phase 50 on plugin maturity.
- **Anti-slop extension:** sibling script `scripts/audit/check_no_slop_e2e.py` (NOT a redesign of `check_no_ai_slop.py`).
- **Privacy fixture location:** `tests/e2e/macbook/conftest.py::test_no_off_limits_write`. Asserts ZERO writes to `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/` per memory `feedback_privacy_scope_narrow`.
- **report.html path:** `dist/e2e-macbook-runs/<UTC>/report.html` per ARCHITECTURE.md § 4.
- **Snapshot storage:** `tests/e2e/macbook/__snapshots__/` in-repo (~2.5 MB total, not LFS) per ARCHITECTURE.md § 4.
- **Gate 6b name + location:** `scripts/e2e/check_e2e_report.sh`, wired into `scripts/launch/cut_release.sh` immediately after Gate 2b without duplicating its logic.
- **50a screencast:** committed to `docs/e2e/2026-05-walk.webm` (LFS or < 25 MB). Engineering provides empty-placeholder + capture rig; Kaan records.
- **Pixelmatch threshold:** `maxDiffPixelRatio: 0.02` per ARCHITECTURE.md § 4 (matches REQ E2E-03 verbatim).
- **OS-matrix target count for 50b:** ≥ 2 of 5 — engineering scaffolds for all 5, real-VM execution gated on §INSTALL-VM-RUN. Engineering-green = harness present + dry-run on 2 configs.
</prior_decisions>

<spec_lock>
No SPEC.md exists. Requirements lock comes from `.planning/REQUIREMENTS.md` § E2E (E2E-01..E2E-10) + ROADMAP.md § Phase 50 Success Criteria. Both are MANDATORY reads for planner.
</spec_lock>

<decisions>
### Architecture
- Harness location: `tests/e2e/macbook/` (single canonical path per ARCHITECTURE.md § 4).
- Output directory: `dist/e2e-macbook-runs/<UTC>/report.html` — project-scoped, NEVER writes outside.
- Snapshots: `tests/e2e/macbook/__snapshots__/` in-repo (small footprint, not LFS).
- Test stack: `@playwright/test==1.50.x` + `pixelmatch==7.1.0` + `pytest-playwright==0.5.x` + `tauri-plugin-playwright==0.1.0`.
- Audio-loopback: pytest fixture that replays VCR cassette pinned to v3.0 GATE-02 baseline. ZERO live Gemini calls in CI.

### 50a Subjective Kaan-Ear Pass (Engineering Scaffold)
- Deliverables: harness scaffold + Nielsen 10-heuristic checklist + screencast capture rig (CLI helper) + gap-closure routing into STATE.md Kaan-action surface.
- Kaan-action: §E2E-50A-WALK (walk + screencast recording on his MacBook + real DJ-set audio).
- Does NOT auto-build 30-session replay harness, LLM scorer, F1 validator (memory `project_phase_16_kaan_dj_testing`).

### 50b Objective OS-Matrix Smoke (Engineering Harness)
- Scope: install / launch / first-event / shutdown on ≥ 2 of {macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11}.
- Driver: extends Phase 49's `scripts/dist/install_vm_matrix.sh` with `--check-e2e` flag (NOT a new harness — composition).
- Engineering-green = harness + dry-run on 2 reachable configs (CI macOS-latest + a Tart 14 AS image if available); real-VM run on all 5 gated on §INSTALL-VM-RUN.

### Gates Wired
- Gate 6b: `scripts/e2e/check_e2e_report.sh` — parses latest `dist/e2e-macbook-runs/<UTC>/report.html`; blocks on any dimension `status: FAIL`.
- Wired into `scripts/launch/cut_release.sh` immediately after Gate 2b — does NOT duplicate Gate 2b logic.
- Gate 2b (`scripts/release/check_gate.sh`) re-run unchanged — must return engineering-clean before 50a/50b pass marked PASS (REQ E2E-05).

### Privacy Fixture (REQ E2E-09)
- `tests/e2e/macbook/conftest.py::test_no_off_limits_write` — pytest fixture that snapshots `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/` mtime + file-count pre-run, re-snapshots post-run, asserts ZERO delta.
- Runs on EVERY e2e test invocation (not opt-in).

### Anti-Slop Coverage (REQ E2E-10)
- Sibling script: `scripts/audit/check_no_slop_e2e.py` (mirrors `check_no_slop_opp.py` precedent).
- Grep targets: `dist/e2e-macbook-runs/**/report.html` titles + sections.
- Uses same 15-token + `\bdeeply\s+\w+` blocklist as canonical `check_no_ai_slop.py`.
- Wired into CI alongside existing slop gates.

### Visual Regression (REQ E2E-03)
- Playwright + pixelmatch, `maxDiffPixelRatio: 0.02`.
- Baseline GLBs: Phase 47 placeholders at `tauri/ui/assets/mascot/animations/`.
- Re-baseline trigger: §VIS-04 discharge (real Mixamo retargets land).
- Surfaces snapshotted: mascot persona-smoke states + library page + live-session page (Tier-1 only — Tier-2 deferred).

### Worktree Invariant
- Every subagent prompt spawned under Phase 50 plans MUST include Step-0:
  ```
  Step 0: cd <worktree> && git fetch origin main && git merge origin/main --no-edit
  Verify: git rev-parse origin/main == merge-base with HEAD
  ```
- Plan-checker rejects any plan missing this block.
</decisions>

<invariants>
- **Privacy rule** — e2e harness writes ONLY to `dist/e2e-macbook-runs/` + `tests/e2e/macbook/__snapshots__/`. Fixture asserts on every run.
- **Anti-slop blocklist** — absolute on every `report.html` AND every commit message AND every UI string in scaffolded `report.html` template.
- **POC immutability** — e2e exercises v3.0 Tauri+Three.js production surface; `mascot.html` NEVER referenced. CI grep gate from Phase 47 already enforces.
- **IPC schema parity** — ZERO new IPC messages introduced. e2e probes existing 38-wrapper surface only.
- **ModelRouter seam** — audio-loopback fixture pins to VCR cassette baseline. NEVER inlines `gemini-*` literals; uses ModelRouter abstraction.
- **No live Gemini in CI** — VCR cassette replay only (REQ E2E-04).
- **No new model literals** — existing CI grep gate enforces.
</invariants>

<deferred>
- **§E2E-50A-WALK** (KAAN-ACTION-LEGAL) — Kaan executes MacBook walk + real DJ audio + screencast capture. Engineering ships harness + checklist; Kaan discharges.
- **§INSTALL-VM-RUN downstream** (KAAN-ACTION-LEGAL, carried from Phase 49) — fresh-VM matrix real execution on all 5 OS configs. Engineering ships dry-run + 2 reachable configs; full execution waits.
- **§VIS-04 re-baseline** — visual-diff baselines re-shoot after Mixamo real-asset land. Not a Phase 50 blocker.
- **30-session formal hallucination harness** — explicitly deferred per memory `project_phase_16_kaan_dj_testing`. NOT v3.1 scope.
- **Quantified SUS / NASA-TLX usability metrics** — out-of-scope per REQUIREMENTS § Future. Kaan-ear gates instead.
</deferred>

<scope_guardrails>
**OUT (would be scope creep, route to backlog if surfaced):**
- New IPC wrappers — schema is frozen.
- New AI providers — Gemini-only.
- CLAP / MERT / OpenL3 — memory `feedback_no_clap_use_gemini_embedding`.
- Stem separation features — memory `feedback_no_scope_creep_clean_utility`.
- Linux distribution — v3.2+.
- Auto-update silent installs — release-cycle decision.
- POC file edits — `cohost*.py` + `mascot.html` immutable.
- 30-session replay harness — explicitly NOT v3.1.
</scope_guardrails>

<success_criteria_recap>
1. `tests/e2e/macbook/` installs SHIPPED `.dmg` to `/Applications`, launches, exercises live-session golden path, produces structured `report.html` (E2E-01, E2E-02).
2. Playwright + pixelmatch `maxDiffPixelRatio: 0.02` against Phase 47 placeholder GLBs; audio-loopback fixture replays VCR cassette pinned to v3.0 GATE-02 (E2E-03, E2E-04).
3. Gate 2b re-run via `check_gate.sh` returns engineering-clean before pass marked PASS; Nielsen 10 checklist + 50a screencast committed (E2E-05, E2E-06, E2E-07).
4. `cut_release.sh` Gate 6b (`scripts/e2e/check_e2e_report.sh`) blocks on FAIL dimension; wired alongside Gate 2b without duplicating (E2E-08).
5. Pytest fixture asserts zero off-limits writes; sibling anti-slop script greens every report.html (E2E-09, E2E-10).
</success_criteria_recap>

<kaan_action_surface>
Surfaced to STATE.md Accumulated Context (additions for Phase 50):

- **§E2E-50A-WALK** — Kaan's MacBook walk (50a subjective pass). Needs: Kaan + real DJ-set audio + working signed `.dmg` on his MacBook. Engineering ships harness scaffold + Nielsen checklist + screencast capture rig + gap-closure routing. Kaan executes walk + records `docs/e2e/2026-05-walk.webm`.
- **§INSTALL-VM-RUN (carry-forward from Phase 49)** — 50b OS-matrix real-VM execution depends on this. Engineering scaffolds for all 5 configs + dry-runs 2; real-VM walk on all 5 waits on §INSTALL-VM-RUN + §INSTALL-COMPANION-SIGN.
</kaan_action_surface>

---
*Generated under `/gsd-autonomous fully` — auto-accepted grey-area answers; no AskUserQuestion pauses; blockers deferred to Kaan-action surface.*
