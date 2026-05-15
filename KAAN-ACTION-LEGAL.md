# Kaan-Action: Legal & Security Surface

Phase 34 ships the **surface** for several security/legal artefacts. The
artefacts themselves require Kaan's personal credentials, identity, or
keys — they cannot be generated autonomously. This file is the runbook.

Each item below is **blocking for v1 launch** but **non-blocking** for
the engineering Phase 34/38 pipeline. The CI workflows handle absence
gracefully (skip-with-note pattern).

---

## LEGAL-CAPACITY CARVEOUTS (Pitfall P46 — hard rule)

**Autonomous agents (Claude or otherwise) operating on this repo must
NEVER discharge the following items.** They require human legal capacity
or human identity attestation:

1. **DIST-09 — Apple Developer Program Agreement update.** Francesco-action
   (legal entity capacity — Bravoh SAGL signatory). See §6 below.
2. **DIST-11 — SignPath OSS Foundation application.** Kaan-action (identity
   attestation — the human who owns the OSS project). See §7 below.

The remaining items below (cert generation, secret upload, smoke-tests)
are **post-approval mechanical steps**. Once the two carveouts above
discharge, Kaan can perform them autonomously or via guided automation.

**CI enforcement (P46 audit):** `.github/workflows/verify-signed.yml` and
`.github/workflows/release.yml` greps for forbidden `(curl|wget|
Invoke-WebRequest|Invoke-RestMethod).*(POST|PUT).*(apple\.com|signpath\.io|
notarytool)` patterns in any workflow or script. CI fails fast if an
autonomous-discharge attempt slips through.

---

## 1. PGP key for `security@bravoh.com` (SEC-06)

**File to replace:** [`KAAN-PGP-PLACEHOLDER.asc`](./KAAN-PGP-PLACEHOLDER.asc)
**SECURITY.md table to update:** Fingerprint cell.

**Steps:**

```bash
# 1. Generate ed25519 (modern, smaller key, faster verify).
gpg --quick-generate-key 'security@bravoh.com' ed25519 cert,sign,auth,encr 2y

# 2. Note the fingerprint.
gpg --list-secret-keys --keyid-format LONG security@bravoh.com

# 3. Export ASCII-armored public key.
gpg --armor --export security@bravoh.com > KAAN-PGP-PLACEHOLDER.asc
mv KAAN-PGP-PLACEHOLDER.asc KAAN-PGP.asc
# OR replace in place if we want to keep the filename:
gpg --armor --export security@bravoh.com > KAAN-PGP-PLACEHOLDER.asc

# 4. Upload to keyservers.
gpg --keyserver keys.openpgp.org --send-keys <FINGERPRINT>
gpg --keyserver pgp.mit.edu      --send-keys <FINGERPRINT>

# 5. Generate + safe-store the revocation cert.
gpg --output revoke-bravoh-security.asc --gen-revoke security@bravoh.com
# Store the revocation cert OFFLINE (1Password vault, encrypted USB).
```

**Then:** edit `SECURITY.md` to replace
`PLACEHOLDER-FINGERPRINT-NOT-REAL` with the real fingerprint and the
`Status` column from `placeholder` to `live`.

---

## 2. Apple Developer ID signing (deferred to Phase 38)

Phase 34 provides the verifier surface (`verify_signed.py` +
`.github/workflows/verify-signed.yml`). Phase 38 wires the real
signing. **No autonomous POST/PUT** to Apple endpoints is permitted at
any phase boundary — see Pitfall P46 audit step in `verify-signed.yml`.

**When Phase 38 runs, Kaan must:**

1. Enroll the Bravoh org in Apple Developer Program (one-time, paid).
2. Generate Developer ID Application certificate via Xcode.
3. Export `.p12` → base64-encode → store in GitHub Secret
   `APPLE_DEVELOPER_ID_P12_BASE64`.
4. Generate App-Specific Password for notarytool → store in
   `APPLE_NOTARY_PASSWORD`.
5. Set `APPLE_TEAM_ID` and `APPLE_NOTARY_EMAIL` GitHub Secrets.

The `release.yml` workflow already references these secrets and falls
back to mock-signing if absent.

---

## 3. SignPath OSS code-signing for Windows (deferred to Phase 38)

SignPath offers free code-signing certificates for OSS projects on
GitHub.

**Steps:**

1. Apply via <https://signpath.org/products/foundation> with the GitHub
   repo URL.
2. Wait for SignPath team approval.
3. SignPath issues an API token → store in GitHub Secret
   `SIGNPATH_API_TOKEN`.
4. Configure the signing policy via SignPath dashboard (NEVER via
   curl from CI — Pitfall P46).
5. Add `SIGNPATH_ORG_ID` and `SIGNPATH_PROJECT_ID` GitHub Secrets.

---

## 4. Tauri updater public key (Phase 18 already shipped placeholder)

Phase 18 Plan 18-04 wired the updater. Kaan must replace the placeholder
ed25519 key:

```bash
cargo tauri signer generate -w ~/.tauri/vibemix-updater.key
# pubkey goes into tauri/src-tauri/tauri.conf.json5 (updater.pubkey)
# privkey goes into GitHub Secret TAURI_UPDATER_PRIVATE_KEY
```

---

## 5. Bravoh proxy per-client rate-limit token issuance

The threat model (Phase 34 / SEC-07) assumes the Bravoh proxy issues
short-lived JWTs per vibemix install ID. This is a Bravoh-side service
configuration:

1. Define `vibemix.client.signin` endpoint on Bravoh proxy.
2. Issue ed25519 device-bound JWT (TTL 24h, refresh via install-id).
3. Add per-install token-bucket: 60 req/min default; 600 req/min on opt-in
   "power user" tier (out-of-band approved).
4. Log abuse events to Bravoh's `abuse-log` topic.

This is **Bravoh-side work**, not vibemix-repo work. Tracked in Bravoh's
backlog, not in this repo's `.planning/`.

---

## Audit boundary

Claude (and any other AI agent operating on this repo) **must not**:

- POST or PUT to `*.apple.com`, `*.signpath.io`, `notarytool` endpoints.
- Generate real PGP keys autonomously (would invalidate Kaan's identity claim).
- Commit any of the secrets listed above (CI gitleaks + .secrets.baseline
  catch this; the surgical AIza-fixture allowlist does not cover any of
  the above patterns).

The `.github/workflows/verify-signed.yml::audit-no-apple-signpath-post`
job is the persistent gate.

---

## 6. DIST-09 — Apple Developer Program Agreement update (FRANCESCO-ACTION)

**REQ-ID:** DIST-09
**Owner:** Francesco (Bravoh cofounder, legal entity signatory)
**Status:** ☐ pending  ☐ in-progress  ☐ done
**Effort:** ~10 minutes once Francesco logs in
**Blocking for:** v1 launch (any tagged release that needs signed macOS binaries)

### Why this is FRANCESCO-action

Apple's Developer Program License Agreement updates require **acceptance
by a person with legal capacity to bind the developer entity** (here:
Bravoh SAGL). Francesco is the cofounder with that capacity. Claude (and
any other AI agent) **cannot** legally accept this on Bravoh's behalf —
Pitfall P46 hard rule.

### Protocol

1. Francesco logs into <https://developer.apple.com/account/> with the
   Bravoh org's Apple ID (NOT a personal Apple ID).
2. Banner at top: "Review and accept the updated Developer Program
   License Agreement." Click → read → accept.
3. If Apple prompts for an entity update (e.g. updated D-U-N-S, address,
   tax info) → complete it. May require uploading a corporate document
   (Camera di Commercio certificate) — Francesco knows where this is.
4. Confirm the org page shows "Active" + green checkmark on the
   "Program License Agreement" row.
5. Update this section's checkbox to ☑ done with date.

### What unblocks

- Apple Developer ID Application certificate generation (mechanical, §2 above).
- GitHub Secret upload (mechanical, §2 above).
- macOS sign + notarize CI leg (`release.yml::build-macos::SIGN + PACKAGE`).

### Sign-off block

```
DIST-09 ACCEPTED by:    _____________________   (Francesco signature)
Date:                   _____________________
Bravoh org Apple ID:    _____________________   (last 4 chars only — full ID is private)
Program License Agreement version: _____________________
```

---

## 7. DIST-11 — SignPath OSS Foundation application (KAAN-ACTION)

**REQ-ID:** DIST-11
**Owner:** Kaan (founder, owns the OSS project + identity)
**Status:** ☐ pending  ☐ submitted  ☐ approved  ☐ secret-loaded
**Effort:** ~20 minutes to submit; **~1-week SLA** for SignPath approval
**Blocking for:** v1 launch (any tagged release that needs signed Windows binaries)

### Why this is KAAN-action

SignPath OSS Foundation grants free code-signing certificates to
**identifiable open-source maintainers**. The form requires a personal
identity attestation + repo ownership confirmation. Claude (and any
other AI agent) **cannot** attest to Kaan's identity on his behalf —
Pitfall P46 hard rule.

### Protocol

1. Open <https://signpath.org/products/foundation>.
2. Click "Apply for free OSS code signing".
3. Fill the form:
   - **Repo URL:** the public vibemix repo URL (Kaan replaces with real URL).
   - **License:** Apache-2.0 (confirm via `LICENSE` file at repo root).
   - **Maintainer name + email:** Kaan's real name + GitHub-verified email.
   - **Project description:** vibemix one-line pitch from `README.md`.
   - **Distribution model:** GitHub Releases (link to releases page).
4. Submit. SignPath emails an acknowledgement within ~24h.
5. **Wait ~1 week** for SignPath team review. They may request follow-up
   info (e.g. screenshot of repo activity, confirmation that no
   commercial entity controls the project).
6. On approval, SignPath provisions:
   - An organization ID (UUID).
   - A project slug.
   - A signing-policy slug.
   - An API token (in the SignPath dashboard under Settings → API Tokens).
7. Kaan uploads to GitHub Secrets (mechanical, §3 above):
   - `SIGNPATH_API_TOKEN`
   - `SIGNPATH_ORGANIZATION_ID`
   - `SIGNPATH_PROJECT_SLUG`
   - `SIGNPATH_SIGNING_POLICY_SLUG`
8. Update this section's checkbox to ☑ approved + ☑ secret-loaded with date.
9. **Optional but recommended:** Kaan rehearses the local signing flow
   first via `scripts/dist/sign_windows.ps1` (DIST-18 — needs the
   `SignPathClient.exe` CLI installed locally) before the first tagged
   release relies on CI signing.

### What unblocks

- SignPath signing policy configuration via SignPath dashboard
  (NEVER via curl from CI — Pitfall P46).
- Windows sign CI leg (`release.yml::build-windows::SIGN — Submit
  signing request to SignPath`).

### Sign-off block

```
DIST-11 APPLIED on:     _____________________   (date submitted)
DIST-11 APPROVED on:    _____________________   (date SignPath confirmed)
SignPath org ID (last 4 chars only):   _____________________
SignPath project slug:  _____________________
Secrets uploaded by:    _____________________   (Kaan signature)
```

---

## 8. DIST-19 — Sign+verify smoke on first signed binary (KAAN-ACTION)

**REQ-ID:** DIST-19
**Owner:** Kaan
**Status:** ☐ pending  ☐ done
**Effort:** ~5 minutes per platform once first signed CI artifact lands

After the first tagged release that successfully exercises both signing
legs (i.e. DIST-09 + DIST-11 + all GitHub Secrets discharged), Kaan must:

1. Download the signed `.dmg` from GitHub Releases.
2. Run `bash tauri/src-tauri/spike/sign-and-test.sh` against it — the
   spike script does ad-hoc codesign + AX probe (Phase 24 OVERLAY-02
   verdict closure).
3. Verify verdict is `VERDICT_PASS` or `VERDICT_PARTIAL`.
4. Download the signed `.msi` from the same release.
5. Right-click → Properties → Digital Signatures → confirm "SignPath
   Foundation" CA appears in the chain.
6. Update this section's checkbox.

This closes v2.0 OVERLAY-02 Wave-0 verdict (was deferred to Phase 38
gating).

### Sign-off block

```
DIST-19 SMOKE PASS on:  _____________________   (date)
macOS verdict:          _____________________   (PASS / PARTIAL / FAIL)
Windows chain:          _____________________   (SignPath / OTHER)
Sign-off by:            _____________________   (Kaan signature)
```

---

## INSTALL-VM-RUN — Fresh-VM rehearsal real execution (Phase 33 / Plan 33-08)

**Owner:** Kaan
**Status:** ☐ pending  ☐ done
**Effort:** Variable — depends on whether tart images / Windows ISO are already cached locally.

Phase 33 ships the rehearsal **scaffold** (`scripts/install_rehearsal/`
+ `.github/workflows/install-rehearsal.yml` dry-run). Real VM execution
stays Kaan-action because it requires:

1. Disk space (multi-GB per macOS image; ~20GB per Windows VM).
2. A macOS license already attached to the host (tart images inherit
   from Apple-licensed bare-metal).
3. A Windows 10/11 ISO Kaan downloads from `microsoft.com/software-download`.

The harness intentionally double-gates real execution behind:

- `--real` CLI flag passed to `scripts/install_rehearsal/rehearsal_runner.py`.
- `INSTALL_REHEARSAL_REAL=1` environment variable.

Both must be present. Autonomous agents never set either; CI runs in
dry-run mode only.

### Run protocol (Kaan)

1. Install tart on a Mac: `brew install cirruslabs/cli/tart`.
2. Pre-cache the matrix images (one-time):
   ```bash
   tart clone ghcr.io/cirruslabs/macos-12.3:latest macos-12.3-base
   tart clone ghcr.io/cirruslabs/macos-14:latest macos-14-base
   tart clone ghcr.io/cirruslabs/macos-15:latest macos-15-base
   ```
3. For Windows, edit `scripts/install_rehearsal/win_vm_setup.ps1` and
   replace the `<KAAN: paste ... ISO URL>` placeholders with real
   Microsoft ISO URLs.
4. Run the matrix in real mode:
   ```bash
   INSTALL_REHEARSAL_REAL=1 python scripts/install_rehearsal/rehearsal_runner.py --matrix all --real
   ```
5. Stopwatch each VM's first-launch onboarding flow against the ≤60s
   target (INSTALL-05). Record results in the sign-off block below.

### Sign-off block

```
INSTALL-VM-RUN  macOS 12.3:   _____ s  (target ≤ 60)
INSTALL-VM-RUN  macOS 14:     _____ s  (target ≤ 60)
INSTALL-VM-RUN  macOS 15:     _____ s  (target ≤ 60)
INSTALL-VM-RUN  Windows 10:   _____ s  (target ≤ 60)
INSTALL-VM-RUN  Windows 11:   _____ s  (target ≤ 60)
Sign-off by:    _____________________   (Kaan signature)
```
