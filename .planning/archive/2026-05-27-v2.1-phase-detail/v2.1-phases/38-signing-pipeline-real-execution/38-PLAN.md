# Phase 38 — Signing Pipeline Real Execution — PLAN

**Status:** Ready to execute
**Plans:** 6 (38-01 → 38-06)
**Mode:** `gsd-autonomous fully` with HARD legal-capacity carveouts (Pitfall P46)

---

## Cross-cutting rules

1. **No POST/PUT to apple.com / signpath.io / notarytool from any script.**
2. **Workflows MUST stay valid before Apple/SignPath approve** — empty-secret skip pattern.
3. **POC files (`cohost*.py`, `mascot.html`) UNTOUCHED.**
4. **Atomic commits per plan.**
5. **Tests against synthetic fixtures only.**

---

## Plan 38-01 — release.yml Apple notarytool empty-secret skip confirmation + explicit annotation

**REQ-IDs:** DIST-15

**Edits:**
- `.github/workflows/release.yml`:
  - Confirm `detect-signing-mode` job + `SIGNING_AVAILABLE` gating on the macOS SIGN
    step (already present).
  - Add a NEW step inside `build-macos` job named `SIGN — Apple notarytool wiring
    annotation` that runs FIRST when `SIGNING_AVAILABLE != 'true'` and prints
    `::warning::Apple Dev ID secrets absent — see KAAN-ACTION-LEGAL.md DIST-09
    (Francesco-action) + DIST-11`. This makes the skip behaviour explicit in CI
    logs instead of silent.
- `tests/security/test_release_yml_signing_skips.py`:
  - `test_release_yml_apple_skip_step_exists`
  - `test_release_yml_notarytool_invocation_present`
  - `test_release_yml_apple_sign_step_guarded_by_signing_available`

**Acceptance:** all 3 new tests + existing test suite passes.

---

## Plan 38-02 — release.yml SignPath GH Action empty-secret skip annotation

**REQ-IDs:** DIST-16

**Edits:**
- `.github/workflows/release.yml`:
  - Add `SIGN — SignPath wiring annotation` step in `build-windows` job, parallel to
    38-01. Emits `::warning::SignPath approval pending — see KAAN-ACTION-LEGAL.md
    DIST-11` when secret is empty.
  - Confirm SignPath action remains gated on `SIGNING_AVAILABLE == 'true'`.
- `tests/security/test_release_yml_signing_skips.py` (same file as 38-01, extended):
  - `test_release_yml_signpath_skip_step_exists`
  - `test_release_yml_signpath_action_pinned_version`
  - `test_release_yml_signpath_sign_step_guarded_by_signing_available`

**Acceptance:** all new tests pass + 38-01 still green.

---

## Plan 38-03 — post-sign verifier release-publish gate

**REQ-IDs:** DIST-17

**Edits:**
- `.github/workflows/release.yml`:
  - Add new job `verify-signed-publish-gate` between `build-{macos,windows}` and
    `release-publish`. Runs only when `SIGNING_AVAILABLE == 'true'` AND tag-push.
    Downloads built artifacts, runs `python scripts/dist/verify_signed.py
    --artifact <path>` WITHOUT `--skip-if-missing`. Job fails fast if verifier
    returns non-zero.
  - Update `release-publish.needs` to include `verify-signed-publish-gate`.
- `scripts/dist/verify_signed.py`:
  - Add a `--require-signed` flag — when set, exits 1 if `signed_mac` or
    `signed_win` is False for the corresponding artifact type. Default off (preserves
    Phase 34 surface contract).
- `tests/security/test_verify_signed.py` (extended):
  - `test_post_sign_verifier_blocks_publish_on_unsigned` — synthesize unsigned
    .dmg bytes (`b"not a real mach-o"`), call verify with `--require-signed`,
    assert exit 1 and verdict mentions "missing signature".
  - `test_post_sign_verifier_passes_on_mach_o_magic` — synthesize bytes starting
    with Mach-O magic, assert exit 0 with `--require-signed`.

**Acceptance:** all new tests + 4 existing verify_signed tests pass.

---

## Plan 38-04 — `scripts/dist/sign_windows.ps1` local-rehearsal script

**REQ-IDs:** DIST-18

**Edits:**
- `scripts/dist/sign_windows.ps1` (new file):
  - PowerShell 5+ compatible.
  - Inputs: `-MsiPath`, `-ApiToken` (else read from `$env:SIGNPATH_API_TOKEN`),
    optional `-OrganizationId`, `-ProjectSlug`, `-PolicySlug`, `-ArtifactConfigSlug`,
    `-OutputDir` (default `./dist/signed-binaries`).
  - Body: locate `SignPathClient.exe` on PATH (via `Get-Command`). If missing,
    write a clear error message linking to SignPath CLI docs and exit 2. If
    present, invoke it with the supplied args (the CLI handles the actual POST
    to signpath.io — our script does NOT POST directly).
  - Strict P46 compliance: NO `Invoke-WebRequest` / `Invoke-RestMethod` /
    `[System.Net.WebClient]` calls.
- `tests/security/test_sign_windows_ps1.py` (new file):
  - `test_sign_windows_ps1_exists`
  - `test_sign_windows_ps1_has_param_block` — regex grep for `param(` block with
    required fields.
  - `test_sign_windows_ps1_no_forbidden_posts` — grep for `Invoke-WebRequest`,
    `Invoke-RestMethod`, `WebClient` AND for `POST|PUT` patterns paired with
    `apple|signpath|notarytool`.
  - `test_sign_windows_ps1_syntax_valid` — uses `pwsh -NoProfile -Command
    '[scriptblock]::Create([io.file]::ReadAllText("path"))'` IF pwsh available,
    ELSE bracket-balance + quote-pair Python parser.

**Acceptance:** all new tests pass.

---

## Plan 38-05 — KAAN-ACTION-LEGAL.md DIST-09 + DIST-11 protocols

**REQ-IDs:** DIST-09, DIST-11

**Edits:**
- `KAAN-ACTION-LEGAL.md`:
  - EXTEND existing §2 (Apple) with a "DIST-09 — Apple Developer Program Agreement
    update (FRANCESCO-ACTION)" subsection. Detailed protocol: Francesco logs in,
    accepts License Agreement updates, completes entity update if needed; status
    checklist; countersign block.
  - EXTEND existing §3 (SignPath) with a "DIST-11 — SignPath OSS Foundation
    application (KAAN-ACTION)" subsection. Detailed protocol: submit at
    signpath.org/foundation, 1-week SLA, fill open-source-project form with the
    repo URL + open-source license confirmation. Status checklist + countersign.
  - Bonus: add a top-of-file LEGAL-CAPACITY CARVEOUTS callout summarising P46.
- `tests/security/test_kaan_action_legal.py` (new file):
  - `test_kaan_action_legal_md_has_dist_09_protocol`
  - `test_kaan_action_legal_md_has_dist_11_protocol`
  - `test_kaan_action_legal_md_has_p46_callout`

**Acceptance:** all new tests pass + the existing legal file's structure remains
parseable.

---

## Plan 38-06 — P46 audit extension

**REQ-IDs:** DIST-19 (as smoke-protocol scaffold) + ENFORCES P46

**Edits:**
- `.github/workflows/verify-signed.yml`:
  - Extend `audit-no-apple-signpath-post` step to also scan `.ps1` files in
    `scripts/`.
  - Add a second grep pass for PowerShell verbs: `Invoke-WebRequest`,
    `Invoke-RestMethod`, `WebClient` paired with `apple\.com|signpath\.io|notarytool`.
- `.github/workflows/release.yml`:
  - Add a new top-level Wave 0 job `p46-audit` that mirrors the verify-signed
    audit (so `release.yml` on tag-push fails before any signing step runs).
- `tests/security/test_p46_audit.py` (new file):
  - `test_p46_audit_blocks_post_to_apple` — write a synthetic workflow with
    `curl -X POST https://apple.com/foo`, run the actual grep, assert match.
  - `test_p46_audit_blocks_post_to_signpath`
  - `test_p46_audit_blocks_powershell_invoke_webrequest_to_signpath`
  - `test_p46_audit_allows_clean_workflow`
  - `test_release_yml_has_p46_audit_job`

**Acceptance:** all new tests pass + the verify-signed.yml + release.yml YAML
still parse.

---

## Hard gates (collected from CONTEXT)

| Gate | Plan | Test name |
|---|---|---|
| `test_release_yml_skip_on_empty_apple_secret` | 38-01 | `test_release_yml_apple_sign_step_guarded_by_signing_available` |
| `test_release_yml_skip_on_empty_signpath_secret` | 38-02 | `test_release_yml_signpath_sign_step_guarded_by_signing_available` |
| `test_p46_audit_blocks_post_to_apple` | 38-06 | (exact name) |
| `test_p46_audit_blocks_post_to_signpath` | 38-06 | (exact name) |
| `test_post_sign_verifier_blocks_publish_on_unsigned` | 38-03 | (exact name) |
| `test_sign_windows_ps1_syntax_valid` | 38-04 | (exact name) |
| `test_kaan_action_legal_md_has_dist_09_dist_11_protocols` | 38-05 | `test_kaan_action_legal_md_has_dist_09_protocol` + `test_kaan_action_legal_md_has_dist_11_protocol` |

Each plan = one atomic commit. Verification at the end runs the full pytest
suite touching the new files + the existing `tests/security/` directory.
