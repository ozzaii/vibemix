---
phase: 70-github-sexified-generated-tested
plan: 04
type: execute
wave: 3
depends_on: []
files_modified:
  - docs/assets/sources/demo-poster.html
  - scripts/regenerate_assets.sh
  - docs/assets/demo-poster.png
  - docs/assets/MANIFEST.yaml
  - README.md
  - KAAN-ACTION-LEGAL.md
autonomous: true
requirements: [GH-01]
must_haves:
  truths:
    - "docs/assets/demo-poster.png exists as a CDJ-Whisper still poster, source-generated + MANIFEST-pinned"
    - "scripts/check_readme_hero_hash.py stays GREEN (the sha256=PLACEHOLDER sentinel is preserved until the real demo.mp4 lands)"
    - "The README hero <video> poster points at a committed, non-broken poster (no 404)"
    - "§ASSETS-DEMO-CUT KAAN-ACTION cluster exists and covers the 30-sec film capture + <=8MB cap + cross-browser inline-play"
  artifacts:
    - path: "docs/assets/demo-poster.png"
      provides: "CDJ-Whisper still poster for the README + landing demo embed"
    - path: "KAAN-ACTION-LEGAL.md"
      provides: "§ASSETS-DEMO-CUT cluster routing the real 30-sec demo.mp4 capture"
      contains: "§ASSETS-DEMO-CUT"
  key_links:
    - from: "README.md"
      to: "docs/assets/demo-poster.png"
      via: "video poster= attribute"
      pattern: "demo-poster\\.png"
    - from: "scripts/check_readme_hero_hash.py"
      to: "README hero block"
      via: "sha256=PLACEHOLDER sentinel"
      pattern: "PLACEHOLDER"
---

<objective>
Ship the engineering side of GH-01: a source-generated CDJ-Whisper demo poster, the README
hero kept green via the sha256=PLACEHOLDER sentinel (the real 30-sec demo.mp4 is Francesco's
capture day — gated), and a §ASSETS-DEMO-CUT KAAN-ACTION cluster routing the real film. The
poster carries the visual until the film lands; the hero-hash gate stays green either way.

Purpose: A non-broken, on-brand demo embed today + a clean fix-path for the real film —
under gsd-autonomous fully the capture does NOT block; engineering closes on the poster +
placeholder-green gate.
Output: docs/assets/sources/demo-poster.html + docs/assets/demo-poster.png + regenerator wiring + MANIFEST pin + README poster repoint + KAAN-ACTION-LEGAL.md §ASSETS-DEMO-CUT.
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

<!-- The hero-hash gate this wave keeps GREEN — do NOT rewrite it; preserve the PLACEHOLDER sentinel: -->
@scripts/check_readme_hero_hash.py
<!-- The README hero <video> block (lines 9-21) — demo.mp4 src + poster=demo-placeholder.gif today: -->
@README.md
<!-- CDJ-Whisper aesthetic source-of-truth for the poster still — lift :root + body VERBATIM (no Geist/Fraunces): -->
@mocks/vibemix-direction-final.html
<!-- Wave 0 + 1 infra the poster registers into (regenerator dispatcher + MANIFEST schema): -->
@scripts/regenerate_assets.sh
@docs/assets/MANIFEST.yaml
@tests/repo/test_asset_manifest_shape.py
<!-- The §V7-LIVE / §VIS-09 cluster shape §ASSETS-DEMO-CUT mirrors + the existing Francesco-capture VIS-09 runbook (line ~1344): -->
@KAAN-ACTION-LEGAL.md
<!-- 2 MB image budget gate the poster consumes against (already reconciled in Wave 1 if a bump was needed): -->
@tests/repo/test_docs_assets.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate docs/assets/demo-poster.png + repoint the README hero poster (keep hash green)</name>
  <files>docs/assets/sources/demo-poster.html, scripts/regenerate_assets.sh, docs/assets/demo-poster.png, docs/assets/MANIFEST.yaml, README.md</files>
  <read_first>
    - docs/assets/sources/demo-poster.html (does NOT exist — create; may share the Wave 1 og-card CDJ-Whisper structure)
    - scripts/check_readme_hero_hash.py (understand the PLACEHOLDER sentinel logic — must stay green; do NOT modify this script)
    - README.md (lines 9-21 — the vibemix:hero-start block; poster currently = demo-placeholder.gif)
    - scripts/regenerate_assets.sh (the og-card generator from Wave 1 — add a sibling demo-poster step)
    - docs/assets/MANIFEST.yaml (the assets list with og-card; add demo-poster)
  </read_first>
  <action>
    Create docs/assets/sources/demo-poster.html — a CDJ-Whisper still poster source template. It may derive from
    the Wave 1 og-card.html structure but sized to the README hero / landing demo aspect (a 16:9-ish poster,
    e.g. 1280×720, OR match the hero <video width="720">). Lift the :root tokens + body vignette + film-grain
    VERBATIM from mocks/vibemix-direction-final.html. Show the vibemix "live session" feel — the .display-window
    LCD vocabulary from the UI-SPEC demo-embed note + a silk-40 mono caption `demo film coming soon` (the
    empty-state copy from the UI-SPEC Copywriting Contract). Amber accent literal #ff8a3d, 20/80 rule, no
    Geist/Fraunces/Inter.

    Add a `demo-poster` generator step to scripts/regenerate_assets.sh (sibling of the Wave 1 og-card step),
    rendering demo-poster.html → docs/assets/demo-poster.png via the same headless mechanism at the chosen fixed
    dimensions. Run the regenerator, recompute shasum, and append the MANIFEST.yaml `assets:` entry:
    `{path: docs/assets/demo-poster.png, source: docs/assets/sources/demo-poster.html, sha256: <real 64-hex>,
    generator: demo-poster}` — shape passes test_asset_manifest_shape.py unchanged. If the poster pushes the
    docs/assets image total over the budget cap in test_docs_assets.py (Wave 1 may already have reconciled it),
    shrink (PIL quantize-256 + optimize) first; only adjust the documented cap as a last resort with a comment.

    Repoint the README hero <video poster=...> from demo-placeholder.gif to docs/assets/demo-poster.png
    (CONTEXT reconciliation #2 allows the repoint). CRITICAL: do NOT touch the
    `<!-- vibemix:hero-start sha256=PLACEHOLDER path=docs/assets/demo.mp4 -->` sentinel — keep sha256=PLACEHOLDER
    so scripts/check_readme_hero_hash.py stays green (the real demo.mp4 has not landed; the gate is "asset
    pending → exit 0"). The <video src> still points at docs/assets/demo.mp4 (not-yet-present); the new poster +
    the existing <img> fallback keep the hero non-broken. Run check_readme_hero_hash.py to confirm exit 0.
  </action>
  <verify>
    <automated>bash scripts/regenerate_assets.sh && source .venv/bin/activate && PYTHONPATH=src python3 -c "from PIL import Image; Image.open('docs/assets/demo-poster.png').verify(); print('poster valid PNG')" && PYTHONPATH=src python3 scripts/check_readme_hero_hash.py && grep -c 'demo-poster.png' README.md && grep -c 'sha256=PLACEHOLDER' README.md && PYTHONPATH=src python3 -c "import yaml; d=yaml.safe_load(open('docs/assets/MANIFEST.yaml')); e=[a for a in d['assets'] if a['path']=='docs/assets/demo-poster.png']; assert len(e)==1 and e[0]['sha256']!='PENDING', e; print('MANIFEST poster pinned')" && PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py tests/repo/test_docs_assets.py tests/repo/test_readme_hero_hash_sync.py -q && git diff --exit-code docs/assets/demo-poster.png</automated>
  </verify>
  <acceptance_criteria>
    - `bash scripts/regenerate_assets.sh` produces docs/assets/demo-poster.png; `git diff --exit-code docs/assets/demo-poster.png` exits 0 (deterministic).
    - `python3 scripts/check_readme_hero_hash.py` exits 0 (PLACEHOLDER sentinel preserved — pending-asset path).
    - `grep -c 'sha256=PLACEHOLDER' README.md` >=1 (sentinel NOT rewritten).
    - `grep -c 'demo-poster.png' README.md` >=1 (poster repointed).
    - `grep -ric 'geist\|fraunces' docs/assets/sources/demo-poster.html` returns 0.
    - MANIFEST has a demo-poster entry with a real 64-hex sha256; `pytest tests/repo/test_asset_manifest_shape.py tests/repo/test_docs_assets.py tests/repo/test_readme_hero_hash_sync.py -q` exits 0.
  </acceptance_criteria>
  <done>demo-poster.png source-generated + MANIFEST-pinned + README hero repointed; check_readme_hero_hash.py green with the PLACEHOLDER sentinel intact.</done>
</task>

<task type="auto">
  <name>Task 2: Create the §ASSETS-DEMO-CUT KAAN-ACTION cluster</name>
  <files>KAAN-ACTION-LEGAL.md</files>
  <read_first>
    - KAAN-ACTION-LEGAL.md (the §VIS-09 Francesco capture-day runbook at line ~1344 to cross-reference + the §V7-LIVE 6-section cluster shape at line ~3710 to mirror)
  </read_first>
  <action>
    Append a NEW `## §ASSETS-DEMO-CUT — v7.0 GH-01 Real Demo Film Discharge` section to KAAN-ACTION-LEGAL.md
    (CONTEXT calls it "existing" but grep confirms NO §ASSETS-DEMO-CUT header exists — the only demo-capture
    surface is §VIS-09 Francesco capture day at line ~1344, so CREATE this cluster and cross-reference §VIS-09).
    Mirror the §V7-LIVE 6-section shape (read a live §V7-LIVE entry first to match heading + Sign-off format).
    The cluster covers the real 30-sec demo film per CONTEXT <specifics> §ASSETS-DEMO-CUT:
    - Surface/Tests it gates: the README `<video src="docs/assets/demo.mp4">` real asset + the
      scripts/check_readme_hero_hash.py PLACEHOLDER→real-SHA flip + the <=8 MB cap (8388608 bytes) + cross-browser
      inline-play on Chrome + Safari + Firefox;
    - Why it can't ship green in CI / autonomous: the 30-sec CDJ-Whisper hero film requires Francesco's capture
      day (the v3.0 P43 VIS-09 runbook — AV spec, mascot head-bob feel, palette sign-off); no engineering step
      can produce it;
    - Fix path: Francesco shoots per §VIS-09 → the editor cuts to <=8 MB → Kaan drops docs/assets/demo.mp4 +
      updates the README hero comment sha256=PLACEHOLDER → the real SHA-256 (check_readme_hero_hash.py then
      verifies the match) → Kaan confirms inline-play on the 3 browsers;
    - Owner-clock: Francesco (capture) + Kaan (drop + browser check), SOFT under gsd-autonomous fully — engineering
      closes on the poster + the PLACEHOLDER-green gate; the real film rides this clock and does NOT block close;
    - Cross-reference: §VIS-09 (Francesco capture-day runbook) · scripts/check_readme_hero_hash.py · README hero
      block · docs/assets/demo-poster.png (the interim still) · Wave 4 test_github_presence.py demo-asset+size check;
    - Sign-off block (☐ pending · ☐ done — date/SHA/<=8MB held yes-no/3-browser inline-play yes-no).
    State at the top: under gsd-autonomous fully this is a SOFT discharge; engineering closed on the poster +
    placeholder sentinel; the real film does not gate the milestone close.
  </action>
  <verify>
    <automated>grep -c '## §ASSETS-DEMO-CUT' KAAN-ACTION-LEGAL.md && grep -c '8388608\|8 MB\|8MB' KAAN-ACTION-LEGAL.md && grep -c 'VIS-09' KAAN-ACTION-LEGAL.md && grep -ci 'chrome.*safari.*firefox\|inline-play\|inline play' KAAN-ACTION-LEGAL.md && grep -c 'Sign-off' KAAN-ACTION-LEGAL.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '## §ASSETS-DEMO-CUT' KAAN-ACTION-LEGAL.md` returns 1 (new cluster header, exactly once).
    - The cluster covers: the real demo.mp4, the PLACEHOLDER→real-SHA flip, the <=8 MB cap (8388608), and cross-browser inline-play (Chrome + Safari + Firefox).
    - It cross-references §VIS-09 (the existing Francesco capture-day runbook) + scripts/check_readme_hero_hash.py.
    - It carries the §V7-LIVE 6-section shape including a Sign-off block.
    - It states the discharge is SOFT under gsd-autonomous fully and does NOT gate milestone close.
    - Pre-existing KAAN-ACTION-LEGAL.md content is byte-unchanged (append-only).
  </acceptance_criteria>
  <done>§ASSETS-DEMO-CUT cluster appended, routing the real 30-sec film to Francesco's capture clock with the <=8MB + cross-browser gates; cross-refs §VIS-09; soft under autonomous mode.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| README hero sentinel ↔ real asset | sha256=PLACEHOLDER vs a real ≤8MB film; the hash gate is the integrity anchor |
| poster source ↔ committed PNG | drift caught by the Wave 0 asset-bitrot gate |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-70P04-01 | Tampering | placeholder sentinel passing CI as if real | mitigate | check_readme_hero_hash.py distinguishes PLACEHOLDER (pending, exit 0) from a real SHA (must match the asset); a fake non-placeholder SHA with no asset fails the gate (anti-slop demo-honesty invariant) |
| T-70P04-02 | Tampering | demo-poster.png drift from source | mitigate | MANIFEST sha256 pin + Wave 0 asset-bitrot git-diff gate |
| T-70P04-03 | Denial of service | oversized demo asset bloats the clone | mitigate | the ≤8 MB cap (8388608) is gated by §ASSETS-DEMO-CUT + Wave 4 test_github_presence.py size assert |
| T-70P04-SC | Tampering | npx/headless render in regenerator | accept | poster render runs only in the regenerator (dev/CI), produces a deterministic PNG verified by git-diff; no Python dep added |
</threat_model>

<verification>
Per-wave gate (run from repo root):
```
bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/demo-poster.png
source .venv/bin/activate && PYTHONPATH=src python3 scripts/check_readme_hero_hash.py   # MUST exit 0 (PLACEHOLDER preserved)
grep -c 'sha256=PLACEHOLDER' README.md   # MUST be >=1
PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py tests/repo/test_docs_assets.py tests/repo/test_readme_hero_hash_sync.py -q
grep -c '## §ASSETS-DEMO-CUT' KAAN-ACTION-LEGAL.md   # MUST be 1
git diff --stat HEAD -- src/vibemix/   # MUST be empty
git diff --stat HEAD -- pyproject.toml uv.lock   # MUST be empty
```
</verification>

<success_criteria>
- docs/assets/demo-poster.png source-generated (CDJ-Whisper), MANIFEST-pinned, regenerable.
- README hero <video poster> repointed to demo-poster.png; sha256=PLACEHOLDER sentinel preserved; check_readme_hero_hash.py green.
- KAAN-ACTION-LEGAL.md §ASSETS-DEMO-CUT cluster created (real film + ≤8MB + cross-browser inline-play), cross-refs §VIS-09; soft under autonomous mode.
- ZERO src/vibemix/ edits. ZERO pyproject.toml/uv.lock edits.
</success_criteria>

<output>
Create `.planning/phases/70-github-sexified-generated-tested/70P04-SUMMARY.md` when done.
</output>
