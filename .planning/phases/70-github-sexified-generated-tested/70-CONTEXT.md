# Phase 70: GitHub Sexified, Generated, Tested - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — `gsd-autonomous fully`)

<domain>
## Phase Boundary

Finish the GitHub front-porch — the LAST v7.0 pillar. A stranger landing on the README or the Pages site should grok vibemix in 30 seconds, see a real demo (not a placeholder), and have a clean path to "install" or "join the Bravoh waitlist." Every visual asset is auto-generated from source (no hand-cut bitrot), pinned by hash, and CI-gated. Five sub-tracks (GH-01..05), one per ROADMAP success criterion:

1. **GH-04 — Asset reproducibility infra (FOUNDATIONAL):** `scripts/regenerate_assets.sh` regenerates every source-derived asset; `docs/assets/MANIFEST.yaml` enumerates each generated asset + its source + pinned SHA-256 (hand-cut bespoke assets opt-out so they don't break the gate); `.github/workflows/asset-bitrot.yml` runs the regenerator + `git diff --exit-code docs/assets/` and fails on drift. This wave lands FIRST — GH-03's og-card registers into it.

2. **GH-03 — OG/social card auto-gen:** `docs/assets/og-card.png` (1200×630) generated from `docs/assets/sources/og-card.html` (Tailwind + Puppeteer template, CDJ-Whisper aesthetic) via `regenerate_assets.sh`; pinned by SHA-256 in `MANIFEST.yaml`; referenced via `<meta property="og:image">` in BOTH the README and the Pages landing. (The existing `docs/assets/social-card.png` (380k) is the hand-cut predecessor — og-card.png is its source-generated, hash-pinned successor; social-card.png either becomes a MANIFEST opt-out bespoke asset or is superseded — decided in planning.)

3. **GH-02 — GitHub Pages landing (BIGGEST, frontend):** `docs/landing/` static site in the CDJ-Whisper aesthetic (5 warm blacks + single amber accent + Saira + JetBrains Mono — NO Geist/Fraunces); `/` route = "what is this in 30 seconds" hero + install CTA + opt-in Bravoh-waitlist hook (UTM-tracked per locked v3.0 funnel rule, default-OFF); Lighthouse a11y ≥95 / perf ≥90; anti-backsliding gate `grep -ri 'geist\|fraunces' docs/landing/` returns zero. Governed by the `frontend-enforcement` skill. The live `bravoh-ai.github.io/vibemix` URL + Kaan-felt aesthetic sign-off ride `KAAN-ACTION-LEGAL.md §V7-LANDING` — engineering closes when the auto-checks pass (Lighthouse on a local/CI build + anti-backsliding grep + asset-reproducibility), the felt sign-off + Pages enablement is Kaan's clock.

4. **GH-01 — Real demo film:** `docs/assets/demo.mp4` (30-sec CDJ-Whisper hero film) at the path README's `<video src>` already points at + `docs/assets/demo-poster.png` poster fallback. Engineering side: ship the poster + keep `scripts/check_readme_hero_hash.py` green via the `sha256=PLACEHOLDER` sentinel until the real asset lands. The real film is gated on Francesco's capture day (v3.0 P43 VIS-09 runbook) → routes to `KAAN-ACTION-LEGAL.md §ASSETS-DEMO-CUT` (existing cluster). The ≤8 MB cap + cross-browser inline-play check ride that discharge.

5. **GH-05 — One-stop presence suite (LAST):** `tests/repo/test_github_presence.py` — GREEN coverage of: every README badge URL returns 200 (`requests.get`, 5s timeout, `@pytest.mark.network`); demo asset present + under size cap; OG image present + hash matches MANIFEST; README hero hash matches sentinel; every `.github/ISSUE_TEMPLATE/*` non-empty + has required GitHub-Forms front-matter; `.github/pull_request_template.md` exists + non-empty; the four P69 OSS files (CONTRIBUTING/CoC/SECURITY/MAINTAINERS) exist + link cleanly. This is "GitHub sexified, generated, tested" encoded in code. Pins everything Waves 0-3 produce.

**Out of scope** (acid test held — "does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"):
- Zero `src/vibemix/` edits (no reaction-path touch — cardinal invariants hold by zero-touch). Phase 70 is docs/assets/landing/CI/tests only.
- Zero new product capability, zero new deps in `pyproject.toml`/`uv.lock` (asset tooling — Puppeteer, lighthouse — is Node/CI-side, NOT a Python dep; if a Python helper needs a lib, prefer stdlib).
- The actual Pages enablement + live-URL Lighthouse run + Kaan-felt aesthetic sign-off (→ §V7-LANDING).
- The real demo.mp4 capture (→ §ASSETS-DEMO-CUT).

</domain>

<decisions>
## Implementation Decisions

### CRITICAL Doc-vs-Reality Reconciliations (apply before any task)
- **ISSUE_TEMPLATE is `.yml` GitHub Issue Forms, NOT `.md` with `---\nname:\nabout:\n---` front-matter.** The ROADMAP SC5 wording assumes the old `.md` format. Reality: `.github/ISSUE_TEMPLATE/{ai_misbehavior,bug_report,feature_request,new_controller,config}.yml` use GitHub Forms schema (`name:`, `description:`, `body:`). `test_github_presence.py` MUST validate the ACTUAL `.yml` Forms shape (each non-empty + has `name:` + `description:` + `body:` keys via yaml.safe_load), NOT grep for `about:` front-matter. Document this reconciliation in the test + SUMMARY.
- **`scripts/check_readme_hero_hash.py` already exists** and is green against the `sha256=PLACEHOLDER` sentinel in README (hero block at README lines 9-21, `<video src="docs/assets/demo.mp4" ... poster="docs/assets/demo-placeholder.gif">`). GH-01 keeps it green; do NOT rewrite it. Note the poster is currently `demo-placeholder.gif` — GH-01 adds `demo-poster.png` and may repoint the `poster=` attr (decided in planning; keep the hash sentinel green either way).
- **`docs/assets/social-card.png` (380k, hand-cut) already exists.** GH-03's `og-card.png` is the source-generated successor. Decide in planning: either (a) regenerate og-card.png from source + keep social-card.png as a MANIFEST opt-out bespoke asset, or (b) supersede social-card.png. Recommended (a) — least destructive, social-card.png may be referenced elsewhere (grep before deleting).
- **Lighthouse can't run against a live Pages URL in CI** (Pages isn't enabled until Kaan flips repo settings). GH-02 runs Lighthouse against a LOCAL static-server build of `docs/landing/` in CI (lighthouse-ci or `lighthouse http://localhost:PORT`), and routes the live-URL run to §V7-LANDING. Engineering closes on the local/CI Lighthouse pass.

### Wave Decomposition (5 plans, dependency-ordered — UNLIKE Phase 69, Phase 70 HAS inter-wave deps)
- **Wave 0 (70P01) — GH-04 asset infra:** `scripts/regenerate_assets.sh` + `docs/assets/MANIFEST.yaml` + `.github/workflows/asset-bitrot.yml` + `tests/repo/test_asset_manifest_shape.py`. Foundational — no deps. MANIFEST starts with whatever source-derived assets exist today (architecture.svg if it has a source; else MANIFEST is seeded empty + grows in Wave 1).
- **Wave 1 (70P02) — GH-03 og-card:** `docs/assets/sources/og-card.html` (Tailwind+Puppeteer, CDJ-Whisper) + wire into `regenerate_assets.sh` + `og-card.png` output + MANIFEST SHA pin + README `<meta property="og:image">`. **Depends on Wave 0** (regenerate_assets.sh + MANIFEST exist).
- **Wave 2 (70P03) — GH-02 landing (frontend, needs UI-SPEC):** `docs/landing/index.html` + assets + CDJ-Whisper CSS + hero/CTA/waitlist + lighthouse CI workflow + anti-backsliding grep gate + `og:image` meta (reuses Wave 1's og-card). **Depends on Wave 1** (og:image). Biggest wave; UI-SPEC governs.
- **Wave 3 (70P04) — GH-01 demo film:** `docs/assets/demo-poster.png` (engineering-generated poster, CDJ-Whisper still) + keep hero-hash green + route real demo.mp4 to §ASSETS-DEMO-CUT (verify/extend existing cluster). Largely KAAN-ACTION; engineering ships the poster + placeholder-green gate. No hard dep (can run parallel to Waves 1-2) but scheduled here for clean ordering.
- **Wave 4 (70P05) — GH-05 presence suite:** `tests/repo/test_github_presence.py` one-stop suite. **Depends on Waves 0-3** (pins all their artifacts). LAST.

### CDJ-Whisper Aesthetic Lock (frontend-enforcement skill — Waves 1 + 2)
- **Fonts:** Saira (display/body) + JetBrains Mono (numerals/code) via Google Fonts. NO Geist, NO Fraunces, NO Inter/Roboto/Arial/system-ui. The anti-backsliding gate `grep -ri 'geist\|fraunces' docs/landing/` MUST return zero.
- **Palette (from `mocks/vibemix-direction-final.html`):** 5 warm blacks `--void: #000000 / --void-1: #020205 / --void-2: #05070b / --void-3: #0a0c12 / --void-4: #11141c`; single amber accent `--amber: #ff8a3d` (+ `--amber-deep: #ff5a1a`, `--amber-pale: #ffb88a`); ink `--silk: #d6cfc7`. 20/80 rule: ~80% warm-black/silk, ~20% amber accent only on LEDs/CTAs/active states.
- **Material feel:** brushed-aluminum gradients, anodised panel depth, faint scanlines, glowing amber LED accents, inset/raised bevels. NO flat `#1a1a1a` fills. Pioneer/Roland industrial vocabulary.
- **Baseline references:** `mocks/vibemix-direction-final.html` (palette + fonts source-of-truth), `mocks/vibemix-cinematic-storyboard.html` (hero demo storyboard), `mocks/vibemix-app-ui.html` (live session UI shape). The landing should feel like the same product.
- **UI-SPEC:** Wave 2 gets a `gsd-ui-phase` UI-SPEC.md design contract BEFORE planning that wave's tasks (frontend phase — orchestrator generates it).

### Waitlist hook (GH-02, locked v3.0 funnel rule)
- Opt-in Bravoh-waitlist CTA on the landing, UTM-tracked, **default-OFF** (no tracking fires unless the visitor clicks through). Links to the Bravoh waitlist (`altidus.world` waitlist endpoint or the canonical Bravoh signup — confirm the exact URL in planning; if unknown, use a placeholder + route the real URL to §V7-LANDING). NO analytics script that auto-loads on page view (privacy + anti-slop).

### Claude's Discretion
- Static-site tooling for `docs/landing/` — recommended: plain HTML/CSS/JS (no build step, GitHub-Pages-native, matches the `mocks/*.html` precedent which are all single-file no-build). Avoid a heavy framework (Astro/Next) — overkill for a one-page landing + adds a build dep. Pick plain HTML unless planning surfaces a strong reason.
- Puppeteer invocation shape in `regenerate_assets.sh` — `npx puppeteer` screenshot of the og-card.html at 1200×630, OR a small Node script in `docs/assets/sources/`. Pick whichever is cleaner; Node/npx is CI-side, not a Python dep.
- Whether `regenerate_assets.sh` is bash or a Python script — prefer bash (matches `cut_release.sh` / `sync_packaging.sh` precedent) calling `npx puppeteer` + `shasum`.
- Exact MANIFEST.yaml schema — recommend `assets: [{path, source, sha256, generator}]` list + an `opt_out: [paths]` for bespoke hand-cut assets.
- Whether badge-URL checks in test_github_presence.py are `@pytest.mark.network` (deselected by default grid, run in CI with network) — YES, recommended, so the default `pytest -q` stays offline-clean.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mocks/vibemix-direction-final.html` — CDJ-Whisper palette + Saira/JetBrains-Mono fonts source-of-truth (Wave 1 + 2 lift the CSS variables verbatim).
- `mocks/vibemix-cinematic-storyboard.html` + `mocks/vibemix-app-ui.html` — hero storyboard + product UI shape (Wave 2 landing visual reference).
- `docs/assets/` — existing `hero.png` (137k), `social-card.png` (380k hand-cut), `demo-placeholder.gif`, `readme-hero.png/webm`, `architecture.svg`. Wave 0 MANIFEST inventories these.
- `scripts/check_readme_hero_hash.py` — existing, green against the README `sha256=PLACEHOLDER` sentinel. GH-01 keeps it green.
- `scripts/glb_optimize.py` + `docs/asset_pipeline.md` — existing asset-pipeline precedent (mascot GLBs); `regenerate_assets.sh` follows the same "doc is doctrine, script is runnable" shape.
- `.github/workflows/full-test-matrix.yml` + `packaging-audit.yml` (Phase 67P04 + 69-04) — SHA-pinned-actions CI template that `asset-bitrot.yml` + the lighthouse workflow lift (permissions.contents: read, on: pull_request not pull_request_target, fail-fast: false, timeout-minutes, concurrency cancel-in-progress).
- `.github/ISSUE_TEMPLATE/*.yml` (5 forms) + `.github/pull_request_template.md` — existing; GH-05 validates their real `.yml` Forms shape.
- `tests/repo/test_oss_presence.py` (Phase 69-01) — the four-OSS-files presence pattern that GH-05 re-uses for its OSS-files sub-check.
- `tests/repo/test_packaging_scaffolds_present.py` + `test_byo_doc_shape.py` (Phase 69) — parametrized presence-test shape that `test_github_presence.py` mirrors.

### Established Patterns
- **Single-file no-build mocks** — all `mocks/*.html` are self-contained (inline `<style>` + Google Fonts link, no bundler). The Pages landing follows this (plain HTML/CSS/JS, GitHub-Pages-native).
- **Hash-pinned assets** — `check_readme_hero_hash.py` + the README `sha256=` sentinel establish the hash-pin pattern; MANIFEST.yaml + asset-bitrot.yml generalize it.
- **`@pytest.mark.network` for live HTTP** — badge-URL 200 checks deselected from default grid (the default `pytest -q` is offline-clean per Phase 67/68 markers).
- **KAAN-ACTION clusters for live/external gates** — §ASSETS-DEMO-CUT (existing) for the demo film, §V7-LANDING (NEW or existing) for Pages-live + Kaan-felt sign-off.
- **frontend-enforcement skill** auto-loads for any frontend work — 20/80 rule, textured material, no AI slop, CDJ-Whisper hardware vocabulary.

### Integration Points
- `README.md` — Wave 1 adds `<meta property="og:image">` (if README supports meta — it's GitHub-rendered markdown, so the og:image meta lives in the Pages `index.html`, and the README references og-card.png via a visible `<img>` or the social-preview is set in repo settings → route repo-settings social-preview to §V7-LANDING). Wave 3 keeps the hero `<video>` sentinel green.
- `docs/landing/index.html` — NEW (Wave 2); the Pages site root.
- `docs/assets/sources/og-card.html` — NEW (Wave 1); Puppeteer source.
- `docs/assets/MANIFEST.yaml` + `scripts/regenerate_assets.sh` — NEW (Wave 0).
- `.github/workflows/asset-bitrot.yml` + the lighthouse workflow — NEW (Wave 0 + Wave 2).
- `tests/repo/test_github_presence.py` — NEW (Wave 4).
- `KAAN-ACTION-LEGAL.md` — Wave 2 (§V7-LANDING) + Wave 3 (§ASSETS-DEMO-CUT verify/extend).

</code_context>

<specifics>
## Specific Ideas

- **Anti-backsliding gate:** `grep -ri 'geist\|fraunces' docs/landing/` returns zero matches (exact gate from ROADMAP SC2 + memory project_visual_direction_cdj_whisper — Geist + Fraunces were tried in v1 and REJECTED).
- **OG card dimensions:** exactly 1200×630 (`og-card.png`).
- **Demo asset size cap:** ≤ 8 MB (`8388608` bytes).
- **Hero hash sentinel:** the literal `sha256=PLACEHOLDER` in README stays until the real demo.mp4 lands (keeps `check_readme_hero_hash.py` green under autonomous mode).
- **Lighthouse thresholds:** a11y ≥ 95, perf ≥ 90 (run against local build in CI; live-URL run → §V7-LANDING).
- **Fonts:** `Saira` + `JetBrains Mono` (Google Fonts) — exact family names for the landing + og-card.
- **Amber accent:** `#ff8a3d` (primary), the single 20%-surface accent.
- **§V7-LANDING cluster:** holds (a) Pages enablement + live-URL Lighthouse, (b) Kaan-felt CDJ-Whisper aesthetic sign-off, (c) the real Bravoh-waitlist URL if unknown at execution.
- **§ASSETS-DEMO-CUT cluster:** existing — GH-01 verifies it covers the 30-sec film capture + ≤8MB + cross-browser inline-play; extends if needed.

</specifics>

<deferred>
## Deferred Ideas

- **Real demo.mp4 30-sec film** — Francesco's capture day (v3.0 P43 VIS-09 runbook) → §ASSETS-DEMO-CUT. Engineering ships poster + placeholder-green.
- **GitHub Pages enablement + live-URL Lighthouse run** — Kaan flips repo Settings → Pages; the live `bravoh-ai.github.io/vibemix` run → §V7-LANDING. Engineering closes on local/CI Lighthouse.
- **Kaan-felt CDJ-Whisper aesthetic sign-off** — taste gate, not auto-checkable → §V7-LANDING. Engineering closes when anti-backsliding grep + Lighthouse + asset-reproducibility pass.
- **Repo social-preview image** (GitHub Settings → social preview) — manual repo-settings action → §V7-LANDING.
- **Real Bravoh-waitlist URL** — if unknown at execution, placeholder + → §V7-LANDING.
- **Homebrew/Scoop actual publish** — already deferred in Phase 69 OSS-05 (future milestone), not Phase 70 scope.

</deferred>
