---
phase: 70-github-sexified-generated-tested
plan: 05
wave: 4
subsystem: github-presence-suite
tags: [github, presence, tests, ci-gate, assets, issue-forms, oss, gh-05, wave-4, final]
requirements:
  - GH-05
provides:
  - "tests/repo/test_github_presence.py — the one-stop GH-05 repo-presence suite: 26 checks (16 offline + 10 network-marked) pinning every Wave 0-3 artifact + the 4 P69 OSS files under one CI roof"
  - "test_og_card_present_and_hash_matches — the exact ROADMAP-SC3-named test (og-card.png sha256 == MANIFEST.yaml pin)"
  - "test_readme_badge_urls_resolve_200 — @pytest.mark.network parametrized over the 10 README shields.io badges (deselected from the default offline grid; CI runs with network)"
  - "test_issue_templates_are_valid_github_forms — yaml.safe_load + name/description/body key asserts over every .github/ISSUE_TEMPLATE/*.yml EXCEPT config.yml (validates the REAL GitHub-Forms .yml shape per CONTEXT reconciliation #1, NOT .md about: front-matter)"
requires:
  - "70P01 — docs/assets/MANIFEST.yaml (og-card sha256 pin read for the hash-match assert)"
  - "70P02 — docs/assets/og-card.png (existence + hash)"
  - "70P03 — docs/landing/index.html (Wave 2; not directly re-pinned here — landing has its own lighthouse/anti-backsliding gates)"
  - "70P04 — docs/assets/demo-poster.png + README hero <video> repoint (demo-asset + hero-hash checks)"
  - "69-01 — tests/repo/test_oss_presence.py (the 4-OSS-files presence pattern re-used; intentional overlap)"
affects:
  - tests/repo/test_github_presence.py (NEW)
tech-stack:
  added: []
  patterns:
    - "Dynamic badge-URL extraction: the network test parametrizes over urls parsed from README.md at collection time (_BADGE_SRC_RE) — never hardcoded, so a README badge edit can't silently drift the test out of sync. A separate offline test_at_least_one_badge_url_present (>=5) guards against a vacuous zero-case pass."
    - "PLACEHOLDER-tolerant demo gate (T-70P05-04 accept): if docs/assets/demo.mp4 is absent (autonomous-mode pending capture), the suite asserts the README hero sentinel is still sha256=PLACEHOLDER; once the real .mp4 lands the <=8388608-byte (8MB) cap activates. Mirrors check_readme_hero_hash.py's placeholder logic."
    - "Hero-hash single-source-of-truth re-use: test_readme_hero_hash_matches_sentinel imports check() from scripts/check_readme_hero_hash.py via importlib.util.spec_from_file_location (not a subprocess, not a re-implementation) and asserts exit 0 — the gate logic stays owned by the script."
    - "Vacuous-pass guards on both parametrized tests (badges + issue forms): a separate offline sanity test asserts the parametrize source is non-empty, so a mass-deletion can't make the parametrized test collect zero cases and pass trivially (no false-green)."
    - "config.yml special-cased: _issue_form_yml_files() globs *.yml and excludes config.yml; config.yml gets its own test_issue_forms_config_has_valid_shape asserting blank_issues_enabled|contact_links (the Issue-Forms-config shape, NOT a form)."
key-files:
  created:
    - tests/repo/test_github_presence.py
    - .planning/phases/70-github-sexified-generated-tested/70P05-SUMMARY.md
  modified: []
decisions:
  - "HTTP client = requests (2.32.5, available as a transitive dep of the google-genai/httpx ecosystem). Verified present (python3 -c 'import requests'). Guarded with pytest.importorskip('requests') so a minimal env stays green rather than erroring. httpx was the fallback (also available) but requests' .get(timeout=) is the simplest 200-check API and matches the CONTEXT/plan wording."
  - "Badge URLs parsed from README at test-collection time rather than hardcoded — avoids a second source of truth that could drift."
  - ".yml-not-.md reconciliation honored: the suite validates the ACTUAL GitHub Issue Forms .yml shape (name/description/body via yaml.safe_load), documented in a module docstring + the test docstrings + here. config.yml excluded from Forms validation, validated separately."
metrics:
  tasks_completed: 1
  files_created: 1
  files_modified: 0
  tests_added: 26
  duration_minutes: 9
  completed: 2026-05-24
---

# Phase 70 Plan 05: GH-05 One-Stop GitHub Presence Suite Summary

`tests/repo/test_github_presence.py` — "GitHub sexified, generated, tested" encoded in
code: a single CI gate (26 checks) that pins every Wave 0-3 artifact plus the four P69
OSS files, so asset deletion, hash drift, a broken badge, a malformed issue template, or
a missing OSS file all fail CI under one roof. This is the LAST plan of the FINAL v7.0
pillar.

## What the suite pins (for the verifier to cross-check)

| # | Test | Pins | Network? |
|---|------|------|----------|
| 1 | `test_readme_badge_urls_resolve_200` | all 10 README shields.io badge URLs return HTTP 200 (timeout=5) | yes — `@pytest.mark.network`, deselected from default grid |
| 1b | `test_at_least_one_badge_url_present` | README badge block has >=5 badges (anti-vacuous-pass) | no |
| 2 | `test_demo_poster_present` | `docs/assets/demo-poster.png` exists + >1KB (Wave 3 / 70P04) | no |
| 2b | `test_demo_asset_under_size_cap_or_placeholder` | `demo.mp4` <=8388608 bytes IF present, ELSE README hero sentinel == `sha256=PLACEHOLDER` | no |
| 3 | `test_og_card_present_and_hash_matches` (ROADMAP-SC3 named) | `docs/assets/og-card.png` exists + sha256 == MANIFEST `089a8a91…3728` (Wave 1 / 70P02) | no |
| 4 | `test_readme_hero_hash_matches_sentinel` | `scripts/check_readme_hero_hash.py::check()` returns exit 0 (GH-01 hero integrity) | no |
| 5 | `test_issue_templates_are_valid_github_forms` | every `.github/ISSUE_TEMPLATE/*.yml` (ai_misbehavior, bug_report, feature_request, new_controller) is valid GitHub Forms: yaml-parses + has `name`/`description`/`body` + non-empty `body:` list | no |
| 5b | `test_issue_forms_config_has_valid_shape` | `config.yml` parses + has `blank_issues_enabled`/`contact_links` (excluded from Forms validation) | no |
| 5c | `test_at_least_one_issue_form_present` | >=1 form .yml exists (anti-vacuous-pass) | no |
| 6 | `test_pull_request_template_exists_nonempty` | `.github/pull_request_template.md` exists + >=50 bytes | no |
| 7 | `test_four_oss_files_present_and_linked` | MAINTAINERS/CONTRIBUTING/CODE_OF_CONDUCT/SECURITY .md each exist at root, >=200 bytes, README-linked (intentional overlap with test_oss_presence.py) | no |

26 total parametrized cases: 16 offline-grid + 10 network-grid.

## CRITICAL reconciliation confirmed (.yml not .md)

The ROADMAP SC5 wording assumes the OLD `.github/ISSUE_TEMPLATE/*.md` format with
`---\nname:\nabout:\n---` front-matter. **Reality:** the repo uses GitHub **Issue Forms**
(`.yml`, schema `name:`/`description:`/`body:`). The suite validates the ACTUAL `.yml`
Forms shape via `yaml.safe_load` + key asserts — NOT `about:` front-matter. `config.yml`
is the special Issue-Forms *config* (`blank_issues_enabled`/`contact_links`, no `body:`)
and is EXCLUDED from Forms validation, validated separately for its own shape. Documented
in the module docstring, the per-test docstrings, and the frontmatter `decisions` above.
The test honors reality; the doc is the stale party.

## HTTP client used

`requests` (2.32.5) — confirmed available (transitive via the google-genai/httpx
ecosystem). Guarded with `pytest.importorskip("requests")` so a minimal env skips rather
than errors. `httpx` was the documented fallback (also present); `urllib` the stdlib
last-resort. `requests` won on the simplest `get(url, timeout=5).status_code` API.

## Deviations from Plan

None — plan executed exactly as written. No Rule-1 auto-fixes needed: `requests` was
available (no client substitution), all 5 ISSUE_TEMPLATE .yml files had the expected
Forms shape, config.yml had the expected config shape, and all 10 badge URLs returned 200
(no dead-badge xfail). Two anti-vacuous-pass sanity tests (`test_at_least_one_badge_url_present`,
`test_at_least_one_issue_form_present`) were added beyond the plan's enumerated tests as a
no-false-green hardening — additive, in-scope (Rule 2: correctness of the gate itself).

## Verification

**Default offline grid (the new suite):**
```
PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py -q -m "not network"
→ 16 passed, 10 deselected
```

**Network grid (CI w/ network — badge 200s):**
```
PYTHONPATH=src python3 -m pytest tests/repo/test_github_presence.py -q -m network
→ 10 passed, 16 deselected   (all 10 README badges returned HTTP 200)
```

**ROADMAP-SC3 named test collected:**
```
pytest --collect-only … | grep -c 'test_og_card_present_and_hash_matches' → 1
```

**Full tests/repo/ offline grid (no-regression):**
```
PYTHONPATH=src python3 -m pytest tests/repo/ -q
→ 2 failed, 337 passed
```
The 2 failures are the PRE-EXISTING P68 `test_readme_feature_matrix_sync.py` AUTO-GEN
drift (phases 68, 69 missing from the README feature-matrix block) — documented in
`.planning/phases/69-oss-fully-integrated/deferred-items.md`. NOT introduced by this plan;
the baseline carried them in. Every other test, including all 16 new offline cases,
passes.

**Zero-touch (cardinal invariant):**
```
git diff --stat HEAD -- src/vibemix/          → EMPTY
git diff --stat HEAD -- pyproject.toml uv.lock → EMPTY
```
ZERO `src/vibemix/` edits, ZERO dep changes — only `tests/repo/test_github_presence.py`
was added.

## Self-Check: PASSED

- `tests/repo/test_github_presence.py` — FOUND
- Commit `b73378f` (test) — FOUND in git log

## Phase 70 status

**ENGINEERING-COMPLETE — 5/5 plans shipped, GH-01..GH-05 closed engineering-side.**

| Plan | Req | Wave | Status |
|------|-----|------|--------|
| 70P01 | GH-04 | 0 | SHIPPED — MANIFEST.yaml + regenerate_assets.sh + asset-bitrot.yml |
| 70P02 | GH-03 | 1 | SHIPPED — og-card.png 1200×630, MANIFEST sha-pinned |
| 70P03 | GH-02 | 2 | SHIPPED — docs/landing CDJ-Whisper + lighthouse.yml + §V7-LANDING |
| 70P04 | GH-01 | 3 | SHIPPED — demo-poster.png + §ASSETS-DEMO-CUT + README hero repoint |
| 70P05 | GH-05 | 4 | SHIPPED — this plan; one-stop presence suite |

Remaining v7.0 work is KAAN-ACTION / external clock only: Pages enablement + live-URL
Lighthouse + Kaan-felt aesthetic sign-off (§V7-LANDING), the real demo.mp4 capture
(§ASSETS-DEMO-CUT), and the repo social-preview image. No engineering tasks remain in
Phase 70 — the FINAL v7.0 "Open House" pillar is engineering-complete.

## EXECUTION COMPLETE
