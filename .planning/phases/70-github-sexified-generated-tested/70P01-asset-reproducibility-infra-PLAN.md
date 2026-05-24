---
phase: 70-github-sexified-generated-tested
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - scripts/regenerate_assets.sh
  - docs/assets/MANIFEST.yaml
  - .github/workflows/asset-bitrot.yml
  - tests/repo/test_asset_manifest_shape.py
autonomous: true
requirements: [GH-04]
must_haves:
  truths:
    - "Re-running scripts/regenerate_assets.sh produces byte-identical outputs for every MANIFEST-listed source-derived asset (or differs ONLY by intentional source edits)"
    - "A CI gate fails if a committed docs/assets/ asset drifts from its regenerated form"
    - "Hand-cut bespoke assets (social-card.png) are opt-out and do NOT break the gate"
    - "The MANIFEST schema is pinned by a test so future edits can't silently malform it"
  artifacts:
    - path: "scripts/regenerate_assets.sh"
      provides: "Deterministic regenerator for every source-derived asset; bash + shasum + headless-render"
      contains: "set -euo pipefail"
    - path: "docs/assets/MANIFEST.yaml"
      provides: "Enumeration of source-derived assets {path, source, sha256, generator} + opt_out list"
      contains: "assets:"
    - path: ".github/workflows/asset-bitrot.yml"
      provides: "CI bitrot gate — runs regenerator + git diff --exit-code docs/assets/"
      contains: "git diff --exit-code"
    - path: "tests/repo/test_asset_manifest_shape.py"
      provides: "Schema pin for MANIFEST.yaml (assets list shape + opt_out list)"
      contains: "yaml.safe_load"
  key_links:
    - from: ".github/workflows/asset-bitrot.yml"
      to: "scripts/regenerate_assets.sh"
      via: "workflow run step"
      pattern: "regenerate_assets\\.sh"
    - from: "tests/repo/test_asset_manifest_shape.py"
      to: "docs/assets/MANIFEST.yaml"
      via: "yaml.safe_load + key asserts"
      pattern: "MANIFEST\\.yaml"
---

<objective>
Land the FOUNDATIONAL asset-reproducibility infrastructure for GH-04: a deterministic
regenerator script, a manifest enumerating every source-derived asset with a pinned
SHA-256, a CI bitrot gate, and a schema-pin test. This wave lands FIRST — Wave 1's
og-card registers INTO this manifest, and Wave 4's presence suite reads the manifest's
OG hash.

Purpose: Eliminate "lost the original Figma file" bitrot — every committed asset is
byte-identical-reproducible from its source, or explicitly opted out as bespoke.
Output: scripts/regenerate_assets.sh + docs/assets/MANIFEST.yaml + .github/workflows/asset-bitrot.yml + tests/repo/test_asset_manifest_shape.py
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

<!-- Source-of-truth analogs the executor MUST follow, not reinvent: -->
<!-- Bash script precedent (set -euo pipefail, shasum -a 256, repo-root resolution): -->
@scripts/launch/sync_packaging.sh
<!-- Headless-render-to-PNG precedent (Chrome --headless=new --screenshot, repo-relative paths): -->
@docs/assets/screenshots/regen.sh
<!-- SHA-pinned CI workflow template (on: pull_request not pull_request_target, permissions.contents: read, concurrency, timeout-minutes): -->
@.github/workflows/packaging-audit.yml
<!-- Presence/shape-test pattern (REPO_ROOT resolution, parametrize, exact pin asserts): -->
@tests/repo/test_packaging_scaffolds_present.py
<!-- The 2 MB image budget gate that og-card.png + demo-poster.png will consume against (current total ~1.44 MB / ~559 KB headroom): -->
@tests/repo/test_docs_assets.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Seed MANIFEST.yaml + the schema-pin test</name>
  <files>docs/assets/MANIFEST.yaml, tests/repo/test_asset_manifest_shape.py</files>
  <read_first>
    - docs/assets/MANIFEST.yaml (does NOT exist yet — create)
    - tests/repo/test_packaging_scaffolds_present.py (the REPO_ROOT + exact-pin assert pattern to mirror)
    - tests/repo/test_docs_assets.py (the 2 MB budget gate + existing asset inventory)
  </read_first>
  <action>
    Create docs/assets/MANIFEST.yaml with this exact schema (Claude's-Discretion recommendation from
    CONTEXT.md is locked): a top-level `assets:` list of mappings, each with keys `path` (repo-relative,
    e.g. `docs/assets/og-card.png`), `source` (repo-relative source, e.g. `docs/assets/sources/og-card.html`),
    `sha256` (64-hex or the literal `PENDING` for not-yet-generated assets), and `generator` (the
    regenerate_assets.sh step name that produces it, e.g. `og-card`). Plus a top-level `opt_out:` list of
    repo-relative paths for hand-cut bespoke assets that the bitrot gate MUST NOT check.

    Seed `assets:` EMPTY (a literal empty list `assets: []`) — Wave 1 (70P02) appends the og-card entry.
    Seed `opt_out:` with the existing hand-cut assets so the bitrot gate ignores them: `docs/assets/social-card.png`
    (380k hand-cut predecessor, confirmed zero live refs — grep showed only CONTEXT.md mentions it, so it stays
    as a bespoke opt-out per CONTEXT reconciliation option (a), least-destructive), `docs/assets/hero.png`,
    `docs/assets/demo-placeholder.gif`, `docs/assets/readme-hero.png`, `docs/assets/readme-hero.webm`,
    and the existing generated-elsewhere assets `docs/assets/architecture.svg` (regenerated by its own
    scripts/dist/render_architecture.py, not by regenerate_assets.sh) plus all of `docs/assets/screenshots/*.png`
    (regenerated by docs/assets/screenshots/regen.sh) and all of `docs/assets/controllers/*.svg` +
    `docs/assets/dj-software/*.svg`. Add a top-of-file YAML comment explaining: this manifest enumerates only
    assets regenerated by scripts/regenerate_assets.sh; assets with their own generators or hand-cut originals
    are opt_out so the bitrot gate is scoped, not global.

    Create tests/repo/test_asset_manifest_shape.py with SPDX header `# SPDX-License-Identifier: Apache-2.0`,
    `REPO_ROOT = Path(__file__).resolve().parents[2]`, `import yaml`. Tests: (1) MANIFEST.yaml exists and
    yaml.safe_load parses without error; (2) top-level keys are exactly `assets` and `opt_out` (a set-equality
    assert so an extra/typo'd key trips it); (3) `assets` is a list and every entry is a dict with EXACTLY the
    keys {path, source, sha256, generator} — fail loud if any entry is missing a key or has an extra one;
    (4) every `assets[].sha256` is either the literal `PENDING` or a 64-char lowercase hex string
    (`re.fullmatch(r'[0-9a-f]{64}', sha)`); (5) `opt_out` is a list of strings and every opt_out path points
    at a file that exists under REPO_ROOT (catches a stale opt_out entry); (6) no path appears in BOTH `assets`
    and `opt_out` (a path is either source-generated or bespoke, never both).
  </action>
  <verify>
    <automated>source .venv/bin/activate && PYTHONPATH=src python3 -c "import yaml; d=yaml.safe_load(open('docs/assets/MANIFEST.yaml')); assert set(d)=={'assets','opt_out'}, d.keys(); assert d['assets']==[], d['assets']; print('MANIFEST seed OK')" && PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "import yaml; yaml.safe_load(open('docs/assets/MANIFEST.yaml'))"` parses (exit 0).
    - `tests/repo/test_asset_manifest_shape.py` exists, carries the SPDX header, and `pytest tests/repo/test_asset_manifest_shape.py -q` exits 0.
    - MANIFEST `assets:` is the empty list `[]` at this wave (Wave 1 fills it).
    - `docs/assets/social-card.png` appears in `opt_out` (CONTEXT reconciliation (a) — bespoke, not deleted).
    - `grep -c 'sources/og-card' docs/assets/MANIFEST.yaml` returns 0 (Wave 1 adds it, not this wave).
  </acceptance_criteria>
  <done>MANIFEST.yaml seeded with empty assets + opt_out of all current bespoke/foreign-generated images; schema-pin test green.</done>
</task>

<task type="auto">
  <name>Task 2: Write regenerate_assets.sh + the asset-bitrot CI workflow</name>
  <files>scripts/regenerate_assets.sh, .github/workflows/asset-bitrot.yml</files>
  <read_first>
    - scripts/regenerate_assets.sh (does NOT exist yet — create)
    - .github/workflows/asset-bitrot.yml (does NOT exist yet — create)
    - scripts/launch/sync_packaging.sh (bash: set -euo pipefail, shasum -a 256, repo-root resolution)
    - docs/assets/screenshots/regen.sh (headless-Chrome screenshot-to-PNG precedent + the EXIT trap cleanup pattern)
    - .github/workflows/packaging-audit.yml (SHA-pinned actions, on: pull_request, permissions.contents: read, concurrency, timeout-minutes)
  </read_first>
  <action>
    Create scripts/regenerate_assets.sh (bash, NOT Python — matches cut_release.sh / sync_packaging.sh /
    regen.sh precedent; prefer bash per CONTEXT Claude's-Discretion). SPDX header line 2. `set -euo pipefail`.
    Resolve REPO root from the script's own path (mirror sync_packaging.sh's `HERE`/`REPO` pattern). The script
    reads docs/assets/MANIFEST.yaml's `assets:` list and, for each entry, runs its `generator` step to produce
    `path` from `source`, then recomputes the SHA-256 (`shasum -a 256`). At THIS wave the assets list is empty,
    so the script body is a dispatch skeleton with NO generator steps yet — a `case "$generator"` (or a
    per-generator function) dispatcher plus a clear `# Wave 1 (70P02) registers the og-card generator here`
    comment marking the extension point. The script MUST: (a) be a no-op-clean exit 0 when assets list is empty
    (so the bitrot gate is green from this wave forward), (b) accept an optional `--check` style behavior is NOT
    required here — the workflow does the git-diff check. Make the script executable (`chmod +x`). Node/npx
    puppeteer OR headless-Chrome is the render mechanism — pick at Wave 1 when the first real asset registers;
    this wave only lands the dispatcher + the empty-list clean exit. Document at the top: "this regenerates only
    docs/assets/MANIFEST.yaml `assets:` entries; opt_out + foreign-generator assets are out of scope by design."

    Create .github/workflows/asset-bitrot.yml. Lift the security posture VERBATIM from packaging-audit.yml:
    `name: Asset Bitrot`; `on: { push: { branches: [main] }, pull_request: }` (NOT pull_request_target —
    fork-PR-secrets-safe); `concurrency: { group: asset-bitrot-${{ github.ref }}, cancel-in-progress: true }`;
    `permissions: { contents: read }`; one job `asset-bitrot` `runs-on: ubuntu-latest` (the regenerator only needs
    headless Chrome which ubuntu runners have; no macOS/Windows needed), `timeout-minutes: 15`. Steps:
    (1) `actions/checkout` SHA-pinned to the SAME pin used in packaging-audit.yml
    (`34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1`); (2) a step that runs `bash scripts/regenerate_assets.sh`;
    (3) a step that runs `git diff --exit-code docs/assets/` and on non-zero exit prints a clear message
    ("a committed docs/assets/ asset drifted from its regenerated form — re-run scripts/regenerate_assets.sh and
    commit the result, or add the asset to MANIFEST.yaml opt_out if it is hand-cut"). Because the assets list is
    empty this wave, the regenerator is a no-op and the diff is clean → the workflow is green at landing.
    Add a top-of-file comment block (mirroring packaging-audit.yml's) explaining the gate + the lifted posture.
  </action>
  <verify>
    <automated>bash -n scripts/regenerate_assets.sh && test -x scripts/regenerate_assets.sh && bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/ && source .venv/bin/activate && PYTHONPATH=src python3 -c "import yaml; w=yaml.safe_load(open('.github/workflows/asset-bitrot.yml')); assert 'asset-bitrot' in w['jobs']; print('workflow parses + job present')"</automated>
  </verify>
  <acceptance_criteria>
    - `bash -n scripts/regenerate_assets.sh` exits 0 (valid bash syntax).
    - `test -x scripts/regenerate_assets.sh` succeeds (executable bit set).
    - `bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/` exits 0 (no-op clean at empty-assets wave).
    - `grep -c 'set -euo pipefail' scripts/regenerate_assets.sh` returns ≥1.
    - `grep -c 'git diff --exit-code' .github/workflows/asset-bitrot.yml` returns ≥1.
    - `grep -c 'pull_request_target' .github/workflows/asset-bitrot.yml` returns 0 (fork-PR-safe).
    - `grep -c '34e114876b0b11c390a56381ad16ebd13914f8d5' .github/workflows/asset-bitrot.yml` returns ≥1 (SHA-pinned checkout matching packaging-audit.yml).
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/asset-bitrot.yml'))"` parses (exit 0).
  </acceptance_criteria>
  <done>Regenerator dispatcher + bitrot CI gate land green-at-empty-assets; Wave 1's og-card generator slots into the marked extension point.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| fork-PR → CI workflow | Untrusted PR code runs the regenerator in CI; must not leak secrets or run elevated |
| committed asset ↔ source | Drift here is the bitrot the gate exists to catch |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-70P01-01 | Elevation | asset-bitrot.yml on fork PRs | mitigate | `on: pull_request` (NOT pull_request_target) + `permissions: contents: read` — fork PRs get no secrets, read-only token; lifted verbatim from packaging-audit.yml |
| T-70P01-02 | Tampering | committed docs/assets drift | mitigate | `git diff --exit-code docs/assets/` after regenerate fails CI on any unreproducible asset |
| T-70P01-03 | Tampering | MANIFEST.yaml malformed silently | mitigate | test_asset_manifest_shape.py pins exact key set + sha256 format + opt_out path existence |
| T-70P01-SC | Tampering | npx/npm installs in regenerator | accept | This wave installs nothing (empty assets, no-op); Wave 1 introduces the puppeteer/headless render and carries its own legitimacy note. No package-manager installs at this wave. |
</threat_model>

<verification>
Per-wave gate (run from repo root):
```
bash -n scripts/regenerate_assets.sh && test -x scripts/regenerate_assets.sh
bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py -q
git diff --stat HEAD -- src/vibemix/   # MUST be empty — zero reaction-path touch
git diff --stat HEAD -- pyproject.toml uv.lock   # MUST be empty — zero new Python deps
```
</verification>

<success_criteria>
- scripts/regenerate_assets.sh exists, is executable, valid bash, no-op-clean exit 0 at empty-assets wave.
- docs/assets/MANIFEST.yaml seeded (assets: [], opt_out includes social-card.png + foreign-generated assets).
- .github/workflows/asset-bitrot.yml lands with the packaging-audit.yml security posture + git-diff gate.
- tests/repo/test_asset_manifest_shape.py green; MANIFEST schema pinned.
- ZERO src/vibemix/ edits. ZERO pyproject.toml/uv.lock edits.
</success_criteria>

<output>
Create `.planning/phases/70-github-sexified-generated-tested/70P01-SUMMARY.md` when done.
</output>
