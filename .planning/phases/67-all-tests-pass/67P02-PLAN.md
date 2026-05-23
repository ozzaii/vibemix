---
phase: 67-all-tests-pass
plan: 67P02
type: execute
wave: 1
depends_on: [67P01]
files_modified:
  - KAAN-ACTION-LEGAL.md
  - tests/  # selected files only — Tier-B xfail decorators added per triage outcome
autonomous: true
requirements: [TEST-01, TEST-02]
must_haves:
  truths:
    - "Every test in the opt-in marker grid is classified as Tier A / Tier B / Tier C"
    - "Every Tier-B failure has a §V7-LIVE entry with a concrete fix path"
    - "No marker is a graveyard — each Tier-B test carries `xfail(strict=False, reason=…)` + adjacent `# reason:` pointing at §V7-LIVE-NN"
  artifacts:
    - path: KAAN-ACTION-LEGAL.md
      provides: "New `## §V7-LIVE — v7.0 Live-Hardware Discharge Surface` section"
      contains: "§V7-LIVE"
    - path: .planning/phases/67-all-tests-pass/67P02-TRIAGE.md
      provides: "Per-marker Tier-A/B/C triage record"
      contains: "Tier A"
  key_links:
    - from: any Tier-B test in tests/
      to: KAAN-ACTION-LEGAL.md §V7-LIVE-NN
      via: "# reason: comment referencing the §V7-LIVE-NN id"
      pattern: '§V7-LIVE-'
---

<objective>
Wave 1 — Triage the 65 currently-deselected opt-in tests into Tier A (CI-greenable) / Tier B (hardware-required → xfail + §V7-LIVE entry) / Tier C (flaky → defer to Wave 4 quarantine); create the new `## §V7-LIVE` section in `KAAN-ACTION-LEGAL.md` mirroring the existing `§SHIP-V4` / `§RECALL-EAR` pattern; apply `xfail(strict=False)` decorators with adjacent `# reason:` comments to every Tier-B test.

Purpose: TEST-02 says "no marker is a graveyard" — every opt-in test either passes on real hardware or has its failure mode documented in `§V7-LIVE` with a concrete fix path. This wave produces the documented-fix-path artifact (which Wave 3's CI matrix consumes via `xfail(strict=False)`-as-amber rather than red on hosted runners). Default to Tier B over Tier C per CONTEXT D-TRIAGE — "trust the audio (and the real hardware) more than retries."

Output: Per-marker triage record `.planning/phases/67-all-tests-pass/67P02-TRIAGE.md`; new `## §V7-LIVE` section in `KAAN-ACTION-LEGAL.md` with one sub-entry per Tier-B failure-mode cluster (not per individual test — cluster by environmental constraint, e.g. "BlackHole-on-hosted-macOS" gets one entry covering all 5 cases in `test_audio_macos_live.py`); xfail decorators on every Tier-B test pointing at its §V7-LIVE-NN id.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/67-all-tests-pass/67-CONTEXT.md
@.planning/phases/67-all-tests-pass/67-RESEARCH.md
@.planning/phases/67-all-tests-pass/67P01-SUMMARY.md
@KAAN-ACTION-LEGAL.md
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Per-marker triage spike — classify each opt-in test as Tier A/B/C</name>
  <read_first>
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Failure-Mode Triage` — Tier A/B/C definitions + "default to Tier B over Tier C")
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (`## Current State` marker-counts table; Pitfall 1 + 2 — BlackHole reboot + windows-latest≠Win11; Open Question 4 — triage strategy)
    - pyproject.toml (the 8 declared markers + the newly-added `flaky` from Wave 0)
    - CLAUDE.md (canonical test invocation patterns)
  </read_first>
  <action>
    Enumerate every test that the opt-in marker grid catches: run `uv run pytest --collect-only -q -m "<marker>"` for each of the 7 opt-in markers (`macos_audio`, `windows_only`, `integration`, `slow`, `e2e`, `cli`, `network`) on Kaan's Mac. Capture the test ids. For each test, attempt to actually run it (e.g. `uv run pytest -q -m macos_audio` for the `macos_audio` set). Classify each result: Tier A = PASSED → no further work; Tier B = FAILED but explainable by environment (real BlackHole / FLX4 USB / Win 11 desktop SKU / live external API not in CI / fork-PR-no-secret); Tier C = inconsistent across runs (rare — default to Tier B per CONTEXT). Write the triage record to `.planning/phases/67-all-tests-pass/67P02-TRIAGE.md` with a per-marker table — columns: `test_id | observed | tier | fix_path_id (e.g. §V7-LIVE-01) | one-line rationale`. Group Tier-B failures by environmental constraint into clusters (e.g. all "BlackHole kext not loadable on hosted runner" failures share one cluster) — the cluster count determines how many `§V7-LIVE-NN` sub-entries Task 2 will create. `windows_only` tests cannot be run on Kaan's Mac — mark all `windows_only` tests as Tier-B-pending-Win-VM-confirmation in the triage and use RESEARCH.md's Assumption A6 (most are platform-skipif gated and will be Tier-B via §V7-LIVE-02 "Windows 11 desktop SKU" cluster).
  </action>
  <verify>
    <automated>test -f .planning/phases/67-all-tests-pass/67P02-TRIAGE.md && grep -c "Tier A\|Tier B\|Tier C" .planning/phases/67-all-tests-pass/67P02-TRIAGE.md</automated>
  </verify>
  <done>`67P02-TRIAGE.md` exists with one table per marker; every collected opt-in test appears in exactly one row with a tier; Tier-B clusters are enumerated (RESEARCH.md predicts ~2-5 clusters: BlackHole-hosted-mac, win11-desktop-SKU, FLX4-USB, possibly live-external-API, possibly fork-PR-no-secret). The total row count ≥ 65 (the deselected baseline; may be more if collection drifted).</done>
</task>

<task type="auto">
  <name>Task 2: Write §V7-LIVE section + apply xfail decorators to all Tier-B tests</name>
  <read_first>
    - .planning/phases/67-all-tests-pass/67P02-TRIAGE.md (the triage record from Task 1)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (Pattern 3 — `§V7-LIVE` entry template; Code Examples — "Mark a Tier-B failure (xfail with §V7-LIVE pointer)")
    - KAAN-ACTION-LEGAL.md lines 3387-3510 (existing `§SHIP-V4` section as the structural mirror) and lines 3510+ (existing `§RECALL-EAR` for the "sign-off ☐ pending / ☐ done" pattern)
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Reason Tagging` — `# reason:` comment must be within 2 lines above or on the decorator line)
  </read_first>
  <action>
    Append a new `## §V7-LIVE — v7.0 Live-Hardware Discharge Surface` section to `KAAN-ACTION-LEGAL.md` at end-of-file (do NOT insert before existing sections — append-only preserves git-blame of prior sections). Header structure mirrors `§SHIP-V4` (intro paragraph explaining the discharge contract — "engineering side ships xfail(strict=False) with `# reason:` adjacent; this section is the fix-path for the live confirmation"). One sub-entry `### §V7-LIVE-NN — <one-line constraint cluster name>` per Tier-B cluster identified in Task 1's triage. Each sub-entry has 4 fields per RESEARCH.md Pattern 3: **Tests** (list of test ids in the cluster), **Why it can't ship green in CI** (cite specifics — e.g. actions/runner-images#11746 for BlackHole, Server-2022-not-Win11 for windows_only desktop SKU), **Fix path** (the exact one-line Kaan invocation to discharge — e.g. `uv run pytest -m macos_audio` on Kaan's Mac), **Sign-off** (☐ pending · ☐ done — date: ____ · SHA: ____ · result: ____). Then, for every Tier-B test in the triage: open the test file, add `@pytest.mark.xfail(strict=False, reason="<env constraint> — see §V7-LIVE-NN")` adjacent to the existing opt-in marker decorator (place the xfail BELOW the marker so the opt-in filter still selects it for runs), and add a `# reason:` comment within the 2-line window above the xfail line citing the §V7-LIVE-NN cluster id. For module-level pytestmark tests (e.g. `test_audio_macos_live.py`), apply the xfail as a module-level addition to the pytestmark list rather than per-test. DO NOT add xfail to Tier-A tests (they're already passing). DO NOT add xfail to Tier-C candidates (defer to Wave 4 — Tier C is flaky quarantine territory, not Tier B documented-env-blocker territory). After all decorators are added, re-run the full opt-in grid on Kaan's Mac: `for m in macos_audio integration slow e2e cli network; do uv run pytest -q -m "$m"; done` and `uv run pytest -q` for the default suite. Every previously-failing Tier-B test now exits as XFAIL (yellow, not red); every Tier-A test still PASSES; the default suite stays GREEN (Wave 0 invariant held).
  </action>
  <verify>
    <automated>grep -c "^## §V7-LIVE\|^### §V7-LIVE-" KAAN-ACTION-LEGAL.md && for m in macos_audio integration slow e2e cli network; do uv run pytest -q -m "$m" --tb=no 2>&1 | tail -1; done && uv run pytest -q --tb=no 2>&1 | tail -1</automated>
  </verify>
  <done>`KAAN-ACTION-LEGAL.md` has `## §V7-LIVE` header + N `### §V7-LIVE-NN` sub-entries (N matches the cluster count from Task 1). Every Tier-B test carries `@pytest.mark.xfail(strict=False, reason="… §V7-LIVE-NN")` + adjacent `# reason:` comment pointing at the same cluster id. Per-marker pytest runs report xfailed counts ≥ Tier-B counts from triage; no `FAILED` lines in any marker run. Default `pytest -q` still exits 0. Mandatory implements: TEST-02 success criterion ("each Tier-B failure-mode documented in §V7-LIVE"); TEST-01 success criterion #1 ("every existing skip/xfail/xpass carries a one-line `# reason:` adjacent to its marker") for the new xfail decorators.</done>
</task>

</tasks>

<verification>
  - `## §V7-LIVE` section exists in KAAN-ACTION-LEGAL.md with cluster sub-entries
  - Every Tier-B test has xfail decorator + `# reason:` pointer to its §V7-LIVE-NN id
  - `uv run pytest -q` default still GREEN (Wave 0 invariant preserved)
  - Each per-marker run reports 0 FAILED (xfails are amber, not red)
  - `67P02-TRIAGE.md` exists with the per-marker classification table
</verification>

<success_criteria>
- TEST-02 "no marker is a graveyard" satisfied — every opt-in test is either Tier-A green, Tier-B xfailed-with-§V7-LIVE-pointer, or (rare) deferred to Wave 4 Tier-C quarantine.
- §V7-LIVE section is the Kaan-action discharge surface for the 4 soft items P67 TEST-02 carries (Mac + Win VM × per-cluster constraint).
- No test in the default suite changed behavior. No `src/vibemix/` file touched.
</success_criteria>

<output>
Create `.planning/phases/67-all-tests-pass/67P02-SUMMARY.md` when done with: cluster summary table (cluster id → tests covered), the §V7-LIVE section markdown excerpt, and the post-decoration per-marker pytest tail-line outputs.
</output>
