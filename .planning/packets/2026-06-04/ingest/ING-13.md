## ING13 — CI / workflows + supply-chain adversarial verification (ship-ingestion pass)

**HEAD read at: `d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, 2026-06-04 20:06 +0300). Same HEAD ING-01 read at; tree has not moved since the ship-ingestion workflow commit `322e8c44`.

Proof tiers, never conflated: **SRC** = green test on source · **PKG** = present/correct in a signed DMG built at HEAD · **LIVE** = a real stranger reaches it. `test-passing-but-dark = 0`. Flags: **LANDED** / **CLAIMED-BUT-DARK** / **NOT-STARTED**.

Scope: this pass owns `.github/workflows/*` + supply-chain + secret discipline + the README/partner-copy CI gates + the GA-tag landmine. The 4 locked decisions are FULLY verified in ING-01 (`d7d5337a`); I cross-reference where a workflow gate touches them and do NOT re-derive. Where ING-01 and the SHIP-MAP disagree, HEAD wins and I re-pinned.

Builds on: `SHIP-MAP-MASTER.md` (synth `7ac35a84`, several claims STALE), `BACKEND-WIRING-EXIT-MAP.md`, `ING-01.md` (voice/start/proxy verified LANDED).

---

## VERDICT TABLE — the workflows that fire on a `v*` GA tag or `release: published`

| Workflow | Fires on | Status at HEAD | GA-tag verdict |
|----------|----------|----------------|----------------|
| `release.yml` | `push: tags v*` + `workflow_dispatch` | **LANDED, but matrix HOT** | fires arm64+x86_64-mac + Windows; moss-gate SWAPPED; **needs matrix scoping before GA** |
| `companion-sign.yml` | `push: tags v* / branches main` + PR(paths) + dispatch | **LANDED, has a secret-name BUG** | uses `SIGNPATH_ORG_ID` (drift from release.yml `SIGNPATH_ORGANIZATION_ID`) |
| `sbom.yml` | `release: published` + dispatch | **LANDED, decoupled** | safe — runs after manual publish, no `needs:` gate on publish |
| `verify-signed.yml` | `workflow_run: [Release] completed` + dispatch | **LANDED** | safe — surface-only verifier, P46 audit clean |
| `secret-scan.yml` | PR + `push: main` + dispatch | **LANDED** | safe — gitleaks, surgical baseline; org-agnostic |
| `dep-audit.yml` | PR/push(paths) + dispatch | **LANDED** | safe — 7 jobs (uv-regen, cargo-deny, npm-audit, AUDIT.md ×2, dep-cull, pinact, opp-scan) |
| `python-cve.yml` | PR + push:main + nightly 6am + dispatch | **LANDED** | safe — pip-audit + osv-scanner + severity gate |
| `rust-cve.yml` | PR/push(tauri paths) + nightly 7am + dispatch | **LANDED** | safe — cargo-audit + cargo-deny + severity gate |
| `full-test-matrix.yml` | `push: main` + PR | **LANDED, GREEN** | safe — key-independent default suite; no GA dependency |
| `no-api-key-surface.yml` | PR/push(ui paths) + dispatch | **LANDED, now GREEN** | NOT a blocker — gate was SCOPED to allow the BYO key field (SHIP-MAP "RED" is STALE) |
| README gates (4) | inside `full-test-matrix` / launch scripts | **GREEN, but do NOT enforce partner-copy** | partner-copy rewrite is NOT-STARTED but won't break these 4 gates |
| `model-literal-check.yml` | PR/push(src paths) + dispatch | **LANDED, but voice/audio IDs ungated** | matches only `gemini-*`; chatterbox/CUE model IDs drift silently (W17) |

Net: every workflow is LANDED and structurally sound. The GA-tag is blocked by **three** real items, in priority order: (1) the release.yml cross-platform matrix is statically hot and will fire Windows + Intel-mac on `v*` (SHIP-SHAPE wants arm64-only); (2) `companion-sign.yml` SignPath secret-name drift; (3) the placeholder-pubkey + signing-secrets gates will hard-fail or skip-to-mock until Kaan provisions secrets. None is a code regression; all are release-infra + secrets-provisioning items.

---

## (A) release.yml — the GA-tag driver — LANDED, matrix HOT [PKG/release]

`release.yml:57-60` fires on `push: tags 'v*'` (+ `workflow_dispatch` with `dry_run` default `true`). Structure is mature and correct:

- **Wave 0 pre-flight gates (all tag-gated):**
  - `p46-audit` (`:86-115`) — greps workflows + scripts for forbidden POST/PUT to apple/signpath/notarytool. Comment-stripping is correct. CLEAN at HEAD (verified: no forbidden verbs).
  - `detect-signing-mode` (`:117-163`) — presence-tests **14 signing secrets** (8 Apple + 5 SignPath + 1 Tauri-key) with `set +x` discipline; emits `signing_available`. If ANY of the 14 is empty → `signing_available=false` → **the entire SIGN/PACKAGE/PUBLISH path is skipped, build runs BUILD→VERIFY only (mock-signing)**. So a `v*` tag pushed today (no secrets on the fresh Bravoh-ai org) produces UNSIGNED artifacts + a green-but-mock run, NOT a published signed release. This is fail-safe, not fail-loud.
  - `secret-name-audit` (`:165-246`) — asserts `TAURI_UPDATER_KEY_PASSWORD` (canonical) is used and `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` (the Tauri-docs alternate) is NOT, across release.yml + tauri.conf.json5 + sign_manifest.sh. Pitfall-7 silent-updater-signature guard. Real gate.
  - `placeholder-pubkey-gate` (`:248-265`, tag-only) — **HARD-FAILS the tag if `tauri.conf.json5` still carries `TAURI_UPDATER_PLACEHOLDER`.** This is a real GA blocker: until Kaan generates the updater keypair and bakes the real pubkey, every `v*` push dies here. Owner-gated.

- **Wave 1 build matrix (`:271-291`) — STATICALLY hot, 3 platforms:**
  - `build-macos` matrix: **arm64 (macos-14) AND x86_64 (macos-13)** — `:283-290`, NO conditioning.
  - `build-windows` (`:470`) — `runs-on: windows-latest`, NO conditioning.
  - **ADVERSARIAL CONFIRM of the GA-tag landmine (matches ING-01):** there is ZERO `if:` / env / input gate on the arch or the Windows job. `VIBEMIX_PRETAG_MAC_ONLY=1` is referenced ONLY in `scripts/dist/pretag_check.sh:148` (skips local SignPath gates) — it has NO effect on the Actions matrix. So a real `v*` tag WILL spin up the x86_64-mac + Windows jobs. Both are voiceless by the PEP 508 marker `platform_machine == 'arm64'` (ING-01 (a)); Windows additionally needs SignPath + Inno + VC++ redist. **To honor the SHIP-SHAPE arm64-only v1 lock, release.yml must scope the matrix** — either drop the x86_64 + windows includes, or gate them behind a `workflow_dispatch.inputs.platforms` toggle defaulted to arm64. This is an infra edit, owner-gated, NOT-STARTED.

- **moss→chatterbox gate-swap (decision #1 cross-check) — LANDED:** `grep -RIn 'require-moss\|moss' .github/workflows/` = **zero hits**. The build-macos app/dmg/updater verify steps (`:355-356`, `:399-400`, `:426-427`) and the windows payload check (`:541-542`) all pass `--require-chatterbox-ref --require-chatterbox-source`. The `--require-moss-source` gate the SHIP-MAP feared is GONE from the entire repo. Matches ING-01 (e). The gate impl (`check_sidecar_bundle_ready.py`, per ING-01) does a real HF HEAD on the pinned chatterbox revision — a tag fails if the pinned public source moved.

- **Wave 1.5 `verify-signed-publish-gate` (`:675-730`)** — tag+signing-gated hard gate; runs `verify_signed.py --require-signed` on arm64 DMG, x86_64 DMG, Windows installer, Windows updater. **NOTE: this gate hard-requires an x86_64 DMG and BOTH Windows artifacts** (`:702-730`). If the matrix is later scoped to arm64-only, this gate's x86_64/Windows steps will fail on missing artifacts — the scoping edit must touch this job too.

- **Wave 2 `release-publish` (`:736-922`)** — tag + signing + verifier gated; signs `latest.json`, POSTs to `api.altidus.world/vibemix/updates/upload` (404-tolerant, `:879-880`, never fails the run), creates a DRAFT GitHub Release (`:895`, Kaan clicks Publish). The manifest-shape gate `check_updater_manifest_ready.py` (`:797`) — per SHIP-MAP — hard-requires all 3 platforms in `latest.json`, another reason matrix-scoping cascades.

**Hardcoded `api.altidus.world` in release.yml** (`:31, :862, :877, :901`) — this is the updater-manifest POST endpoint, internal infra, NOT user-facing partner copy. It is 404-tolerant so it never fails a release. Partner-copy policy concern only if release notes leak it; the draft body (`:901`) does say "consumed by api.altidus.world" — a minor internal-leak in release notes, scrubbable, non-blocking.

---

## (B) companion-sign.yml — LANDED, SignPath secret-name BUG [PKG/release]

`companion-sign.yml:16-19` fires on `push: tags v*` AND `push: branches main` (+ PR-paths + dispatch). So **it fires on every push to `main`** (the Bravoh-ai main was just pushed). On non-tag builds it runs DRY-RUN (`:55-59`, macOS `|| true`) and the SignPath submit step is tag-gated (`:91`), so a main-push run is non-fatal.

**BUG — SignPath org secret-name drift (CLAIMED-BUT-DARK):**
- `release.yml:137/153/575` + `pretag_check.sh:151` + `sign_windows.ps1:51` all use **`SIGNPATH_ORGANIZATION_ID`**.
- `companion-sign.yml:95` uses **`SIGNPATH_ORG_ID`** (different name).
- These are two distinct GitHub secret names. Whichever Kaan provisions, the other resolves to empty. On a tag build the companion submit step (`:103-107`) WARNS + `exit 0` when `SIGNPATH_API_TOKEN` is empty — so the drift is masked into a silent warning, not a hard fail. But if Kaan provisions `SIGNPATH_ORGANIZATION_ID` (the release.yml name) and the token, the companion job's `SIGNPATH_ORG_ID` env is still empty → companion signing submits with a blank org. **Fix: rename `companion-sign.yml:95` to `SIGNPATH_ORGANIZATION_ID`.** One-line. Windows-only → off the v1 critical path, but a real latent bug. Flag for v1.1.

Companion files validated to exist on both OS (`:43-45`, `:76-84`); `verify-companion-signatures` gate (`:116-133`) runs `check_companion_signing.sh` (WARN on branches, fatal on tag).

---

## (C) Supply-chain workflows — all LANDED, structurally sound

- **`secret-scan.yml`** (gitleaks v8.21.2 pinned) — PR + push:main + dispatch. `detect` (committed history, `--baseline-path=.secrets.baseline --redact`) is the gate; `protect` (staged tree, PR-only) is informational. The baseline (`.secrets.baseline`) is surgical: one AIza fixture entry, fully justified. `.gitleaks.toml` extends the default ruleset with a SINGLE narrow allowlist anchored to the `-TEST-FIXTURE-DO-NOT-USE` suffix + path-bound to fixture dirs — Pitfall-P64 discipline held. **Adversarial scan:** `grep AIza[...]{30}` across the tree (excluding fixtures/baseline/node_modules) = **zero live keys committed**. Org-agnostic; runs identically on Bravoh-ai. **Memory note** (`project_respan_observability`): a Respan key was chat-pasted and flagged to rotate — confirmed NOT in the tree (no live key in git). SRC clean.
- **`python-cve.yml`** — pip-audit (`>=2.7.3`) + osv-scanner (v1.9.1 pinned) → `severity_gate.py` (Pitfall-P65). Nightly 6am + PR + push:main. `|| true` on the scanners is intentional (the gate makes the fail decision). Org-agnostic, no secrets needed.
- **`rust-cve.yml`** — cargo-audit (0.20.1) + cargo-deny (0.16.2) → same severity gate. Path-gated to `tauri/src-tauri/**`. Nightly 7am. Advisory-DB cached. Org-agnostic.
- **`dep-audit.yml`** — 7 jobs: hermetic `uv.lock` regen+drift (DEPS-01, rejects `pip freeze`), `cargo-deny` license policy (DEPS-02, 0.16.1), `npm-audit` PR comment (DEPS-03), AUDIT.md freshness (DEPS-05) + generator-drift (DEPS-04), dep-cull verify (DEPS-08), **pinact SHA-pin audit (DEPS-07)**, opp-scan validate + anti-slop (OPP-03). The pinact job (`:201-209`) enforces every `uses:` is SHA-pinned — verified across all workflows read (every action is `@<40-hex> # vX`). Org-agnostic.
- **`sbom.yml`** — fires on `release: published` (after Kaan manually publishes the draft) + dispatch. Two jobs: syft SPDX (anchore/sbom-action v0.17.0 pinned) + CycloneDX (Python+Rust+JS). Attaches SBOMs as release assets. **Decoupled — no `needs:` on release-publish, runs independently after publish** → cannot block a release, cannot misfire on a tag. Safe.
- **`verify-signed.yml`** — fires on `workflow_run: [Release] completed`. P46 audit job + surface-only `verify_signed.py --skip-if-missing`. Safe.
- **`full-test-matrix.yml`** — `push: main` + PR. Matrix `[macos-13, macos-14, windows-latest] × [default + 7 markers]` with OS-incompatible exclusions. **Key-independence VERIFIED:** the default suite has only 2 `@pytest.mark.network` tests, both SKIPPED by default; `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}` (`:80/:86`) is passed but the default+marker suites do not REQUIRE a live key (they mock/skip). **So a missing `GEMINI_API_KEY` secret on Bravoh-ai does NOT fail this matrix.** WR-01 script-injection defense (intermediate `MATRIX_MARKER` env) is present (`:96`). Uses `pull_request` not `pull_request_target` — fork secrets safe.

---

## (D) Which workflows would FAIL or MISFIRE on the Bravoh-ai org today

Adversarial answer to the task's explicit question:

1. **`release.yml` on a `v*` tag → MISFIRES (3 ways):**
   - `placeholder-pubkey-gate` HARD-FAILS the tag until Kaan replaces `TAURI_UPDATER_PLACEHOLDER` in `tauri.conf.json5` with a real updater pubkey. **This is the first hard wall on any `v*` push.** [owner-gated, NOT-STARTED]
   - `detect-signing-mode` → `signing_available=false` (14 secrets absent on fresh org) → SIGN/PACKAGE/PUBLISH skipped, build runs BUILD→VERIFY mock-only. Not a failure, but produces NO published signed release. [secrets-provisioning, Kaan]
   - The matrix spins Windows + x86_64-mac jobs unconditionally. They will BUILD (and likely succeed at BUILD→VERIFY), wasting runner minutes and producing voiceless artifacts; if secrets WERE present they'd attempt SignPath/Inno on Windows. **Scoping needed before GA.** [infra edit, NOT-STARTED]
2. **`companion-sign.yml` on `push: main` → runs NOW, non-fatal** (dry-run on non-tag). On a `v*` tag with secrets, the `SIGNPATH_ORG_ID`-vs-`SIGNPATH_ORGANIZATION_ID` drift submits a blank org. [v1.1 bug]
3. **`secret-scan`, `python-cve`, `rust-cve`, `dep-audit`, `full-test-matrix`, `packaging-audit`, `bundle-id-lock`, `capabilities-lint`, `model-literal-check`, `no-api-key-surface`, `mascot-audit`, README gates → all org-agnostic, no required secrets, GREEN.** None misfires on Bravoh-ai.
4. **`eval.yml`** — PR runs use VCR cassettes (`record_mode=none`, $0, no live key). Nightly canary (cron 5am) needs `GEMINI_API_KEY` for real-API recording; absent → the canary's live-record step would fail, but PR runs are unaffected. [non-blocking, nightly-only]
5. **org-default drift (minor):** `scripts/launch/check_bravoh_org_ready.sh:34` defaults `ORG="bravoh"` and its doc-string targets `gh repo transfer ozai/dj-set-ai bravoh/vibemix`; the actual main push went to **`Bravoh-ai`** (capital, `-ai`). The script takes `--org` so it's not CI-wired, but the default + doc are STALE vs the real org. [doc drift, non-blocking]

---

## (E) Locked-decision × CI cross-check (verified in ING-01, confirmed here where a gate touches it)

1. **VOICE (Chatterbox-only, MOSS nuked)** — CI side LANDED: moss-gate fully swapped to `--require-chatterbox-source`/`--require-chatterbox-ref` across `release.yml` + `pretag_check.sh` (zero moss hits). `local_tts.py` deleted; `src/vibemix/agent/moss_tts/` retains only a `__pycache__/` (no source — effectively dead, stale bytecode; flag for cleanup). Matches ING-01 (e) + decision-1 cross-check.
2. **BRAIN (proxy default + BYO key)** — CI side: the `no-api-key-surface.yml` gate that the SHIP-MAP called a head-on RED conflict is **now GREEN (4 passed at HEAD)**. The test (`tests/security/test_no_api_key_surface.py:7-21`) was deliberately re-scoped: it now ALLOWS exactly one BYO key surface (`brain-group.ts`, the `ALLOWED_BYO_KEY_SURFACE` constant) + a read-only crash-banner exclusion, and forbids key surfaces everywhere else. **The SHIP-MAP "RED gate / owner-policy call needed" is STALE — the gate already reconciles with decision #2.** This is a correction to the SHIP-MAP SRC RED list.
3. **START GATE** — verified LANDED both-ends in ING-01 (handler `session_loop.py:278`, idle-cold test green). No CI gate specifically guards it beyond the smoke test in the default suite (`test_smoke_03b_idle_is_cold_until_start`, green). No misfire.
4. **STREAK robot voice** — NOT-STARTED (correct per lock). No CI surface.

---

## (F) README / partner-copy — CI gates GREEN, partner-copy rewrite NOT-STARTED [docs]

Critical adversarial finding that CORRECTS the framing in the task prompt and ING-01: **the 4 README CI gates do NOT enforce the partner-copy policy.** Verified by running them at HEAD:
- `tests/repo/test_readme_shape.py` + `test_readme_feature_matrix_sync.py` → **53 passed.**
- `scripts/check_readme_hero_hash.py` → **EXIT 0** ("hero asset pending Kaan-action, sha256=PLACEHOLDER sentinel").
- `scripts/launch/check_readme_grids_a11y.py` → **EXIT 0** (DJ grid 6 cells + controller grid 10 cells, alt-text + no-slop).

These gates pin STRUCTURE (shape, feature-matrix sync, grid cell counts vs `midi/profiles`, hero-hash sentinel) — they do NOT grep for `Gemini`/`MOSS`/`altidus.world`/`bravoh.com`. So the README STILL violates every partner-copy rule AND carries STALE voice copy, while CI stays green:
- **Leaks `api.altidus.world`** — README.md lines 39, 61, 241, 259 (+ the `security@bravoh.com` PGP line). Policy: "Bravoh's hosted service".
- **Names `Gemini`** — lines 39, 61, 149, 241, 259, 269, 271, 283, 287. Policy: "AI model".
- **Names `MOSS` AND factually STALE** — lines 229, 241, 271 ("Sven speaks through the local MOSS voice path" / "Speech is rendered locally through the MOSS voice path"). Double bug: model-name leak + WRONG at HEAD (voice is Chatterbox; MOSS is nuked). [the highest-priority README fix — it is both a policy violation and a factual lie]
- **`bravoh.com` not `bravoh.ai`** — line 63 (`security@bravoh.com`).
- **Dev feature-matrix slop** — lines 130-149 (Phase numbers, "SHIPPED 2026-05-28", commit SHAs `c740fd90 → ...`), line 69 ("Kaan ear-passes daily"), lines 11/30/86/198 ("KAAN-ACTION-LEGAL.md"). Internal slop in public copy.

**Coordination requirement:** because `feature_matrix_sync` pins the README feature-matrix block against `sync_feature_matrix.py --check` (AUTO-GEN markers), a partner-copy rewrite of lines 130-149 MUST run `sync_feature_matrix.py` to regenerate, or that gate breaks. The grids gate pins the 6-img/10-cell grids vs `midi/profiles` — leave those structurally intact. The hero-hash gate stays on the PLACEHOLDER sentinel (no action). So the rewrite is scoped: edit prose (domains/model-names/slop) WITHOUT disturbing the AUTO-GEN matrix region (regenerate it) or the grid cells. **NOT-STARTED, owner-visible, won't break the 4 gates if coordinated.**

---

## (G) Supply-chain posture summary (the healthy part)

- **Every `uses:` is SHA-pinned** (40-hex + version comment) across all 24 workflows — enforced by `dep-audit.yml` pinact-audit (DEPS-07). Verified spot-checks: `actions/checkout@34e1148... v4.3.1`, `signpath/...@4f13d37... v1.2`, `softprops/action-gh-release@3bb1273... v2.6.2`, `anchore/sbom-action@d94f46e... v0.17.0`.
- **Lockfile hermeticity:** `uv.lock` regen-drift gate rejects `pip freeze` (Pitfall-1). `cargo-deny` (licenses+bans+sources+advisories) on both the dep-audit and rust-cve paths. `npm-audit` PR comments.
- **Dual SBOM** (SPDX via syft + CycloneDX 4-target) attached on release-published.
- **Dual CVE coverage** (pip-audit+osv / cargo-audit+cargo-deny) + nightly crons + a shared `severity_gate.py`.
- **Secret discipline:** gitleaks + surgical baseline + `--redact`; release.yml `set +x` before every secret-export block; presence-only secret tests; `permissions:` scoped to `contents: read` everywhere except where `write` is genuinely needed (release-publish, sbom, eval-canary). `pull_request` not `pull_request_target` (no fork-secret escalation).
- **Two independent P46 audits** (release.yml Wave-0 + verify-signed.yml) block any POST/PUT to apple/signpath/notarytool — the hard "agent never POSTs to signing endpoints" rule, enforced in CI.

This is a genuinely mature supply-chain layer; the dark is concentrated entirely in (1) the matrix scoping and (2) secret/keypair provisioning — both Kaan-action, not engineering gaps.

---

## What ING13 confirms vs corrects

- **CONFIRMS LANDED:** the entire workflow + supply-chain layer (24 workflows, SHA-pinned, dual SBOM/CVE, gitleaks surgical, P46 audits ×2); the moss→chatterbox release-gate swap (zero moss refs); the GA-tag matrix landmine (ING-01 (D)#4 re-verified independently — matrix is statically hot, `VIBEMIX_PRETAG_MAC_ONLY` does not touch it).
- **CORRECTS the SHIP-MAP (stale at `7ac35a84`):**
  - The "no-api-key-surface RED gate / head-on conflict with decision #2 / owner-policy call needed" is **STALE** — the gate is already scoped to ALLOW the `brain-group.ts` BYO key field and PASSES (4/4).
  - The "test_readme_shape + feature_matrix_sync RED, assert altidus.world" is **STALE** — both pass at HEAD (53/53); they were re-pinned to bravoh.ai (`aaa330ad`). The README partner-copy violations are real but are NOT enforced by these gates (the gates pin structure, not copy).
- **NEW findings (this pass):**
  1. **SignPath org secret-name drift** — `companion-sign.yml:95 SIGNPATH_ORG_ID` vs `release.yml:575 SIGNPATH_ORGANIZATION_ID`. Masked into a silent warning today, blank-org submit if the release.yml name is provisioned. One-line fix. [v1.1, Windows-only]
  2. **`verify-signed-publish-gate` + `check_updater_manifest_ready` + `sign_manifest` hard-require x86_64 + Windows artifacts** — so scoping the matrix to arm64-only is a MULTI-SITE edit (matrix + verify-publish gate + manifest gate), not a one-liner. [infra, NOT-STARTED]
  3. **README MOSS copy is both a model-name leak AND factually wrong** (lines 229/241/271) — highest-priority single README fix.
  4. **`model-literal-check` only guards `gemini-*`** — chatterbox + CUE-DETR + CLAP model IDs drift silently green forever (SHIP-MAP W17 governance gap, confirmed at the CI layer).
  5. **org-default drift** — `check_bravoh_org_ready.sh` defaults `bravoh` (lower, no `-ai`); real org is `Bravoh-ai`. [doc, non-blocking]
  6. **`src/vibemix/agent/moss_tts/` still on disk** (only `__pycache__`, no source) — dead-bytecode cleanup, non-blocking.

---

## What MUST change before a `v*` GA tag is safe (CI/supply-chain lane)

Ordered, owner-gated:
1. **Replace the updater pubkey placeholder** in `tauri/src-tauri/tauri.conf.json5` (generate keypair per `keys/README.md`) — else `placeholder-pubkey-gate` hard-fails every `v*`. [Kaan, NOT-STARTED]
2. **Scope the release.yml matrix to arm64-mac-only** for v1 (drop or gate-off the x86_64-mac + windows includes) AND adjust the dependent gates (`verify-signed-publish-gate` x86_64/Windows steps, `check_updater_manifest_ready` 3-platform requirement, `sign_manifest` x86_64/Windows artifact requirements) so a 1-platform release passes. [infra, NOT-STARTED — the cleanest is a `workflow_dispatch.inputs.platforms` toggle defaulting to arm64, since the matrix is the safe default]
3. **Provision the 14 signing secrets** (8 Apple + 5 SignPath + Tauri-key) on the Bravoh-ai org — else every tag runs mock-only and publishes nothing signed. For a mac-arm64-only v1, only the 8 Apple + Tauri-key are needed; SignPath can wait for v1.1. [Kaan, external clock]
4. **Fix the `companion-sign.yml` SignPath secret name** (or skip the companion job on the arm64-only v1 path). [v1.1, Windows]
5. **Coordinate the README partner-copy rewrite** with `sync_feature_matrix.py --check` (regenerate the AUTO-GEN matrix region) so `feature_matrix_sync` stays green; fix MOSS/Gemini/altidus.world/bravoh.com/slop. Not GA-blocking for CI, but it is public copy that ships with the tag. [docs, NOT-STARTED]

The supply-chain machinery itself needs ZERO new build — it is built, SHA-pinned, and green. The only ship work in this lane is matrix-scoping (infra) + secrets/keypair provisioning (Kaan).
