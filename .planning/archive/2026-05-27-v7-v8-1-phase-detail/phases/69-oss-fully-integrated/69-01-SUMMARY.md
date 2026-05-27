---
phase: 69-oss-fully-integrated
plan: 01
wave: 0
subsystem: oss-docs
tags: [oss, presence-test, anti-drift, doc-only, wave-0]
requirements:
  - OSS-01
provides:
  - "Repo root contains the canonical four OSS docs (MAINTAINERS.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md), each non-empty"
  - "CONTRIBUTING.md carries the exact-match Bravoh carveout sentinel 'the Bravoh proxy is closed-source by design'"
  - "README.md links all four OSS docs via a Community section"
  - "tests/repo/test_oss_presence.py pins the contract: deletion, rename, or sentinel rewording fails CI red"
affects:
  - MAINTAINERS.md (NEW)
  - CONTRIBUTING.md (additive section insertion)
  - README.md (Community section added before footer)
  - tests/repo/test_oss_presence.py (NEW)
tech-stack:
  added: []
  patterns:
    - "Repo-presence gate via stdlib (pathlib + pytest.mark.parametrize), mirrors tests/repo/test_oss_hygiene.py shape"
    - "Exact-match grep sentinel for load-bearing prose (rewording fails CI → deliberate review)"
key-files:
  created:
    - MAINTAINERS.md
    - tests/repo/test_oss_presence.py
    - .planning/phases/69-oss-fully-integrated/deferred-items.md
  modified:
    - CONTRIBUTING.md
    - README.md
  deleted: []
decisions:
  - "Carveout section landed in CONTRIBUTING.md between DCO and Contribution Paths (closest to the decision point — contributor reads it before deciding where to file)"
  - "MAINTAINERS.md sentinel appears exactly once (in the Decision Process bullet); a second self-quoting line was removed during Task 1 to honour the grep-count==1 acceptance criterion"
  - "Community section in README added before the existing footer link row — footer kept verbatim as quick-link convenience (Community is the canonical surface)"
  - "Pre-existing test_readme_feature_matrix_sync.py failures (Phase 68 missing from AUTO-GEN block) logged to deferred-items.md per scope boundary — Plan 69-01 is doc-only OSS-01"
metrics:
  duration: ~15 min
  completed_date: 2026-05-24
  files_touched: 5
  insertions: 116
  deletions: 1
  baseline_before: 4145 passed / 26 skipped / 4 xpassed / 2 failed (the 2 failures pre-existing — see deferred-items.md)
  baseline_after: 4150 passed / 26 skipped / 4 xpassed / 2 failed
  baseline_delta: "+5 tests (test_oss_presence.py: 4 parametrize rows + 1 sentinel test); 2 pre-existing feature-matrix failures unchanged"
  task_commit_shas:
    - ca04951 (Task 1: MAINTAINERS.md)
    - fa1dfb4 (Task 2: CONTRIBUTING.md carveout)
    - 224e332 (Task 3: README Community section)
    - 1ae767a (Task 4: test_oss_presence.py)
---

# Phase 69 Plan 01: OSS Docs Presence Baseline Summary

**One-liner:** Shipped the v7.0 OSS-01 repo-presence baseline — MAINTAINERS.md NEW at repo root, CONTRIBUTING.md carries the exact-match Bravoh carveout sentinel in a new "Scope: vibemix vs Bravoh" section, README.md links all four canonical OSS docs via a new "## Community" section, and `tests/repo/test_oss_presence.py` (5 GREEN tests, ≤120 lines) pins the contract so future deletions, renames, or sentinel rewording fail CI red.

## Objective

Wave 0 of Phase 69. Close the OSS-01 requirement: a stranger landing on the repo sees the four canonical OSS files at root (`MAINTAINERS.md` was the only missing one — CONTRIBUTING/CoC/SECURITY already existed from Phases 19/33), the Bravoh privacy/IP carveout is unmistakable up-front in CONTRIBUTING.md so proxy bugs don't waste maintainer cycles, README points contributors at all four, and the contract is anti-drift-pinned by a presence test that runs under the default pytest grid (no opt-in marker).

This plan is **doc-only**: zero `src/vibemix/` edits (cardinal invariant verified — `git diff --stat HEAD~4..HEAD -- src/vibemix/` is empty).

## What Shipped (4 atomic commits)

### Task 1 — `ca04951` — `feat(69-01): MAINTAINERS.md — repo-root maintainer surface for OSS-01`

NEW file `MAINTAINERS.md` at repo root (28 lines, 1374 bytes). Mirrors `SECURITY.md`'s prose register; SPDX-License-Identifier on line 1; zero emojis; no fenced code blocks.

Five required H2 sections in order:

| Section | Content |
| ------- | ------- |
| `## Active Maintainers` | Kaan Özkan (@bravoh-ai) — `kaan@bravoh.tech`; one-line bio "Founder of Bravoh; vibemix is Bravoh's first open-source release." |
| `## How to Reach Us` | 3 bullets: GitHub issues / SECURITY.md for vuln reports / CONTRIBUTING.md for contributor questions |
| `## Decision Process` | 4 bullets: Apache-2.0 + SPDX / lazy consensus / merge bar = 1 maintainer approval + CI green / Bravoh carveout pointer |
| `## Release Cadence` | One-paragraph: `v0.1.0-rcN` per `docs/release-process.md`; `cut_release.sh` pre-flight; `gh release create` is maintainer-action per §SHIP-V4 |
| `## On-Call / Response Time` | One-paragraph: best-effort, 7-day batch triage, SECURITY.md reports prioritized |

The carveout sentinel `the Bravoh proxy is closed-source by design` lives inside the Decision Process bullet (exactly once, per the grep-count==1 acceptance criterion).

### Task 2 — `fa1dfb4` — `docs(69-01): CONTRIBUTING.md — Bravoh carveout sentinel for OSS-01`

Additive insertion only. New `## Scope: vibemix vs Bravoh` H2 section landed between the existing DCO section (line ~21) and `## Contribution Paths` (line ~23). One paragraph; embeds the exact-match sentinel `the Bravoh proxy is closed-source by design`; forward-references `docs/byo-key.md` (Wave 1 OSS-03 deliverable).

Verified zero pre-existing CONTRIBUTING.md content removed or reordered (`git diff CONTRIBUTING.md` showed only `+6` inserted lines, `-0` deleted). `tests/repo/test_oss_hygiene.py::test_hygiene_file_exists[CONTRIBUTING.md]` continues to pass.

### Task 3 — `224e332` — `docs(69-01): README.md — Community section linking 4 OSS docs`

New `## Community` H2 section inserted just before the existing Apache 2.0 footer link row. Four bulleted markdown links, one per OSS doc, each with a one-line "what this is for" caption. MAINTAINERS.md was the only one not previously linked from README (CONTRIBUTING/CoC/SECURITY already had 4/1/2 mentions respectively).

Footer line preserved verbatim as a quick-link convenience (Community is the canonical surface). Hero-hash sentinel (line 9 `sha256=PLACEHOLDER`) untouched; security email line (line 53) untouched. `tests/repo/test_readme_shape.py` continues to pass (44/44 GREEN).

### Task 4 — `1ae767a` — `test(69-01): tests/repo/test_oss_presence.py — 2-test gate for OSS-01`

NEW file `tests/repo/test_oss_presence.py` (71 lines, ≤120 acceptance ✓). Follows the established `tests/repo/` idiom: SPDX header line 1, `from __future__ import annotations`, `REPO_ROOT = Path(__file__).resolve().parent.parent.parent`, module-level constants, no opt-in marker.

Two test functions:

1. **`test_required_oss_files_exist`** — parametrized over `REQUIRED_OSS_FILES = ["MAINTAINERS.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md"]`. Per row, asserts (in order, with executor-pointing messages): file exists at repo root → `stat().st_size >= 200` → filename substring appears in `README.md`. 4 parametrized rows.

2. **`test_contributing_has_bravoh_carveout`** — reads `CONTRIBUTING.md` once, asserts `text.count(_BRAVOH_CARVEOUT_SENTINEL) == 1` where `_BRAVOH_CARVEOUT_SENTINEL = "the Bravoh proxy is closed-source by design"`. Assert message points the executor at the CONTRIBUTING.md "Scope: vibemix vs Bravoh" section (Plan 69-01 Task 2).

Both tests run under the default `uv run pytest -q` grid (no marker). 5/5 GREEN on first run.

## Negative-Control Verification

Per Task 4 acceptance: sentinel-removal must flip the gate red with a helpful assert.

```
$ sed -i 's/the Bravoh proxy is closed-source by design/the Bravoh proxy is REWORDED-by-design/' CONTRIBUTING.md
$ uv run pytest tests/repo/test_oss_presence.py::test_contributing_has_bravoh_carveout -q
FAILED tests/repo/test_oss_presence.py::test_contributing_has_bravoh_carveout
AssertionError: CONTRIBUTING.md must contain the exact-match sentinel
'the Bravoh proxy is closed-source by design' exactly once; found 0.
See CONTRIBUTING.md '## Scope: vibemix vs Bravoh' section (Plan 69-01 Task 2).
$ <restore CONTRIBUTING.md from backup>
$ uv run pytest tests/repo/test_oss_presence.py -q
5 passed in 0.01s
```

Anti-drift confirmed: any cosmetic rewording or accidental deletion of the sentinel flips the gate red with a message that names the load-bearing section and the source plan.

## Acceptance Criteria — All Met

| Criterion | Result |
| --------- | ------ |
| MAINTAINERS.md exists at repo root with 5 required H2 sections | ✓ 1374 bytes / 28 lines |
| MAINTAINERS.md contains carveout sentinel exactly once | ✓ grep -c → 1 |
| MAINTAINERS.md contains `kaan@bravoh.tech` and SPDX line-1 marker | ✓ both present |
| MAINTAINERS.md zero emojis | ✓ verified |
| CONTRIBUTING.md contains `## Scope: vibemix vs Bravoh` exactly once | ✓ |
| CONTRIBUTING.md contains carveout sentinel exactly once | ✓ |
| CONTRIBUTING.md references `docs/byo-key.md` | ✓ |
| CONTRIBUTING.md pre-existing content preserved (additive only) | ✓ diff shows +6/-0 |
| README.md contains `## Community` exactly once | ✓ |
| README.md links all four OSS docs (≥1 occurrence each) | ✓ MAINTAINERS=1, CONTRIBUTING=4, CoC=2, SECURITY=3 |
| README.md footer link row preserved verbatim | ✓ |
| tests/repo/test_oss_presence.py exists, ≤120 lines, no opt-in marker | ✓ 71 lines |
| 5 GREEN tests under default pytest grid | ✓ |
| Cardinal invariant: zero `src/vibemix/{coach,llm,state,memory,recall,decks,grounding}/` edits | ✓ `git diff` empty |
| Zero net-new deps (`pyproject.toml` + `uv.lock` untouched) | ✓ |
| Negative-control: sentinel removal → red with executor-pointing message | ✓ verified manually |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] MAINTAINERS.md initial draft contained the sentinel twice**

- **Found during:** Task 1, immediately after first write
- **Issue:** First MAINTAINERS.md draft repeated the sentinel verbatim — once in the Decision Process bullet, then again in a self-quoting "The exact carveout sentinel reads:" follow-up line. This would have failed the Task 1 acceptance criterion `grep -c "the Bravoh proxy is closed-source by design" MAINTAINERS.md | grep -q "^1$"` (got 2, expected 1).
- **Fix:** Removed the redundant self-quoting line; the sentinel now appears exactly once, inside the Decision Process bullet referencing CONTRIBUTING.md.
- **Files modified:** `MAINTAINERS.md` (intra-task edit before first commit)
- **Commit:** Folded into Task 1 commit `ca04951` (no separate commit needed — caught pre-commit)

### Deferred Issues (Out of Scope per SCOPE BOUNDARY)

**`tests/repo/test_readme_feature_matrix_sync.py` — 2 pre-existing failures**

- The full-suite baseline run surfaced 2 failures in `test_readme_feature_matrix_sync.py`:
  1. `test_readme_feature_matrix_in_sync` — `scripts/launch/sync_feature_matrix.py --check` exits 1.
  2. `test_feature_matrix_includes_all_completed_phases` — Phase 68 missing from README's `<!-- AUTO-GEN: feature-matrix -->` block.
- **Verified pre-existing:** Both failures reproduce on `HEAD~4` (pre-69-01) — this is a Phase 68 wrap-up gap (the AUTO-GEN block was never regenerated when 68P05 closed), not anything caused by 69-01's doc edits.
- **Disposition:** Logged to `.planning/phases/69-oss-fully-integrated/deferred-items.md` per the executor SCOPE BOUNDARY rule (only auto-fix issues caused by current task's changes). OSS-01 is doc-presence; the feature-matrix sync is a separate AUTO-GEN drift orthogonal to the OSS-presence contract.
- **Recommended fix:** `python scripts/launch/sync_feature_matrix.py --write` folded into the next plan that touches README's feature-matrix block (likely Wave 4 §SHIP-V4 wiring or a one-off doc commit).

### Auth Gates

None.

### Architectural Changes (Rule 4)

None.

## Baseline Reconciliation

|                  | Before        | After         | Delta | Explained by |
| ---------------- | ------------- | ------------- | ----- | ------------ |
| `uv run pytest -q` passed | 4145 | 4150 | +5 | test_oss_presence.py: 4 parametrize rows + 1 sentinel test |
| skipped          | 26            | 26            | 0     | unchanged (3 OS-only + 1 G5 baseline placeholder) |
| xpassed          | 4             | 4             | 0     | §V7-LIVE-01 BlackHole (3) + §V7-LIVE-04 sidecar (1) unchanged |
| failed           | 2             | 2             | 0     | pre-existing test_readme_feature_matrix_sync.py drift (Phase 68 AUTO-GEN gap) — deferred per scope boundary |
| `tests/repo/`    | +5 tests on this gate | confirmed via targeted `pytest tests/repo/test_oss_presence.py -q` |
| wall-clock       | ~218s         | 219.52s       | ~1.5s | within sd; test cost is negligible (≤0.01s for the 5 new tests) |

**The new default-suite baseline is `4150 passed / 26 skipped / 4 xpassed / 2 failed`** where the 2 failures are pre-existing Phase 68 feature-matrix drift, NOT 69-01-caused. Future Phase 69 plans (Waves 1-4) target a +5 lift from here as their starting point.

## Known Stubs / Threat Flags

None. All four required OSS docs ship real content; the sentinel is exact-match grep-pinned; no placeholders introduced.

## Threat-model verification

| Threat ID | Disposition | How verified |
| --------- | ----------- | ------------ |
| T-69P01-01 (Information Disclosure: carveout language) | mitigate | `test_contributing_has_bravoh_carveout` greps the exact sentinel string; any rewording flips red (negative-control verified manually). |
| T-69P01-02 (Tampering: MAINTAINERS / README presence) | mitigate | `test_required_oss_files_exist` parametrizes over all 4 files + asserts each is linked from README; deletion or rename flips red. |
| T-69P01-03 (Repudiation: maintainer claim) | accept | MAINTAINERS.md names `@bravoh-ai` / `kaan@bravoh.tech`; future maintainer additions land via PR with git-history audit trail (no in-test signature check needed). |

## Self-Check: PASSED

Verified post-write:

- **Files created exist:**
  - `MAINTAINERS.md` — FOUND (1374 bytes, 28 lines)
  - `tests/repo/test_oss_presence.py` — FOUND (71 lines)
  - `.planning/phases/69-oss-fully-integrated/deferred-items.md` — FOUND
  - `.planning/phases/69-oss-fully-integrated/69-01-SUMMARY.md` — this file
- **Files modified exist:**
  - `CONTRIBUTING.md` — sentinel present (grep -c → 1), Scope section header present, byo-key reference present
  - `README.md` — Community header present, MAINTAINERS.md linked, footer preserved
- **Commits exist:**
  - `ca04951` (Task 1: MAINTAINERS.md) — `git log --oneline -4` confirms
  - `fa1dfb4` (Task 2: CONTRIBUTING.md carveout) — confirmed
  - `224e332` (Task 3: README Community section) — confirmed
  - `1ae767a` (Task 4: test_oss_presence.py) — confirmed
- **Cardinal invariant:** `git diff --stat HEAD~4..HEAD -- src/vibemix/` empty (zero src edits).

## What's Next

OSS-01 CLOSED. Phase 69 Wave 0 SHIPPED.

Waves 1-4 (Plans 69-02 through 69-05) are unblocked and can run in parallel — they have no inter-wave dependencies per the Phase 69 plan decomposition:

- **Wave 1 (Plan 69-02) — OSS-03 BYO-Key doc** — `docs/byo-key.md` + `tests/repo/test_byo_doc_shape.py` + §V7-LIVE-11 cluster.
- **Wave 2 (Plan 69-03) — OSS-02 client-side proxy fallback** — `proxy_client.py` try/except + pill emission + `test_proxy_fallback.py` 4-test parametrize + §V7-PROXY cluster.
- **Wave 3 (Plan 69-04) — OSS-05 packaging scaffolds** — `packaging/homebrew/Formula/vibemix.rb` + `packaging/scoop/vibemix.json` + `packaging-audit.yml` workflow + `test_packaging_scaffolds_present.py`.
- **Wave 4 (Plan 69-05) — OSS-04 §SHIP-V4 wiring** — `cut_release.sh --dry-run v0.1.0-rc1` re-verify + §SHIP-V4 v7.0 sub-section + `test_ship_v4_section_exists.py`.

When all four ship, OSS-01..05 close together and Phase 69 ENGINEERING-COMPLETE flips. Live discharge (real signature + real `gh release create`) rides Kaan's clock via the §SHIP-V4 cluster.

## EXECUTION COMPLETE
