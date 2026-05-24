# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v6.0 "The Memory Turn" — 2026-05-23 (tech_debt accepted; KAAN-ACTION §RECALL-EAR rides forward on Kaan-ear clock)
**Current milestone:** v7.0 "Open House" — ACTIVE (planning) — Phases 67–70
**Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on the external Apple Dev + SignPath signature clock (NOT archived) — **v7.0's OSS pillar consumes this publish (`OSS-04` discharges §SHIP-V4 for real)**

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🟡 **v4.0 SHIP** — Phases 51–58 (engineering-complete 8/8, publish on signature clock — NOT archived; closes alongside v7.0 OSS-04) — see `.planning/milestones/v4.0-ROADMAP.md`
- ✅ **v5.0 The Useful Cut** — Phases 59–62 (shipped 2026-05-22, tech_debt accepted) — see `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v6.0 The Memory Turn** — Phases 63–66 (shipped 2026-05-23, tech_debt accepted) — see `.planning/milestones/v6.0-ROADMAP.md`
- 🔵 **v7.0 Open House** — Phases 67–70 (ACTIVE — planning) — see "v7.0 Open House" section below

---

# v7.0 "Open House" — ACTIVE (planning)

> **Status:** Active milestone. vibemix is turned from "engineering-green, gated on external clock" into a **publishable, contributable, install-anywhere open-source project** that strangers can clone, install, run, and contribute to — warming visitors into Bravoh waitlist signups along the way. **This is a WIRING + DISCHARGE + POLISH milestone with ZERO new product capability** — every phase closes an existing loop. No new AI providers, no new managed-memory frameworks, no new ws ports, no new IPC envelopes (CLAP / MERT / OpenL3 / torch / Mem0 / Letta / Zep / Cognee all out, unchanged from v6.0). v6.0's `VIBEMIX_RECALL_ENABLED=1` default flip stays on its independent §RECALL-EAR Kaan-ear clock — not v7.0 scope.

## Overview (v7.0)

v6.0 left vibemix engineering-green with a memory-grounded copilot wired but flag-default-off, alongside v4.0's engineering-complete `cut_release.sh --dry-run v0.1.0-rc1` green-but-unsigned. The product is *functionally* there. The OSS posture isn't. Strangers can't yet clone-install-run; the 65 opt-in tests aren't proven on real hardware; the 10 bundled MIDI profiles have shipped catalog duplication (`midi/controllers/` ↔ `midi/profiles/`); the README `<video src="docs/assets/demo.mp4">` still points at a placeholder; the OSS-required files (`CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `MAINTAINERS.md`) don't exist; the Bravoh-side Gemini proxy at `api.altidus.world` isn't hardened for adversarial public traffic; and the `v0.1.0-rc1` publish still hasn't actually shipped — `cut_release.sh` has been one-button-after-signatures for months. v7.0 closes all four loops in one milestone: **TEST → DEV → OSS → GH** (test infrastructure first, then the controller catalog it gates on, then the OSS surface that ships the result, then the GitHub front-porch that points at the artifacts).

The journey, finer-grained so each pillar is its own independently-verifiable checkpoint: **all tests pass on the full marker grid in CI** (Phase 67) → **the 10 bundled controllers + Mac/Win audio backends are live-verified end-to-end with a contributor recipe for adding more** (Phase 68) → **the OSS surface ships (contributor docs + Bravoh-proxy production-hardening + `v0.1.0-rc1` actually publishes, gated on external Apple Dev + SignPath clock)** (Phase 69) → **the GitHub front-porch is finished — real demo, landing page in CDJ-Whisper aesthetic, repo-presence test suite, auto-generated assets from source** (Phase 70).

**Dependency spine — strict left-to-right, no shortcuts:**

- **Phase 67 (TEST)** is dependency-free — start here, runs in parallel CI matrix. Test infrastructure must be green before downstream phases trust it.
- **Phase 68 (DEV)** depends on Phase 67's full-test-matrix workflow — every controller profile contract test + hot-plug integration + audio backend matrix lands on the workflow Phase 67 ships, so green badges appear from day one.
- **Phase 69 (OSS)** depends on Phase 68 (don't ship a release with a broken or duplicated controller catalog) and is the **publish phase** — `OSS-04` actually fires `cut_release.sh v0.1.0-rc1` for real, gated on the external Apple Dev + SignPath clock (KAAN-ACTION §SHIP-V4 discharge). If the signature clock hasn't landed by execution, OSS-04 routes to KAAN-ACTION and the rest of the OSS pillar ships unblocked (`CONTRIBUTING.md` / proxy-hardening / BYO-key docs / Homebrew + Scoop scaffolds all parallelize and have no signature dependency). v4.0 closes alongside OSS-04.
- **Phase 70 (GH)** depends on Phase 69 (the README + landing page reference the actual released artifacts — broken links to a non-existent `v0.1.0-rc1` release would be worse than no release) and is the **front-porch finish** — includes a **Kaan-felt sign-off checkpoint** on the landing-page aesthetic (CDJ-Whisper hold: 5 warm blacks + single amber accent + Saira + JetBrains Mono — no Geist/Fraunces backsliding) since visual taste is the bar.

**External-clock items:** Apple Dev Agreement signed by Francesco + SignPath OSS Foundation cert grant (both ride forward from v3.0/v3.1/v4.0). Both are routed to `KAAN-ACTION-LEGAL.md §SHIP-V4`. They gate **only OSS-04** (the actual `gh release create` publish); everything else in v7.0 is engineering-shippable under `gsd-autonomous fully` without them.

**Cardinal invariants verified by zero-touch.** v7.0 changes no prompt, no evidence source, no emission path. The four cardinal invariants (single-writer · citation-grounding · trust-the-audio · one-socket) hold by construction because no phase modifies the reaction path. This is a **packaging / infrastructure / surface milestone**, not a brain milestone.

**Acid test for any v7.0 phase or plan:** *"does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"* If neither, defer.

## Phases (v7.0)

**Phase Numbering:** Continues from v6.0 (closed at Phase 66). v7.0 starts at **Phase 67** and runs through **Phase 70**. Integer phases (67, 68, 69, 70) = planned milestone work; decimal phases (e.g. 69.1) = urgent insertions if needed.

- [ ] **Phase 67: All Tests Pass** — Every collected test green across the full marker grid (default + macos_audio + windows_only + integration + slow + e2e + cli + network) on Mac + Win, flake-hunted, with a `full-test-matrix.yml` CI workflow running it on every push to `main`. No marker is a graveyard. Dependency-free, runs first. (TEST-01..04 — 4 reqs)
- [x] **Phase 68: All Devices Ready** — All 10 bundled MIDI profiles (DDJ-FLX4 · FLX6 · FLX10 · 400 · 1000 · SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300 · Inpulse 500) have schema-valid contract tests + synthetic-MIDI smoke + documented port_name_hint; the duplicate `midi/controllers/` ↔ `midi/profiles/` catalogs reconciled to a single source of truth; hot-plug verified across ≥3 profiles + KAAN-ACTION live FLX4 ear-pass; audio backend matrix (BlackHole 2ch/16ch + WASAPI loopback + edge fallback) covered in CI with mocked CoreAudio + WASAPI; a "Add Your Controller" contributor recipe at `docs/contributing/add-a-controller.md` verified end-to-end. Depends on P67. (DEV-01..05 — 5 reqs) — **ENGINEERING-COMPLETE 2026-05-23** (Waves 0-4 / 68P01..68P05 all shipped; DEV-01..05 closed engineering-side; §V7-LIVE-07..10 KAAN-ACTION clusters route live-hardware confirmations to Kaan's clock under `gsd-autonomous fully`)
- [ ] **Phase 69: OSS Fully Integrated** — `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `MAINTAINERS.md` ship at the repo root + are covered by a presence test; the Bravoh-side Gemini proxy at `api.altidus.world` is production-hardened (per-install-UUID rate limit + token-bucket + Prom + Sentry + graceful client-side fallback when offline); `docs/byo-key.md` documents the first-class "Bring Your Own Gemini API key" path; **`cut_release.sh v0.1.0-rc1` actually runs (not `--dry-run`)** with Apple Dev + SignPath landed (KAAN-ACTION §SHIP-V4 discharge), publishing signed Mac `.dmg` + signed Windows `.exe` + SBOMs + Apache-2.0 NOTICE — **v4.0 "SHIP" closes alongside**; Homebrew tap + Scoop bucket scaffolds check in and validate via CI (`brew audit` + `scoop checkver`) but tap/bucket *push* stays manual for v7.0 (split off as a future milestone). Depends on P68. (OSS-01..05 — 5 reqs)
- [ ] **Phase 70: GitHub Sexified, Generated, Tested** — Real `docs/assets/demo.mp4` (30s hero film) lands at the path the README `<video src>` already points at; `scripts/check_readme_hero_hash.py` updates from `PLACEHOLDER` to a real SHA-256; GitHub Pages landing at `bravoh-ai.github.io/vibemix` in the CDJ-Whisper aesthetic (5 warm blacks + single amber + Saira + JetBrains Mono, no Geist/Fraunces) with Lighthouse a11y ≥ 95 + perf ≥ 90; OG/social card at `docs/assets/og-card.png` (1200×630) generated from a Tailwind + Puppeteer template, pinned at a known SHA-256; **every visual asset in `docs/assets/` auto-generated from sources in `docs/assets/sources/`** (re-running `scripts/regenerate_assets.sh` produces byte-identical outputs); `tests/repo/test_github_presence.py` is the one-stop repo-presence suite (badges + demo + OG + hero hash + issue templates + PR template + 4 OSS files). **Kaan-felt sign-off on the landing-page aesthetic is the hard gate.** Depends on P69. (GH-01..05 — 5 reqs)

## Phase Details (v7.0)

### Phase 67: All Tests Pass
**Goal**: Every collected test in the repo passes green across the full marker grid (default + every opt-in marker individually) on Kaan's Mac + a Windows 11 VM, flake-hunted, with a `.github/workflows/full-test-matrix.yml` CI workflow running the entire grid on `macos-13` + `macos-14` + `windows-latest` for every push to `main` and every PR. This is the foundation: no downstream pillar can trust the test suite as a contract until 100% is green and CI proves it stays that way. The 65 currently-deselected opt-in tests either pass on real hardware or have their failure mode documented in `KAAN-ACTION-LEGAL.md §V7-LIVE` with a concrete fix path. No marker becomes a graveyard.
**Depends on**: Nothing (first v7.0 phase — DEV/OSS/GH all lean on its green CI matrix)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. A third-party engineer cloning `main` and running `pytest -q` sees an exit code of 0 with no uncategorized failures — every existing skip / xfail / xpass carries a one-line `# reason:` adjacent to its marker explaining why, OR has been converted to a `KAAN-ACTION-LEGAL.md §V7-LIVE` external-clock item with a fix path. Verified by inspecting `pytest -q` output + `grep -rn '@pytest.mark.skip\|@pytest.mark.xfail' tests/`.
  2. Running the full opt-in grid `pytest -m "macos_audio or windows_only or integration or slow or e2e or cli or network"` exits green on Kaan's Mac + a Windows 11 VM — the 65 currently-deselected tests either pass or each failure-mode is documented in `KAAN-ACTION-LEGAL.md §V7-LIVE`. Verified by inspecting per-marker pytest output + a count of `tests collected` matching what `pytest --collect-only -q` reports.
  3. A 10× consecutive re-run of `pytest -q` reveals no test below 100% pass rate, OR any non-deterministic test is quarantined behind a `@pytest.mark.flaky` decorator with a linked GitHub issue. A static gate at `tests/repo/test_no_silent_flakes.py` catches new `@pytest.mark.flaky` decorators that don't carry an issue link — verified by adding a no-issue-link flaky decorator in a scratch PR and watching CI go red.
  4. `.github/workflows/full-test-matrix.yml` exists, runs the full marker grid (default + each opt-in marker individually) on `macos-13` + `macos-14` + `windows-latest` on every push to `main` and every PR, and a green badge for it appears in the README badges row. Verified by opening the workflow run page on `main` HEAD + confirming the badge URL in `README.md` resolves 200 to a green SVG.
**Plans**: 5 plans
- [x] 67P01-PLAN.md — Wave 0: fix the 8 currently-red default tests + register the `flaky` marker in `pyproject.toml` (TEST-01, TEST-03) — SHIPPED 2026-05-23 (commit a08594d)
- [x] 67P02-PLAN.md — Wave 1: triage the 65 opt-in tests Tier-A/B/C + create the `§V7-LIVE` section + xfail decorate all Tier-B tests (TEST-01, TEST-02) — SHIPPED 2026-05-23 (commits 6f79943 + 293135c; §V7-LIVE has 4 cluster sub-entries; 11 Tier-B tests carry xfail(strict=False))
- [x] 67P03-PLAN.md — Wave 2: build the two static gates `test_no_silent_skips.py` + `test_no_silent_flakes.py` (TEST-01, TEST-03) — SHIPPED 2026-05-23 (commits e5b7c98 + dc29e3d; AST-walk gates accept Wave 1 Tier-B decorator shape; flake gate vacuously-green at landing; negative controls verified)
- [x] 67P04-PLAN.md — Wave 3: ship `.github/workflows/full-test-matrix.yml` + add README badge (TEST-02, TEST-04) — SHIPPED 2026-05-23 (commits 6cd0d3a + 8c1482b + 809b66a; 87-line workflow with OS × marker exclude-matrix [8 markers × 3 OSes − 3 excludes = 21 jobs], SHA-pinned actions, workflow-prefixed concurrency, on: pull_request not pull_request_target, fail-fast: false, timeout-minutes: 30; new badge in README line 44 matching the 5 sibling badges' format; §V7-LIVE-05 first-CI-green cluster added to KAAN-ACTION-LEGAL.md for the Kaan-clock first-push discharge)
- [x] 67P05-PLAN.md — Wave 4: 10× flake-hunt + document the protocol in `docs/flake-hunt.md` + quarantine any flake found (TEST-03)

### Phase 68: All Devices Ready
**Goal**: All 10 bundled MIDI controller profiles are live-verified end-to-end as data contracts — each has a schema-valid contract test, a synthetic-MIDI smoke that exercises every CC + NOTE through `find_mapping` → `ControllerState` → `MusicState`, and a documented `port_name_hint` that resolves cleanly on real hardware. The duplicate `src/vibemix/midi/controllers/*.json` ↔ `src/vibemix/midi/profiles/*.json` catalogs are reconciled atomically to a **single source of truth** (one canonical directory, one schema, one loader) — eliminating the "which one does the registry actually use?" ambiguity flagged in v4.0 Phase 53. Hot-plug (connect → disconnect → reconnect with state preservation) is end-to-end verified in CI across ≥3 distinct profiles; live FLX4 plug/unplug on real hardware routes to KAAN-ACTION. The audio backend matrix (macOS BlackHole 2ch + 16ch · Windows WASAPI loopback + edge "no-loopback-driver" fallback) is covered by integration tests against mocked CoreAudio + WASAPI. And a "Add Your Controller" contributor recipe lands at `docs/contributing/add-a-controller.md` — bundled template, the exact 4-step contract-test pattern, a `scripts/discover_midi_port.py` helper, a PR checklist — verified end-to-end by Kaan (or a trusted DJ) adding one new profile in < 30 min as a smoke. This phase is the bridge between "engineering-green" and "third-party-installable": a stranger should be able to plug in their controller and either have it work out-of-the-box or follow a clean recipe to add it.
**Depends on**: Phase 67 (the contract tests + hot-plug integration tests + audio backend matrix all land in the CI workflow P67 ships; broken green = broken DEV)
**Requirements**: DEV-01, DEV-02, DEV-03, DEV-04, DEV-05
**Success Criteria** (what must be TRUE):
  1. Running `pytest tests/midi/test_profile_contracts.py -v` lists 10 GREEN `test_<id>_loads_and_validates` cases (one per bundled profile: FLX4 · FLX6 · FLX10 · 400 · 1000 · SX3 · XDJ-RX3 · Party-Mix-Live · Inpulse-300 · Inpulse-500), each profile additionally has a synthetic-MIDI smoke test that exercises every emitted CC + NOTE through the full decode chain, and each profile JSON declares a non-empty `port_name_hint`. Verified by inspecting test output + `jq '.port_name_hint' src/vibemix/midi/<canonical-dir>/*.json`.
  2. The previously-duplicated `src/vibemix/midi/controllers/*.json` ↔ `src/vibemix/midi/profiles/*.json` catalogs collapse to a **single canonical directory** (the loser's directory either deleted or reduced to a shim that re-exports the canonical one, with a one-paragraph migration note in `docs/contributing/midi-catalog.md` explaining which won and why) — running `find src/vibemix/midi -name "*.json" | xargs -I{} basename {} .json | sort | uniq -c | awk '$1 > 1'` returns zero duplicates. Verified by a single atomic commit with the migration note.
  3. Running `pytest tests/integration/test_hotplug_matrix.py -m integration -v` shows end-to-end hot-plug (connect → disconnect → reconnect with state preservation) GREEN across ≥3 distinct profiles, with the `start_port_watcher` + `mark_disconnected` + single-state callback path closed in v4.0 Phase 53 surviving the test untouched. Live FLX4 plug/unplug Kaan-ear pass routes to `KAAN-ACTION-LEGAL.md §V7-LIVE`.
  4. Running `pytest tests/integration/test_audio_backends.py -m integration -v` shows GREEN coverage of macOS BlackHole 2ch + 16ch + Windows WASAPI loopback + edge "no-loopback-driver" fallback against mocked CoreAudio + WASAPI in CI. Live capture on real BlackHole + real WASAPI routes to `KAAN-ACTION-LEGAL.md §V7-LIVE` (one entry per OS).
  5. `docs/contributing/add-a-controller.md` exists with: a bundled template profile JSON, the exact 4-step contract-test pattern, the `scripts/discover_midi_port.py` helper invocation, and a "submit a PR with these N files" checklist. Verified end-to-end by Kaan (or a trusted DJ) adding **one new profile** in < 30 min as a smoke — a `docs/contributing/add-a-controller-smoke.md` artifact records the new profile name + the wall-clock minutes. (Defensible default under autonomous mode: if no trusted DJ is available before plan-execute, Kaan does the smoke himself on a controller-of-opportunity; if neither is available, the smoke routes to `§V7-LIVE` and the rest of P68 ships.)
**Plans**: 5 plans
- [x] 68P01-PLAN.md — Wave 0: atomic catalog reconciliation (delete `src/vibemix/midi/controllers/` + `map_loader.py` + `schema.json` + 2 orphan tests; rewrite README controller grid + a11y script + test_readme_shape + KAAN-ACTION §LAUNCH-04 + docs/midi-mapping.md + .planning/PROJECT.md; rotate 10 SVG placeholders; add `docs/contributing/midi-catalog.md` migration note) (DEV-02) — SHIPPED 2026-05-23 @ `52405a4` (one atomic commit; 36 files; default baseline 4158 → 4119 / 26 / 4 / 0; +Rule-3 deletion of vacuous `test_flx4_sync_disambig.py`)
- [x] 68P02-PLAN.md — Wave 1: 10-row parametrized contract test (`tests/midi/test_profile_contracts.py`) + 10-row synthetic-MIDI smoke (`tests/midi/test_profile_smokes.py`) — uses `load_profile()` not jsonschema (DEV-01) — SHIPPED 2026-05-23 (commits 9427fee + 613f23e; 224 insertions; 20 new tests GREEN; default baseline 4119 → 4139 / 26 / 4 / 0; no regressions; zero net-new deps; DEV-01 (a)+(b)+(c) closed)
- [x] 68P03-PLAN.md — Wave 2: 3-profile hot-plug matrix (`tests/integration/test_hotplug_matrix.py` — FLX4 + DDJ-400 + Inpulse-500) + 4-fixture audio backend matrix (`tests/integration/test_audio_backends.py` — BlackHole 2ch + 16ch + WASAPI loopback + no-loopback fallback) (DEV-03, DEV-04) — SHIPPED 2026-05-23 (commits 5f243d1 + f12edbb; 385 insertions; 8 new GREEN integration rows [3 parametrized hot-plug + 5 audio backend]; default baseline 4139 → 4147 / 26 / 4 / 0; no regressions; zero net-new deps; sacred-source paths `_midi_common.py` + `midi/state.py` + `blackhole_probe.py` + `_audio_windows.py` all READ-ONLY; Inpulse-500 sample CC rebased from plan's (0,15,90) to (1,4,90)→eq_low_a because the FLX4-shape binding doesn't exist on Inpulse-500; DEV-03 + DEV-04 closed engineering-side; live FLX4 hot-plug + real BlackHole + real WASAPI ride §V7-LIVE-08/09/10 / Wave 4)
- [x] 68P04-PLAN.md — Wave 3: contributor recipe — `scripts/discover_midi_port.py` (≤30 lines) + `docs/contributing/_template.json` + `docs/contributing/add-a-controller.md` (≤200 lines, 4-step + PR checklist) (DEV-05) — SHIPPED 2026-05-23 (commits aea6f26 + d504c71 + da78fec; 237 insertions; 3 new contributor-facing artifacts — 39-line cross-platform port lister with 0/1/2 exit-code contract + 25-line `_parse_profile`-valid template under `docs/contributing/` to dodge Pitfall #5 + 173-line recipe doc with 4 numbered steps + 5-item PR checklist + 4 sibling refs; default baseline 4147 → 4147 / 26 / 4 / 0 [+0 tests — artifacts are docs/script/json, not pytest-collected]; no regressions; zero net-new deps; zero `src/vibemix/` edits; Rule-1 auto-fix on plan reference's button kind `"note_on"` → canonical `"play"` so template validates as-is; DEV-05 engineering-side closed; live <30-min contributor smoke rides §V7-LIVE-07 / Wave 4)
- [x] 68P05-PLAN.md — Wave 4: append §V7-LIVE-07..10 KAAN-ACTION clusters (controller-recipe smoke · macOS BlackHole live · Windows WASAPI live · live FLX4 hot-plug ear) (DEV-03, DEV-04, DEV-05) — SHIPPED 2026-05-23 (commit `8ba2992`; single atomic file edit to KAAN-ACTION-LEGAL.md, +252 / -8; 4 new clusters in canonical order after §V7-LIVE-06 — §V7-LIVE-07 @ line 3889 [DEV-05 controller-recipe <30-min smoke, Owner-clock Kaan or trusted DJ, sign-off captures controller + profile_id + wall-clock minutes + friction points] · §V7-LIVE-08 @ line 3938 [DEV-04 macOS BlackHole 2ch/16ch live capture, Owner-clock Kaan's Mac, cross-refs §V7-LIVE-01 BlackHole-kext lineage] · §V7-LIVE-09 @ line 3995 [DEV-04 Windows WASAPI loopback live capture, Owner-clock Kaan's Win 11 VM Parallels/UTM, cross-refs §V7-LIVE-02 windows-latest=Server2022 lineage] · §V7-LIVE-10 @ line 4052 [DEV-03 live FLX4 plug/unplug ear pass, Owner-clock Kaan's Mac + DDJ-FLX4 USB, cross-refs §V7-LIVE-03 + v4.0 P53 single-state callback invariant + 3× plug-unplug-replug cycle protocol]; each cluster mirrors §V7-LIVE-01..06 baseline 6-section shape (Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off block); discharge tracking TOTAL updated from `11 tests + 1 workflow + 1 recurring` to `11 tests + 1 workflow + 1 recurring + 4 P68 live clusters`; total §V7-LIVE clusters 6 → 10; cross-refs landed `add-a-controller.md` ×3 + `test_audio_backends.py` ×2 + `test_hotplug_matrix.py` ×1 + `discover_midi_port.py` ×3; default baseline 4147 → 4147 / 26 / 4 / 0 [KAAN-ACTION-LEGAL.md not pytest-collected]; no regressions; zero `src/vibemix/` edits; zero net-new deps; under `gsd-autonomous fully` these are SOFT discharges — Phase 68 ENGINEERING-COMPLETE; live confirmations ride Kaan's clock without blocking P69)

### Phase 69: OSS Fully Integrated
**Goal**: The OSS surface goes from "we have a license" to "a stranger can clone, install, contribute, and trust the proxy with their session." Four parallel sub-tracks converge in this phase: (a) the four required OSS docs (`CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `MAINTAINERS.md`) ship at repo root in the Apache-2.0-aligned voice, link cleanly from the README, and are pinned by a repo-presence test; (b) the Bravoh-side Gemini proxy at `api.altidus.world` is production-hardened — per-install-UUID rate limit, token-bucket abuse handling, Prom metrics + Sentry observability, and **graceful client-side fallback when the proxy is offline → a clean "co-host unavailable this session" pill/mascot message** (NOT a crash, NOT a hallucinated coach line — the brain refusing to lie when its grounding is missing is on-thesis); (c) `docs/byo-key.md` documents the first-class "Bring Your Own Gemini API key" self-host path via `VIBEMIX_BRAVOH_PROXY=0` + `GEMINI_API_KEY=<user-key>`; (d) **`cut_release.sh v0.1.0-rc1` actually runs (not `--dry-run`)** — the publish hard-guard fires for real after Apple Dev + SignPath are landed (KAAN-ACTION §SHIP-V4 discharge), `gh release create v0.1.0-rc1` ships signed Mac `.dmg` + signed Windows `.exe` + SBOM (CycloneDX + SPDX) + Apache-2.0 NOTICE. **v4.0 "SHIP" closes alongside this requirement.** Plus Homebrew tap (`packaging/homebrew/Formula/vibemix.rb`) + Scoop bucket (`packaging/scoop/vibemix.json`) scaffolds check in and validate via CI (`brew audit` + `scoop checkver` against the v0.1.0-rc1 artifacts), but the actual tap/bucket publish stays manual for v7.0 — that's a user-visible install upgrade that earns its own follow-on milestone (`docs/release-process.md` documents the split).

**Autonomous-mode signature-clock contingency:** OSS-04 has a hard external dependency (Apple Dev Agreement signed by Francesco + SignPath OSS Foundation cert) that has been on the clock since v3.0. Under `gsd-autonomous fully`, if the signatures have not landed by phase execution: OSS-04 routes to `KAAN-ACTION-LEGAL.md §SHIP-V4` with the **exact `cut_release.sh v0.1.0-rc1` invocation pre-staged** (no engineering step left to discover), the publish hard-guard stays absolute and regression-pinned, and **the rest of OSS-01/02/03/05 ships unblocked** — none of the docs / proxy hardening / BYO docs / packaging scaffolds depend on signatures. v4.0 stays open until OSS-04 actually fires; v7.0 closes when OSS-04 either fires for real or has its discharge artifact accepted in §SHIP-V4. This is the defensible answer under autonomy mode — *engineering ship-ready in the same milestone, publish closes when the clock catches up*.

**Depends on**: Phase 68 (don't ship a release with a broken or duplicated controller catalog — DEV's reconciliation must land before the artifacts go public; the Homebrew + Scoop scaffolds reference the canonical controller list)
**Requirements**: OSS-01, OSS-02, OSS-03, OSS-04, OSS-05
**Success Criteria** (what must be TRUE):
  1. The four required OSS files exist at repo root and are pinned by a test: `tests/repo/test_oss_presence.py::test_required_oss_files_exist` passes, confirming `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `MAINTAINERS.md` are present, non-empty, and linked from the README; `CONTRIBUTING.md` explicitly carves out the Bravoh privacy/IP boundary ("the Bravoh proxy is closed-source by design — vibemix is Apache-2.0; the proxy is the commercial wedge"). Verified by inspecting the four file paths + the test run + a `grep` for the carveout language.
  2. Running `pytest tests/integration/test_proxy_fallback.py -m integration -v` shows GREEN coverage of "proxy offline → graceful client-side fallback" — the test mocks `api.altidus.world` as 503, runs a coach turn, and asserts the pill/mascot surfaces a "co-host unavailable this session" message (NOT a crash, NOT a hallucinated coach line). Production-side, the proxy at `api.altidus.world` exposes `/metrics` (Prom format) with `rate_limit_hits_total{install_uuid="..."}` + `tokens_remaining_bucket{install_uuid="..."}` + has Sentry DSN wired. Verified by `curl https://api.altidus.world/metrics` returning a Prom-formatted body + a synthetic abuse run against a test install-UUID triggering a 429.
  3. `docs/byo-key.md` exists and documents the BYO path end-to-end: a fresh-account install with `VIBEMIX_BRAVOH_PROXY=0` + `GEMINI_API_KEY=<user-key>` reaches a live coach session with the user's own Gemini quota — verified by Kaan walking the doc on a fresh user account and recording the walk in `docs/byo-key-walk.md` (or routing to `KAAN-ACTION-LEGAL.md §V7-LIVE` if the fresh-account walk is gated on a future Kaan-action slot under autonomy mode).
  4. **`cut_release.sh v0.1.0-rc1` runs without `--dry-run`** — Apple Dev Agreement (Francesco) + SignPath OSS Foundation cert (Kaan) are landed (KAAN-ACTION §SHIP-V4 discharge confirmed), the publish hard-guard fires for real, `gh release view v0.1.0-rc1` returns a public release with signed Mac `.dmg` + signed Windows `.exe` + CycloneDX SBOM + SPDX SBOM + Apache-2.0 NOTICE as assets, and `verify_signed.py --require-signed <each-asset>` exits 0. v4.0 "SHIP" closes alongside in `MILESTONES.md`. **If signatures haven't landed by phase execution under `gsd-autonomous fully`**: OSS-04 routes to `KAAN-ACTION-LEGAL.md §SHIP-V4` with the exact pre-staged invocation, and the other 4 OSS reqs ship to satisfy the rest of the pillar.
  5. `packaging/homebrew/Formula/vibemix.rb` + `packaging/scoop/vibemix.json` check into the repo; CI runs `brew audit --new packaging/homebrew/Formula/vibemix.rb` + `scoop checkver -d packaging/scoop/vibemix.json` against the v0.1.0-rc1 artifacts (or against a deterministic fixture if OSS-04 hasn't fired yet) — both exit 0. `docs/release-process.md` explicitly documents that pushing to `bravoh-ai/homebrew-tap` + `bravoh-ai/scoop-bucket` is a future-milestone publish (split rationale: "the actual tap/bucket push is the user-visible install upgrade and earns its own milestone"). Verified by inspecting the two scaffold files + the doc section + the CI workflow.
**Plans**: 5 plans
- [x] 69-01-PLAN.md — Wave 0: MAINTAINERS.md + CONTRIBUTING.md carveout audit + README Community section + tests/repo/test_oss_presence.py (OSS-01)
- [x] 69-02-PLAN.md — Wave 1: docs/byo-key.md + tests/repo/test_byo_doc_shape.py + KAAN-ACTION §V7-LIVE-11 BYO fresh-account walk cluster (OSS-03)
- [x] 69-03-PLAN.md — Wave 2: src/vibemix/agent/proxy_client.py ProxyUnavailable + classify + probe_health + dj_cohost.py + session_loop.py orchestration + tests/integration/test_proxy_fallback.py + KAAN-ACTION §V7-PROXY cluster (OSS-02)
- [ ] 69-04-PLAN.md — Wave 3: packaging/homebrew/Formula/vibemix.rb + packaging/scoop/vibemix.json + scripts/launch/sync_packaging.sh + .github/workflows/packaging-audit.yml + docs/release-process.md split-rationale + tests/repo/test_packaging_scaffolds_present.py (OSS-05)
- [ ] 69-05-PLAN.md — Wave 4: cut_release.sh --dry-run v0.1.0-rc1 re-verify + KAAN-ACTION §SHIP-V4 v7.0 OSS-04 sub-section + docs/release-process.md autonomous-mode-route section + tests/repo/test_ship_v4_section_exists.py (OSS-04)

### Phase 70: GitHub Sexified, Generated, Tested
**Goal**: The GitHub front-porch is finished — every visual asset auto-generated from source (no hand-cut bitrot, no "lost the original Figma file"), the README's placeholder demo replaced with the real 30-sec CDJ-Whisper hero film, a GitHub Pages landing at `bravoh-ai.github.io/vibemix` that hooks visitors with a "what is this in 30 seconds" pitch + install CTA + opt-in Bravoh waitlist link, an OG/social card pinned at a known SHA, and a one-stop `tests/repo/test_github_presence.py` suite that catches asset bitrot, broken badges, missing OSS files, or hash drift in CI. This is the final pillar — the v0.1.0-rc1 release is shipped (P69), and now the front-porch points at it: a stranger landing on the README or the Pages site should grok the product in 30 seconds, see a real demo (not a placeholder), and have a clean path to "install" or "join the Bravoh waitlist." The CDJ-Whisper aesthetic (5 warm blacks + single amber accent + Saira + JetBrains Mono — no Geist/Fraunces backsliding) is held by the `frontend-enforcement` skill across both the landing page and any new visual asset.

**Kaan-felt sign-off checkpoint:** the landing-page aesthetic is the bar — taste is the gate, not Lighthouse scores. P70 ships engineering-green when all five success criteria below are observable, but the final Pages deploy carries a Kaan-felt sign-off in `KAAN-ACTION-LEGAL.md §V7-LANDING` (mirroring the §RECALL-EAR / §SHIP-V4 pattern). Under `gsd-autonomous fully`, the engineering-side closes when the auto-checks pass; the felt sign-off rides forward and does not gate the milestone close.

**Depends on**: Phase 69 (the README + landing page reference the actual released artifacts — broken links to a non-existent `v0.1.0-rc1` release would be worse than no release; if OSS-04 has routed to §SHIP-V4, the landing page still ships but with a "coming soon" install CTA pointing at the same KAAN-ACTION surface, and the test_github_presence suite tolerates the placeholder per a documented exception)
**Requirements**: GH-01, GH-02, GH-03, GH-04, GH-05
**Success Criteria** (what must be TRUE):
  1. The real `docs/assets/demo.mp4` (30-second hero film matching the CDJ-Whisper aesthetic) exists at the path the README `<video src>` already points at; `scripts/check_readme_hero_hash.py` reads a non-`PLACEHOLDER` SHA-256 from the README and matches it against the actual asset's SHA-256, exits 0; the asset is ≤ 8 MB (`stat -f%z docs/assets/demo.mp4` returns ≤ 8388608); it plays inline on Chrome + Safari + Firefox (verified by Kaan opening the README on each in `KAAN-ACTION-LEGAL.md §ASSETS-DEMO-CUT` walk); the `<img>` poster fallback at `docs/assets/demo-poster.png` is also committed. **§ASSETS-DEMO-CUT KAAN-ACTION discharged.**
  2. The GitHub Pages landing at `bravoh-ai.github.io/vibemix` (or the repo's Pages equivalent if Pages is hosted on a per-repo subdomain) is live in the CDJ-Whisper aesthetic — verified by (a) opening the URL and confirming visually (Kaan-felt sign-off in §V7-LANDING) the 5-warm-blacks palette + single amber accent + Saira + JetBrains Mono hold, (b) `lighthouse <pages-url> --only-categories=accessibility,performance --quiet` returns scores ≥ 95 (a11y) and ≥ 90 (perf), (c) the `/` route renders a "what is this in 30 seconds" hero + install CTA + opt-in Bravoh-waitlist hook (UTM-tracked per the locked v3.0 funnel rule, default-OFF), and (d) `grep -ri 'geist\|fraunces' docs/landing/` returns zero matches (anti-backsliding gate).
  3. The OG / social card at `docs/assets/og-card.png` (1200×630) is generated from `docs/assets/sources/og-card.html` (a Tailwind + Puppeteer template) via `scripts/regenerate_assets.sh`; the card is pinned at a known SHA-256 in `docs/assets/MANIFEST.yaml`; the GitHub Pages landing + the README both reference it via `<meta property="og:image">`; `tests/repo/test_github_presence.py::test_og_card_present_and_hash_matches` passes. Verified by inspecting the test run + opening the README in a Twitter/X card validator (or running `curl -I https://opengraph.xyz/url/<pages-url>` and confirming the card resolves).
  4. All visual assets in `docs/assets/` are **auto-generated from sources** in `docs/assets/sources/` — running `scripts/regenerate_assets.sh` produces byte-identical outputs to what's committed (or differs ONLY by intentional source edits). Verified by a CI gate at `.github/workflows/asset-bitrot.yml` that runs the regenerator, runs `git diff --exit-code docs/assets/`, and fails if a committed asset doesn't match its regenerated form. The list of source-generated assets is enumerated in `docs/assets/MANIFEST.yaml` (so hand-cut assets that are intentionally bespoke can be opt-out and don't break the gate).
  5. `tests/repo/test_github_presence.py` exists as a one-stop repo-presence suite — running `pytest tests/repo/test_github_presence.py -v` shows GREEN coverage of: every README badge URL returns 200 (via `requests.get` with a 5s timeout), the demo asset is present + under the size cap, the OG image is present + hash matches the manifest, the README hero hash matches the sentinel, every `.github/ISSUE_TEMPLATE/*.md` is non-empty + has the required front-matter (`---\nname: ...\nabout: ...\n---`), `.github/pull_request_template.md` exists + is non-empty, and the four OSS files from P69 (CONTRIBUTING / CoC / SECURITY / MAINTAINERS) all exist + link cleanly. **This test is the "GitHub sexified, generated, tested" success criterion encoded in code.**
**Plans**: TBD
**UI hint**: yes — the GitHub Pages landing is a Tier-1 surface for first-time visitors; the `frontend-enforcement` skill governs the CDJ-Whisper material/typography pass and the Kaan-felt sign-off is the hard taste gate (mirrors v4.0 P57 + v5.0 P62 pattern)

## Progress (v7.0)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 67. All Tests Pass | v7.0 | 5/5 | Complete   | 2026-05-23 |
| 68. All Devices Ready | v7.0 | 5/5 | Complete (Waves 0-4 / 68P01..68P05 all shipped 2026-05-23 — atomic catalog reconciliation + 10×2 parametrized contract/smoke + 3-profile hot-plug matrix + 4-fixture audio backend matrix + contributor recipe + §V7-LIVE-07..10 KAAN-ACTION clusters; DEV-01..05 all closed engineering-side; live-hardware confirmations ride Kaan's clock via §V7-LIVE-07..10) | 2026-05-23 |
| 69. OSS Fully Integrated | v7.0 | 3/5 | In Progress|  |
| 70. GitHub Sexified, Generated, Tested | v7.0 | 0/0 | Not started | - |

**Coverage:** 19/19 v7.0 requirements mapped ✓ (no orphans, no duplicates) — TEST-01..04 → P67 · DEV-01..05 → P68 · OSS-01..05 → P69 · GH-01..05 → P70

---

# v6.0 "The Memory Turn" — SHIPPED 2026-05-23 (tech_debt accepted)

<details>
<summary>✅ v6.0 The Memory Turn (Phases 63–66) — SHIPPED 2026-05-23 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 12 plans, 14/14 v6.0 REQ-IDs satisfied, 6/6 cross-phase integration seams WIRED, 53/53 must-haves verified, 247/247 v6.0 surface tests GREEN. A **WIRING / REUSE milestone with ZERO net-new dependencies** — built entirely on the shipped `src/vibemix/library/` primitives (sqlite-vec, cosine_topk, embed-cache, grounding pattern, EVIDENCE_SOURCES schema).

- [x] Phase 63: Memory Store (3/3 plans) — 2026-05-22 (STORE-01..04 GREEN; 19/19 tests/memory/)
- [x] Phase 64: Session Ingest (3/3 plans) — 2026-05-22 (INGEST-01..03 GREEN; one v1 moment kind = `coach_line`; `moment` cut, `audio_moment` deferred)
- [x] Phase 65: Memory Retrieval Seam — ANTI-SLOP RELEASE GATE (4/4 plans) — 2026-05-22 (RECALL-01..04 GREEN; existence-only `recall` source à la P59 `key:`, fabricated `[recall:<id>]` strips whole turn)
- [x] Phase 66: Visible Copilot Move (2/2 plans) — 2026-05-22 (COPILOT-01..03 GREEN; transition-shape + vocabulary callbacks; ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass)

**KAAN-ACTION (live-confirm, rides forward):** §RECALL-EAR felt-quality discharge (4 ear items) + §LIVE-EMBED real-session FLEX-tier round-trip + two doc-drifts (code correct) + STORE-03 recordings-UI call-site (out of v6.0 scope; future recordings-UI phase). All in `KAAN-ACTION-LEGAL.md §RECALL-EAR` + `66-HUMAN-UAT.md`.

**Git tag deferred** (consistent with v4.0 + v5.0): the `v6.0` tag + branch merge are Kaan's call on his clock.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`

</details>

---

# v5.0 "The Useful Cut" — SHIPPED 2026-05-22 (tech_debt accepted)

<details>
<summary>✅ v5.0 The Useful Cut (Phases 59–62) — SHIPPED 2026-05-22 (tech_debt accepted)</summary>

Deck-aware, actionable, unobtrusive. Full session-wide deck-state (pyrekordbox XML → Gemini-vision → numpy ladder) with a citable `key:` evidence source; a deterministic Camelot harmonic key-clash gate the LLM only narrates (ships **default-OFF** behind the Kaan-ear veto); an actionable-not-hype coach persona extending the `live-tuning-or-brain` branch (hype goldens regression-fenced); and a transparent, draggable, non-focus-stealing **floating pill** as the primary live surface (Three.js mascot kept opt-in/secondary, mascot-audit green). 4/4 phases, 17/17 requirements satisfied, 4/4 cross-phase integration seams WIRED.

- [x] Phase 59: Full Deck Awareness + Grounding (5/5 plans) — 2026-05-21
- [x] Phase 60: Harmonic-Feedback Confidence Gate (4/4 plans) — 2026-05-21 (detector default-OFF until the Kaan-ear veto flip)
- [x] Phase 61: Actionable-Not-Hype Coach Persona (2/2 plans) — 2026-05-21
- [x] Phase 62: Floating Pill UI (5/5 plans) — 2026-05-22

Full archive: `.planning/milestones/v5.0-ROADMAP.md` · Requirements: `.planning/milestones/v5.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v5.0-MILESTONE-AUDIT.md`

</details>

---

# v4.0 SHIP — OPEN (engineering-complete 8/8, publish on signature clock — NOT archived)

> **Status:** All 8 phases (51–58) are engineering-complete. The milestone is deliberately **left open and unarchived** — its public RC publish stays gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). **v7.0's OSS-04 actually consumes this publish** (closes alongside §SHIP-V4 discharge). Do not delete or archive this section until OSS-04 fires.

<details>
<summary>🟡 v4.0 SHIP (Phases 51–58) — engineering-complete 2026-05-21, publish on signature clock</summary>

- [x] Phase 51: Real-Hardware Bring-Up (3/3 plans) — 2026-05-21
- [x] Phase 52: Audio Path + Feature Grounding (4/4 plans) — 2026-05-21
- [x] Phase 53: Controller Live + Graceful Fallback (2/2 plans) — 2026-05-21
- [x] Phase 54: Hype Mode Live (4/4 plans) — 2026-05-20
- [x] Phase 55: Feedback Mode Live + Citation Integrity (3/3 plans) — 2026-05-21
- [x] Phase 56: Performance + Live Mascot (3/3 plans) — 2026-05-21
- [x] Phase 57: Sexify Finish (3/3 plans) — 2026-05-21
- [x] Phase 58: Ship Readiness (4/4 plans) — 2026-05-21 (`cut_release.sh --dry-run v0.1.0-rc1` GREEN; publish hard-guard regression-pinned)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA). `KAAN-ACTION-LEGAL.md §SHIP-V4` documents the one-button SHIP-CUT sequence. **v4.0 closes alongside v7.0 OSS-04.**

Full archive: `.planning/milestones/v4.0-ROADMAP.md`

</details>

---

## Phase History (Archived)

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v2.1 The Unified Cut (Phases 27–39) — SHIPPED 2026-05-16 (tech_debt accepted)</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC. 105/105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC. 57/57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.1 Distribution-Ready Pass (Phases 46–50) — SHIPPED 2026-05-18 (tech_debt accepted)</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC. 44/44 v3.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v3.1-ROADMAP.md` · Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

</details>

---

## Milestone-Level Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| v3.0 Clean OSS Ship | 40–45 | ✅ Shipped (tech_debt) | 2026-05-17 |
| v3.1 Distribution-Ready Pass | 46–50 | ✅ Shipped (tech_debt) | 2026-05-18 |
| v4.0 SHIP | 51–58 | 🟡 Engineering-complete (8/8) — publish on signature clock; closes alongside v7.0 OSS-04 | - |
| v5.0 The Useful Cut | 59–62 | ✅ Shipped (tech_debt) | 2026-05-22 |
| v6.0 The Memory Turn | 63–66 | ✅ Shipped (tech_debt) | 2026-05-23 |
| v7.0 Open House | 67–70 | 🔵 Active (planning) | - |

---

*Roadmap extended 2026-05-23 for v7.0 "Open House" — **4 phases (67–70)** continuing numbering from v6.0 (which ran 63–66). v4.0 "SHIP" stays OPEN and unarchived above — its publish closes alongside v7.0's OSS-04 (KAAN-ACTION §SHIP-V4 discharge fires `cut_release.sh v0.1.0-rc1` for real). v7.0 derives from 19 requirements across 4 pillars (TEST · DEV · OSS · GH), one phase per pillar, sized by `.planning/REQUIREMENTS.md` Traceability — 4/5/5/5 REQ-IDs per phase, zero orphans, zero duplicates. **Hard scope rule (locked):** v7.0 is WIRING + DISCHARGE + POLISH — zero new product capability, zero new AI providers, zero new managed-memory frameworks, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation grounding / "trust the audio" / one socket) hold by zero-touch — no phase modifies the reaction path. The v4.0 external signature clock is unchanged. Critical path: P67 (test infrastructure, dependency-free) → P68 (controller catalog reconciliation + audio backends, lands on P67's CI matrix) → P69 (OSS surface + actual publish gated on §SHIP-V4) → P70 (GitHub front-porch + Kaan-felt landing-page sign-off). Under `gsd-autonomous fully`, OSS-04 routes to §SHIP-V4 if signatures haven't landed at execution; the other 18 REQ-IDs ship unblocked.*
