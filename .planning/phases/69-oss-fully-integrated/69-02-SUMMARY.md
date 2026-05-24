---
phase: 69-oss-fully-integrated
plan: 02
wave: 1
subsystem: oss-byo-key
tags: [oss, byo-key, doc-only, anti-drift, wave-1, gemini]
requirements:
  - OSS-03
provides:
  - "docs/byo-key.md documents the BYO Gemini API key path end-to-end across macOS / Windows / Linux"
  - "tests/repo/test_byo_doc_shape.py (10 GREEN under default grid) pins the 6 required sections + 2 env var names + the aistudio.google.com/apikey URL — drift fails CI red"
  - "KAAN-ACTION-LEGAL.md §V7-LIVE-11 cluster routes the live fresh-account walk to Kaan's clock (autonomous-mode soft discharge)"
affects:
  - docs/byo-key.md (NEW)
  - tests/repo/test_byo_doc_shape.py (NEW)
  - KAAN-ACTION-LEGAL.md (additive: §V7-LIVE-11 cluster + tracking-table row + Sign-off line)
tech-stack:
  added: []
  patterns:
    - "Anti-rot doc-shape gate via stdlib (pathlib + pytest.mark.parametrize) — same idiom as tests/repo/test_oss_presence.py (Plan 69-01)"
    - "Exact-count == 1 section-header asserts (catch duplication same as deletion — tighter than >= 1)"
    - "KAAN-ACTION-LEGAL.md §V7-LIVE-NN cluster template (Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off) — mirrors §V7-LIVE-10 (Phase 68 DEV-03)"
key-files:
  created:
    - docs/byo-key.md
    - tests/repo/test_byo_doc_shape.py
    - .planning/phases/69-oss-fully-integrated/69-02-SUMMARY.md
  modified:
    - KAAN-ACTION-LEGAL.md
  deleted: []
decisions:
  - "Recovery / Verify smoke chose the genai.Client build over a hypothetical `--m vibemix --health` flag (the latter does not exist in src/vibemix today — verified by reading session_loop.py and the package __main__) — uses the actual google-genai SDK shape the runtime depends on"
  - "Test idiom mirrors tests/repo/test_oss_presence.py exactly (SPDX header line 1, three-parent REPO_ROOT walk, parametrize per row, no opt-in marker) so the OSS-01 + OSS-03 gates wear the same idiom and one shape-test pattern covers both contributor surfaces"
  - "§V7-LIVE-11 cluster header line lifted verbatim shape from §V7-LIVE-10 to preserve the 11-cluster numerical sequence (67P02..68P05 ran §V7-LIVE-01..10; P69 extends to §V7-LIVE-11)"
  - "The Switch-back section makes the proxy-mode env vars explicit (VIBEMIX_LLM_MODE=proxy + VIBEMIX_PROXY_JWT) rather than relying on the wave-2 OSS-02 plan to document them — Plan 69-02 is self-contained so a self-hoster can round-trip between modes without reading Plan 69-03"
metrics:
  duration: ~12 min
  completed_date: 2026-05-24
  files_touched: 3
  insertions: 297
  deletions: 1
  baseline_before: 4150 passed / 26 skipped / 4 xpassed / 2 failed (Wave 0 baseline at SHA 05c6179)
  baseline_after: 4160 passed / 26 skipped / 4 xpassed / 2 failed (Wave 1 close at SHA a774b4b)
  baseline_delta: "+10 tests (test_byo_doc_shape.py: 1 exists + 6 sections parametrize + 2 env-vars parametrize + 1 URL); 2 pre-existing P68 feature-matrix drift failures unchanged (see deferred-items.md)"
  wall_clock_full_suite: 254.00s
  task_commit_shas:
    - 7541776 (Task 1: docs/byo-key.md)
    - df7e716 (Task 2: tests/repo/test_byo_doc_shape.py)
    - a774b4b (Task 3: KAAN-ACTION-LEGAL.md §V7-LIVE-11)
---

# Phase 69 Plan 02: BYO Gemini API Key Documentation Summary

**One-liner:** Shipped the v7.0 OSS-03 Bring-Your-Own-Key contributor surface — `docs/byo-key.md` (147 lines, 6 required H2 sections, three-platform env-var table) documents the BYO Gemini path that `src/vibemix/runtime/session_loop.py:842` has already honoured; `tests/repo/test_byo_doc_shape.py` (84 lines, 10 GREEN tests under default grid) pins the contract so deletion or rename of any required section flips CI red; `KAAN-ACTION-LEGAL.md §V7-LIVE-11` cluster routes the live fresh-account walk to Kaan's clock under autonomous mode.

## Objective

Wave 1 of Phase 69. Close OSS-03 engineering-side: a self-hoster who does not want their evidence packets to hop through the Bravoh proxy can follow one kebab-case doc to switch vibemix to their own Gemini API key in under 5 minutes. The runtime code path (`VIBEMIX_LLM_MODE=direct` with `GEMINI_API_KEY=<key>`) already exists at `runtime/session_loop.py:842` — this plan documents what the code already does (zero new product capability, on-thesis for v7.0 OSS).

This plan is **doc-only**: zero `src/vibemix/` edits (cardinal invariant verified — `git diff --stat HEAD~3..HEAD -- src/vibemix/` is empty).

## What Shipped (3 atomic commits)

### Task 1 — `7541776` — `feat(69-02): docs/byo-key.md — BYO Gemini API key path for OSS-03`

NEW file `docs/byo-key.md` at the canonical kebab-case path (147 lines, ≤200 acceptance ✓; ≥80 acceptance ✓). SPDX-License-Identifier on line 1; zero emojis; tone mirrors `docs/release-process.md`'s prose register.

Six required H2 sections in order (gated by Task 2 exact-count==1 asserts):

| # | Section | Content |
| - | ------- | ------- |
| 1 | `## Why BYO` | 1 paragraph + 3 bullets covering privacy (direct-to-Google, no Bravoh telemetry hop), cost (your own Gemini quota / billing), control (model selection + raw 429s + one fewer network hop). |
| 2 | `## Get a Gemini API key` | 1 paragraph + 4-step numbered list naming `https://aistudio.google.com/apikey` verbatim + free-tier reminder (≈50 req/day, "rely on AI Studio dashboard, not this doc"). Ends with "Keep this key secret — anyone with it can spend your quota." |
| 3 | `## Set the env vars` | Three-platform table (macOS `~/.zshrc`, Linux `~/.bashrc`, Windows PowerShell session-only + persistent forms) for `VIBEMIX_LLM_MODE=direct` + `GEMINI_API_KEY=...`. Notes that `direct` is the default — explicit-set is clarity, not strictly required. |
| 4 | `## Verify` | Runnable smoke `uv run python -c "from google import genai; ..."` (verified against `src/vibemix/runtime/session_loop.py:859` build path) + fallback `uv run python -m vibemix` real-coach-turn confirmation. |
| 5 | `## Switch back to Bravoh proxy` | Two-shell-block round-trip — `VIBEMIX_LLM_MODE=proxy` + `VIBEMIX_PROXY_JWT=<token>` with Windows `$env:` / `Remove-Item` equivalents. Cross-links to the gate code at `src/vibemix/runtime/session_loop.py:842`. |
| 6 | `## Privacy & Limits` | Two paragraphs (privacy: direct-to-`generativelanguage.googleapis.com`, Google TOS, no Bravoh hop; limits: free-tier 429 path → vibemix's existing OSS-02 "co-host unavailable" emission). Cross-links to `CONTRIBUTING.md` "Scope: vibemix vs Bravoh". |

Trailing `## See also` mini-section linking `CONTRIBUTING.md` / `docs/release-process.md` / `MAINTAINERS.md`.

### Task 2 — `df7e716` — `test(69-02): tests/repo/test_byo_doc_shape.py — shape gate for OSS-03`

NEW file `tests/repo/test_byo_doc_shape.py` (84 lines, ≤120 acceptance ✓). Follows the `tests/repo/test_oss_presence.py` (Plan 69-01) idiom verbatim: SPDX line 1, `from __future__ import annotations`, three-parent `REPO_ROOT` walk, module-level constants, no opt-in marker.

Four test functions, 10 total parametrized rows:

1. **`test_byo_doc_exists`** — asserts `BYO_DOC.exists()` (message names the canonical path + Plan 69-02 Task 1) AND `stat().st_size >= 200 bytes`.

2. **`test_byo_doc_has_required_sections`** — parametrized over the 6 required H2 headers. Per row: `text.count(section) == 1` (exact-once: duplication trips the gate same as deletion). Assert message names the missing/duplicate section + Plan 69-02 Task 1.

3. **`test_byo_doc_names_env_vars`** — parametrized over `["VIBEMIX_LLM_MODE", "GEMINI_API_KEY"]`. Per row: `env_var in text`. Assert message names the runtime gate code at `src/vibemix/runtime/session_loop.py:842`.

4. **`test_byo_doc_names_aistudio_url`** — asserts the literal `https://aistudio.google.com/apikey` substring is present. Assert message tells the executor where contributors mint the key.

10/10 GREEN on first run under default `uv run pytest tests/repo/test_byo_doc_shape.py -q`. Negative-control verified (see next section).

### Task 3 — `a774b4b` — `docs(69-02): KAAN-ACTION-LEGAL.md §V7-LIVE-11 — BYO fresh-account walk cluster`

Additive insertion only into `KAAN-ACTION-LEGAL.md`. New cluster `### §V7-LIVE-11 — BYO fresh-account walk` appended at line 4125 (after §V7-LIVE-10 ends at line 4123, before "### Discharge tracking" at line 4188). Mirrors §V7-LIVE-10's 6-section template verbatim:

- **Tests** — references `tests/repo/test_byo_doc_shape.py` (10 anti-rot rows) + the live fresh-account confirmation.
- **Why it can't ship green in CI alone** — explains the felt-quality discharge gap (no hosted runner is a fresh user account; only a stranger walking the doc verifies it teaches rather than lists).
- **Fix path** — fenced bash block: open `aistudio.google.com/apikey` → `export VIBEMIX_LLM_MODE=direct` + `export GEMINI_API_KEY=...` → run the verify smoke → launch `uv run python -m vibemix` → capture walk to `docs/byo-key-walk.md`.
- **Owner-clock** — Kaan or trusted user (Francis Tural, Francesco) on a fresh macOS / Windows account. Expected wall-clock 5-10 min.
- **Cross-reference** — points at `docs/byo-key.md`, `tests/repo/test_byo_doc_shape.py`, `src/vibemix/runtime/session_loop.py:842`, and the §V7-LIVE-07 P68 DEV-05 contributor-recipe smoke (same felt-quality discharge pattern).
- **Sign-off** — single-line in §V7-LIVE-10's checkbox shape (date / account type / wall-clock / friction-captured Y-N).

Three metadata updates alongside the cluster:

- **Discharge tracking table** — new row `| §V7-LIVE-11 | 10 doc-shape (P69 OSS-03) + 1 live fresh-account walk | Kaan or trusted user — fresh account | ☐ pending |` inserted after §V7-LIVE-10 row.
- **TOTAL line** — bumped from `**11 tests + 1 workflow + 1 recurring + 4 P68 live clusters**` to `**11 tests + 1 workflow + 1 recurring + 4 P68 live clusters + 1 P69 doc-walk cluster**`.
- **Sign-off block** — new line `V7-LIVE-11 BYO fresh-account walk (OSS-03)          on: _________   (date — Kaan or trusted user, account type ____, wall-clock ____ min, friction ____)` inserted after the V7-LIVE-10 line, before `Sign-off by: ____`.

Pre-existing §V7-LIVE-01..§V7-LIVE-10 cluster content byte-unchanged (`git diff` shows only the additive cluster + the 1-line TOTAL replacement, no pre-existing prose touched). Grep proofs:

```
$ grep -c "^### §V7-LIVE-11 — BYO fresh-account walk" KAAN-ACTION-LEGAL.md
1
$ grep -c "^### §V7-LIVE-" KAAN-ACTION-LEGAL.md
11
$ grep -q "1 P69 doc-walk cluster" KAAN-ACTION-LEGAL.md && echo OK
OK
$ grep -q "V7-LIVE-11 BYO fresh-account walk" KAAN-ACTION-LEGAL.md && echo OK
OK
```

## Negative-Control Verification

Per Task 2 acceptance: renaming a required section must flip the gate red with an executor-pointing assert.

```
$ cp docs/byo-key.md /tmp/byo-key.md.backup
$ sed -i '' 's/^## Verify$/## Verification/' docs/byo-key.md
$ uv run pytest tests/repo/test_byo_doc_shape.py -q --tb=line 2>&1 | tail -5
====================================== FAILURES ======================================
E   AssertionError: docs/byo-key.md missing or duplicate required section header:
    '## Verify' (found 0, expected 1). v7.0 OSS-03 requires all 6 sections in order.
    See Plan 69-02 Task 1.
FAILED tests/repo/test_byo_doc_shape.py::test_byo_doc_has_required_sections[## Verify]
1 failed, 9 passed in 0.02s
$ cp /tmp/byo-key.md.backup docs/byo-key.md     # restore
$ uv run pytest tests/repo/test_byo_doc_shape.py -q 2>&1 | tail -1
10 passed in 0.02s
$ git diff --stat docs/byo-key.md
(empty = byte-identical restore — confirmed)
```

Anti-drift confirmed: any rewording or accidental deletion of a required section header trips a parametrize row red with a message that names the section, the source plan, and the corrective action.

## Acceptance Criteria — All Met

| Criterion | Result |
| --------- | ------ |
| `docs/byo-key.md` exists with all 6 required H2 sections | ✓ 147 lines, all 6 sections grep-confirmed |
| `docs/byo-key.md` file length ≥ 80 AND ≤ 200 lines | ✓ 147 lines |
| `docs/byo-key.md` SPDX header on line 1 | ✓ `<!-- SPDX-License-Identifier: Apache-2.0 -->` |
| `https://aistudio.google.com/apikey` named verbatim | ✓ grep -c → 1 |
| `VIBEMIX_LLM_MODE` named ≥ 1 time | ✓ grep -c → 8 |
| `GEMINI_API_KEY` named ≥ 1 time | ✓ grep -c → 12 |
| Cross-link to `CONTRIBUTING.md` (Wave 0 carveout) | ✓ both in Privacy section + See-also |
| Zero emoji characters | ✓ verified via Unicode emoji-range regex scan |
| File path is `docs/byo-key.md` (kebab-case at docs/ root) | ✓ |
| `tests/repo/test_byo_doc_shape.py` exists, ≤120 lines, no opt-in marker | ✓ 84 lines |
| 4 test function definitions + 10 parametrized rows | ✓ all 4 named per `<action>` |
| `uv run pytest tests/repo/test_byo_doc_shape.py -q` exits 0 with 10 passed | ✓ 10/10 GREEN in 0.02s |
| Default-grid baseline + exactly +10 tests | ✓ 4150 → 4160 (+10) |
| Negative-control: section rename → red with executor-pointing message → restore → green | ✓ verified manually |
| `KAAN-ACTION-LEGAL.md` §V7-LIVE-11 cluster grep-count == 1 | ✓ |
| `KAAN-ACTION-LEGAL.md` total §V7-LIVE-NN cluster count == 11 | ✓ (was 10 pre-plan) |
| 6 required subsections present in §V7-LIVE-11 | ✓ Tests / Why / Fix path / Owner-clock / Cross-reference / Sign-off |
| Discharge tracking table has new §V7-LIVE-11 row | ✓ |
| TOTAL line contains suffix `+ 1 P69 doc-walk cluster` | ✓ |
| Sign-off block has new `V7-LIVE-11 BYO fresh-account walk (OSS-03)` line | ✓ |
| Pre-existing §V7-LIVE-01..10 byte-unchanged | ✓ git diff shows only additive insertions |
| §V7-LIVE-11 sits AFTER §V7-LIVE-10 and BEFORE Discharge tracking | ✓ line ordering: 4052 / 4125 / 4188 |
| Cardinal invariant: zero `src/vibemix/` edits | ✓ `git diff --stat HEAD~3..HEAD -- src/vibemix/` empty |
| Zero net-new deps (`pyproject.toml` + `uv.lock` untouched) | ✓ |

## Deviations from Plan

### Auto-fixed Issues

None. All three tasks executed exactly as written in `69-02-PLAN.md`.

### Plan-text vs Code Reconciliation (Rule 1 — documented, not a deviation)

The Plan's `<context>` at line 73 references `runtime/session_loop.py:847` as the `VIBEMIX_LLM_MODE` branch anchor, but the actual gate code lives at **line 842** in the current tree (the `mode = os.environ.get("VIBEMIX_LLM_MODE", "direct")...` line). I verified this by reading lines 820-870 of `src/vibemix/runtime/session_loop.py` before drafting the doc. All artifacts (docs/byo-key.md cross-refs, the §V7-LIVE-11 cluster cross-reference, this SUMMARY) point at **line 842** — matching code, not stale plan text. This is the correct call per Rule 8 of the executor protocol ("the doc must match the code").

Default mode is also correctly documented as `direct` (matching `os.environ.get("VIBEMIX_LLM_MODE", "direct")` at line 842), not `proxy` — the Plan's CONTEXT.md `<decisions>` at line 71 incorrectly claimed proxy was default; the Plan's own `<interfaces>` block at line 69 had the right call ("direct IS the default"), which the doc honours.

### Deferred Issues (Out of Scope per SCOPE BOUNDARY)

**`tests/repo/test_readme_feature_matrix_sync.py` — same 2 pre-existing failures (Phase 68 AUTO-GEN drift)**

- Both failures reproduce on Wave 0 baseline (`05c6179`) and were already documented in `.planning/phases/69-oss-fully-integrated/deferred-items.md` by Plan 69-01.
- Wave 1 is doc-only (OSS-03) and does not touch README's feature-matrix block; the drift remains parked per the deferred-items disposition.
- No change to the recommended fix path (run `python scripts/launch/sync_feature_matrix.py --write` in a follow-up plan that touches the feature-matrix block).

### Auth Gates

None.

### Architectural Changes (Rule 4)

None.

## Baseline Reconciliation

|                  | Wave 0 baseline (SHA 05c6179) | Wave 1 close (SHA a774b4b) | Delta | Explained by |
| ---------------- | ----------------------------- | -------------------------- | ----- | ------------ |
| `uv run pytest -q` passed | 4150 | 4160 | +10 | `test_byo_doc_shape.py`: 1 existence + 6 sections parametrize + 2 env-vars parametrize + 1 URL |
| skipped          | 26   | 26   | 0     | unchanged (3 OS-only + others) |
| xpassed          | 4    | 4    | 0     | §V7-LIVE-01 BlackHole (3) + §V7-LIVE-04 sidecar (1) unchanged |
| failed           | 2    | 2    | 0     | pre-existing Phase 68 feature-matrix drift, deferred per scope boundary |
| `tests/repo/test_byo_doc_shape.py` | (file did not exist) | 10/10 GREEN | +10 | new shape gate |
| wall-clock       | ~220s | 254.00s | ~+34s | within normal variance; the 10 new tests cost ≈0.02s |

**The new default-suite baseline is `4160 passed / 26 skipped / 4 xpassed / 2 failed`** at `a774b4b` — the 2 failures stay pre-existing Phase 68 drift, NOT Wave 1-caused. Waves 2-4 target a +10 lift from here as their starting point.

The executor-prompt's stated expected delta of `+6 → 4156` was a stale estimate; the Plan's own success criterion (`<acceptance_criteria>` line 207) explicitly required `+10 vs Wave 0 baseline`, which is what landed.

## Known Stubs / Threat Flags

None. The doc ships real, runnable content; the test is a positive-and-negative-control-verified anti-drift gate; the §V7-LIVE-11 cluster is a felt-quality discharge handoff with no engineering blocker hidden behind it.

## Threat-model verification

| Threat ID | Disposition | How verified |
| --------- | ----------- | ------------ |
| T-69P02-01 (Information Disclosure: BYO key handling) | mitigate | docs/byo-key.md §"Get a Gemini API key" includes "Keep this key secret — anyone with it can spend your quota." ASVS L1 §6.2 reminder satisfied. |
| T-69P02-02 (Tampering: doc section shape rot) | mitigate | `tests/repo/test_byo_doc_shape.py` pins all 6 section headers exactly-once + 2 env vars + the aistudio URL; rewording or deletion fails CI red (negative-control manually verified). |
| T-69P02-03 (Tampering: §V7-LIVE-11 cluster) | mitigate | §V7-LIVE-11 follows the §V7-LIVE-10 6-section template verbatim; pre-existing §V7-LIVE-01..10 are byte-unchanged (git diff confirms). Adding a §V7-LIVE-NN cluster pin to `tests/repo/test_kaan_action_v4_surface.py` was OUT of scope per the threat model (no existing test pins §V7-LIVE clusters; Phase 67/68 precedent did not add one). |
| T-69P02-SC (Supply Chain: package installs) | accept | Plan 69-02 ships zero new package-install tasks. No package legitimacy gate required. |

## Self-Check: PASSED

Verified post-write:

- **Files created exist:**
  - `docs/byo-key.md` — FOUND (147 lines, all 6 sections + 2 env vars + aistudio URL grep-confirmed)
  - `tests/repo/test_byo_doc_shape.py` — FOUND (84 lines, 10/10 GREEN under default grid)
  - `.planning/phases/69-oss-fully-integrated/69-02-SUMMARY.md` — this file
- **Files modified exist + integrity:**
  - `KAAN-ACTION-LEGAL.md` — §V7-LIVE-11 cluster present (grep-count 1), 11 total §V7-LIVE-NN headers, TOTAL line contains "1 P69 doc-walk cluster", Sign-off block contains "V7-LIVE-11 BYO fresh-account walk"
- **Commits exist:**
  - `7541776` (Task 1: docs/byo-key.md) — confirmed via `git log --oneline -3`
  - `df7e716` (Task 2: tests/repo/test_byo_doc_shape.py) — confirmed
  - `a774b4b` (Task 3: KAAN-ACTION-LEGAL.md §V7-LIVE-11) — confirmed
- **Cardinal invariant:** `git diff --stat HEAD~3..HEAD -- src/vibemix/` empty (zero src edits).

## What's Next

OSS-03 CLOSED engineering-side. Phase 69 Wave 1 SHIPPED.

Live discharge (the actual fresh-account walk on a clean Mac / Win account, with `docs/byo-key-walk.md` capture of timestamps + friction points) rides Kaan's clock via `KAAN-ACTION-LEGAL.md §V7-LIVE-11`.

Wave 1 was independent of Waves 0 / 2 / 3 / 4 — execution order across Phase 69 is parallelizable. Remaining unblocked waves:

- **Wave 2 (Plan 69-03) — OSS-02 client-side proxy fallback** — `proxy_client.py` try/except + pill emission + `test_proxy_fallback.py` 4-test parametrize + §V7-PROXY cluster.
- **Wave 3 (Plan 69-04) — OSS-05 packaging scaffolds** — `packaging/homebrew/Formula/vibemix.rb` + `packaging/scoop/vibemix.json` + `packaging-audit.yml` workflow + `test_packaging_scaffolds_present.py`.
- **Wave 4 (Plan 69-05) — OSS-04 §SHIP-V4 wiring** — `cut_release.sh --dry-run v0.1.0-rc1` re-verify + §SHIP-V4 v7.0 sub-section + `test_ship_v4_section_exists.py`.

When all five waves ship, OSS-01..05 close together and Phase 69 ENGINEERING-COMPLETE flips. Live discharge (real signature + real `gh release create`) rides Kaan's clock via §SHIP-V4.

## EXECUTION COMPLETE
