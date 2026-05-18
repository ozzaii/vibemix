# Phase 45: External Discharge + Public RC Publish - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning
**Mode:** Autonomous (gsd-autonomous fully — recommended grey-area answers auto-accepted)

<domain>
## Phase Boundary

Phase 45 is the **final ship phase** of v3.0 "Clean OSS Ship". It cascades from the legal-capacity blockers (Apple Dev Agreement + SignPath OSS approval) into signed-binary discharge → INSTALL-VM matrix → SHIP-CUT (`v3.0.0-rc1` draft) → 5-channel social publish + Discord + repo transfer to `bravoh/vibemix` → 24h monitoring rotation → ~2-week bake → SHIP-V1-DECISION at T+30.

**Two work streams:**
1. **Engineering scaffolding** (this phase's code work) — the orchestration layer that ties existing primitives together: `launch_trigger.sh`, `install_vm_matrix.sh` (tart-based fresh-VM walks), SHIP-V1-DECISION audit script, monitoring-rotation §SHIP-11 runbook, KAAN-ACTION-LEGAL §SHIP-01..13 runbooks.
2. **KAAN-ACTION-LEGAL discharges** (external-clock items) — Apple Dev Agreement (Francesco signs), SignPath OSS approval (Kaan submits, ~1-week SLA), Bravoh server endpoint deploy (Bravoh team), live Discord post, repo transfer to `bravoh/vibemix`, 24h monitoring rotation execution, Windows SmartScreen passive observation, SHIP-V1-DECISION sign-off at T+30.

**Engineering pre-stage GREEN through P44.** Everything that doesn't require external clock or live network execution is already shipped. Phase 45's engineering job is to add the missing orchestration + runbooks so the moment SHIP-01 + SHIP-02 close, the discharge cascade runs autonomously.

**No new product features.** Per memory `feedback_no_scope_creep_clean_utility`, Phase 45 strictly ships the release machinery and the discharge runbooks. The product itself was frozen at Phase 44 verification.

</domain>

<decisions>
## Implementation Decisions

### INSTALL-VM Matrix (SHIP-04, SHIP-05)

- **VM driver:** `tart` on Apple Silicon for macOS 12.3 / 14 / 15; `tart` + Windows VHDX images for Win 10 / 11. Single matrix runner: `scripts/dist/install_vm_matrix.sh`. Driven by a JSON matrix file (`scripts/dist/install_vm_matrix.json`) so additions don't require code changes. Reasoning: existing repo already standardizes on `tart` per `docs/install/INSTALL-VM-MATRIX.md` references in Phase 33 summaries.
- **Onboarding stopwatch wire-in:** `tauri/ui/src/wizard/onboarding-stopwatch.ts` already exists (Phase 33 INSTALL-05) — the matrix runner injects a `VIBEMIX_INSTALL_VM_RUN=1` env flag so the stopwatch dumps timing to `~/.vibemix/install-vm-timing.json` for matrix capture. No UI changes.
- **Screenshot capture:** Each VM run produces `install-vm-<os>-<version>-{wizard-step-1..3,session-live}.png` via `tart screenshot`. Stored under `dist/install-vm-runs/<run-id>/`. Single source of truth: matrix runner writes a `run.json` index.
- **60s gate:** `install_vm_matrix.sh --check-60s` reads the per-VM timing JSON and exits non-zero if any VM exceeded 60s end-to-end (TCC + audio test + controller probe combined). Plan 45-04 ships this check.
- **VM availability:** Matrix runner SKIPS missing OS images with a clear warning (`tart list` exit). Won't block CI on `--check-60s` if zero VMs present (autonomous degradation; full discharge requires all 5 OS images present).

### Launch Trigger Orchestration (SHIP-08)

- **`scripts/launch/launch_trigger.sh --publish`** orchestrates the social publish step:
  1. Reads `scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit,discord}.txt` (locked Phase 44-05).
  2. Asserts Kaan + Francesco sign-off footer present in all 5 (re-uses `scripts/launch/check_no_ai_slop.py`).
  3. Calls `scripts/launch/publish_social_posts.py` for 4 web channels (existing Phase 36 surface).
  4. Calls `scripts/launch/post_discord_launch.py` for Discord (existing).
  5. Logs to `dist/launch-runs/<UTC>.jsonl`.
- **Dry-run default:** `--publish` requires explicit `--live` flag; without it, dry-runs and prints what would publish. This is the safest discharge ergonomics — matches `discord_provision.py` Phase 44-06 convention.
- **Cadence:** T-30 / T+0 / T+5h / T+24h per `docs/launch-prep/LAUNCH-SEQUENCE.md` LAUNCH-10 lock. Trigger script honors `--phase {T-30, T+0, T+5h, T+24h}` flag to publish only the cadence-matched copy variant. Per-channel content selection table lives in `scripts/dayzero/launch_copy/cadence_index.json` (new in plan 45-03).

### Bravoh Server Endpoints (SHIP-06)

- **Bravoh-team-discharge.** Endpoints (`POST /vibemix/updates/upload`, `GET /vibemix/updates/latest.json`, `GET /vibemix/healthz`) live on the Bravoh backend (separate repo). Vibemix repo's contribution:
  - `scripts/release/check_bravoh_server_ready.sh` — polls the 3 endpoints, exits 0 if all healthy + healthz cron heartbeating. Used by `cut_release.sh` Gate 5 (added in plan 45-05).
  - `KAAN-ACTION-LEGAL.md §SHIP-06` runbook — explicit handoff document for Bravoh team (endpoint spec, cron requirement, healthz contract).
- **No client-side change.** Updater binary in `tauri/src-tauri/src/updater/` (Phase 27 universal2 work) already polls `latest.json`; nothing to wire.

### SHIP-V1-DECISION (SHIP-13)

- **Audit script:** `scripts/release/audit_ship_v1_decision.py` reads the last 14 days of:
  - GitHub release telemetry (download counts, crash reports if available via GH issues label `crash`)
  - Bravoh healthz cron uptime (last 14d, target ≥99.5%)
  - `eval/ear-test-logs/` post-RC entries (any new ear-test logs)
  - GitHub issues opened since T+0 (severity rollup)
- **Output:** `.planning/decisions/v3.0-SHIP-V1-DECISION.md` — pre-filled with metrics; Kaan adds his sign-off + decision (cut `v1.0.0` / cycle `v3.0.0-rc2` / pause) at T+30.
- **Template:** `docs/SHIP-V1-DECISION-TEMPLATE.md` defines the decision schema. Used by both the audit script (writes the report) and the §SHIP-13 runbook.

### Monitoring Rotation (SHIP-11)

- **`docs/launch-rotation.md` already exists** (per Phase 33-era handoff). Plan 45-06 audits + appends to it:
  - 24h rotation table T+0 → T+24h with 4 × 6h shifts (Kaan-only solo rotation for v3.0; v3.x may add Francesco/Momo).
  - Triage decision tree: comment volume / crash report / API key rate-limit / Bravoh server down.
  - `KAAN-ACTION-LEGAL.md §SHIP-11` — execution discharge.
- **No new monitoring tooling.** Kaan watches GH Actions + Bravoh healthz dashboard + Discord #bugs channel. Memory `project_one_click_install_hard_req` — fresh-VM install issues are the highest-priority signal.

### KAAN-ACTION-LEGAL Discharge Runbooks (SHIP-01..13 all routed)

Every SHIP-* requirement gets a §SHIP-NN section in `KAAN-ACTION-LEGAL.md` documenting:
- Who discharges (Kaan / Francesco / Bravoh-team)
- Pre-requisites (e.g., SHIP-03 requires SHIP-01 + SHIP-02 GREEN)
- Exact commands to run (`gh release create v3.0.0-rc1 --draft`, `gh api repos/.../transfer`, `launch_trigger.sh --live --phase T+0`)
- Verification step (`check_bravoh_server_ready.sh`, `verify_signed.py --require-signed`, etc.)
- Post-discharge: mark `[x]` in REQUIREMENTS.md + update STATE.md

Runbooks live under sections **§SHIP-01 through §SHIP-13** in canonical §GATE-*/§LAUNCH-* format, appended chronologically after Phase 44's §LAUNCH-08.

### Claude's Discretion

- Number of plans (recommend 6-8); split SHIP-04 (VM matrix) into its own plan if scope justifies.
- Whether to bundle SHIP-08 (launch_trigger) and SHIP-11 (rotation) into a single plan or split.
- Test fixtures for the audit script (synthetic last-14d telemetry payload structure).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 27-44 shipped)
- `scripts/release/cut_release.sh` — 6-gate cut driver (Phase 42 wired Gate 2b for hybrid hallucination gate).
- `scripts/dist/verify_signed.py` — already has `--require-signed` flag (Phase 27 + 34). SHIP-03 verification ready to go the moment SHIP-01 + SHIP-02 close.
- `scripts/dist/sign_macos.sh`, `sign_windows.ps1`, `sign_manifest.sh` — signing scripts shipped Phase 34. Consume Apple Dev cert + SignPath token from GH secrets.
- `scripts/launch/publish_social_posts.py` — 4-channel web publish (existing Phase 36).
- `scripts/launch/post_discord_launch.py` — Discord publish (existing Phase 36).
- `scripts/launch/check_no_ai_slop.py` — AI-slop blocklist + anchor-phrase gate (Phase 44-05).
- `scripts/launch/check_launch_docs.py` — outreach + sequence drift gate (Phase 44-07).
- `scripts/launch/check_bravoh_org_ready.sh` — GH org polling gate (Phase 44-06).
- `scripts/dayzero/discord_provision.py` — taxonomy-driven, dry-run-default (Phase 44-06).
- `scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit,discord}.txt` — 5-channel SHIP-TWEET copy locked (Phase 44-05).
- `scripts/dayzero/discord_taxonomy.json` — 5 roles + 9 channels (Phase 44-06).
- `tauri/ui/src/wizard/onboarding-stopwatch.ts` — Phase 33 INSTALL-05 timing instrumentation.
- `tauri/src-tauri/src/updater/` — universal2 auto-updater (Phase 27 DIST-19 prep).
- `docs/launch-rotation.md` — Phase 33-era rotation doc (needs §SHIP-11 augmentation).
- `docs/launch-prep/{OUTREACH-CALENDAR,LAUNCH-SEQUENCE}.md` — Phase 44-07 lock.
- `KAAN-ACTION-LEGAL.md` — §LAUNCH-03/04/06/07/08 sections present from Phase 44.

### Established Patterns
- **TDD per plan** — RED test → GREEN implementation → atomic commit per task.
- **`--dry-run` default** — live actions require explicit `--live` flag (memory `project_one_click_install_hard_req` ergonomics: never accidental network calls).
- **JSON-driven config** — taxonomies, matrices, cadence indexes all live in versioned JSON, not in-code tuples (Phase 44-06 pattern).
- **Append-only KAAN-ACTION-LEGAL.md** — sections in §SHIP-NN format, chronological order, never reorder existing.
- **CI grep gates** — every contract surface has a check script + pytest pin (Phase 44 pattern: `check_readme_hero_lock.py`, `check_readme_grids_a11y.py`, `check_no_ai_slop.py`).

### Integration Points
- `cut_release.sh` adds **Gate 5 — Bravoh server ready** via `check_bravoh_server_ready.sh`. Gate-2 already wired to `check_gate.sh` (Phase 42). Gate-1 (no-hardcoded-model) wired Phase 41-01.
- `launch_trigger.sh` becomes the single entry point for all post-cut publish actions, reusing existing publish scripts as subroutines.
- `audit_ship_v1_decision.py` reads from `dist/launch-runs/`, `eval/ear-test-logs/`, GH API — same data sources as the monitoring rotation.

</code_context>

<specifics>
## Specific Ideas

- **Kaan's voice for runbooks:** Direct, casual, "type these commands in this order, expect this output". No corporate hedging. KAAN-ACTION-LEGAL.md sections read like git commit messages for steps, not technical writing.
- **SHIP-CUT command literal:** `gh release create v3.0.0-rc1 --draft --target main --title "vibemix v3.0.0-rc1 — public release candidate" --notes-file dist/release-notes.md`. The release notes file is generated by `scripts/launch/populate_changelog.py` (existing).
- **Repo transfer command:** `gh api -X POST repos/$CURRENT_OWNER/vibemix/transfer -f new_owner=bravoh` — but only after Bravoh GH org SHIP-06 prerequisite checked via `check_bravoh_org_ready.sh`.
- **Monitoring rotation cadence:** 4 × 6h shifts. T+0..T+6 Kaan European morning (08:00–14:00 CET). T+6..T+12 Kaan European afternoon. T+12..T+18 Kaan European evening. T+18..T+24 sleep-shift on alerts only (GH Actions email + Discord pings).

</specifics>

<deferred>
## Deferred Ideas

- **Multi-rotation w/ Francesco + Momo** — v3.x or v4. v3.0 is single-rotator (Kaan) per scope.
- **Auto-cycle to RC2 on SmartScreen propagation timeout** — not auto. Decision is human at SHIP-V1-DECISION (T+30).
- **Twitter Spaces / X live Q&A around T+24h** — out of v3.0 scope (memory `feedback_no_scope_creep_clean_utility`). Can fit in v3.1 if comment volume justifies.
- **Substack "how we built it" post automation** — manually drafted by Kaan at T+72h per LAUNCH-SEQUENCE.md.
- **Reddit AMA T+7d** — not in current launch sequence. Defer to v3.1 if engagement metrics demand.

</deferred>
