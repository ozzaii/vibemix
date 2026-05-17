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
