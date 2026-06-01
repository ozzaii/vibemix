# CODEX_HOLD: Open Hold Lanes

Date: 2026-06-01
Verifier: Codex
Source of truth: `.planning/handoffs/2026-05-31-package-checklist.md`
Decision: HOLD all active dirty Hold Lane sections below. Do not stage these
with LAND packages unless a later verifier packet explicitly reclassifies that
lane.

## Current Evidence

Package ledger:

```text
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
OK: 5577 dirty paths covered by .planning/handoffs/2026-05-31-package-checklist.md; 3 generated launch previews ignored.
OK: every dirty path is assigned to an Include/Hold lane.
```

The checker summary currently reports the active hold lanes below. This packet
exists because a green package checker only proves assignment; it does not by
itself make it obvious which dirty islands must stay out of LAND commits.

## Active Hold Classifications

| hold lane | dirty paths | classification | reason to keep held |
|---|---:|---|---|
| Claude Runtime Orientation Drift | 2 | HOLD | Shared `CLAUDE.md`/scratch guidance; needs claim review against current runtime before landing. |
| Demo Source-Run Ship Plan | 1 | HOLD | Demo-night source-run plan conflicts with whole-rebuild/release posture if treated as architecture. |
| Rebuild Intake Digests | 7 | HOLD | Generated/summarized planning digests and file-list scratch; useful intake, not source truth. |
| Rebuild Carry-Forward Serato Cue Carrier | 3 | HOLD | Serato cue/export work needs grouped manifest/lock/import review before promotion. |
| Judge Score Overpraise Clamp | 3 | HOLD | Speech/judge safety hunk overlaps live-claim behavior; requires grounding review before LAND. |
| Runtime Diagnostic Output Resilience | 1 | HOLD | Diagnostic resilience hunk is runtime-adjacent and not yet independently packeted as LAND. |
| Learn Beatmatch Producer Moat Plan | 1 | HOLD | Planning-only moat note; beatmatch producer remains unbuilt/unproven. |
| Singularity Research Census Briefs | 21 | HOLD | Research/census material is evidence input, not product implementation. |
| Mixxx Source Scratch | 18 | HOLD | GPL source scratch/spec extraction; never vendor source into product. |
| Cue Export Folder Bridge | 4 | HOLD | Cue-folder CLI/export bridge is not yet product-wired/proven end to end. |
| Real CLAP Retrieval Eval Gate | 6 | HOLD | Valuable eval gate, but real-ONNX/corpus lane needs isolated CI/eval decision. |
| Eval Judge Cross-Check Gate | 2 | HOLD | Eval judge rubric work overlaps observability/judge surfaces; needs separate owner/gate. |
| FLX4 Live Context Proof Artifacts | 16 | HOLD | Hardware proof artifacts are evidence archives, not source to land broadly. |
| Cohost/Viber Eval Run Archives | 5141 | HOLD | Large eval-run archive tree; keep out of product commits unless intentionally curated. |
| Launch Screenshot Alternates | 14 | HOLD | Alternate marketing/screenshot assets; launch collateral itself remains held. |
| Premium Enterprise Visual Audit | 13 | HOLD | Design audit/mock/proof assets are not accepted product UI by themselves. |
| Sexiest Live Visual Proof | 12 | HOLD | Screenshot proof artifacts; useful evidence, not product source. |
| Frontend Shell Settings Proof | 11 | HOLD | UI/proof hunk needs visual/product acceptance before promotion. |
| Local Code-Signing Certificate Dumps | 3 | HOLD | Local certificate-chain dumps; do not commit. |
| Tauri Sidecar Log Drain | 1 | HOLD | Shares `sidecar.rs`; log-drain hunk should not be absorbed with sidecar lifecycle work. |
| Tauri Cohost Restart Recovery | 2 | HOLD | Current source has boot/Quit proof, but shared Rust hunks still require surgical landing. |
| Local MOSS TTS ONNX Runtime Spike | 7 | HOLD | Local TTS/runtime/dependency spike needs product/provider decision and lockfile review. |
| Deck Audio Controller-Weighted Master Context | 9 | HOLD | Audio/controller weighting remains live-DJ proof dependent. |
| Mix Timing Oracle | 4 | HOLD | Drop/mix timing oracle remains intentionally held until live timing proof exists. |

Inactive hold sections in the checklist, such as carry-forward cue agreement or
live reality pins, are not listed above when they have no current dirty paths.

## Landing Rules

- A hold lane can only move to LAND by creating or updating a specific
  `CODEX_READY-*` packet with current source references, tests, and any required
  live proof.
- Shared files must be staged by hunk. In particular, `src/vibemix/__main__.py`,
  `src/vibemix/agent/dj_cohost.py`, `src/vibemix/state/deck_context.py`,
  `tauri/src-tauri/src/sidecar.rs`, and `pyproject.toml` carry multiple lane
  assignments.
- Large evidence archives under `.planning/eval-runs/` should remain untracked
  unless a release/eval packet explicitly names the subset to preserve.
- Local scratch (`.cp_probe.txt`, `.planning/.tmp_filelist.txt`,
  `.planning_ls_scratch.txt`, `codesign0`, `codesign1`, `codesign2`) should be
  deleted or ignored later, not absorbed into product commits.

## Verification Needed To Promote

Before promoting any row above, rerun:

```text
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
git diff --check -- <lane paths>
```

Then add lane-specific gates. Speech lanes need grounding review; packaging
lanes need signed artifact checks; audio/controller lanes need live source or
packaged proof; frontend lanes need UI tests/screenshots; dependency lanes need
manifest/lock consistency.
