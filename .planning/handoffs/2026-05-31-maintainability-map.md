# Maintainability Map - 2026-05-31

Purpose: make the current cleanup goal executable without disturbing the active
coding sessions. This is a planning artifact only. Do not use it as permission to
refactor product code while concurrent feature lanes are still moving.

## Current State Index

Current refresh, 2026-05-31:

- Dirty tree: `git diff --shortstat` reports 96 tracked files changed, 5117
  insertions, and 1756 deletions; `git ls-files --others --exclude-standard |
  wc -l` reports 91 untracked paths.
- Package coverage: `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passes with 187 dirty paths listed and assigned; 3 generated launch previews
  are intentionally ignored. The checker now includes staged, unstaged, and
  untracked paths so a partially staged tree cannot produce a false green.
- Newest CLAP eval drift: the Real CLAP Retrieval Eval Gate is now 6 dirty paths,
  including README, manifest, vectors, evaluator, synthetic metric tests, and
  real-fixture regression test. `uv run pytest -q tests/library/test_clap_retrieval_eval.py tests/library/test_clap_real_retrieval.py`
  passes 8 tests. It proves real-embedding anisotropy collapse and a no-regression
  retrieval floor, but still does not instantiate ONNX in CI.
- Fresh drift evidence: `src/vibemix/state/drop_predict.py`,
  `tests/state/test_drop_predict.py`, and `src/vibemix/state/refresh.py` are now
  classified under the Mix Timing Oracle hold lane. `refresh.py` drift grew
  again inside the already-assigned path to 64 insertions, adding opt-in
  `VIBEMIX_DROP_DEBUG` countdown logging. The pure helper proof is green:
  `uv run pytest -q tests/state/test_drop_predict.py` reports 9 passed. The
  current integration proof is mixed:
  `uv run pytest -q tests/state/test_refresh.py -k predicted_drop` passes 1
  test, while focused Ruff on `refresh.py` fails on import sorting.
- Local MOSS TTS drift state changed: the wrapper/runtime/test files are no
  longer dirty in the live tree, but `uv.lock` still carries the `sentencepiece`
  / `tts-local` lockfile diff without a matching current `pyproject.toml` diff.
  Keep that lockfile hunk in the Local MOSS hold lane until its owner either
  restores the manifest/runtime slice or removes the residual lock change.
- First staging action when sessions pause: Package 0 only. Do not stage product
  source, dependency files, local MOSS TTS, IPC, launch collateral, or hold lanes
  with the planning ledger.
- Completion state: not complete. The codebase is mapped and package-covered,
  but not landed, refactored, dependency-modernized, or live-proof-complete.

All older count snapshots below are historical evidence, not the live state.
When a future refresh changes the tree, update this index first.

## Interruption Resume Card

Use this when a maintainer or agent returns mid-sweep and needs the shortest
truthful answer before doing anything else.

```text
Current lane: planning/evidence only; no product code edits while other sessions code.
Live tree: 96 tracked files changed, 5117 insertions, 1756 deletions, 91 untracked.
Package checker: green, 187 dirty paths assigned; staged/unstaged/untracked included; 3 generated launch previews ignored.
First safe staging move: Package 0 only, when sessions pause.
Do not stage: src/, tauri/, uv.lock, launch/design assets, local MOSS residual lockfile, or hold lanes with Package 0.
Main active holds: Mix Timing Oracle has refresh.py Ruff red + no live/audio proof; CLAP eval is offline/no-ONNX; Local MOSS is residual uv.lock only; Deck Audio needs live controller/audio proof.
```

Resume commands:

```bash
git status --short
git diff --shortstat
git ls-files --others --exclude-standard | wc -l
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
```

If those commands disagree with this card, trust the commands and update this
card, the Current State Index, and the Package 0 evidence bundle before making
any staging or refactor decision.

## Current Action Queue

Use this queue while other sessions are still coding. It keeps the cleanup goal
moving without pretending the tree is ready to stage.

| Moment | Action | Evidence | Stop condition |
|---|---|---|---|
| While sessions are active | Keep this as planning/evidence work only; refresh and classify drift when the package checker goes red. | `git status --short`, shortstat, untracked count, package checker, and focused inspection of new paths. | A new path is unclassified, or a package owner needs product-code edits. |
| First staging window | Stage Package 0 only: planning inventory, checklist, maintainability map, checker, and checker tests. | Package 0 Stage packet, checker tests, focused Ruff, cached diff check, and package checker before/after staging. | Any product source, dependency manifest, generated artifact, local MOSS TTS file, launch asset, or hold lane appears in the cached diff. |
| After Package 0 lands | Refresh the package checklist and current index because all dirty counts will change. | Package checker summary, current shortstat/untracked count, and updated shared-path list. | A staged commit changed shared-file hunk ownership without updating the checklist. |
| Before product packages | Pick one staging card and prove that lane only. | Staging Cards section plus the package-specific evidence bundle. | Evidence for one lane is being used to claim another lane is ready. |
| Before dependency/refactor work | Confirm all active feature packages are landed or explicitly deferred. | Dependency Modernization Rings and Structural Refactor DoD. | Dependency churn or structural movement appears in the same staged diff as feature work. |

Immediate next safe action remains Package 0 when sessions pause. Everything
else is queueing, not permission to stage.

## No-Drift Continuation Rule

Use this rule when the cleanup session resumes while other agents are still
coding. If the resume commands match the Interruption Resume Card and the strict
package checker stays green, do not keep expanding the planning docs. Report the
stable state, keep Package 0 as the next action, and wait for either a staging
window or real drift.

Update the docs only when a count changes, the checker fails, a hunk materially
changes inside a risky shared path, the user opens a coding lane, or evidence
must be refreshed immediately before staging. This keeps the plan maintainable
instead of becoming another moving part.

## Findings Evidence Ledger

This is the working "jot findings, then gather evidence" register. Each finding
must point to proof, a decision, and the next missing evidence.

| Finding | Current evidence | Decision | Missing proof |
|---|---|---|---|
| The tree is messy but fully classified. | `git diff --shortstat` is 96 files / 5117 insertions / 1756 deletions, untracked count is 91, and strict package checker lists 187 dirty paths assigned; Singularity research and CLAP eval fixtures are classified as hold lanes. | Keep planning ledger as Package 0 and keep research/eval hold lanes out of first staging unless explicitly selected. | Re-run the same checks immediately before any staging window. |
| Package 0 is the only first move that reduces confusion without touching product behavior. | Package 0 contains only three planning docs, the dirty-tree checker, and checker tests; checker tests and focused Ruff are green. | Stage Package 0 first when sessions pause. | Cached diff must contain exactly the five Package 0 acceptance-list paths. |
| Shared files are the main risk, not ordinary file count. | Checker reports shared assignments for `AGENTS.md`, `__main__.py`, `session_loop.py`, IPC schema/generated files, and IPC count/parity tests. | Stage shared paths by hunk or as an explicitly combined package. | `git diff --cached -- <path>` evidence for every shared path in a staged commit. |
| IPC work should default to one contract review. | Packages 2 and 3 share schema, generated TS, generated validator, Python wrappers, Rust/UI consumers, and count/parity tests. | Combine Package 2 and Package 3 unless a deliberate split keeps full schema/codegen proof with each side. | Fresh `check_ipc_schema.py`, IPC wiring checker, UI `check:ipc`, focused tests, and build. |
| Cue, pill, library live-read, and Viber changes are one product pipeline. | Packages 4, 5, and 6 preserve cue source, semantic hot-cue slot, compact pill detail, library context, and Viber/export behavior across layers. | Review/prove them end to end rather than as isolated rendering or ingest edits. | Live DDJ/Viber proof with source/slot/CARE evidence visible from ingest to export/live read. |
| Drop prediction work belongs to the mix-timing hold. | `drop_predict.py` has green unit proof and `refresh.py -k predicted_drop` stays green. `refresh.py` now also adds opt-in `VIBEMIX_DROP_DEBUG` logging, but focused Ruff currently fails on import sorting and there is no live co-host/drop-call proof. | Keep it with Mix Timing Oracle until lint, live/audio, and speech grounding proof exist. | Prove production integration, grounded live timing, and no overclaim before promoting. |
| Local MOSS TTS is now a residual dependency hold, not a current wrapper package. | Only `uv.lock` remains dirty from that slice, adding `sentencepiece` and `tts-local`; the wrapper/runtime/test files are no longer dirty. | Keep the lockfile hunk in Hold and do not stage it with dependency modernization or TTS shutdown. | Either restore the full local-TTS package with proof, or remove/regenerate the residual lockfile diff. |
| Dependency modernization is a future optimization lane, not cleanup glue. | Fresh 12:29 audit: Python has 50 outdated packages and one known SQLCipher omission; npm production audit is clean, dev audit has 6 findings, and `npm explain tmp` traces the high `tmp` finding to `@gltf-transform/cli`; Cargo dry-run has 47 compatible updates. | Run dependency-only rings after active feature packages land or are deferred. | Ring-specific tests/build/live proof at the time of each dependency package. |
| Structural refactors should start from settled or clean targets. | Dirty distribution touches runtime, IPC, pill, library, Learn, settings, audio, memory, and `__main__.py`; clean large candidates include `codex_curate.py` and `dj_cohost.py`. | Land coherent product packages first, then refactor clean or freshly settled subsystems. | Refactor entry criteria: green package checker, owning package settled, focused behavior tests, and preserved public contracts. |

## Live-App Reality Risk Ledger

Evidence refresh, 2026-05-31. These findings steer package order; they do not
open a coding lane while active sessions are still editing the tree.

| Risk | Current evidence | Planning decision | Missing proof |
|---|---|---|---|
| Drop-speaking work is demo/CLI, not live app speech. | `scripts/automix_demo_smoke.py` is the production-looking caller of `build_automix_reel` and `narrate_reel`; current source search finds `runtime/automix_demo.py`, `runtime/drop_reaction.py`, and `state/transition_clock.py` used by scripts/tests, while live refresh only writes/logs drop prediction state. | Keep this in the Mix Timing Oracle / F3 live drop-confirm hold lane. Do not claim shipped live co-host drop speech. | A live caller that fuses offline prediction with live audio authority, gates speech through evidence, and leaves websocket/log/events proof. |
| Vibe Judge persists and credits, but does not directly voice the verdict. | `runtime/coach.py:783` calls `_run_live_judge(...)` and discards the return value; `_run_live_judge` calls `judge_and_record(...)` and `_credit_judged_transition(...)`. | Treat this as live-judge credit plumbing, not voiced verdict UX. | Cited `[judge:]` verdict is routed into the reaction/prompt path, with focused tests and live cited co-host proof. |
| Beatmatching is creditable but lacks a live event producer. | `learn/skill_recognizer.py` accepts `BEATMATCH_GRADED`, and `learn/beatmatch_judge.py` defines `grade_to_event_extra`; current source search finds tests synthesizing the event but no production emitter. | Keep Learn Beatmatch Producer as a real blocker for any "6/6 Mastered" claim. | Live practice loop emits cited `BEATMATCH_GRADED` from owned-deck judge evidence, then the Earned Wall shows mastered proof. |
| Real CLAP/CUE model regressions can still ship green. | `rg "InferenceSession" tests` returns no hits. A dirty offline CLAP retrieval gate now exists (`scripts/eval/clap_retrieval.py`, real fixture, README, and two tests), and focused proof passes 8 tests, but it loads committed embeddings rather than instantiating ONNX. | Treat the CLAP eval gate as a separate hold lane and add it before public semantic/cue claims or dependency upgrades that may affect inference. | Decide whether the offline no-regression fixture is enough for ranking claims; still add or explicitly defer fresh text/audio embedding, section/cue ranking, CUE timing, and slow/local ONNX proof. |
| Section semantic scoring lacks anisotropy centering. | Whole-track search uses `store.search_centered`; section-vector paths in `section_vectors.py`, `toolset.py`, and `ingest.py` do not call centering, and `transition_scorer._semantic_score` raw-normalizes/dot-products vectors. | Split section-vector centering and eval into the semantic package, not the pill UI package. | Section centroid or equivalent calibrated score scale plus section-level real-CLAP eval proving useful separation. |
| Current pill source is not reflected in the tracked bundle. | Pill source/test/CSS files are dirty; `git diff --name-only -- tauri/ui/src/pill tauri/ui/dist` lists only source files and no `tauri/ui/dist` output. | Rebuild and prove the bundle before claiming the latest pill is in the app; backend rewiring is not the first action. | UI build, focused pill tests/Playwright proof, and source-to-bundle/Tauri evidence. |
| The flywheel is bounded, not runaway. | Singularity notes already frame closed loops for taste and mastery-credit, open loops for cue-agreement and judge-calibration, F2+F3 as the cue-detection boost, and F4 as Gemini Flash advisory Viber help. | Sequence one open loop at a time and keep launch language bounded. | Instrument cue-agreement first, then judge calibration; cap deltas over a deterministic floor and require proof after each cycle. |

## Post-Package-0 Rebaseline Protocol

Package 0 changes the bookkeeping surface: the ledger files and checker become
tracked, so the dirty-path counts and the package-checker totals will change
immediately after the commit. Treat that as expected drift, not a reason to rush
into product staging.

Run this sequence after Package 0 lands and before touching any product package:

1. Refresh the tree with `git status --short`, `git diff --shortstat`, and
   `git ls-files --others --exclude-standard | wc -l`.
2. Run `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`.
   Expected result: the checker remains green, but the Package 0 paths no longer
   appear as untracked Include paths.
3. Update this `Current State Index`, the package checklist counts, and the
   shared dirty-path list if the checker summary changed.
4. If updating the ledger creates a small docs-only diff, keep it as a rebaseline
   note. Do not attach product source, dependency manifests, generated IPC
   artifacts, launch assets, or hold-lane files to that rebaseline.
5. Only after the rebaseline is green should the next staging card be selected.

Post-Package-0 acceptance rule: the first post-ledger change should explain the
new counts. It should not advance product behavior.

## Evidence Timeline

Commands run on the live worktree during the planning sweep:

- `git diff --shortstat`: 89 tracked files changed, 4892 insertions, 1748 deletions.
- `git diff --name-only | wc -l`: 89 tracked dirty paths.
- `git ls-files --others --exclude-standard | wc -l`: 72 untracked paths before
  this map was added.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  green after checklist updates; 162 dirty paths listed and assigned.
- `uv pip check`: one incompatibility, `pyrekordbox` asks for `sqlcipher3-wheels`.
  This is intentionally documented in `pyproject.toml` via the never-real-platform
  override, so do not "fix" it by adding SQLCipher without reopening the bundle
  size and Rekordbox XML-only decision.
- `npm --prefix tauri/ui audit --omit=dev --json`: production audit clean.
- `npm --prefix tauri/ui audit --json`: dev audit has 6 findings, mainly
  Vitest's nested Vite/esbuild plus `tmp` through `@gltf-transform/cli`.
- `npm --prefix tauri/ui outdated`: upgrade lanes are Vitest 2.1.9 -> 4.1.7,
  Vite 6.4.2 -> 8.0.14, Three 0.170.0 -> 0.184.0, TypeScript 5.9.3 -> 6.0.3,
  `@types/three` 0.170.0 -> 0.184.1, and `vite-plugin-static-copy` 2.3.2 -> 4.1.0.
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run`: 47
  compatible Rust package updates available, including Tauri 2.11.1 -> 2.11.2.

## Evidence Freshness Ledger

Use this table to avoid overclaiming from older checks. A stale check can still
guide sequencing, but it cannot prove a package is ready to land.

| Evidence class | Current freshness | How to refresh before claim |
|---|---|---|
| Dirty-tree shape | Fresh as of the `Current State Index`; refresh whenever another session changes paths. | `git status --short`, `git diff --shortstat`, untracked count. |
| Package assignment coverage | Fresh as of the latest green strict checker run. | `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`. |
| Package 0 checker tests | Fresh only when `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py` has been rerun after checker edits. | Run the checker tests and focused Ruff before staging Package 0. |
| Dependency versions and audits | Fresh as of the 2026-05-31 12:29 dependency execution audit; useful for ring planning, not landing proof. | `uv pip check`, `uv pip list --outdated --format=json`, npm audit/outdated/ls, `npm explain tmp`, Cargo dry-run, and `cargo tree -d`. |
| Live runtime proof | Partial and historical unless paired with fresh UI log, websocket, and session-event evidence from the current source tree. | Use `VIBEMIX_DEV_SIDECAR=1`, attach as client to `127.0.0.1:8765`, drive the relevant control, then read `ui.log` and session `events.jsonl`. |
| UI visual proof | Historical unless the exact production UI files and assets in the package were rendered after the latest changes. | Run the package's UI test/build path plus screenshots or Playwright/canvas checks for visible behavior. |
| Hold-lane proof | Missing by default. A hold lane is not ready because it is documented. | Collect the hold's promotion evidence first, then update the checklist before staging. |

Latest refresh, 2026-05-31 10:51 +03:

- `git diff --shortstat`: still 89 tracked files changed, 4892 insertions,
  1748 deletions.
- `git diff --name-only | wc -l`: still 89 tracked dirty paths.
- `git ls-files --others --exclude-standard | wc -l`: 73 untracked paths with
  the current planning files present.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  still green; all 162 dirty paths are assigned to Include/Hold lanes.
- `uv pip check`: still only the expected `pyrekordbox` / `sqlcipher3-wheels`
  incompatibility.
- `npm --prefix tauri/ui audit --omit=dev --json`: production audit still clean.
- `npm --prefix tauri/ui audit --json`: dev audit still reports 6 findings
  around Vitest's nested Vite/esbuild path and `tmp`.
- `npm --prefix tauri/ui outdated`: current Node upgrade lanes unchanged.
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run`: still 47
  compatible Rust updates.

Supplemental refresh, 2026-05-31 10:53 +03:

- `git diff --shortstat`: now 93 tracked files changed, 4894 insertions,
  1752 deletions after a parallel IPC/UI-bus test hygiene update.
- `git diff --name-only | wc -l`: now 93 tracked dirty paths.
- `git ls-files --others --exclude-standard | wc -l`: still 73 untracked paths.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  green again after the package checklist classified the four new IPC/UI-bus test
  files; at that point 166 dirty paths were assigned to Include/Hold lanes.
- `uv pip list --outdated`: 50 Python wheels are behind the latest registry
  versions. Highest-risk upgrade groups are AI/runtime SDKs (`google-genai`,
  `openai`, LiveKit packages, `mcp`), telemetry (`opentelemetry-*`), binary/audio
  or model-adjacent packages (`numpy`, `tokenizers`, PyObjC), and major-version
  boundary packages (`protobuf` 6 -> 7, `websockets` 15 -> 16).
- `npm --prefix tauri/ui ls --depth=0`: top-level UI dependency graph resolves
  without npm peer/missing errors.
- `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d`: duplicate versions
  are present in the Tauri tree. Most are transitive, but `core-graphics` remains
  worth special attention because the app has a direct `core-graphics` 0.24 edge
  while Tauri/Tao pull 0.25.

Latest refresh, 2026-05-31 11:01 +03:

- `git diff --shortstat`: still 93 tracked files changed, 4894 insertions,
  1752 deletions.
- `git diff --name-only | wc -l`: still 93 tracked dirty paths.
- `git ls-files --others --exclude-standard | wc -l`: now 74 untracked paths
  after `.planning/LEARN-MOAT-PLAN.md` appeared from a parallel Learn planning
  pass.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  initially caught the new unassigned file. After adding the Learn beatmatch
  producer hold lane, the re-run passed with 167 dirty paths exactly listed,
  3 generated launch previews ignored, and every dirty path assigned.

Dependency refresh, 2026-05-31 11:05 +03:

- `uv pip check`: still one incompatibility: `pyrekordbox` requires
  `sqlcipher3-wheels`, which is intentionally excluded by the `pyproject.toml`
  override because the product uses XML/ANLZ paths and keeps the SQLCipher DB6
  path dormant.
- `uv pip list --outdated --format=json`: still 50 outdated Python packages.
  The risky groups remain AI/runtime SDKs, LiveKit, telemetry, PyObjC,
  `tokenizers`, `protobuf`, and `websockets`.
- `npm --prefix tauri/ui audit --omit=dev --json`: production audit clean
  with 0 findings.
- `npm --prefix tauri/ui audit --json`: dev audit still has 6 findings:
  5 moderate findings through Vitest's nested Vite/esbuild stack and 1 high
  `tmp` finding.
- `npm --prefix tauri/ui outdated --json`: direct upgrade lanes are still
  Vitest 2.1.9 -> 4.1.7, Vite 6.4.2 -> 8.0.14, Three 0.170.0 -> 0.184.0,
  TypeScript 5.9.3 -> 6.0.3, `@types/three` 0.170.0 -> 0.184.1, and
  `vite-plugin-static-copy` 2.3.2 -> 4.1.0.
- `npm --prefix tauri/ui ls --depth=0`: top-level UI dependencies resolve.
  Installed direct versions include `@gltf-transform/cli` 4.3.0,
  `@gltf-transform/core` 4.3.0, `gltf-pipeline` 4.3.1, Playwright 1.60.0,
  Three 0.170.0, Vite 6.4.2, and Vitest 2.1.9.
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run`: still
  47 compatible Rust updates available. Tauri can move 2.11.1 -> 2.11.2
  without changing `Cargo.toml` constraints, but keep it as a lockfile/package
  refresh with Rust gates.
- `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d`: duplicate Rust
  packages remain. The only direct duplicate worth planning around is
  `core-graphics`: the app pins 0.24 for the djay AX bridge while Tauri/Tao
  pulls 0.25.

Dependency refresh, 2026-05-31 11:19 +03:

- `uv pip check`: still one incompatibility, the expected `pyrekordbox` ->
  missing `sqlcipher3-wheels` edge. `pyproject.toml` and `uv.lock` both show
  the never-real-platform override; keep this as an explicit repo exception,
  not as an accidental broken environment.
- `uv pip list --outdated --format=json`: still 50 outdated Python packages.
  The current latest registry values include `google-genai` 2.7.0, `openai`
  2.38.0, LiveKit packages 1.5.15 / protocol 1.1.11, `mcp` 1.27.2,
  telemetry 1.42.1, `numpy` 2.4.6, `tokenizers` 0.23.1, PyObjC 12.2,
  `protobuf` 7.35.0, and `websockets` 16.0.
- `npm --prefix tauri/ui audit --omit=dev --json`: production audit remains
  clean with 0 findings.
- `npm --prefix tauri/ui audit --json`: dev audit still has 6 findings:
  Vitest/Vite/esbuild moderate findings plus one high `tmp` finding.
- `npm --prefix tauri/ui outdated --json`: direct major upgrade lanes remain
  Vitest 2.1.9 -> 4.1.7, Vite 6.4.2 -> 8.0.14, TypeScript 5.9.3 -> 6.0.3,
  Three 0.170.0 -> 0.184.0, `@types/three` 0.170.0 -> 0.184.1, and
  `vite-plugin-static-copy` 2.3.2 -> 4.1.0.
- `npm --prefix tauri/ui ls --depth=0`: top-level UI dependencies resolve.
  The direct GLB stack is `@gltf-transform/core` 4.3.0 plus `gltf-pipeline`
  4.3.1; `@gltf-transform/cli` 4.3.0 is also installed and is the current
  source of the dev-only `tmp` audit path.
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run`: still
  47 compatible Rust package updates are available, including Tauri 2.11.1 ->
  2.11.2, `global-hotkey` 0.7.0 -> 0.8.0, and `tao` 0.35.2 -> 0.35.3.
- `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d`: duplicate Rust
  packages remain. The direct action item is still the app's `core-graphics`
  0.24 dependency beside the Tauri/Tao `core-graphics` 0.25 edge.

Dependency refresh, 2026-05-31 11:33 +03:

- `uv pip check`: still one incompatibility, the expected `pyrekordbox` ->
  missing `sqlcipher3-wheels` edge. Keep it as a named XML/ANLZ-mode exception,
  not a reason to add SQLCipher to the bundle by default.
- `uv pip list --outdated --format=json`: still 50 outdated Python packages.
  Current upgrade groups are unchanged: AI/runtime SDKs, LiveKit, telemetry,
  PyObjC, `numpy`, `tokenizers`, `protobuf`, and `websockets`.
- `npm --prefix tauri/ui audit --omit=dev --json`: production audit remains
  clean with 0 findings.
- `npm --prefix tauri/ui audit --json`: dev audit still has 6 findings:
  Vitest's nested Vite/esbuild path accounts for 5 moderate findings, and
  `tmp` accounts for 1 high finding.
- `npm --prefix tauri/ui outdated --json`: direct major lanes remain Vitest
  2.1.9 -> 4.1.7, Vite 6.4.2 -> 8.0.14, TypeScript 5.9.3 -> 6.0.3, Three
  0.170.0 -> 0.184.0, `@types/three` 0.170.0 -> 0.184.1, and
  `vite-plugin-static-copy` 2.3.2 -> 4.1.0.
- `npm --prefix tauri/ui ls --depth=0`: top-level UI dependencies still
  resolve. Direct installed versions include `@gltf-transform/cli` 4.3.0,
  `@gltf-transform/core` 4.3.0, `gltf-pipeline` 4.3.1, Playwright 1.60.0,
  Three 0.170.0, Vite 6.4.2, and Vitest 2.1.9.
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run`: still
  reports 47 compatible Rust updates, including Tauri 2.11.1 -> 2.11.2,
  `global-hotkey` 0.7.0 -> 0.8.0, and `tao` 0.35.2 -> 0.35.3.
- `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d`: duplicate Rust
  packages remain; the repo-owned follow-up is still the direct
  `core-graphics` 0.24 edge beside Tauri/Tao's 0.25 edge.

Package footprint refresh, 2026-05-31 11:07 +03:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  still green with 167 assigned dirty paths.
- `git diff --stat`: tracked tree remains 93 files, 4894 insertions, and
  1752 deletions.
- Checklist-parser footprint scan over current assignments shows path count is
  not enough to decide staging risk. `Package 5 - Library UI Live Read Context`
  is only 4 paths but carries 1574 tracked additions and 238 deletions.
  `Package 2 - Session IPC And Diagnostics Wiring` carries 684 additions and
  1032 deletions across 29 tracked paths. `Package 3 - IPC Contract Cleanup`
  carries 132 additions, 1323 deletions, and 369 untracked text lines. Launch
  and design holds carry most new asset bytes, not code.

Latest refresh, 2026-05-31 11:09 +03:

- A parallel session added tracked changes in `src/vibemix/audio/deck_signal.py`
  and `tests/audio/test_deck_signal.py`. The package checker caught both as
  unassigned; they are now classified under the Deck Audio Controller-Weighted
  hold lane because the diff makes the Judge's executed-mix routing honor
  `capture.effective_enabled()` and adds the regression for unverified
  auto-Rekordbox deck-pair hints staying honest-null.
- `git diff --shortstat`: now 95 tracked files changed, 5092 insertions, and
  1755 deletions.
- `git ls-files --others --exclude-standard | wc -l`: still 74 untracked paths.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  after classification, 169 dirty paths are exactly listed and every dirty path
  is assigned to an Include/Hold lane.

Latest refresh, 2026-05-31 11:53 +03:

- `git diff --shortstat`: now 98 tracked files changed, 5148 insertions, and
  1760 deletions after the local MOSS TTS wrapper, TTS-chain opt-in, and
  dependency-manifest paths appeared.
- `git ls-files --others --exclude-standard | wc -l`: now 78 untracked paths
  after the local MOSS TTS ONNX runtime, wrapper, and focused test file appeared.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  green again after expanding the local MOSS TTS hold lane; 176 dirty paths are
  exactly listed, 3 generated launch previews are ignored, and every dirty path
  is assigned to an Include/Hold lane.
- `codegraph_context` still identifies the stable app entry points through
  `src/vibemix/__main__.py:main`, `tauri/src-tauri/src/main.rs:main`, and the
  Tauri spike entry point. Keep structural plans behind those boundaries until
  an explicit package changes them.

Drift refresh, 2026-05-31 12:11 +03:

- `git diff --shortstat`: now 96 tracked files changed, 5117 insertions, and
  1756 deletions.
- `git ls-files --others --exclude-standard | wc -l`: now 76 untracked paths.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`:
  green after classifying `src/vibemix/state/drop_predict.py` and
  `tests/state/test_drop_predict.py`; 172 dirty paths are exactly listed,
  3 generated launch previews are ignored, and every dirty path is assigned to an
  Include/Hold lane.
- Focused drift proof for the new drop helper is green:
  `uv run pytest -q tests/state/test_drop_predict.py` reports 9 passed, and
  `uv run ruff check src/vibemix/state/drop_predict.py tests/state/test_drop_predict.py`
  passes. This is unit proof only; live drop-calling remains a hold-lane claim.
- Local MOSS TTS is now represented in the dirty tree only by residual
  `uv.lock` changes; the earlier wrapper/runtime/test files are historical until
  they reappear in `git status`.

Drift refresh, 2026-05-31 12:14 +03:

- `git diff --shortstat`: now 97 tracked files changed, 5153 insertions, and
  1756 deletions after `src/vibemix/state/refresh.py` joined the drop-prediction
  drift.
- `git ls-files --others --exclude-standard | wc -l`: still 76 untracked paths.
- `src/vibemix/state/refresh.py` imports `predict_drop_in_sec` and writes
  `state.predicted_drop_in_sec` from audible-deck sections with confidence and
  horizon guards. That makes the drift an integration hold, not just a pure
  helper.
- Focused evidence: `uv run pytest -q tests/state/test_refresh.py -k predicted_drop`
  passes 1 test; `uv run ruff check src/vibemix/state/refresh.py src/vibemix/state/drop_predict.py tests/state/test_drop_predict.py`
  currently fails on import sorting in `refresh.py`. Do not fix it in the
  planning lane; keep it as a Mix Timing Oracle hold gate.

Intra-path drift refresh, 2026-05-31 12:17 +03:

- `git diff --shortstat`: still 97 tracked files, but insertions rose to 5181
  while deletions stayed 1756.
- `git diff --numstat -- src/vibemix/state/refresh.py` now reports `64 / 0`;
  the same assigned path gained opt-in `VIBEMIX_DROP_DEBUG` countdown logging.
- The package checker remained green with 173 dirty paths assigned. That proves
  path ownership only; it does not prove the hunks stopped changing.

## Goal Completion Audit Matrix

This is the definition of done for the user's full cleanup objective. The goal is
not complete while the tree is merely mapped; completion requires the evidence
below to prove that the codebase is actually organized, maintainable, lighter or
safer where planned, and not hiding active-session work inside broad commits.

Audit refresh on 2026-05-31:

- Current state: `git diff --shortstat` reports 96 tracked files changed,
  5117 insertions, and 1756 deletions; `git ls-files --others --exclude-standard
  | wc -l` reports 91 untracked paths.
- Package state: `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  is green with 187 dirty paths listed and assigned, plus 3 ignored generated
  launch previews. The checker includes staged, unstaged, and untracked paths.
- Completion state: planning is strong, but the objective is not complete. The
  package lanes have not been staged/landed, hold-lane live proof is still
  pending, local MOSS TTS still has a residual lockfile hold, dependency
  modernization is only planned, and structural refactors have not started by
  design.

| Requirement from objective | Current evidence | Completion proof still required |
|---|---|---|
| Do no product coding while other sessions are active | This map, checklist, inventory, package checker, and tests are planning/tooling surfaces; recent passes only changed planning docs. | Before any product edit, coding sessions must pause or the package lane must be explicitly opened by the user. |
| Current work is organized into neat packages | Package checker is green with 187 dirty paths assigned; shared-path assignments are visible, and Singularity research / CLAP eval work are isolated as hold lanes. | Package 0 must stage first, then each Include/Hold lane must be refreshed after every staged commit. |
| Findings are always evidence-backed | Evidence snapshots include git status/shortstat, package checker, dependency checks, architecture density, subsystem boundaries, and orphan inventory. | Each future claim must name the command, file, runtime log, test, or live probe that proves it. |
| Shared files cannot smuggle unrelated work | Shared-File Hunk Discipline names `AGENTS.md`, `__main__.py`, session loop, IPC schema/generated files, and IPC tests. | Every commit touching a shared path must inspect `git diff --cached -- <path>` and document intentional package combinations. |
| Codebase becomes more maintainable | Cleanup sequence, subsystem boundary map, clean refactor candidate map, orphan triage, and extraction work orders now exist. | Structural refactors must wait until owning packages land, then pass entry/exit criteria and focused tests. |
| System becomes lighter/faster/more capable/polished where safe | Dependency opportunity matrix and modernization rings identify Python, UI, Rust, GLB, Three, and release-hardening lanes. | Dependency rings must run as dependency-only packages with their ecosystem gates; performance/bundle claims need measured proof. |
| Used libraries are current and conflicts are understood | `uv pip check`, `uv pip list --outdated`, npm audit/outdated/ls, Cargo dry-run, and Cargo duplicate tree are recorded. | Planned upgrades must land or be explicitly deferred with reasons; the SQLCipher omission remains a named exception, not an unresolved conflict. |
| Cue/pill/Viber correctness is preserved | Package 4-6 are kept as one product pipeline; memory guidance preserves `CuePoint.source`, semantic `CuePoint.number`, and `CARE` uncertainty. | Live DDJ/Viber proof must show ingest/cache -> next suggestion -> compact pill -> export/live-read consistency. |
| IPC and Tauri contracts remain safe | Package 2/3 contract coupling, count 72 guidance, codegen checks, and mock-transfer anchors are documented. | Every IPC split must pass schema, wiring checker, UI codegen/check, parity tests, and relevant Tauri/UI proof. |
| No excluded scope sneaks in | GSD and Learn beginner path are explicitly excluded unless reopened; Learn producer moat is a hold lane. | Future staging/test evidence must continue excluding those suites unless the user changes the boundary. |

Do not call the goal complete until every row above has current evidence in the
right-hand column. A green package checker proves organization of the current
dirty tree, not completion of the cleanup objective.

## Current Completion Blocker Board

This board is the short list that prevents the cleanup goal from being marked
complete. It is intentionally stricter than "the docs look good": every blocker
needs current evidence before it can move to done.

| Blocker | Evidence that it is still open | What closes it |
|---|---|---|
| Packages are mapped but not landed | Package checker is green with 187 assigned dirty paths, and the dirty tree still has 96 tracked files plus 91 untracked paths. | Stage and commit Package 0 first, then land or explicitly defer each Include/Hold lane with refreshed package-checker evidence. |
| Shared-file hunk risk remains | `__main__.py`, `session_loop.py`, IPC schema/codegen files, AGENTS/tooling files, and IPC tests are shared across packages. | Every commit touching those paths includes cached hunk review and intentional package-combination notes. |
| Live proof is incomplete | Live proof queue still names Tauri IPC GUI, cue/pill/Viber DDJ proof, Earned Wall UI proof, memory readiness proof, audible auto-master proof, deck-audio controller proof, and a release-train long set. | Required UI log, websocket, session `events.jsonl`, hardware/audio, screenshot/recording, and cited co-host evidence are pasted into package notes. |
| Local MOSS TTS is not shippable | The current dirty tree keeps only residual `uv.lock` changes for `sentencepiece` / `tts-local`; the previous wrapper/runtime/test slice is no longer dirty. | Either restore the full local-TTS package with tests, NOTICE/docs, install/model-cache, latency/bundle, and grounding proof, or remove/regenerate the residual lockfile diff. |
| Dependency modernization is planned only | Dependency rings exist, but no Python/UI/Rust dependency ring has landed; the 12:29 dependency audit still shows 50 outdated Python packages, 6 npm dev findings, and 47 compatible Cargo updates. | Run dependency-only rings with ecosystem gates and measured proof; keep them separate from product/refactor commits. |
| Structural refactors have not started by design | Refactor DoD and extraction work orders exist, but dirty owning packages are still active. | After package lanes settle, execute subsystem refactors with entry/exit criteria, focused tests, import/codegen/build gates, and live proof where runtime-sensitive. |
| Public claims are not fully proven | Cost/pricing and launch collateral are mapped, but billing-source refresh, exact asset selection, and local-TTS cost/latency implications are unresolved. | Refresh public claim evidence, select assets, and keep internal or unverified claims out of launch-facing packages. |

If a blocker is intentionally deferred, record the deferral reason and owner in
the package checklist. Silent deferral is how this tree becomes confusing again.

## Hold-Lane Decision Ledger

These lanes are intentionally not part of the first shipping stack. A hold lane
can become active only when the listed promotion evidence exists or the user
explicitly changes the boundary.

| Hold lane | Default decision | Promotion evidence | False claim this prevents |
|---|---|---|---|
| Learn Beatmatch Producer Plan | Defer as planning only. | Red tests or implementation plan for the missing `BEATMATCH_GRADED` producer, live/by-ear proof, and explicit decision to reopen the Learn producer path. | Claiming Course 3 mastered credit from UI scaffolding rather than cited live judge evidence. |
| Launch Screenshot Alternates | Defer unless selected. | Exact asset-selection decision and updated Package 11 evidence bundle. | Shipping or reviewing all screenshot variants as if they were canonical launch collateral. |
| Premium Enterprise Visual Audit | Defer as design evidence. | Accepted production visual direction, mock-transfer contract updates, UI build/tests, and screenshot proof. | Moving mock HTML or design-audit artifacts into production UI without contracted anchors. |
| Local MOSS TTS ONNX Runtime | Defer as local-TTS spike. | Green local-TTS tests, NOTICE/license/model-source docs, `tts-local`/`ai-local` install proof, model-cache/download flow, latency/bundle measurement, and grounding review before live speech. | Presenting an opt-in local voice as shippable while tests are red and attribution/runtime proof is incomplete. |
| Deck Audio Controller-Weighted Master Context | Defer as audio/live-proof lane. | Routed Deck A/B audio, controller posture changing captured context, cited co-host evidence, and no deck-identity overclaim. | Claiming controller-aware master context from unit arrays or port-present MIDI alone. |
| Mix Timing Oracle | Defer as mix/audio future work. | Current ruff hygiene fixed, focused mix/drop tests green, and live-audio proof that timing claims are grounded. | Blending spoken-drop timing claims into runtime or launch work before the mix evidence is stable. |
| Debrief Timeline And Citations | Defer as deep work. | Backend producer, UI consumer, schema/codegen, TS validator/session tests, and IPC wiring checks in the same package. | Reintroducing schema-only IPC ghosts for debrief metrics with no live producer/consumer. |

If a hold lane is promoted, first update its package checklist section with a
new Include list, proof packet, and stop conditions. Do not promote by staging
paths first and documenting later.

## Hold-Lane Promotion Workflow

Promotion turns a hold lane into active work only after evidence changes. Use
this workflow for Local MOSS TTS, controller-weighted deck context, launch
alternates, Learn producer work, premium visual audit, Mix Timing Oracle, and
future hold lanes:

1. Name the decision: user acceptance, product owner decision, or new proof that
   makes the hold lane actionable.
2. Add a new Include list to the package checklist before staging. Keep old hold
   evidence in the history so reviewers can see why the lane was blocked.
3. Add a proof packet with commands, live/runtime evidence, asset decisions,
   dependency gates, and attribution/licensing notes as relevant to the lane.
4. Add stop conditions. At minimum, stop if unrelated product behavior,
   dependency manifests, generated artifacts, or shared-file hunks enter without
   being named in the promoted package.
5. Refresh the package checker in strict mode. Promotion is not valid while the
   checker is red or while the promoted paths are still assigned only to a hold
   lane.

Demotion is allowed too: if proof fails, move the lane back to Hold with the
failure pasted as evidence. Do not leave a half-promoted lane in the Include
stack.

## Review Packet Index

Use this index before staging, reviewing, or asking another agent to continue.
It points each decision to the smallest packet that contains the current
evidence, boundaries, and missing proof.

| Packet | Primary place to read | What it proves | Do not claim from it |
|---|---|---|---|
| Completion audit | This map's Goal Completion Audit Matrix | The full cleanup objective is still active, with explicit proof still missing. | That the codebase is already clean or release-ready. |
| Package ledger | `.planning/handoffs/2026-05-31-package-checklist.md` Package 0 and current evidence bundle draft | The dirty tree is assigned into reviewable Include/Hold lanes. | That any product lane is ready to stage without its own evidence. |
| IPC packet | Package checklist's Package 2/3 sections plus Current IPC split audit | The IPC schema/generated/wrapper/test bundle is coupled and defaults to a combined IPC review. | That a schema, generated TS, Python wrapper, or validator file can move alone. |
| Cue/pill/Viber packet | Package checklist's Package 4-6 sections plus Current Packages 4-6 pipeline audit | Auto/ANLZ cues, library live-read context, next suggestions, and compact pill behavior remain one product pipeline. | That unit tests alone prove live DDJ/Viber behavior. |
| Learn/Earned packet | Package checklist's Package 7/8/9 sections plus Current Learn/Earned Wall audit | Learn operator actions and Earned Wall refresh are adjacent but not the same as the beatmatch producer hold. | That GSD or beginner-path suites are reopened. |
| Public-claims packet | Package checklist's Package 10/11 sections plus Current public-claims audit | Cost/pricing and launch collateral have separate claim boundaries. | That launch collateral inherits cost proof, or cost docs inherit launch selection proof. |
| Runtime technical packet | Package checklist's Package 12-15 sections plus Current runtime technical lanes audit | Memory CLAP readiness, sidecar freshness, TTS shutdown, and auto-master routing have distinct gates. | That shared `__main__.py` or `session_loop.py` hunks can be whole-file staged. |
| Local TTS hold packet | Package checklist's Hold Lane - Local MOSS TTS ONNX Runtime Spike | The new MOSS wrapper/runtime/`tts_chain` opt-in slice is isolated from live shutdown, pricing, and dependency packages until attributed, tested, and dependency-gated. | That local MOSS TTS is benchmarked, licensed for shipping, dependency-complete, or live-ready. |
| Dependency packet | This map's Dependency Execution Audit and Dependency Modernization Rings | Current library/version conflicts are understood and sequenced into dependency-only packages. | That dependency modernization has landed. |
| Live proof packet | This map's Live Proof Queue and Remaining Live Proof Burn-Down | Runtime, UI socket, controller, audio, and cited co-host evidence still needed for product-ready claims. | That a green unit/build suite proves live hardware behavior. |
| Local shadow packet | Package checklist's Local Shadow Audit and Final Live Proof Gate | Local stale app/sidecar/worktree hazards are known before live validation. | That ignored `.claude/worktrees/**` state is shippable or safe to delete. |

Review rule: if a claim spans two packets, either collect evidence from both or
write the narrower claim. The safest future commits will be boring because the
packet and proof boundary are obvious before staging starts.

## Parallel Session Drift Protocol

Use this whenever a parallel session changes the worktree while the cleanup goal
is active. The point is to keep the plan true without taking ownership of another
session's code.

1. Refresh: run `git status --short`, `git diff --shortstat`,
   `git ls-files --others --exclude-standard | wc -l`, and
   `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`.
2. If the package checker is red, inspect only enough of each missing path to
   determine its owner, risk, and likely package. Do not edit the product code.
3. Classify the path in `.planning/handoffs/2026-05-31-package-checklist.md`
   as an Include or Hold lane. Prefer a hold lane when attribution, dependency,
   live proof, or product decision is missing.
4. Update the current evidence counts in this map and the Package 0 evidence
   bundle when tracked/untracked totals changed.
5. Run planning guardrails: `git diff --check` on planning docs, the package
   checker, and `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py`.
6. If a focused test for the new lane is already present, run it once for
   evidence. Record failures as blockers; do not repair them unless the user
   opens that package for coding.

Evidence demotion rules:

- When a path disappears from `git status`, remove it from the current dirty
  counts and package footprint. Keep the older proof only as historical context.
- If a manifest or lockfile remains dirty after its source package disappears,
  treat it as a residual dependency hold until the owner restores the package or
  removes/regenerates the stale manifest/lockfile diff.
- A focused green test for a newly appeared helper proves only that helper. It
  does not promote the lane unless runtime integration, live proof, and any
  speech/grounding gates are also current.
- If old and new evidence disagree, the live worktree plus the latest checker
  output wins. The docs should say what changed rather than trying to preserve
  both as current.

Intra-path drift rules:

- If shortstat or numstat changes but the package checker stays green, inspect
  the changed assigned paths before claiming the lane is stable.
- Update package evidence when a hunk materially changes behavior, logging,
  dependency posture, generated output, or public claims, even if no new path was
  added.
- A green package checker is never a substitute for cached hunk review on shared
  files or live-proof-sensitive runtime files.

Current hunk-stability watchlist, 2026-05-31 12:20 +03:

| Path or cluster | Lane | Current numstat evidence | Why watch | Next proof |
|---|---|---:|---|---|
| `src/vibemix/state/refresh.py` | Mix Timing Oracle hold | `64 / 0` | Single-writer runtime hunk now writes `predicted_drop_in_sec` and adds opt-in `VIBEMIX_DROP_DEBUG` logging; focused Ruff is red. | Fix lint in the owning lane, then prove `predicted_drop` focused tests plus live/audio and speech-grounding behavior before promotion. |
| `src/vibemix/__main__.py` | Package 10, Package 14, Deck Audio hold | `171 / 3` | CLI budget, TTS shutdown, and controller/deck-audio hunks share the same high-risk entrypoint file. | Cached hunk review for every staging card; never whole-file stage unless those lanes are intentionally combined. |
| `src/vibemix/runtime/session_loop.py` | Package 2, Package 12 | `24 / 2` | Session IPC ingress normalization and memory-ingest readiness share one runtime file. | Stage by hunk or combine Packages 2 and 12 deliberately, then run IPC and memory gates. |
| IPC schema/generated cluster | Packages 2 and 3 | schema `1 / 414`, TS `0 / 90`, validator `1 / 1`, Python messages `5 / 190`, library schema `3 / 76` | Contract deletion/codegen paths can look green by path while the generated shape is stale. | `scripts/check_ipc_schema.py`, IPC wiring checker, UI `check:ipc`, generated diff review, focused IPC/UI-bus tests. |
| Library live-read UI cluster | Package 5 | `api.ts 408 / 52`, `api.test.ts 433 / 4`, `chat.test.ts 435 / 77`, `index.ts 298 / 105` | Largest UI churn; easy to mix live-read context, command wrappers, and chat artifacts. | Library API/chat tests, UI build, and live-read/Viber evidence before any refactor around it. |
| Pill UI cluster | Package 6 | `pill.css 118 / 15`, `index.ts 45 / 3` | Compact visible copy and recoverable detail can diverge when hunks move independently. | Pill unit tests, Playwright/browser proof where needed, UI build, and accessibility/title detail checks. |

Current drift lesson:

- Parallel sessions can both add and remove package slices. The local MOSS TTS
  wrapper/runtime/test files disappeared from `git status`, leaving only the
  `uv.lock` residual hold; then `drop_predict.py` and its focused tests appeared
  and made the checker red until assigned to the Mix Timing Oracle hold. Always
  trust the live tree first, then preserve older evidence as history rather than
  current proof.

## Current Ownership State

The package checklist is the source of truth for active dirty-path ownership:

- Shipping inventory docs are Package 0.
- IPC work is split between Package 2 and Package 3, with shared schema/generated
  files. Never stage IPC schema, generated TS, validator, Python dataclasses, and
  parity tests separately.
- Auto/ANLZ cue -> pill -> Viber remains a full pipeline lane. Preserve cue
  provenance and semantic hot-cue slot numbering end to end.
- Premium enterprise mockups are a design hold lane, not production UI.
- Controller-weighted deck-audio master context is its own hold lane. It is not
  the same as the desktop 16ch device-selection fix.
- Local MOSS TTS ONNX runtime is a hold lane. It now includes a wrapper and
  opt-in `tts_chain` wiring, but still needs attribution, dependency, model-cache,
  test, latency/bundle, and grounding proof before any live TTS claim.
- Mix timing / spoken-drop work currently belongs in a hold lane and must not be
  mixed into runtime memory, library UI, or launch collateral packages.

## Maintenance Hotspots

Largest source files by line count:

- `src/vibemix/__main__.py`: 6007 lines, dirty. This is the main extraction
  target, but it currently carries active live-audio, budget, shutdown, and CLI
  changes. Do not refactor it until those lanes are staged or settled.
- `tauri/ui/src/pill/pill.css`: 4101 lines, dirty. Split only after the pill
  visual/e2e lane is green and screenshot behavior is accepted.
- `src/vibemix/library/codex_curate.py`: 3888 lines, clean. Good later target
  because it is large but not currently dirty.
- `src/vibemix/state/deck_context.py`: 3247 lines, dirty; current diff is only
  the new deck-audio master-source evidence text. Treat it as high-risk
  grounding code; avoid broad edits.
- `src/vibemix/agent/dj_cohost.py`: 3206 lines, clean but high-risk because it
  changes what the co-host says. Use grounding-review invariants before edits.
- `tauri/ui/src/ipc/messages.schema.json`: 3085 lines, dirty generated-contract
  surface. Treat schema and generated files as one package.
- `tauri/ui/src/pill/index.ts`: 2736 lines, dirty.
- `tauri/ui/src/library/api.ts`: 2595 lines, dirty.
- `tauri/src-tauri/src/library_cmds.rs`: 1890 lines, clean and a good later Rust
  extraction target after library command contracts settle.
- `src/vibemix/ui_bus/messages.py`: 1960 lines, dirty with a large deletion-heavy
  IPC cleanup diff. Keep it paired with schema/generated UI artifacts.
- `src/vibemix/runtime/session_loop.py`: 1477 lines, dirty shared runtime surface
  for IPC/session and memory-ingest readiness. Avoid opportunistic refactors until
  Packages 2 and 12 are staged.
- `src/vibemix/intel/move_grade.py`: 274 lines, dirty but semantically central to
  cue confidence and pill truthfulness. Small file, high product-risk surface.

Structural hotspot rebaseline, 2026-05-31 12:37 +03:

- Fresh size scan confirms the main pressure points: Python totals 97,216 lines
  under `src/vibemix`, led by `__main__.py` 6007, `codex_curate.py` 3888,
  `deck_context.py` 3279, and `dj_cohost.py` 3206. UI TypeScript totals 69,214
  lines, led by `pill/index.ts` 2736, `library/api.ts` 2595,
  `library/index.ts` 2132, and `learn-window.ts` 1530. UI CSS totals 11,096
  lines, led by `pill/pill.css` 4101. Rust shell code totals 8388 lines, led by
  `library_cmds.rs` 1890.
- Fresh directory density keeps `library` as the largest Python area
  (60 `.py` files), followed by `state` 41, `learn` 28, `runtime` 22,
  `platform` 20, `audio` 19, and `agent` 19. UI density is led by `mascot` 50,
  `wizard` 43, `session` 36, `learn` 28, `debrief` 24, and `settings` 21.
- Fresh churn scan says the highest-risk active movement is not the biggest file:
  Package 5's library UI files lead tracked insertions (`chat.test.ts` 435 / 77,
  `api.test.ts` 433 / 4, `api.ts` 408 / 52, `index.ts` 298 / 105), followed by
  audio/deck capture, library ingest, and shared `__main__.py`. Use churn plus
  package ownership, not raw line count, to choose refactor order.
- Codegraph's current entrypoint context still surfaces `SessionLoop` as a key
  runtime class and does not contradict the existing rule: keep
  `vibemix.__main__:main()` and the Tauri Rust `main.rs` thin/stable while
  extracting adapters around them.

First refactor tickets to open after package lanes settle:

1. `library/codex_curate.py` docs-backed extraction: split subprocess/tool-tape,
   set-prep, live-context normalization, and result/error mapping while keeping
   Codex-local MCP behavior stable.
2. `tauri/src-tauri/src/library_cmds.rs` adapter extraction: group command
   handlers by library/Viber domain after IPC and tool contracts are settled.
3. `src/vibemix/__main__.py` CLI-tail extraction: move parser/subparser and
   library budget command handlers before touching live boot, audio callbacks,
   or shutdown helpers.
4. `tauri/ui/src/pill/pill.css` / `pill/index.ts` visual extraction: split only
   after Package 6 visual behavior is accepted and Playwright/screenshot proof is
   current.

## Cleanup Sequence

1. Keep the package checker green after every live-tree movement.
   Evidence gate: `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`.

2. Stage Package 0 first when coding sessions pause.
   Include the inventory, checklist, checker, checker tests, and this map. This
   makes later staging reviewable.

3. Stage small isolated hold lanes before broad refactors.
   Good first candidates are Desktop Auto-Master 16ch Upgrade and Deck Audio
   Controller-Weighted Master Context, but only after their current gates pass.

4. Stage IPC packages as complete contract bundles.
   Required gates: `uv run python scripts/check_ipc_schema.py`,
   `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
   and `npm --prefix tauri/ui run check:ipc`.

5. Stage cue/pill/Viber as a pipeline, not as isolated slices.
   Required idea: the same semantic cue slot and source that survive ingest/cache
   must drive the next suggestion and downstream Viber/export preview.

6. Create a dependency hygiene package after feature lanes quiet down.
   Do not mix dependency churn with product behavior. Treat npm dev-audit, Rust
   compatible patch refresh, and Python repo-aware `uv pip check` handling as
   separate substeps.

7. Only then begin structural refactors.
   Start with clean large modules where behavior can be extracted behind stable
   tests. Favor adapters and command modules over new abstractions.

## Staging Dependency Graph

Use this order when the active coding sessions pause:

1. Package 0 first: it gives the reviewer a trusted ledger and the package
   checker that keeps later commits honest.
2. Packages 1, 13, and 15 can move early because they are tooling or narrow
   runtime boot/capture fixes, but each still needs its listed live/sidecar proof.
3. Packages 2 and 3 are coupled by IPC schema/codegen. Either combine them or
   stage each as a complete schema/generated/Python/test bundle.
4. Packages 4, 5, and 6 should be reviewed as a product pipeline: cue
   materialization, library/Viber live context, and compact pill copy must agree
   about cue source, semantic cue slot, and CARE-grade uncertainty.
5. Packages 7 and 9 touch Learn/operator-credit surfaces. Keep the excluded
   beginner-path suites out unless explicitly requested.
6. Packages 10 and 11 are public-facing economics/launch collateral. Do not mix
   them with dependency upgrades or runtime refactors.
7. Package 12 must land before live proof is treated as durable, because stale
   sqlite-vec memory state can block source-mode verification.
8. Hold lanes stay out of shipping packages until their remaining gates become
   proof, not just plausible test coverage.

## Staging Runbook

Run this as the execution checklist once coding sessions pause. It is intentionally
slower than `git add .`: the current tree has shared files, generated artifacts,
and hold lanes that can make a clean-looking commit lie about product behavior.

Wave 0 - refresh evidence:

- Run `git status --short`, `git diff --shortstat`, and
  `git ls-files --others --exclude-standard | wc -l`.
- Run `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`.
- If any new dirty path appears, stop and classify it in the package checklist
  before staging anything.

Wave 1 - stage the ledger:

- Stage Package 0 only: inventory, checklist, maintainability map, package
  checker, and package-checker tests.
- Re-run the package checker plus `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py`
  and `uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py`.
- After this wave lands, refresh the checklist because every later dirty-path
  count will change.

Wave 2 - low-blast-radius tooling and runtime guards:

- Consider Packages 1, 13, 14, and 15 only if their listed live or focused gates
  are fresh. Package 14 shares `src/vibemix/__main__.py`, so stage shutdown hunks
  away from budget and deck-audio hunks.
- Keep the Deck Audio Controller-Weighted hold lane out unless controller posture,
  route, and cited/audio context proof all exist.

Wave 3 - IPC contract bundle:

- Stage Packages 2 and 3 together by default. If they must split, each split must
  include schema, generated TypeScript, generated validator, Python message
  wrappers, and parity tests that match that split.
- Required gates after each IPC staging shape:
  `uv run python scripts/check_ipc_schema.py`,
  `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
  `npm --prefix tauri/ui run check:ipc`, and the focused IPC/session/UI tests
  listed in the package checklist.

Wave 4 - cue, pill, library, and Viber pipeline:

- Treat Packages 4, 5, and 6 as one product review even if they land in more than
  one commit. The evidence must show the same cue source and semantic hot-cue
  number surviving ingest/cache, next-suggestion scoring, compact pill display,
  and Viber/export preview.
- Do not accept a green unit-only result for this wave; it needs the listed pill
  unit/e2e/build gates plus live DDJ/Viber proof before user-facing claims.

Wave 5 - Learn/operator and earned-wall surfaces:

- Stage Packages 7 and 9 only with their targeted tests and grounding checks.
- Keep GSD and Learn beginner-path suites out unless the user explicitly reopens
  those paths.

Wave 6 - economics and launch collateral:

- Stage Package 10 only after billing-source evidence is refreshed; keep internal
  spike/pricing notes out of external claims.
- Stage Package 11 after selecting the exact launch assets. Keep screenshot
  alternates and premium enterprise design audit files in their hold lanes unless
  selected.

Wave 7 - dependency hygiene:

- Create separate dependency packages after feature lanes quiet down: Python
  health check and SDK rings, UI dev-audit tooling, Rust compatible lock refresh,
  then any larger major-version migrations.
- Do not mix dependency version churn with behavior changes, launch collateral,
  or structural refactors.

Wave 8 - structural refactors:

- Begin only after the owning feature package has landed or the target file is
  clean. Prefer `codex_curate.py` and bounded UI/API extractions before touching
  dirty runtime orchestration.
- Preserve `vibemix.__main__:main()`, IPC schema/codegen shape, Viber/library
  tool contracts, cue/pill uncertainty semantics, and Tauri command signatures.

Abort conditions:

- Package checker is red or any dirty path is unclassified.
- A shared file is staged whole-file while its packages are not intentionally
  combined.
- IPC top-level count or generated artifacts disagree with schema/codegen checks.
- GSD or Learn beginner-path suites are run accidentally as evidence for this
  cleanup scope.
- Runtime or speech-affecting packages lack the live/grounding proof their
  checklist row calls for.
- Dependency upgrades appear in the same staged diff as product behavior or
  structural movement.

## Package Footprint Snapshot

Generated from the package checklist plus `git diff --numstat` on
2026-05-31 11:07 +03. Shared paths are counted in every package that owns them,
so this table is a review-risk map, not a repository-total ledger.

| Lane | Paths | Tracked +/- | Untracked text/assets | Staging read |
|---|---:|---:|---:|---|
| Package 0 - Shipping Inventory Docs | 5 | 0 / 0 | 2939 lines / 0 B | Planning-only; stage first once sessions pause. |
| Package 1 - Agent Tooling | 15 | 34 / 12 | 2718 lines / 0 B | Mostly new tooling/docs; keep out of customer release notes. |
| Package 2 - Session IPC | 29 | 684 / 1032 | 0 / 0 B | Contract-heavy and deletion-heavy; stage only with schema/codegen/wiring proof. |
| Package 3 - IPC Cleanup | 24 | 132 / 1323 | 369 lines / 0 B | Contract pruning; likely combine with Package 2 or stage as full IPC bundle. |
| Package 4 - Cue/Pill/Viber | 8 | 580 / 34 | 0 / 0 B | Small path count but product-critical; keep end-to-end. |
| Package 5 - Library UI Live Read | 4 | 1574 / 238 | 0 / 0 B | Largest tracked code churn; needs UI/library proof before any refactor nearby. |
| Package 6 - Compact Pill Polish | 10 | 582 / 42 | 1156 lines / 0 B | Visual/interaction work; pair unit, Playwright, and build proof. |
| Package 7 - Learn Operator Bridge | 10 | 372 / 14 | 221 lines / 0 B | Keep outside beginner/GSD suites unless explicitly reopened. |
| Hold - Learn Beatmatch Producer Plan | 1 | 0 / 0 | 151 lines / 0 B | Planning only; convert to red-test package later. |
| Package 9 - Earned Wall Refresh | 4 | 174 / 5 | 91 lines / 0 B | Small but speech/credit sensitive; grounding review if wording changes. |
| Package 10 - Cost/Pricing | 11 | 199 / 8 | 1265 lines / 0 B | Public claims need billing-source verification before external use. |
| Package 11 - Launch Collateral | 18 | 0 / 0 | 1207 lines / 7386699 B | Asset-heavy collateral; content selection before staging. |
| Hold - Launch Screenshot Alternates | 14 | 0 / 0 | 0 lines / 6866984 B | Keep as hold unless selected for launch collateral. |
| Hold - Premium Enterprise Visual Audit | 13 | 0 / 0 | 1692 lines / 3971331 B | Design evidence, not production UI. |
| Package 12 - Runtime Memory CLAP | 4 | 235 / 29 | 0 / 0 B | Runtime proof needed because stale local memory can block live validation. |
| Package 13 - Sidecar Freshness Guard | 2 | 68 / 0 | 0 / 0 B | Narrow packaging guard; release build proof remains separate. |
| Package 14 - TTS Shutdown | 2 | 205 / 3 | 0 / 0 B | Shared `__main__.py`; stage hunks carefully away from budget/audio work. |
| Hold - Local MOSS TTS ONNX Runtime | 7 | 56 / 5 | 1398 lines / 0 B | Wrapper + vendored runtime + `tts_chain` opt-in + `tts-local` dependency extra + focused tests; hold until attribution, missing-dependency/model-cache proof, and latency/bundle proof exist. |
| Package 15 - Auto-Master 16ch | 2 | 34 / 1 | 0 / 0 B | Narrow fix; musical/audible proof still separate from route proof. |
| Hold - Deck Audio Controller-Weighted | 9 | 682 / 12 | 0 / 0 B | Hold until full live proof with controller posture and audio context. |

## Shared-File Hunk Discipline

Evidence refresh: `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
and `git diff --unified=0` hunk scans on 2026-05-31 11:09 +03. These files
are assigned to multiple lanes; do not stage them by whole file unless the
listed packages are intentionally combined.

| Shared path | Current diff shape | Hunk boundary rule |
|---|---|---|
| `AGENTS.md` | `28 / 2` tracked +/-. One early hunk adds Supercharge Tooling; one later hunk updates IPC count guidance from 78 to 72. | Package 1 owns the tooling section. Package 3 owns the 72-count IPC guidance. Stage by hunk if Packages 1 and 3 separate. |
| `.claude/skills/ipc-wiring-checker/SKILL.md` and `.../check_ipc_wiring.py` | Untracked tooling files that already encode the 72-type baseline and empty reservation allowlist. | Package 1 owns the tool itself; Package 3 depends on its 72-count and no-reservation behavior. If Package 3 stages first, include the checker or keep a separate proof that the same logic exists. |
| `src/vibemix/__main__.py` | `171 / 3` tracked +/-. Hunk clusters: `inspect` import + `_close_tts_chain()` + shutdown close; controller snapshot/touched-control handoff in `_input_callback_factory`; live budget parser and `_cmd_library_budget_live()`. | Package 14 owns `_close_tts_chain()` and shutdown close. Package 10 owns budget parser/CLI/reporting hunks. Deck-audio hold lane owns controller-state callback hunks. Never whole-file stage this while those lanes are separate. |
| `src/vibemix/runtime/session_loop.py` | `24 / 2` tracked +/-. Hunk clusters: `normalize_legacy_timestamp()` ingress path; `memory_ingest_enabled` constructor and boot/close ingest skips; `run_session()` disables memory ingest for diagnostic session mode. | Package 2 owns legacy timestamp ingress normalization. Package 12 owns memory-ingest disablement for quick session probes. Stage by hunk or combine Packages 2 and 12 deliberately. |
| `src/vibemix/ui_bus/__init__.py`, `src/vibemix/ui_bus/messages.py`, `src/vibemix/ui_bus/schemas/library.py`, `tauri/ui/src/ipc/messages.schema.json`, `tauri/ui/src/ipc/messages.ts`, `tauri/ui/src/ipc/validator.generated.mjs` | Contract bundle: stale debrief reservations and library bus wrappers are removed; schema/codegen/exports move together. | Treat as Package 3 unless Package 2 and 3 are intentionally combined. Run `scripts/check_ipc_schema.py`, IPC wiring checker, and `npm --prefix tauri/ui run check:ipc` after any staging split. |
| `tests/ipc/test_library_schemas.py`, `tests/ui_bus/test_messages_schema.py`, `tests/ui_bus/test_mood_change_envelope.py`, `tests/ui_bus/test_recordings_messages.py` | Count/parity tests updated around the same 72-message contract. | Keep with the IPC contract bundle that owns schema/codegen. If separated, the staged tree will likely lie about IPC count. |

Staging guard before any commit:

- Run `git diff --cached -- <shared-path>` for every shared path above.
- Confirm each staged hunk belongs to exactly one package or to an intentionally
  combined package set.
- Re-run the package checker after staging, because the checker validates path
  ownership but cannot see partial-hunk intent.

## Package Readiness Matrix

| Lane | Current readiness | Next evidence before staging |
|---|---|---|
| Package 0 - Shipping Inventory Docs | Ready once sessions pause | Refresh `check_dirty_package_plan.py --strict-assignments --summary` immediately before staging. |
| Package 1 - Agent Tooling | Mostly ready, but live proof is partial | Prove the helper path through UI log and session `events.jsonl` after app runtime is available. |
| Package 2 - Session IPC | Hold for live GUI proof | Full Tauri pass for `ipc.status.recheck`, `ipc.error`, `ipc.session.citation`, Settings/Profile, and library staleness subscription behavior. |
| Package 3 - IPC Cleanup | Stage only as a complete IPC bundle | Re-run IPC schema count and wiring checks; keep count at 72 unless deliberately changed. |
| Packages 4, 5, 6 - Cue/Pill/Viber | Treat as one product pipeline | Live DDJ/Viber proof with cue source, semantic cue slot, and `CARE` uncertainty visible end to end. |
| Package 7 - Learn Operator Bridge | Mostly ready | Re-run curriculum export check after any source projection edit; keep GSD/beginner-path suites out. |
| Package 8 - Beatmatch Judge | Hold for routed-audio integration | Live practice loop must emit cited `BEATMATCH_GRADED` only from owned-deck judge evidence. |
| Hold - Learn Beatmatch Producer Plan | Hold | `.planning/LEARN-MOAT-PLAN.md` is planning for the missing producer; convert it into a real package only with red tests and by-ear/live proof. |
| Hold - Singularity Research Census Briefs | Hold | Broad read-only research/census docs under `.planning/singularity/2026-05-31/`; validate citations/status language and split into package-specific work before using as implementation authority. |
| Package 9 - Earned Wall Refresh | Hold for live UI proof | Re-run coach/progress tests after `runtime/coach.py`; repeat grounding review after speech edits. |
| Package 10 - Cost/Pricing | Internal-only until billing proof | Confirm Cartesia billing before external financial claims; keep Gemini Live spike out of runtime router/pricing. |
| Package 11 - Launch Collateral | Ready after content selection | Decide whether optional close-up screenshots are included; keep generated preview HTML ignored. |
| Package 12 - Memory CLAP Readiness | Ready except final live gate | Keep with final Tauri/DDJ live proof because stale memory state can block source-mode verification. |
| Package 13 - Sidecar Freshness Guard | Ready for packaging guard | Full `cargo tauri build` / signed artifact proof remains release packaging work. |
| Package 14 - TTS Shutdown | Ready with hunk discipline | Inspect `git diff --cached -- src/vibemix/__main__.py` so budget and shutdown edits do not travel together accidentally. |
| Hold - Local MOSS TTS ONNX Runtime | Hold | Current dirty tree only has residual `uv.lock` changes for `sentencepiece` / `tts-local`; prior wrapper/runtime/test files are historical until they reappear. Do not stage the lockfile with Package 14 or dependency rings. |
| Package 15 - Auto-Master 16ch | Route proof done, musical proof pending | Audible deck audio and cited co-host moment before claiming musical grounding. |
| Launch / Premium Design Holds | Hold | Stage only if the selected visual direction is accepted; do not mix with production UI. |
| Deck Audio Controller-Weighted Hold | Hold | Needs full live proof where controller posture changes audible master/citation context. |
| Mix Timing Oracle Hold | Hold | New `drop_predict.py` helper has green unit proof and `refresh.py -k predicted_drop` passes, but focused Ruff fails on `refresh.py` import sorting; live/audio drop-calling and speech grounding remain missing. |
| Debrief Timeline/Citations Deep Work | Future package only | Re-add IPC only with backend producer, UI consumer, schema/codegen, and wiring checks in the same package. |

## Execution Scoreboard

Evidence refresh on 2026-05-31: package checker is green with
187 dirty paths assigned, the tracked diff is 96 files / 5117 insertions /
1756 deletions, and there are 91 untracked paths. Use this scoreboard as the
operator view when staging begins; refresh it after any commit or parallel
session movement.

| Lane group | Current execution state | Why | Unlock / next action |
|---|---|---|---|
| Package 0 - planning ledger | Stage first when sessions pause | It contains the inventory, checklist, map, checker, and checker tests that keep later commits reviewable. | Refresh package checker, run checker tests/ruff, stage only Package 0. |
| Packages 2 + 3 - IPC contract bundle | Combine by default | Shared schema, generated TS, validator, Python wrappers, and count/parity tests make split staging high-risk. | Run schema check, IPC wiring checker, UI `check:ipc`, focused IPC/UI-bus tests, and UI build after any split. |
| Packages 4 + 5 + 6 - cue/pill/Viber | Review as one product pipeline | Ingested cue source and semantic hot-cue number must survive through scorer, compact pill, library live-read, and Viber/export. | Keep unit/e2e/build proof plus live DDJ/Viber proof before external claims. |
| Packages 1, 13, 14, 15 | Candidate early technical lanes | Tooling, sidecar freshness, TTS shutdown, and 16ch route fix are narrower than IPC or product-pipeline work. | Re-check live/sidecar gates; stage `__main__.py` hunks by package for Package 14/15 overlap. |
| Packages 7 + 9 | Wait for focused Learn/grounding proof | Learn operator bridge and Earned Wall refresh are product-adjacent and speech/credit sensitive. | Use targeted Learn/operator tests and grounding review; keep GSD/beginner suites excluded. |
| Packages 10 + 11 | Wait for claim/content selection | Cost/pricing and launch collateral can become public claims. | Refresh billing-source evidence, choose exact launch assets, keep alternates/design audit in holds. |
| Package 12 | Pair with final live proof | Memory CLAP readiness affects whether source-mode/live proof is trustworthy. | Keep close to final Tauri/DDJ proof and rerun memory tests. |
| Hold lanes | Do not stage as product work | Learn producer moat, local MOSS TTS, launch alternates, premium design audit, deck-audio controller weighting, mix timing, and debrief deep work are not ready to ship. | Convert a hold lane into an active package only with red tests or live proof and an explicit user/product decision. |
| Dependency modernization rings | Future dependency-only packages | Upgrades are planned, but mixing them with active feature packages would hide regressions. | Run rings 0-8 separately with ecosystem gates and measured proof for performance/bundle claims. |
| Structural refactors | Future only | Dirty feature packages still own many of the highest-risk files. | Start after package lanes land; use refactor entry/exit criteria and prefer clean large files first. |

Scoreboard abort rule: if a lane's "why" no longer matches the live worktree,
stop and update the package checklist before staging. The checker proves path
assignment, while this scoreboard records staging intent.

## Commit Stack Blueprint

Evidence refresh on 2026-05-31 11:27 +03: suggested commit names and package
gates are pulled from `.planning/handoffs/2026-05-31-package-checklist.md`.
Every commit must be DCO signed (`git commit -s`) and should be staged by path
or hunk from the package checklist, never by `git add .`.

| Stack slot | Commit shape | Suggested subject | Commit rule |
|---|---|---|---|
| 0 | Planning ledger only | `docs(planning): document dirty tree shipping lanes` | Stage the three planning docs, package checker, and checker tests. No product source. |
| 1 | Agent/operator tooling | `chore(agent-tooling): add live verification and IPC helper tooling` | Keep as maintainer tooling; exclude local `.claude/worktrees/**` and user-local settings. |
| 2 | IPC contract bundle | Combine `fix(session-ipc): wire status recheck errors and citation telemetry` with `fix(ipc): prune stale bus contracts` unless a deliberate split keeps full schema/codegen/parity proof in each commit. | Run IPC schema, wiring checker, UI `check:ipc`, focused tests, and UI build. Keep IPC count 72 unless deliberately changed. |
| 3 | Cue/pill/Viber pipeline | `fix(library-cues): preserve hot cue slots through suggestions`, `feat(library-ui): ground Viber live reads with deck-pair context`, and `feat(pill): polish next suggestion care interactions` as one review stack. | May be multiple commits, but review/proof must be end-to-end; no Learn/pricing/launch work. |
| 4 | Narrow technical fixes | `fix(packaging): reject stale bundled IPC schemas`, `fix(runtime): close nested live tts providers`, `fix(audio): honor explicit blackhole variants in auto-master mode` | Stage shared `__main__.py` hunks carefully. Do not include deck-audio controller-weighted hold hunks without live proof. |
| 5 | Learn/operator and earned-wall | `feat(learn): bridge route-mismatch operator actions`, `fix(learn-runtime): refresh earned wall after live cited credits` | Keep GSD/beginner suites excluded. Run targeted Learn/operator/grounding gates. |
| 6 | Cost/pricing and launch collateral | `feat(library-cost): add live stack budget model`, `docs(launch): package launch collateral and screenshots` | Refresh billing evidence before public claims. Select exact assets; leave screenshot alternates/design audit in holds unless chosen. |
| 7 | Runtime memory readiness | `fix(memory): reconcile stale sqlite-vec embedding dimensions` | Land near final Tauri/DDJ proof because stale memory can invalidate source-mode claims. |
| 8 | Hold-lane conversions | `docs(learn): plan beatmatch graded producer`, `docs(launch): refresh launch screenshot alternates`, `docs(design): capture premium session audit`, `feat(audio): weight deck-pair master by controller posture`, `feat(mix-timing): add spoken drop timing oracle` | Only create these commits when the hold has explicit product acceptance and the missing proof named in the checklist. |
| 9 | Dependency-only rings | Ring-specific dependency subjects, not feature subjects | Run modernization rings 0-8 separately. Do not include behavior changes or refactors. |
| 10 | Structural refactors | Refactor subjects scoped by subsystem, e.g. CLI/library/API extraction | Start only after owning feature packages land and refactor entry criteria are true. |

Stacking discipline:

- Re-run the package checker before and after every staged commit.
- For shared files, inspect `git diff --cached -- <path>` and verify the staged
  hunks belong to the selected stack slot.
- If a generated artifact changes during proof (`messages.ts`,
  `validator.generated.mjs`, lockfiles, bundle manifests), either include it in
  the matching contract/dependency package or revert/regenerate before staging.
- If a live proof fails, keep the package unstaged and record the failure in the
  checklist instead of moving the commit with partial evidence.

## Staging Cards

Use these cards as the quick execution surface when staging begins. Each card is
deliberately narrower than the full package notes: it says what to stage, what
must be proved, and what makes the card stop.

| Card | Stage shape | Evidence to refresh | Stop if |
|---|---|---|---|
| 0 - Ledger | Package 0 only: planning inventory, checklist, maintainability map, checker, checker tests. | `git status --short`, `git diff --shortstat`, untracked count, package checker, checker tests, focused Ruff, cached diff check. | Any product source, hold-lane file, dependency file, or generated artifact appears in the cached diff. |
| 1 - Tooling | Package 1 maintainer tooling only. | Tooling tests, IPC helper scan, UI log/session-event proof for live helper paths when available. | It starts describing customer-facing behavior or absorbs IPC count changes without Package 3. |
| 2 - Narrow Runtime Guards | Packages 13, 14, and 15 only if fresh; stage `__main__.py` by hunk for Package 14. | Sidecar freshness checks, shutdown tests, macOS/audio route tests, source/Tauri route proof as listed in the checklist. | `__main__.py` carries budget or deck-audio hold hunks, or Package 15 claims musical grounding without audible/cited proof. |
| 3 - IPC Bundle | Packages 2 and 3 together by default. | Schema count, IPC wiring checker, UI `check:ipc`, generated TS/validator review, IPC/UI-bus focused tests, UI build. | Schema, generated files, Python wrappers, tests, or Rust/TS consumers cannot move together. |
| 4 - Cue/Pill/Viber Pipeline | Packages 4, 5, and 6 as one review stack. | Library/intel tests, pill unit/e2e/build, live-read/Viber proof, then live DDJ/Viber proof for source/slot/CARE. | Cue provenance or semantic hot-cue number is visible in one layer but not the others. |
| 5 - Learn/Earned | Packages 7 and 9; keep Package 8 and Learn producer hold separate unless explicitly reopened. | Targeted Learn/operator tests, curriculum export, Earned Wall UI proof, grounding review after speech edits. | GSD or beginner-path suites become the evidence, or credit is uncited. |
| 6 - Public Claims | Package 10 and/or selected Package 11 collateral, kept as claim/content work. | Billing-source verification, cost/pricing tests, exact launch asset selection, generated-preview ignore check. | Cost claims are external without refreshed billing proof, or screenshot alternates/design audit ride along by accident. |
| 7 - Memory Live Gate | Package 12 near final source/Tauri proof. | Memory tests, model readiness, source/Tauri close proof, no stale sqlite-vec/CLAP shutdown failure. | Proof uses stale MCP children, missing local models, or old `.venv` dependency state. |
| 8 - Hold Conversion | Any hold lane only after a product decision turns it into active work. | The hold's named missing proof, plus red tests or live/runtime evidence before code moves. | The hold is merely interesting or plausible. Local MOSS TTS especially needs attribution, wrapper tests, install/model-cache proof, latency/bundle, and grounding proof. |
| 9 - Dependency Ring | One dependency modernization ring at a time. | Ecosystem audit/outdated/pip-check/cargo-tree evidence plus ring-specific tests/builds/live proof. | Any behavior, launch collateral, or structural refactor appears in the same staged diff. |
| 10 - Structural Refactor | One subsystem extraction after owning packages land. | Structural Refactor DoD row, focused tests, import/codegen/build gates, and live proof for runtime-sensitive movement. | The extraction starts because a file is large rather than because its package is settled and its contract is guarded. |

Card handoff shape:

```text
Card:
Package lane(s):
Files/hunks staged:
Evidence refreshed:
Generated artifacts:
Live proof:
Keep-outs:
Stop conditions checked:
Residual risk:
```

If a card needs evidence from another card, either promote the combined review
explicitly or narrow the claim. Do not let a future reviewer infer coupling from
the diff alone.

## Verification Registry

Use this registry to pick evidence by change type. The package checklist remains
the source of truth for exact focused suites; this table is the staging shortcut
so maintainers do not accidentally prove a broad claim with a narrow check.

| Change type | Evidence to collect | Notes |
|---|---|---|
| Any staging movement | `git status --short`, `git diff --shortstat`, `git ls-files --others --exclude-standard`, and `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary` | Run before and after staging. The package checker proves path assignment, not partial-hunk intent. |
| Shared-file staging | `git diff --cached -- <shared-path>` for each path in Shared-File Hunk Discipline | Required for `AGENTS.md`, `src/vibemix/__main__.py`, session loop, and IPC schema/generated files. |
| Package 0 planning ledger | `git diff --check` on planning docs, package checker, `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py`, and the focused `ruff check` | This is the only package that should move before product code when sessions pause. |
| IPC/schema/codegen | `uv run python scripts/check_ipc_schema.py`, IPC wiring checker, `npm --prefix tauri/ui run check:ipc`, focused IPC/UI-bus tests, and UI build when UI consumers change | Keep schema, Python wrappers, generated TS, validator, and parity tests together. |
| Python runtime/library behavior | Focused `uv run pytest -q ...` for touched subsystem plus `uv run ruff check ...` on changed files/tests | Add live/source-mode proof for runtime, audio, memory, or websocket claims. |
| Co-host speech or grounding | Focused Python tests plus `.claude/skills/vibemix-grounding-review/references/invariant-checks.md` | Required for `state/coach.py`, `agent/dj_cohost.py`, prompts, and event-detector wording paths. |
| UI behavior | Focused `npm --prefix tauri/ui test -- ...` plus `npm --prefix tauri/ui run build` | Add Playwright/screenshot proof for pill, visual, and interaction changes. |
| Mock-transfer or production visual anchors | `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts` | Any new `data-wire` anchor or event/channel must be contracted before mock visuals move into production. |
| Rust/Tauri shell or sidecar packaging | `cargo check --manifest-path tauri/src-tauri/Cargo.toml`, focused Cargo tests, and sidecar bundle readiness checks | Full `cargo tauri build` and signing are release-package gates, not routine proof. |
| Live runtime proof | `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix` or Tauri dev-source boot, client-only websocket probe, UI log, and session `events.jsonl` | Do not open a second websocket listener. Brain-mute evidence is repeated `citation_count:0` plus empty transcript deltas. |
| Cue/pill/Viber pipeline | Library/intel tests, pill unit/e2e/build, then live DDJ/Viber proof | Verify both `CuePoint.source` and semantic `CuePoint.number`; cue-review uncertainty must remain `CARE`-grade. |
| Learn/operator work | Targeted Learn/operator tests and curriculum export check | Keep GSD and Learn beginner-path suites out unless explicitly reopened. |
| Dependency hygiene | `uv pip check`, `uv pip list --outdated --format=json`, npm audit/outdated/ls, `cargo update --dry-run`, `cargo tree -d`, and ecosystem-specific gates | Dependency churn must be its own package, separated from product behavior and structural refactors. |

Do not treat a command as proof unless it covers the claimed behavior. For
example, unit tests can support cue-slot semantics, but live DDJ/Viber claims
need the runtime proof listed above.

## Evidence Bundle Template

Use this template when a package moves from mapped to staged or review-ready.
The goal is to make every future handoff auditable without re-reading the whole
dirty tree.

Required bundle fields:

- Package lane and intended commit subject.
- `git status --short`, `git diff --shortstat`, and package-checker summary
  before staging.
- Exact files staged, with shared-file hunk notes for any path listed in
  Shared-File Hunk Discipline.
- Focused commands run, with pass/fail result and enough output to identify the
  suite or subsystem.
- Generated artifacts changed, regenerated, or intentionally left untouched.
- Live proof artifacts when the claim touches runtime, UI socket, hardware,
  speech, cue/pill/Viber behavior, or Tauri GUI behavior.
- Explicit keep-outs: GSD, Learn beginner path, hold lanes, dependency churn,
  structural refactors, and any package lanes deliberately not included.
- Residual risk or missing evidence, written as a blocker when it blocks
  product-ready claims.
- `git diff --cached --check`, package-checker summary, and final cached diff
  review after staging.

Minimal review note shape:

```text
Package:
Commit:
Scope:
Staged files:
Shared-file hunks:
Checks:
Live proof:
Generated artifacts:
Keep-outs:
Residual risk:
```

If any field is "none", write why. Empty evidence fields are how accidental
scope creep hides.

## Live Proof Queue

Evidence refresh on 2026-05-31 11:29 +03:

- Current checklist status says live proof is partial. Source-mode and Tauri
  dev-source probes have reached `127.0.0.1:8765`, the renderer/Rust bridge/pill
  path, DDJ-FLX4 status, and BlackHole 16ch route/capture signals.
- Still pending before product-ready claims: audible deck-audio proof, a cited
  co-host moment, long controller-set pass, Tauri GUI evidence for IPC/UI
  interactions, and live DDJ/Viber proof for cue source/slot/CARE semantics.
- Use the `drive-vibemix` rule from `AGENTS.md`: attach as a client to the one
  `127.0.0.1:8765` socket, never start a second listener; inspect UI log and
  session `events.jsonl`; treat repeated `citation_count:0` plus empty transcript
  deltas as the brain-mute/slop signature.

Capture artifacts for every live proof:

- exact launch command and whether it was source-mode, Tauri dev-source, or
  packaged sidecar;
- `ws_probe.py` command/output or MCP websocket observation;
- relevant `ui.log` lines;
- session id and relevant `events.jsonl` excerpts;
- controller/audio device state (`DDJ-FLX4`, BlackHole 16ch, Rekordbox route)
  when hardware is part of the claim;
- screenshot or short recording for user-visible UI states;
- explicit pass/fail summary tied to the package lane.

| Proof lane | Unlocks | Current evidence | Still needed |
|---|---|---|---|
| Helper/tooling live path | Package 1 | Source-mode probes and `ws_probe.py --ipc` status/profile checks work; controller has been seen in some runs. | Prove helper path through UI log and session `events.jsonl` from the app runtime. |
| Tauri IPC GUI path | Packages 2 + 3 | Diagnostic bus proves sidecar handlers and schema-valid status/profile frames. | Tauri GUI pass for `ipc.status.recheck`, `ipc.error`, `ipc.session.citation`, Settings/Profile one-shot behavior, and Library staleness subscription behavior. |
| Cue/pill/Viber live pipeline | Packages 4 + 5 + 6 | Unit/e2e/build proof exists; live-read UI tests reject raw rejected deck-audio frames. | Live DDJ/Viber proof that `CuePoint.source`, semantic `CuePoint.number`, and `CARE` uncertainty survive ingest/cache -> next suggestion -> compact pill -> Viber/export/live-read. |
| Pill visual/runtime polish | Package 6 | Pill unit/e2e/build proof exists. | Optional visual pass in the live UI once sidecar is running. |
| Learn/operator credit | Packages 7, 8, 9, Learn producer hold | Targeted Learn tests and curriculum export proof exist for current slices. | Live practice loop must emit cited `BEATMATCH_GRADED` only from owned-deck judge evidence; Earned Wall needs live UI proof and grounding review after speech edits. |
| Runtime memory readiness | Package 12 | Memory tests and CLAP/model readiness are documented. | Keep final proof near Tauri/DDJ run because stale sqlite-vec state can invalidate source-mode validation. |
| TTS shutdown | Package 14 | Full live rerun with DDJ-FLX4, trigger, and Cartesia speech is documented. | Keep hunk discipline with `__main__.py`; no extra live gate unless shared hunks change. |
| Auto-master 16ch route | Package 15 | Tauri dev proof reached renderer/Rust bridge/pill path and recorded configured deck-pair capture. | Audible deck audio and a cited co-host moment before claiming musical grounding. |
| Controller-weighted deck audio | Deck Audio hold lane | Unit tests, Tauri/Rekordbox route observations, and honest unverified routing behavior are documented. | Full live deck-audio proof where controller posture changes audible master/citation context, not just synthesized arrays or silent routing. |
| Release-train final live pass | Completion audit | Current evidence proves pieces of runtime readiness. | Long controller set pass with audible route, cited co-host moment, no brain-mute signature, and documented UI/log/session artifacts. |

## Remaining Live Proof Burn-Down

This is the live-proof subset that still blocks product-ready or
maintainability-complete claims. Keep it separate from unit-test readiness:
package tests can make a lane reviewable, but only these artifacts prove the
runtime surfaces that have historically hidden failures.

| Burn-down item | Blocks | Current known state | Next evidence to capture | Abort or defer if |
|---|---|---|---|---|
| Package 1 helper path through real app logs | Tooling package ready-to-ship claim | Source-mode probes and IPC status/profile checks have worked, but the helper path still needs UI log plus session-event proof. | Launch current source, drive `ws_probe.py --ipc`, capture `ui.log` request/reply lines and matching `events.jsonl` session id. | The running process is a stale packaged sidecar or the socket owner is unknown. |
| Packages 2/3 Tauri IPC GUI pass | IPC bundle staging confidence | Schema/codegen/wiring checks pass, but GUI behavior for status/error/citation/settings/library subscriptions still needs proof. | Tauri dev-source run exercising `ipc.status.recheck`, `ipc.error`, `ipc.session.citation`, Settings/Profile one-shot behavior, and Library staleness subscription. | `npm --prefix tauri/ui run check:ipc` changes generated files unexpectedly after staging. |
| Packages 4/5/6 DDJ/Viber cue pipeline | Cue/pill/Viber product claims | Focused Python/UI tests and build proof exist; live DDJ/Viber cue source/slot/CARE behavior is still unproven. | Live route with DDJ + library/Viber path showing `CuePoint.source`, semantic `CuePoint.number`, and compact pill `CARE` uncertainty across ingest/cache -> suggestion -> pill -> Viber/export/live-read. | Deck audio route is silent, controller data is absent, or Viber uses ungrounded/raw track ids. |
| Package 9 Earned Wall live UI proof | Earned/Mastered user-visible claim | Backend progress emission tests exist; live UI refresh and grounding review remain the proof boundary. | Tauri/Learn run with cited skill-credit event, Earned Wall refresh visible, and grounding-review checklist re-read if wording changed. | Evidence source is uncited or the event comes from a non-owned deck path. |
| Package 12 final memory readiness proof | Durable source-mode validation | Memory tests and CLAP/model readiness are documented; stale sqlite-vec state previously blocked probes. | Final source-mode/Tauri proof after memory self-heal with session close showing no CLAP-memory shutdown failure. | The proof uses an old `.venv`, missing CLAP/CUE assets, or stale MCP helper children. |
| Package 13 release packaging proof | Signed/bundled artifact claim | Sidecar freshness guard passes; full release build/signing proof is separate. | `cargo tauri build` or release-package smoke, signed-app sidecar hash check, and bundle-size review when release owner opens packaging. | This is only a dev-source run; do not imply signed artifact freshness. |
| Package 15 audible auto-master proof | Musical grounding for 16ch route | Tauri source run reached BlackHole 16ch, controller positions, and grounded/cited co-host frames; audible deck proof remains the user-facing claim. | Long controller set with Deck A/B audible, no brain-mute signature, at least one cited co-host moment, and UI/log/session excerpts. | Rekordbox is not routed Deck 1 -> 1/2 and Deck 2 -> 3/4, or `deck_audio_activity` is unverified. |
| Deck Audio hold lane full controller-weighted proof | Future controller-weighted master context | Regression tests keep unverified routes honest-null; live controller posture was observed after route fix. | Controller moves changing captured deck/master context with cited co-host evidence and no overclaim of deck identity. | MIDI/HID/controller state is only port-present, not event-present. |
| Release-train long set | Completion/release readiness | Pieces are proven in separate runs; no single long pass proves the whole release train yet. | One longer source/Tauri run with audible route, controller motion, cited co-host, no repeated `citation_count:0` empty transcript deltas, and saved artifacts. | Any stale app owns `8765`, source and packaged sidecar hashes differ in the run, or runtime falls back to silent/idle evidence. |

Burn-down rule: when a live proof succeeds, paste the exact command, session id,
UI-log pointer, and `events.jsonl` excerpt into the package checklist before
loosening the corresponding readiness state. When it fails, record the failure
as evidence too; a failed live proof is useful if it prevents a false claim.

## Subsystem Boundary Map

Evidence refresh on 2026-05-31 11:24 +03:

- Source-like Python file counts: `src/vibemix/learn` 67, `library` 60,
  `state` 46, `runtime` 22, `platform` 20, `audio` 19, `midi` 18,
  `intel` 18, `agent` 16, `ui_bus` 11, and `debrief` 11.
- Source-like UI file counts: `tauri/ui/src/mascot` 51, `wizard` 44,
  `session` 36, `learn` 28, `debrief` 24, `settings` 21, `pill` 15,
  `shell` 14, `library` 12, and `ipc` 5.
- Rust shell density: `library_cmds.rs` 1890 lines, `sidecar.rs` 967,
  `tray.rs` 831, `config.rs` 525, `debrief_window.rs` 493,
  `pill_window.rs` 484, and `main.rs` 285.
- `tauri/ui/src/shell/surfaces.ts` defines five keep-alive shell surfaces:
  Deck, Crate, Learn, Debrief, and Settings. The comment explicitly says the
  floating pill, click-through overlay, and mascot are separate transparent
  windows, not shell surfaces.
- `scripts/integration_audit.py` still names five historical critical seams:
  EvidenceRegistry -> CitationLinter, GeminiContextCache -> DJCoHostAgent,
  RekordboxLibrary -> EvidenceRegistry, replay_harness -> eval gate, and mascot
  priority stack -> ws_bus.
- `src/vibemix/ui_bus/messages.py` documents the IPC source-of-truth rule:
  Python wrapper dataclasses must mirror exactly one schema `oneOf` entry, with
  count parity enforced by `scripts/check_ipc_schema.py`.
- `tauri/src-tauri/src/main.rs` is intentionally thin and delegates business
  logic to modules; keep it that way.

Boundary rules for future organization:

| Boundary | Owns | Must not absorb | Contract/gate |
|---|---|---|---|
| `library` / Crate / Viber | Rekordbox/XML/ANLZ ingest, search/similar, smart cues, live-read context, Viber tool contracts, cost/pricing helpers. | Runtime websocket plumbing, pill rendering, Learn lesson logic, launch collateral. | Library tests, Viber/tool invariants, Tauri `library_cmds`, library UI tests, and live-read proof. |
| `runtime` / Deck session | Session loop, websocket bus, live probes, sidecar-facing status, shutdown hygiene. | Long-lived library semantics, UI-only state, direct speech policy. | Runtime/session tests, IPC schema checks, source-mode or Tauri live proof. |
| `state` / grounding | MusicState-derived evidence, deck context, coach/progress state, spoken-claim guardrails. | Raw UI copy or ungrounded co-host phrasing. | State tests, grounding-review invariants, EvidenceRegistry/CitationLinter seam tests. |
| `audio` + `midi` + `platform` | Hardware capture, deck routing, controller posture, macOS device selection. | Viber decisions, Learn credit claims without cited judge evidence. | Audio/midi/platform tests and live controller/audio proof. |
| `intel` | Move grading, transition scoring, CARE/uncertainty semantics. | Presentation-specific pill copy or ingest persistence. | Intel/library tests plus pill tests when labels or risk states change. |
| `learn` | Curriculum, operator actions, skill credit, Earned Wall, practice judge. | GSD and beginner-path suites unless explicitly reopened; cue/Viber feature work. | Targeted Learn/operator tests, curriculum export check, live judge proof for Course 3 claims. |
| `ui_bus` + `tauri/ui/src/ipc` | IPC schema, Python wrappers, generated TS, validator, parity tests. | Business behavior not represented by producers and consumers. | `check_ipc_schema.py`, IPC wiring checker, `check:ipc`, UI-bus tests. |
| UI shell surfaces | Deck, Crate, Learn, Debrief, Settings keep-alive regions and their `data-wire` anchors. | Floating pill, overlay, and mascot window behavior. | Mock-transfer contract, surface tests, UI build. |
| Floating UI windows | Pill, overlay, mascot window, their visual/runtime contracts. | Shell route state or library/chat semantics. | Focused UI tests, Playwright/screenshot/canvas proof, UI build. |
| Tauri shell modules | Sidecar launch, Rust command bridge, tray/window/config/updater/hotkey glue. | Python business logic or UI render state. | Cargo check/tests, sidecar bundle readiness, Tauri dev-source smoke. |

First safe organizing moves after package lanes land:

- Split command/adapters from core behavior before splitting domain logic:
  `library_cmds.rs`, `library/api.ts`, and CLI command handlers are better first
  seams than evidence or scoring internals.
- Keep contract files together: IPC schema/codegen, mock-transfer anchors, Tauri
  command allowlists, and Python wrapper dataclasses move as bundles.
- Prefer clean large files for early refactors (`codex_curate.py`,
  `dj_cohost.py`, `library_cmds.rs`, `runtime/suggestion.py`) only after their
  listed grounding or contract gates are fresh.
- Do not move hardware/audio/controller code into library, Learn, or UI packages;
  pass only summarized evidence across boundaries.
- Do not let UI copy become the source of truth for cue confidence. The
  `move_grade`/library evidence path must decide whether a cue is earned,
  reviewed, or `CARE`.

## Orphan And Dead-Surface Triage

Evidence refresh on 2026-05-31 11:23 +03:

- `uv run python scripts/integration_audit.py --orphan-inventory` reported 57
  top-level symbols with no static production caller and no direct test import:
  33 classes and 24 functions.
- Grouping those rows by package gives: `src/vibemix/library` 20,
  `src/vibemix/intel` 14, `src/vibemix/runtime` 7, `src/vibemix/state` 5,
  `src/vibemix/learn` 5, `src/vibemix/debrief` 2, `src/vibemix/bench` 2,
  `src/vibemix/platform` 1, and `src/vibemix/audio` 1.
- Representative flagged symbols include `DecisionModel`,
  `RuntimeDecisionResult`, `validate_and_degrade`, `MoveGrade`, `SmartCue`,
  `SmartCuePolicy`, `CoursePackDraft`, `LiveTimingHint`, `DeckAudioFrame`,
  library doctor `check_*` functions, and dev-MCP `default_*_root` helpers.
- A duplicate-basename scan across 681 source-like files found common names such
  as `index.ts`, `router.ts`, `state.ts`, `ws-client.ts`, `settings.py`,
  `registry.py`, `profile.py`, `coach.py`, `ingest.py`, and `matrix.py`. These
  are not wrong, but they increase navigation ambiguity during refactors.
- A text scan for TODO/FIXME/HACK/XXX/dead/orphan language is mostly explanatory
  comments around already-fixed dead controls and lifecycle hazards, not an
  immediate deletion list. Notable current clusters are live/session comments,
  Tauri tray `dead_code` allowance, and dev-MCP dead-control docs.

Triage rules:

- Treat orphan inventory as a prompt for review, not proof of unused code.
  Dataclasses, command payloads, CLI helpers, doctor checks, public exports, and
  dynamic tool entry points are expected false positives in this repo.
- Never remove an orphan-flagged symbol from a dirty active package until that
  package lands and its verification gates are fresh.
- First triage wave should be read-only classification:
  public/dynamic API, test fixture/support, generated/contract surface,
  active-package code, or likely removable.
- A likely-removable symbol needs stronger evidence before deletion:
  `rg` for name/string use, codegraph caller/callee check where available,
  focused tests, import smoke, and live/source proof if runtime-facing.
- Prefer adding a narrow test or comment for an intentionally dynamic symbol over
  leaving it as a recurring orphan false positive.
- Avoid introducing new generic basenames in broad areas. If a file is not the
  primary package entry point, prefer descriptive names such as
  `session_ws_client.ts`, `library_state.ts`, or `deck_audio_state.py` over
  another `state.ts`, `registry.py`, or `ws-client.ts`.

First cleanup candidates after active packages land:

| Candidate group | Why it needs triage | First evidence |
|---|---|---|
| `src/vibemix/intel/*decision*`, gold, claim, ontology symbols | Many clean intel classes/functions appear as static orphans; some may be framework inputs or future scoring hooks. | `rg` symbol scan, intel tests, move-grade/transition tests, and any prompt/runtime caller check. |
| `src/vibemix/library/doctor.py` `check_*` helpers | Doctor commands are often invoked dynamically from CLI/tooling, so static orphan status may be false. | CLI command path check, library doctor tests or import smoke, and docs/reference search. |
| `src/vibemix/library/smart_cues.py` proposal classes | Currently tied to cue/pill/Viber semantics; do not touch until Packages 4-6 settle. | Smart-cue tests, next-suggestion tests, Viber/export proof. |
| `src/vibemix/runtime/suggestion.py` timing dataclasses | Runtime suggestion flow is clean but large; static orphan status may mean internal refactor opportunity. | Runtime suggestion tests, pill/next-suggestion tests, source-mode proof if behavior changes. |
| Duplicate generic basenames | Not broken, but they slow navigation and raise wrong-file edit risk. | Rename only during local refactor packages with import/codegen/build gates. |

## Architecture Density Findings

Current file-density evidence from source-like files only (`*.py`, `*.ts`,
`*.tsx`, `*.css`, `*.rs`, `*.json`) on 2026-05-31 11:16 +03:

- Largest implementation file: `src/vibemix/__main__.py` at 6007 lines. It is
  currently dirty and shared by live audio boot, budget CLI, and shutdown work.
- Largest UI surface: `tauri/ui/src/pill/pill.css` at 4101 lines, followed by
  `tauri/ui/src/pill/index.ts` at 2736 lines and `tauri/ui/src/library/api.ts`
  at 2595 lines.
- Local-TTS drift is currently reduced to a residual `uv.lock` diff for
  `sentencepiece` / `tts-local`. The earlier `pyproject.toml`,
  `local_tts.py`, vendored `moss_tts`, `tts_chain.py`, and focused test files
  are no longer dirty in the live tree, so treat their red-test evidence as
  historical context rather than current proof. Do not stage the residual
  lockfile hunk without either restoring the full local-TTS package or removing
  the stale dependency change.
- Largest clean Python refactor candidate: `src/vibemix/library/codex_curate.py`
  at 3888 lines. Because it is clean, it is a better later extraction target than
  dirty runtime files.
- Highest source-like file-count areas in Python are `src/vibemix/learn`
  (67 files), `src/vibemix/library` (60), `src/vibemix/state` (46),
  `src/vibemix/runtime` (22), `src/vibemix/platform` (20), and
  `src/vibemix/audio` (19). Treat these as subsystem packages, not a single
  cleanup bucket.
- Highest source-like file-count UI areas are `tauri/ui/src/mascot` (51 files),
  `tauri/ui/src/wizard` (44), `tauri/ui/src/session` (36),
  `tauri/ui/src/learn` (28), `tauri/ui/src/debrief` (24),
  `tauri/ui/src/settings` (21), `tauri/ui/src/pill` (15), and
  `tauri/ui/src/library` (12).
- Current dirty source distribution is concentrated in settings, pill, ui-bus,
  library, Learn, session, IPC, runtime, audio, and one-file touches in state,
  platform, midi, memory, LLM, intel, and `__main__.py`. That argues for waiting
  until the dirty feature packages land before structural movement in those areas.
- TODO/FIXME/HACK/XXX scan is modest but clustered: `src/vibemix/library/clap_engine.py`
  has 5 hits, `tauri/ui/src/settings/components/help-group.ts` has 4, and
  `tauri/ui/src/session/render-loop.ts` has 3. Treat these as triage targets
  after the package lanes settle, not as automatic refactor scope.

Implication: first reduce review risk by landing coherent product packages, then
refactor the large clean or freshly settled files. Do not start by splitting the
largest dirty files just because they are large.

## Clean Refactor Candidate Map

These targets are currently clean, so they are better later maintainability
packages than dirty shared runtime files. Each still needs its own behavior gate.

| Candidate | Evidence | Why later, not now | First gate |
|---|---:|---|---|
| `src/vibemix/library/codex_curate.py` | 3888 clean lines | Large and central to Viber/library tooling; avoid while cue/pill/Viber packages are active. | Library curate, stop-reason, live-context, and CLI exit-code tests. |
| `src/vibemix/agent/dj_cohost.py` | 3206 clean lines | Speech behavior is high risk even when clean. | Grounding-review invariants plus co-host/prompt tests. |
| `tauri/ui/src/library/library.css` | 1926 clean lines | Visual density cleanup should follow accepted library UI direction. | Library UI tests, build, and screenshot proof. |
| `tauri/src-tauri/src/library_cmds.rs` | 1890 clean lines | Rust command surface should wait until library/Viber contracts settle. | Cargo check and focused library command tests. |
| `src/vibemix/runtime/suggestion.py` | 1813 clean lines | Suggestion flow interacts with pill/cue uncertainty semantics. | Suggestion and next-suggestion tests with CARE cases. |
| `src/vibemix/learn/runtime.py` | 1798 clean lines | Learn work must stay outside GSD and beginner paths unless explicitly reopened. | Targeted Learn operator/action tests only. |
| `src/vibemix/library/toolset.py` | 1674 clean lines | Tool spine is security/grounding-sensitive. | Viber/library tool contract tests and web/fetch invariants. |

## Refactor Entry Criteria

Start refactoring only when these gates are true:

- Package checker is green on the live tree immediately before the refactor.
- The file being refactored is either clean or its owning product package has
  landed/staged as a coherent unit.
- The relevant subsystem has focused tests that can fail for behavior, not just
  formatting.
- The refactor can preserve the public contract at the current boundary:
  `vibemix.__main__:main()`, IPC schema/codegen, Viber/library tool contract,
  cue/pill uncertainty semantics, or Tauri command signatures.
- Dependency upgrades are not in the same branch/commit as structural movement.

Refactor exit criteria:

- Public entry points and generated contracts remain byte/shape compatible unless
  the package explicitly changes them.
- Old and new module paths are covered by focused tests or import smoke tests.
- Runtime-sensitive refactors include the matching live or source-mode proof
  listed in the package checklist.
- The package checker is green again after the refactor.

## Structural Refactor DoD By Subsystem

This is the maintainability definition of done for future organizing commits.
Use it after the active package lanes land; it is not permission to start
refactors while the tree is still moving.

Evidence refresh on 2026-05-31 after the local MOSS TTS hold appeared:

- Codegraph still identifies the stable entry points as
  `src/vibemix/__main__.py:main`, `tauri/src-tauri/src/main.rs:main`, and the
  Rust spike entry point. Preserve those boundaries unless a package explicitly
  changes them.
- File-density evidence still points to `src/vibemix/__main__.py` at 6007
  lines, `tauri/ui/src/pill/pill.css` at 4101, `src/vibemix/library/codex_curate.py`
  at 3888, `src/vibemix/state/deck_context.py` at 3279,
  `tauri/ui/src/pill/index.ts` at 2736, `tauri/ui/src/library/api.ts` at 2595,
  and `tauri/src-tauri/src/library_cmds.rs` at 1890.
- Dirty churn is currently led by `tauri/ui/src/library/chat.test.ts`
  (`435 / 77`), `tauri/ui/src/library/api.ts` (`408 / 52`),
  `tauri/ui/src/library/api.test.ts` (`433 / 4`),
  `tauri/ui/src/ipc/messages.schema.json` (`1 / 414`),
  `tauri/ui/src/library/index.ts` (`298 / 105`), and
  `src/vibemix/library/ingest.py` (`177 / 31`). Do not use line count alone to
  choose the first refactor.

| Subsystem | Start only after | Preserve | Evidence required | Stop condition |
|---|---|---|---|---|
| CLI/runtime entrypoint | Packages 10, 14, Deck Audio hold hunks in `__main__.py` are staged or deliberately combined. | `vibemix.__main__:main()`, `cli_entry()`, model-router resolution, shutdown behavior, and live source-mode boot. | `tests/test_main_smoke.py`, focused CLI/library/budget tests, model-literal scan, and source-mode or Tauri proof for runtime hunks. | Any refactor requires whole-file staging of mixed budget/TTS/audio hunks. |
| IPC contracts | Packages 2 and 3 are reviewed as a complete IPC bundle. | 72-count schema/wrapper parity unless deliberately changed; generated TS and validator stay in sync. | `uv run python scripts/check_ipc_schema.py`, IPC wiring checker, `npm --prefix tauri/ui run check:ipc`, UI-bus tests, and UI build when consumers move. | Schema, generated files, Python wrappers, or Rust/TS consumers would land separately. |
| Cue/pill/Viber pipeline | Packages 4, 5, and 6 land or are explicitly reviewed as one product pipeline. | `CuePoint.source`, semantic `CuePoint.number`, compact pill `CARE` uncertainty, and grounded Viber tool spine. | Library/intel tests, pill unit/e2e/build, Viber/live-read tests, and live DDJ/Viber proof before product claims. | A UI refactor hides cue-review uncertainty or turns live-read rejection into optimistic copy. |
| Library API and Viber tooling | Library UI live-read changes and cue/Viber packages settle. | Search/discover/fetch/create/export tool contracts, stop reasons, path scrubbing, and Codex-local backend boundary. | `src/library/api.test.ts`, `src/library/chat.test.ts`, library Python tests, Viber tool contract tests, and CLI smoke. | A refactor mixes API normalization with tool security or backend-routing changes. |
| Audio, MIDI, and deck context | Package 15 lands and Deck Audio hold lane either lands with live proof or stays out. | Live audio remains authoritative; unverified deck-pair routes stay honest-null; deck identity is not overclaimed. | Audio/midi/state tests, `tests/state/test_deck_context.py`, live controller/audio proof, and grounding-review if speech text changes. | Controller evidence is only port-present, or deck-audio activity is unverified. |
| Co-host speech and grounding | Any speech-affecting package has grounding-review notes. | EvidenceRegistry resolution, citation fallback, negative-dict filtering, and no hardcoded model names. | Grounding-review invariant checklist, co-host/prompt/filter tests, and live cited co-host proof for runtime claims. | The change can produce spoken claims without cited evidence or with generic optimistic language. |
| Learn/Earned UI | Packages 7 and 9 settle; Package 8 and Learn producer hold are intentionally included or kept out. | GSD and beginner-path suites stay excluded unless reopened; Earned/Mastered state is cited. | Targeted Learn/operator tests, curriculum export check, Earned Wall UI proof, and cited judge event proof. | Evidence comes from non-owned deck behavior or uncited credit. |
| Tauri shell and packaging | IPC, sidecar freshness, and runtime source proof are fresh. | Rust command signatures, sidecar launch contract, one-socket rule, and signed-artifact distinction. | `cargo check`, focused Cargo tests, sidecar bundle readiness, Tauri dev-source smoke, and release build/signing only when packaging opens. | A dev-source proof is used to claim signed-app freshness. |
| Local TTS / vendor runtimes | Local MOSS TTS hold lane gets attribution, passing/extended wrapper tests, dependency install proof, and model-cache flow. | Vendored runtime stays upstream-syncable; live TTS chain remains opt-in, config-driven, and closable. | NOTICE/docs, focused local-TTS tests, import smoke with missing-model/dependency behavior, provider/sample-mode tests, `uv sync`/install proof for `tts-local` and `ai-local`, latency/bundle measurement, grounding-review before live speech. | The vendored file is refactored directly or the opt-in path is marketed as ready without attribution, dependency, and runtime proof. |
| Dependency modernization | Active feature/refactor packages are paused or cleanly staged. | Dependency-only commits; SQLCipher omission remains a named exception; Three/Vite/TS/protobuf/websockets move in rings. | Ecosystem audit/outdated/pip-check/cargo-tree evidence plus ring-specific tests/builds/live proof. | Dependency churn shares a commit with product behavior or structural refactors. |

## Refactor Backlog

## Extraction Work Orders

These are future work orders, not permission to refactor while dirty feature
packages are still moving.

| Target | Current evidence | First extraction seam | Gates |
|---|---|---|---|
| `src/vibemix/__main__.py` | 6007 lines; 88 top-level definitions. Shape scan: 18 pre-main helpers, 2 runtime-main-region definitions, 68 CLI-tail definitions after the library/bench parser area. | Move parser/subparser and command handlers out first, then audio boot/device selection, then shutdown helpers. Keep `vibemix.__main__:main()` and `cli_entry()` stable. | `tests/test_main_smoke.py`, library CLI tests, budget/pricing tests, model-literal scan, and live/source-mode proof for audio/runtime hunks. |
| `src/vibemix/library/codex_curate.py` | 3888 lines; 99 definitions. Shape scan: 15 curate/core definitions, 2 set-prep definitions, 82 chat/live-context definitions. | Preserve public exports, then split tool-tape/subprocess guards, set-prep, chat result normalization, live-context normalization, and live-claim verification. | `tests/library/test_codex_curate.py`, `tests/library/test_codex_curate_stop_reason.py`, `tests/library/test_live_context_cli.py`, CLI exit-code tests, and Viber/library live-read tests. |
| `tauri/ui/src/pill/index.ts` | 2736 lines; 166 function/type/const definitions. Shape scan: model/reducer, demo controls, state/focus helpers, render/reaction FX, boot/IPC. | Extract demo controls and reaction FX first because they are visually bounded; keep reducer/frame parsing and next-suggestion state until Package 4/6 settle. | `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`, pill Playwright, and UI build. |
| `tauri/ui/src/pill/next-suggestion.ts` | 1311 lines; 43 exported/internal definitions. It owns next-suggestion wire/view normalization and rendering. | Split pure view-model/label helpers from DOM rendering after cue/pill/Viber pipeline proof. | Same pill unit/e2e gates; verify `CARE` uncertainty remains visible. |
| `tauri/ui/src/library/api.ts` | 2595 lines; 149 definitions. It mixes schema normalizers, live-context evidence derivation, command wrappers, dev fallbacks, and Tauri event listeners. | Extract live-context normalization/evidence helpers first, then command wrappers, then dev fixtures/listeners. Keep exported API names stable. | `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`, build, and live-read proof. |
| `src/vibemix/state/deck_context.py` | 3247 lines; 121 definitions. It mixes context text normalizers, renderers, audio-token extraction, live evidence, and claim policy. | Split only after deck-audio hold lane settles: normalizers, deck-audio token helpers, live evidence renderers, and claim policy. | `tests/state/test_deck_context.py`, coach/runtime grounding tests, and grounding-review invariants before speech-affecting changes. |
| `src/vibemix/ui_bus/messages.py` | 1960 lines; 109 helper/dataclass definitions. It is an IPC contract file, not ordinary application logic. | Do not split casually. Later option: generate or group payload/wrapper definitions only if schema/codegen/count parity remains one-command reproducible. | `uv run python scripts/check_ipc_schema.py`, IPC wiring checker, UI `check:ipc`, and UI-bus schema tests. |

### CLI And Runtime Entrypoint

Target: `src/vibemix/__main__.py`.

Proposed shape:

- `vibemix.cli.parser`: argument/subparser construction.
- `vibemix.cli.library_commands`: library command handlers.
- `vibemix.cli.budget_commands`: budget/pricing command handlers.
- `vibemix.runtime.live_main`: live co-host orchestration.
- `vibemix.runtime.audio_boot`: device selection, deck audio routing, stream open.

Exit criteria:

- `vibemix.__main__:main()` remains the orchestration entry point.
- Existing smoke tests and CLI tests pass.
- No hardcoded model names are introduced.

### Library Curation

Target: `src/vibemix/library/codex_curate.py`.

Proposed shape:

- separate artifact parsing,
- MCP/tool invocation adapter,
- playlist/export orchestration,
- terminal/Telegram presentation.

Exit criteria:

- Viber/library tool spine remains grounded: `fetch_url` only reads URLs from a
  same-run `web_search`; empty pages error; non-finite scores degrade to `0.0`.

### Grounding And Deck Context

Targets: `src/vibemix/state/deck_context.py`, `src/vibemix/agent/dj_cohost.py`,
`src/vibemix/runtime/coach.py`.

Proposed shape:

- isolate evidence sanitizers,
- isolate deck-audio context renderers,
- isolate historical spoken-claim cleanup,
- keep co-host wording changes behind grounding-review checks.

Exit criteria:

- No new spoken claim path bypasses `EvidenceRegistry` or grounding validation.
- Deck audio remains authoritative when live audio exists.

### UI Surfaces

Targets: pill and library UI.

Proposed shape:

- split pill state machine, rendering, controls, and CSS tokens.
- split library API live-context merge, command bridge, and chat artifact shaping.
- keep mock-transfer `data-wire` contracts synchronized before moving mock visuals
  into production UI.

Exit criteria:

- Existing pill unit tests and Playwright e2e pass.
- `npm --prefix tauri/ui run build` passes.
- No UI text hides cue uncertainty as earned certainty.

## Dependency Hygiene Plan

Python:

- Add a repo-aware dependency health check that treats the pyrekordbox SQLCipher
  omission as an expected exception with an explicit reason.
- Upgrade groups only in dedicated dependency PRs:
  AI/runtime SDKs (`google-genai` 2.0.1 -> 2.7.0, `openai` 2.36.0 -> 2.38.0,
  LiveKit packages 1.5.14 -> 1.5.15 / protocol 1.1.8 -> 1.1.11, `mcp`
  1.27.1 -> 1.27.2), telemetry (`opentelemetry-*` 1.39.1 -> 1.42.1),
  audio/model-adjacent binaries (`numpy` 2.4.4 -> 2.4.6, `tokenizers`
  0.22.2 -> 0.23.1, PyObjC 12.1 -> 12.2), and major-boundary packages
  (`protobuf` 6.33.6 -> 7.35.0, `websockets` 15.0.1 -> 16.0).
- Targeted gates: `uv pip check`, model readiness, memory ingest tests, live
  source-mode boot, and at least one co-host/status websocket probe.

Node:

- First handle the dev audit by upgrading Vitest and its nested Vite/esbuild path.
- Then consider Vite 8 and TypeScript 6 as separate major-version migrations.
- Keep Three upgrades visual-test gated.
- `tmp` is a dev-only high finding through `@gltf-transform/cli`; handle it in
  the same UI tooling audit package or pin/replace the transitive path with proof.
- Targeted gates: UI unit tests, pill Playwright, mock-transfer contract, and
  `npm --prefix tauri/ui run build`.

Rust:

- Start with the compatible Cargo patch refresh.
- Then investigate the direct `core-graphics` duplicate only if `cargo check` and
  Tauri shell tests stay green.
- Targeted gates: `cargo check --manifest-path tauri/src-tauri/Cargo.toml`,
  launch-decision tests, and sidecar bundle freshness checks.

## Dependency Modernization Rings

Run these as separate dependency-only packages after the active feature lanes
quiet down. Do not combine any ring with product behavior, launch collateral, or
structural refactors.

| Ring | Scope | Why this order | Gates |
|---|---|---|---|
| 0 - Health-check exception | Keep the `pyrekordbox` / `sqlcipher3-wheels` omission explicit and repo-aware. | `uv pip check` is currently noisy only because SQLCipher is intentionally excluded; make future checks fail on new incompatibilities without re-adding the dormant DB6 blob. | `uv pip check`, `tests/library/test_pyrekordbox_install.py`, sidecar bundle readiness, and package size review. |
| 1 - Python patch/minor SDKs | LiveKit 1.5.15 / protocol 1.1.11, `mcp` 1.27.2, `openai` 2.38.0, `google-genai` 2.7.0, plus adjacent small patch updates. | These are capability/runtime packages but mostly patch/minor; they should move before major protocol boundaries so model/router behavior can be isolated. | `tests/llm/test_model_router.py`, pricing/cost tests, memory ingest tests, source-mode boot, and a websocket status probe. |
| 2 - Python telemetry and binaries | `opentelemetry-*` 1.42.1, PyObjC 12.2, `numpy` 2.4.6, `tokenizers` 0.23.1. | Telemetry and binary/model-adjacent wheels can affect startup, bundle weight, and local CLAP readiness; keep them out of AI SDK changes. | `uv pip check`, CLAP/model readiness tests, memory tests, sidecar build smoke, and live source-mode boot. |
| 3 - Python major-boundary protocols | `protobuf` 7.35.0 and `websockets` 16.0. | These can affect LiveKit, generated protocol surfaces, and websocket runtime behavior; keep as explicit migrations. | IPC/schema tests, runtime websocket/session tests, LiveKit/status probe, and source-mode bus proof. |
| 4 - UI dev audit | Vitest 4.1.7 and its nested Vite/esbuild audit path; separately decide whether `@gltf-transform/cli` is still needed or can be removed/pinned to clear `tmp`. | Production audit is already clean; this ring removes dev-audit noise without changing app runtime behavior. | `npm --prefix tauri/ui audit --json`, full UI unit suites, mock-transfer contract, pill Playwright, and UI build. |
| 5 - UI platform majors | Vite 8, TypeScript 6, and `vite-plugin-static-copy` 4. | These can change build semantics and typechecking, so they should follow the Vitest audit ring and stay separate from product UI work. | UI build, IPC codegen/checks, settings/session/library/pill focused tests, and Tauri dev-source smoke. |
| 6 - Mascot/Three visual stack | Three 0.184 and `@types/three` 0.184. | Three is runtime visual code concentrated in mascot surfaces; move only with canvas/screenshot proof. | Mascot unit tests, GLB bundle/build gates, UI build, and screenshot or canvas-pixel proof. |
| 7 - Rust compatible lock refresh | Cargo dry-run's 47 compatible updates, including Tauri 2.11.2. | Compatible lock refresh is the lowest-risk Rust step, but it still touches the desktop shell and updater stack. | `cargo check --manifest-path tauri/src-tauri/Cargo.toml`, focused Cargo tests, launch-decision tests, and sidecar bundle readiness. |
| 8 - Rust duplicate cleanup | Investigate direct `core-graphics` 0.24 -> 0.25 and release `devtools` feature gating/removal. | These are not simple lockfile refreshes; they touch macOS window capture/debug posture and need release hardening proof. | `cargo tree -d`, `cargo check`, djay AX/window-capture tests, Tauri dev-source boot, and release-package smoke. |

## Dependency Opportunity Matrix

These are future dependency packages, not edits to make while the feature tree is
dirty.

| Area | Evidence | Opportunity | Gates |
|---|---|---|---|
| Python SQLCipher omission | `uv pip check` reports only `pyrekordbox` -> `sqlcipher3-wheels`; `pyproject.toml` documents the never-real-platform override and dormant DB6 path. | Keep the omission. Add a repo-aware dependency health check so `uv pip check` can fail on new issues while allowing this one named exception. | `uv pip check`, pyrekordbox dormancy tests, sidecar bundle size/leak gates. |
| Python AI/runtime SDKs | `uv pip list --outdated --format=json` shows `google-genai`, `openai`, LiveKit, `mcp`, `protobuf`, and `websockets` behind current releases. | Upgrade in rings: first patch/minor LiveKit/MCP/OpenAI/Google SDKs, then protocol boundary packages, then major-boundary `protobuf`/`websockets`. Keep model names routed through `model_router`. | Model-router tests, cost/pricing tests, live source-mode boot, `ws_probe.py` status check, sidecar bundle smoke. |
| UI dev audit | Prod audit is clean; dev audit has Vitest/Vite/esbuild moderate findings plus high `tmp`. `npm outdated` says Vitest major upgrade is the audit fix path. | Make a dedicated UI tooling audit package: Vitest 4 first, then Vite 8 and TypeScript 6 separately. Do not combine with pill/library UI behavior changes. | UI unit suites, mock-transfer contract, pill Playwright, `npm --prefix tauri/ui run build`. |
| GLB tooling | `tauri/ui/scripts/build-mascot-bundle.mjs` imports `@gltf-transform/core` and shells to `gltf-pipeline`; `@gltf-transform/cli` is documented but no current exact CLI invocation appeared in the source scan outside package metadata/docs. `npm --prefix tauri/ui explain tmp --json` confirms `tmp` 0.2.5 is pulled by `@gltf-transform/cli` 4.3.0. | Verify whether `@gltf-transform/cli` is still needed as a direct devDependency. If only historical, remove or move it to a local asset-production recipe; if kept, document the invoking command. This directly addresses the `tmp` audit path. | `npm audit --json`, mascot bundle build, mascot GLB size gates, mascot render tests. |
| Three runtime | Direct runtime dependency; source imports are concentrated under `tauri/ui/src/mascot/*` plus mascot tests. | Upgrade Three only with mascot-specific visual/canvas proof. It should not travel with session, pill, library, or IPC packages. | Mascot unit tests, chrome/visual tests, UI build, Tauri screenshot/canvas check if runtime visuals changed. |
| Rust patch refresh | `cargo update --dry-run` lists 47 compatible updates including Tauri 2.11.2; `cargo tree -d` shows direct `core-graphics` 0.24 beside Tauri/Tao 0.25. | First refresh compatible lockfile updates. Later test whether direct `core-graphics` can move to 0.25 without breaking `djay_ax` / overlay behavior. | `cargo check`, focused Tauri tests, `cargo tree -d`, sidecar bundle readiness. |
| Tauri devtools feature | `tauri/src-tauri/Cargo.toml` still enables Tauri `devtools` with a comment calling it temporary for mascot render debug. | Investigate gating or removing release devtools support in a release-hardening package. Keep it separate from dependency version bumps. | `cargo check`, Tauri dev-source boot, release/package smoke, operator-debug fallback note. |

## Dependency Execution Audit

Evidence refresh on 2026-05-31 12:29 +03:

- `uv pip check` still reports exactly one incompatibility: `pyrekordbox`
  requires `sqlcipher3-wheels`, which remains the named repo exception because
  DB6/SQLCipher is dormant and XML/ANLZ ingest is the active path.
- `uv pip list --outdated --format=json` still reports 50 outdated Python
  packages. Representative upgrade edges: `google-genai` 2.0.1 -> 2.7.0,
  `openai` 2.36.0 -> 2.38.0, `livekit-agents` 1.5.14 -> 1.5.15,
  `livekit-protocol` 1.1.8 -> 1.1.11, `mcp` 1.27.1 -> 1.27.2,
  `numpy` 2.4.4 -> 2.4.6, `tokenizers` 0.22.2 -> 0.23.1,
  `protobuf` 6.33.6 -> 7.35.0, and `websockets` 15.0.1 -> 16.0.
- `npm --prefix tauri/ui audit --omit=dev --json` remains production-clean
  with 0 findings.
- `npm --prefix tauri/ui audit --json` still reports 6 dev findings: 5
  moderate findings through Vitest's nested Vite/esbuild path and 1 high
  `tmp` finding.
- `npm --prefix tauri/ui outdated --json` still shows direct major lanes:
  Vitest 2.1.9 -> 4.1.7, Vite 6.4.2 -> 8.0.14, TypeScript 5.9.3 -> 6.0.3,
  Three 0.170.0 -> 0.184.0, `@types/three` 0.170.0 -> 0.184.1, and
  `vite-plugin-static-copy` 2.3.2 -> 4.1.0.
- `npm --prefix tauri/ui ls --depth=0` resolves direct UI dependencies without
  missing/peer errors; `npm --prefix tauri/ui explain tmp --json` confirms
  `tmp` 0.2.5 is pulled by `@gltf-transform/cli` 4.3.0, which is still
  installed as a direct devDependency.
- `cargo update --manifest-path tauri/src-tauri/Cargo.toml --dry-run` still
  reports 47 compatible Rust updates, including Tauri 2.11.1 -> 2.11.2,
  `global-hotkey` 0.7.0 -> 0.8.0, and `tao` 0.35.2 -> 0.35.3. The lockfile was
  not updated.
- `cargo tree --manifest-path tauri/src-tauri/Cargo.toml -d` still shows
  transitive duplicate families; the repo-owned direct duplicate to plan around
  is `core-graphics` 0.24.0 in `vibemix` beside `core-graphics` 0.25.0 through
  Tauri/Tao.

Dependency package order:

1. Health-check exception package: add/refresh a repo-aware dependency check
   that allows only the `pyrekordbox` SQLCipher omission and fails on any new
   Python incompatibility.
2. Python patch/minor runtime SDK package: LiveKit/MCP/OpenAI/Google GenAI and
   adjacent small packages. Keep `protobuf` and `websockets` out of this pass.
3. Python binary/telemetry package: OTel, PyObjC, `numpy`, and `tokenizers`,
   with CLAP/model readiness and sidecar bundle proof.
4. Python protocol-major package: `protobuf` 7 and `websockets` 16, gated by
   IPC/session/websocket proof.
5. UI dev-audit package: Vitest 4 first, and decide whether
   `@gltf-transform/cli` is still needed or should move to an asset-production
   recipe to clear the `tmp` path.
6. UI platform-major package: Vite 8, TypeScript 6, and
   `vite-plugin-static-copy` 4 after the Vitest ring.
7. Visual-stack package: Three and `@types/three`, only with mascot/canvas or
   screenshot proof.
8. Rust compatible-lock package: Cargo's 47 compatible updates with shell and
   sidecar gates.
9. Rust release-hardening package: direct `core-graphics` alignment and
   `devtools` feature decision, kept separate from the compatible lock refresh.

Dependency abort rules:

- Do not combine dependency changes with active feature packages, launch
  collateral, or structural refactors.
- Do not present `npm audit --omit=dev` as proof that dev tooling is clean; the
  full dev audit still has 6 findings.
- Do not add SQLCipher just to silence `uv pip check` without reopening bundle
  size, DB6, and Rekordbox XML-only product decisions.
- Do not upgrade Three without a visual/canvas proof packet.
- Do not treat Cargo `--dry-run` as a lockfile refresh; it is only evidence of
  available compatible updates until `Cargo.lock` is intentionally changed.

## Keep-Outs Until Explicitly Requested

- Do not run GSD.
- Do not run Learn beginner-path suites.
- Do not refactor `dj_cohost.py` without grounding-review invariants.
- Do not mix launch collateral screenshots with premium enterprise design hold
  artifacts.
- Do not mix dependency upgrades with active product feature packages.

## Next Evidence To Gather

- A fresh package-checker run after any other session stages/unstages work.
- Refresh the package footprint snapshot immediately before staging begins,
  because shared files such as `src/vibemix/__main__.py` and IPC generated
  artifacts can move under parallel sessions.
- Before any non-doc staging, inspect cached diffs for every path in
  "Shared-File Hunk Discipline" so shared files do not drag unrelated package
  hunks across commit boundaries.
- Full live deck-audio proof for controller-weighted master context.
- Full live cue/pill/Viber proof after cue pipeline packages settle.
- Dependency upgrade dry-run matrix with exact test gates per ecosystem.
