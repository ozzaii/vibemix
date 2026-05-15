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

## §SHIP — Phase 39 Public RC Cut + Ship (Kaan + Francesco actions)

The Phase 39 autonomous deliverables prepare scripts, content, gates, and
templates. The six customer-facing actions below are **Kaan/Francesco-
action**: autonomous agents never click "publish".

### SHIP-CUT — Execute `cut_release.sh` + `gh release create` (KAAN-ACTION)

**REQ-ID:** SHIP-01 / SHIP-06
**Owner:** Kaan
**Status:** ☐ pending  ☐ done
**Blocked on:** Phase 38 secrets populated (DIST-09 + DIST-11) + signed
binaries in `dist/`.

**Protocol:**

1. Wait for Phase 37 milestone audit to be re-run (verdict WIRED).
2. Wait for Phase 38 signing pipeline to produce signed `dist/*.dmg` + `dist/*.msi`.
3. Run `python scripts/launch/populate_changelog.py --tag v2.1.0-rc1` to
   render `CHANGELOG-v2.1.0-rc1.md` at repo root. Review.
4. Run `bash scripts/launch/cut_release.sh v2.1.0-rc1`. Confirm all 6
   pre-flight gates PASS.
5. Copy the printed `gh release create v2.1.0-rc1 --draft ...` command.
6. Run it. **First cut MUST be `--draft`.**
7. Inspect the GitHub-side draft: artifacts attached, changelog renders,
   no signing verification warnings.
8. Flip to published: `gh release edit v2.1.0-rc1 --draft=false --repo bravoh/vibemix`.
9. Update sign-off block.

**Sign-off block:**

```
SHIP-CUT EXECUTED on:    _____________________   (date)
Tag:                     _____________________   (e.g. v2.1.0-rc1)
Pre-flight gates:        _____________________   (6/6 PASS / partial)
gh release URL:          _____________________
Draft → published flip:  _____________________   (date)
Sign-off by:             _____________________   (Kaan signature)
```

### SHIP-TWEET — 4-channel social publish (KAAN + FRANCESCO-action)

**REQ-ID:** SHIP-03
**Owner:** Kaan (Twitter, HN, Reddit) + Francesco (IG IT/EN)
**Status:** ☐ pending  ☐ in-NACK-window  ☐ published  ☐ verified
**Blocked on:** SHIP-CUT published (Release URL live).

**Protocol:**

1. Confirm `gh release` is live + public (not draft).
2. Run `python scripts/launch/publish_social_posts.py --dry-run` — Discord
   preview channel receives 5 rendered post previews.
3. 5-minute NACK window: react 👎 to any post in `#vibemix-launch-preview`
   to veto. The script aborts if NACK detected.
4. Once NACK window clears clean: Kaan manually posts to Twitter + HN +
   Reddit r/DJs using the rendered text. Francesco posts to IG IT + IG EN.
5. All posts must use the canonical `utm_source=github&utm_medium=oss&utm_campaign=vibemix_launch`
   URL trail.
6. Record post URLs in sign-off block.

**Sign-off block:**

```
SHIP-TWEET TWITTER on:   _____________________   (URL)
SHIP-TWEET HN on:        _____________________   (URL)
SHIP-TWEET REDDIT on:    _____________________   (URL)
SHIP-TWEET IG_IT on:     _____________________   (URL — Francesco)
SHIP-TWEET IG_EN on:     _____________________   (URL — Francesco)
Sign-off by:             _____________________   (Kaan + Francesco)
```

### SHIP-DISCORD — `#announcements` launch post (KAAN-ACTION)

**REQ-ID:** SHIP-04
**Owner:** Kaan
**Status:** ☐ pending  ☐ done

**Protocol:**

1. Confirm `DISCORD_WEBHOOK_URL` (real `#announcements` webhook) is set in your
   shell, plus `DISCORD_ALIGNED_ROLE_ID` (aligned-community pinged role).
2. `LAUNCH_REAL=1 python scripts/launch/post_discord_launch.py --real`.
3. Verify the announcement renders properly on the Discord side (role
   ping resolved, link unfurls, image preview from the README hero loads).
4. Pin the message.

**Sign-off block:**

```
SHIP-DISCORD POSTED on:  _____________________   (date)
Channel:                 _____________________   (#announcements)
Role pinged:             _____________________   (role name)
Pin confirmed:           _____________________   (Y/N)
Sign-off by:             _____________________   (Kaan)
```

### SHIP-TRANSFER — Repo transfer to `bravoh/vibemix` GitHub org (KAAN-ACTION)

**REQ-ID:** SHIP-05
**Owner:** Kaan
**Status:** ☐ pending  ☐ done

**Protocol:**

1. Confirm `docs/launch/github-meta.md` description + topics are correct.
2. `GH_META_REAL=1 bash scripts/launch/sync_github_meta.sh --real`.
3. Verify topics + description applied at <https://github.com/bravoh/vibemix>.
4. **Then** trigger the repo transfer flow: GitHub Settings → "Transfer
   ownership" → enter `bravoh` org → confirm. This step requires
   destination-org admin acceptance (~1 click on Bravoh-org side).
5. After transfer completes, re-run `sync_github_meta.sh --real` against
   the new `bravoh/vibemix` path (topics/description re-applied).
6. Update all `bravoh-ai/vibemix` references in docs to `bravoh/vibemix`.

**Sign-off block:**

```
SHIP-TRANSFER REQUESTED on:  _____________________
SHIP-TRANSFER COMPLETED on:  _____________________   (org-admin confirmation)
GitHub topics applied:       _____________________   (10/10)
Sign-off by:                 _____________________   (Kaan)
```

### SHIP-ROTATE — 24h monitoring rotation execution (KAAN + FRANCESCO + BRAVOH-action)

**REQ-ID:** SHIP-07
**Owner:** Kaan (primary) + Francesco (EU evening) + Bravoh-team (async + overnight)
**Status:** ☐ pending  ☐ in-progress  ☐ done

**Protocol:** Follow `docs/launch-rotation.md` (24h hourly schedule).

Each responder logs end-of-hour handoff in `#vibemix-rota` per the
schema in §"Handoff format". Escalation paths in the rotation doc.

**Sign-off block (record at T+24h):**

```
SHIP-ROTATE T+0  → T+8   primary:   _____________________
SHIP-ROTATE T+8  → T+16  primary:   _____________________
SHIP-ROTATE T+16 → T+24  primary:   _____________________
Issues opened in 24h:                _____________________
Showstoppers escalated:              _____________________
Star count at T+24:                  _____________________
Sign-off by:                         _____________________   (Kaan)
```

### SHIP-V1-DECISION — Cut v1.0.0 from RC bake (KAAN-ACTION, separate phase)

**REQ-ID:** SHIP-06 (ext)
**Owner:** Kaan
**Status:** ☐ pending  ☐ greenlit  ☐ cut

**Bake window:** Minimum ~2 weeks after RC1 published. During the bake:

- Monitor for showstopper bugs.
- Collect anti-slop bug reports.
- Triage controller-mapping issues.
- Watch star quality (~30 day retention check; P59).

If RC1 holds clean for 2+ weeks: separate phase scaffolds the v1.0.0 cut.
If RC2 is needed: same flow, new RC tag (`v2.1.0-rc2`).

**Sign-off block:**

```
SHIP-V1-DECISION at:     _____________________   (date)
Decision:                _____________________   (cut v1 / cycle RC2 / pause)
Reasoning:               _____________________   (1-2 lines)
Sign-off by:             _____________________   (Kaan)
```

---

## §POST-RC-CLEANUP — Phase 16 override expiry + v2.2 grooming (KAAN-ACTION)

**REQ-ID:** SHIP-08 / P85
**Owner:** Kaan
**Status:** ☐ pending  ☐ done

After the v2.1 RC is published AND the ~2-week bake window has elapsed
without showstoppers, the following cleanup MUST be performed before
v1.0.0 cut or v2.2 milestone scaffolding:

### 1. Phase 16 ear-test memory override expiry (P85)

The autonomy override line in `.planning/STATE.md`:

> Phase 16 ear-test memory override accepted for v2.1 only (autonomous
> proxy gate via Phase 27 substitutes). **Override expires post-v2.1.**

…must be removed (or marked `EXPIRED on YYYY-MM-DD`). The Phase 27
autonomous hallucination-proxy gate was a v2.1-scoped substitute for
the original Kaan-ear-only test (Phase 16). Post-v2.1, the original
gate is back in force — meaning v2.2+ phases that ship reaction prompts
must include Kaan-ear test sign-off, not autonomous-only proxy gates.

The `scripts/launch/cut_release.sh` exit reminder line ("Phase 16
override cleanup reminder") flags this every time the cutter runs.

### 2. Bravoh funnel verification

Confirm the `utm_source=github&utm_medium=oss&utm_campaign=vibemix_launch`
attribution lands in Bravoh's analytics. If signups are not arriving
or attribution is broken, work with Momo to fix the proxy / landing.

### 3. v2.2 backlog grooming

Open issues in `.planning/research/v2-2/` (TBD) for deferred items:

- Mixxx OSC integration (`v2_open_candidates`).
- Rekordbox parse (carry-forward from v2.0 hardening).
- ProDJ Link probe (v2 stretch).
- Mac App Store / MS Store distribution.
- Translation of social copy beyond IT.

### Sign-off block

```
POST-RC-CLEANUP Phase 16 override expired on:  _____________________
POST-RC-CLEANUP Bravoh funnel verified on:     _____________________
POST-RC-CLEANUP v2.2 backlog seeded on:        _____________________
Sign-off by:                                   _____________________   (Kaan)
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
