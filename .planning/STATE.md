---
gsd_state_version: 1.0
milestone: v7.0
milestone_name: Open House
status: ready for Wave 4 (10× flake-hunt + `docs/flake-hunt.md` protocol + quarantine any flake behind @pytest.mark.flaky + # issue: link)
last_updated: "2026-05-23T10:18:00.000Z"
last_activity: "2026-05-23 — Plan 67P04 SHIPPED. `.github/workflows/full-test-matrix.yml` (87 lines) runs the full marker × OS grid: `[macos-13, macos-14, windows-latest] × [default, macos_audio, windows_only, integration, slow, e2e, cli, network]` minus 3 impossible combinations (windows × macos_audio + mac × windows_only × 2) = 21 real jobs per push. Workflow-prefixed concurrency (`full-test-matrix-${{ github.ref }}`) cancels in-flight on the same ref. `fail-fast: false` so one OS failing doesn't kill the rest. `timeout-minutes: 30` per job. All 3 `uses:` SHA-pinned to the exact pins used by `eval.yml` + `dep-audit.yml` (checkout v4.3.1 + setup-python v5.6.0 + setup-uv v3.2.4). Security posture: `on: pull_request` (NOT `pull_request_target`) — no fork-PR privilege escalation; `permissions.contents: read` minimum scope; `GEMINI_API_KEY` sourced from existing GH Secret. README badge added at line 44 (after CycloneDX SBOM badge) using the same shields.io flat-square format + branch=main query param + bravoh-ai org slug as the 5 sibling badges. `KAAN-ACTION-LEGAL.md` got new §V7-LIVE-05 cluster (first-CI-green confirmation; owner-clock = Kaan's next push to GitHub) + Discharge tracking table row + Sign-off block line. Default `uv run pytest -q` GREEN at 4158 passed / 26 skipped / 4 xpassed / 0 failed (Wave 2 baseline preserved exactly; zero new tests added). `uv run pytest tests/repo/ -q` exits 0 at 282 passed (unchanged). Zero `src/vibemix/` edits; zero net-new deps. Commits `6cd0d3a` (workflow file) + `8c1482b` (README badge) + `809b66a` (§V7-LIVE-05). TEST-04 ENGINEERING SIDE SATISFIED; first-green observation is a one-push Kaan-clock discharge."
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
  percent: 0
---

# vibemix — State

**Last updated:** 2026-05-23 (Plans 67P01 + 67P02 + 67P03 + 67P04 SHIPPED) — **v7.0 "Open House" IN PROGRESS under `gsd-autonomous fully`.** Phase 67 Plan 67P04 (Wave 3 — `.github/workflows/full-test-matrix.yml` + README badge + §V7-LIVE-05 first-CI-green cluster) SHIPPED 2026-05-23: 87-line workflow runs the 21-job OS × marker exclude-matrix on every push to `main` + PR; workflow-prefixed concurrency cancel-in-progress; SHA-pinned actions (lifted from `eval.yml` + `dep-audit.yml`); `on: pull_request` not `pull_request_target` for fork-PR security; `permissions.contents: read`; `fail-fast: false`; `timeout-minutes: 30`. README badges row gets 1 new line at position 44 (mirrors the 5 sibling badges' format). KAAN-ACTION-LEGAL.md gets the §V7-LIVE-05 cluster (engineering side complete; first-green observation is Kaan's one-push clock). TEST-04 ENGINEERING SIDE SATISFIED. Commits `6cd0d3a` (workflow) + `8c1482b` (badge) + `809b66a` (§V7-LIVE-05). Wave 0+1+2 baselines preserved (default `pytest -q` 4158 passed / 26 skipped / 4 xpassed / 0 failed; `tests/repo/` 282 passed). Phase 67 Plan 67P03 (Wave 2 — static AST gates against silent skips + silent flakes) SHIPPED 2026-05-23: `tests/repo/test_no_silent_skips.py` (148 lines · AST-walk gate requiring `reason=` kwarg OR `# reason:` comment on every `@pytest.mark.skip` / `skipif` / `xfail`) + `tests/repo/test_no_silent_flakes.py` (126 lines · AST-walk gate requiring `# issue: https://github.com/.../issues/N` adjacency on every `@pytest.mark.flaky`, vacuously-green at landing). TEST-01 + TEST-03 anti-drift surfaces SATISFIED — future undocumented skip/xfail/flake additions fail CI at collection time. Default suite `uv run pytest -q` GREEN (4158 passed / 26 skipped / 4 xpassed / 0 failed — was 4156 in Wave 1, +2 for the new gates; Wave 0+1 invariant preserved). Zero `src/vibemix/` edits, zero net-new deps (stdlib ast + pathlib + re only). Phase 67 Plan 67P02 (Wave 1 — per-marker triage + §V7-LIVE discharge surface + xfail decorators on 11 Tier-B tests) SHIPPED 2026-05-23: 65 opt-in tests triaged into 54 Tier-A / 11 Tier-B / 0 Tier-C; 4 cluster sub-entries created in new `KAAN-ACTION-LEGAL.md ## §V7-LIVE` section (BlackHole-hosted-mac · Win 11 desktop SKU · FLX4 USB · live full-stack); `@pytest.mark.xfail(strict=False)` + `# reason:` comments applied to 11 Tier-B tests. TEST-02 "no marker is a graveyard" SATISFIED. Phase 67 Plan 67P01 (Wave 0) shipped earlier same day: 9 test-as-contract drift failures fixed; `flaky:` marker registered under --strict-markers; TEST-01 SC#1 + TEST-03 marker-declaration prerequisite SATISFIED. 4 phases (67–70), one per pillar (TEST · DEV · OSS · GH), 19/19 REQ-IDs mapped to exactly one phase (no orphans, no duplicates): TEST-01..04 → P67 (4) · DEV-01..05 → P68 (5) · OSS-01..05 → P69 (5) · GH-01..05 → P70 (5). **WIRING + DISCHARGE + POLISH milestone — zero new product capability**, zero new AI providers (CLAP / MERT / OpenL3 / torch all out, unchanged), zero new managed-memory frameworks (Mem0 / Letta / Zep / Cognee all out, unchanged), zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by zero-touch — no phase modifies the reaction path. **Dependency spine (strict left-to-right):** P67 dep-free (test infra) → P68 on P67's CI matrix → P69 on P68 (don't publish a broken catalog; OSS-04 actually fires `cut_release.sh v0.1.0-rc1` for real after §SHIP-V4 discharge — v4.0 SHIP closes alongside) → P70 on P69 (front-porch references real artifacts). **Acid test** for any v7.0 phase or plan: *"does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"* If neither, defer. v6.0's `VIBEMIX_RECALL_ENABLED=1` flip stays on its independent §RECALL-EAR Kaan-ear clock — not v7.0 scope.

---

### (prior) v6.0 "The Memory Turn" SHIPPED 2026-05-23 (tech_debt accepted) — 4/4 phases 63–66, 14/14 REQ-IDs, 6/6 integration seams WIRED, 53/53 must-haves, 247/247 v6.0 surface tests GREEN, zero net-new deps. STORE-01..04 + INGEST-01..03 + RECALL-01..04 + COPILOT-01..03. Memory-grounded copilot via local sqlite-vec store + ~50-line `MemoryStore` wrapper + off-hot-path session-ingest + existence-only `recall` evidence source + two visible copilot moves. Ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass (independent clock). Git tag deferred (consistent with v4.0/v5.0). Full archive: `.planning/milestones/v6.0-*`.

---

### (prior) v5.0 "The Useful Cut" SHIPPED 2026-05-22 (tech_debt accepted) — 4/4 phases 59–62, 17/17 REQ-IDs, 4/4 integration seams WIRED. Deck-aware + actionable coach + floating pill. P59=DECK-01..05 (deck-state ladder + citable `key:` source), P60=HARMONIC-01..04 (deterministic Camelot clash, default-OFF behind Kaan-ear veto), P61=COACH-01..04 (actionable-not-hype persona), P62=PILL-01..04 (floating pill = primary surface, mascot demoted/opt-in, mascot-audit green). KAAN-ACTION live-confirm items ride forward. `v5.0` tag deferred. Full archive: `.planning/milestones/v5.0-*`.

---

### (prior) v4.0 "SHIP" engineering-complete 2026-05-21 (8/8 phases 51–58, 19/19 REQ-IDs) — **kept OPEN, NOT archived per Kaan directive.** Public RC publish gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). `cut_release.sh --dry-run v0.1.0-rc1` exits GREEN — everything-but-the-signature ready; publish hard-guard regression-pinned. **v7.0's OSS-04 actually consumes this publish** — v4.0 closes alongside OSS-04 (KAAN-ACTION §SHIP-V4 discharge fires `cut_release.sh v0.1.0-rc1` for real, or routes to KAAN-ACTION if signatures haven't landed at execution).

---

## Project Reference

See: .planning/PROJECT.md (Current Milestone: v7.0 "Open House")

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **v7.0 thesis:** turn engineering-green into installable, contributable, install-anywhere OSS. Four pillars — TEST · DEV · OSS · GH — one phase per pillar (P67/P68/P69/P70). **Wiring + discharge + polish, zero new product capability.** Every phase reads as "verify / wire / discharge / generate / test" — never "build a new X". Anti-creep gated by the acid test: *"does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"*
- **Cardinal invariants verified by zero-touch:** the four cardinal invariants (single-writer · citation-grounding · trust-the-audio · one-socket) hold by construction because no v7.0 phase modifies the reaction path. v7.0 is a packaging/infrastructure/surface milestone, not a brain milestone.
- **Current focus:** Phase 67 (TEST · All Tests Pass) — Waves 0+1+2+3 SHIPPED (Plans 67P01 + 67P02 + 67P03 + 67P04) · Status: ready for Wave 4 (10× flake-hunt + `docs/flake-hunt.md` protocol)
- **Last shipped:** v6.0 "The Memory Turn" — 2026-05-23 (tech_debt accepted).
- **Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on Apple Dev Agreement + SignPath OSS cert (external clock). **Closes alongside v7.0 OSS-04.** NOT archived.
- **Project mode:** standard. **Granularity:** fine. **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously; only privacy rule + destructive risk + legal-capacity carveouts (Apple Dev + SignPath gating OSS-04) still pause. Soft Kaan-discharge gates (Kaan-felt landing-page sign-off in P70 §V7-LANDING, FLX4 live ear in P68 §V7-LIVE) surface to KAAN-ACTION but do NOT pause work.

---

## Current Position

Phase: 67 (TEST · All Tests Pass) — Wave 0 + Wave 1 + Wave 2 + Wave 3 SHIPPED · Status: in progress (4/5 plans)
Plan: 67P04 — Wave 3 `.github/workflows/full-test-matrix.yml` + README badge + §V7-LIVE-05 (SHIPPED 2026-05-23)
Status: ready for Wave 4 (`uv run pytest -q` × 10 consecutive runs flake-hunt + `docs/flake-hunt.md` protocol + quarantine any flake behind @pytest.mark.flaky + `# issue:` link — the 67P03 gate then enforces the link)
Last activity: 2026-05-23 — Plan 67P04 SHIPPED. Two new AST-walk static gates landed under `tests/repo/`: `test_no_silent_skips.py` (148 lines) enforces `reason=` kwarg OR `# reason:` comment on every `@pytest.mark.skip` / `skipif` / `xfail` decorator (passes against Wave 1's Tier-B fleet which carries both forms); `test_no_silent_flakes.py` (126 lines) enforces `# issue: https://github.com/.../issues/N` adjacency on every `@pytest.mark.flaky` decorator (vacuously-green at landing — 0 flaky decorators in tree; fires red on the first undocumented flake addition). Both use `ast.parse` + `ast.walk` (not regex) so multi-line decorators (e.g. `test_tts_3_1.py:164`'s 7-line skipif with wrapped reason) are handled correctly. Default `uv run pytest -q` GREEN at 4158 passed / 26 skipped / 4 xpassed / 0 failed (was 4156 in Wave 1, +2 for the new gates; Wave 0+1 invariant preserved). `uv run pytest tests/repo/ -q` exits 0 at 282 passed (was 280; +2 for the new gates). Negative controls verified for both gates (scratch violation file → red → revert → green); positive control verified for flake gate (scratch with valid issue link → green). Zero `src/vibemix/` edits; zero net-new deps. Commits `e5b7c98` (skip gate) + `dc29e3d` (flake gate). TEST-01 + TEST-03 anti-drift surfaces SATISFIED.

## v7.0 Phase Map

| Phase | Goal | Requirements (count) | Depends on | UI |
|-------|------|----------------------|-----------|----|
| 67 — All Tests Pass | Every collected test green across the full marker grid on Mac + Win; `.github/workflows/full-test-matrix.yml` runs the grid on every push to `main`; flake-hunt; no marker is a graveyard. Dependency-free, runs first. | TEST-01..04 (4) | — (first v7.0 phase) | — |
| 68 — All Devices Ready | 10 bundled MIDI profiles (FLX4/6/10/400/1000/SX3/XDJ-RX3/Party-Mix-Live/Inpulse-300/500) with contract test + synthetic-MIDI smoke + port_name_hint; duplicate `midi/controllers/` ↔ `midi/profiles/` catalogs reconciled to a single source of truth; hot-plug ≥3 profiles + KAAN-ACTION FLX4 live ear; audio backend matrix (BlackHole 2ch/16ch + WASAPI loopback + edge fallback) in CI; "Add Your Controller" contributor recipe verified end-to-end. | DEV-01..05 (5) | P67 (CI matrix) | — |
| 69 — OSS Fully Integrated | `CONTRIBUTING/CoC/SECURITY/MAINTAINERS.md` ship + presence-tested; Bravoh proxy production-hardened (per-install-UUID rate limit + token-bucket + Prom + Sentry + graceful offline fallback to "co-host unavailable this session"); `docs/byo-key.md` first-class BYO path; **`cut_release.sh v0.1.0-rc1` actually runs** after §SHIP-V4 discharge (signed Mac .dmg + signed Win .exe + CycloneDX/SPDX SBOM + Apache-2.0 NOTICE) — **v4.0 closes alongside**; Homebrew tap + Scoop bucket scaffolds check in + CI-validate but actual publish stays manual for v7.0 (split off as a future milestone). Under autonomous mode, OSS-04 routes to §SHIP-V4 if signatures haven't landed; rest ships unblocked. | OSS-01..05 (5) | P68 (don't publish a broken catalog) | — |
| 70 — GitHub Sexified, Generated, Tested | Real `docs/assets/demo.mp4` (30s hero film) replaces placeholder + §ASSETS-DEMO-CUT discharged; GitHub Pages landing at `bravoh-ai.github.io/vibemix` in CDJ-Whisper aesthetic (5 warm blacks + amber + Saira + JetBrains Mono, no Geist/Fraunces) Lighthouse a11y ≥95 + perf ≥90; OG card (1200×630) auto-generated from Tailwind+Puppeteer source + pinned SHA; all `docs/assets/` auto-generated from `docs/assets/sources/` (byte-identical reproducibility CI gate); `tests/repo/test_github_presence.py` one-stop repo-presence suite. **Kaan-felt sign-off on landing aesthetic rides §V7-LANDING** (engineering closes when auto-checks pass; felt sign-off does not gate close under autonomous mode). | GH-01..05 (5) | P69 (references real released artifacts) | yes (Tier-1 landing surface — `frontend-enforcement` skill governs) |

**Build-order rationale (dependency-correct):** TEST is dependency-free and ships the CI matrix every downstream pillar lands on; DEV's contract tests + hot-plug + audio matrix land on that CI green from day one; OSS reconciles the catalog before the artifacts go public + ships the docs/proxy/BYO + actually publishes (gated on the external signature clock — autonomous-mode contingency routes OSS-04 to KAAN-ACTION while the other 4 OSS reqs ship); GH front-porch points at the actual released artifacts. The four cardinal invariants hold by zero-touch — no phase modifies the reaction path. v6.0's `VIBEMIX_RECALL_ENABLED=0` default stays unchanged (independent §RECALL-EAR Kaan-ear clock).

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action) |
| Phases complete (v2.1) | 13 / 13 engineering-green |
| Phases complete (v3.0) | 6 / 6 engineering-green (22 carveouts → KAAN-ACTION-LEGAL) |
| Phases complete (v3.1) | 5 / 5 engineering-green (7 carveouts on external clock) |
| Phases complete (v4.0) | 8 / 8 engineering-green (publish on external signature clock; **closes alongside v7.0 OSS-04**) |
| Phases complete (v5.0) | 4 / 4 engineering-green (KAAN-ACTION live-confirm items ride forward) |
| Phases complete (v6.0) | 4 / 4 engineering-green (§RECALL-EAR + §LIVE-EMBED ride forward) |
| v7.0 phase count | 4 (Phases 67–70) |
| Phases complete (v7.0) | 0 / 4 — Phase 67 in progress (4/5 plans shipped) |
| Plans complete (v7.0) | 4 / 5+ (67P01 + 67P02 + 67P03 + 67P04 SHIPPED 2026-05-23 — default-grid green + flaky marker + §V7-LIVE discharge surface + 11 Tier-B xfail decorators + 2 static AST gates against silent skips/flakes + 21-job OS × marker CI matrix workflow + README badge + §V7-LIVE-05 first-CI-green cluster) |
| v7.0 REQ-IDs mapped | 19 / 19 ✓ (100% coverage, no orphans, no duplicates) |
| v7.0 REQ-IDs complete | 4 / 19 (TEST-01 SC#1 + TEST-03 marker-decl prerequisite via 67P01; TEST-02 "no marker is a graveyard" via 67P02; TEST-01 + TEST-03 anti-drift surfaces via 67P03; TEST-04 engineering-side via 67P04 [first-CI-green observation rides §V7-LIVE-05 Kaan-clock]) |
| v7.0 per-phase REQ counts | P67=4 (TEST) · P68=5 (DEV) · P69=5 (OSS) · P70=5 (GH) |
| v7.0 net-new dependencies | 0 (WIRING + DISCHARGE + POLISH milestone — no new product capability) |
| v7.0 net-new ws ports | 0 (one-socket invariant held) |
| v7.0 net-new IPC envelopes | 0 (zero-touch on reaction path) |
| Default `pytest -q` (Phase 67 baseline) | 4158 passed / 26 skipped / 4 xpassed / 0 failed (exit 0) — Plan 67P04 preserves Wave 2 baseline exactly (workflow YAML is data, not Python — pytest doesn't collect `.github/workflows/`); 4 xpasses unchanged = Tier-B tests on Kaan's Mac |
| `tests/repo/` count | 282 passed (Wave 2 baseline preserved exactly through Wave 3) |
| §V7-LIVE clusters (Phase 67P02 + 67P04 ledger) | 5 clusters · 11 Tier-B tests + 1 workflow · ☐ all pending Kaan-discharge — §V7-LIVE-05 (first-CI-green observation) added by 67P04 |
| v4.0 git tag | local artifacts on `live-tuning-or-brain`; unsigned `v0.1.0-rc1` .dmg built — closes alongside v7.0 OSS-04 |
| External signature clock | Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA) — gates ONLY OSS-04 in v7.0; routes to §SHIP-V4 under autonomous mode if not landed at execution |

---

## Accumulated Context

### v7.0 Roadmap Decisions Locked (2026-05-23)

v7.0 "Open House" roadmapped into **4 phases (67–70)** continuing numbering from v6.0 (ran 63–66) — NO reset. 19/19 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates). One phase per pillar — TEST · DEV · OSS · GH — per the REQUIREMENTS.md pre-decided structure. Every phase reads as "verify / wire / discharge / generate / test" — no phase grows the product surface.

**Why one phase per pillar (and not finer-grained per fine-granularity default).** The 4-pillar decomposition is *pre-decided* in REQUIREMENTS.md (Kaan's milestone framing) — the requirements are already pillar-sized (4/5/5/5 reqs per pillar), each pillar is internally coherent (a single goal: "tests green" / "devices ready" / "OSS shipped" / "front-porch finished"), and the cross-pillar dependencies are strict left-to-right (P67 → P68 → P69 → P70). Splitting a pillar into multiple phases would manufacture artificial seams without delivering finer verifiability — each pillar's success criteria are already a 4-5-item observable checklist. Fine granularity applies *within* each phase via plan decomposition, not by inflating phase count.

**Critical-path / autonomous-mode contingencies:**

- **OSS-04 signature contingency:** `cut_release.sh v0.1.0-rc1` has a hard external dependency on Apple Dev Agreement (Francesco) + SignPath OSS Foundation cert (Kaan) — both on the clock since v3.0. Under `gsd-autonomous fully`: if signatures haven't landed by phase execution, OSS-04 routes to `KAAN-ACTION-LEGAL.md §SHIP-V4` with the exact pre-staged `cut_release.sh v0.1.0-rc1` invocation, the publish hard-guard stays absolute, and OSS-01/02/03/05 ship unblocked (none depend on signatures). v4.0 stays open until OSS-04 fires for real. This is the defensible answer — engineering ship-ready in the same milestone, publish closes when the clock catches up.
- **GH-01 §ASSETS-DEMO-CUT discharge:** the real 30-sec demo film is gated on Francesco's capture day per v3.0 P43 VIS-09 runbook — surface in P70 plan, route to KAAN-ACTION if Francesco hasn't shot it by execution.
- **GH-02 Kaan-felt landing sign-off:** the CDJ-Whisper aesthetic is a taste gate, not an automated check — engineering closes when auto-checks pass (Lighthouse + anti-backsliding grep + visual asset reproducibility), the felt sign-off rides `§V7-LANDING` (new KAAN-ACTION-LEGAL section to create in plan).
- **DEV-03 FLX4 live ear + DEV-04 real BlackHole/WASAPI capture + DEV-05 contributor smoke:** all route to `KAAN-ACTION-LEGAL.md §V7-LIVE` (new section to create in plan) — the engineering side ships green in CI with mocks; the live confirmation is Kaan's clock.
- **TEST-02 65 opt-in tests on real hardware:** any test that can't pass on `macos-13/14` + `windows-latest` GH runners (BlackHole-real / FLX4-real / etc.) documents its failure-mode in `§V7-LIVE` and stays opt-in — never a graveyard, always a fix-path entry.

**Cardinal invariants verified by zero-touch.** Every v7.0 phase is asked: "does this modify any prompt, evidence source, emission path, or reaction-time module?" Answer for all four phases: NO. P67/P68 are test infrastructure + device contracts; P69 is OSS docs + proxy hardening + release publish (all outside `src/vibemix/{coach,state,agent,runtime,memory,library,grounding}`); P70 is docs + assets + presence tests. The cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by construction.

**Scope rule acid test applied to every requirement.** Every REQ-ID in REQUIREMENTS.md was checked against "does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?" — 19/19 pass. No requirement proposes a new feature, new dep, new socket, new IPC envelope, or new prompt change. The two "grey-area" candidates that would have failed this test (multi-language localization · Homebrew/Scoop *publish*) are explicitly deferred in REQUIREMENTS.md §Future.

### v7.0 KAAN-ACTION / External-Clock Flags (carry into planning)

- **P67 — TEST-02 live opt-in matrix (KAAN-ACTION, soft):** Mac + Win 11 VM execution of the 65 currently-deselected opt-in tests. CI side ships mocked; live confirmation routes to `§V7-LIVE`.
- **P67 — TEST-04 first-CI-green observation (KAAN-ACTION, soft):** `.github/workflows/full-test-matrix.yml` ships engineering-complete in 67P04 (87 lines, 21-job matrix, SHA-pinned, security-correct); first-green observation requires the next push to GitHub to fire the workflow on hosted runners. Routes to `§V7-LIVE-05`.
- **P68 — DEV-03 / DEV-04 / DEV-05 live hardware (KAAN-ACTION, soft):** FLX4 plug/unplug ear-pass, real BlackHole + WASAPI capture, contributor recipe < 30-min smoke. CI side ships mocked; live confirmation routes to `§V7-LIVE`.
- **P69 — OSS-04 external signature clock (KAAN-ACTION, hard):** Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA) — gates the actual `gh release create v0.1.0-rc1`. Routes to `§SHIP-V4` if not landed at execution. **v4.0 SHIP closes alongside.** OSS-01/02/03/05 ship unblocked.
- **P69 — OSS-02 Bravoh proxy production hardening (engineering side — autonomous):** per-install-UUID rate limit + token-bucket + Prom + Sentry + graceful client-side fallback. Lives in the `api.altidus.world` proxy repo (separate from vibemix OSS); coordination point with Bravoh deployment.
- **P70 — GH-01 §ASSETS-DEMO-CUT (KAAN-ACTION, soft):** Francesco's 30-sec demo capture day per v3.0 P43 VIS-09 runbook. CI side ships placeholder-detection green; real asset routes to `§V7-LANDING`.
- **P70 — GH-02 Kaan-felt landing aesthetic sign-off (KAAN-ACTION, soft):** the CDJ-Whisper hold is taste-gated, not auto-checked. Engineering closes when auto-checks pass; felt sign-off rides `§V7-LANDING`.

### Anti-slop invariants baked into v7.0 success criteria

- **Proxy-offline fallback (OSS-02):** when the Bravoh proxy is offline, the pill/mascot says "co-host unavailable this session" — NOT a crash, NOT a hallucinated coach line. The brain refusing to lie when its grounding is missing is on-thesis.
- **Demo asset honesty (GH-01):** the README's `<video src>` hash sentinel must match a real, non-placeholder, ≤8MB asset. A placeholder sentinel passing CI is a regression and the hash check catches it.
- **Anti-backsliding gate (GH-02):** `grep -ri 'geist\|fraunces' docs/landing/` returns zero matches — the CDJ-Whisper typography lock from v3.0/v5.0 holds.
- **Visual asset reproducibility (GH-04):** every `docs/assets/` artifact is byte-identical-reproducible from `docs/assets/sources/` via `scripts/regenerate_assets.sh` — eliminates "lost the original Figma file" rot.
- **OSS files presence-tested (OSS-01):** `tests/repo/test_oss_presence.py` catches a contributor docs deletion before it ships.
- **Four cardinal invariants:** held by zero-touch (no v7.0 phase modifies the reaction path).

### v6.0 carry-forward context (for reference — does NOT modify behavior in v7.0)

v6.0's memory-grounded copilot ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass (independent clock). v7.0 does NOT touch the flag default. The reuse map under `src/vibemix/library/` + `src/vibemix/memory/` is untouched. Tests under `tests/memory/` are part of the default `pytest -q` grid that TEST-01 must hold green.

---

## Session Continuity

**Next command:** execute Phase 67 Wave 4 — `/gsd:execute-phase 67` (the next plan in the wave map; planner produces 67P05 for the 10× flake-hunt + `docs/flake-hunt.md` protocol + quarantine pattern).

**What's done:** **v7.0 "Open House" ROADMAPPED + Phase 67 Plans 67P01 + 67P02 + 67P03 + 67P04 SHIPPED.** Plan 67P04 (Wave 3) landed the CI matrix surface: `.github/workflows/full-test-matrix.yml` (87 lines · 21-job OS × marker matrix · workflow-prefixed concurrency cancel-in-progress · SHA-pinned actions lifted from `eval.yml` + `dep-audit.yml` · `on: pull_request` not `pull_request_target` · `permissions.contents: read` · `fail-fast: false` · `timeout-minutes: 30`); README badge at line 44 mirrors the 5 sibling badges' format (flat-square + ?label=tests&branch=main); §V7-LIVE-05 first-CI-green cluster added to `KAAN-ACTION-LEGAL.md` for the Kaan-clock one-push discharge. Commits `6cd0d3a` (workflow) + `8c1482b` (badge) + `809b66a` (§V7-LIVE-05). Default `uv run pytest -q` GREEN at 4158 / 26 / 4 / 0 (Wave 2 baseline preserved exactly — zero new tests, zero regressions). `uv run pytest tests/repo/ -q` exits 0 at 282 passed. Zero `src/vibemix/` edits; zero net-new deps. TEST-04 ENGINEERING SIDE SATISFIED; first-green observation rides §V7-LIVE-05 (Kaan's next push). Plan 67P03 (Wave 2) landed the two static AST gates that lock the test-as-contract surface against future drift: `tests/repo/test_no_silent_skips.py` (148 lines · AST-walk gate requiring `reason=` kwarg OR `# reason:` comment within 2 lines above every `@pytest.mark.skip` / `skipif` / `xfail` decorator) + `tests/repo/test_no_silent_flakes.py` (126 lines · AST-walk gate requiring `# issue: https://github.com/.../issues/N` adjacency on every `@pytest.mark.flaky` decorator). Both use `ast.parse` + `ast.walk` (not regex) so multi-line decorators (the live witness: `tests/llm/test_tts_3_1.py:164`'s 7-line skipif with wrapped `reason=` across 4 lines) are handled correctly. Skip gate passes against current tree (28 existing `skipif` decorators all carry `reason=`; 11 Wave 1 Tier-B `xfail` decorators carry both `reason=` AND `# reason:` comment — the dual-channel Wave 1 shape). Flake gate vacuously-green at landing (0 flaky decorators in tree — fires red on the first undocumented flake). Default `uv run pytest -q` GREEN at 4158 passed / 26 skipped / 4 xpassed (+2 from Wave 1's 4156 = the new gates; Wave 0+1 invariant preserved). `uv run pytest tests/repo/ -q` GREEN at 282 passed (+2 from 280). Negative controls verified locally for both gates; positive control verified for the flake gate (valid issue link → green). Zero `src/vibemix/` edits; zero net-new deps (stdlib `ast` + `pathlib` + `re` only). TEST-01 + TEST-03 anti-drift surfaces SATISFIED. Commits `e5b7c98` (skip gate) + `dc29e3d` (flake gate). Earlier same day: Plan 67P02 (Wave 1) triaged 65 opt-in tests into 54 Tier-A / 11 Tier-B / 0 Tier-C; created `## §V7-LIVE` section in `KAAN-ACTION-LEGAL.md`; applied 11 Tier-B `xfail(strict=False)` decorators. Plan 67P01 (Wave 0) flipped default suite from 9-red to 0-red + registered `flaky:` marker.

**What's next:** Phase 67 Wave 4 — `/gsd:plan-phase 67` produces 67P05: 10× consecutive `uv run pytest -q` flake-hunt loop + `docs/flake-hunt.md` documents the protocol + quarantine any non-deterministic test surfaced behind `@pytest.mark.flaky` + `# issue: https://github.com/.../issues/N` link (the 67P03 gate then enforces the link). The wave map per RESEARCH.md: Wave 0 ✓, Wave 1 ✓, Wave 2 ✓, Wave 3 ✓ (this plan), Wave 4 (the flake-hunt). Then P68 (DEV) on P67's CI matrix — every controller profile contract test + hot-plug integration + audio backend matrix lands on the workflow this wave just shipped. Then P69 (OSS) on P68, then P70 (GH) on P69. OSS-04 has the external Apple Dev + SignPath clock — under autonomous mode, routes to §SHIP-V4 if not landed; other 18 reqs ship unblocked. v4.0 SHIP closes alongside OSS-04.

**Open before next execution:** none blocking. Default-grid baseline is 4158 passed + 4 xpassed = 4162 non-failures + 26 skipped — exit-0 preserved through Wave 3 (workflow YAML is data, not Python; pytest doesn't collect it). The five §V7-LIVE-NN clusters await Kaan's clocks: §V7-LIVE-01..04 (3 BlackHole + 5 windows_only + 1 FLX4 + 2 live-full-stack tests = 11 Tier-B test discharges per 67P02) + §V7-LIVE-05 (first-CI-green observation = Kaan's next push to GitHub fires the workflow on hosted runners — 21 jobs scheduled; default × 3 GREEN; macos_audio × 2 AMBER per §V7-LIVE-01 xfails; etc.). All 5 clusters are soft Kaan-discharge under `gsd-autonomous fully` — engineering side is GREEN; live confirmation rides Kaan's clock. The original KAAN-ACTION soft items (FLX4 ear / proxy hardening / Francesco demo cut / Kaan landing sign-off) still route to §V7-LIVE + §V7-LANDING.

---

## Deferred Items

Items acknowledged and deferred at v7.0 milestone start on 2026-05-23 (all intentional KAAN-ACTION carry-forwards per `gsd-autonomous fully` directive — inherited from v4.0 SHIP + v5.0 + v6.0; v7.0 adds soft sign-off items to be created during plan execution):

| Category | Phase | Status | Note |
|----------|-------|--------|------|
| verification | 51 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 53 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 54 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 55 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 56 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 57 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 58 | human_needed | v4.0 SHIP — closes alongside v7.0 OSS-04 (external signature clock) |
| verification | 59 | human_needed | v5.0 SHIPPED — KAAN-ACTION live-confirm |
| verification | 60 | human_needed | v5.0 SHIPPED — KAAN-ACTION live-confirm (harmonic veto flip) |
| verification | 61 | human_needed | v5.0 SHIPPED — KAAN-ACTION live-confirm (coach live-ear) |
| verification | 62 | human_needed | v5.0 SHIPPED — KAAN-ACTION live-confirm (pill live-ear) |
| verification | 66 | human_needed | v6.0 §RECALL-EAR (felt-quality discharge) |
| uat | 54 | partial (2 open) | v4.0 SHIP HUMAN-UAT |
| uat | 55 | partial (2 open) | v4.0 SHIP HUMAN-UAT |
| uat | 56 | partial (4 open) | v4.0 SHIP HUMAN-UAT |
| uat | 57 | partial (5 open) | v4.0 SHIP HUMAN-UAT |
| uat | 58 | partial (4 open) | v4.0 SHIP HUMAN-UAT |
| uat | 66 | partial (4 open) | v6.0 §RECALL-EAR HUMAN-UAT |
| v7.0 soft | 67 | created (5 clusters pending discharge) | TEST-02 11 Tier-B tests on real hardware → `§V7-LIVE-01..04` (created in 67P02; ☐ all pending Kaan-discharge) + TEST-04 first-CI-green observation → `§V7-LIVE-05` (created in 67P04; ☐ pending Kaan's next push) |
| v7.0 soft | 68 | to create in plan | DEV-03 FLX4 live ear + DEV-04 BlackHole/WASAPI live + DEV-05 contributor smoke → `§V7-LIVE` |
| v7.0 hard | 69 | to create in plan | OSS-04 external signatures (Apple Dev + SignPath) → `§SHIP-V4` discharge |
| v7.0 soft | 70 | to create in plan | GH-01 Francesco demo cut → `§V7-LANDING` (or existing §ASSETS-DEMO-CUT) + GH-02 Kaan-felt landing aesthetic sign-off → `§V7-LANDING` |

**Total deferred at v7.0 start: 22 items** (12 verification gaps + 6 UAT gaps inherited from v4.0/v5.0/v6.0 + 4 v7.0 soft/hard items to be formalized in plan execution). None block v7.0 engineering close under autonomous mode; OSS-04 alone gates the *publish* (which closes v4.0 SHIP alongside).

## Historical Audit Annotations

Retained for audit-trail continuity (Plan 42-05 spec was annotate-not-delete; pinned by `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`):

- **Phase 16 ear-test memory override — RETIRED.** The v2.1 P85 autonomous-only override (Phase 16 ear-test memory override, accepted as a one-milestone carveout per `gsd-autonomous fully` mode while Kaan's ear was deferred) is formally retired as of Plan 42-05 (2026-05-16). Replaced by the v3.0 hybrid hallucination gate (`scripts/release/check_gate.sh` + `check_ear_test.sh`) wired into `cut_release.sh` at Gate 2b. Cross-reference: `.planning/decisions/P85-OVERRIDE-RETIRED.md`.

## Operator Next Steps

- Execute Phase 67 Wave 4 via `/gsd:plan-phase 67` (next plan = 67P05: 10× consecutive `uv run pytest -q` flake-hunt + `docs/flake-hunt.md` protocol + quarantine any flake found behind `@pytest.mark.flaky` + `# issue: https://github.com/.../issues/N` link — the 67P03 gate then enforces the link).
