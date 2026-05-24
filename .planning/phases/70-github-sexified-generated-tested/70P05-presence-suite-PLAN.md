---
phase: 70-github-sexified-generated-tested
plan: 05
type: execute
wave: 4
depends_on: [70-01, 70-02, 70-03, 70-04]
files_modified:
  - tests/repo/test_github_presence.py
autonomous: true
requirements: [GH-05]
must_haves:
  truths:
    - "pytest tests/repo/test_github_presence.py exits 0 — the one-stop repo-presence suite is GREEN"
    - "Every README badge URL returns 200 (network-marked, deselected from the default offline grid)"
    - "The demo asset is present + under the <=8MB size cap; the OG image is present + hash matches MANIFEST"
    - "The README hero hash matches the sentinel; every .github/ISSUE_TEMPLATE/*.yml form is valid GitHub-Forms shape; the PR template exists + non-empty; the 4 P69 OSS files exist + README-linked"
  artifacts:
    - path: "tests/repo/test_github_presence.py"
      provides: "The one-stop GH-05 repo-presence suite encoded in code"
      contains: "test_og_card_present_and_hash_matches"
  key_links:
    - from: "tests/repo/test_github_presence.py"
      to: "docs/assets/MANIFEST.yaml"
      via: "og hash read + compare"
      pattern: "MANIFEST"
    - from: "tests/repo/test_github_presence.py"
      to: ".github/ISSUE_TEMPLATE/*.yml"
      via: "yaml.safe_load Forms-shape validation"
      pattern: "ISSUE_TEMPLATE"
---

<objective>
Land GH-05: the one-stop tests/repo/test_github_presence.py suite — "GitHub sexified,
generated, tested" encoded in code. It pins everything Waves 0-3 produced: badge URLs,
demo asset + size cap, OG image + hash, README hero hash, issue templates (real .yml
GitHub-Forms shape), the PR template, and the four P69 OSS files. LAST wave — depends on
all prior plans.

Purpose: A single CI gate that catches asset bitrot, broken badges, missing OSS files,
or hash drift before it ships.
Output: tests/repo/test_github_presence.py (GREEN).
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

<!-- The presence-test pattern this suite mirrors (REPO_ROOT resolution, parametrize, exact-pin asserts, SPDX header): -->
@tests/repo/test_oss_presence.py
@tests/repo/test_packaging_scaffolds_present.py
<!-- The actual ISSUE_TEMPLATE shape — .yml GitHub Forms (name/description/body), NOT .md front-matter (CONTEXT reconciliation #1): -->
@.github/ISSUE_TEMPLATE/bug_report.yml
<!-- config.yml is a SPECIAL GitHub config (blank_issues_enabled + contact_links) — it is NOT an issue form; EXCLUDE it from Forms validation: -->
@.github/ISSUE_TEMPLATE/config.yml
<!-- The hero-hash gate this suite re-asserts (PLACEHOLDER sentinel logic): -->
@scripts/check_readme_hero_hash.py
<!-- The MANIFEST the OG-hash check reads (Wave 1 pinned og-card.png): -->
@docs/assets/MANIFEST.yaml
<!-- The README badge URLs (the 5 shields + the full-test-matrix badge) the network check hits: -->
@README.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write tests/repo/test_github_presence.py (the one-stop GH-05 suite)</name>
  <files>tests/repo/test_github_presence.py</files>
  <read_first>
    - tests/repo/test_github_presence.py (does NOT exist — create)
    - tests/repo/test_oss_presence.py (REQUIRED_OSS_FILES list + README-link assert pattern to re-use)
    - tests/repo/test_packaging_scaffolds_present.py (REPO_ROOT + exact-pin assert idiom)
    - .github/ISSUE_TEMPLATE/bug_report.yml (the real Forms shape: name/description/body keys)
    - .github/ISSUE_TEMPLATE/config.yml (the special config — MUST be excluded from Forms validation)
    - scripts/check_readme_hero_hash.py (re-use its check() or replicate the PLACEHOLDER-aware assert)
    - docs/assets/MANIFEST.yaml (read the og-card sha256 to compare against the committed file's hash)
  </read_first>
  <action>
    Create tests/repo/test_github_presence.py with SPDX header `# SPDX-License-Identifier: Apache-2.0`,
    `from __future__ import annotations`, `REPO_ROOT = Path(__file__).resolve().parents[2]`, `import yaml`,
    `import hashlib`, `import pytest`. Document at the top the CONTEXT reconciliation #1: ISSUE_TEMPLATE is .yml
    GitHub Forms (name/description/body), NOT .md front-matter — this suite validates the real .yml shape, and
    config.yml is excluded (it is the special blank_issues_enabled/contact_links config, not a form).

    Tests (each a clear failure message pointing at the producing wave):

    1. test_readme_badge_urls_resolve_200 — `@pytest.mark.network`, parametrized over the README badge URLs
       (extract https://img.shields.io/... + the actions/workflow badge URLs from README.md, or hardcode the
       list with a comment). `requests.get(url, timeout=5)` returns status 200. Network-marked so the default
       offline `pytest -q` grid DESELECTS it (CONTEXT <decisions> + the Phase 67/68 offline-clean convention);
       CI runs it with network. If `requests` is unavailable, `pytest.importorskip("requests")`.

    2. test_demo_asset_present_or_poster_fallback + test_demo_asset_under_size_cap — the README hero points at
       docs/assets/demo.mp4 (not-yet-present under autonomous mode) with docs/assets/demo-poster.png committed.
       Assert demo-poster.png exists (Wave 3); IF docs/assets/demo.mp4 exists, assert its size <= 8388608 bytes
       (<=8MB cap); if it does not exist yet, assert the README sentinel is sha256=PLACEHOLDER (the documented
       pending-asset exception per ROADMAP P70 depends-on note — the suite TOLERATES the placeholder). Document
       this tolerance.

    3. test_og_card_present_and_hash_matches — docs/assets/og-card.png exists; read its sha256
       (hashlib.sha256 over the bytes); read MANIFEST.yaml's og-card entry sha256; assert they match. This is
       the exact test name the ROADMAP SC3 names (`test_og_card_present_and_hash_matches`).

    4. test_readme_hero_hash_matches_sentinel — invoke scripts/check_readme_hero_hash.py's `check()` (import it
       via importlib from the scripts path, or subprocess it) and assert exit/return code 0. PLACEHOLDER → 0
       (pending), real SHA → must match. Re-asserts the GH-01 hero-hash integrity from the suite.

    5. test_issue_templates_are_valid_github_forms — `@pytest.mark.parametrize` over every
       `.github/ISSUE_TEMPLATE/*.yml` EXCEPT config.yml. For each: yaml.safe_load parses without error; the file
       is non-empty; the loaded dict has `name`, `description`, and `body` keys (the GitHub Issue Forms required
       shape — NOT `.md` front-matter `about:`). config.yml is validated SEPARATELY (or simply excluded): assert
       config.yml exists + parses + has `blank_issues_enabled` OR `contact_links` (its special shape).

    6. test_pull_request_template_exists_nonempty — `.github/pull_request_template.md` exists and is non-empty
       (>= a small min-bytes like 50).

    7. test_four_oss_files_present_and_linked — re-use the REQUIRED_OSS_FILES idea from test_oss_presence.py:
       CONTRIBUTING.md / CODE_OF_CONDUCT.md / SECURITY.md / MAINTAINERS.md each exist at repo root, are
       non-empty, and appear (linked) in README.md. (This deliberately overlaps test_oss_presence.py — GH-05 is
       the one-stop suite per the ROADMAP; cite the overlap in a comment so a future reader knows it is intentional.)

    Make the default-grid behavior offline-clean: only test 1 is `@pytest.mark.network`; everything else runs in
    the default offline `pytest -q` grid and must be GREEN at landing (all Wave 0-3 artifacts now exist).
  </action>
  <verify>
    <automated>source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py -q -m "not network" && PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py --collect-only -q | grep -c 'test_og_card_present_and_hash_matches' && PYTHONPATH=src python3 -c "import ast,sys; t=ast.parse(open('tests/repo/test_github_presence.py').read()); print('parses')"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/repo/test_github_presence.py -q -m "not network"` exits 0 (every non-network test GREEN at landing — all Wave 0-3 artifacts exist).
    - A test named exactly `test_og_card_present_and_hash_matches` is collected (ROADMAP SC3 names it).
    - The badge-URL test carries `@pytest.mark.network` (deselected from the default offline grid).
    - Issue-template validation uses `yaml.safe_load` + asserts `name`/`description`/`body` keys on each `*.yml` EXCEPT config.yml; config.yml validated for its `blank_issues_enabled`/`contact_links` shape.
    - The suite asserts: demo-poster present + (demo.mp4 size<=8388608 OR PLACEHOLDER sentinel); og-card hash matches MANIFEST; hero-hash check exits 0; PR template non-empty; 4 OSS files present + README-linked.
    - File carries the SPDX header and parses (`ast.parse` clean).
  </acceptance_criteria>
  <done>tests/repo/test_github_presence.py lands GREEN on the default offline grid; the one network test is deselected; GH-05 success criterion encoded in code.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| badge URL → external shields.io / GitHub | network call; only in the network-marked test |
| committed assets ↔ presence suite | the suite is the integrity anchor for the whole front-porch |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-70P05-01 | Tampering | OG image / demo asset / OSS file silent deletion or drift | mitigate | the presence suite asserts existence + size cap + hash match + README-link; deletion or drift fails CI |
| T-70P05-02 | Tampering | issue-template Forms shape rot (broken yaml or missing keys) | mitigate | yaml.safe_load + name/description/body key asserts catch a malformed or `.md`-reverted template |
| T-70P05-03 | Denial of service | network badge check hanging CI | mitigate | requests.get timeout=5s + @pytest.mark.network deselected from the default offline grid |
| T-70P05-04 | Tampering | placeholder demo passing as a real shipped film | accept | suite TOLERATES sha256=PLACEHOLDER per the documented ROADMAP autonomous-mode exception; the real-film honesty gate is check_readme_hero_hash.py once the SHA flips (§ASSETS-DEMO-CUT) |
</threat_model>

<verification>
Per-wave gate (run from repo root):
```
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py -q -m "not network"
PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py --collect-only -q | grep test_og_card_present_and_hash_matches
# Full-suite no-regression check (default offline grid):
PYTHONPATH=src python3 -m pytest tests/repo/ -q
git diff --stat HEAD -- src/vibemix/   # MUST be empty
git diff --stat HEAD -- pyproject.toml uv.lock   # MUST be empty
```
</verification>

<success_criteria>
- tests/repo/test_github_presence.py GREEN on the default offline grid (network test deselected).
- Covers: badge 200s (network), demo asset + size cap (or PLACEHOLDER tolerance), OG hash match, hero-hash, .yml Forms validation (config.yml excluded), PR template, 4 OSS files.
- test_og_card_present_and_hash_matches present (ROADMAP SC3 named test).
- ZERO src/vibemix/ edits. ZERO pyproject.toml/uv.lock edits.
</success_criteria>

<output>
Create `.planning/phases/70-github-sexified-generated-tested/70P05-SUMMARY.md` when done.
</output>
