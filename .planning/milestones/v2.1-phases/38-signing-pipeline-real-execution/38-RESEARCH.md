# Phase 38 — Research

**Gathered:** 2026-05-15
**Status:** Ready for plan
**Mode:** `gsd-autonomous fully` (with hard legal-capacity carveouts)

---

## Existing surface (don't re-invent)

### `.github/workflows/release.yml` (v2.0 Phase 18-05, 18-21, 27-06)

- Already wires Apple notarytool via `scripts/dist/sign_macos.sh` (Stage 5 of the script
  runs `xcrun notarytool submit --wait` + `xcrun stapler staple` + `spctl --assess`).
- Already wires SignPath via `signpath/github-action-submit-signing-request@v1.2.0` (Wave 1
  Windows leg).
- Already implements an **empty-secret-skip pattern** via the `detect-signing-mode` job —
  publishes `signing_available=true|false`, all sign/package steps gate on
  `env.SIGNING_AVAILABLE == 'true' && env.DRY_RUN != 'true'`.
- VERIFY stage already runs `scripts/dist/verify_binary.py` post-sign (AIza scan).
- `release-publish` job is `if: startsWith(github.ref, 'refs/tags/v') && needs.detect-signing-mode.outputs.signing_available == 'true'` — i.e. no publish without secrets.

### `scripts/dist/sign_macos.sh` (Phase 18-02)

- Real `xcrun notarytool submit --apple-id … --password … --team-id … --wait` call
  (idempotent retry x3, exponential backoff). No POST/PUT — `xcrun notarytool` is
  Apple's own CLI; the audit grep excludes plain `apple.com` references that aren't
  paired with `curl|wget … POST|PUT`.
- Uses GitHub Secrets that DON'T EXIST YET — gracefully skipped because the
  `detect-signing-mode` gate fires.

### `scripts/dist/verify_signed.py` (Phase 34 — surface shipped)

- Surface verifier — checksum + Mach-O / PE magic-byte presence checks.
- `--skip-if-missing` flag exits 0 with `::notice::` for forks / dry-run / pre-Phase-38.
- Phase 38 ACTIVATES it as a release-publish gate (was a separate workflow_run-driven
  workflow; Phase 38 adds invocation directly inside `release.yml` BEFORE the
  GitHub Release publish step).

### `.github/workflows/verify-signed.yml` (Phase 34)

- Already contains the P46 audit step (`audit-no-apple-signpath-post`).
- Greps `.github/workflows/*.yml` + `scripts/*` for `(curl|wget).*(POST|PUT).*(apple\.com|signpath\.io|notarytool)`.
- Phase 38 EXTENDS this audit:
  - Cover `.ps1` PowerShell scripts (new in 38-04 sign_windows.ps1).
  - Cover `Invoke-WebRequest`, `Invoke-RestMethod` PowerShell verbs (the audit
    today only matches curl/wget — PowerShell could discharge POST silently).
  - Run as a top-level audit in `release.yml` Wave 0 (currently only verify-signed.yml
    audits — but `release.yml` is what runs on tag push; double-coverage is cheap).

### `tauri/src-tauri/spike/sign-and-test.sh` (v2.0 OVERLAY-02 spike)

- Ad-hoc codesign + bundle assembly + AX probe (Phase 24 Wave 0).
- Locked to `world.bravoh.vibemix.spike` bundle ID (NOT production — TCC keying isolation).
- Phase 38 DIST-19 is "Kaan runs this on the first signed binary post-CI" — documented
  in KAAN-ACTION-LEGAL.md, not autonomous.

### `KAAN-ACTION-LEGAL.md` (Phase 34)

- Has §2 Apple Developer ID signing entry (deferred to Phase 38 — Phase 38 EXTENDS it
  with the DIST-09 Francesco-action protocol).
- Has §3 SignPath OSS entry (Phase 38 EXTENDS with DIST-11 1-week SLA + form pre-fill).

---

## External references

### `xcrun notarytool` (Apple official CLI)

Apple CLI; not an HTTP endpoint. The CLI internally talks to App Store Connect
over Apple's signed protocol — our P46 audit explicitly excludes it (the audit
fires on `(curl|wget) … POST|PUT … (apple\.com|signpath\.io|notarytool)`, not on
mere mentions of the word "notarytool" or "apple.com"). The shipped
`sign_macos.sh` uses the CLI, never `curl POST`.

Modern syntax (Phase 38 confirms):

```bash
xcrun notarytool submit "$DMG" \
  --apple-id "$APPLE_ID_USERNAME" \
  --password "$APPLE_ID_APP_PASSWORD" \
  --team-id "$APPLE_TEAM_ID" \
  --wait
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"
```

OR (App Store Connect API mode — what `sign_macos.sh` uses):

```bash
xcrun notarytool submit "$DMG" \
  --key "$APPLE_API_KEY_PATH" \
  --key-id "$APPLE_API_KEY_ID" \
  --issuer "$APPLE_API_KEY_ISSUER" \
  --wait
```

Both modes are valid. Existing release.yml uses ASC API mode (which is more
robust — no app-specific-password needed).

### `signpath/github-action-submit-signing-request@v1.2.0`

Official SignPath GH Action. Communicates with `app.signpath.io` over its own
signed/encrypted protocol — the action itself encapsulates that. Our workflow
just passes the API token + project/policy slugs as inputs.

P46 audit interpretation: the GH Action's HTTP traffic is NOT `curl … POST …
signpath.io` in our workflow text — the action's internals are not our concern
(Pitfall P46 is about **autonomous discharge** of the legal-capacity carveouts,
which is the application + acceptance step, not the act of running the official
action with secrets the human supplied).

### PowerShell signing patterns (DIST-18)

- `signtool.exe sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a <msi>`
  — local rehearsal would normally use Windows SDK signtool, but SignPath OSS
  artifacts must go through SignPath's submission flow. The local rehearsal
  script's purpose is to **smoke-test the SignPath submission** locally
  (vibemix CLI → SignPath API token → wait → download signed artifact).
- SignPath ships a PowerShell module `SignPath.PowerShellAutomation` (NuGet
  package). But for v1 we'll keep it dependency-light: a thin wrapper that
  invokes the SignPath CLI tool (`SignPathClient.exe`) IF present, otherwise
  print a clear "install SignPath CLI" message and exit non-zero.
- Critical: the script MUST NOT POST to signpath.io itself — that's exactly
  what P46 forbids when written autonomously. Instead: invoke the official
  CLI binary (which is downloaded + installed manually by Kaan; the CLI is a
  vendor-signed Windows executable that does its own POSTs).

---

## Plan list (proposed)

1. **38-01 — release.yml empty-secret skip pattern confirmation + Apple notarytool
   step extraction.** Validate `detect-signing-mode` job already gates the Apple
   leg. Add an inline annotated `notarytool` step that lives in release.yml itself
   (NOT inside sign_macos.sh) — this satisfies "Apple notarytool wiring" in CONTEXT
   §DIST-15 with the empty-secret-skip pattern explicit in the workflow body. Tests:
   `test_release_yml_skip_on_empty_apple_secret` (parses workflow YAML, asserts
   `if:` clause matches empty-secret-skip pattern); `test_release_yml_notarytool_step_exists`.

2. **38-02 — release.yml SignPath GH Action empty-secret skip confirmation.**
   Validate SignPath leg already gates on `SIGNING_AVAILABLE`. Add an annotation
   step in release.yml that PRINTS the `::warning::` line when SignPath secret is
   absent (today the step is silently skipped — explicit warning helps debugging).
   Tests: `test_release_yml_skip_on_empty_signpath_secret`,
   `test_release_yml_signpath_warning_emitted`.

3. **38-03 — post-sign verifier activated as release-publish gate.** Add a
   `verify-signed-publish-gate` job to release.yml between `build-{macos,windows}`
   and `release-publish` that runs `python scripts/dist/verify_signed.py
   --artifact <signed-dmg>` and `--artifact <signed-msi>` WITHOUT
   `--skip-if-missing`. The job fires only when `SIGNING_AVAILABLE == 'true'` (so
   forks/mock-mode unaffected). `release-publish` depends on it. Tests:
   `test_post_sign_verifier_blocks_publish_on_unsigned` (synthesize unsigned
   bytes → call `verify_signed.verify()` → assert verdict reflects unsigned).

4. **38-04 — `scripts/dist/sign_windows.ps1` local-rehearsal script.** PowerShell
   wrapper around SignPath CLI for Kaan's local rehearsal. Strict P46 compliance:
   no `Invoke-WebRequest` / `Invoke-RestMethod` to signpath.io directly — invokes
   the official `SignPathClient.exe` CLI binary IF present. Tests:
   `test_sign_windows_ps1_syntax_valid` (uses `pwsh -NoProfile -Command
   '$PSParser::Tokenize'` if pwsh installed, else falls back to a Python-side
   regex parser — both check for unmatched braces / quotes / brackets);
   `test_sign_windows_ps1_no_forbidden_posts`.

5. **38-05 — KAAN-ACTION-LEGAL.md DIST-09 + DIST-11 protocols.** Add two new
   sections (or expand §2/§3) with detailed protocols. DIST-09: Francesco logs
   into developer.apple.com, accepts Program License Agreement updates, ~10
   minutes. DIST-11: Kaan submits the SignPath OSS Foundation form at
   signpath.org/foundation (~1 week SLA). Each section has a status checklist
   + countersign block. Tests:
   `test_kaan_action_legal_md_has_dist_09_dist_11_protocols`.

6. **38-06 — P46 audit extension.** Extend `.github/workflows/verify-signed.yml`
   audit step to:
   - Cover `.ps1` files in `scripts/`.
   - Include PowerShell verbs `Invoke-WebRequest`, `Invoke-RestMethod`.
   - Also mirror the audit job inside `release.yml` Wave 0 (so a forbidden POST
     in release.yml triggers an immediate fail without waiting for verify-signed
     to run). Tests: `test_p46_audit_blocks_post_to_apple` (synthesize forbidden
     POST in a tmp workflow → run audit grep → assert exit 1);
   `test_p46_audit_blocks_post_to_signpath`;
   `test_p46_audit_blocks_powershell_invoke_webrequest_to_signpath`.

---

## Out of scope (HARD carveouts — Pitfall P46)

- ACTUAL Apple Developer Program Agreement update (Francesco-action).
- ACTUAL SignPath OSS Foundation application (Kaan-action).
- ACTUAL cert generation / GitHub Secrets upload (Kaan-action after approvals).
- ACTUAL `sign-and-test.sh` smoke on real signed binary (Kaan-action).
- ACTUAL `sign_windows.ps1` execution on real installer (Kaan-action).

The deliverables above are **workflow scaffolds + scripts + protocols + tests
that pass against synthetic fixtures**. Real signing activates when Kaan/Francesco
discharge the legal-capacity items and drop secrets into the repo's settings.

---

## Phase entry contract

- Atomic commits per plan.
- No POC files touched.
- All tests against synthetic fixtures only.
- After each plan: re-run the full test file added by that plan.
- After all plans: full pytest sweep on `tests/security/` + `tests/dist/` +
  any new test paths.
