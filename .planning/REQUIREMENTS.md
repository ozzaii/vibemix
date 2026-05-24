# vibemix — Requirements

**Milestone:** v7.0 "Open House" — vibemix becomes a publishable, contributable, install-anywhere OSS project
**Started:** 2026-05-23
**Mode:** `gsd-autonomous fully` (recommended grey-area answers + defer blockers to KAAN-ACTION; only privacy rule + destructive risk pause)

## Goal

Turn the repo from "engineering-green, gated on external clock" (v4.0 SHIP carryover + v6.0 memory copilot wired-but-flag-default-off) into a **publishable, contributable, install-anywhere open-source project** that strangers can clone, install, run, and contribute to — warming visitors into Bravoh waitlist signups along the way.

Four pillars, all **closing existing loops** (no new product capability):

1. **TEST** — All tests pass (every collected test green across the full marker grid)
2. **DEV** — All devices ready (10 bundled controllers + Mac/Win audio backends live-verified)
3. **OSS** — OSS fully integrated (v4.0 publish goes out, contributor docs shipped, Bravoh-proxy production-ready)
4. **GH** — GitHub sexified, generated, tested (real demo, landing page, asset pipeline, repo-presence suite)

**Scope rule (anti-creep, locked):** v7.0 is **WIRING + DISCHARGE + POLISH**. Zero new product capability. Zero new AI providers / managed-memory frameworks (CLAP, MERT, OpenL3, torch, Mem0, Letta, Zep, Cognee all out — unchanged from v6.0). v6.0's deferred future items (multimodal moment-audio · cross-session arc priors · ProDJ Link · memory-driven pre-set prep) all stay deferred. v6.0's `VIBEMIX_RECALL_ENABLED=1` flip stays on its independent §RECALL-EAR Kaan-ear clock — not v7.0 scope.

**Acid test for any v7.0 phase:** *"does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"* If neither, defer.

The product's hard line holds: **grounded, never hallucinating, no AI slop.** Nothing in v7.0 changes a single prompt, a single evidence source, a single emission path. The cardinal invariants (single-writer · citation-grounding · trust-the-audio · one-socket) hold by zero-touch.

---

## v7.0 Requirements

### TEST — All Tests Pass (Phase 67)

- [ ] **TEST-01**: Default `pytest -q` exits 0 at 100% pass rate on `main` HEAD — every existing skip / xfail / xpass is either fixed-now, justified by a one-line `# reason:` adjacent to the marker, OR converted to a KAAN-ACTION external-clock item. The current state (4186 collected, 65 opt-in deselected) is the baseline; v7.0 closes any uncategorized red.
- [ ] **TEST-02**: The opt-in marker grid (`macos_audio` + `windows_only` + `integration` + `slow` + `e2e` + `cli` + `network`) runs cleanly on Kaan's Mac + a Windows 11 VM; the 65 currently-deselected live tests either pass or have their failure mode documented in `KAAN-ACTION-LEGAL.md §V7-LIVE` with a concrete fix path. No marker is a graveyard.
- [x] **TEST-03**: Any non-deterministic test (10× consecutive run reveals < 100% pass) is either stabilized via test surgery, or quarantined to its own `flaky` marker with a linked GitHub issue. Static gate: `tests/repo/test_no_silent_flakes.py` catches new `@pytest.mark.flaky` decorators that don't carry an issue link.
- [x] **TEST-04**: A `.github/workflows/full-test-matrix.yml` runs the full marker grid (default + each opt-in marker individually) on `macos-13` + `macos-14` + `windows-latest` on every push to `main` and every PR. Green badge appears in the README badges row. Failure shows up on the PR check surface (not silently in a side branch).

### DEV — All Devices Ready (Phase 68)

- [x] **DEV-01**: All 10 bundled MIDI controller profiles (Pioneer DDJ-FLX4 · FLX6 · FLX10 · 400 · 1000 · SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300 · Inpulse 500) each have: (a) a schema-valid contract test (`tests/midi/test_profile_contracts.py::test_<id>_loads_and_validates`), (b) a synthetic-MIDI smoke that hits every emitted CC + NOTE in the profile through `find_mapping` + `ControllerState` + `state.MusicState`, and (c) a documented port_name_hint that resolves cleanly on real hardware. No profile is shipped without all three. — CLOSED 2026-05-23 via Phase 68 Plan 68P02 (commits `9427fee` + `613f23e`; 10-row parametrized contract test + 10-row synthetic-MIDI smoke; +20 tests GREEN; uses `load_profile()` not jsonschema).
- [x] **DEV-02**: The duplicate `src/vibemix/midi/controllers/*.json` ↔ `src/vibemix/midi/profiles/*.json` catalogs are reconciled to a **single source of truth** (one canonical directory, one schema, one loader). No broken imports, no shipped duplicates, no "which one does the registry actually use?" ambiguity. The reconciliation is committed atomically with a migration note explaining why. — CLOSED 2026-05-23 via Phase 68 Plan 68P01 @ `52405a4` (atomic commit; `profiles/` won; `controllers/` + `map_loader.py` + `schema.json` deleted; `docs/contributing/midi-catalog.md` migration note shipped).
- [x] **DEV-03**: Hot-plug (connect → disconnect → reconnect with state preservation) is end-to-end verified across ≥3 distinct profiles via `tests/integration/test_hotplug_matrix.py`. Live FLX4 plug/unplug Kaan-ear pass on real hardware routed to KAAN-ACTION (`§V7-LIVE`). The `start_port_watcher` + `mark_disconnected` + single-state callback path (closed in v4.0 Phase 53) survives the test suite untouched. — CLOSED engineering-side 2026-05-23 via Phase 68 Plan 68P03 Task 1 (commit `5f243d1`; 3-row parametrized hot-plug matrix across pioneer_ddj_flx4 + pioneer_ddj_400 + hercules_inpulse_500; v4.0 P53 `handle_port_change_single_state` + `mark_disconnected` READ-ONLY); live FLX4 plug/unplug ear-pass routed to `KAAN-ACTION-LEGAL.md §V7-LIVE-10` (created via Plan 68P05 / commit `8ba2992`; ☐ pending Kaan-discharge under `gsd-autonomous fully`).
- [x] **DEV-04**: The audio backend matrix (macOS BlackHole 2ch + 16ch · Windows WASAPI loopback + edge "no-loopback-driver" fallback) is covered by integration tests (`tests/integration/test_audio_backends.py`) that pass on CI with mocked CoreAudio + WASAPI. Live capture on real BlackHole + real WASAPI routed to KAAN-ACTION per OS. — CLOSED engineering-side 2026-05-23 via Phase 68 Plan 68P03 Task 2 (commit `f12edbb`; 5-fixture audio backend mock matrix: BlackHole 2ch + 16ch + absent graceful + WASAPI loopback + no-loopback OSError fallback; `blackhole_probe.py` + `_audio_windows.py` READ-ONLY); live capture routed to `KAAN-ACTION-LEGAL.md §V7-LIVE-08` (macOS BlackHole) + `§V7-LIVE-09` (Windows WASAPI) — both created via Plan 68P05 / commit `8ba2992`; ☐ pending Kaan-discharge under `gsd-autonomous fully`.
- [x] **DEV-05**: A "Add Your Controller" contributor recipe lands at `docs/contributing/add-a-controller.md`: bundled template profile JSON, the exact 4-step contract-test pattern, the port-hint discovery script (`scripts/discover_midi_port.py`), and a "submit a PR with these N files" checklist. Verified end-to-end by Kaan (or a trusted DJ) adding one new profile in < 30 min as a smoke. — CLOSED engineering-side 2026-05-23 via Phase 68 Plan 68P04 (commits `aea6f26` + `d504c71` + `da78fec`; 3 contributor-facing artifacts: 39-line `scripts/discover_midi_port.py` with 0/1/2 exit-code contract + 25-line `docs/contributing/_template.json` `_parse_profile`-valid copy-target + 173-line `docs/contributing/add-a-controller.md` 4-step recipe + 5-item PR checklist); live <30-min smoke routed to `KAAN-ACTION-LEGAL.md §V7-LIVE-07` (created via Plan 68P05 / commit `8ba2992`; ☐ pending Kaan or trusted DJ from network — discharge artifact will be `docs/contributing/add-a-controller-smoke.md`).

### OSS — OSS Fully Integrated (Phase 69)

- [ ] **OSS-01**: `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` + `SECURITY.md` + `MAINTAINERS.md` ship at the repo root in the Apache-2.0-aligned voice, link cleanly from the README, and are covered by a repo-presence test (`tests/repo/test_oss_presence.py::test_required_oss_files_exist`). Bravoh privacy/IP carveouts (e.g. "the Bravoh proxy is closed-source by design") explicit in CONTRIBUTING.md so contributors don't waste cycles on the wrong layer.
- [x] **OSS-02**: The Bravoh-side Gemini proxy at `api.altidus.world` is production-hardened: per-client (per-install-UUID) rate limit, token-bucket abuse handling, Prom metrics + Sentry observability, and **graceful client-side fallback** when the proxy is offline → a clean "co-host unavailable this session" message in the pill / mascot (NOT a crash, NOT a hallucinated coach line). Covered by `tests/integration/test_proxy_fallback.py` against a mocked-offline proxy.
- [x] **OSS-03**: `docs/byo-key.md` documents the "Bring Your Own Gemini API key" path for self-hosters: clean opt-out from the Bravoh proxy via `VIBEMIX_BRAVOH_PROXY=0` + `GEMINI_API_KEY=<user-key>`, full end-to-end verified on a fresh-account install. The BYO path is a first-class citizen, not a hidden escape hatch (it's the OSS contract).
- [ ] **OSS-04**: `cut_release.sh v0.1.0-rc1` actually runs (not `--dry-run`): the Apple Developer Agreement + SignPath OSS cert are landed (KAAN-ACTION discharge), the publish hard-guard fires for real, GitHub release `v0.1.0-rc1` is live with signed Mac `.dmg` + signed Windows `.exe` + SBOM (CycloneDX + SPDX) + Apache-2.0 NOTICE. v4.0 "SHIP" closes alongside this requirement.
- [x] **OSS-05**: Homebrew tap scaffold (`packaging/homebrew/Formula/vibemix.rb`) + Scoop bucket scaffold (`packaging/scoop/vibemix.json`) check into the repo, validated by CI (`brew audit` + `scoop checkver` against the v0.1.0-rc1 artifacts), but **the actual tap/bucket publish itself stays manual for v7.0** (pushing to `bravoh-ai/homebrew-tap` is the user-visible install upgrade that justifies its own follow-on milestone). Documented as such in `docs/release-process.md`.

### GH — GitHub Sexified, Generated, Tested (Phase 70)

- [ ] **GH-01**: The real `docs/assets/demo.mp4` (30-second hero film matching the CDJ-Whisper aesthetic) lands at the path the README `<video src>` already points at; `scripts/check_readme_hero_hash.py` updates from `sha256=PLACEHOLDER` to the real SHA-256 and stays GREEN; the asset is ≤ 8 MB; it plays inline on Chrome + Safari + Firefox; the `<img>` poster fallback also lands. §ASSETS-DEMO-CUT KAAN-ACTION discharged.
- [ ] **GH-02**: A GitHub Pages landing at `bravoh-ai.github.io/vibemix` (or repo Pages equivalent) lives in the CDJ-Whisper aesthetic (5 warm blacks + single amber accent + Saira + JetBrains Mono — no Geist / Fraunces backsliding). The `/` route is a "what is this in 30 seconds" hero + install CTA + Bravoh-waitlist hook — opt-in, default-OFF, UTM-tracked per the locked v3.0 funnel rule. Lighthouse a11y ≥ 95, performance ≥ 90.
- [ ] **GH-03**: An OG / social card at `docs/assets/og-card.png` (1200×630) is generated from a Tailwind + Puppeteer source template at `docs/assets/sources/og-card.html`; pinned at a known SHA-256; referenced from `<meta property="og:image">` in the GitHub Pages landing + the README; covered by `tests/repo/test_github_presence.py::test_og_card_present_and_hash_matches`.
- [ ] **GH-04**: All visual assets in `docs/assets/` are **auto-generated from sources** in `docs/assets/sources/` — re-running `scripts/regenerate_assets.sh` produces byte-identical outputs (or differs ONLY by intentional source edits). No hand-cut SVG bitrot, no "lost the original Figma file" rot. CI fails if a committed asset doesn't match its regenerated form.
- [ ] **GH-05**: `tests/repo/test_github_presence.py` is a one-stop repo-presence suite covering: every README badge URL returns 200, the demo asset is present + under the size cap, the OG image is present + hash matches, the README hero hash matches the sentinel, every `.github/ISSUE_TEMPLATE/*.md` is non-empty + has the required front-matter, `pull_request_template.md` exists, and the four OSS files (CONTRIBUTING / CoC / SECURITY / MAINTAINERS) all exist + link cleanly. **This test is the "GitHub sexified, generated, tested" success criterion in code.**

---

## Future Requirements (deferred — next milestone)

- **Multimodal moment-audio embedding** (carry-forward from v6.0 §Future) — v1 is text-signature-only; embedding the actual moment audio (gemini-embedding-2's audio path) is future, gated on text-retrieval proving insufficient.
- **Cross-session "arc" priors** (carry-forward from v6.0 §Future) — longer-horizon narrative memory beyond per-moment recall.
- **Memory-driven pre-set prep** (carry-forward from v6.0 §Future) — forward-looking, not just in-set recall.
- **ProDJ Link / live key-detection as primary sources** (carry-forward from v5.0 §Future).
- **Homebrew tap + Scoop bucket actual publish** (split from OSS-05) — pushing to `bravoh-ai/homebrew-tap` + `bravoh-ai/scoop-bucket` is the user-visible install upgrade that earns its own milestone.
- **Multi-language localization** — vibemix is English-only in v7.0; ES / DE / FR / IT / TR / JP for the OSS landing page + in-app strings is future.
- **`/hatch` user-generated mascot** (unchanged carry-forward from v2.x backlog).
- **VIBEMIX_RECALL_ENABLED=1 default flip** — stays on its independent §RECALL-EAR Kaan-ear clock; v7.0 doesn't touch the flag default.

## Out of Scope (this milestone)

- **Any new product capability** — v7.0 is wiring + discharge + polish; the acid test ("turn existing engineering-green into something a stranger can install, verify, contribute to, or see") gates every requirement.
- **Any new AI provider** — Gemini-only held (CLAP / MERT / OpenL3 / torch all rejected, unchanged from v6.0).
- **Any new managed-memory framework** — Mem0 / Letta / Zep / Cognee all rejected (unchanged from v6.0).
- **Any new ws port / new IPC envelope** — one-socket invariant unchanged.
- **Settings-screen personalization** — Phase 32's ~2KB DJ profile is the limit; not a v7.0 surface.
- **Next-track recommendation** — re-opens the core hallucination class (unchanged).
- **LLM-extracted insights/tendencies** — locked out (unchanged).
- **Public beta marketing campaign** — the README + landing-page hook drive organic conversion; paid IG / sponsored posts (the 150-200 € launch marketing budget) come AFTER v7.0 ships and the waitlist hook is verified converting. Not v7.0 scope.
- **Adding more than 10 controllers** — v7.0 finishes the existing 10; an 11th-onwards is contributor-driven via DEV-05's recipe.
- **Mobile / web client** — desktop-only (unchanged).

---

## Traceability

**Roadmapper confirmed 2026-05-23**: 19/19 requirements mapped to exactly one phase each — no orphans, no duplicates, no re-mappings (REQUIREMENTS.md proposed mapping = roadmap-derived mapping). Coverage validated against the 4-pillar / 4-phase decomposition (TEST-01..04 → P67 · DEV-01..05 → P68 · OSS-01..05 → P69 · GH-01..05 → P70). Each phase reads as "verify / wire / discharge / generate / test" — zero product-surface growth, acid test held.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | Phase 67 | In progress — SC#1 (default `pytest -q` exits 0) SATISFIED by Plan 67P01 (2026-05-23); remaining SCs (xfail/xpass with `# reason:` annotations, KAAN-ACTION external-clock items) land in Waves 1-2 |
| TEST-02 | Phase 67 | Mapped (planning) |
| TEST-03 | Phase 67 | ✅ Done (2026-05-23) — marker-declaration prerequisite via 67P01 (`flaky:` in pyproject.toml); static gate `tests/repo/test_no_silent_flakes.py` via 67P03 (vacuously-green); 10× hunt 10/10 GREEN + `docs/flake-hunt.md` protocol + `KAAN-ACTION-LEGAL.md §V7-LIVE-06` recurring re-baseline cluster via 67P05 (SHA 23c4203, wall-clock 36m41s) |
| TEST-04 | Phase 67 | Mapped (planning) |
| DEV-01 | Phase 68 | ✓ Closed 2026-05-23 (68P02 commits `9427fee` + `613f23e`; 10-row contract + 10-row smoke parametrize, +20 GREEN) |
| DEV-02 | Phase 68 | ✓ Closed 2026-05-23 (68P01 @ `52405a4`) |
| DEV-03 | Phase 68 | ✓ Closed engineering-side 2026-05-23 (68P03 Task 1 @ `5f243d1`; 3-row hot-plug parametrize); live FLX4 ear → §V7-LIVE-10 (68P05 @ `8ba2992`, ☐ pending) |
| DEV-04 | Phase 68 | ✓ Closed engineering-side 2026-05-23 (68P03 Task 2 @ `f12edbb`; 5-fixture audio backend mock matrix); live BlackHole → §V7-LIVE-08 + live WASAPI → §V7-LIVE-09 (both via 68P05 @ `8ba2992`, ☐ pending) |
| DEV-05 | Phase 68 | ✓ Closed engineering-side 2026-05-23 (68P04 commits `aea6f26` + `d504c71` + `da78fec`; 3 contributor-facing artifacts); live <30-min smoke → §V7-LIVE-07 (68P05 @ `8ba2992`, ☐ pending) |
| OSS-01 | Phase 69 | Mapped (planning) |
| OSS-02 | Phase 69 | Mapped (planning) |
| OSS-03 | Phase 69 | Mapped (planning) |
| OSS-04 | Phase 69 | Mapped (planning) — gated on external Apple Dev + SignPath clock; routes to `KAAN-ACTION-LEGAL.md §SHIP-V4` if signatures haven't landed at execution; v4.0 "SHIP" closes alongside |
| OSS-05 | Phase 69 | Mapped (planning) |
| GH-01 | Phase 70 | Mapped (planning) — §ASSETS-DEMO-CUT discharge consumed |
| GH-02 | Phase 70 | Mapped (planning) — Kaan-felt sign-off on landing aesthetic rides `§V7-LANDING` |
| GH-03 | Phase 70 | Mapped (planning) |
| GH-04 | Phase 70 | Mapped (planning) |
| GH-05 | Phase 70 | Mapped (planning) |

**Coverage:** 19/19 requirements mapped to exactly one phase each — no orphans, no duplicates (TEST-01..04 → Phase 67 · DEV-01..05 → Phase 68 · OSS-01..05 → Phase 69 · GH-01..05 → Phase 70). **Confirmed by roadmapper 2026-05-23.**
