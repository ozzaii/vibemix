# Phase 58: Ship Readiness - Research

**Researched:** 2026-05-21
**Domain:** Release engineering — gate verification + wiring + KAAN-ACTION documentation (no new machinery)
**Confidence:** HIGH (everything verified on-disk with file:line; this is a verify/wire/document phase, not a build-new phase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Engineering closes everything not requiring an external signature** (per `gsd-autonomous fully` + STATE blockers). The signed publish stays KAAN-ACTION. This phase makes the release **one-button-after-signatures** and proves the button works minus the signature.
- **REL-01 (gates green on real artifacts):** run `scripts/launch/cut_release.sh`'s pre-flight gates on REAL built artifacts. Build the real artifacts where the dev machine can (the macOS app/DMG + sidecar). Gates that are fully engineering-determinable MUST go green now. Gates that depend on a Kaan input — **Gate 2b (hallucination)** fed by Kaan's live ear-pass on Phases 54+55 (`54-HUMAN-UAT` + `55-HUMAN-UAT`), **Gate 6b (e2e report)** fed by the §E2E-50A-WALK recording — are **PRE-WIRED + dry-run-verified** so they flip green the moment Kaan's input lands, with NO engineering step left to discover. Document exactly which gates are green-now vs gated-on-Kaan-input.
- **REL-02 (§E2E-50A-WALK):** the real end-to-end walk on the MacBook with real DJ-set audio, recorded to `docs/e2e/2026-05-walk.webm`, is **KAAN-ACTION**. Engineering ships: the exact walk script/checklist, the recording recipe, and confirms the harness/app path the walk exercises is green. Do NOT fake the .webm.
- **REL-03 (one-button SHIP-CUT documented + pre-verified):** document the EXACT one-button ship sequence; run a **dry-run** that confirms everything-but-the-signature is ready. Surface ALL external-clock + Kaan-action discharge items in ONE consolidated cookbook (Apple Dev Agreement, SignPath OSS cert, the §E2E walk, the Gate-2b ear-passes, + carry-forward v3.0/v3.1 KAAN-ACTION items if still open). The v3.x precedent exists: KAAN-ACTION-LEGAL §SHIP-01..13 cookbook + `audit_ship_v1_decision.py` — extend/reuse, don't reinvent.
- **Sidecar binary rebuild** (`scripts/build_sidecar.py`) deferred from Phase 57 lands here as part of producing real artifacts. Rebuild + verify the sidecar is current before the gate run.
- **Don't reinvent the release machinery — verify + wire + document.** Any change is surgical + test-pinned.

### Claude's Discretion
- The exact mechanism of the dry-run / signature-stub (new flag vs env var vs separate runner) — recommendation below.
- How to reconcile the hardcoded `v2.1.0-rc` tag regex + `v2.1-MILESTONE-AUDIT.md` reference against the current v4.0 milestone (a real blocker — see Pitfall 1). Recommendation below.
- Cookbook file location + structure for the v4.0 consolidated KAAN-ACTION surface.

### Deferred Ideas (OUT OF SCOPE — KAAN-ACTION / external clock)
- **External signatures:** Apple Developer Program Agreement update (Francesco) + SignPath OSS Foundation cert (Kaan). The literal signed publish.
- **§E2E-50A-WALK recording** on the real Mac with real DJ-set audio → `docs/e2e/2026-05-walk.webm` (feeds Gate 6b).
- **Gate 2b hallucination sign-off** — Kaan's live ear-pass on hype (54) + coach (55) across ≥2 genres.
- Carry-forward v3.0/v3.1 KAAN-ACTION items still open (SignPath cert shared with v3.x; Tart VM walk; etc.).
</deferred>
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-01 | All engineering-side release gates pass on real artifacts — `cut_release.sh` 6-gate pre-flight + Gate 2b (hallucination) + Gate 6b (e2e report) green | Full gate-by-gate inventory below with GREEN-NOW / KAAN-GATED / EXTERNAL classification + the artifact each needs + the exact blocker each currently trips |
| REL-02 | §E2E-50A-WALK discharged by driving the real app end-to-end; walk artifact recorded | The walk harness (`tests/e2e/macbook/50a_kaan_walk_checklist.md`), recording rig (`scripts/e2e/record_50a_walk.sh`), and the report producer (`tests/e2e/macbook/render_report.py`) all exist + are verified. The recorded `.webm` is KAAN-ACTION; engineering proves the app path + can produce a real `dist/e2e-macbook-runs/<UTC>/report.html` Gate 6b consumes |
| REL-03 | External-clock items surfaced as KAAN-ACTION with the exact one-button SHIP-CUT sequence documented + pre-verified | `KAAN-ACTION-LEGAL.md` §SHIP-CUT (3385-line cookbook) exists in the canonical pattern; `audit_ship_v1_decision.py` (610-line evidence pre-filler) exists. Extend with a v4.0 consolidated surface + a dry-run that exits green with the signature stubbed |
</phase_requirements>

## Summary

Phase 58 is a **verify + wire + document** phase — every piece of release machinery already exists on disk and was built across Phases 39 (`cut_release.sh`), 42 (Gate 2b hybrid hallucination gate), 45 (`audit_ship_v1_decision.py` + §SHIP cookbook), 49 (installer/companion signing), and 50 (Gate 6b e2e report + 50a Kaan-walk scaffold). The job is NOT to build new gates; it is to (1) build the real artifacts the gates need, (2) run the engineering-determinable gates green on those real artifacts, (3) prove the two Kaan-input-gated gates (2b hallucination, 6b e2e) are pre-wired to flip cleanly with zero hidden engineering step, and (4) consolidate the KAAN-ACTION discharge surface + add a signature-stubbed dry-run that exits green.

**The single largest finding is a hard blocker the plan MUST address:** `scripts/launch/cut_release.sh` is **hardcoded to the v2.1 release** — Gate 1's tag regex is `^v2\.1\.0-rc[0-9]+$` ([cut_release.sh:45](scripts/launch/cut_release.sh#L45)) and Gate 4 requires `.planning/v2.1-MILESTONE-AUDIT.md` with verdict WIRED ([cut_release.sh:122](scripts/launch/cut_release.sh#L122)). The current milestone is v4.0; the live `v2.1-MILESTONE-AUDIT.md` has `status: tech_debt` (not WIRED). A v4.0 cut against the current script is impossible without a surgical update to the tag regex + milestone-audit path/verdict, plus generating a fresh `v4.0-MILESTONE-AUDIT.md`. This is the load-bearing engineering work of the phase. Several other gates also reference v2.1/v3.0-era inputs (`check_gate.sh` 7-day nightly proxy + 14-day ear-test window; `check_e2e_report.sh` needs a `dist/e2e-macbook-runs/` run that does not yet exist).

**Primary recommendation:** Build the sidecar (already current — rebuild + verify) and a real macOS `.dmg`, then walk `cut_release.sh` gate-by-gate, classify each as GREEN-NOW / KAAN-GATED / EXTERNAL, surgically re-point the v2.1-hardcoded gates to v4.0 (tag regex + milestone audit), generate the v4.0 milestone audit, add a `--dry-run`/`--no-sign` mode that stubs the signed-binary gate and exits green, and roll the open v3.0/v3.1 carry-forwards (esp. the shared SignPath cert) into one consolidated v4.0 KAAN-ACTION surface alongside the existing §SHIP-CUT cookbook. Pin every surgical change with a repo test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Release pre-flight gating | Shell driver (`cut_release.sh`) | Python/pytest gate scripts | The driver orchestrates; each gate is a standalone script/test it shells out to |
| Hallucination gate (Gate 2b) | `check_gate.sh` (nightly proxy + ear-test) | `eval/` data dirs + `check_ear_test.sh` | Hybrid: autonomous proxy (`.planning/eval-runs/`) AND Kaan ear-test logs (`eval/ear-test-logs/`) |
| E2E report gate (Gate 6b) | `check_e2e_report.sh` | `dist/e2e-macbook-runs/<UTC>/report.html` (produced by `render_report.py`) | Parses latest report's 5 dimensions; blocks on any FAIL |
| Real artifact build | `scripts/build_sidecar.py` (PyInstaller) + Tauri bundler | `tauri/src-tauri/binaries/` | Sidecar onedir → Tauri `externalBin` → `.dmg`/`.app` |
| KAAN-ACTION discharge surface | `KAAN-ACTION-LEGAL.md` (docs) | `audit_ship_v1_decision.py` (evidence pre-fill) | Human legal/identity capacity items; signed publish |
| Signing | `scripts/dist/sign_macos.sh` / `sign_windows.ps1` / `verify_signed.py` | CI `.github/workflows/release.yml` | EXTERNAL — gated on Apple Dev Agreement + SignPath cert |

## Standard Stack

This phase adds **no new dependencies**. Everything is already in-tree. The "stack" here is the existing release toolchain — verified present on this dev machine:

| Tool | Where | Verified | Purpose |
|------|-------|----------|---------|
| `bash` | system | ✓ | All gate drivers (`cut_release.sh`, `check_gate.sh`, `check_e2e_report.sh`, `check_ear_test.sh`, `check_bravoh_server_ready.sh`) |
| `jq` 1.8.1 | `/opt/homebrew/bin/jq` | ✓ [VERIFIED: `jq --version`] | Gate 2b nightly-scorecard + ear-test JSON parsing |
| `ffmpeg` 8.0.1 | `/opt/homebrew/bin/ffmpeg` | ✓ [VERIFIED: `ffmpeg -version`] | §E2E walk `.mov`→`.webm` transcode (`record_50a_walk.sh --transcode`) |
| `python3` 3.12 | `.venv/` | ✓ | gate pytest legs + `build_sidecar.py` + `populate_changelog.py` |
| PyInstaller | via `uv`/`.venv` | (used by build_sidecar) | sidecar onedir build (`vibemix-core.macos.spec`) |
| Tauri CLI | `cargo tauri` | macOS-only | `.dmg`/`.app` bundle |
| `curl` | system | ✓ | Gate 5b Bravoh server probe |

**Installation:** none. If a gate needs `jq` and it is somehow absent on a fresh checkout, `check_gate.sh:60` and `check_ear_test.sh:54` already exit 1 with a clear message — no action needed here, both are present.

## Package Legitimacy Audit

> **Not applicable.** Phase 58 installs zero external packages. It builds artifacts from already-pinned deps (`uv.lock`) and runs already-committed gate scripts. No registry interaction, no slopcheck needed.

## cut_release.sh — Gate-by-Gate Inventory (THE core of the plan)

Source: [scripts/launch/cut_release.sh](scripts/launch/cut_release.sh). Gates execute in file order; ANY fail → `exit 1` and the cut command is NOT printed. The script **never** calls `gh release create` — it only prints it (cut_release.sh:33, 175-189). That hard guard is preserved.

| Gate | File:line | What it checks | Artifact/input needed | Classification | Current state on disk |
|------|-----------|----------------|------------------------|----------------|------------------------|
| **1 — Tag prefix** | [L62-67](scripts/launch/cut_release.sh#L62) | `TAG =~ ^v2\.1\.0-rc[0-9]+$` (P83) | the tag arg | **GREEN-NOW (after surgical fix)** | ⚠️ **HARDCODED to v2.1** — a v4.0 tag (`v4.0.0-rc1`?) fails. Plan MUST update `TAG_REGEX` (L45) to the v4.0 scheme. See Pitfall 1 |
| **2 — Signed binaries** | [L71-90](scripts/launch/cut_release.sh#L71) | `verify_signed.py --require-signed` for every `dist/*.{dmg,pkg,msi,exe}` | a **signed** artifact in `dist/` | **EXTERNAL** | No `.dmg` in `dist/` yet; even when built, `--require-signed` needs the Apple/SignPath signature (EXTERNAL). This is the gate the dry-run must stub |
| **2b — Hallucination** | [L94-99](scripts/launch/cut_release.sh#L94) | `scripts/release/check_gate.sh` — 7 nightly proxy scorecards green AND `check_ear_test.sh` green | `.planning/eval-runs/<run>/eval_report.json` ×7 + `eval/ear-test-logs/*.json` (≥2 sessions, ≥2 genres, 14d, 0 slop) | **KAAN-GATED (ear-test) + ENG (nightly)** | ⚠️ ear-test-logs dir holds only `schema.json` + `.gitkeep` (EMPTY). eval-runs holds `loadtest_*.json` (latency, NOT the `.overall.f1` nightly format `check_gate.sh:161` expects). BOTH legs currently fail. Fed by `54-HUMAN-UAT` + `55-HUMAN-UAT` |
| **6b — E2E report** | [L104-108](scripts/launch/cut_release.sh#L104) | `scripts/e2e/check_e2e_report.sh` — latest `dist/e2e-macbook-runs/<UTC>/report.html` has no dimension FAIL | a rendered report.html | **KAAN-GATED** | ⚠️ `dist/e2e-macbook-runs/` does NOT exist → `check_e2e_report.sh:23` exits **2** ("run e2e first"). Fed by the §E2E-50A-WALK. `render_report.py` can produce a real run dir (see REL-02) |
| **3 — README hero hash** | [L113-117](scripts/launch/cut_release.sh#L113) | `pytest tests/repo/test_readme_hero_hash_sync.py` | committed README + hero asset | **GREEN-NOW** | Runnable now; verify green (Phase 35 gate, hero asset drift) |
| **4 — Milestone audit** | [L121-132](scripts/launch/cut_release.sh#L121) | `.planning/v2.1-MILESTONE-AUDIT.md` exists + frontmatter `overall_verdict: WIRED` (or `status: passed`) | the audit file | **GREEN-NOW (after surgical fix + audit gen)** | ⚠️ Points at **`v2.1`** audit whose `status: tech_debt` ([v2.1-MILESTONE-AUDIT.md:8]). Plan MUST: (a) generate `v4.0-MILESTONE-AUDIT.md` via `scripts/integration_audit.py --write-milestone-audit` (writes `overall_verdict: WIRED` when all seams green, integration_audit.py:613,650), (b) re-point `AUDIT=` path (L122) to v4.0 |
| **5 — POC retired** | [L137-141](scripts/launch/cut_release.sh#L137) | `pytest tests/repo/test_g5_poc_files_untouched.py` | n/a (scrub gate) | **GREEN-NOW** | Runnable now; POC variants stay deleted (also pinned by `tests/repo/test_repo_scrub.py`) |
| **5b — Bravoh server** | [L146-150](scripts/launch/cut_release.sh#L146) | `check_bravoh_server_ready.sh --quiet` — 3 endpoints on `api.altidus.world` + fresh healthz | live Bravoh server | **ENG-determinable (network)** | Probes prod `api.altidus.world` (`/vibemix/healthz`, `/updates/latest.json`, HEAD `/updates/upload`). Green iff the Bravoh server side is up + healthz cron fresh (≤10 min). Runnable now; result depends on server state, not on Kaan input |
| **6 — Bundle ID locked** | [L155-159](scripts/launch/cut_release.sh#L155) | `pytest tests/security/test_bundle_id_locked.py` | `tauri.conf.json5` | **GREEN-NOW** | Runnable now; pins `identifier == world.bravoh.vibemix`. ⚠️ Kaan's WIP touches `tauri.conf.json5` — verify the WIP didn't change the identifier (it shouldn't have) |

### Classification rollup

- **GREEN-NOW (run + go green this phase):** Gate 3 (README hash), Gate 5 (POC retired), Gate 6 (bundle ID), **Gate 1 after tag-regex fix**, **Gate 4 after v4.0 audit gen + path fix**, Gate 2b **nightly leg** (needs ≥7 real nightly proxy scorecards — see Open Question 1).
- **KAAN-GATED (pre-wire, prove flips clean):** Gate 2b **ear-test leg** (fed by 54+55 HUMAN-UAT live ear-pass), Gate 6b (fed by §E2E-50A-WALK recording).
- **EXTERNAL (signature, dry-run stubs it):** Gate 2 (signed binaries — Apple Dev Agreement + SignPath cert).
- **ENG-but-server-dependent:** Gate 5b (Bravoh server probe — green when the server is up; not a Kaan input but not purely local).

### What "wired to flip with no hidden engineering step" concretely means
- **Gate 2b ear-test:** the `eval/ear-test-logs/` writer + `schema.json` exist; `check_ear_test.sh` already parses them. The ONLY missing thing is ≥2 signed ear-test JSON logs across ≥2 genres in a 14-day window with 0 slop flags. Those logs are produced by Kaan's live ear-pass (the Phase 29 debrief ear-test toggle, per `check_ear_test.sh:13`). 54/55 HUMAN-UAT are `status: partial`/`pending` — the live drive that fills them ALSO produces these logs. Engineering verifies the writer path lands a schema-valid log; the content is KAAN-ACTION.
- **Gate 6b e2e:** `render_report.py` writes `dist/e2e-macbook-runs/<run_id>/report.html` from an `EeRun` (render_report.py:26-42); `check_e2e_report.sh` parses the 5 dimension statuses. The Hallucination dimension (dimensions.py:61) is the seam where the §E2E walk's qualitative pass lands. Engineering proves the producer→consumer path green on a real (non-faked) run; the actual recorded walk is KAAN-ACTION.

## Real Artifact Build — what can be built here

| Artifact | Build path | Buildable headless on this Mac? | Notes |
|----------|-----------|----------------------------------|-------|
| **Python sidecar** (`vibemix-core`) | `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec` | ✓ YES | [VERIFIED on disk] Already built 2026-05-20: `dist/vibemix-core/vibemix-core` (33 MB onedir) + both triples staged at `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` + `...-x86_64-apple-darwin/`. The "deferred from Phase 57" rebuild = re-run the spec + confirm currency (AIza-leak scan runs automatically per build_sidecar.py:13-16). Refuses `--onefile`; uses `rustc -vV` for triple |
| **macOS `.app`/`.dmg`** | `cargo tauri build` (consumes the staged sidecar via `externalBin`) | ✓ build YES / ✗ sign NO | The DMG can be **built** locally headlessly (Apple Silicon). It CANNOT be **signed/notarized** without the Apple Dev Agreement (EXTERNAL). Gate 2 needs the SIGNED artifact → that's exactly what the dry-run stubs |
| **Windows `.exe`/`.msi`** | CI `release.yml::build-windows` or `scripts/win/build_local.ps1` in a VM | ✗ NO (cross-build is CI-only on Mac) | Out of this phase's local scope; Windows artifact + SignPath cert is EXTERNAL. The dry-run treats Windows artifacts as stubbed too |

**Recommendation:** rebuild the sidecar to confirm currency (it is current as of 2026-05-20, post-dates the last sidecar-relevant source change; confirm with a fresh `build_sidecar.py` run + the auto AIza scan), then build an **unsigned** local `.dmg` so Gate 2's `verify_signed.py` has a real file to inspect under the dry-run/stub path. Do NOT attempt to sign.

## KAAN-ACTION Cookbook + Ship-Decision Audit (REL-03)

### The existing precedent (extend, don't reinvent)
- **`KAAN-ACTION-LEGAL.md`** (repo root, 3385 lines) — the canonical discharge cookbook. Structure: numbered sections (§1-§8 + §SHIP + §POST-RC-CLEANUP + AUDIO-05/06/07 + INSTALL-VM-RUN + GATE-01/02...) each with: REQ-ID, Owner, Status checkboxes, Effort, "Why this is KAAN/FRANCESCO-action", numbered Protocol, "What unblocks", and a fenced **Sign-off block**. The key section for this phase is **§SHIP → SHIP-CUT** ([KAAN-ACTION-LEGAL.md:307-339]) — the exact 9-step publish runbook (`populate_changelog.py` → `cut_release.sh <tag>` → copy printed `gh release create --draft` → inspect → flip published).
- **The two LEGAL-CAPACITY CARVEOUTS** ([KAAN-ACTION-LEGAL.md:13-33]): DIST-09 Apple Dev Program Agreement (Francesco) + DIST-11 SignPath OSS Foundation cert (Kaan, ~1-week SLA). CI greps for forbidden autonomous POST/PUT to apple.com/signpath.io (P46 hard rule, enforced in `verify-signed.yml` + `release.yml`). **Autonomous agents must NEVER discharge these** — the plan documents them, never attempts them.
- **`scripts/release/audit_ship_v1_decision.py`** (610 lines, Plan 45-04) — reads 14 days of evidence from 4 sources (GH releases, Bravoh healthz uptime, ear-test logs, GH issues) and pre-fills a SHIP-V1-DECISION report. `--fixtures` (hermetic) / `--live` (read-only gh + Bravoh) modes; all subprocess argv are read-only (no POST/PATCH/DELETE — audit_ship_v1_decision.py:39). This is the T+30 v1.0.0-cut evidence collator, NOT the rc-cut gate — relevant as the *pattern* for the consolidated surface + as a carry-forward item.

### Open v3.0/v3.1 KAAN-ACTION carry-forwards that MUST roll into the v4.0 surface
From [STATE.md:236-254] + [STATE.md "Blockers"]:

| Item | Status | Roll into v4.0? |
|------|--------|------------------|
| §INSTALL-COMPANION-SIGN — SignPath OSS cert for companion `.ps1`/`.py` | external_clock | **YES — SAME cert as SHIP-CUT** (the shared external clock). Consolidate |
| DIST-11 SignPath OSS Foundation cert (Windows binary signing) | pending, ~1wk SLA | **YES — same shared cert** |
| DIST-09 Apple Dev Program Agreement (Francesco) | pending | **YES — gates signed macOS** |
| §E2E-50A-WALK | v4.0 Phase 58 SC-2 | **YES — this phase's REL-02** |
| §INSTALL-VM-RUN (Tart VM 5-OS matrix) | gated on COMPANION-SIGN | YES — surface as carry-forward (not a v4.0 blocker per STATE risk #1) |
| §VIS-04/§VIS-05 Mixamo retargets | independent/parallel | Surface as parallel asset-discharge (not ship-blocking) |
| §SHIP-CONTACT-VBAUDIO (email VB-Audio) | drafted, send | Surface (ship-optimization, not blocker) |
| Gate-2b ear-passes (54+55 HUMAN-UAT) | partial/pending | **YES — feeds Gate 2b** |
| DEPS-08 (`livekit-plugins-openai` cull) | tech_debt, post-v3.1 | Surface as tech-debt (not ship-blocking) |

**Recommendation:** create ONE consolidated v4.0 ship surface — either a new top section in `KAAN-ACTION-LEGAL.md` (e.g. `## §SHIP-V4 — Consolidated Ship Surface`) cross-referencing the existing §SHIP-CUT runbook, or a sibling `.planning/phases/58-ship-readiness/58-KAAN-ACTION.md` that links into the canonical cookbook. Prefer extending the canonical file (single source of truth) with a clearly-dated v4.0 section that lists the shared external clock + the live ear-pass + the §E2E walk, each with its existing Sign-off block referenced. Mirror the existing 8-block format exactly.

## One-Button SHIP-CUT Dry-Run (REL-03)

**Finding:** `cut_release.sh` has **no `--dry-run` / `--no-sign` flag today.** It has a HARD GUARD comment ([cut_release.sh:32-33]) that even `--really`/`--real` never invoke `gh release create` — but no signature-stub mode. The Gate-2 signed-binary check ([L83]) is unconditional.

**What a green dry-run concretely requires:**
1. A real (unsigned) `.dmg` in `dist/` so `verify_signed.py` has a file to inspect.
2. A way to make Gate 2 pass WITHOUT a real signature — i.e. the stub. `verify_signed.py` itself (verify_signed.py:14-19) already exits 0 with `::notice::` when signing artifacts are absent UNLESS `--require-signed` is passed; Gate 2 passes `--require-signed` ([L83]). So the stub must either (a) drop `--require-signed` in dry-run mode, or (b) inject a fake ticket.
3. Gates 1, 3, 4, 5, 6 green (after the v2.1→v4.0 surgical fixes).
4. Gates 2b + 6b green via real-but-minimal inputs OR explicitly skipped-with-reason in dry-run mode (so the dry-run proves the WIRING, while the real flip waits on Kaan input).

**Recommendation (Claude's discretion area):** add a `--dry-run` flag to `cut_release.sh` that:
- Sets a `DRY_RUN=1` guard.
- Gate 2: runs `verify_signed.py` WITHOUT `--require-signed` (checksum-only, exits 0 on unsigned local `.dmg`) and prints `-- DRY-RUN: signature gate stubbed (EXTERNAL — Apple/SignPath)`.
- Gates 2b + 6b: if the real inputs aren't present, print `-- DRY-RUN: <gate> wired; awaiting Kaan input (54/55 ear-pass | §E2E walk)` and treat as PASS-for-dry-run while loudly logging the pending dependency. Do NOT silently green them in a real cut.
- All other gates run for real.
- On success print: "DRY-RUN GREEN — everything but the signature is ready. Real cut blocked only on: [Apple Dev Agreement, SignPath cert, 54/55 ear-pass, §E2E walk]."
- Pin the dry-run with a test (`tests/repo/test_cut_release_dry_run.py` or similar) asserting the flag exits 0 against the current tree + the stub log lines appear.

**Keep the hard guard absolute:** even `--dry-run` must never call `gh release create`. Add a regression test asserting the string `gh release create` only ever appears inside the printed heredoc, never as an executed command.

## §E2E-50A-WALK (REL-02)

Source: [docs/e2e/README.md], [tests/e2e/macbook/50a_kaan_walk_checklist.md], [scripts/e2e/record_50a_walk.sh].

**What the walk exercises:** install signed `.dmg` → load ≥10 min real DJ-set audio in djay Pro/rekordbox → arm screencast → walk the checklist (cold launch ≤3s first-mascot-frame, audio loopback connect, start live session, mascot persona transitions per `EVENT_LAYER_PRIORITY_MAP`, time-to-react per reaction) → score Tier-1 surfaces against `nielsen_10_checklist.json` (zero HIGH findings = bar) → transcode `.mov`→`.webm` → land at `docs/e2e/2026-05-walk.webm`.

**Recording recipe:** `bash scripts/e2e/record_50a_walk.sh --record` (macOS `screencapture -v -a`, Esc to stop) → `bash scripts/e2e/record_50a_walk.sh --transcode <raw>.mov` (ffmpeg VP9 + opus 32k, crf 32, ~18-24 MB target, <25 MB budget). ffmpeg 8.0.1 verified present.

**⚠️ BUG to fix (engineering, GREEN-NOW):** [record_50a_walk.sh:20-21] sets `REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` which resolves to `scripts/` (one level up from `scripts/e2e/`), then `OUT_DIR="${REPO_ROOT}/../docs/e2e"`. The `--record` path doesn't use `OUT_DIR` so the bug is latent, but `OUT_DIR` is computed wrong (resolves to repo-root/docs/e2e by accident of the double `..`, but `REPO_ROOT` itself is mislabeled as repo root when it's actually `scripts/`). `OUT_WEBM="docs/e2e/2026-05-walk.webm"` (relative to cwd) is correct only if run from repo root. Plan should fix `REPO_ROOT` to two-levels-up (`../..`) and make `OUT_WEBM` absolute, with a test, so the recipe works regardless of cwd. Confirm `.webm` target path = `docs/e2e/2026-05-walk.webm` ✓ (matches CONTEXT + record script + README).

**What engineering proves vs Kaan-action:**
- **Engineering (GREEN-NOW):** the app path the walk exercises is green (boot→listen→react→mascot — validated across Phases 51-57); the recording rig runs (`--record`/`--transcode` work, ffmpeg present, path bug fixed); `render_report.py` can produce a real `dist/e2e-macbook-runs/<UTC>/report.html` that `check_e2e_report.sh` (Gate 6b) accepts with all 5 dimensions PASS/PARTIAL/SKIPPED. Do NOT fake the report — produce it from a real `EeRun`.
- **KAAN-ACTION:** the actual recorded walk on the real Mac with real DJ-set audio → committed `docs/e2e/2026-05-walk.webm` (>25 MB → git-lfs). This is the Gate 6b feed + REQ E2E-06 (zero HIGH Nielsen findings).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Release pre-flight gating | A new cut script | Existing `cut_release.sh` (surgically re-pointed v2.1→v4.0) | The 8-gate driver + hard guard already exist + are battle-tested across 3 milestones |
| Hallucination gate | A new scoring harness | `check_gate.sh` + `check_ear_test.sh` (already wired as Gate 2b) | Per memory `project_phase_16_kaan_dj_testing` — Kaan-ear, NOT a 30-session replay harness |
| E2E report gate | A new report parser | `check_e2e_report.sh` + `render_report.py` | 5-dimension dataclass + Jinja template + bash parser, all Phase 50, all tested |
| Milestone audit | Hand-writing the audit md | `scripts/integration_audit.py --write-milestone-audit` | Auto-composes 7 sections + writes `overall_verdict: WIRED` deterministically (integration_audit.py:12,613,650) |
| Changelog | Hand-writing CHANGELOG | `scripts/launch/populate_changelog.py --tag <tag>` | Walks phase SUMMARY.md files, renders into the template |
| Sidecar build | A manual PyInstaller invocation | `scripts/build_sidecar.py` | Handles triple detection, onedir→externalBin rename, AIza-leak scan, anti-`--onefile` guard |
| KAAN-ACTION discharge surface | A new doc format | Extend `KAAN-ACTION-LEGAL.md` in its 8-block format | Single source of truth; CI greps it; the §SHIP-CUT runbook is already canonical |

**Key insight:** every artifact this phase needs already exists. The risk is NOT under-building — it's accidentally rebuilding (scope creep) or faking a green (fabricated `.webm`/report). The work is surgical re-pointing + real-artifact gate runs + documentation consolidation.

## Runtime State Inventory

> This phase is verify+wire+document — it does not rename/refactor runtime state. But it DOES touch a hardcoded version string that has runtime-adjacent implications, so the relevant categories:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — phase produces release artifacts + docs, no datastore writes | None (verified: gates are read-only probes + pytest) |
| Live service config | Gate 5b probes `api.altidus.world` (Bravoh prod) read-only. The Bravoh server must be UP + healthz cron fresh for Gate 5b green — but that is Bravoh-side ops, not vibemix-repo state | None in this repo; note Bravoh server readiness as a precondition for a real cut |
| OS-registered state | macOS TCC grants are keyed on bundle ID `world.bravoh.vibemix` (locked, Gate 6). Sidecar binary at `tauri/src-tauri/binaries/` is OS-arch-specific (two triples staged) | None — bundle ID stays locked; sidecar rebuild keeps the same triples |
| Secrets/env vars | `GEMINI_API_KEY` (sidecar build does NOT need it; AIza-leak scan asserts it is NOT in the bundle). Signing secrets (`APPLE_*`, `SIGNPATH_*`, `TAURI_UPDATER_PRIVATE_KEY`) are EXTERNAL/Kaan-action, referenced by `release.yml` | None autonomously — signing secrets are Kaan-action per P46 |
| Build artifacts | `dist/vibemix-core/` (33 MB onedir, 2026-05-20) + `tauri/src-tauri/binaries/vibemix-core-{aarch64,x86_64}-apple-darwin/` are CURRENT but the CONTEXT flags a "rebuild deferred from Phase 57" — re-run `build_sidecar.py` to confirm currency vs any post-2026-05-20 source change | Rebuild + verify sidecar; build a fresh local unsigned `.dmg` for the dry-run |

**Nothing found requiring data migration.** This is a release-cut phase, not a rename.

## Common Pitfalls

### Pitfall 1: cut_release.sh is hardcoded to v2.1 (THE blocker)
**What goes wrong:** Running `cut_release.sh v4.0.0-rc1` (or whatever the v4.0 tag is) fails Gate 1 immediately — `TAG_REGEX='^v2\.1\.0-rc[0-9]+$'` (L45). Even if you pass `v2.1.0-rc99`, Gate 4 then fails because `.planning/v2.1-MILESTONE-AUDIT.md` has `status: tech_debt`, not `WIRED`.
**Why it happens:** The script was written for the v2.1 RC cut (Phase 39) and never re-pointed across v3.0/v3.1/v4.0 (those milestones were engineering-green but never actually cut a public release — the external clock never discharged).
**How to avoid:** Surgically update (a) `TAG_REGEX` (L45) to the v4.0 scheme — DECIDE the tag (`v4.0.0-rc1`? or is the public RC still `v2.1.0-rc1` per the original product-versioning intent? this needs a decision — see Open Question 2), (b) the milestone-audit path (L122) to `v4.0-MILESTONE-AUDIT.md`, and (c) generate that audit via `integration_audit.py --write-milestone-audit`. Pin the new regex + path with a test.
**Warning signs:** Gate 1 prints "does NOT match" + refuses to cut; Gate 4 prints "verdict is not WIRED/passed".

### Pitfall 2: Faking a green Gate 2b or 6b
**What goes wrong:** The temptation to drop a hand-written `eval_report.json` or a synthetic `report.html` with all-PASS to make the gates green.
**Why it happens:** The real inputs (≥7 nightly proxy scorecards, ≥2 ear-test logs, the §E2E walk recording) are slow/Kaan-gated.
**How to avoid:** NEVER fabricate. The CONTEXT is explicit: "Do NOT fake the .webm. Do NOT simulate-green a gate." Engineering proves the WIRING (producer→consumer path green on a real minimal run) and PRE-WIRES the flip; the real inputs are KAAN-ACTION. The dry-run mode is the honest mechanism for "wired but awaiting input."
**Warning signs:** A `report.html` not produced by `render_report.py`; an `eval_report.json` without the real `.overall.*` aggregate fields; an ear-test log not matching `eval/ear-test-logs/schema.json`.

### Pitfall 3: Touching Kaan's ~17 uncommitted WIP files
**What goes wrong:** Phase 58 edits `tauri.conf.json5` (Gate 6 reads it), `audio/constants.py`, `prompts/matrix.py`, etc. — all of which Kaan has uncommitted persona/cooldown/audio tuning WIP in this session.
**Why it happens:** Gate 6 (bundle ID) reads `tauri.conf.json5`; a careless "fix" could clobber WIP.
**How to avoid:** Release-gate/doc work lives ONLY in `scripts/launch/`, `scripts/release/`, `scripts/e2e/`, `scripts/audit/`, `docs/`, `.planning/`, and `tests/repo/`+`tests/e2e/`. Do NOT edit `src/vibemix/**` or `tauri/src-tauri/src/**`. For Gate 6, only READ `tauri.conf.json5` (verify the identifier is unchanged); never write it. Confirm the gate file set is disjoint from the WIP set (it is — see verification below).
**Warning signs:** `git status` showing a release-phase edit to any `src/vibemix/` or `tauri/src-tauri/src/` file.

### Pitfall 4: Attempting an autonomous signature (P46 hard rule)
**What goes wrong:** Trying to discharge Apple Dev Agreement / SignPath cert / notarization autonomously.
**Why it happens:** "Make the gates green" pressure.
**How to avoid:** P46 is absolute — `verify-signed.yml`/`release.yml` grep for and FAIL on any autonomous POST/PUT to apple.com/signpath.io/notarytool. The signature gate (Gate 2) is EXTERNAL; the dry-run stubs it; the cookbook documents the Kaan/Francesco discharge. NEVER attempt the real signature.
**Warning signs:** any `curl`/`gh`/`Invoke-WebRequest` to apple/signpath in a script.

### Pitfall 5: Gate 5b depends on Bravoh prod being up
**What goes wrong:** Gate 5b probes `api.altidus.world` live; if the Bravoh server is down or the healthz cron stale (>10 min), the gate fails through no fault of the release artifacts.
**Why it happens:** It's a network probe of an external (Bravoh-side) service.
**How to avoid:** Classify Gate 5b as ENG-but-server-dependent. For the dry-run, either probe with the real endpoint (green when Bravoh is up) or note it as a server-readiness precondition. The cookbook should list "Bravoh server up + healthz fresh" as a SHIP-CUT precondition. Do NOT weaken the gate.

## Code Examples

### Build + verify the sidecar (REL-01 artifact prep)
```bash
# Source: scripts/build_sidecar.py:18-19 (verified header)
uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec
# → tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
# AIza-leak scan runs automatically (build_sidecar.py:13-16); aborts non-zero on any AIza match
```

### Build a local unsigned .dmg (for the dry-run Gate 2 stub)
```bash
# Tauri consumes the staged sidecar via externalBin; build (NOT sign) locally
cargo tauri build   # produces target/release/bundle/dmg/*.dmg (unsigned)
# copy into dist/ so verify_signed.py (checksum-only, no --require-signed) has a real file
```

### Generate the v4.0 milestone audit (Gate 4)
```bash
# Source: scripts/integration_audit.py:12-13, :720 (verified)
python scripts/integration_audit.py --write-milestone-audit .planning/v4.0-MILESTONE-AUDIT.md
# writes frontmatter `overall_verdict: WIRED` iff all seams green (integration_audit.py:613,650)
```

### Run a single gate green-now (Gate 6 example)
```bash
# Source: cut_release.sh:155 (verified)
python3 -m pytest tests/security/test_bundle_id_locked.py -q --no-header
```

### Produce a real Gate-6b report (NOT faked)
```python
# Source: tests/e2e/macbook/render_report.py:26-42 (verified)
from tests.e2e.macbook.dimensions import EeRun
from tests.e2e.macbook.render_report import render
run = EeRun(run_id="2026-05-21T00-00-00Z")  # populate dimensions from a real run
report_path = render(run)  # → dist/e2e-macbook-runs/<run_id>/report.html
# then: bash scripts/e2e/check_e2e_report.sh  # Gate 6b
```

### The SHIP-CUT runbook (already canonical — REL-03 references this)
```bash
# Source: KAAN-ACTION-LEGAL.md:319-327 (verified) — the existing 9-step runbook
python scripts/launch/populate_changelog.py --tag <TAG>   # renders CHANGELOG-<TAG>.md
bash scripts/launch/cut_release.sh <TAG>                   # 8 gates; prints (never runs) gh release create
# Kaan copies + runs the printed `gh release create ... --draft` command
# then: gh release edit <TAG> --draft=false --repo bravoh/vibemix
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cut gate hardcoded to `v2.1.0-rc` | (needs) v4.0-aware tag regex + audit path | Phase 58 (this) | Surgical re-point required before any v4.0 cut |
| `v2.1-MILESTONE-AUDIT.md` (tech_debt) | (needs) `v4.0-MILESTONE-AUDIT.md` (WIRED) | Phase 58 (this) | Gate 4 input must be regenerated for v4.0 |
| No dry-run / signature-stub mode | (needs) `--dry-run` flag stubbing Gate 2 | Phase 58 (this) | "One-button-after-signatures" proof mechanism |
| P85 Phase 16 ear-test override | RETIRED (Plan 42-05) — Kaan-ear back in force | v3.0 | Gate 2b ear-test leg is mandatory; no autonomous-only bypass |

**Deprecated/outdated:**
- The "autonomous-only ear-test bypass" (P85 override) is formally RETIRED — do not resurrect it to green Gate 2b. The cut_release.sh exit reminder still flags the historical anchor (cut_release.sh:191-196).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The v4.0 public RC tag scheme is undecided (v4.0.0-rc1 vs keeping v2.1.0-rc1 product versioning) — Gate 1 regex must be updated to *something* | Pitfall 1 / Open Q2 | If wrong tag scheme chosen, Gate 1 stays red or a wrong-versioned release is cut. NEEDS Kaan decision |
| A2 | The sidecar (built 2026-05-20) may be stale relative to Kaan's WIP source edits in this session; rebuild confirms currency | Real Artifact Build / RSI | If WIP changed sidecar-relevant code, the staged binary is stale — rebuild catches it |
| A3 | Gate 2b nightly leg needs ≥7 real proxy scorecards in `.planning/eval-runs/` in the `.overall.*` format; current dir has only `loadtest_*.json` (wrong format) | Gate inventory / Open Q1 | If no real nightly canary has run 7 days, the nightly leg can't go green this phase — may itself be a carry-forward |
| A4 | Adding `--dry-run` to cut_release.sh is the right mechanism (vs a separate runner script) | Dry-run section | Low — either works; flag keeps single source of truth |
| A5 | Extending KAAN-ACTION-LEGAL.md (vs a new 58-KAAN-ACTION.md) is preferred | Cookbook section | Low — both viable; extending keeps SSOT |
| A6 | Bravoh prod server (`api.altidus.world`) will be up + healthz-fresh at cut time | Pitfall 5 | Gate 5b red if server down — a real-cut precondition, not an engineering bug |

## Open Questions

1. **Gate 2b nightly proxy leg — are there ≥7 real nightly scorecards?**
   - What we know: `check_gate.sh` needs 7 consecutive `.planning/eval-runs/<run>/eval_report.json` with `.overall.{f1,useful_response_ratio,cited_cosine,bypass_rate}` (check_gate.sh:161-167). The dir currently holds `loadtest_*.json` (latency benchmarks, wrong shape).
   - What's unclear: whether the nightly canary CI has actually been running + landing scorecards. If not, the nightly leg can't go green this phase.
   - Recommendation: inventory `.planning/eval-runs/` for real scorecards; if absent, surface the nightly leg as a carry-forward (the gate is WIRED; the data is pending), and lean on the ear-test leg + dry-run to prove the wiring.

2. **What is the v4.0 public RC tag?** (needs Kaan decision)
   - What we know: Gate 1 regex is `^v2\.1\.0-rc[0-9]+$`; product versioning intent (P83) was "no premature v1.0.0". Git tags show `v2.1.0`, `v3.0`, `v3.1` already exist as milestone tags.
   - What's unclear: whether the public OSS release cuts as `v0.1.0-rc1` (pyproject says `version = "0.1.0-dev0"`; the public-facing version) or continues the internal milestone numbering. The internal milestone (v4.0) ≠ the public artifact version (likely v0.1.0 for a first OSS release).
   - Recommendation: surface to Kaan. The README hero / public pitch is a first OSS release → likely `v0.1.0-rc1`. The cut_release Gate 1 regex must match whatever is chosen. This is a discuss-phase / plan-time decision.

3. **Does the unsigned local `.dmg` build succeed headlessly on this Mac?**
   - What we know: sidecar builds; Tauri externalBin is staged.
   - What's unclear: whether `cargo tauri build` completes without signing config errors (it should produce an unsigned bundle).
   - Recommendation: attempt the unsigned build early in the phase; if it errors on signing, the dry-run can still use the existing `dist/vibemix-0.1.0.dev0-py3-none-any.whl` or a stub artifact for the Gate-2 path proof, but a real `.dmg` is preferred.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `jq` | Gate 2b (check_gate, check_ear_test) | ✓ | 1.8.1 | none needed |
| `ffmpeg` | §E2E walk transcode | ✓ | 8.0.1 | none needed |
| `python3` | gate pytest legs + builds | ✓ | 3.12 (.venv) | none needed |
| `cargo tauri` | local `.dmg` build | macOS — assume present (Tauri dev used in prior phases) | — | use whl/stub for dry-run Gate 2 proof |
| PyInstaller | sidecar build | ✓ (via uv.lock; sidecar built 2026-05-20) | — | existing staged sidecar |
| `curl` | Gate 5b Bravoh probe | ✓ | system | none |
| Bravoh prod server | Gate 5b | external (server-side) | — | none — server-readiness precondition |
| Apple Dev cert / SignPath cert | Gate 2 (real cut) | ✗ EXTERNAL | — | dry-run stub (no fallback for real cut — Kaan-action) |

**Missing dependencies with no fallback (block REAL cut, NOT this phase's engineering):**
- Apple Developer Program Agreement acceptance (Francesco) + SignPath OSS cert (Kaan). EXTERNAL clock. This phase makes the cut one-button-after-these; it does NOT block on them.

**Missing dependencies with fallback (this phase):**
- Real signed `.dmg` → dry-run uses unsigned local `.dmg` with the signature gate stubbed.
- ≥7 nightly proxy scorecards → if absent, the wiring is proven via the ear-test leg + dry-run; the data is a carry-forward.

## Validation Architecture

> `nyquist_validation: true` in config.json — section included.

The honest split: **the runnable gates + dry-run + cookbook completeness are testable now; the recorded E2E walk + live ear-pass + signatures are KAAN-ACTION.**

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (Python 3.12) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/repo/test_bundle_... -q` (per-gate) |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-01 | Gate 1 tag regex accepts the v4.0 tag | unit | `pytest tests/repo/test_cut_release_tag_regex.py -x` | ❌ Wave 0 (new pin for the surgical regex change) |
| REL-01 | Gate 3 README hero hash green | gate | `bash -c 'cd repo && pytest tests/repo/test_readme_hero_hash_sync.py -q'` | ✅ |
| REL-01 | Gate 4 v4.0 milestone audit WIRED | gate | `python scripts/integration_audit.py --write-milestone-audit .planning/v4.0-MILESTONE-AUDIT.md` then grep verdict | ✅ (generator) / ❌ audit file Wave 0 |
| REL-01 | Gate 5 POC retired | gate | `pytest tests/repo/test_g5_poc_files_untouched.py -q` | ✅ |
| REL-01 | Gate 6 bundle ID locked | gate | `pytest tests/security/test_bundle_id_locked.py -q` | ✅ |
| REL-01 | Gate 2b ear-test leg parses schema-valid logs | gate | `bash scripts/release/check_ear_test.sh` | ✅ (input KAAN-gated) |
| REL-01 | Gate 6b parses a real report with no FAIL | gate | `bash scripts/e2e/check_e2e_report.sh` | ✅ (needs a real run produced) |
| REL-02 | Recording rig path-correct + ffmpeg present | unit | `pytest tests/repo/test_record_50a_walk_paths.py -x` | ❌ Wave 0 (pin the path-bug fix) |
| REL-02 | `render_report.py` produces a Gate-6b-valid report | integration | `pytest tests/e2e/macbook/test_report_render.py -q` | ✅ |
| REL-03 | `cut_release.sh --dry-run` exits 0 with signature stubbed | integration | `pytest tests/repo/test_cut_release_dry_run.py -x` | ❌ Wave 0 (new flag + pin) |
| REL-03 | `gh release create` never executed (hard guard) | unit | `pytest tests/repo/test_cut_release_no_autonomous_publish.py -x` | ❌ Wave 0 (regression guard) |
| REL-03 | Cookbook lists all open carry-forwards | unit | `pytest tests/repo/test_kaan_action_v4_surface.py -x` | ❌ Wave 0 (completeness pin) |

### Sampling Rate
- **Per task commit:** the specific gate/test touched (`pytest <file> -q`)
- **Per wave merge:** all `tests/repo/` + `tests/e2e/macbook/` + the dry-run
- **Phase gate:** full suite green + `bash scripts/launch/cut_release.sh --dry-run <TAG>` exits 0 before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/repo/test_cut_release_tag_regex.py` — pins the v2.1→v4.0 regex change (REL-01)
- [ ] `tests/repo/test_cut_release_dry_run.py` — pins `--dry-run` exits 0 + stub log lines (REL-03)
- [ ] `tests/repo/test_cut_release_no_autonomous_publish.py` — pins `gh release create` never executed even in dry-run (REL-03, hard guard)
- [ ] `tests/repo/test_record_50a_walk_paths.py` — pins the OUT_DIR/OUT_WEBM path fix (REL-02)
- [ ] `tests/repo/test_kaan_action_v4_surface.py` — pins the consolidated cookbook lists all open carry-forwards (REL-03)
- [ ] `.planning/v4.0-MILESTONE-AUDIT.md` — generated artifact (Gate 4 input), not a test but a Wave-0 deliverable
- [ ] Framework install: none — pytest infra exists

**KAAN-ACTION (NOT testable by engineering — explicit):**
- The recorded `docs/e2e/2026-05-walk.webm` (REL-02) — real Mac + real audio + Kaan ear.
- Gate 2b ear-test logs content (54+55 HUMAN-UAT live ear-pass) — Kaan's "real DJ friend in ear" sign-off.
- The actual signed publish (Apple Dev Agreement + SignPath cert) — EXTERNAL clock.

## Security Domain

> `security_enforcement` absent in config → treat as enabled. This is a release phase; security posture centers on supply-chain + signing + secret-leak.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a (release-cut phase) |
| V5 Input Validation | yes | Gate scripts treat scorecard/ear-test JSON as untrusted — `check_gate.sh` parses via `jq` only, never `eval`/`$(...)` (check_gate.sh:34-36 threat note T-42-04-01) |
| V6 Cryptography | yes | Signing via Apple Developer ID + SignPath OSS; updater ed25519 (NEVER hand-roll; private keys never in repo — KAAN-ACTION-LEGAL §4/AUDIO-06) |
| V10 Malicious Code | yes | `build_sidecar.py` AIza-leak scan over the bundle (build_sidecar.py:13-16); gitleaks + `.secrets.baseline` |
| V14 Configuration | yes | Bundle ID locked (Gate 6); P46 forbidden-autonomous-POST grep in `verify-signed.yml`/`release.yml` |

### Known Threat Patterns for the release toolchain
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Embedded API key leak in shipped binary | Information Disclosure | `AIza[A-Za-z0-9_-]{35}` scan at build time (build_sidecar.py) + Bravoh-proxy (no raw key shipped) |
| Autonomous agent forging a signature/publish | Elevation / Spoofing | P46 hard rule — CI greps forbid POST/PUT to apple.com/signpath.io/notarytool; `cut_release.sh` never runs `gh release create` |
| Untrusted scorecard JSON injection | Tampering | `jq`-only parse, no shell `eval` (check_gate.sh T-42-04-01) |
| Fabricated green gate (faked report/log) | Tampering | Reports only via `render_report.py`; ear-test logs validated against `schema.json`; CONTEXT forbids simulated-green |
| Bundle-ID flip resetting TCC grants | Tampering | `test_bundle_id_locked.py` pins `world.bravoh.vibemix` (Gate 6) |

## Sources

### Primary (HIGH confidence — all verified on disk, file:line)
- `scripts/launch/cut_release.sh` (full read) — 8-gate driver, tag regex, milestone-audit path, hard guard
- `scripts/release/check_gate.sh` (full read) — Gate 2b nightly proxy + ear-test composition
- `scripts/release/check_ear_test.sh` (full read) — ear-test 3-invariant gate
- `scripts/e2e/check_e2e_report.sh` (full read) — Gate 6b 5-dimension parser
- `scripts/e2e/record_50a_walk.sh` (full read) — recording rig + the OUT_DIR path bug
- `scripts/build_sidecar.py` (header) — sidecar build pipeline + AIza scan
- `scripts/release/audit_ship_v1_decision.py` (header) — SHIP-V1 evidence pre-filler
- `scripts/release/check_bravoh_server_ready.sh` (header) — Gate 5b 3-endpoint probe
- `scripts/dist/verify_signed.py` (header) — Gate 2 signed-binary verifier (exits 0 unsigned unless --require-signed)
- `scripts/launch/populate_changelog.py` (header) — changelog auto-populator
- `tests/e2e/macbook/render_report.py` (full read) — Gate-6b report producer
- `tests/e2e/macbook/dimensions.py` (grep) — 5 dimensions incl. Hallucination
- `tests/e2e/macbook/50a_kaan_walk_checklist.md` (head) — walk steps
- `docs/e2e/README.md` (full read) — §E2E-50A-WALK discharge procedure + .webm budget
- `KAAN-ACTION-LEGAL.md` (lines 1-984 of 3385) — cookbook structure, P46 carveouts, §SHIP-CUT runbook
- `.planning/STATE.md` (full read) — carry-forward KAAN-ACTION items, blockers, invariants
- `.planning/REQUIREMENTS.md` (full read) — REL-01/02/03 + traceability
- `.planning/phases/58-ship-readiness/58-CONTEXT.md` (full read) — locked decisions
- `tests/security/test_bundle_id_locked.py`, `tests/repo/test_readme_hero_hash_sync.py` (heads) — Gate 6/3 pins
- On-disk state: `git tag`, `dist/` listing, `pyproject.toml` version, `tauri.conf.json5` version, `.planning/eval-runs/` + `eval/ear-test-logs/` contents, `tauri/src-tauri/binaries/` triples, milestone-audit files, config.json

### Secondary / Tertiary
- None — this phase is fully grounded in-tree; no WebSearch/Context7 needed (no external libraries, no API research).

## Metadata

**Confidence breakdown:**
- Gate inventory + classification: HIGH — every gate read at file:line, every input dir inspected on disk
- Real artifact build path: HIGH — sidecar built artifacts confirmed present; build_sidecar.py header verified; .dmg-build is the one unverified-headless step (Open Q3)
- KAAN-ACTION cookbook: HIGH — KAAN-ACTION-LEGAL.md + audit_ship_v1_decision.py + STATE carry-forwards all read
- Dry-run mechanism: MEDIUM — recommendation is sound but the exact stub design is Claude's-discretion; no existing flag to verify against
- Pitfalls: HIGH — the v2.1-hardcoded blocker + faked-green + WIP-collision risks are all evidenced on disk
- Tag scheme (Open Q2): LOW — undecided, needs Kaan; flagged as A1

**Research date:** 2026-05-21
**Valid until:** ~2026-06-04 (14 days — stable in-tree machinery; the only moving part is Kaan's WIP which may change sidecar source + the tag decision)
