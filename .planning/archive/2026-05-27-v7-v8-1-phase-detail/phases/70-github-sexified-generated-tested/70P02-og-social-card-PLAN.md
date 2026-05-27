---
phase: 70-github-sexified-generated-tested
plan: 02
type: execute
wave: 1
depends_on: [70-01]
files_modified:
  - docs/assets/sources/og-card.html
  - scripts/regenerate_assets.sh
  - docs/assets/og-card.png
  - docs/assets/MANIFEST.yaml
  - README.md
  - tests/repo/test_docs_assets.py
autonomous: true
requirements: [GH-03]
must_haves:
  truths:
    - "docs/assets/og-card.png exists at exactly 1200×630"
    - "og-card.png is generated from docs/assets/sources/og-card.html via scripts/regenerate_assets.sh (re-running is byte-identical or differs only by intentional source edits)"
    - "og-card.png is pinned by SHA-256 in docs/assets/MANIFEST.yaml"
    - "The OG card holds CDJ-Whisper DNA (Saira + JetBrains Mono, amber #ff8a3d, void palette) and reads legibly at thumbnail scale"
    - "The README references the card via a visible <img> or a documented social-preview path"
  artifacts:
    - path: "docs/assets/sources/og-card.html"
      provides: "Headless-render source template, 1200×630, CDJ-Whisper aesthetic"
      contains: "ff8a3d"
    - path: "docs/assets/og-card.png"
      provides: "Generated 1200×630 OG/social card"
    - path: "docs/assets/MANIFEST.yaml"
      provides: "og-card entry with pinned sha256"
      contains: "og-card.png"
  key_links:
    - from: "scripts/regenerate_assets.sh"
      to: "docs/assets/sources/og-card.html"
      via: "headless render step → og-card.png"
      pattern: "og-card"
    - from: "docs/assets/MANIFEST.yaml"
      to: "docs/assets/og-card.png"
      via: "assets entry {path, source, sha256, generator}"
      pattern: "og-card\\.png"
---

<objective>
Generate the OG/social card (GH-03): a 1200×630 CDJ-Whisper card rendered from a source
template, wired into the Wave 0 regenerator, pinned by SHA-256 in MANIFEST.yaml, and
referenced by the README. This is the source-generated, hash-pinned successor to the
hand-cut docs/assets/social-card.png (which Wave 0 already opted-out as bespoke).

Purpose: A thumbnail that reads as the same product on Slack/Discord/Twitter unfurl —
no hand-cut bitrot, regenerable from source.
Output: docs/assets/sources/og-card.html + docs/assets/og-card.png + regenerator wiring + MANIFEST pin + README reference.
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

<!-- BINDING DESIGN CONTRACT for the card (## OG / Social Card Contract section): -->
@.planning/phases/70-github-sexified-generated-tested/70-UI-SPEC.md
<!-- CDJ-Whisper palette + Saira/JetBrains-Mono fonts source-of-truth — lift :root + body gradients VERBATIM. -->
<!-- DO NOT lift tokens from mocks/vibemix-cinematic-storyboard.html (it carries REJECTED Geist/Inter). -->
@mocks/vibemix-direction-final.html
<!-- Wave 0 artifacts this wave extends — the regenerator dispatcher extension point + the MANIFEST schema: -->
@scripts/regenerate_assets.sh
@docs/assets/MANIFEST.yaml
@tests/repo/test_asset_manifest_shape.py
<!-- Headless-render precedent (Chrome --headless=new --screenshot --window-size, EXIT trap): -->
@docs/assets/screenshots/regen.sh
<!-- The 2 MB docs/assets image budget gate — current total ~1.44 MB, ~559 KB headroom; og-card.png consumes against it: -->
@tests/repo/test_docs_assets.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author docs/assets/sources/og-card.html (CDJ-Whisper, 1200×630)</name>
  <files>docs/assets/sources/og-card.html</files>
  <read_first>
    - docs/assets/sources/og-card.html (does NOT exist — create; the docs/assets/sources/ dir also does not exist yet)
    - .planning/phases/70-github-sexified-generated-tested/70-UI-SPEC.md (## OG / Social Card Contract — the binding spec)
    - mocks/vibemix-direction-final.html (lift :root tokens + body vignette + film-grain VERBATIM)
  </read_first>
  <action>
    Create docs/assets/sources/og-card.html — a single self-contained HTML file sized to a fixed 1200×630
    canvas (the root container is exactly 1200×630px; NOT responsive — it is a headless-render source
    template). Per the UI-SPEC OG / Social Card Contract: background = the void stack + cinematic vignette +
    film-grain, lifting the `:root` CSS custom properties + the `body` `radial-gradient`/`linear-gradient` +
    the `body::before` film-grain feTurbulence data-URIs VERBATIM from mocks/vibemix-direction-final.html.
    Centered composition: the `vibemix` wordmark in Saira condensed-heavy (`font-variation-settings: 'wdth' 82,
    'wght' 700`, large ~120–160px since the canvas is fixed), the one-line pitch beneath in Saira `wght 400`
    silk-65 reading exactly `the only AI co-host that actually listens to your set` (≥28px on the 1200-wide
    canvas), and a SINGLE amber accent — either the brand LED dot or one amber word (20/80 rule holds at card
    scale; amber is ~one element, NOT a wash). One JetBrains-Mono micro-label `OPEN SOURCE · MAC + WIN`.
    Load Saira + JetBrains Mono via Google Fonts `<link rel="preconnect">` + `<link href>` exactly as the mock
    does. Tailwind utility classes ARE allowed INSIDE this card source per UI-SPEC (it is a headless-render
    template, NOT the landing — the no-Tailwind constraint is landing-specific) — but FONTS + PALETTE + 20/80 +
    the no-Geist/no-Fraunces rule still apply. Amber accent literal MUST be `#ff8a3d`. Document the deliberate
    weight set + why in a CSS comment (frontend-enforcement rule 5).
  </action>
  <verify>
    <automated>test -f docs/assets/sources/og-card.html && grep -ci 'saira' docs/assets/sources/og-card.html && grep -c 'ff8a3d' docs/assets/sources/og-card.html && grep -c 'the only AI co-host that actually listens' docs/assets/sources/og-card.html && test "$(grep -ric 'geist\|fraunces' docs/assets/sources/og-card.html)" = "0" && echo "og-card.html aesthetic gates pass"</automated>
  </verify>
  <acceptance_criteria>
    - `docs/assets/sources/og-card.html` exists.
    - `grep -ci 'saira' docs/assets/sources/og-card.html` ≥1 AND `grep -ci 'jetbrains' docs/assets/sources/og-card.html` ≥1 (both fonts present).
    - `grep -c 'ff8a3d' docs/assets/sources/og-card.html` ≥1 (amber accent literal).
    - `grep -ric 'geist\|fraunces' docs/assets/sources/og-card.html` returns 0 (anti-backsliding).
    - `grep -ric 'inter\b\|roboto\|arial' docs/assets/sources/og-card.html` returns 0 (no AI-slop fonts as primary).
    - The exact pitch string `the only AI co-host that actually listens to your set` is present.
  </acceptance_criteria>
  <done>og-card.html source template authored in CDJ-Whisper aesthetic, fonts + palette + 20/80 + anti-backsliding all clean.</done>
</task>

<task type="auto">
  <name>Task 2: Wire the og-card generator, render og-card.png, pin in MANIFEST, reference from README, reconcile budget</name>
  <files>scripts/regenerate_assets.sh, docs/assets/og-card.png, docs/assets/MANIFEST.yaml, README.md, tests/repo/test_docs_assets.py</files>
  <read_first>
    - scripts/regenerate_assets.sh (the Wave 0 dispatcher extension point comment)
    - docs/assets/MANIFEST.yaml (the assets: [] list Wave 0 seeded)
    - README.md (lines 1-21 — the hero block + where a visible card <img> / social-preview note belongs)
    - tests/repo/test_docs_assets.py (the 2 MB budget gate + dimension-test precedent)
    - docs/assets/screenshots/regen.sh (headless-Chrome --screenshot --window-size pattern)
  </read_first>
  <action>
    Slot an `og-card` generator step into scripts/regenerate_assets.sh at the Wave 0 extension-point comment.
    Render docs/assets/sources/og-card.html to docs/assets/og-card.png at EXACTLY 1200×630 — use the headless
    render mechanism (either `npx puppeteer` screenshot at viewport 1200×630, OR headless Chrome
    `--headless=new --screenshot --window-size=1200,630 --force-device-scale-factor=1` mirroring regen.sh; pick
    the cleaner one per CONTEXT Claude's-Discretion; Node/npx is CI-side, NOT a Python dep). Set a fixed
    viewport + scale factor + wait-for-fonts so re-runs are byte-stable; if perfect byte-determinism is not
    achievable across Chrome minor versions, document the tolerance in a script comment — the asset-bitrot
    gate's "differs ONLY by intentional source edits" clause covers chrome-version drift, but aim for stable.

    Run the regenerator to produce og-card.png, then append the og-card entry to MANIFEST.yaml `assets:`:
    `{path: docs/assets/og-card.png, source: docs/assets/sources/og-card.html, sha256: <real 64-hex>,
    generator: og-card}`. The shape MUST pass tests/repo/test_asset_manifest_shape.py unchanged.

    Reference the card from the README per CONTEXT integration note: README is GitHub-rendered markdown so a
    raw `<meta property="og:image">` does NOT render there (the live <meta> tag lives in the Wave 2 landing
    `<head>`). For the README, add a visible `<img src="docs/assets/og-card.png" alt="vibemix — the only AI
    co-host that actually listens" ...>` somewhere that fits the composition (or, if it disrupts the hero, add
    an HTML comment documenting that the repo social-preview is set via repo Settings → route that repo-settings
    action to §V7-LANDING, NOT this wave). EITHER WAY ensure the literal path `docs/assets/og-card.png` appears
    in README.md so Wave 4's presence test can assert the reference.

    BUDGET RECONCILIATION (load-bearing): the 2 MB docs/assets image gate in test_docs_assets.py currently sits
    at ~1.44 MB (~559 KB headroom). Measure og-card.png's size. If current+og-card stays < 2 MB, leave the gate
    untouched and confirm it still passes. If og-card.png pushes the total ≥ 2 MB, FIRST shrink the card (PIL
    quantize-256 + optimize, or fewer gradient stops) to fit. If after optimization it genuinely cannot fit AND
    staying under 2 MB would force degrading the card below the UI-SPEC legibility bar, bump the cap in
    test_docs_assets.py to a documented new ceiling (e.g. 2.5 MB) with a one-paragraph comment: the og-card
    (+ Wave 3's demo-poster) are new launch-required source-generated assets, LFS is banned, the new ceiling is
    the realistic-artifact scale. Do NOT silently raise the cap — the comment is mandatory. Prefer shrinking.
  </action>
  <verify>
    <automated>bash scripts/regenerate_assets.sh && source .venv/bin/activate && PYTHONPATH=src python3 -c "from PIL import Image; im=Image.open('docs/assets/og-card.png'); assert im.size==(1200,630), im.size; print('og-card 1200x630 OK')" && PYTHONPATH=src python3 -c "import yaml; d=yaml.safe_load(open('docs/assets/MANIFEST.yaml')); e=[a for a in d['assets'] if a['path']=='docs/assets/og-card.png']; assert len(e)==1 and e[0]['sha256']!='PENDING', e; print('MANIFEST og-card pinned')" && grep -c 'og-card.png' README.md && PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py tests/repo/test_docs_assets.py -q && git diff --exit-code docs/assets/og-card.png && echo "regenerator deterministic"</automated>
  </verify>
  <acceptance_criteria>
    - `bash scripts/regenerate_assets.sh` exits 0 and produces docs/assets/og-card.png.
    - og-card.png is EXACTLY 1200×630 (`PIL Image.open(...).size == (1200, 630)`).
    - `git diff --exit-code docs/assets/og-card.png` exits 0 after a re-run (deterministic / committed matches regenerated).
    - MANIFEST.yaml has exactly one `assets` entry with `path == docs/assets/og-card.png` and a real 64-hex sha256 (not PENDING).
    - `grep -c 'og-card.png' README.md` ≥1 (referenced).
    - `pytest tests/repo/test_asset_manifest_shape.py tests/repo/test_docs_assets.py -q` exits 0 (budget reconciled, schema intact).
  </acceptance_criteria>
  <done>og-card.png generated 1200×630, regenerable, MANIFEST-pinned, README-referenced, image budget reconciled with documented decision.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| og-card.html source ↔ committed PNG | Drift caught by asset-bitrot gate (Wave 0) |
| npx/headless render in regenerator | Untrusted npm fetch surface during regeneration |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-70P02-01 | Tampering | og-card.png drift from source | mitigate | regenerator is deterministic (fixed viewport+scale); MANIFEST sha256 pin + Wave 0 asset-bitrot git-diff gate catch drift |
| T-70P02-02 | Spoofing | OG card content (brand impersonation at thumbnail) | accept | static self-authored card, no user input, no fetch — nothing to spoof |
| T-70P02-SC | Tampering | npx puppeteer / headless-chrome supply chain | mitigate | render runs only in the regenerator (dev/CI), produces a deterministic PNG verified by git-diff; no puppeteer entry added to pyproject.toml/uv.lock (Node/CI-side); if `npx puppeteer` is used, it pins via npx's lockfile-less ephemeral run only at regeneration time — the committed PNG is the trust anchor, not the tool |
</threat_model>

<verification>
Per-wave gate (run from repo root):
```
bash scripts/regenerate_assets.sh
git diff --exit-code docs/assets/og-card.png   # deterministic
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py tests/repo/test_docs_assets.py -q
grep -ric 'geist\|fraunces' docs/assets/sources/og-card.html   # MUST be 0
git diff --stat HEAD -- src/vibemix/   # MUST be empty
git diff --stat HEAD -- pyproject.toml uv.lock   # MUST be empty — Node/npx is CI-side, not a Python dep
```
</verification>

<success_criteria>
- docs/assets/sources/og-card.html authored in CDJ-Whisper (Saira + JetBrains Mono + amber #ff8a3d), anti-backsliding clean.
- docs/assets/og-card.png generated at 1200×630, regenerable, MANIFEST-pinned by SHA-256.
- README references docs/assets/og-card.png.
- 2 MB image budget reconciled (shrink-first; documented cap bump only if forced).
- ZERO src/vibemix/ edits. ZERO pyproject.toml/uv.lock edits (Puppeteer is Node/CI-side).
</success_criteria>

<output>
Create `.planning/phases/70-github-sexified-generated-tested/70P02-SUMMARY.md` when done.
</output>
