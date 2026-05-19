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

## AUDIO-05 — Real PGP key generation + publish (post-Plan 40-05 discharge)

**REQ-ID:** AUDIO-05 (supersedes SEC-06 PGP — same slot, new ID)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 40-05 scaffolded slot file)  ☐ key generated  ☐ published to keys.openpgp.org  ☐ SECURITY.md updated  ☐ legacy `.asc` removed
**Effort:** ~5 minutes (key gen) + ~5 minutes (email-verify on keys.openpgp.org)
**Blocking for:** Phase 40 AUDIO-05 requirement closure (engineering pre-stage ships green; this discharge flips the gate test to post-discharge mode automatically).

### Why this is KAAN-action

Real PGP keys carry identity attestation — only Kaan can generate one
for `security@bravoh.com`. Autonomous agents must NOT discharge this
(would invalidate the identity claim — Pitfall P46 hard rule).

### Files involved

- **Slot file:** `docs/security/pgp-public-key.txt` (created by Plan 40-05; currently contains the `PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED` sentinel inside a valid PGP armor envelope).
- **SECURITY.md:** PGP section + fingerprint table.
- **Legacy placeholder:** `KAAN-PGP-PLACEHOLDER.asc` at repo root — removed via `git rm` during discharge.

### Runbook (5 steps)

```bash
# 1. Generate ed25519 key (modern, smaller, faster verify).
#    No passphrase for the OSS security@ inbox key.
gpg --quick-gen-key 'Bravoh Security <security@bravoh.com>' ed25519 default 0

# 2. Get the fingerprint (copy this into SECURITY.md table).
gpg --list-keys security@bravoh.com
# → look for the 40-char hex fingerprint on the second line

# 3. Export ASCII-armored public key, overwriting the placeholder slot file.
gpg --armor --export security@bravoh.com > docs/security/pgp-public-key.txt

# 4. Publish to keys.openpgp.org (HKPS — requires email verification).
gpg --send-keys --keyserver hkps://keys.openpgp.org <FINGERPRINT>
# → keys.openpgp.org sends a verification email to security@bravoh.com
# → click the link in that email to make the key searchable by email

# 5. SECURITY.md cleanup + legacy file removal.
# - Replace `PLACEHOLDER-FINGERPRINT-NOT-REAL` with the real fingerprint
# - Replace `placeholder — Kaan-action` with `live`
# - Remove the "This is a placeholder key." paragraph
git rm KAAN-PGP-PLACEHOLDER.asc
git add docs/security/pgp-public-key.txt SECURITY.md
git commit -m "chore(security): publish real PGP key for security@bravoh.com (AUDIO-05)"
```

### Discharge checklist

When the runbook is complete, the following invariants must hold (the
gate test `tests/security/test_pgp_published.py` enforces them):

- [ ] `docs/security/pgp-public-key.txt` no longer contains `PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED`.
- [ ] `docs/security/pgp-public-key.txt` contains a valid `-----BEGIN PGP PUBLIC KEY BLOCK-----` armor envelope with ≥200 chars of body.
- [ ] `docs/security/pgp-public-key.txt` contains NO `-----BEGIN PGP PRIVATE KEY BLOCK-----` (only the public half ever lives in the repo).
- [ ] `SECURITY.md` no longer references `KAAN-PGP-PLACEHOLDER.asc`.
- [ ] `SECURITY.md` no longer contains `PLACEHOLDER-FINGERPRINT-NOT-REAL`.
- [ ] `KAAN-PGP-PLACEHOLDER.asc` no longer exists at repo root.
- [ ] The key is searchable via `gpg --keyserver hkps://keys.openpgp.org --search security@bravoh.com` (after email-verify click).

### Sign-off block

```
AUDIO-05 KEY GEN on:     _____________________   (date)
AUDIO-05 FINGERPRINT:    _____________________   (real fingerprint)
AUDIO-05 PUBLISHED on:   _____________________   (date keys.openpgp.org confirmed)
SECURITY.md updated:     _____________________   (commit hash)
Legacy .asc removed:     _____________________   (commit hash)
Sign-off by:             _____________________   (Kaan signature)
```

---

## AUDIO-06 — Tauri ed25519 updater key rotation (post-Plan 40-05 discharge)

**REQ-ID:** AUDIO-06 (supersedes the §4 stub — same slot, new ID)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 40-05 scaffolded comment block)  ☐ keypair generated  ☐ pubkey in tauri.conf.json5  ☐ private half in GH secret  ☐ rehearsal run green
**Effort:** ~10 minutes
**Blocking for:** First tagged release that needs auto-update signatures (the `placeholder-pubkey-gate` job in `release.yml` fires only on tagged pushes).

### Why this is KAAN-action

The private half of the updater keypair must never touch the repo. Only
Kaan can run `tauri signer generate` on his machine, copy the public half
into `tauri.conf.json5`, and upload the private half as a GitHub Secret
via `gh secret set`. Autonomous agents could only ever scaffold the
rotation — not perform it.

### Files involved

- **`tauri/src-tauri/tauri.conf.json5`:** `plugins.updater.pubkey` field (currently the 2026-05-13 dev key from Phase 18-04).
- **GitHub Secret:** `TAURI_UPDATER_PRIVATE_KEY` (base64-encoded private half).
- **`.github/workflows/release.yml`:** `placeholder-pubkey-gate` job (already wired; fires on tagged pushes only).

### Runbook (4 steps)

```bash
# 1. Generate new keypair locally (no password — matches Phase 18 setup,
#    Tauri CI signing tolerates passwordless via TAURI_UPDATER_KEY_PASSWORD="").
npx @tauri-apps/cli signer generate \
    -w ~/.tauri/vibemix_updater_prod.key \
    --no-password

# 2. Read the public half; paste into tauri.conf.json5.
cat ~/.tauri/vibemix_updater_prod.key.pub
# → replace the pubkey value at tauri/src-tauri/tauri.conf.json5
#   plugins.updater.pubkey (the 2026-05-13 dev-key string starting
#   "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDk0QThGNkNFNDJFNjQ4N0Q...")

# 3. Base64-encode the private half and store as GH secret.
base64 -i ~/.tauri/vibemix_updater_prod.key | gh secret set TAURI_UPDATER_PRIVATE_KEY

# 4. Rehearse via workflow_dispatch (the placeholder-pubkey-gate skips
#    on non-tag pushes, so a dispatch run exercises the build path).
gh workflow run release.yml --ref main
# → confirm the "Build macOS" + "Build Windows" jobs reach the signing
#   step without "minisign signature verification failed" errors.
```

### Discharge checklist

When the runbook is complete, the following invariants must hold (the
gate test `tests/tauri/test_updater_key_rotated.py` enforces them):

- [ ] `tauri/src-tauri/tauri.conf.json5` no longer contains the dev-key fingerprint `94A8F6CE42E6487D`.
- [ ] `plugins.updater.pubkey` decodes via base64 to a string starting with `untrusted comment: minisign public key:`.
- [ ] `gh secret list` shows `TAURI_UPDATER_PRIVATE_KEY` present (with the recent updated date).
- [ ] A `workflow_dispatch` rehearsal run of `release.yml` completes the signing step without errors.
- [ ] `.github/workflows/release.yml::placeholder-pubkey-gate` job still exists (Pitfall 6 regression guard — RESEARCH §State of the Art).

### Sign-off block

```
AUDIO-06 KEYPAIR GEN on:     _____________________   (date)
AUDIO-06 PUBKEY ROTATED on:  _____________________   (commit hash)
AUDIO-06 GH SECRET SET on:   _____________________   (gh secret set output OK)
AUDIO-06 REHEARSAL on:       _____________________   (workflow run URL)
Sign-off by:                 _____________________   (Kaan signature)
```

---

## AUDIO-07 — Fresh-Mac BlackHole probe walk-through (post-Plan 40-06 discharge)

**REQ-ID:** AUDIO-07
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 40-06 shipped emit hooks + Pitfall 5 retry)  ☐ fresh-account walk done  ☐ events.jsonl artifact captured  ☐ Sign-off
**Effort:** ~15 minutes on a Mac with a spare user account (no BlackHole installed) — covers full wizard click-through + post-install re-probe.

### Why this is KAAN-action

The probe engineering surface (event emission + Pitfall 5 fresh-boot
race defense) is fully scaffolded by Plan 40-06 and pinned by the
`tests/install/test_blackhole_probe_events.py` suite. What stays
KAAN-action is the end-to-end install-funnel walk on a Mac that has
never seen BlackHole — only Kaan can run that on his own hardware
(autonomous agents have no fresh-Mac user account to step through, no
way to click an external installer, no way to verify the post-install
events.jsonl artifact qualitatively against real DJ ear).

### Pre-requisites

- A Mac (any supported macOS version — 12.3 / 14 / 15).
- A spare user account on that Mac with **no BlackHole installed**
  (or a fresh user via System Settings → Users & Groups → Add User).
  An existing account that already has BlackHole works only after
  `sudo /usr/local/bin/BlackHole-uninstaller` is run first.
- vibemix installer or dev build available on disk.

### Walk-through (4 steps)

1. **Pre-walk sanity check.** Log into the fresh user account. Confirm
   `system_profiler SPAudioDataType | grep -i blackhole` prints
   nothing. Launch vibemix.

2. **Wizard step — probe-missing path.** The wizard should land on
   the "Install BlackHole 2ch" affordance. Watch the running
   session's `events.jsonl` (locate via the session-dir log; typical
   path is `~/Library/Application Support/vibemix/sessions/<UUID>/events.jsonl`).

   Expected event sequence so far:
   ```
   {"t": ..., "kind": "audio.probe.missing", "device_name": null}
   ```

3. **Wizard step — CTA click.** Click "Install BlackHole" in the
   wizard. The OS default browser must open
   `https://existential.audio/blackhole/`. Immediately re-read
   `events.jsonl` — expected next line:
   ```
   {"t": ..., "kind": "audio.probe.cta_fired", "cta": "blackhole_install_link_opened", "url": "https://existential.audio/blackhole/"}
   ```

4. **External install + re-probe.** Download and install BlackHole 2ch
   from the official site. Return to vibemix and either (a) click the
   wizard's "I've installed it, retry" affordance, or (b) restart the
   sidecar. The probe should now detect the device; expected next
   line in `events.jsonl`:
   ```
   {"t": ..., "kind": "audio.probe.detected", "device_name": "BlackHole 2ch"}
   ```

### Pitfall 5 sanity (optional — covered by automated tests but worth
eyeballing once on real hardware)

After installing BlackHole, **reboot the Mac** and re-launch vibemix
within 5-10 seconds of the desktop appearing (i.e. before CoreAudio
has fully enumerated devices). The Plan 40-06 retry guard should
prevent a spurious `audio.probe.missing` → `audio.probe.cta_fired`
sequence — the probe sleeps 1.5s and re-queries before declaring
missing. The events.jsonl should show ONLY:
```
{"t": ..., "kind": "audio.probe.detected", "device_name": "BlackHole 2ch"}
```
If you see a `missing` event followed seconds later by `detected` on
this fresh-boot run, the Pitfall 5 retry isn't firing — open a bug.

### Discharge checklist

When the walk is complete, the following must hold:

- [ ] `events.jsonl` from the fresh-account walk contains all three
      `audio.probe.*` event kinds in the order:
      `missing` → `cta_fired` → `detected`.
- [ ] The `cta_fired` event's `url` field equals
      `https://existential.audio/blackhole/` exactly (no trailing
      query strings, no protocol downgrade).
- [ ] The OS default browser opened to the install URL on CTA click.
- [ ] Post-install re-probe surfaced `audio.probe.detected` with a
      non-null `device_name` containing the substring `"BlackHole"`.
- [ ] Pitfall 5 fresh-boot retry was visually confirmed (no spurious
      missing → detected sequence on cold-boot probe).
- [ ] Captured `events.jsonl` artifact attached to the sign-off block
      (link or path).

### Sign-off block

```
AUDIO-07 PRE-WALK CHECK on:    _____________________   (date)
AUDIO-07 FRESH-USER ACCOUNT:   _____________________   (account name on Mac)
AUDIO-07 MAC OS VERSION:       _____________________   (12.3 / 14 / 15)
AUDIO-07 EVENTS.JSONL ARTIFACT:_____________________   (path or link)
AUDIO-07 PITFALL-5 RETRY OK:   _____________________   (yes / no — single detected event after fresh boot)
Sign-off by:                   _____________________   (Kaan signature)
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

### Parallels quickstart (Win 11 only, ~20 min) — Kaan's MacBook

Use when the full 5-row tart matrix is overkill and a single Win-side smoke
is enough to flip the "drop-in install works on Windows" claim from claimed
to verified. Kaan ships a Parallels license; this path uses it.

1. **Get the installer.** Either:
   - Wait for a tagged release → grab `vibemix-Setup-<ver>-x64.exe` from
     the GH release page; OR
   - Build locally from the current main:
     ```bash
     # On the host MacBook
     cd ~/projects/dj-set-ai
     # Win cross-build is CI-only on Mac; for a local smoke, either grab the
     # latest `install-rehearsal.yml` artifact OR run `release.yml` against a
     # disposable tag (e.g. `v0-rehearsal-$(date +%Y%m%d)`).
     gh run download <run-id> --name vibemix-windows-x64-installer
     ```

2. **Provision a fresh Win 11 VM in Parallels.**
   - Parallels → File → New → Install Windows 11 (Express install OK).
   - 4 vCPU / 8 GB RAM / 64 GB disk minimum.
   - Once Windows lands at the desktop, take a snapshot named
     `clean-postinstall` — every retry starts from this snapshot.

3. **Drag-and-drop the installer into the VM** (Parallels shared folder or
   plain Cmd+drag onto the VM window). Resist the urge to pre-install
   VB-CABLE or any other dep — the install flow MUST handle that itself.

4. **Stopwatch the smoke.** Start timing the moment you double-click
   `vibemix-Setup-<ver>-x64.exe`. Stop when the first-launch wizard says
   "Ready" (or the equivalent end-of-onboarding screen). Target ≤ 60 s
   per INSTALL-05.

5. **Sanity checks before signing off:**
   - SmartScreen prompt: should show "Bravoh OZAI Bilişim" or the
     SignPath cert subject — NOT "unknown publisher".
   - VB-CABLE: fetched from `vb-audio.com`, installed silently, audible
     in Win sound settings as a playback device.
   - vibemix launches at end of wizard; no Python traceback in
     `%APPDATA%\vibemix\install.log`.
   - Audio test: pick VB-CABLE as the system output, play any track,
     vibemix UI should show music levels rising.

6. **Record the result** in the sign-off block above. If failure: revert
   to `clean-postinstall` snapshot, attach `install.log` to a GitHub
   issue, do NOT re-run blindly.

This covers the "Windows drop-in works" claim that the v3.1 close hook
flagged as unverified on real hardware. macOS 12.3 / 14 / 15 rows still
need tart (or a separate Mac VM tool); they are nice-to-have, not ship
blockers for a `gsd-autonomous fully` close.

### Build the installer inside the VM (when CI is unavailable)

If GH Actions billing is locked OR you just want a one-shot local build,
`scripts/win/build_local.ps1` reproduces `release.yml::build-windows`
entirely on the Win VM. First-time prereq install (one PowerShell line):

```powershell
winget install Python.Python.3.12 OpenJS.NodeJS.LTS Rustlang.Rustup JRSoftware.InnoSetup astral-sh.uv
rustup default stable
```

Then from a `git clone` of the repo inside the VM:

```powershell
pwsh scripts\win\build_local.ps1
```

Output: `installer\windows\output\vibemix-installer.exe` (unsigned —
SmartScreen will show "unrecognized app" until SignPath cert + first
release SmartScreen reputation accrues; that's expected for the smoke).

---

## §GATE-01 — Ack-bank quota refresh (20 → 40 OPUS files)

**REQ-ID:** GATE-01 (Phase 42-01)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 42-01 ships resume wrapper)  ☐ key in env  ☐ run complete  ☐ AIza scan green
**Effort:** ~5 minutes once free-tier reset window opens
**Blocking for:** GATE-04 threshold recalibration (Plan 42-02) running against a 40/40 ack-bank-complete eval.

### Why this is KAAN-action

Gemini TTS free-tier quota refresh requires Kaan's personal API key
(`GEMINI_API_KEY`). Phase 27-08 / LATENCY-15 scaffolded the batch
generator with skip-existing idempotency; 20 of the 40 OPUS entries
landed before the free-tier window closed (the residual
`ACK-BANK-REMAINING-20` set). Plan 42-01 ships the resume wrapper that
lists the missing entries + gates subprocess invocation behind
`--really`. The ~$0.10 spend itself is Kaan-discharge — autonomous
agents NEVER export `GEMINI_API_KEY` (Pitfall LATENCY-15).

### Files involved

- **Resume wrapper:** `scripts/eval/generate_ack_audio_resume.py` (Plan 42-01).
- **Underlying batch generator:** `scripts/generate_ack_audio.py` (Phase 27-08; already idempotent via skip-existing).
- **Manifest:** `assets/ack_bank/manifest.json` (40 entries, 5 buckets × 8 ids).
- **OPUS output root:** `src/vibemix/audio/ack_bank/<bucket>/<id>.opus`.

### Kaan oneliner

```bash
GEMINI_API_KEY=... uv run python scripts/eval/generate_ack_audio_resume.py --really
```

### Verification

```bash
# Inventory must show 0 missing entries after the run:
uv run python scripts/eval/generate_ack_audio_resume.py --dry-run | grep "missing: 0"

# Closeout suite must pass (Phase 27-08 audit + Plan 40 AIza scan):
uv run pytest tests/runtime_closeouts/test_ack_bank_real_audio.py \
              tests/runtime_closeouts/test_ack_bank_aiza_scan.py
```

### What unblocks

- GATE-04 threshold recalibration (Plan 42-02) — the 2-judge eval runs
  against a full 40/40 ack-bank and the F1 numbers reflect realistic
  acknowledgement-coverage instead of partial-coverage degradation.

### Sign-off block

```
GATE-01 RUN on:           _____________________   (date)
Entries generated:        _____________________   (NN / 20)
AIza scan green:          _____________________   (yes / no)
Closeout pytest green:    _____________________   (yes / no)
Sign-off by:              _____________________   (Kaan signature)
```

---

## §GATE-02 — VCR cassette population (one-time)

**REQ-ID:** GATE-02 (Phase 42-01)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 42-01 ships record-mode helper)  ☐ key in env  ☐ run complete  ☐ CI green with VCR_RECORD_MODE=none
**Effort:** ~10 minutes for the run; cassette bytes commit-via-LFS not required (cassettes are deterministic JSON < 100 KB each)
**Blocking for:** PR-mode CI eval gate no longer requiring `GEMINI_API_KEY` (today the secret is referenced in `.github/workflows/eval.yml`; cassettes make this $0).

### Why this is KAAN-action

VCR cassette population requires a real `GEMINI_API_KEY` so the
recorded interactions reflect real Gemini Pro + Flash judge responses.
One-time ~$1-2 spend across the Phase 27 eval test suite. After
cassettes land, CI replays them at $0 — the autonomous proxy gate
becomes secret-free on PR mode.

### Files involved

- **Recorder helper:** `scripts/eval/record_cassettes.py` (Plan 42-01).
- **Cassette output dir:** `tests/eval/cassettes/` (Phase 27-04; `.gitkeep` marker present).
- **VCR-decorated tests (discovered by the helper):**
  - `tests/eval/test_judge_pro_rubric.py`
  - `tests/eval/test_judge_flash_rubric.py`
  - `tests/eval/test_cited_relevance.py`
  - `tests/eval/test_substance_metric.py`

### Kaan oneliner

```bash
GEMINI_API_KEY=... uv run python scripts/eval/record_cassettes.py \
    --really --record-mode new_episodes
```

### Verification

```bash
# Cassettes dir must be non-empty after the run:
ls tests/eval/cassettes/

# CI eval gate must pass against the recorded cassettes (no API key needed):
VCR_RECORD_MODE=none uv run pytest tests/eval/test_judge_pro_rubric.py \
    tests/eval/test_judge_flash_rubric.py tests/eval/test_cited_relevance.py \
    tests/eval/test_substance_metric.py -q

# Nightly canary CI dispatch (cassettes mode):
gh workflow run "Eval Gate"
```

### What unblocks

- PR-mode eval workflow no longer requires `GEMINI_API_KEY` secret access
  (cassettes replay at $0).
- Nightly canary becomes the sole consumer of the real key (for new-episodes
  drift detection) — narrows the blast radius of an accidental key leak.

### Sign-off block

```
GATE-02 RUN on:           _____________________   (date)
Cassettes recorded:       _____________________   (NN tests covered)
PR-mode CI green:         _____________________   (workflow run URL)
Nightly canary green:     _____________________   (workflow run URL)
Sign-off by:              _____________________   (Kaan signature)
```

---

## §GATE-03 — Real-corpus DJ session WAVs (6 × 30-min, 200 MB git-LFS)

**REQ-ID:** GATE-03 (Phase 42-01)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 42-01 ships LFS layout + MANIFEST/LICENSES templates)  ☐ 6 sources curated  ☐ ffmpeg-normalized  ☐ git lfs committed
**Effort:** ~2 hours (curation + license check + ffmpeg pass + commit)
**Blocking for:** GATE-04 real-corpus threshold recalibration (Plan 42-02 `--check-real-corpus` mode no longer 0-sessions-warns).

### Why this is KAAN-action

200 MB of public-domain / CC0 DJ session audio needs human curation:
license check per source, genre balance across ≥2 genres (≥3 ideally
per CONTEXT EVAL-03), ffmpeg normalization to 16kHz mono, and the
final `git lfs add` + commit. Plan 42-01 ships the LFS scaffold
(`.gitattributes` LFS rule for `eval/corpus/sessions/**/*.wav` already
present from Phase 27-03, plus `MANIFEST.md` and `LICENSES.md`
templates with placeholder slots for the 6 sessions). The WAV bytes
themselves are Kaan-discharge — autonomous agents NEVER fetch / commit
third-party audio (license risk).

### Files involved

- **LFS rule:** `.gitattributes` line for `eval/corpus/sessions/**/*.wav` (already present).
- **Sessions root:** `eval/corpus/sessions/<id>/audio.wav` for each of:
  `hard_tek_01`, `hard_tek_02`, `techno_01`, `techno_02`, `house_01`, `house_02`.
- **Human-readable manifest:** `eval/corpus/MANIFEST.md` (Plan 42-01).
- **Structured manifest:** `eval/corpus/manifest.json` (Phase 27-03 — update `source` field per session post-curation).
- **License records:** `eval/corpus/LICENSES.md` (Plan 42-01 expanded schema).

### Kaan steps (6)

1. **Source curation.** Pick 6 sessions across ≥2 genres
   (`hard_tek`/`techno`/`house`) from archive.org / CCMixter / FMA
   Electronic. **Public-domain or CC0 only** — CC-BY is also acceptable
   if attribution slot is filled.
2. **ffmpeg normalize.** For each source file:
   ```bash
   ffmpeg -i raw_<id>.wav -ac 1 -ar 16000 \
       eval/corpus/sessions/<id>/audio.wav
   ```
3. **Fill manifests.**
   - `eval/corpus/MANIFEST.md`: complete the 7-field block per session
     (Session ID / Genre / Duration / Source URL / License / Attribution
     / SHA256).
   - `eval/corpus/LICENSES.md`: fill the 6-field block per session
     (Source URL / License / Attribution / Retrieval date / ffmpeg
     normalize / SHA256).
   - `eval/corpus/manifest.json`: update each session's `source` field
     from `TBD-*` to the real source identifier.
4. **Track LFS.** (Idempotent — rule already in `.gitattributes` from
   Phase 27-03; this step is a no-op if rule survives.)
   ```bash
   git lfs track "eval/corpus/sessions/**/*.wav"
   ```
5. **Stage + commit.**
   ```bash
   git add eval/corpus/sessions/*/audio.wav \
       eval/corpus/MANIFEST.md eval/corpus/LICENSES.md \
       eval/corpus/manifest.json
   git commit -m "corpus(42-01): GATE-03 real DJ session WAVs (200 MB LFS)"
   ```
6. **Verify.** Run the verification block below.

### Verification

```bash
# Structured manifest must validate:
uv run python -c "from scripts.eval.corpus_manifest import validate_manifest; \
                  from pathlib import Path; \
                  r=validate_manifest(Path('eval/corpus/manifest.json')); \
                  assert r['valid'], r"

# Diversity gate must pass:
uv run pytest tests/eval/test_corpus_diversity_gate.py -q

# Total LFS bytes ≈ 200 MB:
du -sh eval/corpus/sessions/

# Six LFS-tracked WAVs visible:
git lfs ls-files | grep "eval/corpus/sessions" | wc -l   # → 6
```

### What unblocks

- GATE-04 real-corpus threshold recalibration (Plan 42-02
  `--check-real-corpus` no longer 0-sessions-warns).
- `scripts/release/check_ear_test.sh` (Plan 42-03) reading the
  populated manifest at gate time satisfies the `≥2 genres` invariant
  on a real corpus.

### Sign-off block

```
GATE-03 SOURCED on:       _____________________   (date)
Genres represented:       _____________________   (hard_tek, techno, house — at least 2)
Total WAV bytes:          _____________________   (~200 MB)
ffmpeg normalize OK:      _____________________   (6 / 6)
LICENSES.md filled:       _____________________   (6 / 6)
MANIFEST.md filled:       _____________________   (6 / 6)
git lfs commit hash:      _____________________
Sign-off by:              _____________________   (Kaan signature)
```

---

## §GATE-05 — First 2 ear-test sessions (real DJ play)

**REQ-ID:** GATE-05 + GATE-07 (Phase 42-03)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 42-03 ships protocol + capture surface + bash gate)  ☐ session 1 signed  ☐ session 2 signed (different genre)  ☐ `check_ear_test.sh` exits 0
**Effort:** 2 × ≥30 min DJ sessions + ~2 min per session for the debrief toggle sign-off
**Blocking for:** Plan 42-04 `check_gate.sh` Gate-2 — the autonomous-proxy lane (7 nightly green) cannot ship by itself; the ear-test lane needs ≥ 2 in-window signed sessions across ≥ 2 genres with zero slop flags.

### Why this is KAAN-action

Real DJ play cannot be fabricated. v3.0 is single-DJ (Kaan-signed; cross-DJ
sign-off deferred to v3.x per Plan 42 CONTEXT). Per the anti-slop manifesto
("real DJ friend in your ear, no AI slop") only Kaan's ear closes the
qualitative gate that the autonomous 2-judge proxy cannot.

### Files involved

- **Protocol document:** `eval/EAR-TEST-PROTOCOL.md` (Plan 42-03 Task 1).
- **JSON Schema:** `eval/ear-test-logs/schema.json`.
- **Capture writer:** `src/vibemix/debrief/ear_test_capture.py::write_ear_test_log`.
- **Debrief UI toggle:** `tauri/ui/src/debrief/components/ear-test-toggle.ts` —
  mounts inside the existing Phase 29 debrief window on `session-loaded`.
- **Gate script:** `scripts/release/check_ear_test.sh` (Plan 42-03 Task 3).
- **Output location:** `eval/ear-test-logs/<session-id>.json`.

### Kaan steps

1. **Session 1 — pick any genre.** Run a DJ set ≥ 30 min through vibemix
   (any cohost variant). The recording session_id becomes the log filename.
2. **Open the debrief window.** When the session ends, vibemix opens the
   Phase 29 debrief window automatically (or via Settings → Recordings →
   "View debrief"). Wait for `session-loaded` to fire — the ear-test
   toggle mounts at the bottom of the layout.
3. **Click the toggle:** `Bu session'ı release-gate için işaretle / Rate
   this session for release-gate`. The form expands.
4. **Fill the form.**
   - Genre is pre-filled from the session metadata; correct if needed.
   - Tick **only** the slop-flag checkboxes that actually applied
     (`felt_slop`, `felt_scripted`, `felt_late`, `felt_generic`). For an
     ear-pass session: leave **all four unchecked**.
   - Optional: drop a one-line note in the textarea (what worked /
     didn't — stays in repo as audit trail per
     `feedback_privacy_scope_narrow`; redacted from `eval/README.md`).
5. **Hit Sign off.** The toggle posts via Tauri IPC → writer → atomic
   write of `eval/ear-test-logs/<session-id>.json`.
6. **Session 2 — different genre.** Repeat steps 1–5 within a 14-day
   window, picking a genre that differs from Session 1 (the `≥ 2 genres`
   invariant trips if both fall into the same `genre` enum value).
7. **Run the gate.**
   ```bash
   bash scripts/release/check_ear_test.sh
   ```
   Expected stdout: `PASS check_ear_test: 2 sessions across 2 genres in
   last 14 days, 0 slop-flags`. Exit code 0.
8. **Commit the logs.**
   ```bash
   git add eval/ear-test-logs/*.json
   git commit -m "ear-test(42-03): first 2 GATE-05 sessions signed"
   ```

### Verification

```bash
# Direct gate invocation:
bash scripts/release/check_ear_test.sh

# Contract tests (must still pass after Kaan-discharge):
uv run pytest tests/eval/test_check_ear_test_sh.py -q
```

### What unblocks

- Plan 42-04 `check_gate.sh` Gate-2 — the umbrella cut-script that AND-gates
  the 7 nightly autonomous-proxy results with this ear-test result.
- `cut_release.sh` Gate-2 (Phase 39-01 slot) — the v3.0 release cut.

### Sign-off block

```
GATE-05 SESSION-1 on:       _____________________   (date)
GATE-05 SESSION-1 GENRE:    _____________________
GATE-05 SESSION-1 SLOP:     _____________________   (none / list)
GATE-05 SESSION-2 on:       _____________________   (date — within 14d of session 1)
GATE-05 SESSION-2 GENRE:    _____________________   (must differ from session 1)
GATE-05 SESSION-2 SLOP:     _____________________   (none / list)
check_ear_test.sh exit 0:   _____________________   (yes / no)
Sign-off by:                _____________________   (Kaan signature)
```

---

## §VIS-04 — Mixamo account login + 5 clip downloads + retarget run

**REQ-ID:** VIS-04 (Phase 43-05)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 43-05 ships retarget pipeline + bundle size gate + clip source manifest)  ☐ Mixamo login complete  ☐ 5 clips downloaded  ☐ 5 retargets run  ☐ `check_bundle_size.sh` exit 0
**Effort:** ~30 min Mixamo browsing + 5 downloads + ~5 min per retarget run = ~1 h total
**Blocking for:** VIS-05 mood pool runtime validation (Plan 43-06) running against real retargets instead of placeholders; v3.0 ship-cut gate (Phase 45) — the visual ship lock cannot pass with placeholder GLBs in the bundle.

### Why this is KAAN-action

Mixamo (adobe.com) requires a personal Adobe ID login + browser session for clip download. Autonomous agents cannot create Adobe accounts or operate the Mixamo preview/download UI. Per CONTEXT §VIS-04: "Engineering ships retarget script + size gate + placeholder→real swap-in CI step. Kaan-discharge: actual Mixamo account login + 5 clip downloads."

Per the CDJ Whisper aesthetic constraint (CONTEXT `<specifics>`): "the Neon Rebel mascot mood for the celebrate clip should feel like a Pioneer CDJ headbob, NOT a generic VTuber dance" — only Kaan can apply that aesthetic judgment when picking among Mixamo variants. The script picks slots; Kaan picks energies.

### Files involved

- **Retarget pipeline:** `scripts/mascot/retarget_to_neon_rebel.py` (Plan 43-05 Task 1).
- **Bundle size gate:** `scripts/mascot/check_bundle_size.sh` (Plan 43-05 Task 2 — two-tier: 25 MB total + 400 KB–1200 KB per-clip).
- **Source manifest:** `scripts/mascot/MIXAMO-CLIP-SOURCES.md` (Plan 43-05 Task 2 — selection guidance for Kaan; Pioneer-CDJ-headbob aesthetic surfaced).
- **Target rig (locked):** `tauri/ui/assets/mascot/character.glb` (Neon Rebel; per memory `project_mascot_as_vtuber_personality_surface`).
- **Output slots (replace placeholders):** `tauri/ui/assets/mascot/animations/prep_*.glb` × 5.
- **Placeholder origin doc:** `tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md` (Phase 22 lineage + idle-zero contract).

### Kaan steps

1. **Open Mixamo.** Visit <https://www.mixamo.com/> and log in with the personal Adobe ID.
2. **Download 5 clips** per `scripts/mascot/MIXAMO-CLIP-SOURCES.md`:
   - Idle → `prep_settle`
   - Talk_short → `prep_head_turn_left`
   - Talk_long → `prep_head_turn_right`
   - Celebrate → `prep_lean_in_hyped` (apply CDJ-headbob aesthetic — reserved energy, not vtuber dance)
   - Headbob → `prep_lean_in_neutral`
   - Format: glTF Binary (.glb); Skin: "Without Skin" if offered (the rig comes from `character.glb`).
3. **Stage downloads:** save to `~/Downloads/mixamo_<slot>.glb` for each (the runbook's one-liners assume that filename convention).
4. **Run 5 retargets** (one per clip):
   ```bash
   uv run python scripts/mascot/retarget_to_neon_rebel.py \
       --source ~/Downloads/mixamo_idle.glb --slot prep_settle --really
   uv run python scripts/mascot/retarget_to_neon_rebel.py \
       --source ~/Downloads/mixamo_talk_short.glb --slot prep_head_turn_left --really
   uv run python scripts/mascot/retarget_to_neon_rebel.py \
       --source ~/Downloads/mixamo_talk_long.glb --slot prep_head_turn_right --really
   uv run python scripts/mascot/retarget_to_neon_rebel.py \
       --source ~/Downloads/mixamo_celebrate.glb --slot prep_lean_in_hyped --really
   uv run python scripts/mascot/retarget_to_neon_rebel.py \
       --source ~/Downloads/mixamo_headbob.glb --slot prep_lean_in_neutral --really
   ```

   The Plan 43-05 scaffold ships the CLI + size-band gate + draco shell-out wiring; the **skeleton-remap call** inside `retarget()` is `NotImplementedError` and exit code 3. Two implementation paths to fill in during discharge:

   **(a) pygltflib path** — Python-native, preferred for simple skinned-mesh inputs. `uv pip install pygltflib`, then implement the joint remap inside `retarget()` (load source.glb → walk source skeleton hierarchy → match to rig joint names → apply animation channels onto rig joints → write single-clip GLB).

   **(b) Blender headless path** — fallback when (a) can't handle blend-weight transfer cleanly:
   ```bash
   blender --background --python scripts/mascot/retarget_blender.py -- \
       --source ~/Downloads/mixamo_idle.glb \
       --slot prep_settle \
       --rig tauri/ui/assets/mascot/character.glb
   ```
   `retarget_blender.py` is authored at discharge time too — it imports `bpy`, loads source + rig, runs the standard skeleton-retarget operator, exports the result.
5. **Tune draco** if any clip falls outside the 400 KB – 1200 KB band — the script's stderr names the flag to tune (`--draco.compressionLevel 1..10`; default 7). Lower the level for clips below 400 KB; raise it for clips above 1200 KB.
6. **Run the bundle gate:**
   ```bash
   bash scripts/mascot/check_bundle_size.sh
   ```
   Expected: `PASS: bundle <= 25 MB AND prep_*.glb per-clip 400 KB - 1200 KB`. Exit 0.
7. **Visual sanity check** — the load-bearing aesthetic judgment:
   - Open the running dev build (`npm run dev` in `tauri/ui/`).
   - Trigger each persona (Hype-man / Teacher / Coach) and watch the mascot.
   - On `Celebrate`: confirm it feels like a Pioneer-CDJ headbob, NOT vtuber dance. If any clip feels "AI slop" / "vtuber slop", re-pick the Mixamo source and re-run the retarget for that slot.
   - Specifically reject: jazz hands, body twirl, hip pop, exaggerated weight-shift, full-arm dance.
8. **Commit the retargeted GLBs:**
   ```bash
   git add tauri/ui/assets/mascot/animations/prep_*.glb
   git commit -m "mascot(43-05): VIS-04 real Mixamo retargets (5 clips, Neon Rebel rig)"
   ```

### Verification

```bash
# Bundle gate (both tiers green):
bash scripts/mascot/check_bundle_size.sh

# Per-clip inventory (5 files, each 400 KB – 1200 KB):
ls -lh tauri/ui/assets/mascot/animations/prep_*.glb

# Plan 43-05 pytest suite (engineering tests must still pass post-swap):
uv run pytest tests/mascot/ -q

# Existing mascot Vitest specs (TS-side idle-zero contract, additive layer):
cd tauri/ui && npx vitest run src/mascot --reporter=min
```

### What unblocks

- **VIS-05** mood pool runtime validation (Plan 43-06) — running against real retargets instead of placeholders gives the 30 s persona smoke its actual ship-quality signal.
- **v3.0 ship-cut gate** (Phase 45) — the visual ship lock cannot pass with placeholder GLBs in the bundle.
- **Hero demo capture** (Phase 43-08/09 + Francesco-discharge) — the mascot's celebrate moment in the storyboard's cut 7 needs the real Pioneer-CDJ-headbob clip to read on camera.

### Sign-off block

```
VIS-04 MIXAMO LOGIN on:        _____________________   (date)
VIS-04 CLIPS DOWNLOADED:        _____________________   (count / 5)
VIS-04 RETARGETS RUN:           _____________________   (count / 5)
VIS-04 BUNDLE SIZE (post-run):  _____________________   (MB; target ≤ 25)
VIS-04 PER-CLIP BAND HELD:      _____________________   (yes / no — all 5 in 400 KB - 1200 KB)
VIS-04 CDJ-HEADBOB FEEL OK:     _____________________   (yes / no — Kaan ear/eye judgment)
check_bundle_size.sh exit 0:    _____________________   (yes / no)
Sign-off by:                    _____________________   (Kaan signature)
```

---

## §VIS-09 — Francesco capture day discharge

**REQ-ID:** VIS-09 (Phase 43-09)
**Owner:** Francesco (capture day) + Kaan (verification of footage + aesthetic sign-off)
**Status:** ☐ pre-discharge (Plan 43-09 ships handoff package + demo-mode sequencer)  ☐ pre-production review with Francesco  ☐ capture day complete  ☐ footage reviewed by Kaan  ☐ final cut signed off
**Effort:** ~1 day pre-production review + ~1 day shoot + ~2 days edit
**Blocking for:** Phase 44 (Launch Pre-stage) README hero artefact (the `demo.mp4` referenced from the README) + Phase 45 (External Discharge) social-publish demo video.

### Why this is Francesco-discharge

vibemix is a real-world product — the hero demo requires real DJ hands on a real Pioneer DDJ-FLX4, in a real room with real lighting. None of this can be automated. Francesco owns capture day as cofounder per CONTEXT — engineering ships the deterministic playback environment (demo-mode sequencer + storyboard + shot list + audio capture plan); Francesco brings the booth, the cameras, and the DJ ear.

Per CONTEXT specifics: *"Mascot in cut 7 should feel like a Pioneer CDJ headbob, NOT a generic VTuber dance"* — that aesthetic gate closes on qualitative judgment, not on engineering output. Kaan + Francesco sign off jointly post-shoot.

### Files involved

- **Shot list:** [`docs/launch-prep/SHOT-LIST.md`](docs/launch-prep/SHOT-LIST.md) (Plan 43-09 Task 2)
- **Audio capture plan:** [`docs/launch-prep/AUDIO-CAPTURE.md`](docs/launch-prep/AUDIO-CAPTURE.md) (Plan 43-09 Task 2)
- **Demo-mode config:** [`docs/launch-prep/DEMO-MODE-CONFIG.md`](docs/launch-prep/DEMO-MODE-CONFIG.md) (Plan 43-09 Task 2)
- **Handoff index:** [`docs/launch-prep/README.md`](docs/launch-prep/README.md) (Plan 43-09 Task 2)
- **Demo-mode sequencer:** [`src/vibemix/runtime/demo_mode.py`](src/vibemix/runtime/demo_mode.py) (Plan 43-09 Task 1) — 30-event deterministic sequence; anchors at 2:33 kick_swap / 4:50 layer_drop / 6:00 track_end.
- **Demo-mode pytest pins:** [`tests/runtime/test_demo_mode_sequence.py`](tests/runtime/test_demo_mode_sequence.py) (Plan 43-09 Task 1) — 10/10 pins green guarantees the sequence is bit-identical across takes.
- **Storyboard mock (8 cuts):** [`mocks/vibemix-cinematic-storyboard.html`](mocks/vibemix-cinematic-storyboard.html) (Plan 43-08)
- **Cut count gate:** [`scripts/launch/check_cut_count.py`](scripts/launch/check_cut_count.py)
- **Visual baseline (CDJ Whisper locked):** [`mocks/vibemix-direction-final.html`](mocks/vibemix-direction-final.html)
- **Output location:** `docs/launch-prep/takes/take_NN/` (gitignored; final master `demo.mp4` referenced from the Phase 44 README hero).

### Francesco steps

1. **Pre-production review (1 day before shoot, with Kaan):**
   - Walk the shot list ([`SHOT-LIST.md`](docs/launch-prep/SHOT-LIST.md)) end-to-end; confirm cut sequence + B-roll feasibility against the booth.
   - Confirm the 3-track audio capture chain ([`AUDIO-CAPTURE.md`](docs/launch-prep/AUDIO-CAPTURE.md)) — line-out from headphone amp for Gemini voice; off-axis room mic; Y-cable on headphone monitor.
   - Test-run vibemix demo-mode locally: `vibemix --demo-mode start` plays the 30-event sequence end-to-end. Confirm the mascot reacts at 2:33 (kick_swap → celebrate) and 4:50 (layer_drop → teacher line).

2. **Capture day prep:**
   - Set up booth with Pioneer DDJ-FLX4 + headphones + ambient mic + cameras (1080p+ 60fps+).
   - Mount the vibemix demo-mode display visible to camera 1 (screen-cap or external monitor).
   - Stage the clapboard (visual + audio slate; single source).

3. **Per take:**
   - `vibemix --demo-mode reset` before each take — cursor back to step 0.
   - Slate (clapboard) for sync. Visible on all cameras + audible on all 3 audio tracks.
   - Roll all recorders (3 audio tracks + cameras + vibemix's own session.wav auto-captures when demo-mode starts).
   - Run `vibemix --demo-mode start`; the deterministic 30-event sequence plays across 6:00.
   - Capture the planned cuts during playback; cut 1 + cut 7 are real-world camera angles, cuts 2-6 + 8 are screen-cap (composited in post).
   - End take; review playback; confirm clapboard transient is present at the head of all 4 audio sources; copy `session.wav` into the take folder.

4. **Pickup B-roll:**
   - Cut 1 (DJ hands on FLX4 in dim room) — separate camera setup; ≥ 5 angles.
   - Cut 7 (mascot celebrate full-frame) — screen-cap during demo-mode (mascot animation fires at the 2:33 kick_swap anchor).

5. **Edit:**
   - Sync the 4 audio sources via clapboard transient (3 mics + vibemix `session.wav`).
   - Cut to 8 cuts per the [`SHOT-LIST.md`](docs/launch-prep/SHOT-LIST.md) timing budget (~30s total runtime).
   - Final master at 1080p+ / 60fps+ / 48kHz; export `demo.mp4` for the Phase 44 README hero.

### Verification

```bash
# Pre-shoot: demo-mode sequencer integrity (RED-fail if anchors moved):
uv run pytest tests/runtime/test_demo_mode_sequence.py -q

# Pre-shoot: shot list ↔ storyboard cut count parity:
uv run python scripts/launch/check_cut_count.py    # exit 0 (== 8 cuts)
grep -cE "^\| [1-8] \|" docs/launch-prep/SHOT-LIST.md   # 8

# Pre-shoot: handoff docs are all in place:
test -f docs/launch-prep/SHOT-LIST.md
test -f docs/launch-prep/AUDIO-CAPTURE.md
test -f docs/launch-prep/DEMO-MODE-CONFIG.md
test -f docs/launch-prep/README.md

# Post-shoot: footage spec check (Kaan reviews):
ffprobe take_01_master.mp4 2>&1 | grep -E "1920x1080|3840x2160|fps=60|48000 Hz"

# Post-shoot: no regression in the broader runtime suite:
uv run pytest tests/runtime/ -q
```

### What unblocks

- **Phase 44 README hero artefact** — the `demo.mp4` referenced in the launch-pre-stage README is the output of this capture day.
- **Phase 45 external discharge** — Instagram / Twitter / TikTok cuts derive from the master.
- **`gsd-autonomous fully` ship gate** — Kaan's anti-slop quality bar (per CLAUDE.md `Quality bar` constraint) is satisfied only when the hero demo *reads* like "real DJ friend in your ear", not "voice assistant doing music commentary".

### Sign-off block

```
VIS-09 PRE-PROD REVIEW on:     _____________________   (date — with Kaan + Francesco)
VIS-09 CAPTURE DAY on:          _____________________   (date)
VIS-09 TAKES SHOT:              _____________________   (count)
VIS-09 AV SPEC HELD:            _____________________   (yes / no — 1080p+ / 60fps+ / 48kHz)
VIS-09 PIONEER-HEADBOB FEEL OK: _____________________   (yes / no — Kaan judgment on mascot cut 7)
VIS-09 CDJ WHISPER PALETTE OK:  _____________________   (yes / no — 5 warm blacks + single amber)
VIS-09 FINAL CUT SIGNED:        _____________________   (date)
Sign-off by (Francesco):        _____________________
Sign-off by (Kaan):             _____________________
```

---

## §LAUNCH-07 — SHIP-TWEET 5-channel copy sign-off

**REQ-ID:** LAUNCH-07 (Phase 44-05)
**Owner:** Kaan + Francesco (mutual)
**Status:** ☐ all 5 files engineering-green (`uv run pytest tests/launch/test_no_ai_slop.py`)  ☐ Kaan signature on all 5  ☐ Francesco signature on all 5  ☐ `Locked for: v3.0.0-rc1 launch` tag confirms
**Effort:** ~60 seconds once Francesco responds — fill 5 signature blanks + 5 date blanks + 1 commit
**Blocking for:** Phase 45 SHIP-08 SHIP-TWEET live publish (`scripts/launch/publish_social_posts.py` reads these files at T-0; without mutual sign-off the publish step refuses).

### Why this is KAAN-action

Francesco sign-off is a human-credibility lock — engineering can't fake
Francesco's signature any more than it can fake Kaan's. The grep gate
(`scripts/launch/check_no_ai_slop.py`) catches AI-slop drift + anchor
absence + signature-marker absence, but the SIGNATURE VALUES themselves
(blank `____` placeholders) deliberately stay blank from engineering's
side. Plan 44-05 ships:

- The 5 copy files with the 4-line sign-off footer block at the bottom
- The 16-token AI-slop blocklist + 5 anchor phrases gate
- This runbook

The two-line discharge below is the only thing humans need to do.

### Files involved

- **Copy files (5 channels, in publish order):**
  - `scripts/dayzero/launch_copy/twitter.txt`
  - `scripts/dayzero/launch_copy/instagram.txt`
  - `scripts/dayzero/launch_copy/linkedin.txt`
  - `scripts/dayzero/launch_copy/reddit.txt`
  - `scripts/dayzero/launch_copy/discord.txt`
- **Engineering gate (CI):** `scripts/launch/check_no_ai_slop.py`
  + `tests/launch/test_no_ai_slop.py`
- **Publish step (Phase 45 consumer):** `scripts/launch/publish_social_posts.py`

### Kaan oneliner

```bash
# 1. Read each file end-to-end one last time:
for f in scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit,discord}.txt; do
    echo "=== $f ==="; cat "$f"; echo
done

# 2. Open each file, sign the two blanks (Kaan + Francesco) with date:
#    BEFORE:  Kaan signature:     ____  (date: ____)
#    AFTER:   Kaan signature:     Kaan Özkan  (date: 2026-MM-DD)
#    BEFORE:  Francesco signature: ____  (date: ____)
#    AFTER:   Francesco signature: Francesco <surname>  (date: 2026-MM-DD)
#    (Francesco's reply email / DM is the audit trail — paste his name
#     and the date he replied; the grep gate doesn't validate the
#     signature VALUES, just that the marker lines stay present.)

# 3. Verify engineering gate still green AFTER signing:
uv run pytest tests/launch/test_no_ai_slop.py -v
uv run python scripts/launch/check_no_ai_slop.py

# 4. Commit the lock:
git add scripts/dayzero/launch_copy/*.txt
git commit -m "lock(launch): SHIP-TWEET 5-channel copy locked v3.0.0-rc1"
```

### Verification

```bash
# Engineering gate must stay green AFTER signatures land
# (signatures replace placeholders; markers stay):
uv run pytest tests/launch/test_no_ai_slop.py -v

# Each of the 5 files must carry both signature markers (post-signing
# the placeholders are gone but the marker LINES persist):
grep -l "Kaan signature:" scripts/dayzero/launch_copy/*.txt | wc -l
# → expected: 5

grep -l "Francesco signature:" scripts/dayzero/launch_copy/*.txt | wc -l
# → expected: 5

# Each file must still tag the locked version:
grep -c "Locked for: v3.0.0-rc1 launch" scripts/dayzero/launch_copy/*.txt
# → expected: each file = 1
```

### What unblocks

- **Phase 45 SHIP-08 SHIP-TWEET live publish** —
  `scripts/launch/publish_social_posts.py --really` reads these 5
  files at T-0 (per the LAUNCH-SEQUENCE doc) and posts to twitter /
  instagram / linkedin / reddit / discord. Without the mutual lock,
  the publish step gates closed.
- **§ROADMAP Phase 44 success criterion 5** —
  "SHIP-TWEET copy files signed off (Kaan + Francesco mutual approval)
  for all 5 channels (twitter/instagram/linkedin/reddit/discord)."
  Engineering has shipped all 5 + the gate + this runbook; the
  mutual-sign discharge closes the row.

### Sign-off block

```
LAUNCH-07 ENGINEERING GREEN on:    _____________________   (date — pytest + check script both green)
LAUNCH-07 KAAN READ-THROUGH on:    _____________________   (date — Kaan re-read all 5 end-to-end)
LAUNCH-07 FRANCESCO REPLY on:      _____________________   (date — Francesco's "OK to ship" email/DM)
LAUNCH-07 SIGNATURES COMMITTED:    _____________________   (yes / no — `lock(launch): ...` commit hash)
LAUNCH-07 LOCKED VERSION TAG:      _____________________   (v3.0.0-rc1 expected)
Sign-off by (Kaan):                _____________________
Sign-off by (Francesco):           _____________________
```

---

## §LAUNCH-03 — DJ-software real logo upload

**REQ-ID:** LAUNCH-03 (Phase 44-02)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 44-02 shipped 6 wordmark SVG placeholders + a11y gate)  ☐ 6 real logos sourced trademark-compliant  ☐ 6 files dropped into `docs/assets/dj-software/`  ☐ `<img src>` references in README confirmed (no rename needed if filenames preserved)  ☐ a11y gate stays green
**Effort:** ~20 minutes once logos sourced (download + optimize + drop)
**Blocking for:** Public launch polish — placeholders are functional but Bravoh's first OSS surface deserves real brand logos before the SHIP-TWEET cross-post fires.

### Why this is KAAN-action

Sourcing trademark-compliant DJ-software logos requires human judgement
on which press-kit / brand-guidelines page to lift from for each app
(rekordbox via Pioneer/AlphaTheta press kit, Serato via Serato Press
Hub, Traktor via Native Instruments brand portal, djay Pro via Algoriddim
press assets, VirtualDJ via Atomix brand page, Mixxx via the OSS project
repo — Apache 2.0 already-compatible with vibemix). Each vendor has
different attribution rules; an autonomous agent can't make that legal
call. Plan 44-02 ships:

- 6 SVG wordmark placeholders under `docs/assets/dj-software/<slug>.svg`
  (rekordbox / serato / traktor / djay-pro / virtualdj / mixxx)
- `scripts/launch/check_readme_grids_a11y.py` 4-gate CI enforcement
  (alt-text + cell count + balance + slop-free) so a real-logo swap
  can't accidentally break the README structure
- This runbook

The discharge is purely asset swap — no code touched.

### Files involved

- **Placeholders (6, to be replaced):**
  - `docs/assets/dj-software/rekordbox.svg`
  - `docs/assets/dj-software/serato.svg`
  - `docs/assets/dj-software/traktor.svg`
  - `docs/assets/dj-software/djay-pro.svg`
  - `docs/assets/dj-software/virtualdj.svg`
  - `docs/assets/dj-software/mixxx.svg`
- **README reference (no edit needed if filenames preserved):** `README.md` "## Works alongside whatever DJ app you already use" section.
- **CI gate (stays in place):** `scripts/launch/check_readme_grids_a11y.py` + `tests/launch/test_readme_grids_a11y.py`.

### Kaan oneliner

```bash
# 1. Source each logo from the vendor's press / brand portal:
#    - rekordbox      → https://rekordbox.com (Pioneer/AlphaTheta press kit)
#    - Serato         → https://serato.com/press
#    - Traktor        → https://www.native-instruments.com/brand
#    - djay Pro       → https://www.algoriddim.com/press
#    - VirtualDJ      → https://www.virtualdj.com (Atomix brand page)
#    - Mixxx          → https://github.com/mixxxdj/mixxx (Apache 2.0 — vendored logo OK)

# 2. Optimize to <=10KB SVG (preferred) or PNG at 200x80px transparent bg.
#    SVG via `svgo`; PNG via `pngquant --quality 65-80`.

# 3. Drop each file at the same path with the same slug filename
#    (so the README <img src> URLs don't need editing):
#      docs/assets/dj-software/rekordbox.svg
#      docs/assets/dj-software/serato.svg
#      ... (six total)

# 4. Re-run the a11y gate to confirm nothing broke:
uv run pytest tests/launch/test_readme_grids_a11y.py -v
uv run python scripts/launch/check_readme_grids_a11y.py

# 5. Commit:
git add docs/assets/dj-software/*.svg docs/assets/dj-software/*.png
git commit -m "assets(launch): swap DJ-software placeholders for real trademark-compliant logos (LAUNCH-03)"
```

### Verification

```bash
# Six files still present under the same slug path (PNG accepted instead of SVG):
ls docs/assets/dj-software/{rekordbox,serato,traktor,djay-pro,virtualdj,mixxx}.* | wc -l
# → expected: 6

# README references still resolve (no broken <img src>):
grep -E 'src="docs/assets/dj-software/' README.md | wc -l
# → expected: 6

# a11y gate still green after swap:
uv run pytest tests/launch/test_readme_grids_a11y.py -v

# Each new asset is reasonably small (under 50KB — sanity check):
for f in docs/assets/dj-software/*.{svg,png}; do
    [ -f "$f" ] && wc -c < "$f" | awk -v f="$f" '$1 > 51200 {print "OVERSIZED:", f, $1, "bytes"}'
done
```

### What unblocks

- **§ROADMAP Phase 44 success criterion 3 polish layer** —
  "DJ-software grid + controllers grid render in README; alt-text +
  accessibility checks pass." Engineering closed the gate; real-logo
  swap closes the brand-polish row.
- **SHIP-TWEET visual surface** — the "Works alongside whatever DJ app
  you already use" section is one of the screenshots Francesco's
  twitter / IG / linkedin posts reference. Real logos here = real
  credibility in the cross-post hero shot.

### Sign-off block

```
LAUNCH-03 ENGINEERING GREEN on:    _____________________   (date — placeholders + a11y gate both shipped 44-02)
LAUNCH-03 LOGOS SOURCED on:        _____________________   (date — 6 trademark-compliant assets downloaded)
LAUNCH-03 OPTIMIZE PASS on:        _____________________   (date — svgo / pngquant run)
LAUNCH-03 ASSETS COMMITTED:        _____________________   (yes / no — assets(launch) commit hash)
LAUNCH-03 a11y GATE GREEN POST:    _____________________   (yes / no — re-run after swap)
Sign-off by (Kaan):                _____________________
```

---

## §LAUNCH-04 — Controller real logo upload

**REQ-ID:** LAUNCH-04 (Phase 44-02)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 44-02 shipped 10 wordmark SVG placeholders + a11y gate + canonical-10 reconciliation against `src/vibemix/midi/controllers/*.json`)  ☐ 10 real controller product shots sourced (vendor press kits)  ☐ 10 files dropped into `docs/assets/controllers/`  ☐ `<img src>` references in README confirmed  ☐ a11y gate stays green
**Effort:** ~30 minutes once vendor press-kit access lined up (download + crop + optimize)
**Blocking for:** Public launch polish — same asset-swap pattern as §LAUNCH-03; placeholders are functional but real product photography raises "this works with my controller" credibility.

### Why this is KAAN-action

Controller product photography sourcing is identical to the §LAUNCH-03
problem at higher volume (10 vs 6), and requires vendor-press-kit
account access (Pioneer/AlphaTheta DJ portal, Native Instruments brand
portal, Denon DJ press kit, Numark press kit) plus the same per-vendor
trademark-attribution judgement. The 44-02 legacy-table reconciliation
already closed the harder problem (drift between README controllers
list and `src/vibemix/midi/controllers/*.json`); this discharge is
purely the visual polish layer.

Note: prior to Plan 44-02 the README's "Supported controllers" table
referenced PNGs at `docs/assets/controllers/pioneer_ddj_*.png` for
controllers that were never mapped (FLX6/FLX10/1000/SX3/XDJ-RX3, etc.)
— those PNGs never existed (only `.gitkeep` was ever committed). Plan
44-02 closed the drift by replacing the legacy table with the canonical
10 controllers from the JSON profile set, each with a placeholder SVG
under the canonical slug filename. So this discharge has a clean
ground state to swap against.

### Files involved

- **Placeholders (10, to be replaced):**
  - `docs/assets/controllers/ddj-200.svg`
  - `docs/assets/controllers/ddj-400.svg`
  - `docs/assets/controllers/ddj-flx4.svg`
  - `docs/assets/controllers/ddj-rev1.svg`
  - `docs/assets/controllers/kontrol-s2.svg`
  - `docs/assets/controllers/kontrol-s4.svg`
  - `docs/assets/controllers/mc-6000.svg`
  - `docs/assets/controllers/mc-7000.svg`
  - `docs/assets/controllers/mixtrack-platinum-fx.svg`
  - `docs/assets/controllers/mixtrack-pro-fx.svg`
- **Source of truth (do NOT edit during asset swap):** `src/vibemix/midi/controllers/*.json` — the 10 canonical profiles. Adding / removing a controller here requires a planner decision + README grid update + new placeholder/asset, NOT a "while I'm here" tweak during this discharge.
- **README reference (no edit needed if filenames preserved):** `README.md` "## Supported controllers" section.
- **CI gate (stays in place):** `scripts/launch/check_readme_grids_a11y.py` + `tests/launch/test_readme_grids_a11y.py` (the controllers-grid half of the same gate that enforces §LAUNCH-03).

### Kaan oneliner

```bash
# 1. Source each product shot from the vendor's press kit:
#    - Pioneer DDJ-200 / DDJ-400 / DDJ-FLX4 / DDJ-REV1 → Pioneer/AlphaTheta DJ press portal
#    - NI Traktor Kontrol S2 / S4                       → Native Instruments brand portal
#    - Denon DJ MC6000 / MC7000                         → Denon DJ press kit
#    - Numark Mixtrack Platinum FX / Pro FX             → Numark press kit

# 2. Crop to a consistent aspect ratio (top-down product shot preferred for grid uniformity);
#    optimize to PNG <=80KB at 360x180 source (200px display width is README-render-size).
#    Use `pngquant --quality 70-85` for size, `oxipng -o4` for final lossless pass.

# 3. Drop each file at the same slug path. SVG OR PNG both legal —
#    if swapping to PNG, also delete the .svg placeholder + update the
#    README <img src> extension (one Edit per cell, 10 cells total):
#      docs/assets/controllers/ddj-200.png       (replaces ddj-200.svg)
#      docs/assets/controllers/ddj-400.png
#      ... (ten total)

# 4. Re-run the a11y gate:
uv run pytest tests/launch/test_readme_grids_a11y.py -v
uv run python scripts/launch/check_readme_grids_a11y.py

# 5. Commit:
git add docs/assets/controllers/*.{svg,png} README.md
git commit -m "assets(launch): swap controller placeholders for real product photography (LAUNCH-04)"
```

### Verification

```bash
# Ten files still present under the canonical slug paths:
for slug in ddj-200 ddj-400 ddj-flx4 ddj-rev1 kontrol-s2 kontrol-s4 mc-6000 mc-7000 mixtrack-platinum-fx mixtrack-pro-fx; do
    ls docs/assets/controllers/${slug}.* 2>/dev/null | head -1
done | wc -l
# → expected: 10

# README references still resolve (no broken <img src>):
grep -E 'src="docs/assets/controllers/' README.md | wc -l
# → expected: 10

# Canonical 10 still matches src-of-truth:
ls src/vibemix/midi/controllers/*.json | wc -l
# → expected: 10  (same count as README grid)

# a11y gate still green:
uv run pytest tests/launch/test_readme_grids_a11y.py -v
```

### What unblocks

- **§ROADMAP Phase 44 success criterion 3 polish layer (same as §LAUNCH-03)** —
  the "controllers grid renders" row is engineering-green already;
  real-photo swap closes the visual-credibility layer.
- **Outreach calendar credibility** — DJ TechTools / DDJ Tips / Mixmag
  editorial pitches reference vibemix's controller support breadth as
  the news hook ("10 mapped controllers out of the box, generic-MIDI
  fallback for everything else"). Real product shots in the
  "Supported controllers" grid let those editors lift the screenshot
  for their post without falling back to a placeholder.

### Sign-off block

```
LAUNCH-04 ENGINEERING GREEN on:    _____________________   (date — 10 placeholders + a11y gate + canonical-10 reconciliation shipped 44-02)
LAUNCH-04 ASSETS SOURCED on:       _____________________   (date — 10 product shots downloaded from vendor press kits)
LAUNCH-04 CROP + OPTIMIZE on:      _____________________   (date — pngquant / oxipng run)
LAUNCH-04 ASSETS COMMITTED:        _____________________   (yes / no — assets(launch) commit hash)
LAUNCH-04 a11y GATE GREEN POST:    _____________________   (yes / no — re-run after swap)
Sign-off by (Kaan):                _____________________
```

---

## §LAUNCH-06 — Bravoh GH org standup

**REQ-ID:** LAUNCH-06 (Phase 44-06)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 44-06 shipped polling gate + this runbook)  ☐ Bravoh Enterprise billing flag resolved  ☐ `bravoh` org created on github.com  ☐ Kaan + Francesco invited as owners  ☐ `bash scripts/launch/check_bravoh_org_ready.sh` exit 0
**Effort:** ~10 minutes once Bravoh Enterprise billing flag clears (the billing-flag resolution itself can take 1–3 business days on first-time GH Enterprise org creation — start early)
**Blocking for:** Phase 45 SHIP-TRANSFER (`gh repo transfer ozai/dj-set-ai bravoh/vibemix`) + the `bravoh/vibemix` URLs that the README install instructions, the SHIP-TWEET copy, and every onboarding doc reference become live destinations instead of 404s.

### Why this is KAAN-action

`gh org create` requires a session with org-create scope against
Kaan's GH account + the Bravoh Enterprise billing context. Autonomous
agents NEVER hold GH tokens with `admin:org` or `write:org` scope (see
the broader privacy-rule discipline in CLAUDE.md). The Bravoh
Enterprise billing flag is a one-time admin-panel resolution that
requires Kaan's Bravoh-billing login — the engineering agent has no
path to that surface.

Plan 44-06 ships the pre-stage:

- `scripts/launch/check_bravoh_org_ready.sh` — polls
  `https://api.github.com/orgs/bravoh` and exits 0 once the org
  exists (gh-first, curl fallback; the public-org existence check is
  unauth-readable so Plan 45 SHIP-TRANSFER consumers don't need GH
  tokens just to verify the gate).
- This runbook.

The 4-line discharge below is the only thing Kaan needs to do.

### Files involved

- **Polling gate (engineering):** `scripts/launch/check_bravoh_org_ready.sh`
  + `tests/launch/test_check_bravoh_org_ready.py` (Plan 44-06).
- **Plan 45 consumer:** `scripts/launch/ship_transfer.sh` (or
  equivalent — Plan 45 ships the actual `gh repo transfer` call;
  this runbook is its upstream gate).
- **External references that flip from 404 to live after this
  discharge:**
  - `README.md` install URLs (Plan 44-01 hero block + 44-02 grid
    sections reference `github.com/bravoh/vibemix/releases`)
  - `scripts/dayzero/launch_copy/*.txt` (Plan 44-05 SHIP-TWEET copy
    references the same)
  - `docs/launch-prep/LAUNCH-SEQUENCE.md` T-0 row (Plan 44-07)

### Kaan oneliner

```bash
# 1. Resolve Bravoh Enterprise billing flag (one-time, ~1–3 business days
#    if first-time GH Enterprise org). Surface: github.com/enterprises/bravoh
#    → Billing & licensing → resolve any outstanding flags. If Bravoh has
#    no Enterprise account yet, this collapses to "create a free GH org"
#    on Kaan's personal account, which is fine for the open-source
#    vibemix repo (Bravoh-paid Enterprise can adopt later).
#    Cross-ref: `signpath-application.md` for the broader Bravoh-credentials
#    context (same billing surface).

# 2. Create the org (KAAN-VERIFY: exact GH org-create endpoint depends on
#    Bravoh's GH plan tier — Enterprise admins use the admin panel UI,
#    free-tier creates via UI at github.com/account/organizations/new):
#    Free-tier UI path:
#      → https://github.com/account/organizations/new
#      → name: bravoh, contact email: kaan@bravoh.com, plan: free
#    Enterprise CLI path (if applicable):
#      gh api -X POST /admin/organizations \
#          -f login=bravoh -f admin=kaanozk -f profile_name='Bravoh'

# 3. Invite Kaan + Francesco as owners:
gh api -X PUT "orgs/bravoh/memberships/kaanozk"     -f role=admin
gh api -X PUT "orgs/bravoh/memberships/francescotural" -f role=admin

# 4. Verify the gate flips:
bash scripts/launch/check_bravoh_org_ready.sh
# → expected: "OK: org 'bravoh' exists on github.com"; exit 0
```

### Verification

```bash
# Gate script must return exit 0:
bash scripts/launch/check_bravoh_org_ready.sh && echo "LAUNCH-06 GATE GREEN"

# Polling test suite (offline invariants) must stay green:
uv run pytest tests/launch/test_check_bravoh_org_ready.py -v -m "not network"

# Live network smokes (opt-in; require internet):
uv run pytest tests/launch/test_check_bravoh_org_ready.py -v -m network

# Manual: org owners include both Kaan and Francesco:
gh api orgs/bravoh/members --jq '.[].login' | sort
# → expected: kaanozk, francescotural (at minimum)
```

### What unblocks

- **Phase 45 SHIP-TRANSFER** — the canonical
  `gh repo transfer ozai/dj-set-ai bravoh/vibemix` call. Plan 45
  ships the transfer script + the watch-for-redirect-stability gate
  + the post-transfer `git remote set-url` for Kaan's local clones;
  none of those can run before this org exists.
- **README install URLs go live** — Plan 44-01's hero block already
  references `github.com/bravoh/vibemix/releases/latest/download/...`
  for the Mac DMG + Windows MSI. Those URLs 404 today; they become
  live download targets the moment Plan 45 SHIP-TRANSFER lands the
  repo into `bravoh/vibemix` AND the v3.0.0-rc1 release ships.
- **§ROADMAP Phase 44 success criterion 4** —
  "`bravoh` GitHub org exists (engineering ships readiness check +
  runbook; org creation = Kaan-discharge)." Engineering side is
  green via this plan; the org-creation discharge closes the row.

### Sign-off block

```
LAUNCH-06 ENGINEERING GREEN on:    _____________________   (date — Plan 44-06 polling gate + runbook shipped)
LAUNCH-06 BILLING FLAG RESOLVED:   _____________________   (date — Bravoh Enterprise billing flag cleared)
LAUNCH-06 ORG CREATED on:          _____________________   (date — `bravoh` org exists at github.com/bravoh)
LAUNCH-06 OWNERS INVITED:          _____________________   (yes / no — Kaan + Francesco both org admins)
LAUNCH-06 GATE GREEN (rc=0):       _____________________   (date — `bash scripts/launch/check_bravoh_org_ready.sh` exits 0)
Sign-off by (Kaan):                _____________________
```

---

## §LAUNCH-08 — Discord live-execution discharge

**REQ-ID:** LAUNCH-08 (Phase 44-06)
**Owner:** Kaan
**Status:** ☐ pre-discharge (Plan 44-06 locked taxonomy + dry-run zero-network + this runbook)  ☐ Bravoh-vibemix Discord guild created  ☐ `BRAVOH_DISCORD_BOT_TOKEN` sourced from Bravoh Discord Developer Portal  ☐ GH secret `BRAVOH_DISCORD_BOT_TOKEN` set  ☐ dry-run green against real guild ID  ☐ `--live` execution complete (5 roles + 9 channels created)
**Effort:** ~15 minutes (guild create + token source + dry-run + live execute)
**Blocking for:** Phase 45 SHIP-DISCORD (#announcements launch post via `scripts/launch/post_discord_launch.py`) + the broader community surface that every onboarding doc + LAUNCH-SEQUENCE T-0 row references.

### Why this is KAAN-action

Bot-token sourcing requires the Bravoh Discord admin seat — only
Kaan holds that. Live `--live` execution against a real Discord guild
requires the token in environment + the guild ID. Per the privacy +
secrets discipline (CLAUDE.md), autonomous agents NEVER hold a real
Discord bot token (the dry-run path is built specifically so the
engineering surface ships without ever needing one).

Plan 44-06 ships:

- `scripts/dayzero/discord_taxonomy.json` — single source of truth
  for the 5 roles + 9 channels merged canonical set (the merge
  resolution is embedded in the JSON's `_merge_resolution` field).
- `scripts/dayzero/discord_provision.py` — refactored to read the
  taxonomy JSON at module load; defaults to dry-run; supports both
  `BRAVOH_DISCORD_BOT_TOKEN` (preferred) and `DISCORD_BOT_TOKEN`
  (legacy) env vars; logs `[live] bot token source: <ENV_NAME>` for
  audit (never logs the token value).
- `tests/dayzero/test_discord_provision_dryrun.py` — pins
  taxonomy.json contract + dry-run zero-network + dry-run zero-SDK
  + token-preference behavior.
- This runbook.

The 5-step discharge below is the only thing Kaan needs to do.

### Files involved

- **Taxonomy lock:** `scripts/dayzero/discord_taxonomy.json` (Plan 44-06).
- **Provision script:** `scripts/dayzero/discord_provision.py` (Plan 44-06).
- **Dry-run + token-preference gate:**
  `tests/dayzero/test_discord_provision_dryrun.py` (Plan 44-06).
- **Legacy idempotency + diff gate:**
  `tests/dayzero/test_discord_provision.py` (Phase 36 baseline,
  taxonomy updated in 44-06).
- **Phase 45 consumer:** `scripts/launch/post_discord_launch.py`
  (Phase 45 SHIP-DISCORD).

### Kaan oneliner

```bash
# 1. Create the Bravoh-vibemix Discord guild
#    → Bravoh Discord admin panel → New Server
#    → name: vibemix, region: closest to Bravoh team
#    → grab the numeric guild ID (right-click server icon → Copy Server ID
#       requires Developer Mode enabled in Discord settings)

# 2. Source the bot token
#    → https://discord.com/developers/applications → New Application
#    → name: vibemix-bot, owner: Bravoh team
#    → Bot tab → Add Bot → Reset Token → copy
#    → OAuth2 → URL Generator → scopes: bot
#    → Bot permissions: Manage Roles + Manage Channels (minimum
#       required for the provision script's create_role +
#       create_text_channel calls)
#    → Visit the generated URL → invite the bot into the vibemix guild

export BRAVOH_DISCORD_BOT_TOKEN='<paste-token-here>'

# 3. Persist into GH secret (Plan 45 SHIP-DISCORD reads this in CI):
gh secret set BRAVOH_DISCORD_BOT_TOKEN --body "$BRAVOH_DISCORD_BOT_TOKEN"

# 4. Dry-run verify (no API call; pins taxonomy + plan):
uv run python scripts/dayzero/discord_provision.py
# → expected: prints 5 roles + 9 channels + "DRY-RUN complete"

# 5. Live execute against the real guild:
uv run python scripts/dayzero/discord_provision.py \
    --live --guild-id <numeric-guild-id>
# → expected: prints "[live] bot token source: BRAVOH_DISCORD_BOT_TOKEN"
#   then "[done] created role <X>" × 5 and "[done] created channel #<Y>" × 9
#   (idempotent: re-running prints "[skip] role exists" / "[skip] channel exists")
```

### Verification

```bash
# Engineering gates must stay green AFTER the live run:
uv run pytest tests/dayzero/test_discord_provision_dryrun.py -v
uv run pytest tests/dayzero/test_discord_provision.py -v

# Manual guild inspection — open the Discord server and confirm:
#   Roles tab → founder, contributor, DJ, lurker, moderator (5)
#   Channels list → announcements, general, help, show-and-tell,
#                   controllers, ai-misbehavior, dev, bugs, showcase (9)

# Idempotency smoke — re-run --live and confirm zero new entries:
uv run python scripts/dayzero/discord_provision.py \
    --live --guild-id <numeric-guild-id> | grep -c "^\[skip\]"
# → expected: 14 (5 roles + 9 channels all skipped)

# Token-source audit — confirm BRAVOH var was the source:
uv run python scripts/dayzero/discord_provision.py \
    --live --guild-id <numeric-guild-id> 2>&1 | \
    grep "bot token source"
# → expected: "[live] bot token source: BRAVOH_DISCORD_BOT_TOKEN"
```

### What unblocks

- **Phase 45 SHIP-DISCORD** — the canonical #announcements launch
  post via `scripts/launch/post_discord_launch.py --really`. That
  script reads `BRAVOH_DISCORD_BOT_TOKEN` from GH secrets at T-0 and
  posts the v3.0.0-rc1 launch announcement; without the provisioned
  guild + secret, the publish step gates closed.
- **Community surface goes live** — onboarding docs, README community
  section, LAUNCH-SEQUENCE T-3 DJ TechTools Discord cross-pollination
  + T-0 announcement post all reference a real Discord invite. That
  invite only works once the guild exists + the bot is in.
- **§ROADMAP Phase 44 success criterion 6** —
  "Discord provision dry-run completes without errors (live execution
  = Kaan-discharge)." Engineering side green via Plan 44-06
  (dry-run pinned + taxonomy locked + zero-network asserted); the
  live-execution discharge closes the row.

### Sign-off block

```
LAUNCH-08 ENGINEERING GREEN on:    _____________________   (date — Plan 44-06 taxonomy + dry-run + token-preference + runbook shipped)
LAUNCH-08 GUILD CREATED on:        _____________________   (date — vibemix Discord server exists; ID recorded)
LAUNCH-08 BOT TOKEN SOURCED on:    _____________________   (date — token in Kaan-local env + GH secret set)
LAUNCH-08 GUILD ID:                _____________________   (numeric — record for Plan 45 SHIP-DISCORD reference)
LAUNCH-08 GH SECRET SET:           _____________________   (yes / no — `gh secret list | grep BRAVOH_DISCORD_BOT_TOKEN`)
LAUNCH-08 DRY-RUN GREEN:           _____________________   (date — `discord_provision.py` dry-run exit 0)
LAUNCH-08 LIVE EXECUTE COMPLETE:   _____________________   (date — 5 roles + 9 channels created, idempotent re-run shows 14 skips)
Sign-off by (Kaan):                _____________________
```

## §SHIP-01 — Apple Developer Program agreement (FRANCESCO-ACTION)

**REQ-ID:** SHIP-01 (Phase 45)
**Owner:** Francesco
**Status:** ☐ pre-discharge  ☐ Apple Developer Program enrollment complete  ☐ paid annual fee posted ($99 USD)  ☐ Team ID captured  ☐ Developer ID Application cert generated  ☐ Developer ID Installer cert generated  ☐ App-specific notarization password generated  ☐ all 3 secrets posted to GH secrets

**Effort:** ~30 minutes web flow + Apple's ~24h account-activation SLA. The activation SLA is the critical path — start this the day Francesco gets the email confirming legal capacity to sign for Bravoh.

**Blocking for:** §SHIP-03 (DIST-19 signed-binary smoke), §SHIP-04 (INSTALL-VM matrix), §SHIP-07 (SHIP-CUT). Without Apple-signed binaries, Mac users hit Gatekeeper and the launch is dead in the water.

### Why this is FRANCESCO-action

Bravoh as a legal entity holds the Apple Developer Program seat. Francesco is the signatory of record for the company — Kaan can't enroll on Bravoh's behalf without Francesco's eyes on the Apple legal agreements. Per CLAUDE.md privacy + secrets discipline, autonomous agents never hold an Apple Developer Program login.

### Pre-requisites

- Bravoh legal entity registered (already true).
- Francesco logged in to https://developer.apple.com with the Bravoh-team Apple ID.
- Bravoh credit card on file for the $99 annual fee.

### Discharge commands

```bash
# 1. Enroll Bravoh as a Developer Program member
#    → https://developer.apple.com/programs/enroll/
#    → entity type: Organization
#    → D-U-N-S number: <Bravoh D-U-N-S>
#    → legal entity name: Bravoh <legal suffix per registration>
#    → pay $99 USD annual fee
#    → wait for Apple's "Welcome to the Apple Developer Program" email
#      (account activation: typically 24h)

# 2. Capture the Team ID (10-char alphanumeric)
#    → developer.apple.com → Account → Membership
#    → copy the Team ID into a secure note

# 3. Generate Developer ID Application cert
#    → Account → Certificates → "+" → Developer ID Application
#    → upload CSR generated locally with:
#      openssl req -new -newkey rsa:2048 -nodes \
#          -keyout vibemix-developer-id-application.key \
#          -out vibemix-developer-id-application.csr \
#          -subj "/CN=Bravoh Developer ID Application/O=Bravoh/C=<country>"
#    → download .cer; import into Keychain Access on Francesco's Mac

# 4. Generate Developer ID Installer cert (for .pkg installers)
#    → same flow, choose "Developer ID Installer" type

# 5. Generate app-specific password for notarization
#    → appleid.apple.com → Sign-In and Security → App-Specific Passwords
#    → label: vibemix-notarization
#    → copy the 16-char password

# 6. Post the 3 GH secrets (run on Kaan's machine via Francesco-shared values):
gh secret set APPLE_DEVELOPER_ID --body "<Team ID>"
gh secret set APPLE_TEAM_ID --body "<Team ID>"
gh secret set APPLE_NOTARIZATION_PASSWORD --body "<app-specific password>"

# Note: actual cert .p12 + private key for signing are posted as:
gh secret set APPLE_CERTIFICATE_P12_BASE64 --body "$(base64 < cert.p12)"
gh secret set APPLE_CERTIFICATE_PASSWORD --body "<p12 export password>"
```

### Verification

```bash
# 1. GH secrets visible:
gh secret list | grep -E "APPLE_(DEVELOPER_ID|TEAM_ID|NOTARIZATION_PASSWORD|CERTIFICATE_P12_BASE64|CERTIFICATE_PASSWORD)"
# → expected: 5 lines

# 2. Developer ID cert visible in Apple Developer account:
#    → developer.apple.com → Account → Certificates → see "Developer ID Application" + "Developer ID Installer" rows

# 3. Notarization smoke (after first signed binary builds in §SHIP-03):
xcrun notarytool history --apple-id <bravoh-apple-id> --team-id $APPLE_TEAM_ID --password $APPLE_NOTARIZATION_PASSWORD
# → expected: lists past notarization attempts (or empty list if first run)
```

### Post-discharge

- Mark `[x] SHIP-01` in REQUIREMENTS.md.
- Record Team ID in `.planning/STATE.md` decisions section.
- Update §SHIP-03 status to ☑ pre-req met.

### Unblocks

- **§SHIP-03** — DIST-19 signed-binary smoke can now run.
- **§SHIP-04** — INSTALL-VM matrix has signed binaries to walk through.
- **§SHIP-07** — SHIP-CUT can attach signed `.dmg` / `.pkg` artifacts.
- **Roadmap Phase 45 success criterion** — "Mac binary signed + notarized" row goes green.

### Sign-off block

```
SHIP-01 ENROLLMENT POSTED on:        _____________________   (date — Francesco hits "enroll" on developer.apple.com)
SHIP-01 ACCOUNT ACTIVATED on:        _____________________   (date — Apple welcome email received)
SHIP-01 TEAM ID:                     _____________________   (10-char alphanumeric)
SHIP-01 DEV-ID APP CERT GEN on:      _____________________   (date)
SHIP-01 DEV-ID INSTALLER CERT GEN:   _____________________   (date)
SHIP-01 NOTARIZATION PW GEN on:      _____________________   (date)
SHIP-01 GH SECRETS POSTED on:        _____________________   (date — 5 secrets visible via `gh secret list`)
Sign-off by (Francesco):             _____________________
Counter-sign by (Kaan):              _____________________
```

## §SHIP-02 — SignPath OSS Foundation approval (KAAN-ACTION)

**REQ-ID:** SHIP-02 (Phase 45)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ SignPath OSS Foundation application submitted  ☐ ~1-week SLA wait  ☐ SignPath signing token issued  ☐ token posted to GH secrets

**Effort:** ~15 minutes form fill + SignPath's ~1-week SLA. Submit the SAME day §SHIP-01 enrollment kicks off so the two external clocks run in parallel.

**Blocking for:** §SHIP-03 (DIST-19 signed-binary smoke on Windows side), §SHIP-04 (INSTALL-VM matrix needs signed `.msi`), §SHIP-07 (SHIP-CUT attaches signed Windows artifacts), §SHIP-12 (INSTALL-DEFENDER SmartScreen reputation can only accrue against a SignPath-signed binary).

### Why this is KAAN-action

SignPath OSS Foundation tier is free for open-source projects but requires per-project approval. Kaan is the GitHub-account holder of `ozzaii/vibemix` (pre-transfer) so the application has to come from his identity. Once approved, the signing token is provisioned to a GitHub Actions workflow — no manual ceremony per release.

### Pre-requisites

- §SHIP-01 not strictly required (these two run in parallel), but recommend submitting on the same day so SignPath SLA + Apple SLA overlap.
- Vibemix repo public (already true).
- README has explicit OSS license badge (Apache-2.0 — already locked Phase 44-01).

### Discharge commands

```bash
# 1. Open the OSS Foundation application
#    → https://signpath.org/foundation
#    → "Apply Now" → fill the form:
#      • Project name: vibemix
#      • Repo URL: https://github.com/ozzaii/vibemix (pre-transfer) or
#                  https://github.com/bravoh/vibemix (post-transfer — both
#                  work; SignPath re-binds on transfer)
#      • License: Apache-2.0
#      • Project description: "AI co-host for live DJ sets — listens to
#         your master output, watches your DJ software's screen, ingests
#         controller actions over MIDI, reacts in your ear. macOS +
#         Windows. Built by DJs."
#      • Lead maintainer: Kaan Özkan (Bravoh founder)
#      • Why OSS-Foundation tier: "Vibemix is Apache-2.0 open source.
#         Windows binary signing is free for OSS via SignPath Foundation."

# 2. Submit + wait
#    → SignPath SLA is ~1 week. Watch inbox for approval email from
#      SignPath team@signpath.io.
#    → If 14 days pass with no reply, escalate via signpath.org/contact.

# 3. Once approved, SignPath provisions an org + a signing policy.
#    → Log in to https://signpath.io/manage/<your-org>
#    → Settings → API Tokens → Generate Token
#    → scope: signing-request:submit + artifact:download
#    → copy the token

# 4. Post to GH secret (CI workflow reads this at every build):
gh secret set SIGNPATH_SIGNING_TOKEN --body "<paste-token-here>"
gh secret set SIGNPATH_ORGANIZATION_ID --body "<org-id-from-signpath-dashboard>"
gh secret set SIGNPATH_PROJECT_SLUG --body "vibemix"
gh secret set SIGNPATH_SIGNING_POLICY_SLUG --body "release-signing"
```

### Verification

```bash
# 1. GH secrets visible:
gh secret list | grep SIGNPATH
# → expected: 4 lines (SIGNING_TOKEN, ORGANIZATION_ID, PROJECT_SLUG, SIGNING_POLICY_SLUG)

# 2. SignPath dashboard shows a project named "vibemix" with status "Active":
#    → https://signpath.io/manage/<your-org>/projects

# 3. Token scope check — confirm the issued token can submit + download:
curl -fsSL -H "Authorization: Bearer $SIGNPATH_SIGNING_TOKEN" \
    "https://app.signpath.io/api/v1/$SIGNPATH_ORGANIZATION_ID/projects" \
    | jq '.[] | select(.slug=="vibemix") | .slug'
# → expected: "vibemix"
```

### Post-discharge

- Mark `[x] SHIP-02` in REQUIREMENTS.md.
- Record approval-email date + token-issue date in `.planning/STATE.md`.
- Update §SHIP-03 status to ☑ pre-req met (combined with §SHIP-01).

### Unblocks

- **§SHIP-03** — Windows side of DIST-19 verification gains a signed .msi to verify.
- **§SHIP-04** — INSTALL-VM matrix walks Windows VMs with a SignPath-signed installer.
- **§SHIP-07** — SHIP-CUT attaches signed `dist/*.msi` / `dist/*.exe` to the release.
- **§SHIP-12** — INSTALL-DEFENDER SmartScreen reputation can begin accruing.

### Sign-off block

```
SHIP-02 APPLICATION SUBMITTED on:    _____________________   (date — form submitted to signpath.org/foundation)
SHIP-02 APPROVAL EMAIL on:           _____________________   (date — SignPath approval email received)
SHIP-02 ORG SLUG:                    _____________________   (signpath.io org identifier)
SHIP-02 PROJECT SLUG:                _____________________   (should be "vibemix")
SHIP-02 SIGNING POLICY SLUG:         _____________________   (e.g. "release-signing")
SHIP-02 TOKEN GENERATED on:          _____________________   (date)
SHIP-02 GH SECRETS POSTED on:        _____________________   (date — 4 secrets visible via `gh secret list`)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-03 — DIST-19 signed-binary smoke (KAAN-ACTION)

**REQ-ID:** SHIP-03 / DIST-19 (Phase 27/34 baseline, Phase 45 discharge)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-01 GREEN  ☐ §SHIP-02 GREEN  ☐ release.yml workflow dispatched  ☐ artifacts downloaded  ☐ verify_signed.py exits 0 on all 4 artifact shapes

**Effort:** ~30 minutes — dispatch the workflow, wait for the runner (~10-15 min Mac + Windows build matrix), download artifacts, run verifier.

**Blocking for:** §SHIP-04 (INSTALL-VM matrix needs verified signed binaries as inputs), §SHIP-07 (SHIP-CUT Gate 5 — `verify_signed.py --require-signed`).

### Why this is KAAN-action

Workflow dispatch is a GH-write action against the repo — Kaan as repo admin holds the only seat that can trigger it without a tag push. The verify step itself is plain CLI but the artifacts must come from the real CI build, not a local build, so the signed-with-real-certs proof carries forward.

### Pre-requisites

- §SHIP-01 GREEN: `gh secret list | grep APPLE_` returns 5 lines.
- §SHIP-02 GREEN: `gh secret list | grep SIGNPATH` returns 4 lines.
- `scripts/dist/verify_signed.py` ships `--require-signed` flag (Phase 27 + 34 — already present).
- `scripts/dist/sign_macos.sh`, `sign_windows.ps1`, `sign_manifest.sh` shipped Phase 34.

### Discharge commands

```bash
# 1. Dispatch the release workflow (builds signed Mac + Win binaries on
#    main HEAD without cutting a release yet):
gh workflow run release.yml --ref main

# 2. Watch the run land + complete:
gh run list --workflow=release.yml --limit 1
# → grab the run ID
gh run watch <run-id>
# → expected: green check across the macos-13 + macos-14 + windows-latest legs

# 3. Download the artifacts to dist/:
mkdir -p dist
gh run download <run-id> --dir dist/
# → expected: dist/{vibemix-*.dmg, vibemix-*.pkg, vibemix-*.msi, vibemix-*.exe}

# 4. Verify each artifact carries a real signature:
for art in dist/*.dmg dist/*.pkg dist/*.msi dist/*.exe; do
  [ -f "$art" ] || continue
  echo "--- verifying $art ---"
  uv run python scripts/dist/verify_signed.py --artifact "$art" --require-signed
done
```

### Verification

```bash
# 1. All 4 artifact shapes present:
ls dist/*.dmg dist/*.pkg dist/*.msi dist/*.exe 2>/dev/null | wc -l
# → expected: 4 (or more if multi-arch Mac)

# 2. Each artifact passes signed verification with NO warnings:
for art in dist/*.dmg dist/*.pkg dist/*.msi dist/*.exe; do
  uv run python scripts/dist/verify_signed.py --artifact "$art" --require-signed \
    && echo "$art: SIGNED OK" || echo "$art: SIGNATURE FAIL"
done
# → expected: 4 × "SIGNED OK"

# 3. Mac notarization stapled:
spctl --assess --type install dist/vibemix-*.dmg 2>&1 | grep "accepted"
# → expected: "accepted, source=Notarized Developer ID"

# 4. Windows signature trust chain:
osslsigncode verify dist/vibemix-*.msi 2>&1 | grep -E "Signature verification: ok"
# → expected: present (uses SignPath chain)
```

### Post-discharge

- Mark `[x] SHIP-03` and `[x] DIST-19` in REQUIREMENTS.md.
- Record the dispatched run ID + artifact SHA-256 hashes in `.planning/STATE.md`.
- Tag the workflow run ID in §SHIP-07 sign-off block as the "last clean signed build" reference.

### Unblocks

- **§SHIP-04** — INSTALL-VM matrix has signed binaries to walk fresh VMs through.
- **§SHIP-07** — SHIP-CUT Gate 5 (`verify_signed.py --require-signed` per `cut_release.sh`) passes.
- **Roadmap success criterion** — "DIST-19 verified against real signed binary" row goes green.

### Sign-off block

```
SHIP-03 WORKFLOW DISPATCHED on:      _____________________   (date — `gh workflow run release.yml`)
SHIP-03 RUN ID:                      _____________________   (gh run identifier)
SHIP-03 BUILD GREEN on:              _____________________   (date — all matrix legs green)
SHIP-03 ARTIFACTS DOWNLOADED on:     _____________________   (date)
SHIP-03 VERIFY_SIGNED PASS:          _____________________   (4 × SIGNED OK)
SHIP-03 NOTARIZATION STAPLED:        _____________________   (yes — spctl accepted)
SHIP-03 SIGNPATH CHAIN OK:           _____________________   (yes — osslsigncode verify ok)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-04 — INSTALL-VM matrix discharge (KAAN-ACTION)

**REQ-ID:** SHIP-04 (Phase 45 / Plan 45-01)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-03 GREEN  ☐ tart images present (macOS 12.3 / 14 / 15 + Win 10 / 11)  ☐ live run captured  ☐ all 5 OS legs green  ☐ 60s gate passes

**Effort:** ~90 minutes total — tart spins each VM, install_vm_matrix.sh drives the wizard, screenshots collect, 60s gate evaluates. Most of the time is VM cold-start across 5 images.

**Blocking for:** §SHIP-05 (INSTALL-60S contract), §SHIP-07 (SHIP-CUT cannot proceed without fresh-VM proof per the one-click-install hard requirement).

### Why this is KAAN-action

`tart` driving VMs requires the Apple Silicon host's local privileges (Virtualization.framework). Live screen capture + wizard-step screenshots persist to `dist/install-vm-runs/<run-id>/` on Kaan's machine. Kaan is the operator of record because the one-click-install bar is his memory rule — anyone else running the matrix can't make the green/red call on whether the experience clears the bar.

### Pre-requisites

- §SHIP-03 GREEN: `dist/*.dmg`, `dist/*.pkg`, `dist/*.msi`, `dist/*.exe` all present + signed.
- `tart list` shows all 5 target VMs (macos-12.3, macos-14, macos-15, win-10, win-11). Missing images SKIP with a warning per `install_vm_matrix.sh` autonomous-degradation rule, but full discharge requires all 5.
- `scripts/dist/install_vm_matrix.json` reflects the OS list to run.
- `scripts/dist/install_vm_matrix.sh` exists (Plan 45-01) and is executable (`chmod +x`).
- The onboarding stopwatch (`tauri/ui/src/wizard/onboarding-stopwatch.ts`) writes to `~/.vibemix/install-vm-timing.json` when the `VIBEMIX_INSTALL_VM_RUN=1` env flag is set inside the VM — verify this is wired before the live run (Phase 33 INSTALL-05 baseline).

### Discharge commands

```bash
# 1. Pre-flight: tart inventory
tart list
# → expected: 5 rows for macos-12.3, macos-14, macos-15, win-10, win-11
# → if any missing, pull them first:
#    tart pull ghcr.io/cirruslabs/macos-sonoma-base:latest
#    (or whichever the matrix JSON references)

# 2. Live discharge — record under a UTC-stamped run-id:
RUN_ID="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
bash scripts/dist/install_vm_matrix.sh --live --run-id "$RUN_ID"

# → For each OS the runner:
#    a. clones the base image
#    b. attaches the freshly-signed binary from dist/
#    c. injects VIBEMIX_INSTALL_VM_RUN=1 so onboarding-stopwatch dumps
#       timing to ~/.vibemix/install-vm-timing.json inside the VM
#    d. drives the wizard (TCC → audio probe → controller probe → ready)
#    e. captures install-vm-<os>-<version>-{wizard-step-1..3,session-live}.png
#       to dist/install-vm-runs/$RUN_ID/
#    f. records timing JSON back to dist/install-vm-runs/$RUN_ID/<os>/

# 3. Inspect outputs:
ls dist/install-vm-runs/$RUN_ID/
# → expected: 5 OS subdirs + run.json index

cat dist/install-vm-runs/$RUN_ID/run.json | jq '.runs[] | {os, status, install_seconds}'
# → expected: 5 entries with status="passed" + install_seconds < 60
```

### Verification

```bash
# 1. 60s gate — gates §SHIP-05:
bash scripts/dist/install_vm_matrix.sh --check-60s
# → exits 0 if every OS leg of the latest run completed in ≤60s
# → exits non-zero with diagnostics if any leg exceeded

# 2. Screenshot manifest sanity:
find dist/install-vm-runs/$RUN_ID -name "install-vm-*.png" | wc -l
# → expected: 5 OS × 4 wizard-steps = 20 PNGs minimum

# 3. Per-OS install timing sanity:
for os_dir in dist/install-vm-runs/$RUN_ID/*/; do
  os="$(basename "$os_dir")"
  jq -r '.install_seconds' "$os_dir/timing.json" \
    | awk -v os="$os" '{printf "%s: %.1fs\n", os, $1}'
done
# → expected: 5 lines, each under 60.0s
```

### Post-discharge

- Mark `[x] SHIP-04` in REQUIREMENTS.md.
- Commit `dist/install-vm-runs/$RUN_ID/run.json` + per-OS timing.json into the repo (PNGs go to release-artifacts storage, not the repo, per repo-scrub rules).
- Update `.planning/STATE.md` with the run-id + 5 timing values.

### Unblocks

- **§SHIP-05** — INSTALL-60S contract verified by the same `--check-60s` invocation.
- **§SHIP-07** — SHIP-CUT cut_release.sh can advance past the one-click-install gate.
- **Roadmap success criterion** — "INSTALL-VM matrix discharged across 5 OS images" row goes green.

### Sign-off block

```
SHIP-04 TART INVENTORY VERIFIED on:  _____________________   (date — `tart list` shows 5/5 images)
SHIP-04 LIVE RUN STARTED on:         _____________________   (date — VIBEMIX_INSTALL_VM_RUN=1 captured timing)
SHIP-04 RUN ID:                      _____________________   (UTC timestamp passed to --run-id)
SHIP-04 ALL 5 OS LEGS GREEN:         _____________________   (yes/no — run.json status field)
SHIP-04 60s GATE PASS:               _____________________   (date — `--check-60s` exit 0)
SHIP-04 SCREENSHOTS COMPLETE:        _____________________   (count — expected ≥20)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-05 — INSTALL-60S onboarding-stopwatch contract (KAAN-ACTION)

**REQ-ID:** SHIP-05 (Phase 45 / Plan 45-01)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-04 GREEN  ☐ `--check-60s` gate exits 0  ☐ Kaan-eyes-on confirmation against a fresh personal-Mac install

**Effort:** ~10 minutes verification beyond §SHIP-04 — the gate is already run as part of the matrix discharge. This section documents the CONTRACT (≤60s end-to-end) so future changes can't silently degrade.

**Blocking for:** §SHIP-07 (SHIP-CUT — one-click-install hard requirement gate-keeps the cut).

### Why this is KAAN-action

The 60-second bar is Kaan's product memory (`project_one_click_install_hard_req`). The matrix runner enforces it mechanically via `--check-60s`, but the eyes-on confirmation against an actual fresh Mac (not a tart-cloned VM) is the trust anchor. If `--check-60s` passes but the fresh-Mac walk feels janky, Kaan blocks the cut — that judgement call sits with him.

### Pre-requisites

- §SHIP-04 GREEN: matrix run completed, timing.json dumped per OS.
- One bare-metal fresh Mac available for the eyes-on walk (any Apple Silicon Mac freshly imaged or with vibemix uninstalled + `~/.vibemix/` purged).

### Discharge commands

```bash
# 1. Gate run — same invocation as §SHIP-04, asserts ≤60s contract:
bash scripts/dist/install_vm_matrix.sh --check-60s
# → exits 0 if every OS leg of the latest matrix run completed in ≤60s

# 2. Eyes-on fresh-Mac walk (no script — Kaan does this manually with a
#    stopwatch app open):
#    a. Open the freshly-signed dist/vibemix-*.dmg
#    b. Drag vibemix to /Applications
#    c. Launch from /Applications/vibemix.app
#    d. Start stopwatch when the first wizard screen appears
#    e. Click through: TCC permissions → audio device pick → controller probe → "ready" screen
#    f. Stop the stopwatch when "ready" lands
# → expected: ≤60 seconds wall-clock from wizard-screen-1 to ready

# 3. If the eyes-on walk feels janky despite the gate passing, capture
#    notes to eval/onboarding-feedback/<UTC>.md — that file feeds the
#    SHIP-V1-DECISION audit at T+30 (§SHIP-13).
```

### Verification

```bash
# 1. Re-run the gate after eyes-on:
bash scripts/dist/install_vm_matrix.sh --check-60s
# → exit 0

# 2. Confirm the timing JSON shape:
jq '.os, .install_seconds, .wizard_steps_seen' \
   dist/install-vm-runs/$(ls -1t dist/install-vm-runs/ | head -1)/macos-15/timing.json
# → expected: "macos-15", a number < 60, ≥4 wizard step names

# 3. Eyes-on stopwatch read recorded in
#    eval/onboarding-feedback/<UTC>.md with the wall-clock seconds.
```

### Post-discharge

- Mark `[x] SHIP-05` in REQUIREMENTS.md.
- Append the eyes-on stopwatch value (seconds + pass/fail call) to
  `eval/onboarding-feedback/<UTC>.md`.

### Unblocks

- **§SHIP-07** — the one-click-install hard requirement bar is verified.
- **Roadmap success criterion** — "Fresh-machine install ≤60s end-to-end" row goes green.

### Sign-off block

```
SHIP-05 GATE-RUN GREEN on:           _____________________   (date — `--check-60s` exit 0)
SHIP-05 EYES-ON WALK DATE:           _____________________   (date — fresh-Mac stopwatch walk)
SHIP-05 EYES-ON STOPWATCH:           _____________________   (seconds — wall-clock from wizard-1 to ready)
SHIP-05 EYES-ON FEEL:                _____________________   (pass / fail — Kaan's call)
SHIP-05 FEEDBACK FILE:               _____________________   (path to eval/onboarding-feedback/<UTC>.md)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-06 — Bravoh server endpoints + healthz cron (BRAVOH-TEAM-ACTION)

**REQ-ID:** SHIP-06 / OPS-14-SERVER (Phase 45 / Plan 45-03)
**Owner:** Bravoh team (deploys); Kaan verifies
**Status:** ☐ pre-discharge  ☐ 3 endpoints deployed to https://api.altidus.world  ☐ healthz cron heartbeating every 5 minutes  ☐ `check_bravoh_server_ready.sh` exits 0

**Effort:** ~half-day for the Bravoh-backend team to wire the 3 endpoints + cron. Kaan-side verification is ~5 minutes once they signal "ready".

**Blocking for:** §SHIP-07 (SHIP-CUT Gate 5b — `check_bravoh_server_ready.sh` is invoked by `cut_release.sh`).

### Why this is BRAVOH-TEAM-action

Endpoints live on the Bravoh backend (separate repo: `/var/www/bravoh-backend/`). The vibemix repo's contribution is the verification harness (`scripts/release/check_bravoh_server_ready.sh`) + this runbook as the handoff document.

### Pre-requisites

- Bravoh backend repo has a working FastAPI app at `/var/www/bravoh-backend/`.
- DNS for `api.altidus.world` resolves to the Bravoh backend host (already true).
- `pm2` available on the host for cron scheduling.

### Discharge commands

```bash
# === Bravoh-team side (on the Bravoh backend host) ===

# 1. Implement the 3 endpoints in the Bravoh FastAPI app:
#    • POST /vibemix/updates/upload     — accept signed binary uploads
#                                          from the GH release workflow
#    • GET  /vibemix/updates/latest.json — return the manifest the Tauri
#                                          updater polls
#    • GET  /vibemix/healthz             — return {"ok": true, "ts": ...}

# 2. Deploy the change:
ssh altidus
cd /var/www/bravoh-backend/
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
pm2 restart bravoh-api

# 3. Wire the healthz cron — every 5 minutes hit /vibemix/healthz and
#    record the response into a metrics store:
crontab -l > /tmp/cron.bak
echo "*/5 * * * * curl -s -m 5 https://api.altidus.world/vibemix/healthz | logger -t vibemix-healthz" >> /tmp/cron.bak
crontab /tmp/cron.bak

# 4. Smoke-test from anywhere with internet:
curl -fsSL https://api.altidus.world/vibemix/healthz
# → expected: {"ok": true, "ts": <unix timestamp>}

# === Kaan-side verification (from the vibemix repo on Kaan's Mac) ===

# 5. Run the verifier:
bash scripts/release/check_bravoh_server_ready.sh
# → 3-endpoint probe:
#    • POST /vibemix/updates/upload  (with a tiny dummy payload)
#    • GET  /vibemix/updates/latest.json
#    • GET  /vibemix/healthz
# → exits 0 if all 3 responsive
```

### Verification

```bash
# 1. Direct endpoint hits (matches what check_bravoh_server_ready.sh runs):
curl -fsSL https://api.altidus.world/vibemix/healthz | jq .ok
# → expected: true

curl -fsSL https://api.altidus.world/vibemix/updates/latest.json | jq 'keys'
# → expected: array including "version", "url", "signature", "platform"

curl -fsSL -X POST https://api.altidus.world/vibemix/updates/upload \
    -H "Content-Type: application/json" \
    -d '{"probe": true}' | jq .status
# → expected: "rejected-probe" or "accepted" (probe-mode response)

# 2. Healthz cron heartbeating — wait 6 minutes after enabling cron then:
ssh altidus "journalctl -t vibemix-healthz --since '10 minutes ago' | wc -l"
# → expected: ≥1 (at least one cron hit logged in last 10 min)

# 3. Wire-in test — confirms cut_release.sh calls the verifier:
uv run pytest tests/repo/test_cut_release_invokes_bravoh_server.py -v
# → green (Plan 45-03 baseline; must still pass post-discharge)
```

### Post-discharge

- Mark `[x] SHIP-06` and `[x] OPS-14-SERVER` in REQUIREMENTS.md.
- Bravoh team logs the deploy hash + cron-enable timestamp in their internal handoff.
- Update §SHIP-07 status to ☑ Bravoh-server pre-req met.

### Unblocks

- **§SHIP-07** — SHIP-CUT Gate 5b (`check_bravoh_server_ready.sh`) passes.
- **Tauri auto-updater path** — the v3.0 binary in users' hands actually has a live updater target.
- **Roadmap success criterion** — "Bravoh-server endpoints live + healthz cron heartbeating" row goes green.

### Sign-off block

```
SHIP-06 ENDPOINTS DEPLOYED on:       _____________________   (date — Bravoh team `pm2 restart bravoh-api` post-merge)
SHIP-06 HEALTHZ CRON ENABLED on:     _____________________   (date — */5 * * * * cron added)
SHIP-06 SMOKE GREEN on:              _____________________   (date — curl /vibemix/healthz returns ok=true)
SHIP-06 KAAN VERIFIER PASS on:       _____________________   (date — check_bravoh_server_ready.sh exit 0)
SHIP-06 WIRE-IN TEST PASS:           _____________________   (date — test_cut_release_invokes_bravoh_server.py green)
Sign-off by (Bravoh-team-lead):      _____________________
Counter-sign by (Kaan):              _____________________
```

## §SHIP-07 — SHIP-CUT public RC draft (KAAN-ACTION)

**REQ-ID:** SHIP-07 (Phase 45 / Plan 45-02 + Plan 45-03)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-03 GREEN  ☐ §SHIP-04 GREEN  ☐ §SHIP-05 GREEN  ☐ §SHIP-06 GREEN  ☐ tag-regex bumped  ☐ cut_release.sh exits 0 across all 6 gates  ☐ `gh release create v3.0.0-rc1 --draft` succeeds

**Effort:** ~15 minutes once all prerequisites are green. The cut itself is one `cut_release.sh` invocation + one `gh release create` invocation; most of the time was pre-spent in §SHIP-01..06.

**Blocking for:** §SHIP-08 (SHIP-TWEET — social publish wants a tagged release URL), §SHIP-09 (SHIP-DISCORD — same), §SHIP-10 (SHIP-TRANSFER — clean cut on `main` before the repo flips owners), §SHIP-11 (SHIP-ROTATE — 24h monitoring keys on the public RC's first traffic), §SHIP-12 (INSTALL-DEFENDER — SmartScreen reputation only starts after a real public release), §SHIP-13 (SHIP-V1-DECISION — the T+30 audit reads from the cut tag).

### Why this is KAAN-action

`gh release create` writes to the public GitHub repo with the production tag. The command is small but the consequence is the most visible action of the entire phase — once the draft flips to `--draft=false` (via the GH UI), the universe knows vibemix shipped. Kaan's eyes confirm release notes + attached artifacts before that publish click.

### Pre-requisites

- §SHIP-03 GREEN: `dist/*.dmg`, `dist/*.pkg`, `dist/*.msi`, `dist/*.exe` all signed + verified.
- §SHIP-04 GREEN: INSTALL-VM matrix discharged + screenshots captured.
- §SHIP-05 GREEN: 60s onboarding-stopwatch contract met.
- §SHIP-06 GREEN: Bravoh server endpoints live, `check_bravoh_server_ready.sh` exit 0.
- **Pre-requisite — tag-regex bump:** `scripts/launch/cut_release.sh` line 44 currently ships `TAG_REGEX='^v2\.1\.0-rc[0-9]+$'` from the Phase 39 v2.1 carryover. v3.0 needs `'^v3\.0\.0-rc[0-9]+$'`. This is a one-line `sed` to be executed by Kaan (or via a one-line follow-up PR) BEFORE invoking the cut:

  ```bash
  sed -i.bak "s|TAG_REGEX='\\^v2\\\\.1\\\\.0-rc\\[0-9\\]+\\$'|TAG_REGEX='\\^v3\\\\.0\\\\.0-rc\\[0-9\\]+\\$'|" \
      scripts/launch/cut_release.sh
  rm scripts/launch/cut_release.sh.bak
  uv run pytest tests/repo/test_cut_release_invokes_check_gate.py \
                 tests/repo/test_cut_release_invokes_bravoh_server.py -v
  # → both green (gates 2b + 5b wiring untouched)
  git add scripts/launch/cut_release.sh
  git commit -m "chore(45-07-prep): bump cut_release.sh tag regex v2.1.0-rc → v3.0.0-rc1 for SHIP-CUT"
  ```

  This is a deliberate prerequisite (not a deviation): the regex change ships as its own commit so the cut commit stays clean.
- `scripts/launch/populate_changelog.py` ran to produce `dist/release-notes.md` (or the equivalent path).

### Discharge commands

```bash
# 0. Tag-regex bump (see Pre-requisites above) — must happen before step 1.

# 1. Run cut_release.sh — exercises all 6 gates:
bash scripts/launch/cut_release.sh v3.0.0-rc1
# → Gate 1: tag matches new regex ^v3\.0\.0-rc[0-9]+$  → pass
# → Gate 2: no-hardcoded-model gate (Phase 41-01)
# → Gate 2b: hybrid hallucination gate (Phase 42)
# → Gate 3: launch-copy AI-slop clean (Phase 44-05)
# → Gate 4: launch-docs drift check (Phase 44-07)
# → Gate 5: dist artifacts signed + verified (Phase 27/34 verify_signed.py)
# → Gate 5b: Bravoh server ready (Plan 45-03 check_bravoh_server_ready.sh)
# → final: prints the `gh release create` command for human review

# 2. Generate release notes if not already present:
uv run python scripts/launch/populate_changelog.py --tag v3.0.0-rc1 --output dist/release-notes.md

# 3. Create the DRAFT release (note: --draft means it's NOT live yet —
#    Kaan flips to non-draft via GH UI after eyeballing):
gh release create v3.0.0-rc1 \
    --draft \
    --target main \
    --title "vibemix v3.0.0-rc1 — public release candidate" \
    --notes-file dist/release-notes.md \
    dist/*.dmg dist/*.pkg dist/*.msi dist/*.exe

# 4. Eyeball the draft on github.com/ozzaii/vibemix/releases/tag/v3.0.0-rc1
#    Confirm: title + notes + 4 artifact shapes all present.
#    Confirm: download counts start at 0 (we haven't published yet).

# 5. Flip to public via GH UI:
#    → "Edit release" → uncheck "Set as a pre-release" / "Save as draft"
#       → "Publish release"
#    Equivalent CLI (skips the UI eyeball — discouraged for the first
#    public cut):
#    gh release edit v3.0.0-rc1 --draft=false --prerelease
```

### Verification

```bash
# 1. All 6 gates passed in cut_release.sh — exit code 0:
echo $?
# → 0

# 2. Draft release exists with the right artifacts:
gh release view v3.0.0-rc1 --json assets --jq '.assets[].name' | sort
# → expected: 4 lines (dmg, pkg, msi, exe — or more if multi-arch Mac)

# 3. The release notes file contains the v3.0 anchor phrases (sanity):
grep -E "real DJ friend in your ear|built by DJs|open[- ]source|Mac \+ Windows" \
      dist/release-notes.md | wc -l
# → expected: ≥3 (anchor phrases per Plan 44-05 sign-off footer rule)

# 4. After publish-click — release is live:
curl -fsSL https://api.github.com/repos/ozzaii/vibemix/releases/tags/v3.0.0-rc1 \
    | jq '{draft, prerelease, published_at}'
# → expected: {"draft": false, "prerelease": true, "published_at": "<ISO timestamp>"}

# 5. The first install via curl-pipe-sh works against the public artifact URL
#    (validates Tauri updater can fetch the latest.json after Bravoh server pulls
#    from the public release):
curl -fsSL https://api.altidus.world/vibemix/updates/latest.json | jq .version
# → expected: "v3.0.0-rc1"
```

### Post-discharge

- Mark `[x] SHIP-07` in REQUIREMENTS.md.
- Record the cut commit SHA + release-tag UTC timestamp in `.planning/STATE.md`.
- Update §SHIP-08 status to ☑ pre-req met — social publish can fire.
- Update §SHIP-10 status to ☑ pre-req met — repo transfer can run.

### Unblocks

- **§SHIP-08** — SHIP-TWEET 5-channel social publish has a public release URL to point to.
- **§SHIP-09** — SHIP-DISCORD #announcements post can include the public release URL.
- **§SHIP-10** — Repo transfer to bravoh-vibemix can proceed (cut belongs on the pre-transfer URL; transfer happens AFTER cut).
- **§SHIP-11** — 24h monitoring rotation starts when this lands.
- **§SHIP-12** — Windows SmartScreen reputation clock starts on the public binary.
- **§SHIP-13** — T+30 SHIP-V1-DECISION audit reads from this release-tag's telemetry.

### Sign-off block

```
SHIP-07 TAG-REGEX BUMPED on:         _____________________   (date — sed + commit)
SHIP-07 CUT_RELEASE GREEN on:        _____________________   (date — `bash cut_release.sh v3.0.0-rc1` exit 0)
SHIP-07 ALL 6 GATES GREEN:           _____________________   (gate 1 / 2 / 2b / 3 / 4 / 5 / 5b — all pass)
SHIP-07 RELEASE NOTES GENERATED:     _____________________   (date — `populate_changelog.py` ran)
SHIP-07 DRAFT RELEASE CREATED on:    _____________________   (date — `gh release create --draft` returned URL)
SHIP-07 RELEASE URL:                 _____________________   (https://github.com/.../releases/tag/v3.0.0-rc1)
SHIP-07 ASSETS ATTACHED:             _____________________   (count — expected ≥4)
SHIP-07 EYEBALL PASS:                _____________________   (yes/no — title + notes + assets all look right)
SHIP-07 PUBLIC PUBLISH on:           _____________________   (date — draft flipped off via GH UI)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-08 — SHIP-TWEET 5-channel social publish (KAAN-ACTION)

**REQ-ID:** SHIP-08 (Phase 45 / Plan 45-02)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-07 GREEN (public release URL live)  ☐ launch-copy signature footers locked (Plan 44-05)  ☐ 4 cadence-stage invocations fired  ☐ dist/launch-runs/<UTC>.jsonl records 14 channel:stage pairs

**Effort:** ~30 seconds active execution per stage × 4 stages = ~2 minutes total compute. Spread across 24h calendar window (T-30 / T+0 / T+5h / T+24h) — each stage fires at its scheduled moment per `scripts/dayzero/launch_copy/cadence_index.json`.

**Blocking for:** §SHIP-09 (SHIP-DISCORD #announcements post — the Discord cadence rides on the same trigger), §SHIP-11 (SHIP-ROTATE 24h monitoring window starts at T+0 launch_trigger fire), §SHIP-13 (SHIP-V1-DECISION audit reads from `dist/launch-runs/` jsonls).

### Why this is KAAN-action

`launch_trigger.sh --live` writes to public social channels (Twitter, Instagram, LinkedIn, Reddit, Discord). The `--live` flag is the kill switch — `LAUNCH_REAL=1` env var enforces double-confirmation that this is the real publish, not a dry-run. Per CLAUDE.md privacy + secrets discipline, autonomous agents NEVER hold Twitter/Instagram/Reddit posting tokens. Kaan's machine sources the OAuth tokens at runtime.

### Pre-requisites

- §SHIP-07 GREEN: public release URL is live + flipped off draft.
- Plan 44-05 sign-off footer + AI-slop gate green across all 5 launch-copy files (`scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit,discord}.txt`).
- `scripts/launch/launch_trigger.sh` exists + executable (Plan 45-02).
- `scripts/dayzero/launch_copy/cadence_index.json` reflects the per-stage per-channel routing (Plan 45-02).
- OAuth tokens posted to GH secrets:
  - Twitter / X: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`.
  - Instagram: `INSTAGRAM_ACCESS_TOKEN`.
  - LinkedIn: `LINKEDIN_ACCESS_TOKEN`.
  - Reddit: `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`.
  - Discord: `DISCORD_WEBHOOK_URL` (announcements channel webhook).
- GH CLI auth ready (`gh auth status` exit 0) so `GITHUB_TOKEN=$(gh auth token)` resolves.

### Discharge commands

```bash
# Pre-flight (run once before the cadence fires):
gh auth status
export LAUNCH_REAL=1
export GITHUB_TOKEN="$(gh auth token)"
export DISCORD_WEBHOOK_URL="<announcements-webhook-from-GH-secret>"
# Twitter / Instagram / LinkedIn / Reddit OAuth tokens are sourced by
# scripts/launch/publish_social_posts.py from GH secrets in CI mode;
# for local execution, also export them:
#   export TWITTER_API_KEY=... TWITTER_API_SECRET=...
#   export INSTAGRAM_ACCESS_TOKEN=... LINKEDIN_ACCESS_TOKEN=...
#   export REDDIT_USERNAME=... REDDIT_PASSWORD=...
#   export REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=...

# Stage 1: T-30 — 30 minutes before launch hour (Twitter + Instagram + Discord)
bash scripts/launch/launch_trigger.sh --live --phase T-30

# Stage 2: T+0 — the launch moment itself (Twitter + Instagram + LinkedIn + Reddit + Discord)
bash scripts/launch/launch_trigger.sh --live --phase T+0

# Stage 3: T+5h — mid-day amplification (Twitter + Discord only per cadence_index.json)
bash scripts/launch/launch_trigger.sh --live --phase T+5h

# Stage 4: T+24h — one-day-later recap (Twitter + Instagram + LinkedIn + Discord)
bash scripts/launch/launch_trigger.sh --live --phase T+24h
```

### Verification

```bash
# 1. Each stage logs to dist/launch-runs/<UTC>.jsonl — confirm one per stage:
ls -1 dist/launch-runs/*.jsonl | wc -l
# → expected: 4 (one jsonl per stage; matches the 4 invocations above)

# 2. Per-channel per-stage publish accounting:
cat dist/launch-runs/*.jsonl \
    | jq -r 'select(.mode=="live") | .channel + ":" + .stage' \
    | sort -u
# → expected: the channel:stage pairs from cadence_index.json non-null cells:
#   discord:T+0, discord:T+24h, discord:T+5h, discord:T-30,
#   instagram:T+0, instagram:T+24h, instagram:T-30,
#   linkedin:T+0, linkedin:T+24h,
#   reddit:T+0,
#   twitter:T+0, twitter:T+24h, twitter:T+5h, twitter:T-30
#   = 14 unique pairs

# 3. Per-stage publish was not silently dry-run — `mode=="live"` flag set:
jq 'select(.mode != "live") | .channel + ":" + .stage' dist/launch-runs/*.jsonl
# → expected: empty (zero non-live records when LAUNCH_REAL=1 set)

# 4. Twitter / Instagram / LinkedIn / Reddit / Discord posts visible on
#    the live accounts:
#    → https://twitter.com/<bravoh-handle>
#    → https://www.instagram.com/<bravoh-handle>/
#    → https://www.linkedin.com/company/bravoh
#    → https://reddit.com/user/<bravoh-handle>/submitted
#    → Discord #announcements channel
```

### Post-discharge

- Mark `[x] SHIP-08` in REQUIREMENTS.md.
- Archive the 4 jsonl logs under `dist/launch-runs/v3.0.0-rc1/` (rename or copy from the UTC-stamped names — keeps them grouped by release).
- Update §SHIP-09 status to ☑ T+0 stage fired — Discord launch post lands here.
- Update §SHIP-11 status to ☑ T+0 fired — 24h rotation clock starts.

### Unblocks

- **§SHIP-09** — SHIP-DISCORD #announcements post is one of the 14 channel:stage pairs (T+0 row).
- **§SHIP-11** — 24h monitoring rotation begins T+0..T+24h per `docs/launch-rotation.md §SHIP-11`.
- **§SHIP-13** — T+30 audit reads `dist/launch-runs/*.jsonl` for engagement metrics.
- **Roadmap success criterion** — "5-channel social publish discharged across 4 cadence stages" row goes green.

### Sign-off block

```
SHIP-08 LAUNCH_REAL EXPORTED on:     _____________________   (date — env var set in Kaan's shell)
SHIP-08 OAUTH TOKENS VERIFIED:       _____________________   (yes/no — all 11+ env vars resolve)
SHIP-08 T-30 STAGE FIRED on:         _____________________   (timestamp — wall-clock T-30 invocation)
SHIP-08 T+0  STAGE FIRED on:         _____________________   (timestamp — launch moment)
SHIP-08 T+5h STAGE FIRED on:         _____________________   (timestamp — mid-day amplification)
SHIP-08 T+24h STAGE FIRED on:        _____________________   (timestamp — one-day recap)
SHIP-08 14 PAIRS RECORDED:           _____________________   (yes/no — jq channel:stage sort -u count)
SHIP-08 ZERO DRY-RUN RECORDS:        _____________________   (yes/no — `mode != "live"` count is 0)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-09 — SHIP-DISCORD #announcements launch post + provision-live (KAAN-ACTION)

**REQ-ID:** SHIP-09 (Phase 45)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-07 GREEN  ☐ §LAUNCH-08 GUILD CREATED + BOT TOKEN SOURCED  ☐ provision-live one-time fired (5 roles + 9 channels)  ☐ #announcements launch post fired  ☐ idempotency re-run shows 14 skips

**Effort:** ~10 minutes — provision-live is one command (one-shot, idempotent); launch post is one command. Most time is eyes-on verification in Discord.

**Blocking for:** §SHIP-11 (24h rotation watches Discord #bugs + #announcements engagement).

### Why this is KAAN-action

`BRAVOH_DISCORD_BOT_TOKEN` lives in Kaan's environment + GH secrets per §LAUNCH-08 — autonomous agents never hold it. Both invocations write to the real Discord guild; both require `--live` / `--real` explicit opt-in flags per the Phase 44-06 ergonomics rule. The dry-run paths are the engineering test surface; live discharge is operator-only.

### Pre-requisites

- §SHIP-07 GREEN: public release URL exists (the launch post links to it).
- §LAUNCH-08 fully signed off: guild created + bot token in `BRAVOH_DISCORD_BOT_TOKEN` env var + GH secret set + dry-run green against real guild ID.
- `scripts/dayzero/discord_provision.py` exists (Phase 44-06).
- `scripts/launch/post_discord_launch.py` exists (Phase 36).
- Guild ID captured (numeric, 18-19 digits — recorded in §LAUNCH-08 sign-off block).

### Discharge commands

```bash
# Pre-flight:
export BRAVOH_DISCORD_BOT_TOKEN='<from-GH-secret-or-1Password>'
export LAUNCH_REAL=1

# 1. Provision-live — one-shot, idempotent (re-running prints 14 skips
#    instead of 14 creates). Already done as part of §LAUNCH-08 discharge,
#    re-run here to confirm idempotency before the launch post:
LAUNCH_REAL=1 uv run python scripts/dayzero/discord_provision.py \
    --live --guild-id <numeric-guild-id>
# → expected if first time: 5 × "[done] created role" + 9 × "[done] created channel"
# → expected if re-run: 14 × "[skip] role exists"/"[skip] channel exists"

# 2. Post the launch announcement to #announcements channel:
LAUNCH_REAL=1 uv run python scripts/launch/post_discord_launch.py --real
# → reads the v3.0.0-rc1 launch copy from
#   scripts/dayzero/launch_copy/discord.txt (Plan 44-05 locked),
#   substitutes the public release URL from §SHIP-07,
#   posts via webhook (or via bot token to channel ID — script handles both)
# → prints the resulting message URL on success
```

### Verification

```bash
# 1. Idempotency confirmed — re-run provision shows 14 skips:
LAUNCH_REAL=1 uv run python scripts/dayzero/discord_provision.py \
    --live --guild-id <numeric-guild-id> | grep -c "^\[skip\]"
# → expected: 14

# 2. Token-source audit:
LAUNCH_REAL=1 uv run python scripts/dayzero/discord_provision.py \
    --live --guild-id <numeric-guild-id> 2>&1 | grep "bot token source"
# → expected: "[live] bot token source: BRAVOH_DISCORD_BOT_TOKEN"

# 3. Eyes-on the Discord guild — #announcements channel shows the launch post:
#    → message body cites the public release URL from §SHIP-07
#    → embed renders (if scripts/launch/post_discord_launch.py uses embed payload)
#    → no @everyone / @here ping (we explicitly do NOT spam pings — Plan 44-05 rule)

# 4. Post-publish — Discord #announcements engagement is one of the
#    surfaces §SHIP-11 monitoring watches; record initial message ID for
#    later reference:
#    → right-click message in Discord → Copy Message Link → record in §SHIP-09 sign-off.

# 5. Engineering gates still green:
uv run pytest tests/dayzero/test_discord_provision_dryrun.py tests/dayzero/test_discord_provision.py -v
# → green (Phase 44-06 baseline preserved)
```

### Post-discharge

- Mark `[x] SHIP-09` in REQUIREMENTS.md.
- Record the launch-post Discord message URL in §SHIP-09 sign-off block.
- Update §SHIP-11 status to ☑ Discord launch surface live (rotation watches it).

### Unblocks

- **§SHIP-11** — 24h rotation monitors Discord #bugs + #announcements engagement as one of the 7 monitoring sources per `docs/launch-rotation.md §SHIP-11`.
- **Community surface fully live** — README community link, onboarding docs, LAUNCH-SEQUENCE T-0 row all resolve to a real Discord with a real launch post.
- **Roadmap success criterion** — "Discord #announcements launch post fired live" row goes green.

### Sign-off block

```
SHIP-09 PROVISION-LIVE IDEMPOTENT:   _____________________   (yes — re-run prints 14 [skip] lines)
SHIP-09 TOKEN SOURCE CONFIRMED:      _____________________   (yes — BRAVOH_DISCORD_BOT_TOKEN env var was used)
SHIP-09 LAUNCH POST FIRED on:        _____________________   (timestamp — `post_discord_launch.py --real` ran)
SHIP-09 LAUNCH POST MESSAGE URL:     _____________________   (https://discord.com/channels/.../...)
SHIP-09 RELEASE URL IN POST:         _____________________   (yes — message body cites §SHIP-07 release URL)
SHIP-09 NO @EVERYONE / @HERE PINGS:  _____________________   (yes — Plan 44-05 anti-spam rule honored)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-10 — SHIP-TRANSFER repo handoff to bravoh/vibemix (KAAN-ACTION)

**REQ-ID:** SHIP-10 (Phase 45)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-07 GREEN  ☐ check_bravoh_org_ready.sh exit 0  ☐ `gh api -X POST` transfer fired  ☐ new URL resolves to bravoh/vibemix  ☐ webhooks + CI secrets re-mapped to new repo

**Effort:** ~30 minutes total. The transfer itself is one `gh api` command; the bulk of the time is post-transfer cleanup (re-mapping CI secrets, updating README badges, updating Tauri updater URL if it pointed at the old repo).

**Blocking for:** None — this is a one-way action that closes out the pre-launch repo identity. After this fires, the repo lives at `github.com/bravoh/vibemix` permanently.

### Why this is KAAN-action

Repo transfer is the highest-privilege manual command in the entire publish cascade. The literal command is intentionally not parameterized into a script — Kaan eyeballs it before pressing return (T-45-06-04 threat model: elevation-of-privilege mitigation). The destination `bravoh` org must exist + Kaan must have admin on both sides (source ozzaii personal + destination bravoh org).

### Pre-requisites

- §SHIP-07 GREEN: public release `v3.0.0-rc1` exists on the pre-transfer URL `github.com/ozzaii/vibemix/releases/tag/v3.0.0-rc1`. GitHub preserves release URLs across transfers (redirects), but the cut belongs on the pre-transfer identity for audit clarity.
- Bravoh GH org `bravoh` exists + Kaan is an admin (verified via `bash scripts/launch/check_bravoh_org_ready.sh` per Phase 44-06).
- All 5 launch-copy posts (§SHIP-08) already fired — re-running them after transfer would duplicate.
- Tauri updater target URL audited: `tauri/src-tauri/tauri.conf.json` updater section should point at `api.altidus.world/vibemix/updates/latest.json` (Bravoh-side, not GH-pages), so the transfer doesn't break the auto-updater. Confirm:
  ```bash
  jq '.tauri.updater.endpoints' tauri/src-tauri/tauri.conf.json
  # → expected: array containing "https://api.altidus.world/vibemix/updates/latest.json"
  ```

### Discharge commands

```bash
# Pre-flight: confirm Bravoh org standup is complete
bash scripts/launch/check_bravoh_org_ready.sh
# → exit 0 (Phase 44-06 polling gate; checks Bravoh org exists +
#   teams created + Kaan admin)

# Resolve the current owner (should be "ozzaii" pre-transfer):
CURRENT_OWNER="$(gh repo view --json owner --jq .owner.login)"
echo "Current owner: $CURRENT_OWNER"
# → expected: "ozzaii"

# THE TRANSFER COMMAND (literal — Kaan eyeballs before return):
gh api -X POST repos/$CURRENT_OWNER/vibemix/transfer -f new_owner=bravoh

# GitHub responds 202 Accepted (async transfer); the new owner has 7 days
# to accept via email confirmation. Kaan as bravoh org admin clicks the
# confirmation email — once accepted, the redirect is in place.
```

### Verification

```bash
# 1. Direct API check — new owner is "bravoh":
gh repo view bravoh/vibemix --json owner --jq .owner.login
# → expected: "bravoh"

# 2. Redirect in place — old URL forwards to new:
curl -fsSLI https://github.com/ozzaii/vibemix | grep -i "^location:"
# → expected: location: https://github.com/bravoh/vibemix

# 3. Release URLs preserved (the §SHIP-07 release-page URL still works
#    via redirect):
curl -fsSL https://api.github.com/repos/ozzaii/vibemix/releases/tags/v3.0.0-rc1 \
    | jq .html_url
# → expected: "https://github.com/bravoh/vibemix/releases/tag/v3.0.0-rc1"

# 4. CI secrets — GH transfers org-level secrets but NOT user-level ones
#    that the old workflow inherited. Re-post any user-scoped secrets to
#    the bravoh-org level:
gh secret list --repo bravoh/vibemix
# → eyeball the list; re-post any missing secrets that were on ozzaii:
gh secret set APPLE_DEVELOPER_ID --repo bravoh/vibemix --body "<value>"
# (...and the other Apple + SignPath + Discord + social tokens as needed)

# 5. Tauri auto-updater still resolves — the Bravoh-side latest.json
#    doesn't care about the GH URL, so this is a smoke check:
curl -fsSL https://api.altidus.world/vibemix/updates/latest.json | jq .version
# → expected: "v3.0.0-rc1"
```

### Post-discharge

- Mark `[x] SHIP-10` in REQUIREMENTS.md.
- Record the transfer-accept timestamp + new repo URL in `.planning/STATE.md`.
- Update README badges if any were `ozzaii/vibemix`-prefixed:
  ```bash
  rg "ozzaii/vibemix" README.md
  # → eyeball; if any found, sed to bravoh/vibemix + commit on the new repo
  ```

### Unblocks

- **§SHIP-11** — Rotation watches the post-transfer URL (bravoh/vibemix issues + PRs).
- **§SHIP-13** — T+30 audit reads telemetry from the post-transfer release URL.
- **Repo identity is final** — onboarding docs, GitHub topics, README badges all reference the canonical `bravoh/vibemix` location.

### Sign-off block

```
SHIP-10 ORG-READY GATE PASS on:      _____________________   (date — `check_bravoh_org_ready.sh` exit 0)
SHIP-10 PRE-TRANSFER OWNER:          _____________________   (expected "ozzaii")
SHIP-10 TRANSFER FIRED on:           _____________________   (timestamp — `gh api -X POST ... transfer` returned 202)
SHIP-10 ACCEPTED VIA EMAIL on:       _____________________   (date — Kaan clicked the bravoh-side confirmation link)
SHIP-10 NEW OWNER VERIFIED:          _____________________   (date — `gh repo view bravoh/vibemix` returned bravoh)
SHIP-10 REDIRECT GREEN:              _____________________   (date — old URL forwards to new)
SHIP-10 CI SECRETS RE-MAPPED:        _____________________   (date — bravoh-side secrets posted)
SHIP-10 TAURI UPDATER UNAFFECTED:    _____________________   (yes — api.altidus.world resolution still green)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-11 — SHIP-ROTATE 24h monitoring rotation (KAAN-ACTION)

**REQ-ID:** SHIP-11 (Phase 45 / Plan 45-05)
**Owner:** Kaan (solo rotation for v3.0)
**Status:** ☐ pre-discharge  ☐ §SHIP-07 GREEN  ☐ §SHIP-08 T+0 GREEN  ☐ §SHIP-09 GREEN  ☐ 4 × 6h shifts executed  ☐ shift handoff notes posted per docs/launch-rotation.md

**Effort:** 24 hours of intermittent attention. Per shift, ~10-15 minutes per check-in × ~4 check-ins per shift = ~60 minutes active work per 6h shift. Sleep-shift T+18..T+24 is alerts-only (GH Actions email + Discord pings).

**Blocking for:** §SHIP-13 (T+30 SHIP-V1-DECISION audit reads rotation handoff notes).

### Why this is KAAN-action

The operational source-of-truth for shift schedule + triage decision tree + 7 monitoring sources lives at `docs/launch-rotation.md §SHIP-11` (Plan 45-05). This runbook section is the discharge handle — it points operators at the rotation doc and tracks per-shift sign-off here. Per memory `feedback_no_scope_creep_clean_utility`, v3.0 is single-rotator (Kaan); v3.x may add Francesco/Momo.

### Pre-requisites

- §SHIP-07 GREEN: public release live (rotation starts at the T+0 publish moment).
- §SHIP-08 T+0 stage GREEN: social publish fired (gives the public an entry-point to discover the release).
- §SHIP-09 GREEN: Discord #announcements post landed (one of the 7 monitoring sources).
- `docs/launch-rotation.md` carries the §SHIP-11 24h schedule + triage tree + 7 monitoring sources list (Plan 45-05 — must exist on disk before this discharge).
- Bravoh server `healthz` cron heartbeating (§SHIP-06) — rotation monitors uptime.

### Discharge commands

```bash
# The rotation has no single command — it's a 24h watch window. Each
# shift has the same structure per docs/launch-rotation.md §SHIP-11:

# Shift 1: T+0..T+6h (Kaan European morning, 08:00-14:00 CET)
# Shift 2: T+6..T+12h (Kaan European afternoon, 14:00-20:00 CET)
# Shift 3: T+12..T+18h (Kaan European evening, 20:00-02:00 CET)
# Shift 4: T+18..T+24h (Kaan sleep-shift, alerts-only — GH Actions email +
#          Discord pings on #bugs / #announcements)

# Per shift, run the 7 monitoring spot-checks per docs/launch-rotation.md:
#   1. GitHub Actions runs — `gh run list --workflow=release.yml --limit 5`
#   2. Bravoh healthz uptime — `curl -fsSL https://api.altidus.world/vibemix/healthz | jq .ok`
#   3. GH issues opened since T+0 — `gh issue list --repo bravoh/vibemix --search "created:>$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%S)"`
#   4. Discord #bugs channel — eyes-on
#   5. Discord #announcements engagement — eyes-on
#   6. Twitter mentions — eyes-on
#   7. README download counts — `gh release view v3.0.0-rc1 --json assets --jq '.assets[] | {name, download_count}'`

# Per shift, record handoff notes by appending to docs/launch-rotation.md
# §SHIP-11 shift-log table (one row per shift):
#   | shift | start | end | issues | crashes | api_key_rate_limit_hits | bravoh_healthz_uptime | call |
```

### Verification

```bash
# 1. docs/launch-rotation.md §SHIP-11 shift-log carries 4 rows:
grep -A 100 "^## §SHIP-11" docs/launch-rotation.md \
    | grep -cE "^\| shift-[1-4] \|"
# → expected: 4 (one per shift)

# 2. Bravoh healthz uptime over the 24h window (post-rotation summary):
ssh altidus "journalctl -t vibemix-healthz --since 'T+0 timestamp' --until 'T+24h timestamp' | wc -l"
# → expected: ≥288 (24h × 12 hits/hour = 288 minimum given 5-min cron)

# 3. Sign-off block in docs/launch-rotation.md §SHIP-11 filled (every
#    shift row has a "call" cell — green / yellow / red):
grep -A 50 "^## §SHIP-11" docs/launch-rotation.md \
    | grep -cE "(green|yellow|red)"
# → expected: ≥4 (one per shift)

# 4. No unresolved P0/P1 issues at T+24h:
gh issue list --repo bravoh/vibemix --label "P0,P1" --state open
# → expected: empty (or escalation path engaged per triage decision tree)
```

### Post-discharge

- Mark `[x] SHIP-11` in REQUIREMENTS.md.
- Final shift handoff: post the 24h summary to Discord #announcements (free-form, not a launch-copy file).
- Update `.planning/STATE.md` with the 24h roll-up metrics (issues opened/closed/escalated, healthz uptime %, crash reports if any).

### Unblocks

- **§SHIP-13** — T+30 audit reads the §SHIP-11 shift-log table + STATE.md 24h metrics.
- **Roadmap success criterion** — "24h post-launch monitoring rotation executed without P0 unresolved" row goes green.

### Sign-off block

```
SHIP-11 ROTATION DOC EXISTS:         _____________________   (yes — docs/launch-rotation.md §SHIP-11 from Plan 45-05)
SHIP-11 SHIFT-1 (T+0..T+6h) on:      _____________________   (call: green/yellow/red)
SHIP-11 SHIFT-2 (T+6..T+12h) on:     _____________________   (call: green/yellow/red)
SHIP-11 SHIFT-3 (T+12..T+18h) on:    _____________________   (call: green/yellow/red)
SHIP-11 SHIFT-4 (T+18..T+24h) on:    _____________________   (call: green/yellow/red — sleep-shift alerts-only)
SHIP-11 P0/P1 ISSUES AT T+24h:       _____________________   (count — expected 0)
SHIP-11 HEALTHZ UPTIME OVER 24h:     _____________________   (% — expected ≥99.5%)
SHIP-11 ROLL-UP POSTED on:           _____________________   (date — Discord #announcements 24h summary)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-12 — INSTALL-DEFENDER SmartScreen reputation observation (KAAN-ACTION — passive)

**REQ-ID:** SHIP-12 (Phase 45)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-07 GREEN  ☐ first-week observation captured  ☐ first-SmartScreen-warning-gone date recorded

**Effort:** Passive — 1-2 weeks elapsed time. Zero active execution; the discharge is documenting what was observed.

**Blocking for:** §SHIP-13 (T+30 audit pulls SmartScreen status as one of the bake-in signals).

### Why this is KAAN-action

Windows SmartScreen reputation accrues against the SignPath signing identity (§SHIP-02) as users download + run the signed binary. For brand-new signing identities, Microsoft Defender SmartScreen shows a "Windows protected your PC" warning on first-run until ~thousands of installs accumulate. There is NO command to fast-track this — it's purely passive observation. Kaan documents the first date a fresh Win 11 install no longer hits the warning. This is a known-unknown calibration data point for §SHIP-13.

### Pre-requisites

- §SHIP-07 GREEN: public release published — that's the moment the reputation clock starts.
- §SHIP-02 GREEN: SignPath-signed Windows binary in the wild — without this signing identity, SmartScreen behavior is "untrusted publisher" not "no reputation yet" (worse case).
- A fresh Win 11 VM available for periodic re-test (per `tart` image in §SHIP-04 matrix).

### Discharge commands

```bash
# No commands. The discharge is a checklist + observation log:

# Day 1, Day 3, Day 7, Day 14, Day 21, Day 28 (or earlier if signal clears):
#   1. tart clone the fresh win-11 image:
#      tart clone ghcr.io/cirruslabs/windows-server-2022:latest smartscreen-probe-$(date +%Y%m%d)
#   2. tart run smartscreen-probe-... (boot the VM)
#   3. In the VM, open a browser → navigate to the release page (post-§SHIP-10 transfer:
#      https://github.com/bravoh/vibemix/releases/tag/v3.0.0-rc1)
#   4. Download vibemix-*.msi (or .exe)
#   5. Double-click to run
#   6. OBSERVE: does Defender SmartScreen show "Windows protected your PC"?
#      → YES = reputation still propagating; record date + screenshot
#      → NO  = reputation reached threshold; record date as "first-clear date"
#   7. Append result to eval/smartscreen-observations/$(date +%Y-%m-%d).md:
#      - date, win-11 build, SmartScreen verdict, screenshot path
#   8. Destroy the probe VM: tart delete smartscreen-probe-...
```

### Verification

```bash
# 1. Observation log exists with ≥1 entry per probe day:
ls eval/smartscreen-observations/ | wc -l
# → expected: ≥4 entries (Day 1 + 3 + 7 + 14 minimum)

# 2. Each entry carries the 5 fields (date, win-11 build, verdict,
#    screenshot path, signing identity used):
for f in eval/smartscreen-observations/*.md; do
  echo "--- $f ---"
  grep -E "^(date|win-11 build|smartscreen verdict|screenshot|signing identity):" "$f" | wc -l
done
# → expected: 5 per file

# 3. First-clear date documented (the moment "no SmartScreen warning"
#    flips from never-true to true):
grep -l "smartscreen verdict: no warning" eval/smartscreen-observations/*.md \
    | head -1 \
    | xargs -I{} grep "^date:" {}
# → expected: a date string (or empty if SmartScreen hasn't cleared yet by §SHIP-13)
```

### Post-discharge

- Mark `[x] SHIP-12` in REQUIREMENTS.md (regardless of clear/not-clear — the discharge is observation, not outcome).
- Record the first-clear date (or "not yet cleared at T+30") in `.planning/STATE.md`.
- Feed the §SHIP-13 audit script with the SmartScreen status as one of its decision inputs.

### Unblocks

- **§SHIP-13** — T+30 SHIP-V1-DECISION audit pulls SmartScreen status. If still showing warnings, the decision tree biases toward "cycle to v3.0.0-rc2 with same SignPath identity" rather than "cut v1.0.0".
- **Future SignPath identity stability** — first-clear date informs how long subsequent releases under the same identity need to bake.

### Sign-off block

```
SHIP-12 DAY-1 PROBE on:              _____________________   (date — smartscreen verdict: warning / no warning)
SHIP-12 DAY-3 PROBE on:              _____________________   (date — smartscreen verdict: ...)
SHIP-12 DAY-7 PROBE on:              _____________________   (date — smartscreen verdict: ...)
SHIP-12 DAY-14 PROBE on:             _____________________   (date — smartscreen verdict: ...)
SHIP-12 FIRST-CLEAR DATE:            _____________________   (date — first probe with "no warning"; or "not cleared by T+30")
SHIP-12 OBSERVATION LOG PATH:        _____________________   (eval/smartscreen-observations/)
Sign-off by (Kaan):                  _____________________
```

## §SHIP-13 — SHIP-V1-DECISION T+30 audit + Kaan sign-off (KAAN-ACTION)

**REQ-ID:** SHIP-13 (Phase 45 / Plan 45-04)
**Owner:** Kaan
**Status:** ☐ pre-discharge  ☐ §SHIP-07..§SHIP-12 dispositioned  ☐ 30 calendar days elapsed since §SHIP-07 publish  ☐ `audit_ship_v1_decision.py --live` run  ☐ `.planning/decisions/v3.0-SHIP-V1-DECISION.md` generated  ☐ Kaan reads + checks one of 3 boxes + signs off

**Effort:** ~2 hours total — ~5 minutes to run the audit script + ~90 minutes for Kaan to read the report + 30-day perspective + decision rationale + sign-off.

**Blocking for:** v3.0 milestone close. This is the terminal step of the publish cascade — either vibemix cuts v1.0.0, cycles to v3.0.0-rc2, or pauses.

### Why this is KAAN-action

The decision is a product call, not a metric threshold. The audit script (`scripts/release/audit_ship_v1_decision.py` — Plan 45-04) reads the 14-day telemetry roll-up + the §SHIP-11 rotation handoff notes + the §SHIP-12 SmartScreen log + GitHub issues + ear-test feedback, but the WHICH-OF-3-BOXES call is Kaan's eyes + product memory (`feedback_no_scope_creep_clean_utility`, `project_anti_slop_grounded_gemini_thesis`, `project_phase_16_kaan_dj_testing`).

### Pre-requisites

- §SHIP-07..§SHIP-12 all signed off (every checkbox above filled in their respective sign-off blocks).
- 30 calendar days elapsed since the §SHIP-07 PUBLIC PUBLISH timestamp (not 30 days since the draft was created — measure from the moment the public could install it).
- `scripts/release/audit_ship_v1_decision.py` exists + executable (Plan 45-04).
- `docs/SHIP-V1-DECISION-TEMPLATE.md` exists (Plan 45-04 schema).
- GitHub API reachable via `gh auth token`.
- Bravoh healthz stats endpoint live: `https://api.altidus.world/vibemix/healthz/stats` (rollup endpoint, not just the per-hit `/healthz`).
- `eval/ear-test-logs/` has any post-RC ear-test entries Kaan ran during the bake period.

### Discharge commands

```bash
# Pre-flight:
export GITHUB_TOKEN="$(gh auth token)"

# 1. Generate the audit report — reads 14d telemetry + writes the decision template:
GITHUB_TOKEN="$(gh auth token)" uv run python scripts/release/audit_ship_v1_decision.py \
    --live \
    --release-tag v3.0.0-rc1 \
    --bravoh-healthz-stats-url https://api.altidus.world/vibemix/healthz/stats \
    --output .planning/decisions/v3.0-SHIP-V1-DECISION.md
# → reads:
#   • GH release download counts (gh api .../releases/tags/v3.0.0-rc1)
#   • GH issues opened since T+0 (severity rollup via labels)
#   • crash-report issues (label = "crash")
#   • Bravoh healthz cron uptime (last 14d, target ≥99.5%)
#   • eval/ear-test-logs/ post-RC entries (any new ear-test logs)
#   • §SHIP-11 rotation handoff table from docs/launch-rotation.md
#   • §SHIP-12 SmartScreen observation log
#   • dist/launch-runs/*.jsonl engagement metrics
# → writes the report at the --output path, pre-filled with metrics +
#   the 3 decision checkboxes (cut v1.0.0 / cycle v3.0.0-rc2 / pause)

# 2. Read the report — Kaan opens it, eyeballs each section:
${EDITOR:-vim} .planning/decisions/v3.0-SHIP-V1-DECISION.md

# 3. Kaan checks ONE of the 3 decision boxes in the report + writes
#    rationale + signs off.

# 4. Commit the signed decision:
git add .planning/decisions/v3.0-SHIP-V1-DECISION.md
git commit -m "decision(v3.0): SHIP-V1-DECISION sign-off — <cut-v1.0.0 / cycle-rc2 / pause>"
```

### Verification

```bash
# 1. Decision file exists:
[ -f .planning/decisions/v3.0-SHIP-V1-DECISION.md ] && echo "exists" || echo "missing"
# → expected: exists

# 2. Exactly one of the 3 decision boxes is checked:
grep -cE "^\s*-\s*\[x\]\s+(cut v1\.0\.0|cycle to v3\.0\.0-rc2|pause)" \
     .planning/decisions/v3.0-SHIP-V1-DECISION.md
# → expected: 1

# 3. Kaan sign-off line filled (not the underscore placeholder):
grep "^Sign-off by (Kaan):" .planning/decisions/v3.0-SHIP-V1-DECISION.md
# → expected: contains a date + name, NOT underscores

# 4. Rationale section has content (>500 chars — forces actual reasoning,
#    not a one-liner):
awk '/^## Rationale/,/^## /' .planning/decisions/v3.0-SHIP-V1-DECISION.md \
    | wc -c
# → expected: ≥500

# 5. All 8 audit inputs present in the report:
grep -cE "^## (Download Counts|GH Issues|Crash Reports|Healthz Uptime|Ear-Test|Rotation Handoffs|SmartScreen|Launch Engagement)" \
     .planning/decisions/v3.0-SHIP-V1-DECISION.md
# → expected: 8
```

### Post-discharge

- Mark `[x] SHIP-13` in REQUIREMENTS.md.
- Update `.planning/STATE.md` with the decision outcome + commit SHA of the signed decision file.
- If decision = "cut v1.0.0": fire the v1.0.0 cut cascade (separate plan in v3.1 milestone).
- If decision = "cycle to v3.0.0-rc2": kick the v3.0.0-rc2 cut cycle (new SHIP-07 invocation with `--tag v3.0.0-rc2`).
- If decision = "pause": post a #announcements update in Discord with the rationale + next-checkpoint date.
- Close the v3.0 milestone in `.planning/ROADMAP.md`.

### Unblocks

- **v3.0 milestone closure** — this is the terminal step.
- **v3.x roadmap kickoff** — next-milestone planning unblocks once the v3.0 decision is on record.

### Sign-off block

```
SHIP-13 30-DAY GATE on:              _____________________   (date — 30 cal days after §SHIP-07 PUBLIC PUBLISH)
SHIP-13 AUDIT SCRIPT RAN on:         _____________________   (date — `audit_ship_v1_decision.py --live` ran)
SHIP-13 REPORT PATH:                 _____________________   (.planning/decisions/v3.0-SHIP-V1-DECISION.md)
SHIP-13 DECISION:                    _____________________   (one of: cut v1.0.0 / cycle v3.0.0-rc2 / pause)
SHIP-13 RATIONALE COMMITTED on:      _____________________   (date — signed decision file in git)
SHIP-13 DOWNSTREAM ACTION KICKED:    _____________________   (date — v1.0.0-cut OR v3.0.0-rc2-cut OR pause-post)
SHIP-13 v3.0 MILESTONE CLOSED on:    _____________________   (date — ROADMAP.md update)
Sign-off by (Kaan):                  _____________________
```

