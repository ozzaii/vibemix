# Phase 46 Context — Dependency Audit + Lockfile + AUDIT.md

**Date:** 2026-05-18
**Mode:** `gsd-autonomous fully` / `gsd-discuss-phase --auto` — all grey areas auto-resolved with recommended defaults; no AskUserQuestion calls; defer blockers to Kaan-action surface.
**Discuss pass:** 1 of 1 (single-pass cap per `modes/auto.md`).

---

## Domain

This phase delivers a hermetic, auditable dependency surface across all three ecosystems (Python / Rust / JS) plus GitHub Actions, with a single human-readable rationale + install-impact rating table at `docs/AUDIT.md`, a CI freshness gate that prevents lockfile/audit drift, a CycloneDX SBOM joining the existing syft SPDX, and a dep-cull pass that retires the three suspected unused transitives carried over from Kaan's `.venv` pip-freeze era.

**This phase is build-time + CI + docs only — zero runtime code edits.** POC files (`cohost*.py`) and the Tauri runtime surface stay byte-identical.

---

## Locked Requirements (from REQUIREMENTS.md § DEPS)

- **DEPS-01** — Python deps regenerated from curated `requirements.in` into hermetic `uv.lock` inside `python:3.12-slim-bookworm` container (no `pip freeze` from Kaan's `.venv`).
- **DEPS-02** — Rust deps pinned in `Cargo.lock`; `cargo-deny` `deny.toml` enforces license allowlist (Apache-2.0/MIT/BSD/ISC/Unicode-DFS-2016/MPL-2.0) + GPL ban; CI fails on policy violation.
- **DEPS-03** — JS deps pinned in `package-lock.json` (frozen lockfile install in CI); npm-audit signal surfaced as PR comment.
- **DEPS-04** — `docs/AUDIT.md` ships 3-table surface (Python / Rust / JS) — every direct dep with version + license + rationale + green/yellow/red install-impact rating per memory `project_one_click_install_hard_req`.
- **DEPS-05** — CI freshness gate `scripts/audit/check_audit_freshness.sh` invoked by `.github/workflows/dep-audit.yml` fails any PR whose lockfile mtime is newer than `docs/AUDIT.md`.
- **DEPS-06** — CycloneDX SBOM via `cyclonedx-python==7.3.0` alongside existing syft SPDX; both SBOMs attached to GH release assets.
- **DEPS-07** — GH Actions SHAs pinned via `pinact` v3.x (no `@vX` floating refs); audit script runs on PR.
- **DEPS-08** — Dep-cull pass: `livekit-plugins-openai`, `google-cloud-speech`, `google-cloud-texttospeech` either removed or formally re-justified; decision logged in `docs/AUDIT.md`.
- **DEPS-09** — README dep-health badges (uv lock status / cargo-deny / npm-audit / CycloneDX SBOM) wired to CI status.
- **DEPS-10** — Dependabot configured for Python (`uv`) + Cargo + npm + GH Actions with weekly cadence and security-only patch policy.

---

## Canonical Refs (downstream MUST read these before planning)

- `.planning/ROADMAP.md` § Phase 46 — goal, success criteria, invariants
- `.planning/REQUIREMENTS.md` § DEPS-01..DEPS-10 — locked acceptance criteria
- `.planning/research/PITFALLS.md` § Pitfall 1 — hermetic-build mandate (`pip freeze` from `.venv` = critical regression)
- `.planning/codebase/STACK.md` — installed-dep observed list (basis for the "is this transitive actually used?" cull)
- `.planning/codebase/CONCERNS.md` — Dependencies-at-Risk section (cited by Pitfall 1)
- `pyproject.toml` — current direct-dep declaration with extensive `[tool.uv.sources]` overrides (e.g., pyrekordbox `--no-deps` install recipe at lines 28+); rationale comments already embedded inline — AUDIT.md harvests these
- `uv.lock` — current hermetic resolution (regenerate inside container, do not freeze from `.venv`)
- `tauri/src-tauri/Cargo.toml` + `Cargo.lock` + `deny.toml` — existing Rust pin + license policy surface
- `tauri/ui/package.json` + `package-lock.json` — existing JS pin surface
- `.github/workflows/python-cve.yml`, `rust-cve.yml`, `sbom.yml` — existing CI gates (extend, don't duplicate)
- `.github/workflows/model-literal-check.yml` — pattern for extending CI grep gates (AUDIT.md generator output must NOT inline `gemini-*` literals — invariant)
- Memory anchors: `project_one_click_install_hard_req` (green/yellow/red rating mandate), `feedback_no_clap_use_gemini_embedding` (Gemini-only — any cull suggestion proposing CLAP/MERT/OpenL3 is REJECTED), `feedback_no_scope_creep_clean_utility` (no Snyk/Black Duck enterprise tooling), `feedback_worktree_must_sync_main_first` (Step-0 invariant for any subagent prompt).

---

## Decisions (auto-resolved per `--auto` recommended defaults)

### Lockfile Generation Strategy

- **[auto] Q: How are Python deps locked?** → **`uv` workflow with curated `requirements.in`-equivalent (`pyproject.toml` `[project.dependencies]` as source of truth) + `uv.lock` regenerated hermetically in `python:3.12-slim-bookworm` container.** (recommended default; Pitfall 1 mandates hermetic build; `uv==0.11.14` per `.planning/research/STACK.md`).
- **[auto] Q: Where does the hermetic builder run?** → **CI workflow `.github/workflows/dep-audit.yml` invokes the container via `docker run --rm -v "$PWD":/work python:3.12-slim-bookworm bash -lc "..."` — never on Kaan's `.venv`.** Same workflow regenerates and diffs the lock against the committed version; PR fails on drift.
- **[auto] Q: Pyproject preserves the pyrekordbox `--no-deps` override (line 28+ recipe)?** → **YES.** The `[tool.uv.sources]` override + manual transitives (bidict, construct, blowfish, etc.) is load-bearing; AUDIT.md rationale column documents WHY (SQLCipher path dormant, stdlib-sqlite3 fallback).

### `docs/AUDIT.md` Structure

- **[auto] Q: One file with 3 tables or 3 separate files?** → **Single `docs/AUDIT.md` with 3 H2 sections (Python / Rust / JS) + a 4th § Decisions section for dep-cull + § GitHub Actions for `pinact` audit output.** Roadmap success criterion 3 explicitly says "3-table surface" in a single doc.
- **[auto] Q: Table column shape?** → Columns: `Package | Version | License | Rationale | Install-Impact (G/Y/R) | Notes`. Install-Impact rendered as emoji (🟢/🟡/🔴) for at-a-glance scan; `Notes` column carries cull/defer markers and links to ADRs if any.
- **[auto] Q: Rating rubric (G/Y/R)?** → Defined inline in AUDIT.md preamble per `project_one_click_install_hard_req`:
  - **🟢 Green** — Pure-Python wheel or rustc/npm pure dep; no native build, no OS extension, no driver, no user prompt during installer. Falls into one-click happy path without remediation.
  - **🟡 Yellow** — Native wheel or Rust crate with `cc`/system lib dep that has prebuilt binaries for both Mac (arm64+x86_64) AND Win64 on PyPI/crates.io; installer ships the binary, no user action required, but a missing-wheel platform variant would require a fallback. Includes deps with optional native paths that we explicitly disable (e.g., pyrekordbox SQLCipher disabled).
  - **🔴 Red** — Requires a system extension, kernel driver, OS-Settings approval, manual brew/winget install, or any prompt the user must consent to (BlackHole, VB-CABLE, system MIDI driver are external-to-package and surface in Phase 49 installer; this rating column treats Python/Rust/JS package install only — driver coverage is Phase 49's table).
- **[auto] Q: AUDIT.md generation — handwritten or generated?** → **Hybrid: `scripts/audit/gen_audit_md.py` produces a draft AUDIT.md from lockfile metadata (version + license auto-pulled via `uv pip licenses --format=json` or equivalent + `cargo-license --json` + `license-checker --json`); rationale + install-impact columns sourced from a YAML side-file `scripts/audit/dep_ratings.yaml` that Kaan/agents author manually.** The generated file is committed (not gitignored) so the PR diff shows what changed. Drift = generated AUDIT.md doesn't match committed `dep_ratings.yaml` ratings → CI flags.

### CI Freshness Gate

- **[auto] Q: How does the freshness gate define "stale"?** → **`scripts/audit/check_audit_freshness.sh` compares git-tracked mtimes of `uv.lock`, `Cargo.lock`, `tauri/ui/package-lock.json` against `docs/AUDIT.md` AND `scripts/audit/dep_ratings.yaml` using `git log -1 --format=%ct <file>` (last-commit-time, not filesystem mtime — mtime is unstable on fresh clones).** Fails the PR if any lockfile's last-commit-time is newer than the audit doc's last-commit-time.
- **[auto] Q: What CI workflow file?** → **New `.github/workflows/dep-audit.yml`** — runs freshness gate, hermetic uv regenerate + diff, cargo-deny check, npm-audit-with-PR-comment, pinact audit. Existing `python-cve.yml` + `rust-cve.yml` stay for CVE-specific gates (don't duplicate).

### Dep-Cull Pass (DEPS-08)

- **[auto] Q: Default position on the three suspected transitives?** → **REMOVE all three (`livekit-plugins-openai`, `google-cloud-speech`, `google-cloud-texttospeech`).** Justification per memory `feedback_no_clap_use_gemini_embedding` (Gemini-only — never propose Google Cloud Speech/TTS as alternatives) and per `.planning/codebase/STACK.md`: "Installed but not directly imported in main cohost files" + "Installed as livekit-agents transitive dep; not used directly in cohost code." Each removal verified by:
  1. `rg -n "from google.cloud.speech|google.cloud.texttospeech|livekit.plugins.openai|livekit_plugins_openai" --type py src/` returns zero matches.
  2. Full test suite (`uv run pytest`) green after removal.
  3. v3.0 GATE-02 VCR cassette re-record check: removing these does NOT touch `google-genai==2.0.1` resolution → cassettes unaffected.
- **[auto] Q: What if `livekit-agents` pulls them as a hard transitive?** → If so, document via `pip-deptree --reverse <pkg>` output pasted into AUDIT.md § Decisions; mark as 🟡 with "transitive of livekit-agents, not imported directly, retained until upstream drops" rationale. This is a fallback — primary path is removal.
- **[auto] Q: Are `bidict`, `construct`, `blowfish` (pyrekordbox transitives explicitly declared in pyproject.toml) culled?** → **NO.** Keep — the `[tool.uv.sources]` override declared them deliberately because pyrekordbox uses `--no-deps`; they're real direct deps from vibemix's POV. AUDIT.md rationale column documents this.

### SBOM Strategy (DEPS-06)

- **[auto] Q: Replace syft SPDX with CycloneDX, or ship both?** → **Ship BOTH.** Roadmap success criterion 4 says "GH release assets contain BOTH CycloneDX `vibemix.cdx.json` and syft SPDX `vibemix.spdx.json`." Existing `.github/workflows/sbom.yml` already emits SPDX via syft — extend to also run `cyclonedx-py environment` (cyclonedx-python==7.3.0) against the uv-resolved env and `cargo cyclonedx` for Rust. JS gets `@cyclonedx/cdxgen` or equivalent.
- **[auto] Q: SBOM-cull or surface every transitive?** → **Surface every transitive** (SBOM is per-spec a full inventory). The AUDIT.md surface stays direct-deps-only; SBOM is the deep inventory.

### GH Actions SHA Pinning (DEPS-07)

- **[auto] Q: `pinact` or hand-roll?** → **`pinact` v3.x** per Constraint block in task spec. Audit script runs on PR; fails if any `uses:` line in `.github/workflows/*.yml` references a tag (`@vX`) instead of a SHA + version comment.
- **[auto] Q: Migrate all workflows in one PR or per-file?** → **One PR (part of Phase 46 final integration plan).** `pinact run` is mechanical; review burden is the SHA list.

### Dependabot (DEPS-10)

- **[auto] Q: Single `dependabot.yml` or split per ecosystem?** → **Single `.github/dependabot.yml`** with 4 `package-ecosystem` blocks (`pip` with `enable-beta-ecosystems: true` for uv; `cargo`; `npm`; `github-actions`). Cadence: weekly. Security-only patch policy: `open-pull-requests-limit: 5` + `ignore` block for non-security major bumps (Kaan-driven majors only).
- **[auto] Q: Auto-merge security patches?** → **NO** — keep PR review in the loop. Memory `feedback_autonomous_no_grey_area_pause` applies to *engineering work*, not unattended infra auto-merge.

### Anti-slop blocklist invariant extension

- **[auto] Q: Which gen-script outputs join the blocklist grep target?** → **`docs/AUDIT.md`, `scripts/audit/*.{py,sh}` generator output, `docs/dep-opportunities/*.md` (Phase 48 surface — pre-emptively included), `dep_ratings.yaml`.** Extend `scripts/ci/check_no_ai_slop.py` (or whatever the existing slop grep target list is named) to include these paths. Verify via grep gate in CI.

### ModelRouter seam invariant

- **[auto] Q: Can AUDIT.md mention `gemini-*` model literals?** → **NO.** AUDIT.md MAY mention `google-genai` (the SDK package), `livekit-plugins-google` (the LiveKit adapter), but MUST NOT inline any `gemini-3-flash-preview`, `gemini-2.5-flash-native-audio-preview-12-2025`, etc. Verified by extending `.github/workflows/model-literal-check.yml` grep target to include `docs/AUDIT.md` + `scripts/audit/`.

### Privacy invariant

- **[auto] Q: Which paths can audit scripts write to?** → **Only `docs/AUDIT.md`, `scripts/audit/**`, `dep_ratings.yaml`, `dep_ratings.json`, `.planning/phases/46-*/`, and CI-produced SBOM artifacts under `dist/sbom/`.** Per memory `feedback_privacy_scope_narrow` privacy rule is narrow (Hermes/OZ/LM Studio transcript paths only) — audit scripts have FULL project FS access; only off-limits paths are the privacy-rule list.

---

## Plan Decomposition (locked — planner uses this as input)

Six plans, atomic commits each, ordered for clean serial execution (parallelization deferred to planner — but file-boundary independence noted):

1. **46-01-PLAN.md — Hermetic uv lockfile regeneration + `requirements.in` discipline** (DEPS-01) — files: `pyproject.toml` (preserve overrides), `uv.lock` (regenerate in container), new `scripts/audit/regen_uv_lock.sh`, new `.github/workflows/dep-audit.yml` (uv-regen + diff step only).
2. **46-02-PLAN.md — Cargo + cargo-deny license policy + npm frozen lockfile + npm-audit PR comment** (DEPS-02, DEPS-03) — files: `tauri/src-tauri/deny.toml` (extend allowlist + GPL ban), `tauri/ui/package-lock.json` (verify shrinkwrap), `.github/workflows/dep-audit.yml` (cargo-deny + npm steps).
3. **46-03-PLAN.md — `docs/AUDIT.md` + `dep_ratings.yaml` + `gen_audit_md.py` generator + freshness gate** (DEPS-04, DEPS-05) — files: `docs/AUDIT.md`, `scripts/audit/dep_ratings.yaml`, `scripts/audit/gen_audit_md.py`, `scripts/audit/check_audit_freshness.sh`, `.github/workflows/dep-audit.yml` (freshness gate step).
4. **46-04-PLAN.md — CycloneDX SBOM (Python + Rust + JS) alongside syft SPDX, dep-cull pass with verification, `dep_ratings.json` schema** (DEPS-06, DEPS-08) — files: `.github/workflows/sbom.yml` (extend), new `scripts/audit/gen_cyclonedx.sh`, `pyproject.toml` (cull entries), `uv.lock` (regenerated), `docs/AUDIT.md` § Decisions block populated, `dep_ratings.json` schema spec'd.
5. **46-05-PLAN.md — `pinact` v3.x GH Actions SHA pinning + audit on PR** (DEPS-07) — files: every `.github/workflows/*.yml` (SHA pin migration), `.github/workflows/dep-audit.yml` (pinact audit step), new `scripts/audit/run_pinact.sh`.
6. **46-06-PLAN.md — README dep-health badges + Dependabot 4-ecosystem config + final integration verification** (DEPS-09, DEPS-10) — files: `README.md` (badge block), new `.github/dependabot.yml`, final `.github/workflows/dep-audit.yml` polish.

**Sequencing notes:**
- Plan 1 must precede Plan 4 (regen lock before culling deps from the regenerated lock).
- Plan 3 must precede Plan 6 (AUDIT.md must exist before its badge can point to its CI gate).
- Plans 1+2 share `.github/workflows/dep-audit.yml` — planner sequences them, then merges.
- Plans 5+6 can run after Plans 1–4 land; they don't touch lockfile content.

---

## Invariants Touched (planner must verify each plan)

- **ModelRouter seam** — AUDIT.md must NOT inline `gemini-*` literals. Verified by extending `model-literal-check.yml` grep target.
- **Anti-slop blocklist** — extend grep target to `docs/AUDIT.md` + `scripts/audit/` generator output + `docs/dep-opportunities/` (pre-emptive for P48).
- **Privacy rule** — audit scripts write only to `docs/AUDIT.md`, `scripts/audit/**`, `dep_ratings.json`/`yaml`, `dist/sbom/`. Verified by greppable allow-list inside script preamble.
- **POC immutability** — zero edits to `cohost*.py`, `mascot.html`. Verified by file-set in each plan's commit not touching these paths.
- **Worktree-Subagent Invariant** — every plan that spawns a subagent MUST embed the Step-0 block (`cd <worktree> && git fetch origin main && git merge origin/main --no-edit`). Plan-checker rejects any plan missing it.

---

## Kaan-Action Surface (deferred items — autonomous-mode continues)

None expected at engineering-green close. Possible deferrals if research surfaces them:
- If `livekit-agents` HARD-imports `livekit-plugins-openai` (cull would fail) — defer with formal re-justification in AUDIT.md § Decisions (auto-handled in plan 4).
- If CycloneDX Rust generator (`cargo cyclonedx`) has a known compatibility break with Tauri 2.x — fall back to manual SPDX-only for Rust + note in AUDIT.md § Decisions (Yellow risk; engineering proceeds).

No legal-capacity carveouts (no Apple Dev / SignPath dependency in Phase 46).

---

## Out of Scope (deferred to other phases or backlog)

- Driver-level install impact ratings (BlackHole, VB-CABLE, system MIDI) — Phase 49 installer companion territory; Phase 46's G/Y/R column scope is Python/Rust/JS packages only.
- New-dep opportunity scan (Mixxx OSC, controller map transpiler, pyrekordbox depth) — Phase 48.
- E2E MacBook harness integration of the audit gate — Phase 50 wires the e2e gate, not Phase 46.
- Vendor SBOM tooling (Snyk, Black Duck, Sonatype) — `feedback_no_scope_creep_clean_utility` rejects enterprise SBOM stack; cyclonedx-python + syft + cargo-license is sufficient.
- CLAP / MERT / OpenL3 alternatives surfaced by dep-cull — auto-REJECTED per `feedback_no_clap_use_gemini_embedding`.
- Auto-merge of Dependabot security PRs — kept manual for review-in-the-loop.

---

## Auto-mode audit trail

[auto] Discuss-mode: --auto (gsd-autonomous fully).
[auto] All 12 gray areas auto-resolved with recommended defaults per memory anchors:
  - `project_one_click_install_hard_req` (G/Y/R rubric)
  - `feedback_no_clap_use_gemini_embedding` (Gemini-only — REJECT any non-Gemini cull suggestion)
  - `feedback_no_scope_creep_clean_utility` (no enterprise SBOM tooling)
  - `feedback_autonomous_no_grey_area_pause` (continue + defer; no pause)
  - `feedback_privacy_scope_narrow` (audit scripts have full project FS access)
  - `feedback_worktree_must_sync_main_first` (Step-0 invariant in every subagent prompt)
  - Pitfall 1 (`.planning/research/PITFALLS.md`) — hermetic container build mandate.
[auto] Single-pass cap respected — CONTEXT.md written once, no re-pass.
[auto] Next step: `gsd-plan-phase 46` (auto-advance via `modes/chain.md`).
