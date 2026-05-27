---
phase: 70-github-sexified-generated-tested
plan: 03
type: execute
wave: 2
depends_on: [70-02]
files_modified:
  - docs/landing/index.html
  - docs/landing/style.css
  - docs/landing/app.js
  - .github/workflows/lighthouse.yml
  - KAAN-ACTION-LEGAL.md
autonomous: true
requirements: [GH-02]
must_haves:
  truths:
    - "docs/landing/ renders a single-page static site in the CDJ-Whisper aesthetic (5 warm blacks + single amber accent + Saira + JetBrains Mono)"
    - "The / route shows a 'what is this in 30 seconds' hero + install CTA (brew/scoop one-liners) + opt-in Bravoh-waitlist hook (default-OFF, no tracking on page view) + footer OSS links"
    - "Lighthouse against a LOCAL build returns a11y >=95 and perf >=90 in CI"
    - "grep -ri 'geist|fraunces' docs/landing/ returns zero (anti-backsliding gate holds)"
    - "The landing <head> references og-card.png via <meta property=og:image>"
  artifacts:
    - path: "docs/landing/index.html"
      provides: "The Pages site root — hero + demo + install CTA + waitlist + footer, semantic landmarks"
      contains: "og:image"
    - path: ".github/workflows/lighthouse.yml"
      provides: "CI Lighthouse against a local static-server build + anti-backsliding grep gate"
      contains: "accessibility"
    - path: "KAAN-ACTION-LEGAL.md"
      provides: "§V7-LANDING cluster (Pages-live + Kaan-felt sign-off + real waitlist URL)"
      contains: "§V7-LANDING"
  key_links:
    - from: "docs/landing/index.html"
      to: "docs/assets/og-card.png"
      via: "meta property og:image"
      pattern: "og:image"
    - from: ".github/workflows/lighthouse.yml"
      to: "docs/landing/"
      via: "local static server + lighthouse run + grep gate"
      pattern: "docs/landing"
---

<objective>
Build the GitHub Pages landing (GH-02): a single-file static CDJ-Whisper site that grabs
a stranger in 30 seconds, gives a clean install path (brew/scoop one-liners from Phase 69),
an opt-in default-OFF Bravoh-waitlist hook, and OSS footer links — gated in CI by a local
Lighthouse run (a11y >=95 / perf >=90) + an anti-backsliding grep. The live Pages URL, the
Kaan-felt aesthetic sign-off, and the real waitlist URL route to a NEW §V7-LANDING cluster.

Purpose: The front-porch a first-time visitor lands on — the conversion surface that warms
visitors into Bravoh waitlist signups.
Output: docs/landing/ static site + .github/workflows/lighthouse.yml + KAAN-ACTION-LEGAL.md §V7-LANDING.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/70-github-sexified-generated-tested/70-CONTEXT.md

<!-- THE BINDING DESIGN CONTRACT for this wave. Every token, layout, copy string, a11y rule, -->
<!-- interaction state, and the install-CTA / waitlist / footer shape come from here. Honor it verbatim. -->
@.planning/phases/70-github-sexified-generated-tested/70-UI-SPEC.md
<!-- Palette + Saira/JetBrains-Mono fonts + material treatment source-of-truth — lift :root + body + ::before VERBATIM. -->
<!-- HARD WARNING: do NOT lift tokens from mocks/vibemix-cinematic-storyboard.html — it carries REJECTED Geist/Inter. -->
@mocks/vibemix-direction-final.html
<!-- Wave 1 artifact this wave references — the og-card for the og:image meta: -->
@docs/assets/og-card.png
<!-- SHA-pinned CI workflow template (on: pull_request not pull_request_target, permissions.contents: read, concurrency, timeout-minutes): -->
@.github/workflows/packaging-audit.yml
<!-- The §V7-LIVE cluster shape this wave's §V7-LANDING mirrors (6-section: Tests/Why/Fix path/Owner-clock/Cross-ref/Sign-off): -->
@KAAN-ACTION-LEGAL.md
</context>

<interfaces>
<!-- Install one-liners the CTA renders (UI-SPEC Copywriting Contract — confirm exact formula/bucket path against Phase 69 packaging scaffolds at execution): -->
<!-- brew install bravoh-ai/tap/vibemix     (macOS — packaging/homebrew/Formula/vibemix.rb) -->
<!-- scoop install vibemix                  (Windows — packaging/scoop/vibemix.json) -->
<!-- Waitlist URL (placeholder; real canonical URL routes to §V7-LANDING): -->
<!-- https://altidus.world/waitlist?utm_source=vibemix&utm_medium=landing&utm_campaign=oss -->
<!-- frontend-enforcement skill (@.claude/skills/frontend-enforcement/SKILL.md) governs: 20/80 rule, textured material, no Geist/Fraunces/Inter. -->
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Build docs/landing/ static site (index.html + style.css + app.js)</name>
  <files>docs/landing/index.html, docs/landing/style.css, docs/landing/app.js</files>
  <read_first>
    - docs/landing/index.html (does NOT exist — create; the docs/landing/ dir does not exist yet)
    - .planning/phases/70-github-sexified-generated-tested/70-UI-SPEC.md (the FULL binding contract — Layout, Typography, Color, Material Treatment, Interaction States, Accessibility, Copywriting)
    - mocks/vibemix-direction-final.html (lift :root tokens, body vignette, body::before film-grain, .btn/.btn.on, .display-window, footer treatment VERBATIM)
  </read_first>
  <action>
    Build the Pages landing as plain static HTML/CSS/JS — NO framework, NO bundler, NO build step (HARD per
    UI-SPEC Design System + GitHub-Pages-native + the single-file mocks precedent). CSS may be inline in
    index.html OR a co-located docs/landing/style.css linked relatively (UI-SPEC discretion #5 prefers inline;
    executor's call as long as it stays buildless). JS is vanilla, inline or docs/landing/app.js.

    Implement the UI-SPEC Layout Contract document structure EXACTLY: one header (sticky meta-bar: vibemix
    wordmark + amber brand LED + version/tag mono text) · main with §1 Hero (two-zone grid 1.1fr 1fr
    collapsing at <=900px; headline = the 30-second pitch with one amber accent line; cinematic vignette bg +
    film-grain) · §2 Demo embed (recessed .display-window glass treatment; a video element with controls muted
    playsinline poster="../assets/demo-poster.png" and src="../assets/demo.mp4" plus an img poster fallback —
    poster + fallback keep it non-broken until the real demo.mp4 lands; descriptive alt; aspect-ratio 16/9 to
    avoid CLS) · §3 Install CTA (one amber-filled .btn.on primary GET VIBEMIX, beneath it a JetBrains-Mono
    recessed-glass code tile showing `brew install bravoh-ai/tap/vibemix` (mac) + `scoop install vibemix` (win)
    with tabular-nums + a vanilla-JS copy-to-clipboard affordance degrading gracefully to selectable text) ·
    §4 Waitlist opt-in (secondary silk tile by default — NO amber fill, NO analytics/tracking script
    auto-loading on page view; the UTM-tracked outbound anchor href
    https://altidus.world/waitlist?utm_source=vibemix&utm_medium=landing&utm_campaign=oss fires only on click;
    microcopy frames it as a Bravoh sibling) · footer (JetBrains-Mono small OSS links row: GitHub repo ·
    CONTRIBUTING · LICENSE Apache-2.0 · SECURITY · CODE_OF_CONDUCT).

    Lift ALL tokens VERBATIM from mocks/vibemix-direction-final.html :root: the 5 warm blacks
    (--void..--void-4), amber --amber #ff8a3d (+ --amber-deep/--amber-pale), silk --silk #d6cfc7 (+ silk
    alphas), glass tiers, spacing --sp-* scale, radii --rad-sm/md/lg, blur tokens. Fonts: Saira (display+body,
    variable wdth/wght axes) + JetBrains Mono (numerals/code) via Google Fonts link rel=preconnect + link
    href=...&display=swap exactly as the mock. Material treatment per UI-SPEC: body::before two-layer
    feTurbulence film-grain, cinematic vignette, glass panel bevels, .btn anodised + .btn.on amber backlight,
    recessed .display-window — NO flat #1a1a1a fills. 20/80 rule: amber ONLY on the 7 reserved elements from
    UI-SPEC Color (header LED, install CTA, hero accent line, <=2 lede keywords, footer links, waitlist
    activated-state, optional demo-window perimeter sweep).

    Copywriting: use the UI-SPEC Copywriting Contract draft VERBATIM (hero THE ONLY AI CO-HOST / amber accent
    THAT ACTUALLY LISTENS; the subhead; INSTALL / BUILT BY BRAVOH section headings; GET VIBEMIX /
    JOIN THE WAITLIST CTA labels; install sub-copy `macOS + Windows · free · open source`; the waitlist
    microcopy; footer links + tag line). Exact wording rides §V7-LANDING felt sign-off — ship this draft.

    Accessibility (Lighthouse a11y >=95 HARD — UI-SPEC Accessibility Contract): html lang="en", one h1
    (hero pitch), section h2s no skipped levels, exactly one header/main/footer, viewport meta, descriptive
    title + meta name=description, poster img descriptive alt, decorative SVG/grain aria-hidden="true", VISIBLE
    amber focus ring on EVERY interactive element (outline: 2px solid var(--amber); outline-offset: 2px — never
    bare outline:none), logical DOM focus order, no positive tabindex, >=44px touch targets on mobile for CTA +
    waitlist, and wrap ALL motion in @media (prefers-reduced-motion: reduce) {...} that disables
    animations/transitions.

    og:image: add meta property=og:image content pointing at og-card.png (use the form that resolves on Pages —
    https://bravoh-ai.github.io/vibemix/og-card.png OR a repo-relative ../assets/og-card.png) + meta
    property=og:title + meta property=og:description in head, referencing Wave 1's og-card.
  </action>
  <verify>
    <automated>test -f docs/landing/index.html && test "$(grep -ric 'geist\|fraunces' docs/landing/)" = "0" && grep -ci 'saira' docs/landing/index.html && grep -c 'og:image' docs/landing/index.html && grep -c 'lang="en"' docs/landing/index.html && grep -rc 'prefers-reduced-motion' docs/landing/ && grep -c 'brew install' docs/landing/index.html && grep -c 'utm_source=vibemix' docs/landing/index.html && test "$(grep -ric 'gtag\|googletagmanager\|fbq' docs/landing/)" = "0" && python3 -c "import html.parser; p=html.parser.HTMLParser(); p.feed(open('docs/landing/index.html').read()); print('html parses')"</automated>
  </verify>
  <acceptance_criteria>
    - docs/landing/index.html exists; the page parses as HTML.
    - `grep -ri 'geist\|fraunces' docs/landing/` returns ZERO matches (anti-backsliding gate — the load-bearing one).
    - `grep -ric 'inter\b\|roboto\|arial' docs/landing/` returns 0 as a PRIMARY face (system-ui only allowed inside the Saira fallback chain).
    - Saira + JetBrains Mono both referenced; amber #ff8a3d present; the 5 void hexes (#000000/#020205/#05070b/#0a0c12/#11141c) present.
    - `grep -c 'og:image' docs/landing/index.html` >=1 referencing og-card.png.
    - `grep -c 'lang="en"' docs/landing/index.html` >=1; exactly one h1; one header, one main, one footer.
    - `grep -rc 'prefers-reduced-motion' docs/landing/` >=1.
    - Install one-liners `brew install bravoh-ai/tap/vibemix` + `scoop install vibemix` present; the UTM waitlist link present; NO analytics auto-loaded (`grep -ric 'gtag\|googletagmanager\|fbq' docs/landing/` returns 0).
  </acceptance_criteria>
  <done>docs/landing/ ships a buildless CDJ-Whisper Pages site honoring the full UI-SPEC contract; anti-backsliding clean, a11y landmarks + reduced-motion + focus rings in place, og:image wired.</done>
</task>

<task type="auto">
  <name>Task 2: Lighthouse CI workflow (local build) + anti-backsliding grep gate</name>
  <files>.github/workflows/lighthouse.yml</files>
  <read_first>
    - .github/workflows/lighthouse.yml (does NOT exist — create)
    - .github/workflows/packaging-audit.yml (SHA-pinned actions, on: pull_request, permissions.contents: read, concurrency, timeout-minutes — lift posture)
  </read_first>
  <action>
    Create .github/workflows/lighthouse.yml. Lift the security posture VERBATIM from packaging-audit.yml:
    name: Lighthouse; on: { push: { branches: [main] }, pull_request: } (NOT pull_request_target);
    concurrency: { group: lighthouse-${{ github.ref }}, cancel-in-progress: true };
    permissions: { contents: read }; runs-on: ubuntu-latest; timeout-minutes: 15. Steps:
    (1) actions/checkout SHA-pinned to the SAME pin packaging-audit.yml uses
    (34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1);
    (2) anti-backsliding grep gate FIRST (fail fast): a step that runs
    `if grep -ri 'geist\|fraunces' docs/landing/; then echo "CDJ-Whisper typography lock broken"; exit 1; fi`
    — exit 1 on any match;
    (3) serve docs/landing/ on a LOCAL static server (Pages is NOT enabled in CI — CONTEXT reconciliation #4;
    use `python3 -m http.server PORT --directory docs/landing` backgrounded, or `npx http-server docs/landing -p
    PORT`, then target http://localhost:PORT);
    (4) run Lighthouse via `npx lighthouse http://localhost:PORT --only-categories=accessibility,performance
    --quiet --chrome-flags="--headless=new --no-sandbox" --output=json --output-path=./lh.json` then assert with
    a small inline node/python check that accessibility score >= 0.95 AND performance >= 0.90 — exit 1 if either
    falls short. Node/npx is CI-side, NOT a Python dep. Add a top-of-file comment block explaining: this runs
    Lighthouse against a LOCAL build (live Pages-URL run rides §V7-LANDING per CONTEXT reconciliation #4); the
    grep gate enforces the CDJ-Whisper typography lock.
  </action>
  <verify>
    <automated>source .venv/bin/activate && PYTHONPATH=src python3 -c "import yaml; w=yaml.safe_load(open('.github/workflows/lighthouse.yml')); assert w['jobs']; print('lighthouse.yml parses')" && grep -ci 'geist' .github/workflows/lighthouse.yml && grep -c 'accessibility' .github/workflows/lighthouse.yml && grep -Ec '0\.95|95' .github/workflows/lighthouse.yml && test "$(grep -c 'pull_request_target' .github/workflows/lighthouse.yml)" = "0" && grep -c '34e114876b0b11c390a56381ad16ebd13914f8d5' .github/workflows/lighthouse.yml</automated>
  </verify>
  <acceptance_criteria>
    - .github/workflows/lighthouse.yml parses as YAML and declares a job.
    - The workflow runs Lighthouse with `--only-categories=accessibility,performance` against a LOCAL static server (not a live URL).
    - It asserts a11y >= 0.95 and perf >= 0.90 (exit 1 below threshold).
    - It contains the anti-backsliding grep gate (`grep -ri 'geist\|fraunces' docs/landing/` → exit 1 on match).
    - `grep -c 'pull_request_target' .github/workflows/lighthouse.yml` returns 0 (fork-PR-safe).
    - `grep -c '34e114876b0b11c390a56381ad16ebd13914f8d5' .github/workflows/lighthouse.yml` >=1 (SHA-pinned checkout matching packaging-audit.yml).
  </acceptance_criteria>
  <done>CI Lighthouse gate runs against a local docs/landing/ build (a11y>=95/perf>=90) with the anti-backsliding grep; live-URL run deferred to §V7-LANDING.</done>
</task>

<task type="auto">
  <name>Task 3: Create the §V7-LANDING KAAN-ACTION cluster</name>
  <files>KAAN-ACTION-LEGAL.md</files>
  <read_first>
    - KAAN-ACTION-LEGAL.md (the §V7-LIVE section at line ~3710 — mirror its 6-section cluster shape; append §V7-LANDING after the §V7-LIVE block, before any later milestone surface)
  </read_first>
  <action>
    Append a NEW `## §V7-LANDING — v7.0 GH-02 Landing Live-Surface Discharge` section to KAAN-ACTION-LEGAL.md
    (it does NOT exist yet — confirmed by grep). Mirror the §V7-LIVE cluster 6-section shape (the executor must
    read the live §V7-LIVE-01 entry first to match the exact heading + Sign-off-block format). The cluster holds
    THREE soft Kaan-discharge items per CONTEXT <specifics> §V7-LANDING:
    (a) GitHub Pages enablement + live-URL Lighthouse run — Kaan flips repo Settings → Pages; the live
        bravoh-ai.github.io/vibemix Lighthouse run (engineering closed on the LOCAL/CI Lighthouse pass per
        reconciliation #4);
    (b) Kaan-felt CDJ-Whisper aesthetic sign-off — the taste gate that is NOT auto-checkable (engineering closes
        when the anti-backsliding grep + local Lighthouse + asset-reproducibility pass; the felt sign-off rides
        here and does NOT gate the milestone close under gsd-autonomous fully);
    (c) the real canonical Bravoh-waitlist URL — the landing ships with the placeholder
        https://altidus.world/waitlist?utm_source=vibemix&utm_medium=landing&utm_campaign=oss (UTM shape locked);
        if the real canonical URL differs, Kaan swaps it here;
    plus (d) the repo social-preview image (GitHub Settings → social preview using og-card.png) — manual
        repo-settings action.
    Each item gets the 6-section shape: Tests/Surface (what it gates), Why it can't ship green in CI / autonomous
    (Pages-not-enabled / taste-not-automatable / URL-unknown), Fix path (the exact Kaan steps), Owner-clock
    (Kaan, soft under gsd-autonomous fully), Cross-reference (docs/landing/index.html · .github/workflows/
    lighthouse.yml · §RECALL-EAR + §SHIP-V4 felt-sign-off precedent), and a Sign-off block
    (☐ pending · ☐ done — date/SHA/result). State explicitly at the top of the cluster: under gsd-autonomous
    fully these are SOFT discharges — engineering side closes when auto-checks pass; the felt sign-off + Pages
    enablement do NOT block the milestone close.
  </action>
  <verify>
    <automated>grep -c '§V7-LANDING' KAAN-ACTION-LEGAL.md && grep -c 'Kaan-felt' KAAN-ACTION-LEGAL.md && grep -c 'altidus.world/waitlist' KAAN-ACTION-LEGAL.md && grep -c 'Pages' KAAN-ACTION-LEGAL.md && grep -Ec 'Sign-off' KAAN-ACTION-LEGAL.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '## §V7-LANDING' KAAN-ACTION-LEGAL.md` returns 1 (the new cluster header, exactly once).
    - The cluster names all four soft items: Pages enablement + live-URL Lighthouse, Kaan-felt aesthetic sign-off, real waitlist URL, repo social-preview image.
    - It carries the §V7-LIVE 6-section shape including a Sign-off block (☐ pending · ☐ done — date/SHA/result).
    - It states the items are SOFT under gsd-autonomous fully and do NOT gate the milestone close.
    - Pre-existing KAAN-ACTION-LEGAL.md content above the new section is byte-unchanged (append-only).
  </acceptance_criteria>
  <done>§V7-LANDING cluster appended with the four soft Kaan-discharge items in the §V7-LIVE shape; autonomous-mode does not pause on them.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| visitor browser → static landing | Untrusted client renders the page; no server, no data fetch |
| visitor → outbound waitlist link | Click-through to altidus.world; UTM tracking only on intent |
| fork-PR → lighthouse.yml | Untrusted PR runs Lighthouse + grep gate in CI |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-70P03-01 | Information disclosure | analytics/tracking on page view | mitigate | NO analytics script auto-loads (default-OFF, locked v3.0 funnel rule); grep gate asserts zero gtag/fbq/analytics; UTM fires only on click |
| T-70P03-02 | Tampering | CDJ-Whisper typography lock backsliding | mitigate | lighthouse.yml grep gate `grep -ri 'geist\|fraunces' docs/landing/` exit 1 on match + Wave 4 presence test |
| T-70P03-03 | Elevation | lighthouse.yml on fork PRs | mitigate | on: pull_request (NOT pull_request_target) + permissions: contents: read — lifted from packaging-audit.yml |
| T-70P03-04 | Spoofing | outbound waitlist link target | accept | static self-authored href to altidus.world; real URL confirmed via §V7-LANDING; no open-redirect surface |
| T-70P03-SC | Tampering | npx lighthouse / npx http-server supply chain | accept | runs only in CI against a local build, produces a pass/fail score; no package added to pyproject.toml/uv.lock (Node/CI-side); the grep gate + a11y assertion are the trust anchors |
</threat_model>

<verification>
Per-wave gate (run from repo root):
```
grep -ri 'geist\|fraunces' docs/landing/   # MUST return zero (the load-bearing gate)
python3 -c "import html.parser; p=html.parser.HTMLParser(); p.feed(open('docs/landing/index.html').read())"
source .venv/bin/activate && PYTHONPATH=src python3 -c "import yaml; yaml.safe_load(open('.github/workflows/lighthouse.yml'))"
grep -c '## §V7-LANDING' KAAN-ACTION-LEGAL.md   # MUST be 1
git diff --stat HEAD -- src/vibemix/   # MUST be empty
git diff --stat HEAD -- pyproject.toml uv.lock   # MUST be empty — Lighthouse/http-server are Node/CI-side
```
</verification>

<success_criteria>
- docs/landing/ ships a buildless CDJ-Whisper static site (UI-SPEC contract honored), anti-backsliding clean, a11y + reduced-motion + focus rings, og:image wired to og-card.png.
- .github/workflows/lighthouse.yml runs local Lighthouse (a11y>=95/perf>=90) + the grep gate, fork-PR-safe + SHA-pinned.
- KAAN-ACTION-LEGAL.md §V7-LANDING cluster created (Pages-live + felt sign-off + waitlist URL + social-preview); soft under autonomous mode.
- ZERO src/vibemix/ edits. ZERO pyproject.toml/uv.lock edits.
</success_criteria>

<output>
Create `.planning/phases/70-github-sexified-generated-tested/70P03-SUMMARY.md` when done.
</output>
