# Future AI Routing Handoff - 2026-05-31

Purpose: give the next Codex/Claude session one clean doorway into this dirty
tree. This is not a refactor and not permission to move product code while other
sessions are still coding. It routes files, evidence, and decisions into stable
places so the eventual cleanup can happen without breaking the live app.

## First Read Order

1. `AGENTS.md` - shortest repo contract: commands, invariants, staging rules,
   excluded Learn/GSD suites, live verification skills, and IPC count discipline.
2. `CLAUDE.md` - deeper product/architecture orientation: live co-host value
   bar, model-routing constraints, app invariants, Tauri sidecar caveats, library
   workflow, and local runtime gotchas.
3. `.planning/handoffs/2026-05-31-package-checklist.md` - current dirty-tree
   assignment source. If a dirty file is not under an Include or Hold list, stop
   and classify it before coding or staging.
4. `.planning/handoffs/2026-05-31-maintainability-map.md` - the high-level
   maintainability plan, evidence ledger, live-app risk ledger, dependency rings,
   and structural-refactor prerequisites.
5. `.planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md` - raw
   inventory for the current package split.
6. `.planning/handoffs/2026-05-28-full-surface-wiring-sweep.md` - canonical
   earlier handoff for Viber, settings, research, ANLZ parsing, pill, and
   mock-transfer contracts.

If these disagree, trust the freshest command output first, then the package
checklist, then the maintainability map. Older handoffs are discovery context,
not live truth.

## Current Evidence Snapshot

Latest routing refresh:

- `git diff --shortstat` reported 102 tracked files changed, 5417 insertions,
  and 1853 deletions before Package 0B landed. Post-commit,
  `git diff --shortstat` reported 102 tracked files changed, 5441 insertions,
  and 1872 deletions.
- `git ls-files --others --exclude-standard | wc -l` reported 99 untracked paths.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passed with 201 dirty paths listed and assigned; 3 generated launch previews
  are intentionally ignored.

This handoff pairs with an update to
`.planning/handoffs/2026-05-31-package-checklist.md` that classifies those new
paths. Always rerun the four resume commands before acting, because concurrent
sessions are still moving:

```bash
git status --short
git diff --shortstat
git ls-files --others --exclude-standard | wc -l
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
```

## Clean Place Rule

Do not physically move active source files just to make the tree look tidy.
During concurrent sessions, "clean place" means:

- every dirty path is assigned to exactly one intended package or hold lane;
- shared paths are called out as shared and staged by hunk;
- research/proof collateral is separated from shippable product code;
- future agents can start from one routing file instead of re-discovering the
  entire `.planning/` tree.

Move or restructure files only after the owning package lands or the owner
explicitly opens a cleanup/refactor lane.

## Package Context

Package 0 has already landed:

- `5fa5d4d8 docs(planning): document dirty tree shipping lanes`
- Scope: package inventory, maintainability map, package checklist, checker, and
  checker tests only.

Package 1 has already landed:

- `05ed0b91 chore(agent-tooling): add live verification helpers`
- Scope: repo agent tooling, live websocket probe helpers, IPC wiring checker,
  grounding review skill, and runtime dev MCP helper tests.

Package 0B has already landed:

- `d433a42d docs(planning): add future ai routing handoff`
- Scope: this routing handoff plus checklist/map rebaseline for the newest
  drift classifications only.

After those commits, the remaining dirty tree is mostly product packages and
hold lanes. Do not re-open Package 0 or Package 1 except for a narrow docs
rebaseline like this routing file.

## Next Decision Ladder

Use this when the checker is green and the user asks "what will we do with it?"
Do not keep polishing count snapshots just because concurrent sessions changed
insertions or screenshot totals.

1. If the checker is red, classify missing paths first. This is the only
   planning edit that should happen automatically while other sessions are still
   coding.
2. If the checker is green and no staging window is open, stop changing docs and
   report the current package map. Count-only churn is not a product
   improvement.
3. If a staging window opens, choose one package card. The next strongest review
   candidate is the combined Package 2 + Package 3 IPC contract package, because
   the shared schema/codegen/count files already make a split risky.
4. If the user wants product-facing musical value next, choose Packages 4-6 as
   one cue/pill/Viber pipeline and require live DDJ/Viber evidence before any
   "works in the app" claim.
5. If the user wants low-risk technical cleanup next, choose one of Packages
   12-15, but keep Rust sidecar-log and runtime diagnostic holds separate until
   their own checks exist.
6. If the user wants polish/visual work next, promote Frontend Shell Settings
   Proof or the visual-proof hold lanes only with UI tests/build/screenshots.

Before any commit, verify the cached file list is exactly the chosen package.

## File Groups And Meaning

`AGENTS.md` and `CLAUDE.md`

- These are the entry contracts for agents. `AGENTS.md` is the compact contract;
  `CLAUDE.md` is the deeper product and runtime map.
- Current dirty `AGENTS.md` hunk belongs to IPC-count guidance, not the already
  landed tooling package.
- `CLAUDE.md` may also carry other sessions' concurrent notes; stage hunks
  surgically.

`.planning/handoffs/2026-05-31-package-checklist.md`

- This is the authoritative routing table for dirty paths.
- The checker parses only backticked paths under `Include:` or `Hold:` blocks.
- If a file is only mentioned under `Keep out:` or prose, strict mode still
  treats it as unassigned.
- Use this file to direct work, not to claim work is shippable.

`scripts/check_dirty_package_plan.py`

- Guardrail for the package plan. It reads staged, unstaged, and untracked paths.
- It intentionally catches half-staged trees, which matters because commits race
  across concurrent sessions.
- Run it before staging and after any rebaseline.

IPC and settings/session surfaces

- Packages 2 and 3 share schema/codegen files, Python wrappers, UI consumers,
  generated TypeScript, and count/parity tests.
- Default decision: review them as one IPC contract package unless a deliberate
  split keeps schema, generated files, and all count tests together.
- Any `messages.schema.json` change needs codegen plus:
  `uv run python scripts/check_ipc_schema.py`,
  `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
  and the UI IPC check/build path.

Cue, pill, library live-read, and Viber

- Packages 4, 5, and 6 form one product pipeline: cue provenance and semantic
  slot numbers must survive ingest, smart cue tools, Viber/live-read context,
  and the compact pill.
- Do not claim live Viber/pill correctness from backend cue tests alone.
- Remaining proof needs a live DDJ/Viber run with `CuePoint.source`,
  `CuePoint.number`, CARE risk, and export/live-read evidence visible together.

Learn and Earned Wall

- Packages 7 and 9 are adjacent but not the same thing. Package 7 is operator
  action/curriculum UI plumbing; Package 9 is cited-credit persistence and
  Earned Wall refresh emission.
- Package 8 is beatmatch judge creditability. The producer for real
  `BEATMATCH_GRADED` live events is still a hold lane.
- Keep the user's exclusion: do not run GSD or beginner Learn paths unless asked.

Runtime technical lanes

- Package 12: sqlite-vec/CLAP memory readiness and diagnostic-session memory
  gating.
- Package 13: stale sidecar bundle/schema guard.
- Package 14: nested live TTS shutdown cleanup.
- Package 15: BlackHole 16ch auto-master route selection.
- Deck-audio controller-weighted context remains on hold until audible route and
  cited co-host proof show controller posture changes the grounded live context.

Launch, pricing, and public claims

- Package 10 is internal live-stack economics. Cartesia `sonic-3` remains
  unverified for external pricing copy until billing confirms effective rates.
- Package 11 is selected launch collateral. Screenshot alternates remain in a
  hold lane.
- Do not mix launch collateral, public cost claims, or dependency changes into
  runtime fixes.

## Hold Lanes To Respect

Singularity research/census

- Broad research under `.planning/singularity/2026-05-31/`.
- Useful for discovery, but not shipping proof. Validate every path/line and
  claim before using it to justify product changes.

Real CLAP retrieval eval gate

- Offline model-quality guard with committed real CLAP vectors.
- Useful for catching ranking/anisotropy regressions, but it still does not run
  fresh ONNX inference in CI.
- Do not use it to claim complete real-model coverage.

Local MOSS TTS

- A hold lane for local on-device voice experiments, residual lockfile churn,
  and local proof helpers.
- Needs license/model-source documentation, install proof, latency/bundle proof,
  and grounding-review before becoming live co-host speech.

Frontend shell/settings proof

- Production UI files `tauri/ui/src/shell/app.ts` and
  `tauri/ui/src/settings/components/group.ts` plus proof screenshots/JSON live
  under a hold lane until tested and reviewed as a UI behavior package.
- It is not design-only collateral, because it changes shell/settings state
  behavior.

Cue export folder bridge

- `src/vibemix/library/cue_folder.py` and
  `tests/library/test_cue_folder.py` appeared from the cue-export research lane.
- Treat them as a future cue export package, not part of the current auto-cue
  pill package, until CLI/export integration and proof are accepted.

Mix Timing Oracle

- Drop prediction, automix, transition clock, line voice, and drop reaction work
  stays held until lint, live/audio timing, and grounded speech proof are green.
- Green helper tests do not prove "AI speaks the drop" in the live app.

## Optimization Opportunities

Dependency modernization should be done in rings after feature packages settle:

- Python: prior audit found 50 outdated packages plus the known SQLCipher
  omission. Upgrade AI/runtime SDKs, binary/audio/model-adjacent packages, and
  major-version boundaries separately.
- UI: production npm audit was clean; dev audit had Vitest/Vite/esbuild and
  `tmp` findings through dev tooling. Treat these as dev-tool upgrades, not
  emergency product fixes.
- Rust: prior dry-run found compatible updates. Keep Cargo updates separate from
  Python/UI packages.

Performance and capability opportunities:

- Add a real ONNX `InferenceSession` gate before claiming model-regression
  coverage.
- Mean-center section-level semantic scoring; whole-track search is centered,
  but section paths still need calibration.
- Rebuild and prove UI bundles before saying the latest pill behavior is in the
  app.
- Use live websocket, UI log, and session `events.jsonl` proof for anything the
  co-host says.

Structural refactor opportunities:

- Do not refactor broad dirty subsystems while feature packages are moving.
- Good later targets are clean or freshly settled modules with clear public
  contracts, especially large library/agent modules once package behavior is
  landed and tests are fresh.
- Refactor entry criteria: package checker green, owner package settled, focused
  tests identified, public contracts preserved, and no unrelated dependency
  churn.

## Staging Protocol

1. Refresh status, shortstat, untracked count, and package checker.
2. Pick exactly one package or one hold lane to promote.
3. Inspect shared paths with `git diff -- <path>` and stage only owned hunks.
4. Verify cached diff:

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

5. Run the package-specific tests/build/live checks named in the checklist.
6. Commit with `git commit -s` only when the cached file list matches the package.
7. Rebaseline planning docs only if counts or ownership changed.

Never use broad `git add -A` in this tree.

## Claims Future Agents Must Not Make Yet

- Do not say the codebase is cleaned up. It is mapped and package-covered, not
  refactored.
- Do not say live drop speech is shipped. Current drop-speaking work is helper,
  demo, or held runtime groundwork.
- Do not say real CLAP/CUE regressions are fully covered. The offline gate helps,
  but CI still lacks fresh ONNX inference coverage.
- Do not say six Learn skills are fully mastered live. Beatmatch still lacks a
  production event producer.
- Do not say deck identity is resolved from audio just because deck-pair capture
  is configured. Verified capture and resolved deck identity are different gates.

## Short Answer For The Next Session

The repo is in a concurrent dirty-tree packaging phase. Start from this file,
then `AGENTS.md`, `CLAUDE.md`, the package checklist, and the maintainability
map. Run the resume commands. If the checker is green, choose a package card and
stage surgically. If the checker is red, classify drift first. No broad cleanup,
no broad staging, and no product-readiness claims without live evidence.
